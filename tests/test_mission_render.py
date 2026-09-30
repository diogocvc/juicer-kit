"""Deterministic mission rendering (BUG-05)."""

import json
import re
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
TEMPLATE = KIT / ".juicer" / "templates" / "mission.md"


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def mission_text(tmp_path):
    return (tmp_path / ".juicer" / "mission.md").read_text()


def state(tmp_path):
    return json.loads((tmp_path / ".juicer" / "state.json").read_text())


def init(tmp_path):
    assert run(tmp_path, "init").returncode == 0


def test_mission_status_line_and_objective_replaced(tmp_path):
    init(tmp_path)
    assert run(tmp_path, "mission", "First objective").returncode == 0
    text = mission_text(tmp_path)
    assert "**Status:** planning" in text
    assert "**Status:** idle" not in text
    assert "First objective" in text
    assert "No active mission." not in text


def test_new_mission_resets_customized_sections(tmp_path):
    """A new mission is a clean context: prior customization is replaced."""
    init(tmp_path)
    assert run(tmp_path, "mission", "First objective").returncode == 0
    text = mission_text(tmp_path)
    text = text.replace("- None recorded.", "- Only use the legacy API")
    text = text.replace("- TBD", "- bespoke scope line")
    (tmp_path / ".juicer" / "mission.md").write_text(text)

    assert run(tmp_path, "mission", "Second objective").returncode == 0
    new = mission_text(tmp_path)
    assert "First objective" not in new
    assert "Second objective" in new
    assert "Only use the legacy API" not in new
    assert "bespoke scope line" not in new
    # structural sections all present, in template order
    headings = [line for line in TEMPLATE.read_text().splitlines()
                if line.startswith("#")]
    positions = [new.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_mission_objective_with_arbitrary_markdown(tmp_path):
    init(tmp_path)
    objective = "Implement **X**\n## Embedded note\n- item one\n- item two"
    assert run(tmp_path, "mission", objective).returncode == 0
    text = mission_text(tmp_path)
    assert "Implement **X**" in text
    assert "## Embedded note" in text
    assert text.count("## Success criteria") == 1
    assert "## Constraints" in text
    assert "## Human gates" in text


def test_mission_ids_are_unique_and_ordered(tmp_path):
    init(tmp_path)
    assert run(tmp_path, "mission", "First").returncode == 0
    first = state(tmp_path)["mission_id"]
    assert run(tmp_path, "mission", "Second").returncode == 0
    second = state(tmp_path)["mission_id"]

    pattern = r"^\d{8}-\d{6}-\d{6}-[0-9a-f]{8}$"
    assert re.match(pattern, first), first
    assert re.match(pattern, second), second
    assert first != second
    assert first < second


def test_mission_resets_approvals_and_records(tmp_path):
    init(tmp_path)
    assert run(tmp_path, "mission", "First").returncode == 0
    assert run(tmp_path, "approve", "--by=test").returncode == 0
    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0

    assert run(tmp_path, "mission", "Second").returncode == 0
    s = state(tmp_path)
    assert s["status"] == "planning"
    assert s["approved"] is False
    assert s["ship_approved"] is False
    assert "approval" not in s
    assert "ship_approval" not in s
    assert s["current_unit"] is None


def load_cli(name="juicer_cli_mission"):
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader(name, str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_render_reads_the_shipped_template_not_live_state(tmp_path):
    """M-09: rendering must never pick up this repository's own mission."""
    sentinel = tmp_path / "mission-template.md"
    sentinel.write_text(TEMPLATE.read_text().replace(
        "Define measurable success criteria.", "SENTINEL CRITERIA."))
    cli = load_cli()
    assert cli.MISSION_TEMPLATE == TEMPLATE
    cli.MISSION_TEMPLATE = sentinel

    rendered = cli.render_mission("Objective here")
    assert "SENTINEL CRITERIA." in rendered
    assert "Objective here" in rendered
    assert "Define measurable success criteria." not in rendered
