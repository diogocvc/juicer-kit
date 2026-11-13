"""TASK-008: retry, resume, conflicts, post-merge failure and checkpoints.

Covers plan §10 and the state invariants: a retry never destroys the previous
attempt, interrupted runs are reconciled with evidence, merge conflicts never
leave a partial merge, and post-merge failure never leaves `completed`/`done`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import fake_fail_executor, fake_ok_executor, git as run_git, simple_task_specs
from juicer import gitops
from juicer.errors import GateBlockedError
from juicer.model import new_execution
from juicer.state import utc_now, write_json


def fake_write_then_fail(files, detail="boom"):
    def run(prompt, cwd, agent, timeout):
        for rel, content in files.items():
            path = Path(cwd) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return {"ok": False, "status": "FAIL", "exit_code": 1, "detail": detail,
                "session_id": "ses_fail", "output": detail}
    return run


# ---------- retry: new attempt, previous evidence preserved ----------

def test_retry_uses_new_branch_and_worktree(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_write_then_fail({"partial.py": "P = 1\n"})
    assert juicer.run_task("TASK-001").ok is False
    first = juicer.load_task("TASK-001")
    first_exec = first["current_execution_id"]
    first_result = first["result"]
    assert first_result["branch"] == "juicer/TASK-001"
    first_wt = juicer.root / ".juicer" / "worktrees" / "TASK-001"
    assert first_wt.exists()

    juicer.retry_task("TASK-001")
    retried = juicer.load_task("TASK-001")
    assert retried["attempt_history"][-1]["execution_id"] == first_exec
    assert retried["attempt_history"][-1]["branch"] == "juicer/TASK-001"

    juicer._executor = fake_ok_executor(write_files={"fixed.py": "F = 1\n"})
    assert juicer.run_task("TASK-001").ok is True
    result = juicer.load_task("TASK-001")["result"]
    assert result["branch"] == "juicer/TASK-001-attempt-2"
    assert result["execution_id"] != first_exec
    # both attempts and both branches/worktrees remain auditable
    assert juicer.load_execution(first_exec)["status"] == "failed"
    assert first_wt.exists()
    assert gitops.branch_exists(juicer.root, "juicer/TASK-001")
    assert gitops.branch_exists(juicer.root, "juicer/TASK-001-attempt-2")
    assert (juicer.root / ".juicer" / "worktrees" / "TASK-001-attempt-2").exists()
    preserved = sorted((juicer.evidence_dir / "TASK-001").glob("preserved-*.json"))
    assert preserved

    # the second attempt integrates normally
    juicer.integrate("TASK-001")
    assert juicer.load_task("TASK-001")["status"] == "done"
    assert (juicer.root / "fixed.py").exists()


def test_retry_after_merge_conflict_needs_explicit_intervention(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"app.py": "VALUE = 2\n"})
    assert juicer.run_task("TASK-001").ok
    (juicer.root / "app.py").write_text("VALUE = 999\n", encoding="utf-8")
    run_git(["add", "-A"], juicer.root)
    run_git(["commit", "-m", "concurrent change"], juicer.root)

    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "conflict" in str(exc.value).lower()
    assert "intervention" in str(exc.value).lower()
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "merge conflict" in task["blocked_reason"]
    # no partial merge and the concurrent change is preserved
    assert gitops.is_merging(juicer.root) is False
    assert (juicer.root / "app.py").read_text(encoding="utf-8") == "VALUE = 999\n"

    # explicit retry starts a new attempt from the reconciled main branch
    juicer.retry_task("TASK-001")
    juicer._executor = fake_ok_executor(write_files={"app.py": "VALUE = 3\n"})
    assert juicer.run_task("TASK-001").ok
    result = juicer.load_task("TASK-001")["result"]
    assert result["branch"] == "juicer/TASK-001-attempt-2"
    juicer.integrate("TASK-001")
    assert (juicer.root / "app.py").read_text(encoding="utf-8") == "VALUE = 3\n"


def test_merge_abort_failure_is_reported_as_still_mid_merge(juicer, monkeypatch):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"app.py": "VALUE = 2\n"})
    assert juicer.run_task("TASK-001").ok

    monkeypatch.setattr(gitops, "merge_no_ff",
                        lambda *a, **k: (False, "conflict"))
    calls = {"n": 0}
    real_is_merging = gitops.is_merging

    def flaky_is_merging(repo):
        # Pre-merge check is clean; after the failed merge the abort failed.
        calls["n"] += 1
        return calls["n"] > 1

    monkeypatch.setattr(gitops, "is_merging", flaky_is_merging)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "abort failed" in str(exc.value)
    assert "still mid-merge" in str(exc.value)
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "still mid-merge" in task["blocked_reason"]
    events = [e for e in juicer.events()
              if e["type"] == "integration_conflict"]
    assert events[-1]["data"]["partial_merge"] is True
    assert real_is_merging(juicer.root) is False  # fake did not change git state


# ---------- resume: reconcile interrupted runs with evidence ----------

def _interrupted_task(juicer, worktree_name="TASK-001", execution_id="RUN-INT"):
    branch = "juicer/%s" % worktree_name
    wt = juicer.root / ".juicer" / "worktrees" / worktree_name
    gitops.create_worktree(juicer.root, branch, wt, new_branch=True)
    (wt / "wip.py").write_text("WIP = 1\n", encoding="utf-8")
    exe = new_execution(execution_id, "TASK-001",
                        workspace={"branch": branch, "base_commit": None,
                                   "worktree": str(wt)})
    write_json(juicer.executions_dir / ("%s.json" % execution_id), exe)
    juicer._update_task(
        "TASK-001",
        lambda t: t.update(status="in_progress",
                           current_execution_id=execution_id))
    juicer._update_execution(execution_id, lambda e: e.update(
        status="running", started_at=utc_now()))
    return wt, branch


def test_resume_records_evidence_and_history(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    wt, _ = _interrupted_task(juicer)

    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    task = fresh.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert wt.exists()
    assert task["attempt_history"][-1]["action"] == "resume"
    assert task["attempt_history"][-1]["execution_id"] == "RUN-INT"
    assert fresh.load_execution("RUN-INT")["status"] == "cancelled"

    artifact = Path(report["artifact_ref"])
    assert artifact.exists()
    doc = json.loads(artifact.read_text(encoding="utf-8"))
    assert doc["type"] == "resume_report"
    assert doc["reconciled"][0]["task_id"] == "TASK-001"
    assert "interrupted" in doc["reconciled"][0]["reason"]
    assert "resume_report" in [e["type"] for e in fresh.events()]

    # a second resume does not duplicate or restart anything
    executions_before = sorted(fresh.executions_dir.glob("*.json"))
    report2 = fresh.resume()
    assert report2["recovered"] == []
    assert fresh.load_task("TASK-001")["status"] == "blocked"
    assert sorted(fresh.executions_dir.glob("*.json")) == executions_before


def test_resume_uses_execution_workspace_not_canonical_path(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    wt, _ = _interrupted_task(juicer, worktree_name="TASK-001-attempt-2",
                              execution_id="RUN-ATTEMPT-2")
    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    task = fresh.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert str(wt) in task["blocked_reason"]


def test_resume_terminal_success_reconciles_and_is_idempotent(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    wt, branch = _interrupted_task(juicer, execution_id="RUN-DONE")
    fresh = type(juicer)(juicer.root)
    fresh.init()
    # worker finished, process died before the task flipped
    fresh._update_execution("RUN-DONE", lambda e: e.update(
        status="succeeded", finished_at=utc_now(),
        result={"commit": gitops.head_commit(juicer.root), "branch": branch,
                "execution_id": "RUN-DONE"}))
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    task = fresh.load_task("TASK-001")
    assert task["status"] == "completed"
    assert task["result"]["branch"] == branch
    assert task["attempt_history"][-1]["action"] == "resume"
    assert fresh.resume()["recovered"] == []
    assert fresh.load_task("TASK-001")["status"] == "completed"


# ---------- post-merge failure ----------

def test_post_merge_failure_records_merged_commit(juicer):
    specs = simple_task_specs("TASK-001")
    # This check passes in the task worktree but fails once the marker exists
    # in the integration target, i.e. only on the post-merge phase.
    specs[0]["checks"].append({
        "id": "post-fail",
        "command": [
            sys.executable, "-c",
            "import pathlib,sys; "
            "sys.exit(1 if pathlib.Path('post-fail').exists() else 0)",
        ],
        "required": True,
    })
    juicer.add_tasks(specs)
    juicer._executor = fake_ok_executor(write_files={"f.py": "F = 1\n"})
    assert juicer.run_task("TASK-001").ok
    original = juicer._run_task_checks
    calls = {"post": 0}

    def failing_post(task, cwd, commit, phase="pre_merge"):
        if phase == "post_merge":
            calls["post"] += 1
            if calls["post"] == 1:
                (Path(cwd) / "post-fail").write_text("fail\n", encoding="utf-8")
        return original(task, cwd, commit, phase=phase)

    juicer._run_task_checks = failing_post
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "post-merge" in str(exc.value)

    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert task["status"] not in ("completed", "done")
    merged = gitops.head_commit(juicer.root)
    assert task["result"]["merged_commit"] == merged
    assert task["result"]["post_merge_gate"]["status"] != "PASS"
    assert merged in task["blocked_reason"]

    integration = json.loads(
        (juicer.jdir / "integration-TASK-001.json").read_text(encoding="utf-8"))
    assert integration["merged_commit"] == merged
    assert "integration_post_failed" in [e["type"] for e in juicer.events()]

    # The persisted check artifacts agree with the gate (no PASS/FAIL drift)
    # and pre/post logs are separate files.
    results = [json.loads(line) for line in
               (juicer.checks_dir / "TASK-001.results.jsonl")
               .read_text(encoding="utf-8").splitlines() if line.strip()]
    post_fail = [r for r in results
                 if r["check_id"] == "post-fail" and r["phase"] == "post_merge"]
    assert post_fail and post_fail[-1]["status"] == "FAIL"
    assert post_fail[-1]["log_ref"].endswith("post-fail-post_merge.log")
    pre_fail = [r for r in results
                if r["check_id"] == "post-fail" and r["phase"] == "pre_merge"]
    assert pre_fail and pre_fail[-1]["status"] == "PASS"
    assert pre_fail[-1]["log_ref"] != post_fail[-1]["log_ref"]

    # Explicit correction: retry, re-run, integrate -> done with merge SHA.
    (juicer.root / "post-fail").unlink()
    juicer._run_task_checks = original
    juicer.retry_task("TASK-001")
    juicer._executor = fake_ok_executor(write_files={"f.py": "F = 2\n"})
    assert juicer.run_task("TASK-001").ok
    juicer.integrate("TASK-001")
    fixed = juicer.load_task("TASK-001")
    assert fixed["status"] == "done"
    assert fixed["result"]["merged_commit"] == gitops.head_commit(juicer.root)


# ---------- checkpoint ----------

def test_checkpoint_records_next_step_and_evidence(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"c.py": "C = 1\n"})
    assert juicer.run_task("TASK-001").ok
    result = juicer.load_task("TASK-001")["result"]

    cp = juicer.checkpoint(note="before merge")
    entry = cp["tasks"]["TASK-001"]
    assert entry["next_step"] == "integrate"
    assert entry["evidence"]["commit"] == result["commit"]
    assert entry["evidence"]["execution_id"] == result["execution_id"]
    assert entry["evidence"]["branch"] == result["branch"]
    assert cp["next_action"].startswith("review and integrate")

    juicer.integrate("TASK-001")
    cp2 = juicer.checkpoint(note="after merge")
    assert cp2["tasks"]["TASK-001"]["next_step"] == "none"
    assert cp2["tasks"]["TASK-001"]["status"] == "done"
    assert (cp2["tasks"]["TASK-001"]["evidence"]["merged_commit"]
            == gitops.head_commit(juicer.root))
    assert cp2["next_action"] == "all tasks done; mission complete"

    # failed/blocked tasks advertise an explicit recovery step
    juicer.add_tasks(simple_task_specs("TASK-002"))
    juicer._executor = fake_fail_executor()
    assert juicer.run_task("TASK-002").ok is False
    cp3 = juicer.checkpoint()
    assert cp3["tasks"]["TASK-002"]["next_step"] == "retry"
    # Same-second checkpoints are distinct audit artifacts.
    before = set(juicer.checkpoints_dir.glob("cp-*.json"))
    juicer.checkpoint()
    juicer.checkpoint()
    after = set(juicer.checkpoints_dir.glob("cp-*.json"))
    assert len(after - before) == 2


def test_resume_then_retry_uses_new_attempt_and_preserves_worktree(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    wt, branch = _interrupted_task(juicer)

    # An interrupted task is reported as resumable, not as a dependency wait.
    paused = juicer.checkpoint(note="crashed")
    assert paused["next_action"].startswith("resume in-progress tasks")

    fresh = type(juicer)(juicer.root)
    fresh.init()
    assert fresh.resume()["recovered"] == ["TASK-001"]
    assert fresh.load_task("TASK-001")["status"] == "blocked"

    fresh.retry_task("TASK-001")
    fresh._executor = fake_ok_executor(write_files={"ok.py": "O = 1\n"})
    assert fresh.run_task("TASK-001").ok
    result = fresh.load_task("TASK-001")["result"]
    # The interrupted attempt (attempt_count still 0) is not reused.
    assert result["branch"] == "juicer/TASK-001-attempt-2"
    assert fresh.load_execution(result["execution_id"])["attempt"] == 2
    # Previous worktree/branch/evidence survive the retry.
    assert wt.exists()
    assert gitops.branch_exists(fresh.root, branch)
    preserved = sorted((fresh.evidence_dir / "TASK-001").glob("preserved-*.json"))
    assert preserved
    doc = json.loads(preserved[-1].read_text(encoding="utf-8"))
    assert doc["worktree"] == str(wt)
    assert doc["branch_tip"]

    fresh.integrate("TASK-001")
    assert (fresh.root / "ok.py").exists()
    assert fresh.load_task("TASK-001")["status"] == "done"


def test_resume_ignores_execution_owned_by_another_task(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002"))
    other = new_execution(
        "RUN-OTHER", "TASK-002",
        workspace={"branch": "juicer/TASK-002", "base_commit": None,
                   "worktree": str(juicer.root / ".juicer" / "worktrees" / "TASK-002")})
    other["status"] = "succeeded"
    other["result"] = {"commit": gitops.head_commit(juicer.root),
                       "branch": "juicer/TASK-002"}
    write_json(juicer.executions_dir / "RUN-OTHER.json", other)
    juicer._update_task(
        "TASK-001",
        lambda t: t.update(status="in_progress", current_execution_id="RUN-OTHER"))

    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    task = fresh.load_task("TASK-001")
    # Another task's success must never leak into this task or mark it done.
    assert task["status"] == "failed"
    assert task["status"] != "completed"
    assert task["result"].get("branch") != "juicer/TASK-002"
    assert task["result"].get("execution_id") is None
    assert task["current_execution_id"] is None
    assert all(h.get("execution_id") != "RUN-OTHER"
               for h in task["attempt_history"])
    assert all("TASK-002" not in (h.get("branch") or "")
               for h in task["attempt_history"])
    # A later retry cannot recover the foreign execution either.
    fresh.retry_task("TASK-001")
    retried = fresh.load_task("TASK-001")
    assert retried["attempt_history"][-1]["execution_id"] is None
    assert retried["attempt_history"][-1]["branch"] is None
    assert "resume_execution_mismatch" in [e["type"] for e in fresh.events()]
    assert "TASK-001" in report["recovered"]


def test_preservation_failure_is_recorded_not_silent(juicer, monkeypatch):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_write_then_fail({"partial.py": "P = 1\n"})
    assert juicer.run_task("TASK-001").ok is False
    monkeypatch.setattr(gitops, "update_ref", lambda *a, **k: False)
    juicer.retry_task("TASK-001")
    juicer._executor = fake_ok_executor(write_files={"fixed.py": "F = 1\n"})
    assert juicer.run_task("TASK-001").ok

    assert "attempt_preservation_degraded" in [
        e["type"] for e in juicer.events()]
    preserved = sorted((juicer.evidence_dir / "TASK-001").glob("preserved-*.json"))
    doc = json.loads(preserved[-1].read_text(encoding="utf-8"))
    assert doc["preserved_ref_error"].startswith("refs/juicer/attempts/")
    assert doc["branch_tip"]
    # The new attempt still used a distinct branch; nothing was deleted.
    assert gitops.branch_exists(juicer.root, "juicer/TASK-001")
    assert gitops.branch_exists(juicer.root, "juicer/TASK-001-attempt-2")
