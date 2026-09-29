import re
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"

MIRRORS = [".opencode/", ".claude/", ".cursor/", ".codex/", ".juicer/runtime/",
           ".juicer/state.lock", ".juicer/state.json.tmp"]


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True, capture_output=True)


def test_init_copies_canonical_tree(tmp_path):
    r = run(tmp_path, "init")
    assert r.returncode == 0, r.stderr
    expected = [
        "AGENTS.md",
        ".juicer/state.json",
        ".juicer/mission.md",
        ".juicer/plan.md",
        ".juicer/handoff.md",
        ".juicer/decisions.md",
        ".juicer/learnings.md",
        ".juicer/workflows/feature.md",
        ".juicer/workflows/bugfix.md",
        ".juicer/workflows/refactor.md",
        ".juicer/workflows/release.md",
        "agents/reviewer.md",
        "agents/coder.md",
        ".agents/skills/mission-control/SKILL.md",
        ".agents/skills/code-review/SKILL.md",
    ]
    for rel in expected:
        assert (tmp_path / rel).exists(), f"missing {rel}"


def test_init_is_idempotent_and_preserves_edits(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / "agents" / "reviewer.md").write_text("EDITED WORKER\n")
    (tmp_path / ".juicer" / "mission.md").write_text("EDITED MISSION\n")
    (tmp_path / "AGENTS.md").write_text("EDITED ENTRYPOINT\n")

    r = run(tmp_path, "init")
    assert r.returncode == 0, r.stderr

    assert (tmp_path / "agents" / "reviewer.md").read_text() == "EDITED WORKER\n"
    assert (tmp_path / ".juicer" / "mission.md").read_text() == "EDITED MISSION\n"
    assert (tmp_path / "AGENTS.md").read_text() == "EDITED ENTRYPOINT\n"


def test_init_gitignore_idempotent_and_scoped(tmp_path):
    (tmp_path / ".gitignore").write_text("custom.log\n")
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "init").returncode == 0

    lines = (tmp_path / ".gitignore").read_text().splitlines()
    assert "custom.log" in lines
    for mirror in MIRRORS:
        assert lines.count(mirror) == 1, f"{mirror} count = {lines.count(mirror)}"
    for protected in (".juicer/", "agents/", ".agents/skills/", "AGENTS.md"):
        assert protected not in lines


def test_worker_resolves_project_then_kit(tmp_path):
    assert run(tmp_path, "init").returncode == 0

    r = run(tmp_path, "worker", "reviewer")
    assert r.returncode == 0, r.stderr
    assert "Worker contract:" in r.stdout
    assert str(tmp_path / "agents" / "reviewer.md") in r.stdout

    shutil.rmtree(tmp_path / "agents")
    r = run(tmp_path, "worker", "reviewer")
    assert r.returncode == 0, r.stderr
    assert str(KIT / "agents" / "reviewer.md") in r.stdout


def test_worker_rejects_invalid_names(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    for name in ["../reviewer", "Reviewer", "a/b", "", "no-such-worker"]:
        r = run(tmp_path, "worker", name)
        assert r.returncode == 1, f"{name!r} returned {r.returncode}"
        assert r.stderr.startswith("error:"), r.stderr
        assert r.stdout == ""


def test_mission_requires_initialized_workspace(tmp_path):
    r = run(tmp_path, "mission", "Ship the release")
    assert r.returncode == 1
    assert "juicer init" in r.stderr
    assert not (tmp_path / ".juicer").exists()


def test_unknown_adapter_exits_nonzero(tmp_path):
    r = run(tmp_path, "capabilities", "nonexistent")
    assert r.returncode == 1
    assert "Unknown adapter" in r.stderr
    assert r.stdout == ""


def test_blocked_gate_exits_nonzero_on_stderr(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "start", "UNIT-001")
    assert r.returncode == 1
    assert "Blocked" in r.stderr
    assert r.stdout == ""

    r = run(tmp_path, "approve")
    assert r.returncode == 1
    assert "Cannot approve" in r.stderr
    assert r.stdout == ""


def test_init_copies_pristine_history_templates(tmp_path):
    """BUG-06: kit development history never ships into a new project."""
    assert run(tmp_path, "init").returncode == 0
    for name in ("handoff", "decisions", "learnings"):
        project = tmp_path / ".juicer" / f"{name}.md"
        template = KIT / ".juicer" / "templates" / f"{name}.md"
        assert project.exists(), name
        assert project.read_bytes() == template.read_bytes(), name
        text = project.read_text()
        assert not re.search(r"(?m)^## \d{4}-\d{2}-\d{2}", text), name
        assert not re.search(r"(?m)^### \d{4}-\d{2}-\d{2}", text), name
        assert "post-audit" not in text, name


def test_init_does_not_copy_templates_dir(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert not (tmp_path / ".juicer" / "templates").exists()


def test_kit_templates_are_pristine():
    for name in ("handoff", "decisions", "learnings"):
        text = (KIT / ".juicer" / "templates" / f"{name}.md").read_text()
        assert not re.search(r"(?m)^## \d{4}-\d{2}-\d{2}", text), name
        assert not re.search(r"(?m)^### \d{4}-\d{2}-\d{2}", text), name
        assert "post-audit" not in text, name
