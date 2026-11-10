"""TASK-007: isolation, full-diff scope, protected paths, agent commits.

Covers plan §8 and decision D8: harness permissions are an additional barrier,
never a substitute for the core's scope/protected/gate checks.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import fake_ok_executor, git as run_git, simple_task_specs
from juicer import gitops
from juicer.errors import GateBlockedError, ValidationError
from juicer.state import write_json


# ---------- executors ----------

def fake_committing_executor(files):
    """Write files and create a commit inside the worktree (agent misbehavior)."""
    def run(prompt, cwd, agent, timeout):
        for rel, content in (files or {}).items():
            path = Path(cwd) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        run_git(["add", "-A"], cwd)
        run_git(["commit", "-m", "agent commit"], cwd)
        return {"ok": True, "status": "PASS", "exit_code": 0, "detail": "ok",
                "session_id": "ses_agent", "output": "done"}
    return run


def fake_write_then_fail(files, detail="boom"):
    def run(prompt, cwd, agent, timeout):
        for rel, content in (files or {}).items():
            path = Path(cwd) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return {"ok": False, "status": "FAIL", "exit_code": 1, "detail": detail,
                "session_id": "ses_fail", "output": detail}
    return run


def timed_executor(intervals, delay=0.15):
    lock = __import__("threading").Lock()

    def run(prompt, cwd, agent, timeout):
        started = time.monotonic()
        time.sleep(delay)
        marker = "m-%s.txt" % ("1" if "TASK-001" in prompt else "2")
        (Path(cwd) / marker).write_text("x\n", encoding="utf-8")
        with lock:
            intervals.append((started, time.monotonic()))
        return {"ok": True, "status": "PASS", "exit_code": 0, "detail": "ok",
                "session_id": "ses_x", "output": "done"}
    return run


# ---------- AC1: execution metadata ----------

def test_execution_records_base_head_tree_and_branch(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    result = juicer.load_task("TASK-001")["result"]
    assert result["base_commit"]
    assert result["head_commit"] == result["commit"]
    assert result["tree_hash"] == gitops.tree_hash(juicer.root, result["commit"])
    assert result["branch"] == "juicer/TASK-001"
    execution = juicer.load_execution(result["execution_id"])
    ws = execution["workspace"]
    assert ws["base_commit"] == result["base_commit"]
    assert ws["head_commit"] == result["head_commit"]
    assert ws["tree_hash"] == result["tree_hash"]
    assert ws["branch"] == result["branch"]


# ---------- AC2: full diff scope ----------

def test_scope_covers_untracked_files(juicer):
    juicer.add_tasks([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [],
        "scope": {"paths": ["docs/**"], "constraints": []},
    }])
    juicer._executor = fake_ok_executor(write_files={"outside.py": "x = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "outside scope" in str(juicer.load_task("TASK-001")["result"])


def test_scope_covers_committed_changes(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["allow_agent_commits"] = True
    spec["scope"] = {"paths": ["docs/**"], "constraints": []}
    juicer.add_tasks([spec])
    juicer._executor = fake_committing_executor({"outside.py": "x = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "outside scope" in str(juicer.load_task("TASK-001")["result"])


# ---------- AC3: protected paths in the core ----------

@pytest.mark.parametrize("path", [
    ".juicer/leak.json",
    ".env",
    "certs/server.pem",
    "keys/id_rsa",
    "app/credentials.p12",
    "home/me/.aws/credentials",
])
def test_protected_paths_are_blocked(juicer, path):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={path: "secret\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in str(juicer.load_task("TASK-001")["result"]).lower()
    # never merged
    assert not (juicer.root / path).exists()


def test_git_internal_path_is_protected_in_policy():
    from juicer.errors import ScopeViolationError
    from juicer.scope import check_protected
    with pytest.raises(ScopeViolationError):
        check_protected({"id": "TASK-001"}, [".git/config"])


def test_env_example_is_a_safe_template(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={".env.example": "KEY=\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is True


def test_policy_declared_protected_path_is_blocked(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["scope"] = {"paths": [], "constraints": [],
                     "protected_paths": ["config/prod/**"]}
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"config/prod/db.yml": "x\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in str(juicer.load_task("TASK-001")["result"]).lower()


# ---------- AC4: agent commits ----------

def test_agent_commit_fails_by_default(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_committing_executor({"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "agent created commit" in out.detail
    task = juicer.load_task("TASK-001")
    assert task["status"] == "failed"
    result = task["result"]
    assert result["agent_committed"] is True
    assert result["agent_head_commit"] != result["base_commit"]
    assert result["commit"] is None


def test_agent_commit_allowed_by_explicit_policy(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["allow_agent_commits"] = True
    spec["scope"] = {"paths": ["feat.py"], "constraints": []}
    juicer.add_tasks([spec])
    juicer._executor = fake_committing_executor({"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is True
    result = juicer.load_task("TASK-001")["result"]
    assert result["commit"]
    assert result["agent_committed"] is True
    assert result["commit"] == result["agent_head_commit"]


# ---------- AC5: dirty target ----------

def test_dirty_target_blocks_integration_without_overwrite(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    (juicer.root / "user_work.py").write_text("precious = True\n", encoding="utf-8")
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")
    assert (juicer.root / "user_work.py").read_text(encoding="utf-8") == "precious = True\n"
    assert not (juicer.root / "feat.py").exists()


# ---------- AC6: evidence before removal ----------

def test_prior_attempt_is_preserved_before_retry(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_write_then_fail({"partial.py": "P = 1\n"})
    assert juicer.run_task("TASK-001").ok is False
    juicer.retry_task("TASK-001")
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok is True

    records = sorted((juicer.evidence_dir / "TASK-001").glob("preserved-*.json"))
    assert records, "the previous attempt must be preserved before removal"
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in records]
    assert any(d.get("type") == "preserved_attempt" and d.get("dirty") for d in docs)
    assert any("partial.py" in d.get("changed_files", []) for d in docs)
    assert any(d.get("branch_tip") for d in docs)
    assert any(d.get("preserved_ref") for d in docs)
    # the patch is real evidence, not just a filename list
    patches = [Path(d["diff_ref"]).read_text(encoding="utf-8")
               for d in docs if d.get("diff_ref")]
    assert patches and any("partial.py" in text for text in patches)
    assert "attempt_preserved" in [e["type"] for e in juicer.events()]


# ---------- AC7: serial by default ----------

def test_default_concurrency_is_serial(juicer):
    assert juicer.config()["max_jobs"] == 1
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002"))
    intervals = []
    juicer._executor = timed_executor(intervals, delay=0.15)
    outcomes = juicer.run_eligible()  # no max_jobs override
    assert all(o.ok for o in outcomes)
    assert len(intervals) == 2
    intervals.sort()
    # no overlap: the second run starts only after the first ends
    assert intervals[1][0] >= intervals[0][1] - 0.05


# ---------- AC8: V2 permissions are not evidence ----------

def _allow_all_permissions(juicer):
    cfg = juicer.config()
    cfg["permissions"] = [{"permission": "*", "action": "allow"}]
    write_json(juicer.config_path, cfg)


def test_harness_permissions_do_not_bypass_protected_paths(juicer):
    _allow_all_permissions(juicer)
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={".env": "SECRET=1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in str(juicer.load_task("TASK-001")["result"]).lower()


def test_harness_permissions_do_not_satisfy_review_gate(juicer):
    _allow_all_permissions(juicer)
    spec = simple_task_specs("TASK-001")[0]
    spec["approval_policy"] = {
        "human_approval_required": False,
        "required_gates": ["verification", "review"],
    }
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")


# ---------- deferred suggestions from TASK-006 ----------

def test_unknown_required_gate_is_rejected_at_import(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["approval_policy"] = {
        "human_approval_required": False,
        "required_gates": ["verification", "does-not-exist"],
    }
    with pytest.raises(ValidationError) as exc:
        juicer.add_tasks([spec])
    assert "unknown required_gates" in str(exc.value)


def test_branch_moved_after_evidence_blocks_integration(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    # move the branch tip to an unevidenced commit
    wt = juicer.root / ".juicer" / "worktrees" / "TASK-001"
    (wt / "unapproved.py").write_text("Y = 1\n", encoding="utf-8")
    run_git(["add", "-A"], wt)
    run_git(["commit", "-m", "unapproved commit"], wt)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "evidenced commit" in str(exc.value)
    assert juicer.load_task("TASK-001")["status"] == "completed"
    assert not (juicer.root / "unapproved.py").exists()


# ---------- review follow-ups: history, renames, scope exactness ----------

def fake_sequence_executor(steps):
    """Run side effects inside the worktree, then report success."""
    def run(prompt, cwd, agent, timeout):
        for step in steps:
            step(Path(cwd))
        return {"ok": True, "status": "PASS", "exit_code": 0, "detail": "ok",
                "session_id": "ses_seq", "output": "done"}
    return run


def _agent_commits_spec(scope_paths=None):
    spec = simple_task_specs("TASK-001")[0]
    spec["allow_agent_commits"] = True
    if scope_paths is not None:
        spec["scope"] = {"paths": scope_paths, "constraints": []}
    return spec


def test_protected_file_added_then_deleted_in_history_blocks(juicer):
    juicer.add_tasks([_agent_commits_spec(["feat.py"])])

    def add_then_hide(root):
        (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
        run_git(["add", "-A"], root)
        run_git(["commit", "-m", "add secret"], root)
        (root / ".env").unlink()
        run_git(["add", "-A"], root)
        run_git(["commit", "-m", "hide secret"], root)
        (root / "feat.py").write_text("X = 1\n", encoding="utf-8")

    juicer._executor = fake_sequence_executor([add_then_hide])
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in out.detail.lower()
    # the merge would still bring the secret commit: never integrate
    assert juicer.load_task("TASK-001")["status"] == "failed"


def test_rename_of_protected_file_blocks(juicer):
    juicer.add_tasks([_agent_commits_spec(["notes.txt"])])

    def add_then_rename(root):
        (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
        run_git(["add", "-A"], root)
        run_git(["commit", "-m", "add secret"], root)
        run_git(["mv", ".env", "notes.txt"], root)
        run_git(["commit", "-m", "rename secret"], root)

    juicer._executor = fake_sequence_executor([add_then_rename])
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in out.detail.lower()


def test_scope_exact_name_does_not_allow_same_basename_elsewhere(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["scope"] = {"paths": ["app.py"], "constraints": []}
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"nested/app.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "outside scope" in out.detail


def test_env_example_under_protected_policy_dir_blocks(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["scope"] = {"paths": [], "constraints": [],
                     "protected_paths": ["config/prod/**"]}
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(
        write_files={"config/prod/.env.example": "KEY=\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in out.detail.lower()


def test_integration_blocks_without_base_commit(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["result"].pop("base_commit", None)
    write_json(path, doc)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"
    assert "base_commit" in str(exc.value)


def test_integration_blocks_with_invalid_base_commit(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["result"]["base_commit"] = "deadbeef" * 5
    write_json(path, doc)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"


def test_integration_blocks_when_base_equals_commit(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["result"]["base_commit"] = doc["result"]["commit"]
    write_json(path, doc)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"


def test_failed_protected_write_leaves_no_commit(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={".env": "SECRET=1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    result = juicer.load_task("TASK-001")["result"]
    assert result["commit"] is None
    # the rejected content never became a commit on the task branch
    assert gitops.branch_tip(juicer.root, "juicer/TASK-001") == result["base_commit"]


def test_no_change_run_is_recorded_explicitly(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor()
    out = juicer.run_task("TASK-001")
    assert out.ok is True
    result = juicer.load_task("TASK-001")["result"]
    assert result["no_changes"] is True
    assert result["commit"] == result["base_commit"]
    assert result["touched_files"] == []


def test_tampered_no_changes_flag_blocks_integration(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["result"]["no_changes"] = True
    doc["result"]["base_commit"] = doc["result"]["commit"]
    write_json(path, doc)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"


def test_stale_worktree_fails_cleanly(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    wt = juicer.root / ".juicer" / "worktrees" / "TASK-001"
    wt.mkdir(parents=True)
    (wt / "stale.txt").write_text("stale\n", encoding="utf-8")
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "worktree setup failed" in out.detail
    task = juicer.load_task("TASK-001")
    assert task["status"] == "failed"
    execution = juicer.load_execution(task["current_execution_id"])
    assert execution["status"] == "failed"


def test_unknown_gate_in_tampered_task_blocks_integration(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    path = juicer.tasks_dir / "TASK-001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["approval_policy"] = {"human_approval_required": False,
                              "required_gates": ["verification", "bogus"]}
    write_json(path, doc)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "unknown required_gates" in str(exc.value)


def test_agent_destroyed_worktree_fails_closed(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))

    def destroy(root):
        gitfile = root / ".git"
        if gitfile.is_file() or gitfile.is_symlink():
            gitfile.unlink()

    juicer._executor = fake_sequence_executor([destroy])
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "worktree" in out.detail.lower()
    assert juicer.load_task("TASK-001")["status"] == "failed"

