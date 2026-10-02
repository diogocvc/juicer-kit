"""Handoff freshness: marker, checkpoint log, state.json wins.

Phase 1 contract: `.juicer/handoff.md` carries a CLI-stamped marker,
`checkpoint --note` appends to its Checkpoint log, `juicer handoff`
refreshes the marker, and `juicer status` only ever *notes* staleness —
never blocks, never derives machine facts from the narrative.
"""

import json
import re
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
VERSION = (KIT / "VERSION").read_text().strip()
MARKER_RE = re.compile(r"<!-- juicer:handoff kit=(\S+) revision=(\d+) -->")


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def state(root):
    return json.loads((root / ".juicer" / "state.json").read_text())


def handoff(root):
    return (root / ".juicer" / "handoff.md").read_text()


def marker(root):
    match = MARKER_RE.search(handoff(root))
    assert match is not None, "handoff freshness marker missing"
    return match.group(1), int(match.group(2))


def ready_project(root):
    assert run(root, "init").returncode == 0
    assert run(root, "mission", "Objective under test").returncode == 0
    assert run(root, "approve", "--by=test").returncode == 0


def status_json(stdout):
    return json.loads(stdout.split("\navailable:")[0])


def test_template_ships_marker_and_checkpoint_log():
    text = (KIT / ".juicer" / "templates" / "handoff.md").read_text()
    first = text.splitlines()[0]
    match = MARKER_RE.fullmatch(first)
    assert match is not None, "template must open with the freshness marker"
    assert int(match.group(2)) == 0
    assert "## Checkpoint log" in text
    assert ".juicer/state.json" in text


def test_init_stamps_marker_from_live_state(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    text = handoff(tmp_path)
    assert MARKER_RE.fullmatch(text.splitlines()[0]) is not None
    kit, revision = marker(tmp_path)
    assert kit == VERSION
    assert revision == state(tmp_path)["revision"]


def test_init_stamp_is_byte_idempotent(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    first = (tmp_path / ".juicer" / "handoff.md").read_bytes()
    assert run(tmp_path, "init").returncode == 0
    assert (tmp_path / ".juicer" / "handoff.md").read_bytes() == first


def test_status_is_fresh_right_after_init(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "status")
    assert r.returncode == 0
    assert "handoff" not in r.stderr


def test_status_notes_staleness_but_never_blocks(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    r = run(tmp_path, "status")
    assert r.returncode == 0, "staleness must never block status"
    assert "handoff.md is stale" in r.stderr
    assert "juicer handoff" in r.stderr
    assert status_json(r.stdout)["status"] == "ready"


def test_checkpoint_note_logs_entry_and_refreshes(tmp_path):
    ready_project(tmp_path)
    r = run(tmp_path, "checkpoint", "ready", "--note",
            "unit finished, tests green")
    assert r.returncode == 0, r.stderr
    text = handoff(tmp_path)
    section = text.split("## Checkpoint log", 1)[1]
    entry = [line for line in section.splitlines() if line.startswith("- ")]
    assert len(entry) == 1
    assert "unit finished, tests green" in entry[0]
    assert "**ready**" in entry[0]
    assert f"(rev {state(tmp_path)['revision']})" in entry[0]
    r = run(tmp_path, "status")
    assert r.returncode == 0
    assert "handoff.md is stale" not in r.stderr


def test_checkpoint_note_is_normalized_to_one_line(tmp_path):
    ready_project(tmp_path)
    r = run(tmp_path, "checkpoint", "ready", "--note",
            "first line\nsecond line")
    assert r.returncode == 0, r.stderr
    section = handoff(tmp_path).split("## Checkpoint log", 1)[1]
    entry = [line for line in section.splitlines() if line.startswith("- ")]
    assert len(entry) == 1
    assert "first line second line" in entry[0]


def test_handoff_command_stamps_stale_handoff(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "checkpoint", "ready").returncode == 0  # now stale
    r = run(tmp_path, "handoff")
    assert r.returncode == 0, r.stderr
    assert "Handoff stamped" in r.stdout
    kit, revision = marker(tmp_path)
    assert kit == VERSION
    assert revision == state(tmp_path)["revision"]
    assert "handoff.md is stale" not in run(tmp_path, "status").stderr
    r = run(tmp_path, "handoff")
    assert "already fresh" in r.stdout


def test_handoff_command_requires_the_file(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / ".juicer" / "handoff.md").unlink()
    r = run(tmp_path, "handoff")
    assert r.returncode == 1
    assert "juicer init" in r.stderr
    # status stays advisory
    r = run(tmp_path, "status")
    assert r.returncode == 0
    assert "missing .juicer/handoff.md" in r.stderr


def test_legacy_handoff_without_marker_is_noted_then_stampable(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    legacy = MARKER_RE.sub("", handoff(tmp_path)).lstrip("\n")
    (tmp_path / ".juicer" / "handoff.md").write_text(legacy)
    r = run(tmp_path, "status")
    assert r.returncode == 0
    assert "no freshness marker" in r.stderr
    assert run(tmp_path, "handoff").returncode == 0
    assert marker(tmp_path)[0] == VERSION
    assert "no freshness marker" not in run(tmp_path, "status").stderr


def test_state_json_wins_over_handoff_narrative(tmp_path):
    ready_project(tmp_path)
    text = handoff(tmp_path)
    (tmp_path / ".juicer" / "handoff.md").write_text(
        text.replace("## Current state",
                     "## Current state\n\nStatus: executing (UNIT-999)."))
    r = run(tmp_path, "status")
    assert r.returncode == 0
    shown = status_json(r.stdout)
    assert shown["status"] == "ready"
    assert shown["current_unit"] is None


def test_checkpoint_note_validated_before_state_write(tmp_path):
    ready_project(tmp_path)
    (tmp_path / ".juicer" / "handoff.md").unlink()
    before = state(tmp_path)
    r = run(tmp_path, "checkpoint", "ready", "--note", "should not apply")
    assert r.returncode == 1
    assert "juicer init" in r.stderr
    assert state(tmp_path) == before, "rejected note must not transition state"


def test_checkpoint_note_cannot_follow_symlink_outside_root(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    outside = tmp_path / "outside-handoff.md"
    outside.write_text("PRECIOUS\n")
    ready_project(root)
    (root / ".juicer" / "handoff.md").unlink()
    (root / ".juicer" / "handoff.md").symlink_to(outside)
    before = state(root)
    r = run(root, "checkpoint", "ready", "--note", "redirected")
    assert r.returncode == 1
    assert "resolves outside the project root" in r.stderr
    assert outside.read_text() == "PRECIOUS\n"
    assert state(root) == before
