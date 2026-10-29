"""Task/execution transitions, resume reconciliation, retriable blocked."""

from __future__ import annotations

import json
import sys

import pytest

from juicer.errors import InvalidTransitionError, JuicerError
from juicer.model import (
    EXECUTION_TRANSITIONS, TASK_TRANSITIONS, check_transition, new_execution,
    new_task, transition_execution, transition_task,
)
from conftest import fake_ok_executor, simple_task_specs


def test_transition_helpers_validate_and_apply():
    task = new_task("TASK-001", "MISSION-001", "t", "d")
    transition_task(task, "in_progress")
    assert task["status"] == "in_progress"
    with pytest.raises(InvalidTransitionError):
        transition_task(task, "done")  # in_progress -> done is illegal

    exe = new_execution("RUN-1", "TASK-001")
    transition_execution(exe, "running")
    assert exe["status"] == "running"
    with pytest.raises(InvalidTransitionError):
        transition_execution(new_execution("RUN-2", "TASK-001"), "succeeded")


def test_illegal_execution_transition_from_claimed_to_succeeded():
    exe = new_execution("RUN-3", "TASK-001")
    with pytest.raises(InvalidTransitionError):
        transition_execution(exe, "succeeded")
    check_transition("execution", "claimed", "running", EXECUTION_TRANSITIONS)


def test_update_task_rejects_invalid_status_jump(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    with pytest.raises(InvalidTransitionError):
        juicer._update_task("TASK-001", lambda t: t.update(status="done"))


def test_update_execution_rejects_invalid_status_jump(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor()
    # create a real execution via a successful run, then force an illegal jump
    juicer.run_task("TASK-001")
    task = juicer.load_task("TASK-001")
    assert task["status"] == "completed"
    exec_id = task["current_execution_id"]
    with pytest.raises(InvalidTransitionError):
        juicer._update_execution(exec_id, lambda e: e.update(status="claimed"))


def test_completed_done_invariants_are_enforced(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    # cannot jump ready -> done
    with pytest.raises(InvalidTransitionError):
        juicer._update_task("TASK-001", lambda t: t.update(status="done"))
    juicer._executor = fake_ok_executor(write_files={"a.py": "A=1\n"})
    juicer.run_task("TASK-001")
    assert juicer.load_task("TASK-001")["status"] == "completed"
    # completed is not done until integrate
    assert ("completed", "done") in TASK_TRANSITIONS
    assert ("ready", "done") not in TASK_TRANSITIONS
    assert ("in_progress", "done") not in TASK_TRANSITIONS


def test_resume_without_execution_or_worktree_marks_failed(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._update_task("TASK-001", lambda t: t.update(status="in_progress"))
    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    task = fresh.load_task("TASK-001")
    assert task["status"] == "failed"
    assert task["result"]["resumed"] is True
    # still retriable
    fresh.retry_task("TASK-001")
    assert fresh.load_task("TASK-001")["status"] == "ready"


def test_resume_with_worktree_preserves_evidence_as_blocked(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"x.py": "X=1\n"})
    # start a run then simulate crash mid-flight: force back to in_progress
    # by creating worktree + execution through the normal path, then resetting
    # task to in_progress and execution to running after a successful run is
    # awkward; instead create worktree manually and flip status.
    from juicer import gitops
    from juicer.model import new_execution
    from juicer.state import write_json, utc_now

    branch = "juicer/TASK-001"
    wt = juicer.root / ".juicer" / "worktrees" / "TASK-001"
    gitops.create_worktree(juicer.root, branch, wt, new_branch=True)
    exe = new_execution("RUN-INT", "TASK-001",
                        workspace={"branch": branch, "base_commit": None,
                                   "worktree": str(wt)})
    write_json(juicer.executions_dir / "RUN-INT.json", exe)
    juicer._update_task(
        "TASK-001",
        lambda t: t.update(status="in_progress", current_execution_id="RUN-INT"))
    juicer._update_execution("RUN-INT", lambda e: e.update(
        status="running", started_at=utc_now()))

    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    task = fresh.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "worktree" in task["blocked_reason"]
    assert wt.exists()
    exe_doc = fresh.load_execution("RUN-INT")
    assert exe_doc["status"] == "cancelled"
    assert "interrupted" in exe_doc["failure"]["detail"]
    # explicit unblock
    fresh.retry_task("TASK-001")
    assert fresh.load_task("TASK-001")["status"] == "ready"
    history = fresh.load_task("TASK-001")["attempt_history"]
    assert history[-1]["from_status"] == "blocked"


def test_resume_aligns_finished_execution_with_task(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    from juicer import gitops
    from juicer.model import new_execution
    from juicer.state import write_json, utc_now

    branch = "juicer/TASK-001"
    wt = juicer.root / ".juicer" / "worktrees" / "TASK-001"
    gitops.create_worktree(juicer.root, branch, wt, new_branch=True)
    exe = new_execution("RUN-OK", "TASK-001",
                        workspace={"branch": branch, "base_commit": None,
                                   "worktree": str(wt)})
    write_json(juicer.executions_dir / "RUN-OK.json", exe)
    juicer._update_task(
        "TASK-001",
        lambda t: t.update(status="in_progress", current_execution_id="RUN-OK"))
    juicer._update_execution("RUN-OK", lambda e: e.update(
        status="running", started_at=utc_now()))
    # crash after the worker finished successfully, before task flipped
    juicer._update_execution("RUN-OK", lambda e: e.update(
        status="succeeded", finished_at=utc_now(), result={"ok": True}))

    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    assert fresh.load_task("TASK-001")["status"] == "completed"
    events = [e["type"] for e in fresh.events()]
    assert "resume_reconciled" in events


def test_retry_blocked_preserves_history(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._update_task("TASK-001", lambda t: t.update(
        status="blocked", blocked_reason="manual block for test"))
    doc = juicer.retry_task("TASK-001")
    assert doc["status"] == "ready"
    assert doc["blocked_reason"] is None
    assert doc["attempt_history"][-1]["from_status"] == "blocked"
    assert doc["attempt_history"][-1]["blocked_reason"] == "manual block for test"


def test_retry_rejects_done_and_ready(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    with pytest.raises(JuicerError):
        juicer.retry_task("TASK-001")  # ready
    juicer._executor = fake_ok_executor(write_files={"z.py": "Z=1\n"})
    juicer.run_task("TASK-001")
    juicer.integrate("TASK-001")
    assert juicer.load_task("TASK-001")["status"] == "done"
    with pytest.raises(JuicerError):
        juicer.retry_task("TASK-001")


def test_post_merge_failure_moves_task_to_blocked(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"f.py": "F=1\n"})
    juicer.run_task("TASK-001")
    original = juicer._run_task_checks

    def flaky(task, cwd, commit, phase="pre_merge"):
        results = original(task, cwd, commit, phase=phase)
        if phase == "post_merge":
            for r in results:
                r["status"] = "FAIL"
        return results

    juicer._run_task_checks = flaky
    from juicer.errors import GateBlockedError
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "post-merge" in task["blocked_reason"]


# ---------- CR-2: completed must not be a trap state ----------

def _spec_with_failing_check():
    """Task whose required check fails until the second attempt writes a
    marker file (the check runs inside the task worktree)."""
    spec = simple_task_specs("TASK-001")[0]
    spec["checks"] = [{
        "id": "needs-fix",
        "required": True,
        "command": [sys.executable, "-c",
                    "import os,sys; sys.exit(0 if os.path.exists('fixed.marker') else 1)"],
    }]
    # keep the criterion linked to the check this spec actually runs
    spec["acceptance_criteria"] = [
        {"id": "AC-1", "description": "works", "verification": "check:needs-fix"},
    ]
    return spec


def test_completed_gate_fail_has_legal_recovery_route(juicer):
    """CR-2: a pre-merge gate FAIL must not strand the task in completed.

    Legal route: completed -> blocked (with reason) -> retry -> ready ->
    re-run -> completed -> integrate.
    """
    from juicer.errors import GateBlockedError
    juicer.add_tasks([_spec_with_failing_check()])
    juicer._executor = fake_ok_executor(write_files={"a.py": "A=1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok  # executor succeeded; the failing check surfaces at integrate
    assert juicer.load_task("TASK-001")["status"] == "completed"

    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "FAIL"

    # the task is NOT trapped: it moved to blocked with an explicit reason
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert task.get("blocked_reason")

    # legal recovery: retry -> ready, re-run with the fix, then integrate
    juicer.retry_task("TASK-001")
    assert juicer.load_task("TASK-001")["status"] == "ready"
    juicer._executor = fake_ok_executor(
        write_files={"a.py": "A=2\n", "fixed.marker": "1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok, out.detail
    integration = juicer.integrate("TASK-001")
    assert integration["pre_merge_gate"]["status"] == "PASS"
    task = juicer.load_task("TASK-001")
    assert task["status"] == "done"
    # attempt history survived the recovery
    assert task["attempt_count"] >= 2
    assert len(task["attempt_history"]) >= 1


def test_review_fail_verdict_also_blocks_completed_task(juicer):
    """CR-2 applies to every FAIL gate, not only verification."""
    from juicer.errors import GateBlockedError
    spec = simple_task_specs("TASK-001")[0]
    spec["approval_policy"] = {"human_approval_required": False,
                               "required_gates": ["verification", "review"]}
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X=1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    task = juicer.load_task("TASK-001")
    result = task["result"]
    from juicer import gitops
    tree_hash = gitops.tree_hash(juicer.root, result["commit"])
    juicer.record_review(
        "TASK-001", result["execution_id"], result["commit"], tree_hash,
        ["feat.py"],
        [{"severity": "critical", "description": "hardcoded secret"}],
        "FAIL", "@reviewer")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "FAIL"
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "review" in task["blocked_reason"]
    # and it is retriable out of blocked
    juicer.retry_task("TASK-001")
    assert juicer.load_task("TASK-001")["status"] == "ready"


# ---------- M-1: resume -> integrate must not crash ----------

def test_resume_aligning_completed_copies_execution_result(juicer):
    """M-1: resume aligning in_progress -> completed must copy the
    execution result (commit/branch) into the task, so integrate can use it.
    """
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"a.py": "A=1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    task = juicer.load_task("TASK-001")
    commit = task["result"]["commit"]
    exec_id = task["current_execution_id"]

    # Simulate a crash right after the execution finished: the execution is
    # succeeded but the task was left in_progress with no result.
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["status"] = "in_progress"
    doc["result"] = {}
    path.write_text(json.dumps(doc), encoding="utf-8")

    report = juicer.resume()
    assert "TASK-001" in report["recovered"]
    task = juicer.load_task("TASK-001")
    assert task["status"] == "completed"
    # the result (commit/branch) was copied from the execution record
    assert task["result"].get("commit") == commit
    assert task["result"].get("branch") == "juicer/TASK-001"

    # resume -> integrate flows all the way to done without crashing
    integration = juicer.integrate("TASK-001")
    assert integration["pre_merge_gate"]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"
    assert exec_id  # sanity: execution existed before the crash


def test_integrate_without_commit_fails_cleanly(juicer):
    """M-1: completed without a commit/branch (e.g. lost result) must raise
    a clean GateBlockedError, not crash with AttributeError/TypeError."""
    from juicer.errors import GateBlockedError
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"a.py": "A=1\n"})
    assert juicer.run_task("TASK-001").ok

    # Corrupt the stored result (simulates the pre-M-1 resume bug output).
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["result"] = {"execution_id": doc["result"]["execution_id"]}
    path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "commit" in str(exc.value).lower()
