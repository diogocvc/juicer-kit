"""TASK-011: end-to-end V2 acceptance and negative-path proofs.

The deterministic tests drive the real core and the real OpenCode adapter
(`juicer/harness/opencode.py`) against a scripted V2 binary that speaks the
measured NDJSON protocol. They never call a model provider. The real binary
capability probe is opt-in in `tests/test_opencode_smoke.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import fake_ok_executor, git as run_git, simple_task_specs
from juicer import gitops
from juicer.errors import GateBlockedError
from juicer.model import new_execution
from juicer.state import utc_now, write_json

# A scripted OpenCode V2 CLI: discovery flags, NDJSON events and JSON evidence.
FAKE_V2 = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("opencode v2.2.7")
    sys.exit(0)
if args[:2] == ["run", "--help"]:
    print("""--standalone
--format choice (choices: default, json)
--agent string
--session string
--continue
--auto
""")
    sys.exit(0)
if args[:2] == ["serve", "--help"]:
    print("serve")
    sys.exit(0)

# Real V2 resolves the project from PWD. Require it and fail loudly if the
# adapter only sets the subprocess cwd, which would run in the caller's repo.
root = Path(os.environ["PWD"]).resolve()
if root != Path.cwd().resolve():
    sys.stderr.write("PWD=%s cwd=%s\n" % (root, Path.cwd().resolve()))
    sys.exit(2)

agent = ""
if "--agent" in args:
    agent = args[args.index("--agent") + 1]
message = args[args.index("--") + 1] if "--" in args else ""

if agent in ("reviewer", "security"):
    text = "```json\n" + json.dumps(
        {"verdict": "PASS", "findings": [],
         "summary": "%s evidence" % agent}) + "\n```"
    session = "ses_e2e_%s" % agent
else:
    task = "TASK-002" if "TASK-002" in message else "TASK-001"
    Path("e2e_feature.py").write_text("TASK = %r\n" % task, encoding="utf-8")
    text = "implemented %s" % task
    session = "ses_e2e_%s" % task

print(json.dumps({"type": "text", "sessionID": session,
                  "part": {"type": "text", "text": text}}))
'''


def install_fake_v2(tmp_path: Path, monkeypatch) -> Path:
    script = tmp_path / "opencode-v2"
    script.write_text(FAKE_V2, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("OPENCODE_BIN", str(script))
    return script


def backlog_block(task_id: str, title: str = "Imported task") -> str:
    return "\n".join([
        "### Task: [%s] %s" % (task_id, title),
        "",
        "**Description**: Imported from the Markdown backlog.",
        "",
        "**Priority**: P1-High",
        "",
        "**Status**: Pending",
        "",
        "**Dependencies**: None",
        "",
        "**Acceptance Criteria**:",
        "- [ ] imported criterion",
        "",
        "**Estimated Effort**: S",
        "",
    ])


def commit_passing_test(repo: Path) -> None:
    tests = repo / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_e2e_ok.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.juicer/\n", encoding="utf-8")
    run_git(["add", "-A"], repo)
    run_git(["commit", "-m", "baseline e2e test"], repo)


def fake_committing_executor(files):
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


def commit_tree(juicer, task_id):
    result = juicer.load_task(task_id)["result"]
    return result["commit"], gitops.tree_hash(juicer.root, result["commit"])


def test_full_v2_flow_import_run_review_security_approval_merge(juicer, repo, tmp_path, monkeypatch):
    install_fake_v2(tmp_path, monkeypatch)

    backlog = repo / "backlog" / "backlog.md"
    backlog.parent.mkdir(parents=True, exist_ok=True)
    backlog.write_text(backlog_block("TASK-001"), encoding="utf-8")
    commit_passing_test(repo)

    imported = juicer.import_backlog()
    assert imported["status"] == "imported"
    assert imported["task_ids"] == ["TASK-001"]

    spec = simple_task_specs("TASK-002", deps={"TASK-002": ["TASK-001"]})[0]
    spec["scope"] = {"paths": ["e2e_feature.py"], "constraints": []}
    spec["approval_policy"] = {
        "human_approval_required": True,
        "required_gates": ["verification", "review", "security", "approval"],
        "risk_level": "high",
    }
    juicer.add_tasks([spec])

    # Imported task: run through the real adapter, then human approval.
    first = juicer.run_task("TASK-001")
    assert first.ok, first.detail
    assert first.data["session_id"] == "ses_e2e_TASK-001"
    assert "e2e_feature.py" in first.data["changed_files"]
    assert juicer.load_task("TASK-001")["status"] == "completed"
    assert not gitops.is_dirty(repo, exclude=(".juicer",)), gitops.status_porcelain(repo)
    juicer.approve("TASK-001", approver="alice")
    first_integration = juicer.integrate("TASK-001", approve=True)
    assert first_integration["pre_merge_gate"]["status"] == "PASS"
    assert first_integration["post_merge_gate"]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"
    assert (repo / "e2e_feature.py").read_text(encoding="utf-8").strip() == "TASK = 'TASK-001'"

    # Gated task: run, trigger reviewer/security through the core, approve.
    second = juicer.run_task("TASK-002")
    assert second.ok, second.detail
    assert "e2e_feature.py" in second.data["changed_files"]

    review = juicer.run_review("TASK-002")
    security = juicer.run_security("TASK-002")
    assert review["verdict"] == "PASS"
    assert security["verdict"] == "PASS"
    assert review["commit"] == second.data["commit"]
    assert security["commit"] == second.data["commit"]

    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-002")
    assert "human approval" in str(exc.value).lower()
    assert juicer.load_task("TASK-002")["status"] == "completed"

    assert not gitops.is_dirty(repo, exclude=(".juicer",)), gitops.status_porcelain(repo)
    juicer.approve("TASK-002", approver="bob")
    second_integration = juicer.integrate("TASK-002", approve=True)
    assert second_integration["pre_merge_gate"]["status"] == "PASS"
    assert second_integration["post_merge_gate"]["status"] == "PASS"
    assert juicer.load_task("TASK-002")["status"] == "done"
    assert (repo / "e2e_feature.py").read_text(encoding="utf-8").strip() == "TASK = 'TASK-002'"

    status = juicer.status()
    assert status["mission"]["status"] == "ready"
    assert status["next_action"] == "all tasks done; mission complete"


def test_missing_review_security_and_approval_block_merge(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["approval_policy"] = {
        "human_approval_required": True,
        "required_gates": ["verification", "review", "security", "approval"],
        "risk_level": "high",
    }
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feature.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok

    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "review" in str(exc.value).lower()
    assert exc.value.gate_status in ("BLOCKED", "NOT RUN")

    commit, tree_hash = commit_tree(juicer, "TASK-001")
    result = juicer.load_task("TASK-001")["result"]
    juicer.record_review("TASK-001", result["execution_id"], commit, tree_hash,
                         result["changed_files"], [], "PASS", "@reviewer")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "security" in str(exc.value).lower()
    assert exc.value.gate_status in ("BLOCKED", "NOT RUN")

    juicer.record_security("TASK-001", result["execution_id"], commit, tree_hash,
                           result["changed_files"], [], "PASS", "@security")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "human approval" in str(exc.value).lower()
    assert exc.value.gate_status == "BLOCKED"

    juicer.approve("TASK-001", approver="alice")
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["pre_merge_gate"]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_missing_verification_gate_blocks_merge(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["checks"] = [{
        "id": "optional-only",
        "command": [sys.executable, "-c", "print('optional')"],
        "required": False,
    }]
    spec["acceptance_criteria"] = []
    spec["approval_policy"] = {
        "human_approval_required": False,
        "required_gates": ["verification"],
    }
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"feature.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok

    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "verification gate" in str(exc.value).lower()
    assert exc.value.gate_status == "NOT RUN"
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_out_of_scope_change_blocks_task(juicer):
    spec = simple_task_specs("TASK-001")[0]
    spec["scope"] = {"paths": ["allowed/"], "constraints": []}
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files={"outside.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "outside scope" in out.detail
    assert juicer.load_task("TASK-001")["status"] == "failed"


def test_agent_commit_blocks_task(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_committing_executor({"feature.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "agent created commit" in out.detail
    task = juicer.load_task("TASK-001")
    assert task["status"] == "failed"
    assert task["result"]["agent_committed"] is True
    assert task["result"]["commit"] is None


def test_protected_path_blocks_task(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={".juicer/leak.json": "{}\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    assert "protected" in out.detail.lower()
    task = juicer.load_task("TASK-001")
    assert task["status"] == "failed"
    assert task["result"]["commit"] is None
    # The worktree may still contain the rejected file as evidence, but the
    # blocked change must never reach a commit or the integration checkout.
    assert not (juicer.root / ".juicer" / "leak.json").exists()
    execution = juicer.load_execution(task["current_execution_id"])
    worktree = Path(execution["workspace"]["worktree"])
    assert gitops.head_commit(worktree) == task["result"]["base_commit"]


def test_post_merge_failure_never_reaches_done(juicer):
    specs = simple_task_specs("TASK-001")
    specs[0]["checks"].append({
        "id": "only-after-merge",
        "command": [
            sys.executable, "-c",
            "import pathlib,sys; "
            "sys.exit(1 if pathlib.Path('only-after-merge').exists() else 0)",
        ],
        "required": True,
    })
    juicer.add_tasks(specs)
    juicer._executor = fake_ok_executor(write_files={"merged.py": "M = 1\n"})
    assert juicer.run_task("TASK-001").ok

    original = juicer._run_task_checks
    calls = {"post": 0}

    def fail_after_merge(task, cwd, commit, phase="pre_merge"):
        if phase == "post_merge":
            calls["post"] += 1
            if calls["post"] == 1:
                (Path(cwd) / "only-after-merge").write_text("fail\n", encoding="utf-8")
        return original(task, cwd, commit, phase=phase)

    juicer._run_task_checks = fail_after_merge
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"
    assert task["status"] not in ("completed", "done")
    assert task["result"]["merged_commit"] == gitops.head_commit(juicer.root)
    assert "integration_post_failed" in [e["type"] for e in juicer.events()]


def test_retry_and_resume_preserve_evidence(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_write_then_fail({"partial.py": "P = 1\n"})
    assert juicer.run_task("TASK-001").ok is False
    first = juicer.load_task("TASK-001")
    first_exec = first["current_execution_id"]
    first_evidence = Path(first["result"]["evidence_ref"])
    assert first_evidence.exists() and first_evidence.read_text(encoding="utf-8")

    juicer.retry_task("TASK-001")
    juicer._executor = fake_ok_executor(write_files={"fixed.py": "F = 1\n"})
    assert juicer.run_task("TASK-001").ok is True
    second = juicer.load_task("TASK-001")
    assert second["result"]["attempt"] == 2
    assert second["result"]["execution_id"] != first_exec
    assert juicer.load_execution(first_exec)["status"] == "failed"
    assert first_evidence.exists()
    preserved = list((juicer.evidence_dir / "TASK-001").glob("preserved-*.json"))
    assert preserved
    record = json.loads(preserved[0].read_text(encoding="utf-8"))
    assert record["diff_ref"] and Path(record["diff_ref"]).exists()
    assert "partial.py" in Path(record["diff_ref"]).read_text(encoding="utf-8")

    # Interrupted worker: state is `running`/`in_progress`; resume reconciles
    # and preserves the worktree plus a report artifact.
    juicer.add_tasks(simple_task_specs("TASK-002"))
    branch = "juicer/TASK-002"
    worktree = juicer.root / ".juicer" / "worktrees" / "TASK-002"
    gitops.create_worktree(juicer.root, branch, worktree, new_branch=True)
    (worktree / "wip.py").write_text("WIP = 1\n", encoding="utf-8")
    execution = new_execution("RUN-E2E-INTERRUPTED", "TASK-002",
                              workspace={"branch": branch, "base_commit": None,
                                         "worktree": str(worktree)})
    write_json(juicer.executions_dir / "RUN-E2E-INTERRUPTED.json", execution)
    juicer._update_task("TASK-002", lambda t: t.update(
        status="in_progress", current_execution_id="RUN-E2E-INTERRUPTED"))
    juicer._update_execution("RUN-E2E-INTERRUPTED", lambda e: e.update(
        status="running", started_at=utc_now()))

    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert "TASK-002" in report["recovered"]
    task = fresh.load_task("TASK-002")
    assert task["status"] == "blocked"
    assert worktree.exists()
    assert Path(report["artifact_ref"]).exists()
    assert fresh.load_execution("RUN-E2E-INTERRUPTED")["status"] == "cancelled"

    fresh.retry_task("TASK-002")
    fresh._executor = fake_ok_executor(write_files={"resumed.py": "R = 1\n"})
    assert fresh.run_task("TASK-002").ok
    fresh.integrate("TASK-002")
    assert fresh.load_task("TASK-002")["status"] == "done"
