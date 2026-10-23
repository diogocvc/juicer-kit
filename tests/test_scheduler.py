"""Scheduler releases only eligible tasks and records serialization reasons."""

from juicer.scheduler import RunOutcome, Scheduler


def task(tid, status="ready", deps=None):
    return {"id": tid, "status": status, "depends_on": deps or [], "title": tid,
            "description": "d"}


def test_plan_splits_eligible_and_blocked():
    tasks = [task("T1"), task("T2", deps=["T1"]), task("T3", deps=["T1", "T2"])]
    sched = Scheduler()
    eligible, blocked = sched.plan(tasks)
    assert [t["id"] for t in eligible] == ["T1"]
    assert blocked == {"T2": "waiting on T1", "T3": "waiting on T1, T2"}


def test_dispatch_runs_only_eligible():
    tasks = [task("T1"), task("T2", deps=["T1"])]
    ran = []

    def runner(t):
        ran.append(t["id"])
        return RunOutcome(task_id=t["id"], ok=True)

    out = Scheduler().dispatch(tasks, runner)
    assert ran == ["T1"]
    by_id = {o.task_id: o for o in out}
    assert by_id["T1"].ok is True
    assert "waiting on T1" in by_id["T2"].detail


def test_dispatch_serial_when_one_job_records_reason():
    tasks = [task("T1"), task("T2")]
    out = Scheduler(max_jobs=1).dispatch(tasks, lambda t: RunOutcome(task_id=t["id"], ok=True))
    assert all(o.ok for o in out)


def test_dispatch_parallel_runs_independent_tasks():
    tasks = [task("T1"), task("T2"), task("T3")]
    ran = []

    def runner(t):
        ran.append(t["id"])
        return RunOutcome(task_id=t["id"], ok=True)

    out = Scheduler(max_jobs=3).dispatch(tasks, runner, max_jobs=3)
    assert sorted(ran) == ["T1", "T2", "T3"]
    assert len(out) == 3


def test_dispatch_forced_serial_records_reason():
    tasks = [task("T1"), task("T2")]
    out = Scheduler(max_jobs=2).dispatch(
        tasks, lambda t: RunOutcome(task_id=t["id"], ok=True),
        force_serial_reason="worktrees unavailable")
    reasons = {o.task_id: o.serialized_reason for o in out}
    assert reasons == {"T1": "worktrees unavailable", "T2": "worktrees unavailable"}


def test_runner_exception_becomes_failed_outcome():
    tasks = [task("T1")]

    def runner(t):
        raise RuntimeError("executor crashed")

    out = Scheduler().dispatch(tasks, runner)
    assert out[0].ok is False
    assert "executor crashed" in out[0].detail
