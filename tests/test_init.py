import os
import re
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"

MIRRORS = [
    ".opencode/agents/", ".opencode/juicer-kit.md",
    ".claude/agents/", ".claude/skills/", ".claude/juicer-kit.md",
    ".cursor/agents/", ".cursor/juicer-kit.md",
    ".codex/agents/", ".codex/juicer-kit.md",
    ".juicer/runtime/", ".juicer/state.lock", ".juicer/state.json.tmp",
]
GITIGNORE_MARKER = "# Juicer Kit — generated mirrors"
# Harness configuration the user owns: these must stay tracked.
OWNED_HARNESS_FILES = [".opencode/opencode.json", ".claude/settings.json",
                       ".cursor/rules/keep.mdc", ".codex/config.toml"]


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


def test_init_gitignore_does_not_hide_harness_configuration(tmp_path):
    """M-04: whole-harness ignores would silently untrack user config."""
    assert run(tmp_path, "init").returncode == 0
    lines = set((tmp_path / ".gitignore").read_text().splitlines())
    for directory in (".opencode/", ".claude/", ".cursor/", ".codex/"):
        assert directory not in lines, f"{directory} ignores user-owned files"
    assert GITIGNORE_MARKER in (tmp_path / ".gitignore").read_text()

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for rel in OWNED_HARNESS_FILES:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
        probe = subprocess.run(["git", "check-ignore", "-q", rel],
                               cwd=tmp_path, capture_output=True)
        assert probe.returncode == 1, f"{rel} is git-ignored"
    for rel in (".opencode/agents/reviewer.md", ".claude/skills/ship/SKILL.md",
                ".cursor/agents/coder.md", ".codex/agents/devops.toml"):
        probe = subprocess.run(["git", "check-ignore", "-q", rel],
                               cwd=tmp_path, capture_output=True)
        assert probe.returncode == 0, f"{rel} should be ignored (generated)"


def test_init_rewrites_stale_managed_ignore_block(tmp_path):
    """A block written by an older kit is upgraded in place."""
    assert run(tmp_path, "init").returncode == 0
    path = tmp_path / ".gitignore"
    stale = "custom.log\n\n" + GITIGNORE_MARKER + "\n.opencode/\n.claude/\n.cursor/\n.codex/\n"
    path.write_text(stale)
    assert run(tmp_path, "init").returncode == 0

    text = path.read_text()
    lines = text.splitlines()
    assert lines.count(GITIGNORE_MARKER) == 1, "managed block duplicated"
    assert "custom.log" in lines
    for directory in (".opencode/", ".claude/", ".cursor/", ".codex/"):
        assert directory not in lines, f"stale {directory} survived"
    for mirror in MIRRORS:
        assert lines.count(mirror) == 1, f"{mirror} count = {lines.count(mirror)}"


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
    mark = re.compile(r"<!-- juicer:handoff kit=\S+ revision=\d+ -->")
    def normalized(text):
        # The only legitimate template/copy difference is the stamped
        # handoff freshness marker.
        return mark.sub("<!-- juicer:handoff -->", text)
    for name in ("handoff", "decisions", "learnings"):
        project = tmp_path / ".juicer" / f"{name}.md"
        template = KIT / ".juicer" / "templates" / f"{name}.md"
        assert project.exists(), name
        assert normalized(project.read_text()) == normalized(template.read_text()), name
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


def _load_cli(name="juicer_cli_init"):
    import argparse
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader(name, str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module, argparse


def test_init_copies_shipped_templates_not_live_kit_state(tmp_path):
    """M-09: init ships .juicer/templates/*, never this repo's own state."""
    module, argparse = _load_cli()
    mission_sentinel = tmp_path / "template-mission.md"
    plan_sentinel = tmp_path / "template-plan.md"
    mission_sentinel.write_text(
        (KIT / ".juicer" / "templates" / "mission.md").read_text().replace(
            "No active mission.", "SENTINEL MISSION."))
    plan_sentinel.write_text(
        (KIT / ".juicer" / "templates" / "plan.md").read_text() + "\nSENTINEL PLAN.\n")
    module.MISSION_TEMPLATE = mission_sentinel
    module.PLAN_TEMPLATE = plan_sentinel

    previous = os.getcwd()
    try:
        os.chdir(tmp_path)
        module._bind_for_command("init")
        module.cmd_init(argparse.Namespace(nested=False))
    finally:
        os.chdir(previous)

    assert "SENTINEL MISSION." in (tmp_path / ".juicer" / "mission.md").read_text()
    assert "SENTINEL PLAN." in (tmp_path / ".juicer" / "plan.md").read_text()
    assert (tmp_path / "AGENTS.md").exists()
