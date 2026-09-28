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


def test_corrupt_state_fails_cleanly(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / ".juicer" / "state.json").write_text("{not valid json")
    r = run(tmp_path, "status")
    assert r.returncode == 1
    assert "Invalid state file" in r.stderr
    assert "Traceback" not in r.stderr


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


def to_blocked(tmp_path):
    run(tmp_path, "checkpoint", "ready")
    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    assert run(tmp_path, "checkpoint", "blocked").returncode == 0
    assert state(tmp_path)["status"] == "blocked"


def test_blocked_allows_approve_start_and_ready_checkpoint(tmp_path):
    to_blocked(tmp_path)
    assert run(tmp_path, "approve").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "ready"
    assert s["approved"] is True

    to_blocked(tmp_path)
    assert run(tmp_path, "start", "UNIT-002").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "executing"
    assert s["current_unit"] == "UNIT-002"

    to_blocked(tmp_path)
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "ready"
    assert s["current_unit"] is None


def test_blocked_allows_new_mission(tmp_path):
    to_blocked(tmp_path)
    assert run(tmp_path, "mission", "Replanned objective").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "planning"
    assert s["approved"] is False
    assert "Replanned objective" in (tmp_path / ".juicer" / "mission.md").read_text()


def test_steady_state_gates_are_idempotent(tmp_path):
    fresh(tmp_path)
    assert run(tmp_path, "approve").returncode == 0
    assert state(tmp_path)["status"] == "ready"

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["status"] == "ready"

    assert run(tmp_path, "ship-approve").returncode == 0
    assert run(tmp_path, "ship-approve").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    assert run(tmp_path, "finish").returncode == 0
    assert run(tmp_path, "finish").returncode == 0
    assert state(tmp_path)["status"] == "done"


def test_ship_approve_rejected_from_blocked_allowed_from_done(tmp_path):
    to_blocked(tmp_path)
    r = run(tmp_path, "ship-approve")
    assert r.returncode == 1
    assert "Cannot ship-approve" in r.stderr
    assert state(tmp_path)["ship_approved"] is False

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert run(tmp_path, "finish").returncode == 0
    assert run(tmp_path, "ship-approve").returncode == 0
    assert state(tmp_path)["ship_approved"] is True


def test_unknown_status_rejected_by_every_gate(tmp_path):
    fresh(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data["status"] = "bogus"
    path.write_text(json.dumps(data))

    for args in (("mission", "Objective"), ("approve",), ("start", "UNIT-009"),
                 ("checkpoint", "executing"), ("finish",), ("ship-approve",)):
        r = run(tmp_path, *args)
        assert r.returncode == 1, args
        assert "status=bogus" in r.stderr, args
        assert "Traceback" not in r.stderr

    r = run(tmp_path, "status")
    assert r.returncode == 0
    assert "available:" not in r.stdout


def test_ship_gate_consumers_require_state_check():
    skill = (KIT / ".agents" / "skills" / "ship" / "SKILL.md").read_text()
    workflow = (KIT / ".juicer" / "workflows" / "release.md").read_text()
    devops = (KIT / "agents" / "devops.md").read_text()
    assert "ship_approved" in skill
    assert "ship_approved" in workflow
    assert "ship_approved" in devops
