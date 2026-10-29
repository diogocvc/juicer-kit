"""Integration: explicit merge, post-merge checks, done state, human gate."""

import json

import pytest

from juicer import gitops
from juicer.errors import GateBlockedError
from conftest import fake_ok_executor, simple_task_specs


def ready_completed_task(juicer, files=None, approval=None):
    spec = simple_task_specs("TASK-001")[0]
    if approval is not None:
        spec["approval_policy"] = approval
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files=files or {"new_feature.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    return out


def test_integration_merges_and_runs_post_merge_checks(juicer):
    ready_completed_task(juicer)
    integration = juicer.integrate("TASK-001")
    assert integration["pre_merge_gate"]["status"] == "PASS"
    assert integration["post_merge_gate"]["status"] == "PASS"
    assert integration["merged_commit"] == gitops.head_commit(juicer.root)
    task = juicer.load_task("TASK-001")
    assert task["status"] == "done"
    # the feature is actually on main now
    assert (juicer.root / "new_feature.py").exists()
    # post-merge check results recorded with phase marker and integrated commit
    store = juicer.checks_dir / "TASK-001.results.jsonl"
    results = [json.loads(l) for l in store.read_text(encoding="utf-8").splitlines() if l.strip()]
    post = [r for r in results if r["phase"] == "post_merge"]
    assert post and all(r["commit"] == integration["merged_commit"] for r in post)


def test_post_merge_failure_blocks_done_and_records(juicer):
    ready_completed_task(juicer)
    # after merge the repo tests will fail: make the required check fail on main
    calls = {"n": 0}
    original = juicer._run_task_checks

    def flaky(task, cwd, commit, phase="pre_merge"):
        results = original(task, cwd, commit, phase=phase)
        if phase == "post_merge":
            for r in results:
                r["status"] = "FAIL"
        return results

    juicer._run_task_checks = flaky
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "post-merge" in str(exc.value)
    # merge itself happened; done is withheld and the task is blocked
    assert (juicer.root / "new_feature.py").exists()
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "post-merge" in task.get("blocked_reason", "")
    events = [e["type"] for e in juicer.events()]
    assert "integration_post_failed" in events


def test_human_gate_is_separate_from_technical_gate(juicer):
    ready_completed_task(juicer, approval={"human_approval_required": True,
                                           "required_gates": ["verification"]})
    # technical gate would pass, but human approval is missing
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "human approval" in str(exc.value)
    assert juicer.load_task("TASK-001")["status"] == "completed"
    # explicit approval completes the flow
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["approved"] is True
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_cannot_integrate_uncompleted_task(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")


def test_dependency_chain_end_to_end(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002", deps={"TASK-002": ["TASK-001"]}))
    juicer._executor = fake_ok_executor(write_files={"step1.py": "A = 1\n"})
    assert juicer.run_task("TASK-002").ok is False  # not eligible yet
    assert juicer.run_task("TASK-001").ok is True
    juicer.integrate("TASK-001")
    # after TASK-001 is done, TASK-002 becomes eligible
    juicer._executor = fake_ok_executor(write_files={"step2.py": "B = 2\n"})
    assert juicer.run_task("TASK-002").ok is True
    juicer.integrate("TASK-002")
    assert juicer.load_task("TASK-002")["status"] == "done"
    st = juicer.status()
    assert st["next_action"] == "all tasks done; mission complete"


# ---------- multi-gate tests ----------

def _commit_tree(juicer, task_id):
    task = juicer.load_task(task_id)
    result = task.get("result") or {}
    commit = result.get("commit")
    tree_hash = gitops.tree_hash(juicer.root, commit)
    return commit, tree_hash


def _spec_with_gates(tid, required_gates, risk_level=None):
    spec = simple_task_specs(tid)[0]
    spec["approval_policy"] = {
        "human_approval_required": False,
        "required_gates": required_gates,
    }
    if risk_level:
        spec["approval_policy"]["risk_level"] = risk_level
    return spec


def test_review_gate_required_blocks_without_artifact(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "review"])
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "review" in str(exc.value).lower()
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_review_gate_passes_with_valid_artifact(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "review"])
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    juicer.record_review(
        "TASK-001", out.data["execution_id"], commit, tree_hash,
        ["feat.py"], [], "PASS", "@reviewer")
    integration = juicer.integrate("TASK-001")
    assert integration["pre_merge_gate"]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_security_gate_required_blocks_without_artifact(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "security"], risk_level="high")
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"auth.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "security" in str(exc.value).lower()
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_security_gate_passes_with_valid_artifact(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "security"], risk_level="high")
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"auth.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    juicer.record_security(
        "TASK-001", out.data["execution_id"], commit, tree_hash,
        ["auth.py"], [], "PASS", "@security")
    integration = juicer.integrate("TASK-001")
    assert integration["pre_merge_gate"]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_review_critical_finding_is_fail(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "review"])
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    juicer.record_review(
        "TASK-001", out.data["execution_id"], commit, tree_hash,
        ["feat.py"],
        [{"severity": "critical", "description": "hardcoded secret", "file": "feat.py"}],
        "FAIL", "@reviewer")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "review" in str(exc.value).lower()
    # CR-2: a FAIL verdict moves the task out of `completed` into `blocked`
    # so it never becomes a trap state; the reason is recorded for rework.
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert "review" in task["blocked_reason"]


def test_malformed_review_artifact_is_blocked(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "review"])
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    # write a malformed artifact directly
    ev_dir = juicer.evidence_dir / "TASK-001"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / ("review-%s.json" % commit)).write_text("{not valid json", encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "review" in str(exc.value).lower()
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_stale_review_artifact_is_not_run(juicer):
    spec = _spec_with_gates("TASK-001", ["verification", "review"])
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok
    commit, tree_hash = _commit_tree(juicer, "TASK-001")
    # review artifact linked to a different commit
    juicer.record_review(
        "TASK-001", out.data["execution_id"], "old_commit", "old_tree",
        ["feat.py"], [], "PASS", "@reviewer")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert juicer.load_task("TASK-001")["status"] == "completed"
