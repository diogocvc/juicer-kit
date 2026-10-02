"""Session briefing: read-only orientation for a fresh session.

`juicer session` must create nothing, derive every fact from
state.json (the narrative never overrides it) and only note — never
block — a stale handoff.
"""

import json
import re
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
MARKER_RE = re.compile(r"<!-- juicer:handoff kit=(\S+) revision=(\d+) -->")


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def state(root):
    return json.loads((root / ".juicer" / "state.json").read_text())


def ready_project(root):
    assert run(root, "init").returncode == 0
    assert run(root, "mission", "Objective under test").returncode == 0
    assert run(root, "approve", "--by=test").returncode == 0


def test_session_briefing_after_init(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "session")
    assert r.returncode == 0, r.stderr
    assert "session briefing" in r.stdout
    assert f"workspace: {tmp_path}" in r.stdout
    assert "status: idle" in r.stdout
    assert "objective: No active mission." in r.stdout
    assert f"handoff: {tmp_path / '.juicer' / 'handoff.md'}" in r.stdout
    assert "available:" in r.stdout
    assert ("read .juicer/mission.md, .juicer/plan.md and "
            ".juicer/handoff.md before acting") in r.stdout


def test_session_is_read_only(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    before_state = (tmp_path / ".juicer" / "state.json").read_bytes()
    before_mission = (tmp_path / ".juicer" / "mission.md").read_bytes()
    r = run(tmp_path, "session")
    assert r.returncode == 0
    assert (tmp_path / ".juicer" / "state.json").read_bytes() == before_state
    assert (tmp_path / ".juicer" / "mission.md").read_bytes() == before_mission


def test_session_never_creates_mission(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / ".juicer" / "mission.md").unlink()
    r = run(tmp_path, "session")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / ".juicer" / "mission.md").exists()
    assert "objective: none" in r.stdout


def test_session_reports_status_unit_and_available(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "start", "UNIT-007").returncode == 0
    r = run(tmp_path, "session")
    assert r.returncode == 0, r.stderr
    assert "status: executing" in r.stdout
    assert "unit: UNIT-007" in r.stdout
    assert "objective: Objective under test" in r.stdout
    assert "available:" in r.stdout
    assert "checkpoint <status>" in r.stdout


def test_session_notes_stale_handoff_without_blocking(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "checkpoint", "ready").returncode == 0  # state moved
    r = run(tmp_path, "session")
    assert r.returncode == 0, "staleness must never block a session"
    assert "handoff.md is stale" in r.stderr
    assert "juicer handoff" in r.stderr
    assert "status: ready" in r.stdout
    # the marker really is behind, and the briefing did not touch it
    text = (tmp_path / ".juicer" / "handoff.md").read_text()
    revision = int(MARKER_RE.search(text).group(2))
    assert revision != state(tmp_path)["revision"]


def test_session_requires_workspace_and_creates_nothing(tmp_path):
    r = run(tmp_path, "session")
    assert r.returncode == 1
    assert "juicer init" in r.stderr
    assert not (tmp_path / ".juicer").exists()
