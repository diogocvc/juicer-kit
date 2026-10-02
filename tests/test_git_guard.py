"""Git guard: direct commits on main/master are blocked by default.

Covers the approved escape hatches (`--no-verify`, `JUICER_NO_GIT_GUARD`,
`juicer init --no-git-guard`), hook chaining with preservation of foreign
content, and the never-`core.hooksPath` rule.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
GUARD_BEGIN = "# >>> juicer-kit git guard >>>"

pytestmark = pytest.mark.skipif(shutil.which("git") is None,
                                reason="git not available")


def git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=str(cwd), text=True,
                          capture_output=True,
                          env={**os.environ, **(env or {})})


def run(cwd, *args, env=None):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True,
                          env={**os.environ, **(env or {})})


def guarded_project(root, *init_args):
    assert git(root, "init", "-b", "main").returncode == 0
    assert git(root, "config", "user.email", "t@example.com").returncode == 0
    assert git(root, "config", "user.name", "Test").returncode == 0
    r = run(root, "init", *init_args)
    assert r.returncode == 0, r.stderr
    return r


def commit(root, message="change", env=None):
    (root / "file.txt").write_text("content\n")
    assert git(root, "add", "-A").returncode == 0
    return git(root, "commit", "-m", message, env=env)


def hook(root):
    return root / ".git" / "hooks" / "pre-commit"


def test_init_installs_guard_and_never_sets_hooks_path(tmp_path):
    r = guarded_project(tmp_path)
    text = hook(tmp_path).read_text()
    assert GUARD_BEGIN in text
    assert os.access(hook(tmp_path), os.X_OK)
    assert "git guard: installed" in r.stdout
    assert git(tmp_path, "config", "--get", "core.hooksPath").returncode != 0


def test_guard_blocks_commit_on_main(tmp_path):
    guarded_project(tmp_path)
    r = commit(tmp_path)
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "refusing to commit directly on branch main" in combined
    assert git(tmp_path, "rev-parse", "--verify", "HEAD").returncode != 0


def test_guard_allows_commit_on_a_branch(tmp_path):
    guarded_project(tmp_path)
    assert git(tmp_path, "checkout", "-b", "feature").returncode == 0
    assert commit(tmp_path).returncode == 0


def test_guard_env_escape(tmp_path):
    guarded_project(tmp_path)
    r = commit(tmp_path, env={"JUICER_NO_GIT_GUARD": "1"})
    assert r.returncode == 0, r.stdout + r.stderr


def test_guard_no_verify_escape(tmp_path):
    guarded_project(tmp_path)
    (tmp_path / "file.txt").write_text("content\n")
    git(tmp_path, "add", "-A")
    r = git(tmp_path, "commit", "--no-verify", "-m", "bypass")
    assert r.returncode == 0, r.stdout + r.stderr


def test_init_no_git_guard_skips_install(tmp_path):
    r = guarded_project(tmp_path, "--no-git-guard")
    assert not hook(tmp_path).exists()
    assert "git guard" not in r.stdout


def test_existing_foreign_hook_is_preserved_and_runs_first(tmp_path):
    assert git(tmp_path, "init", "-b", "main").returncode == 0
    assert git(tmp_path, "config", "user.email", "t@example.com").returncode == 0
    assert git(tmp_path, "config", "user.name", "Test").returncode == 0
    existing = hook(tmp_path)
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("#!/bin/sh\necho user-hook-ran\n")
    existing.chmod(0o755)
    assert run(tmp_path, "init").returncode == 0
    text = existing.read_text()
    assert "echo user-hook-ran" in text
    assert GUARD_BEGIN in text
    assert text.index("echo user-hook-ran") < text.index(GUARD_BEGIN)
    (tmp_path / "file.txt").write_text("x\n")
    git(tmp_path, "add", "-A")
    r = git(tmp_path, "commit", "-m", "change")
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "user-hook-ran" in combined, "foreign hook must still run"
    assert "refusing to commit" in combined


def test_init_is_idempotent_for_the_guard_block(tmp_path):
    guarded_project(tmp_path)
    first = hook(tmp_path).read_bytes()
    r = run(tmp_path, "init")
    assert r.returncode == 0, r.stderr
    assert hook(tmp_path).read_bytes() == first
    assert hook(tmp_path).read_text().count(GUARD_BEGIN) == 1


def test_reinit_refreshes_a_stale_guard_block(tmp_path):
    guarded_project(tmp_path)
    text = hook(tmp_path).read_text()
    hook(tmp_path).write_text(text.replace("JUICER_NO_GIT_GUARD",
                                           "TAMPERED_GUARD"))
    assert run(tmp_path, "init").returncode == 0
    refreshed = hook(tmp_path).read_text()
    assert "TAMPERED_GUARD" not in refreshed
    assert "JUICER_NO_GIT_GUARD" in refreshed
    assert refreshed.count(GUARD_BEGIN) == 1


def test_guard_blocks_master_branch_too(tmp_path):
    assert git(tmp_path, "init", "-b", "master").returncode == 0
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / "file.txt").write_text("x\n")
    git(tmp_path, "add", "-A")
    r = git(tmp_path, "commit", "-m", "change")
    assert r.returncode != 0
    assert "branch master" in (r.stdout + r.stderr)


def test_non_git_init_installs_nothing(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert not (tmp_path / ".git").exists()
