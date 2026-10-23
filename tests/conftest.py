"""Shared fixtures: temp git repos and fake executors."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from juicer.orchestrator import Juicer  # noqa: E402


def git(args, cwd):
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "juicer-test")
    env.setdefault("GIT_AUTHOR_EMAIL", "juicer-test@example.com")
    env.setdefault("GIT_COMMITTER_NAME", "juicer-test")
    env.setdefault("GIT_COMMITTER_EMAIL", "juicer-test@example.com")
    subprocess.run(["git"] + args, cwd=str(cwd), check=True, capture_output=True, text=True, env=env)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(["init", "-b", "main"], r)
    (r / "README.md").write_text("# demo\n", encoding="utf-8")
    (r / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(["add", "-A"], r)
    git(["commit", "-m", "baseline"], r)
    return r


@pytest.fixture
def juicer(repo):
    j = Juicer(repo)
    j.init()
    j.set_mission(
        title="Demo mission",
        objective="Deliver a verified increment",
        acceptance_criteria=[
            {"id": "AC-001", "description": "tests pass", "verification": "automated_test", "required": True},
        ],
    )
    return j


def fake_ok_executor(write_files=None, note="done"):
    """Executor double: writes files into the workspace and reports success."""

    def run(prompt, cwd, agent, timeout):
        for rel, content in (write_files or {}).items():
            path = Path(cwd) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return {"ok": True, "status": "PASS", "exit_code": 0, "detail": note,
                "session_id": "ses_fake", "output": "fake ok: %s" % note}

    return run


def fake_fail_executor(detail="boom"):
    def run(prompt, cwd, agent, timeout):
        return {"ok": False, "status": "FAIL", "exit_code": 1, "detail": detail,
                "session_id": "ses_fail", "output": detail}

    return run


def simple_task_specs(*ids, deps=None):
    deps = deps or {}
    specs = []
    for tid in ids:
        specs.append({
            "id": tid,
            "title": "Task %s" % tid,
            "description": "Implement %s" % tid,
            "depends_on": deps.get(tid, []),
            "acceptance_criteria": [
                {"id": "AC-1", "description": "works", "verification": "automated_test", "required": True}
            ],
            "scope": {"paths": [], "constraints": []},
            "approval_policy": {"human_approval_required": False, "required_gates": ["verification"]},
            "agent": "coder",
            "checks": [{"id": "py-ok", "command": [sys.executable, "-c", "print('ok')"], "required": True}],
        })
    return specs
