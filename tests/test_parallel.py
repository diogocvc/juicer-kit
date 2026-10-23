"""Two independent tasks execute in isolated worktrees, including in parallel."""

import time
from pathlib import Path

from conftest import simple_task_specs
from juicer import gitops


def test_two_independent_tasks_use_separate_worktrees_and_branches(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002"))
    juicer._executor = fake_writing_executor()
    out1 = juicer.run_task("TASK-001")
    out2 = juicer.run_task("TASK-002")
    assert out1.ok and out2.ok
    r1 = juicer.load_task("TASK-001")["result"]
    r2 = juicer.load_task("TASK-002")["result"]
    assert r1["branch"] == "juicer/TASK-001"
    assert r2["branch"] == "juicer/TASK-002"
    assert r1["branch"] != r2["branch"]
    assert "only-1.txt" in r1["changed_files"]
    assert "only-2.txt" in r2["changed_files"]
    assert "only-2.txt" not in r1["changed_files"]
    assert "only-1.txt" not in r2["changed_files"]
    # each worktree is a real git worktree of this repo
    worktrees = gitops.git(["worktree", "list"], juicer.root).stdout
    assert "TASK-001" in worktrees and "TASK-002" in worktrees


def fake_writing_executor(delay=0.0):
    def run(prompt, cwd, agent, timeout):
        if delay:
            time.sleep(delay)
        marker = "only-%s.txt" % ("1" if "TASK-001" in prompt else "2")
        (Path(cwd) / marker).write_text("content %s\n" % marker, encoding="utf-8")
        return {"ok": True, "status": "PASS", "exit_code": 0, "detail": "ok",
                "session_id": "ses_par", "output": "done"}
    return run


def test_parallel_dispatch_runs_both_independently(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002"))
    juicer._executor = fake_writing_executor(delay=1.0)
    start = time.time()
    outcomes = juicer.run_eligible(max_jobs=2)
    elapsed = time.time() - start
    assert sorted(o.task_id for o in outcomes) == ["TASK-001", "TASK-002"]
    assert all(o.ok for o in outcomes)
    # real parallelism: wall clock clearly below the serial sum (2.0s+);
    # git worktree setup is inherently serialized, so the margin accounts for it
    assert elapsed < 1.6, "expected concurrent execution, took %.2fs" % elapsed
    t1 = juicer.load_task("TASK-001")
    t2 = juicer.load_task("TASK-002")
    assert t1["status"] == t2["status"] == "completed"
    assert t1["result"]["branch"] != t2["result"]["branch"]


def test_serial_fallback_when_env_cannot_isolate(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002"))
    juicer._executor = fake_writing_executor()
    outcomes = juicer.run_eligible(max_jobs=2, force_serial_reason="worktrees unsupported here")
    assert all(o.ok for o in outcomes)
    assert all(o.serialized_reason == "worktrees unsupported here" for o in outcomes)
