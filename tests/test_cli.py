"""CLI surface smoke tests (no real OpenCode execution)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "juicer"


def run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(BIN)] + args,
        cwd=str(cwd), capture_output=True, text=True,
    )


def test_cli_init_mission_status_cycle(repo):
    proc = run_cli(["init"], repo)
    assert proc.returncode == 0, proc.stderr
    proc = run_cli([
        "mission", "--title", "M", "--objective", "O",
        "--criterion", "c1 passes",
    ], repo)
    assert proc.returncode == 0, proc.stderr
    proc = run_cli(["status", "--json"], repo)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["mission"]["status"] == "ready"
    assert "juicer mission" not in data["next_action"]


def test_cli_gap_flow(repo):
    run_cli(["init"], repo)
    run_cli(["mission", "--title", "M", "--objective", "O", "--gap", "Which host?"], repo)
    proc = run_cli(["status"], repo)
    assert "GAP-001" in proc.stdout or "human" in proc.stdout
    proc = run_cli(["gap", "GAP-001", "--answer", "localhost"], repo)
    assert proc.returncode == 0, proc.stderr
    proc = run_cli(["status", "--json"], repo)
    assert json.loads(proc.stdout)["mission"]["status"] == "ready"


def test_cli_discover_reports_capabilities(repo):
    proc = run_cli(["discover"], repo)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["harness"] == "opencode"
    assert data["status"] in ("supported", "degraded", "unsupported")


def test_cli_error_exit_code(repo):
    run_cli(["init"], repo)
    proc = run_cli(["status"], repo)  # no mission yet — status still works
    assert proc.returncode == 0
    proc = run_cli(["run", "TASK-001"], repo)
    assert proc.returncode == 2
    assert "error:" in proc.stderr


def _ready_repo_with_task(repo):
    """init + mission + one task, ready for CLI subcommand flows."""
    run_cli(["init"], repo)
    run_cli(["mission", "--title", "M", "--objective", "O"], repo)
    (repo / "tasks.json").write_text(json.dumps([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [],
    }]), encoding="utf-8")
    proc = run_cli(["decompose", str(repo / "tasks.json")], repo)
    assert proc.returncode == 0, proc.stderr


def test_cli_review_records_artifact_with_findings(repo):
    _ready_repo_with_task(repo)
    proc = run_cli([
        "review", "TASK-001",
        "--commit", "abc123", "--tree-hash", "tree456",
        "--execution-id", "RUN-001",
        "--scope", "src/a.py",
        "--finding", "medium:minor nit:src/a.py",
        "--finding", "low:docs outdated",
    ], repo)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["verdict"] == "PASS"
    assert data["commit"] == "abc123"
    artifact = json.loads(
        (repo / ".juicer" / "evidence" / "TASK-001" / "review-abc123.json")
        .read_text(encoding="utf-8"))
    assert artifact["agent"] == "@reviewer"
    assert len(artifact["findings"]) == 2
    assert artifact["findings"][0]["severity"] == "medium"
    assert artifact["findings"][0]["file"] == "src/a.py"
    assert artifact["findings"][1]["severity"] == "low"


def test_cli_security_records_artifact(repo):
    _ready_repo_with_task(repo)
    proc = run_cli([
        "security", "TASK-001",
        "--commit", "abc123", "--tree-hash", "tree456",
        "--finding", "high:sql injection:src/db.py",
    ], repo)
    assert proc.returncode == 0, proc.stderr
    artifact = json.loads(
        (repo / ".juicer" / "evidence" / "TASK-001" / "security-abc123.json")
        .read_text(encoding="utf-8"))
    assert artifact["agent"] == "@security"
    assert artifact["findings"][0]["severity"] == "high"


def test_cli_review_pass_overwriting_fail_requires_force(repo):
    """M-4 through the CLI: PASS over a recorded FAIL fails cleanly (exit 2)
    until --force is given explicitly."""
    _ready_repo_with_task(repo)
    fail = run_cli([
        "review", "TASK-001", "--commit", "abc123", "--tree-hash", "tree456",
        "--verdict", "FAIL", "--finding", "critical:hardcoded secret",
    ], repo)
    assert fail.returncode == 0, fail.stderr
    blocked = run_cli([
        "review", "TASK-001", "--commit", "abc123", "--tree-hash", "tree456",
        "--verdict", "PASS",
    ], repo)
    assert blocked.returncode == 2
    assert "FAIL" in blocked.stderr
    # verdict preserved
    artifact = json.loads(
        (repo / ".juicer" / "evidence" / "TASK-001" / "review-abc123.json")
        .read_text(encoding="utf-8"))
    assert artifact["verdict"] == "FAIL"
    forced = run_cli([
        "review", "TASK-001", "--commit", "abc123", "--tree-hash", "tree456",
        "--verdict", "PASS", "--force",
    ], repo)
    assert forced.returncode == 0, forced.stderr
    artifact = json.loads(
        (repo / ".juicer" / "evidence" / "TASK-001" / "review-abc123.json")
        .read_text(encoding="utf-8"))
    assert artifact["verdict"] == "PASS"


def test_cli_retry_reports_illegal_status_cleanly(repo):
    _ready_repo_with_task(repo)
    # a ready task cannot be retried: clean error exit, no traceback
    proc = run_cli(["retry", "TASK-001"], repo)
    assert proc.returncode == 2
    assert "error:" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_cli_integrate_refuses_non_completed_task(repo):
    _ready_repo_with_task(repo)
    proc = run_cli(["integrate", "TASK-001"], repo)
    assert proc.returncode == 2
    assert "error:" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_cli_review_run_wires_to_core(repo, monkeypatch, capsys):
    from juicer import cli
    calls = {}

    def fake_run_review(self, task, timeout=900, force=False):
        calls.update(task=task, timeout=timeout, force=force)
        return {"verdict": "PASS", "artifact_ref": "artifact.json"}

    monkeypatch.setattr(cli.Juicer, "run_review", fake_run_review)
    rc = cli.main(["--root", str(repo), "review-run", "TASK-001",
                   "--timeout", "42", "--force"])
    assert rc == 0
    assert calls == {"task": "TASK-001", "timeout": 42, "force": True}
    assert json.loads(capsys.readouterr().out)["verdict"] == "PASS"


def test_cli_security_run_wires_to_core(repo, monkeypatch, capsys):
    from juicer import cli
    calls = {}

    def fake_run_security(self, task, timeout=900, force=False):
        calls.update(task=task, timeout=timeout, force=force)
        return {"verdict": "PASS"}

    monkeypatch.setattr(cli.Juicer, "run_security", fake_run_security)
    rc = cli.main(["--root", str(repo), "security-run", "TASK-001"])
    assert rc == 0
    assert calls == {"task": "TASK-001", "timeout": 900, "force": False}


def test_cli_review_run_error_is_clean(repo, monkeypatch, capsys):
    from juicer import cli
    from juicer.evidence import EvidenceError

    def fake_run_review(self, task, timeout=900, force=False):
        raise EvidenceError("agent output is not structured evidence")

    monkeypatch.setattr(cli.Juicer, "run_review", fake_run_review)
    rc = cli.main(["--root", str(repo), "review-run", "TASK-001"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "Traceback" not in captured.err
