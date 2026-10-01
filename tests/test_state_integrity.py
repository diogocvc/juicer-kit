"""State integrity: atomic writes, revision fencing, approval provenance.

Covers audit findings R8 (lost update / stale-write resurrection) and the
BUG-01/BUG-02/BUG-03 fixes.
"""

import argparse
import getpass
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"


def run(cwd, *args, stdin=None):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True, stdin=stdin)


def state(tmp_path):
    return json.loads((tmp_path / ".juicer" / "state.json").read_text())


def load_cli(name="juicer_cli_under_test"):
    loader = importlib.machinery.SourceFileLoader(name, str(KIT / "bin" / "juicer"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def ready_project(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Objective under test").returncode == 0
    assert run(tmp_path, "approve", "--by=test").returncode == 0


# --- BUG-01: locking, atomicity, revision fence ---------------------------

def test_stale_write_cannot_resurrect_approvals(tmp_path):
    """R8 replay: an old snapshot written late must fail, not win."""
    ready_project(tmp_path)
    snapshot = json.loads((tmp_path / ".juicer" / "state.json").read_text())
    assert snapshot["approved"] is True

    assert run(tmp_path, "mission", "Second objective").returncode == 0
    assert state(tmp_path)["approved"] is False

    mod = load_cli()
    mod.bind_root(tmp_path)
    with pytest.raises(SystemExit):
        mod.write_state(snapshot)

    final = state(tmp_path)
    assert final["approved"] is False          # not resurrected
    assert final["status"] == "planning"
    assert final["revision"] == snapshot["revision"] + 1


def test_update_state_bumps_revision_monotonically(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    seen = [state(tmp_path)["revision"]]
    assert run(tmp_path, "mission", "One").returncode == 0
    seen.append(state(tmp_path)["revision"])
    assert run(tmp_path, "approve", "--by=test").returncode == 0
    seen.append(state(tmp_path)["revision"])
    assert seen == sorted(seen)
    assert len(set(seen)) == len(seen)
    assert all(isinstance(rev, int) for rev in seen)


def test_legacy_state_without_revision_is_upgraded(tmp_path):
    ready_project(tmp_path)
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data.pop("revision", None)
    path.write_text(json.dumps(data, indent=2) + "\n")

    assert run(tmp_path, "status").returncode == 0
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["revision"] == 1


def test_corrupt_revision_fails_cleanly(tmp_path):
    ready_project(tmp_path)
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data["revision"] = "not-an-int"
    path.write_text(json.dumps(data, indent=2) + "\n")

    r = run(tmp_path, "approve", "--by=test")
    assert r.returncode == 1
    assert "revision must be a non-negative integer" in r.stderr
    assert "Traceback" not in r.stderr


def test_atomic_write_cleans_tmp_and_preserves_original(tmp_path, monkeypatch):
    mod = load_cli()
    mod.bind_root(tmp_path)
    (tmp_path / ".juicer").mkdir()
    target = tmp_path / ".juicer" / "state.json"
    target.write_text('{"revision": 5}\n')

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(mod.os, "replace", boom)
    with pytest.raises(OSError):
        mod._atomic_write_text(target, '{"revision": 6}\n')
    monkeypatch.undo()

    assert not (tmp_path / ".juicer" / "state.json.tmp").exists()
    assert json.loads(target.read_text())["revision"] == 5


LOCK_HOLDER = textwrap.dedent(
    """
    import importlib.machinery, importlib.util, sys
    loader = importlib.machinery.SourceFileLoader("juicer_cli", {cli!r})
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.bind_root({root!r})
    with mod.state_lock():
        print("LOCKED", flush=True)
        sys.stdin.readline()
        mod.update_state(lambda s: s.update(marker="A"))
        print("A-WROTE", flush=True)
    """
)

LOCK_WAITER = textwrap.dedent(
    """
    import importlib.machinery, importlib.util, sys
    loader = importlib.machinery.SourceFileLoader("juicer_cli2", {cli!r})
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.bind_root({root!r})
    print("ABOUT", flush=True)
    mod.update_state(lambda s: s.update(b_saw=s.get("marker")))
    print("DONE", flush=True)
    """
)


def test_state_lock_serializes_concurrent_writers(tmp_path):
    """A writer inside the lock finishes before a second writer reads."""
    assert run(tmp_path, "init").returncode == 0
    args = {"cli": str(CLI), "root": str(tmp_path)}

    holder = subprocess.Popen(
        [sys.executable, "-c", LOCK_HOLDER.format(**args)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        cwd=str(tmp_path))
    try:
        assert holder.stdout.readline().strip() == "LOCKED"
        waiter = subprocess.Popen(
            [sys.executable, "-c", LOCK_WAITER.format(**args)],
            stdout=subprocess.PIPE, text=True, cwd=str(tmp_path))
        try:
            assert waiter.stdout.readline().strip() == "ABOUT"
            holder.stdin.write("GO\n")
            holder.stdin.flush()
            holder.stdin.close()
            assert holder.wait(timeout=15) == 0
            assert waiter.wait(timeout=15) == 0
        finally:
            if waiter.poll() is None:
                waiter.kill()
    finally:
        if holder.poll() is None:
            holder.kill()

    final = state(tmp_path)
    assert final["marker"] == "A"
    assert final["b_saw"] == "A"   # serialized: read after A's write


# --- BUG-02: identity and provenance -------------------------------------

def test_approve_requires_identity_without_tty(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Objective").returncode == 0

    r = run(tmp_path, "approve", stdin=subprocess.DEVNULL)
    assert r.returncode == 1
    assert "identity" in r.stderr and "--by" in r.stderr
    assert state(tmp_path)["approved"] is False


def test_ship_approve_requires_identity_without_tty(tmp_path):
    ready_project(tmp_path)
    r = run(tmp_path, "ship-approve", stdin=subprocess.DEVNULL)
    assert r.returncode == 1
    assert "identity" in r.stderr and "--by" in r.stderr
    assert state(tmp_path)["ship_approved"] is False


def test_approve_with_by_records_automation_provenance(tmp_path):
    ready_project(tmp_path)
    record = state(tmp_path)["approval"]
    assert record["by"] == "test"
    assert record["via"] == "automation"
    assert isinstance(record["revision"], int) and record["revision"] >= 1
    assert record["at"]
    assert record["target"]["parts"]["mission_id"] == state(tmp_path)["mission_id"]


def test_interactive_approve_records_os_user(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Objective").returncode == 0

    master, slave = os.openpty()
    try:
        r = subprocess.run([str(CLI), "approve"], cwd=str(tmp_path), text=True,
                           capture_output=True, stdin=slave)
    finally:
        os.close(slave)
        os.close(master)
    assert r.returncode == 0, r.stderr
    record = state(tmp_path)["approval"]
    assert record["via"] == "interactive"
    assert record["by"] == getpass.getuser()


def test_tampered_approval_record_blocks_start(tmp_path):
    ready_project(tmp_path)
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data["approval"].pop("by")
    path.write_text(json.dumps(data, indent=2) + "\n")

    r = run(tmp_path, "start", "UNIT-001")
    assert r.returncode == 1
    assert "approval record" in r.stderr
    assert state(tmp_path)["status"] == "ready"


def test_status_reports_effective_approval_flags(tmp_path):
    ready_project(tmp_path)
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data["approval"].pop("by")
    path.write_text(json.dumps(data, indent=2) + "\n")

    r = run(tmp_path, "status")
    assert r.returncode == 0
    shown = json.loads(r.stdout.split("\navailable:")[0])
    assert shown["approved"] is False
    assert "note:" in r.stderr and "approval record" in r.stderr


# --- BUG-03: ship target binding -----------------------------------------

def git(tmp_path, *args):
    return subprocess.run(["git", "-C", str(tmp_path), *args],
                          capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_ship_approval_survives_state_persistence_in_git_repo(tmp_path):
    """The anti-cycle: ship-approve writes state; that must not self-invalidate."""
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")

    ready_project(tmp_path)
    git(tmp_path, "add", "-A")
    assert git(tmp_path, "commit", "-m", "base").returncode == 0

    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    # state.json is tracked and dirty after the approval write...
    status = git(tmp_path, "status", "--porcelain").stdout
    assert ".juicer/state.json" in status
    # ...but a follow-up state write must keep the approval.
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    r = run(tmp_path, "status")
    shown = json.loads(r.stdout.split("\navailable:")[0])
    assert shown["ship_approved"] is True


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_ship_approval_invalidated_by_new_commit(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")

    ready_project(tmp_path)
    (tmp_path / "app.py").write_text("print('v1')\n")
    git(tmp_path, "add", "-A")
    assert git(tmp_path, "commit", "-m", "v1").returncode == 0

    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    (tmp_path / "app.py").write_text("print('v2')\n")
    assert git(tmp_path, "commit", "-am", "v2").returncode == 0

    # any subsequent state write eagerly re-validates the target
    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["ship_approved"] is False
    r = run(tmp_path, "status")
    shown = json.loads(r.stdout.split("\navailable:")[0])
    assert shown["ship_approved"] is False


def test_ship_approval_invalidated_by_plan_edit(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    plan = tmp_path / ".juicer" / "plan.md"
    plan.write_text(plan.read_text() + "\n- extra step\n")

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["ship_approved"] is False


def test_ship_requires_valid_plan_approval(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Objective").returncode == 0
    # status=planning: ship-approve must fail on the state gate first
    r = run(tmp_path, "ship-approve", "--by=test")
    assert r.returncode == 1
    assert "Cannot ship-approve" in r.stderr

    # approved flag forged without a record: ship must refuse
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data["status"] = "ready"
    data["approved"] = True
    path.write_text(json.dumps(data, indent=2) + "\n")
    r = run(tmp_path, "ship-approve", "--by=test")
    assert r.returncode == 1
    assert "approval record is missing or invalid" in r.stderr
    assert state(tmp_path)["ship_approved"] is False


# --- M-06: mission and state move together ---------------------------------

def test_mission_write_failure_leaves_state_unchanged(tmp_path):
    """The mission file and the state describing it are written under one lock.

    Writing state first and mission second would let a reader holding the
    lock observe new state with an old mission — or persist new state
    when the mission write was refused.
    """
    assert run(tmp_path, "init").returncode == 0
    cli = load_cli("juicer_cli_m06")
    cli.bind_root(tmp_path)
    state_before = (tmp_path / ".juicer" / "state.json").read_bytes()
    mission_before = (tmp_path / ".juicer" / "mission.md").read_bytes()

    def explode(path, text):
        raise OSError("simulated disk failure")

    cli._atomic_write_text = explode
    with pytest.raises(OSError):
        cli.cmd_mission(argparse.Namespace(objective="New objective"))

    assert (tmp_path / ".juicer" / "state.json").read_bytes() == state_before
    assert (tmp_path / ".juicer" / "mission.md").read_bytes() == mission_before


def test_mission_writes_both_files_in_one_lock(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    cli = load_cli("juicer_cli_m06b")
    cli.bind_root(tmp_path)
    depth = {"seen": -1}

    original = cli._fenced_write
    def spy(state):
        depth["seen"] = cli._lock_depth
        return original(state)
    cli._fenced_write = spy

    cli.cmd_mission(argparse.Namespace(objective="Locked mission"))
    assert depth["seen"] == 1, "state was written outside the lock"
    assert "Locked mission" in (tmp_path / ".juicer" / "mission.md").read_text()


# --- Release ordering: build/package < ship-approve < publish/release ------

def _git_repo(tmp_path, *committed):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    ready_project(tmp_path)
    for name in committed:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("payload\n")
    git(tmp_path, "add", "-A")
    assert git(tmp_path, "commit", "-m", "base").returncode == 0


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_artifact_built_before_approval_survives_state_writes(tmp_path):
    """The canonical order works: build/package runs before ship-approve."""
    _git_repo(tmp_path)

    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "app.tgz").write_text("payload\n")

    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["ship_approved"] is True
    r = run(tmp_path, "status")
    assert "ship_approved invalidated" not in r.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_artifact_built_after_approval_invalidates_it(tmp_path):
    """The inverted order fails: the artifact leaves the approved target."""
    _git_repo(tmp_path)

    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "app.tgz").write_text("payload\n")

    r = run(tmp_path, "status")
    assert "ship_approved invalidated" in r.stderr
    shown = json.loads(r.stdout.split("\navailable:")[0])
    assert shown["ship_approved"] is False

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["ship_approved"] is False


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_gitignored_artifact_is_outside_the_ship_binding(tmp_path):
    """Ignored paths are not in `git status --porcelain`, so they never bind."""
    _git_repo(tmp_path)
    (tmp_path / ".gitignore").write_text("dist/\n")
    git(tmp_path, "add", "-A")
    assert git(tmp_path, "commit", "-m", "ignore dist").returncode == 0

    assert run(tmp_path, "ship-approve", "--by=test").returncode == 0
    assert state(tmp_path)["ship_approved"] is True

    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "app.tgz").write_text("payload\n")
    assert "app.tgz" not in git(tmp_path, "status", "--porcelain").stdout

    assert run(tmp_path, "checkpoint", "ready").returncode == 0
    assert state(tmp_path)["ship_approved"] is True
