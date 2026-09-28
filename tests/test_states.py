import json
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True, capture_output=True)


def state(tmp_path):
    return json.loads((tmp_path / ".juicer" / "state.json").read_text())


def fresh(tmp_path, objective="Objective under test"):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", objective).returncode == 0
    assert run(tmp_path, "approve").returncode == 0


def test_initial_state_is_idle(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "idle"
    assert s["approved"] is False
    assert s["ship_approved"] is False


def test_happy_path_full_cycle(tmp_path):
    fresh(tmp_path)
    assert state(tmp_path)["status"] == "ready"

    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "executing"
    assert s["current_unit"] == "UNIT-001"

    assert run(tmp_path, "checkpoint", "executing").returncode == 0
    assert state(tmp_path)["status"] == "executing"

    assert run(tmp_path, "checkpoint", "blocked").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "blocked"
    assert s["current_unit"] == "UNIT-001"

    assert run(tmp_path, "checkpoint", "executing").returncode == 0
    assert state(tmp_path)["status"] == "executing"

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "ready"
    assert s["current_unit"] is None

    assert run(tmp_path, "ship-approve").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    assert run(tmp_path, "finish").returncode == 0
    assert state(tmp_path)["status"] == "done"


def test_approve_rejected_outside_allowed_states(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "approve")
    assert r.returncode == 1
    assert "Cannot approve" in r.stderr
    assert state(tmp_path)["status"] == "idle"

    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    r = run(tmp_path, "approve")
    assert r.returncode == 1
    assert "Cannot approve" in r.stderr
    assert state(tmp_path)["status"] == "executing"

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert run(tmp_path, "finish").returncode == 0
    r = run(tmp_path, "approve")
    assert r.returncode == 1
    assert "Cannot approve" in r.stderr
    assert state(tmp_path)["status"] == "done"


def test_start_blocked_before_approval(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "start", "UNIT-001")
    assert r.returncode == 1
    assert "Blocked" in r.stderr
    assert state(tmp_path)["status"] == "idle"

    assert run(tmp_path, "mission", "New objective").returncode == 0
    r = run(tmp_path, "start", "UNIT-001")
    assert r.returncode == 1
    assert "Blocked" in r.stderr
    assert state(tmp_path)["status"] == "planning"


def test_start_rejected_from_executing(tmp_path):
    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    r = run(tmp_path, "start", "UNIT-002")
    assert r.returncode == 1
    assert "Cannot start" in r.stderr
    assert state(tmp_path)["current_unit"] == "UNIT-001"

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert run(tmp_path, "start", "UNIT-002").returncode == 0
    assert state(tmp_path)["current_unit"] == "UNIT-002"


def test_checkpoint_rejected_from_idle_and_planning(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    for target in ("executing", "blocked", "ready", "done"):
        r = run(tmp_path, "checkpoint", target)
        assert r.returncode == 1
        assert "Cannot checkpoint" in r.stderr
    assert state(tmp_path)["status"] == "idle"

    assert run(tmp_path, "mission", "Objective").returncode == 0
    for target in ("executing", "blocked", "ready", "done"):
        r = run(tmp_path, "checkpoint", target)
        assert r.returncode == 1
        assert "Cannot checkpoint" in r.stderr
    assert state(tmp_path)["status"] == "planning"


def test_checkpoint_done_only_from_ready(tmp_path):
    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0

    r = run(tmp_path, "checkpoint", "done")
    assert r.returncode == 1
    assert "Cannot checkpoint done" in r.stderr
    assert state(tmp_path)["status"] == "executing"

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert run(tmp_path, "checkpoint", "done").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "done"
    assert s["current_unit"] is None


def test_checkpoint_blocked_requires_active_unit(tmp_path):
    fresh(tmp_path)
    r = run(tmp_path, "checkpoint", "blocked")
    assert r.returncode == 1
    assert "Cannot checkpoint blocked" in r.stderr

    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    assert run(tmp_path, "checkpoint", "blocked").returncode == 0
    r = run(tmp_path, "checkpoint", "blocked")
    assert r.returncode == 0


def test_finish_gates(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "finish")
    assert r.returncode == 1
    assert "Cannot finish" in r.stderr

    assert run(tmp_path, "mission", "Objective").returncode == 0
    r = run(tmp_path, "finish")
    assert r.returncode == 1
    assert "Cannot finish" in r.stderr

    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    r = run(tmp_path, "finish")
    assert r.returncode == 1
    assert "Cannot finish" in r.stderr
    assert state(tmp_path)["status"] == "executing"


def test_ship_approve_gates(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "ship-approve")
    assert r.returncode == 1
    assert "Cannot ship-approve" in r.stderr
    assert state(tmp_path)["ship_approved"] is False

    fresh(tmp_path)
    r = run(tmp_path, "ship-approve")
    assert r.returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    r = run(tmp_path, "ship-approve")
    assert r.returncode == 1
    assert "Cannot ship-approve" in r.stderr
    assert state(tmp_path)["ship_approved"] is True


def test_mission_rejected_from_executing(tmp_path):
    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    r = run(tmp_path, "mission", "Interrupted objective")
    assert r.returncode == 1
    assert "Cannot start a new mission" in r.stderr
    s = state(tmp_path)
    assert s["status"] == "executing"
    assert s["current_unit"] == "UNIT-001"


def test_mission_from_done_starts_new_cycle(tmp_path):
    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert run(tmp_path, "ship-approve").returncode == 0
    assert run(tmp_path, "finish").returncode == 0

    assert run(tmp_path, "mission", "Second objective").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "planning"
    assert s["approved"] is False
    assert s["ship_approved"] is False
    assert s["current_unit"] is None
    assert "Second objective" in (tmp_path / ".juicer" / "mission.md").read_text()


def test_status_lists_available_commands(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "status")
    assert r.returncode == 0
    assert "available: mission" in r.stdout

    fresh(tmp_path)
    r = run(tmp_path, "status")
    assert "available:" in r.stdout
    for command in ("mission", "approve", "start <unit>", "checkpoint <status>"):
        assert command in r.stdout

    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    r = run(tmp_path, "status")
    assert "checkpoint <status>" in r.stdout
    assert "start <unit>" not in r.stdout
    assert "finish" not in r.stdout

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    r = run(tmp_path, "status")
    for command in ("finish", "ship-approve", "start <unit>"):
        assert command in r.stdout
