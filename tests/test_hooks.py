"""`juicer hooks install|uninstall|status`: guard lifecycle.

Uninstall removes only the marked block: foreign hook content and its
executable bit survive, and `core.hooksPath` stays untouched throughout.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
GUARD_BEGIN = "# >>> juicer-kit git guard >>>"

pytestmark = pytest.mark.skipif(shutil.which("git") is None,
                                reason="git not available")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), text=True,
                          capture_output=True, env={**os.environ})


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True)


def git_repo(root, *init_args):
    assert git(root, "init", "-b", "main").returncode == 0
    assert git(root, "config", "user.email", "t@example.com").returncode == 0
    assert git(root, "config", "user.name", "Test").returncode == 0
    r = run(root, "init", *init_args)
    assert r.returncode == 0, r.stderr
    return r


def hook(root):
    return root / ".git" / "hooks" / "pre-commit"


def test_hooks_install_creates_the_guard(tmp_path):
    git_repo(tmp_path, "--no-git-guard")
    r = run(tmp_path, "hooks", "install")
    assert r.returncode == 0, r.stderr
    assert "git guard: installed" in r.stdout
    assert GUARD_BEGIN in hook(tmp_path).read_text()
    assert os.access(hook(tmp_path), os.X_OK)


def test_hooks_status_walks_the_lifecycle(tmp_path):
    git_repo(tmp_path, "--no-git-guard")
    r = run(tmp_path, "hooks", "status")
    assert r.returncode == 0
    assert "git guard: not installed" in r.stdout
    assert "core.hooksPath: unset" in r.stdout

    assert run(tmp_path, "hooks", "install").returncode == 0
    r = run(tmp_path, "hooks", "status")
    assert "git guard: installed" in r.stdout
    assert str(hook(tmp_path)) in r.stdout

    assert run(tmp_path, "hooks", "uninstall").returncode == 0
    assert "git guard: not installed" in run(tmp_path, "hooks", "status").stdout


def test_hooks_uninstall_deletes_a_guard_only_hook(tmp_path):
    git_repo(tmp_path)  # init installs the guard by default
    assert hook(tmp_path).exists()
    r = run(tmp_path, "hooks", "uninstall")
    assert r.returncode == 0, r.stderr
    assert "had only the guard" in r.stdout
    assert not hook(tmp_path).exists()


def test_hooks_uninstall_preserves_foreign_content_and_mode(tmp_path):
    git_repo(tmp_path, "--no-git-guard")
    existing = hook(tmp_path)
    existing.write_text("#!/bin/sh\necho user-hook-ran\n")
    existing.chmod(0o755)
    assert run(tmp_path, "hooks", "install").returncode == 0
    r = run(tmp_path, "hooks", "uninstall")
    assert r.returncode == 0, r.stderr
    assert "content preserved" in r.stdout
    text = existing.read_text()
    assert "echo user-hook-ran" in text
    assert GUARD_BEGIN not in text
    assert os.access(existing, os.X_OK)
    # without the guard, the foreign hook alone gates a commit on main
    (tmp_path / "file.txt").write_text("x\n")
    git(tmp_path, "add", "-A")
    c = git(tmp_path, "commit", "-m", "change")
    assert c.returncode == 0, c.stdout + c.stderr
    assert "user-hook-ran" in (c.stdout + c.stderr)


def test_hooks_uninstall_without_guard_is_a_noop(tmp_path):
    git_repo(tmp_path, "--no-git-guard")
    r = run(tmp_path, "hooks", "uninstall")
    assert r.returncode == 0
    assert "nothing removed" in r.stdout


def test_hooks_install_is_idempotent(tmp_path):
    git_repo(tmp_path, "--no-git-guard")
    assert run(tmp_path, "hooks", "install").returncode == 0
    r = run(tmp_path, "hooks", "install")
    assert r.returncode == 0
    assert "unchanged" in r.stdout
    assert hook(tmp_path).read_text().count(GUARD_BEGIN) == 1


def test_hooks_install_requires_a_git_work_tree(tmp_path):
    assert run(tmp_path, "init", "--no-git-guard").returncode == 0
    r = run(tmp_path, "hooks", "install")
    assert r.returncode == 1
    assert "could not install" in r.stderr
    r = run(tmp_path, "hooks", "status")
    assert r.returncode == 0
    assert "not a git repository" in r.stdout
