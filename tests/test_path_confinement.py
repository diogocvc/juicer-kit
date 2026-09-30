"""Path confinement: no filesystem operation may leave the project root.

Covers audit finding R7 (manifest alone can delete outside ROOT) and the
BUG-07 fix: confine_path/confine_manifest_entry + mandatory root= on
write_generated + two-pass manifest validation.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "adapters"))

from _base import confine_manifest_entry, confine_path, write_generated  # noqa: E402

CLI = KIT / "bin" / "juicer"


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def make_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert run(project, "init").returncode == 0
    victim = tmp_path / "victim.txt"
    victim.write_text("DO NOT TOUCH\n")
    return project, victim


def manifest_file(project, adapter="opencode"):
    return project / ".juicer" / "runtime" / "manifests" / f"{adapter}.json"


def tamper_manifest(project, adapter, entry):
    path = manifest_file(project, adapter)
    data = json.loads(path.read_text())
    data["files"].update(entry)
    path.write_text(json.dumps(data, indent=2) + "\n")


OUTSIDE_ADAPTER = """
from _base import Adapter as BaseAdapter, ensure_entrypoint, write_generated

class Adapter(BaseAdapter):
    id = "outside"
    executable = "juicer-no-such-binary"

    def capabilities(self):
        return {"skills": True, "subagents": False, "parallel_agents": False,
                "human_approval": True, "persistent_context": False}

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        changes.append(write_generated(
            ctx.root.parent / "victim-adapter.txt", "escaped\\n",
            root=ctx.root, dry_run=dry_run))
        return changes
"""


def write_project_adapter(project, source):
    directory = project / "adapters" / "outside"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "adapter.py").write_text(source)
    (directory / "adapter.yaml").write_text("contract_version: 2\n")


STATE_ADAPTER = """
from _base import Adapter as BaseAdapter, ensure_entrypoint, write_generated

class Adapter(BaseAdapter):
    id = "outside"
    executable = "juicer-no-such-binary"

    def capabilities(self):
        return {"skills": True, "subagents": False, "parallel_agents": False,
                "human_approval": True, "persistent_context": False}

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        changes.append(write_generated(
            ctx.root / ".juicer" / "state.json", "{\\"pwned\\": true}\\n",
            root=ctx.root, dry_run=dry_run))
        return changes
"""


# --- unit level -----------------------------------------------------------

def test_write_generated_requires_root_keyword(tmp_path):
    with pytest.raises(TypeError):
        write_generated(tmp_path / "x.txt", "data")  # missing required root=


def test_confine_path_rejects_escape_and_root_itself(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ValueError, match="outside the project root"):
        confine_path(root, tmp_path / "escaped.txt")
    with pytest.raises(ValueError, match="outside the project root"):
        confine_path(root, root / ".." / "escaped.txt")
    with pytest.raises(ValueError, match="project root itself"):
        confine_path(root, root)
    assert confine_path(root, root / "sub" / "ok.txt") == (root / "sub" / "ok.txt").resolve()


def test_confine_path_rejects_symlink_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_text("x\n")
    link = root / "link.txt"
    link.symlink_to(victim)
    with pytest.raises(ValueError, match="outside the project root"):
        confine_path(root, link)


def test_confine_manifest_entry_strict_rules(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ValueError, match="absolute path"):
        confine_manifest_entry(root, str(tmp_path / "victim.txt"))
    with pytest.raises(ValueError, match=r"contains '\.\.'"):
        confine_manifest_entry(root, "../victim.txt")
    with pytest.raises(ValueError, match=r"contains '\.\.'"):
        confine_manifest_entry(root, "nested/../../victim.txt")
    assert confine_manifest_entry(root, ".opencode/agents/x.md", "opencode")


# --- CLI level: tampered manifests never touch files outside ROOT ---------

def test_manifest_absolute_entry_rejected(tmp_path):
    project, victim = make_project(tmp_path)
    sha = "0" * 64
    tamper_manifest(project, "opencode", {str(victim): sha})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1
    assert "unsafe" in r.stderr and "absolute" in r.stderr
    assert victim.read_text() == "DO NOT TOUCH\n"


def test_manifest_relative_escape_rejected(tmp_path):
    project, victim = make_project(tmp_path)
    tamper_manifest(project, "opencode", {"../victim.txt": "0" * 64})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1
    assert "unsafe" in r.stderr and "'..'" in r.stderr
    assert victim.read_text() == "DO NOT TOUCH\n"


def test_manifest_symlink_escape_rejected(tmp_path):
    project, victim = make_project(tmp_path)
    link = project / "link.txt"
    link.symlink_to(victim)
    tamper_manifest(project, "opencode", {"link.txt": "0" * 64})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1
    assert "unsafe" in r.stderr
    assert victim.read_text() == "DO NOT TOUCH\n"


def test_two_pass_validation_prevents_partial_deletes(tmp_path):
    """One valid stale entry + one unsafe entry: nothing is deleted."""
    project, victim = make_project(tmp_path)
    # make a real generated file stale so it WOULD be deleted on sync
    (project / "agents" / "finder.md").unlink()
    assert (project / ".opencode" / "agents" / "finder.md").exists()
    tamper_manifest(project, "opencode", {"../victim.txt": "0" * 64})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1
    assert "unsafe" in r.stderr
    # valid-but-stale file kept (all-or-nothing), outside victim kept
    assert (project / ".opencode" / "agents" / "finder.md").exists()
    assert victim.read_text() == "DO NOT TOUCH\n"


def test_adapter_cannot_write_outside_root(tmp_path):
    project, victim = make_project(tmp_path)
    write_project_adapter(project, OUTSIDE_ADAPTER)

    r = run(project, "sync", "outside", "--trust-project-adapters")
    assert r.returncode == 1
    assert "outside the project root" in r.stderr
    assert not (tmp_path / "victim-adapter.txt").exists()
    assert victim.read_text() == "DO NOT TOUCH\n"


def test_generated_writes_stay_inside_root(tmp_path):
    """Sanity: a normal sync only produces files under the project root."""
    project, victim = make_project(tmp_path)
    before = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert run(project, "sync", "all").returncode == 0
    after = {p for p in tmp_path.rglob("*") if p.is_file()}
    for path in after - before:
        assert str(path).startswith(str(project)), path


# --- B-02: ownership confinement ------------------------------------------
# docs/adapter-contract.md promises adapters "never write outside the
# project root, and never into .juicer/". confine_generated() is what
# actually enforces it; before this suite only the root half held.

def test_write_generated_rejects_juicer_state(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    for rel in (".juicer/state.json", ".juicer/plan.md",
                ".juicer/runtime/manifests/x.json"):
        with pytest.raises(ValueError, match="workflow core"):
            write_generated(root / rel, "{}", root=root)


def test_write_generated_rejects_vcs_config(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ValueError, match="workflow core"):
        write_generated(root / ".git" / "config", "[core]\n", root=root)
    with pytest.raises(ValueError, match="project-owned"):
        write_generated(root / ".gitignore", "*.log\n", root=root)


def test_write_generated_still_allows_harness_and_entrypoint(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    assert write_generated(root / "AGENTS.md", "# entry\n", root=root)
    assert write_generated(root / ".opencode" / "agents" / "x.md", "y\n",
                           root=root)
    assert write_generated(root / ".claude" / "skills" / "s" / "SKILL.md",
                           "y\n", root=root)


def test_manifest_entry_rejects_juicer_and_vcs_paths(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    for rel in (".juicer/plan.md", ".juicer/state.json", ".gitignore",
                ".git/HEAD"):
        with pytest.raises(ValueError):
            confine_manifest_entry(root, rel, "opencode")
    assert confine_manifest_entry(root, "AGENTS.md", "opencode")
    assert confine_manifest_entry(root, ".claude/agents/x.md", "claude-code")


def test_manifest_cannot_delete_juicer_state(tmp_path):
    project, _ = make_project(tmp_path)
    plan = project / ".juicer" / "plan.md"
    before = plan.read_bytes()
    sha = hashlib.sha256(before).hexdigest()
    tamper_manifest(project, "opencode", {".juicer/plan.md": sha})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "unsafe" in r.stderr and "workflow core" in r.stderr
    assert plan.read_bytes() == before, "workflow state was deleted"


def test_manifest_cannot_delete_gitignore(tmp_path):
    project, _ = make_project(tmp_path)
    gitignore = project / ".gitignore"
    before = gitignore.read_bytes()
    sha = hashlib.sha256(before).hexdigest()
    tamper_manifest(project, "opencode", {".gitignore": sha})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "unsafe" in r.stderr
    assert gitignore.read_bytes() == before, ".gitignore was deleted"


def test_adapter_cannot_write_juicer_state(tmp_path):
    project, _ = make_project(tmp_path)
    write_project_adapter(project, STATE_ADAPTER)
    state = project / ".juicer" / "state.json"
    before = state.read_bytes()

    r = run(project, "sync", "outside", "--trust-project-adapters")
    assert r.returncode == 1
    assert "workflow core" in r.stderr
    assert state.read_bytes() == before, "workflow state was overwritten"
