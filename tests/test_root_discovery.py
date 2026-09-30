"""Workspace root discovery (BUG-04): cwd never creates a second workspace."""

import json
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def test_status_works_from_subdirectory(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Objective").returncode == 0
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)

    r = run(nested, "status")
    assert r.returncode == 0, r.stderr
    shown = json.loads(r.stdout.split("\navailable:")[0])
    assert shown["status"] == "planning"
    assert not (nested / ".juicer").exists()


def test_gate_commands_require_initialized_workspace(tmp_path):
    for args in (("status",), ("approve",), ("mission", "x"),
                 ("sync", "all"), ("start", "U"), ("finish",)):
        r = run(tmp_path, *args)
        assert r.returncode == 1, args
        assert "juicer init" in r.stderr, args
        assert not (tmp_path / ".juicer").exists(), args


def test_required_command_error_from_subdirectory(tmp_path):
    (tmp_path / "sub").mkdir()
    r = run(tmp_path / "sub", "ship-approve", "--by=test")
    assert r.returncode == 1
    assert "juicer init" in r.stderr
    assert not (tmp_path / "sub" / ".juicer").exists()
    assert not (tmp_path / ".juicer").exists()


def test_workspace_optional_commands_work_without_workspace(tmp_path):
    r = run(tmp_path, "adapters")
    assert r.returncode == 0, r.stderr
    assert "opencode" in r.stdout

    r = run(tmp_path, "worker", "reviewer")
    assert r.returncode == 0, r.stderr
    assert "Worker contract:" in r.stdout

    r = run(tmp_path, "capabilities", "nonexistent")
    assert r.returncode == 1
    assert "Unknown adapter" in r.stderr
    assert "juicer init" not in r.stderr


def test_init_initializes_current_directory_only(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    r = run(sub, "init")
    assert r.returncode == 0, r.stderr
    assert (sub / ".juicer" / "state.json").exists()
    assert not (tmp_path / ".juicer").exists()


def test_nested_init_refused_without_flag(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Outer").returncode == 0
    inner = tmp_path / "inner"
    inner.mkdir()

    r = run(inner, "init")
    assert r.returncode == 1, r.stderr
    assert "--nested" in r.stderr
    assert not (inner / ".juicer").exists()

    # the outer workspace keeps its state and its mission
    assert (tmp_path / ".juicer" / "state.json").exists()
    outer = json.loads(run(tmp_path, "status").stdout.split("\navailable:")[0])
    assert outer["status"] == "planning"


def test_nested_init_allowed_with_flag_keeps_roots_separate(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Outer").returncode == 0
    inner = tmp_path / "inner"
    inner.mkdir()

    r = run(inner, "init", "--nested")
    assert r.returncode == 0, r.stderr
    assert "nested workspace" in r.stderr
    assert (inner / ".juicer" / "state.json").exists()

    inner_state = json.loads(run(inner, "status").stdout.split("\navailable:")[0])
    assert inner_state["status"] == "idle"
    outer_state = json.loads(run(tmp_path, "status").stdout.split("\navailable:")[0])
    assert outer_state["status"] == "planning"
    assert outer_state["current_unit"] is None


def test_nearest_workspace_wins(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Outer").returncode == 0
    inner = tmp_path / "inner"
    inner.mkdir()
    assert run(inner, "init", "--nested").returncode == 0

    r = run(inner, "status")
    assert r.returncode == 0, r.stderr
    shown = json.loads(r.stdout.split("\navailable:")[0])
    assert shown["status"] == "idle"          # inner workspace, not outer
