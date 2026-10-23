"""Scheduler: release eligible tasks, run serial or in parallel.

Parallelism is real (thread pool over independent executor calls, each in its
own worktree/branch). When the environment or graph forces serialization the
scheduler records the reason instead of simulating parallelism.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .graph import eligible_tasks


@dataclass
class RunOutcome:
    task_id: str
    ok: bool
    detail: str = ""
    error: Optional[str] = None
    serialized_reason: Optional[str] = None
    data: dict = field(default_factory=dict)


class Scheduler:
    def __init__(self, max_jobs: int = 1):
        self.max_jobs = max(1, int(max_jobs))

    def plan(self, tasks, status_of=None):
        """Return (eligible, blocked) where blocked maps id -> reason."""
        eligible = eligible_tasks(tasks, status_of=status_of)
        status_of = status_of or (lambda t: t["status"])
        by_id = {t["id"]: t for t in tasks}
        blocked = {}
        for t in tasks:
            if t["status"] != "ready" or t in eligible:
                continue
            missing = [d for d in t.get("depends_on", []) if status_of(by_id[d]) != "done"]
            blocked[t["id"]] = "waiting on %s" % ", ".join(sorted(missing))
        return eligible, blocked

    def dispatch(self, tasks, runner: Callable[[dict], RunOutcome], max_jobs=None,
                 status_of=None, force_serial_reason: Optional[str] = None):
        """Run every currently eligible task.

        *runner* executes one task (workspace isolation is its responsibility).
        Returns list of RunOutcome. Never parallelizes tasks that are not
        currently eligible together.
        """
        jobs = self.max_jobs if max_jobs is None else max(1, int(max_jobs))
        eligible, blocked = self.plan(tasks, status_of=status_of)
        outcomes: List[RunOutcome] = []
        for tid, reason in sorted(blocked.items()):
            outcomes.append(RunOutcome(task_id=tid, ok=False, detail=reason))
        if not eligible:
            return outcomes
        if jobs == 1 or force_serial_reason or len(eligible) == 1:
            reason = force_serial_reason if jobs > 1 or force_serial_reason else None
            for t in eligible:
                try:
                    out = runner(t)
                except Exception as exc:  # noqa: BLE001 - surface as task failure
                    out = RunOutcome(task_id=t["id"], ok=False, error=traceback.format_exc(),
                                     detail=str(exc))
                if reason:
                    out.serialized_reason = reason
                outcomes.append(out)
            return outcomes
        with ThreadPoolExecutor(max_workers=min(jobs, len(eligible))) as pool:
            futures = {}
            for t in eligible:
                futures[pool.submit(runner, t)] = t["id"]
            for fut in as_completed(futures):
                tid = futures[fut]
                try:
                    outcomes.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    outcomes.append(RunOutcome(task_id=tid, ok=False,
                                               error=traceback.format_exc(), detail=str(exc)))
        return outcomes
