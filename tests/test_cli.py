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
    assert data["status"] in ("supported", "unsupported")


def test_cli_error_exit_code(repo):
    run_cli(["init"], repo)
    proc = run_cli(["status"], repo)  # no mission yet — status still works
    assert proc.returncode == 0
    proc = run_cli(["run", "TASK-001"], repo)
    assert proc.returncode == 2
    assert "error:" in proc.stderr
