"""B-01: no Juicer write may be redirected outside the project root.

A repository can carry symlinks (git stores them). Before this suite,
`juicer init` and every state write resolved the *destination* only after
following those symlinks, so a planted `.juicer -> /outside` or
`.gitignore -> /outside/file` moved Juicer's own writes outside the
workspace with no warning.

Every core write now goes through ``confine_write`` -> ``confine_path``.
"""

import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def outside(tmp_path):
    """A sibling directory that is always outside the workspace."""
    target = tmp_path.parent / (tmp_path.name + "-outside")
    target.mkdir(exist_ok=True)
    for child in target.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return target


def test_state_dir_symlink_cannot_escape_root(tmp_path):
    victim = outside(tmp_path)
    (tmp_path / ".juicer").symlink_to(victim, target_is_directory=True)

    r = run(tmp_path, "init")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "resolves outside the project root" in r.stderr
    assert list(victim.iterdir()) == [], "state was written outside the root"


def test_gitignore_symlink_cannot_escape_root(tmp_path):
    victim = outside(tmp_path) / "victim-gitignore"
    victim.write_text("PRECIOUS\n")
    (tmp_path / ".gitignore").symlink_to(victim)

    r = run(tmp_path, "init")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "resolves outside the project root" in r.stderr
    assert victim.read_text() == "PRECIOUS\n", "outside .gitignore was modified"


def test_gitignore_broken_symlink_cannot_create_outside(tmp_path):
    victim = outside(tmp_path) / "created-from-kit"
    (tmp_path / ".gitignore").symlink_to(victim)

    r = run(tmp_path, "init")
    assert r.returncode == 1, r.stdout + r.stderr
    assert not victim.exists(), "outside file was created"


def test_entrypoint_symlink_cannot_escape_root(tmp_path):
    victim = outside(tmp_path) / "created-from-kit"
    (tmp_path / "AGENTS.md").symlink_to(victim)

    r = run(tmp_path, "init")
    assert r.returncode == 1, r.stdout + r.stderr
    assert not victim.exists(), "outside AGENTS.md was created"


def test_nested_agents_dir_symlink_cannot_escape_root(tmp_path):
    victim = outside(tmp_path)
    (tmp_path / "agents").symlink_to(victim, target_is_directory=True)

    r = run(tmp_path, "init")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "resolves outside the project root" in r.stderr
    assert list(victim.iterdir()) == [], "worker files written outside the root"


def test_mission_symlink_cannot_escape_root(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    victim = outside(tmp_path) / "mission-outside"
    victim.write_text("PRECIOUS MISSION\n")
    (tmp_path / ".juicer" / "mission.md").unlink()
    (tmp_path / ".juicer" / "mission.md").symlink_to(victim)

    r = run(tmp_path, "mission", "New objective")
    assert r.returncode == 1, r.stdout + r.stderr
    assert victim.read_text() == "PRECIOUS MISSION\n"
    state = (tmp_path / ".juicer" / "state.json").read_text()
    assert '"status": "planning"' not in state, (
        "state was advanced even though the mission write was refused")


def test_state_lock_symlink_cannot_escape_root(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    victim = outside(tmp_path)
    (tmp_path / ".juicer" / "state.lock").unlink()
    (tmp_path / ".juicer" / "state.lock").symlink_to(victim / "lock-outside")

    r = run(tmp_path, "mission", "New objective")
    assert r.returncode == 1, r.stdout + r.stderr
    assert not (victim / "lock-outside").exists(), (
        "lock file was created outside the root")


def test_runtime_manifest_symlink_cannot_escape_root(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    victim = outside(tmp_path)
    shutil.rmtree(tmp_path / ".juicer" / "runtime")
    (tmp_path / ".juicer" / "runtime").symlink_to(victim, target_is_directory=True)

    r = run(tmp_path, "sync", "all")
    assert r.returncode == 1, r.stdout + r.stderr
    assert list(victim.iterdir()) == [], (
        "manifest was written outside the root")


def test_normal_workspace_is_unaffected(tmp_path):
    """Positive control: confinement must not reject a plain workspace."""
    assert run(tmp_path, "init").returncode == 0
    assert (tmp_path / ".juicer" / "state.json").exists()
    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert run(tmp_path, "mission", "Ship 2.4.0").returncode == 0
    assert run(tmp_path, "status").returncode == 0
