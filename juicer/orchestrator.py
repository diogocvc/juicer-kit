"""Mission orchestrator: the vertical MVP flow end to end.

Sequence: mission -> inspect -> decompose -> run (isolated) -> checks ->
review gate -> explicit integrate -> post-merge checks -> done, with
checkpoint/resume throughout. Executor and harness are injectable so tests
run with fakes while production uses the installed OpenCode binary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List, Optional

from . import checks as checks_mod
from . import gitops
from .errors import GateBlockedError, JuicerError, ScopeViolationError, ValidationError
from .gates import evaluate_gate, latest_by_check_id, require_gate
from .graph import detect_cycle, eligible_tasks, topo_waves
from .model import (
    new_execution, new_mission, new_task, validate_execution, validate_mission,
    validate_task,
)
from .scheduler import RunOutcome, Scheduler
from .state import (
    append_event, atomic_write_text, ensure_dir, fenced_update, read_events,
    read_json, state_lock, utc_now, write_json,
)

DEFAULT_CONFIG = {
    "schema_version": 1,
    "harness": "opencode",
    "agent_default": "coder",
    "max_jobs": 1,
    "worktree_root": ".juicer/worktrees",
    "checks": [
        {"id": "tests", "command": ["python3", "-m", "pytest", "-q", "tests"], "required": True}
    ],
}


class Juicer:
    def __init__(self, root: Path, config_path: Optional[Path] = None,
                 executor: Optional[Callable[..., dict]] = None):
        self.root = Path(root).resolve()
        self.jdir = self.root / ".juicer"
        self.config_path = Path(config_path) if config_path else self.jdir / "config.json"
        self.tasks_dir = self.jdir / "tasks"
        self.executions_dir = self.jdir / "executions"
        self.checks_dir = self.jdir / "checks"
        self.evidence_dir = self.jdir / "evidence"
        self.events_path = self.jdir / "events.jsonl"
        self.checkpoints_dir = self.jdir / "checkpoints"
        self.mission_path = self.jdir / "mission.json"
        self._executor = executor

    # ---------- setup ----------

    def init(self, force: bool = False) -> dict:
        ensure_dir(self.jdir)
        ensure_dir(self.tasks_dir)
        ensure_dir(self.executions_dir)
        ensure_dir(self.checks_dir)
        ensure_dir(self.evidence_dir)
        ensure_dir(self.checkpoints_dir)
        if self.config_path.exists() and not force:
            cfg = read_json(self.config_path)
        else:
            cfg = dict(DEFAULT_CONFIG)
            write_json(self.config_path, cfg)
        gitignore = self.jdir / ".gitignore"
        if not gitignore.exists():
            atomic_write_text(
                gitignore,
                "worktrees/\nevidence/\nexecutions/\nchecks/\ncheckpoints/\nevents.jsonl\n*.lock\n",
            )
        self._event("init", data={"kit": "4.0.0", "root": str(self.root)})
        return cfg

    def config(self) -> dict:
        cfg = read_json(self.config_path, default=None)
        if cfg is None:
            raise JuicerError("juicer not initialized here; run `juicer init` first")
        return cfg

    def _event(self, etype: str, task_id=None, execution_id=None, data=None, outcome=None):
        append_event(self.events_path, {
            "schema_version": 1,
            "type": etype,
            "task_id": task_id,
            "execution_id": execution_id,
            "occurred_at": utc_now(),
            "outcome": outcome,
            "data": data or {},
        })

    # ---------- mission ----------

    def set_mission(self, title: str, objective: str, scope=None, constraints=None,
                    acceptance_criteria=None, gaps=None, force: bool = False) -> dict:
        if self.mission_path.exists() and not force:
            raise JuicerError("mission already exists; pass force=True/--force to replace "
                              "(approved missions are never overwritten silently)")
        gaps = list(gaps or [])
        criteria = list(acceptance_criteria or [])
        status = "waiting_human" if gaps or not objective else "ready"
        doc = new_mission(
            "MISSION-001", title, objective, scope=scope, constraints=constraints,
            acceptance_criteria=criteria, gaps=gaps, status=status,
        )
        write_json(self.mission_path, doc)
        self._event("mission_set", data={"status": status, "gaps": len(gaps)}, outcome=status)
        return doc

    def resolve_gap(self, gap_id: str, resolution: str) -> dict:
        def mut(doc):
            found = False
            for gap in doc.get("gaps", []):
                if gap.get("id") == gap_id:
                    gap["resolution"] = resolution
                    gap["resolved_at"] = utc_now()
                    found = True
            if not found:
                raise JuicerError("unknown gap %s" % gap_id)
            if all(g.get("resolution") for g in doc.get("gaps", [])):
                doc["status"] = "ready"
        doc = fenced_update(self.mission_path, mut, create=None)
        self._event("gap_resolved", data={"gap_id": gap_id}, outcome=doc["status"])
        return doc

    def mission(self) -> Optional[dict]:
        return read_json(self.mission_path, default=None)

    def require_ready_mission(self) -> dict:
        mission = self.mission()
        if mission is None:
            raise JuicerError("no mission; run `juicer mission` first")
        if mission["status"] == "waiting_human":
            pending = [g["id"] for g in mission.get("gaps", []) if not g.get("resolution")]
            raise GateBlockedError(
                "mission waiting on human input: %s" % ", ".join(pending),
                gate_status="BLOCKED",
            )
        return mission

    # ---------- inspect ----------

    def inspect(self) -> dict:
        branch = gitops.current_branch(self.root)
        commit = gitops.head_commit(self.root)
        dirty = gitops.is_dirty(self.root)
        evidence = {
            "recorded_at": utc_now(),
            "root": str(self.root),
            "git": {
                "branch": branch,
                "head_commit": commit,
                "dirty": dirty,
                "porcelain": gitops.status_porcelain(self.root)[:50],
            },
            "files_top": sorted(p.name for p in self.root.iterdir())[:50],
        }
        try:
            from .harness import opencode as oc
            evidence["harness"] = oc.discover()
        except Exception as exc:  # noqa: BLE001 - inspection must not crash
            evidence["harness"] = {"status": "unsupported", "detail": str(exc)}
        path = self.evidence_dir / "inspect.json"
        write_json(path, evidence)
        self._event("inspect", data={"branch": branch, "commit": commit, "dirty": dirty})
        return evidence

    # ---------- decompose ----------

    def add_tasks(self, task_specs: List[dict]) -> List[dict]:
        mission = self.require_ready_mission()
        existing = {t["id"]: t for t in self.load_tasks()}
        candidates = dict(existing)
        made = []
        for spec in task_specs:
            tid = spec.get("id")
            if not tid:
                raise ValidationError(["task spec missing id"])
            if tid in candidates:
                raise ValidationError(["duplicate task id %s" % tid])
            task = new_task(
                tid, mission["id"], spec.get("title", ""), spec.get("description", ""),
                depends_on=spec.get("depends_on", []),
                acceptance_criteria=spec.get("acceptance_criteria", []),
                scope=spec.get("scope"),
                approval_policy=spec.get("approval_policy"),
                agent=spec.get("agent", self.config().get("agent_default", "coder")),
                checks=spec.get("checks", []),
            )
            candidates[tid] = task
            made.append(task)
        cycle = detect_cycle(list(candidates.values()))
        if cycle:
            raise ValidationError(["dependency cycle: %s" % " -> ".join(cycle)])
        topo_waves(list(candidates.values()))
        with state_lock(self.jdir, "tasks"):
            for task in made:
                write_json(self.tasks_dir / ("%s.json" % task["id"]), task)
        for task in made:
            self._event("task_added", task_id=task["id"],
                        data={"depends_on": task["depends_on"]})
        return made

    def load_tasks(self) -> List[dict]:
        if not self.tasks_dir.exists():
            return []
        out = []
        for path in sorted(self.tasks_dir.glob("*.json")):
            out.append(read_json(path))
        return out

    def load_task(self, task_id: str) -> dict:
        path = self.tasks_dir / ("%s.json" % task_id)
        doc = read_json(path, default=None)
        if doc is None:
            raise JuicerError("unknown task %s" % task_id)
        return doc

    def _update_task(self, task_id: str, mutator) -> dict:
        path = self.tasks_dir / ("%s.json" % task_id)
        with state_lock(self.jdir, "tasks"):
            def wrapped(cur):
                before = dict(cur)
                mutator(cur)
                cur["revision"] = before["revision"]
            doc = fenced_update(path, wrapped)
        validate_task(doc)
        return doc

    # ---------- status ----------

    def status(self) -> dict:
        mission = self.mission()
        tasks = self.load_tasks()
        eligible = [t["id"] for t in eligible_tasks(tasks)]
        by_id = {t["id"]: t for t in tasks}
        waiting = {}
        for t in tasks:
            if t["status"] == "ready" and t["id"] not in eligible:
                missing = [d for d in t["depends_on"] if by_id[d]["status"] != "done"]
                waiting[t["id"]] = missing
        next_action = self._next_action(mission, tasks, eligible)
        return {
            "mission": mission,
            "tasks": [{"id": t["id"], "title": t["title"], "status": t["status"],
                       "depends_on": t["depends_on"], "attempt_count": t["attempt_count"],
                       "current_execution_id": t["current_execution_id"]} for t in tasks],
            "eligible": eligible,
            "waiting": waiting,
            "next_action": next_action,
        }

    def _next_action(self, mission, tasks, eligible) -> str:
        if mission is None:
            return "create a mission (juicer mission)"
        if mission["status"] == "waiting_human":
            pending = [g["id"] for g in mission.get("gaps", []) if not g.get("resolution")]
            return "human input required for gaps: %s" % ", ".join(pending)
        if not tasks:
            return "decompose the mission into tasks (juicer decompose tasks.json)"
        if eligible:
            return "run eligible tasks: %s" % ", ".join(eligible)
        completed = [t for t in tasks if t["status"] == "completed"]
        if completed:
            return "review and integrate: %s" % ", ".join(t["id"] for t in completed)
        failed = [t for t in tasks if t["status"] == "failed"]
        if failed:
            return "investigate failures: %s" % ", ".join(t["id"] for t in failed)
        blocked = [t for t in tasks if t["status"] == "blocked"]
        if blocked:
            return "resolve blocks: %s" % ", ".join(t["id"] for t in blocked)
        if all(t["status"] == "done" for t in tasks):
            return "all tasks done; mission complete"
        return "waiting on dependencies"

    # ---------- execution ----------

    def _resolve_executor(self):
        if self._executor is not None:
            return self._executor
        from .harness import opencode as oc

        def run(prompt, cwd, agent, timeout):
            return oc.execute(prompt, cwd, agent=agent, timeout=timeout)
        return run

    def run_task(self, task_id: str, parallel: bool = False) -> RunOutcome:
        """Execute one eligible task in an isolated worktree."""
        task = self.load_task(task_id)
        tasks = self.load_tasks()
        if task["status"] != "ready":
            return RunOutcome(task_id=task_id, ok=False,
                              detail="task is %s, not ready" % task["status"])
        eligible_ids = {t["id"] for t in eligible_tasks(tasks)}
        if task_id not in eligible_ids:
            by_id = {t["id"]: t for t in tasks}
            missing = [d for d in task["depends_on"] if by_id[d]["status"] != "done"]
            return RunOutcome(task_id=task_id, ok=False,
                              detail="dependencies not done: %s" % ", ".join(missing))
        mission = self.require_ready_mission()
        cfg = self.config()

        branch = "juicer/%s" % task_id
        wt_root = self.root / cfg.get("worktree_root", ".juicer/worktrees")
        worktree = wt_root / task_id
        base_commit = gitops.head_commit(self.root)
        execution = new_execution(
            "RUN-PLACEHOLDER", task_id,
            worker={"id": "local", "harness": cfg.get("harness", "opencode")},
            workspace={"branch": branch, "base_commit": base_commit,
                       "worktree": str(worktree)},
        )
        exec_id = self._new_execution_id(task_id, execution)

        if worktree.exists():
            gitops.remove_worktree(self.root, worktree, force=True)
        ensure_dir(wt_root)
        gitops.create_worktree(self.root, branch, worktree, base=base_commit, new_branch=True)

        self._update_task(task_id, lambda t: t.update(
            status="in_progress", current_execution_id=exec_id))
        self._update_execution(exec_id, lambda e: e.update(
            status="running", started_at=utc_now()))
        self._event("task_started", task_id=task_id, execution_id=exec_id,
                    data={"branch": branch, "base_commit": base_commit})

        prompt = self._build_prompt(task, mission)
        agent = task.get("agent") or cfg.get("agent_default", "coder")
        executor = self._resolve_executor()
        try:
            outcome = executor(prompt, worktree, agent, 900)
        except Exception as exc:  # noqa: BLE001 - captured as task failure
            outcome = {"ok": False, "status": "FAIL", "exit_code": None,
                       "detail": str(exc), "session_id": None, "output": ""}

        evidence_path = self.evidence_dir / ("%s.output.txt" % exec_id)
        atomic_write_text(evidence_path, outcome.get("output") or outcome.get("detail") or "")
        diff = gitops.diff_stat(worktree)
        changed = gitops.changed_files(worktree)
        commit = None
        if outcome.get("ok") and changed:
            try:
                self._check_scope(task, changed)
                commit = gitops.commit_all(
                    worktree, "%s: %s" % (task_id, task["title"]))
            except (ScopeViolationError, gitops.GitError) as exc:
                outcome = {"ok": False, "status": "FAIL", "exit_code": None,
                           "detail": "scope/commit failure: %s" % exc,
                           "session_id": outcome.get("session_id"), "output": outcome.get("output", "")}
        elif outcome.get("ok") and not changed:
            # No code change: still a valid outcome for analysis tasks.
            commit = gitops.head_commit(worktree)

        check_results = self._run_task_checks(task, worktree, commit)

        result = {
            "execution_id": exec_id,
            "exit_code": outcome.get("exit_code"),
            "session_id": outcome.get("session_id"),
            "status": outcome.get("status"),
            "detail": outcome.get("detail"),
            "evidence_ref": str(evidence_path),
            "branch": branch,
            "base_commit": base_commit,
            "commit": commit,
            "diff_stat": diff,
            "changed_files": changed,
            "checks": check_results,
        }
        if outcome.get("ok"):
            self._update_task(task_id, lambda t: t.update(
                status="completed", result=result,
                attempt_count=t["attempt_count"] + 1))
            self._update_execution(exec_id, lambda e: e.update(
                status="succeeded", finished_at=utc_now(), result=result))
            self._event("task_completed", task_id=task_id, execution_id=exec_id,
                        data={"commit": commit, "checks": [c["status"] for c in check_results]},
                        outcome="completed")
            return RunOutcome(task_id=task_id, ok=True, detail=outcome.get("detail", ""),
                              data=result)
        else:
            self._update_task(task_id, lambda t: t.update(
                status="failed", result=result,
                attempt_count=t["attempt_count"] + 1))
            self._update_execution(exec_id, lambda e: e.update(
                status="failed", finished_at=utc_now(),
                failure={"detail": outcome.get("detail"), "exit_code": outcome.get("exit_code")}))
            self._event("task_failed", task_id=task_id, execution_id=exec_id,
                        data={"detail": outcome.get("detail")}, outcome="failed")
            return RunOutcome(task_id=task_id, ok=False, detail=outcome.get("detail", ""),
                              data=result)

    def _new_execution_id(self, task_id: str, execution: dict) -> str:
        from .model import new_run_id
        exec_id = new_run_id()
        execution["id"] = exec_id
        validate_execution(execution)
        write_json(self.executions_dir / ("%s.json" % exec_id), execution)
        return exec_id

    def _update_execution(self, exec_id: str, mutator) -> dict:
        path = self.executions_dir / ("%s.json" % exec_id)
        with state_lock(self.jdir, "executions"):
            return fenced_update(path, mutator)

    def load_execution(self, exec_id: str) -> dict:
        doc = read_json(self.executions_dir / ("%s.json" % exec_id), default=None)
        if doc is None:
            raise JuicerError("unknown execution %s" % exec_id)
        return doc

    def _check_scope(self, task: dict, changed_files: List[str]) -> None:
        paths = (task.get("scope") or {}).get("paths") or []
        if not paths:
            return
        import fnmatch
        for f in changed_files:
            if not any(fnmatch.fnmatch(f, pat) or f.startswith(pat.rstrip("*").rstrip("/"))
                       for pat in paths):
                raise ScopeViolationError(
                    "task %s changed file outside scope: %s (scope: %s)"
                    % (task["id"], f, paths))

    def _build_prompt(self, task: dict, mission: dict) -> str:
        lines = [
            "Mission: %s" % mission.get("title", ""),
            "Task %s: %s" % (task["id"], task["title"]),
            "",
            task.get("description", ""),
            "",
            "Acceptance criteria:",
        ]
        for c in task.get("acceptance_criteria", []):
            lines.append("- [%s] %s" % (c.get("id"), c.get("description")))
        scope = task.get("scope") or {}
        if scope.get("paths"):
            lines.append("")
            lines.append("Scope (only change files matching): %s" % ", ".join(scope["paths"]))
        for constraint in scope.get("constraints", []):
            lines.append("Constraint: %s" % constraint)
        lines.append("")
        lines.append("Work only inside the current directory. Do not commit; the coordinator captures evidence.")
        return "\n".join(lines)

    def retry_task(self, task_id: str) -> dict:
        task = self.load_task(task_id)
        if task["status"] != "failed":
            raise JuicerError("only failed tasks can be retried (task is %s)" % task["status"])
        doc = self._update_task(task_id, lambda t: t.update(status="ready"))
        self._event("task_retried", task_id=task_id)
        return doc

    # ---------- integration ----------

    def integrate(self, task_id: str, approve: bool = False,
                  allow_dirty: bool = False) -> dict:
        """Review + gate + explicit merge + post-merge checks."""
        task = self.load_task(task_id)
        if task["status"] != "completed":
            raise GateBlockedError("task %s is %s; only completed tasks integrate"
                                   % (task_id, task["status"]))
        result = task.get("result") or {}
        commit = result.get("commit")
        all_results = self._load_check_results(task_id)
        latest = latest_by_check_id(
            [r for r in all_results if r.get("phase") == "pre_merge"])
        required_ids = self._required_check_ids(task)
        required = [latest.get(cid, {"check_id": cid, "status": "NOT RUN"})
                    for cid in required_ids]
        gate = evaluate_gate(required, commit=commit)
        require_gate(gate["status"], "integration of %s" % task_id)

        policy = task.get("approval_policy") or {}
        if policy.get("human_approval_required") and not approve:
            raise GateBlockedError(
                "human approval required for %s; re-run with --approve after review"
                % task_id, gate_status="BLOCKED")

        if gitops.is_dirty(self.root, exclude=(".juicer",)) and not allow_dirty:
            raise GateBlockedError(
                "integration target has uncommitted changes; commit/stash first "
                "(never overwrite pre-existing changes)", gate_status="BLOCKED")

        branch = result.get("branch")
        ok, detail = gitops.merge_no_ff(self.root, branch)
        if not ok:
            self._update_task(task_id, lambda t: t.update(status="blocked"))
            self._event("integration_conflict", task_id=task_id,
                        data={"detail": detail}, outcome="conflict")
            raise GateBlockedError("merge conflict for %s: %s" % (task_id, detail))

        merged_commit = gitops.head_commit(self.root)
        post = self._run_task_checks(task, self.root, merged_commit,
                                     phase="post_merge")
        post_gate = evaluate_gate(
            [latest_by_check_id(post).get(cid, {"check_id": cid, "status": "NOT RUN"})
             for cid in required_ids], commit=merged_commit)
        integration = {
            "task_id": task_id,
            "branch": branch,
            "merged_commit": merged_commit,
            "pre_merge_gate": gate,
            "post_merge_gate": post_gate,
            "approved": bool(approve or not policy.get("human_approval_required")),
            "integrated_at": utc_now(),
        }
        write_json(self.jdir / ("integration-%s.json" % task_id), integration)
        if post_gate["status"] != "PASS":
            self._event("integration_post_failed", task_id=task_id,
                        data=integration, outcome="FAIL")
            raise GateBlockedError(
                "post-merge checks %s on %s; investigate before proceeding"
                % (post_gate["status"], merged_commit), gate_status=post_gate["status"])
        self._update_task(task_id, lambda t: t.update(status="done"))
        self._event("task_integrated", task_id=task_id, data=integration, outcome="PASS")
        return integration

    def _required_check_ids(self, task: dict) -> List[str]:
        cfg = self.config()
        specs = task.get("checks") or cfg.get("checks", [])
        return [s["id"] for s in specs if s.get("required", True)]

    def _run_task_checks(self, task, cwd, commit, phase="pre_merge"):
        cfg = self.config()
        specs = task.get("checks") or cfg.get("checks", [])
        log_dir = self.checks_dir / task["id"]
        results = checks_mod.run_checks(
            specs, task["id"], cwd, commit=commit, log_dir=log_dir, phase=phase)
        store = self.checks_dir / (task["id"] + ".results.jsonl")
        ensure_dir(store.parent)
        with open(store, "a", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
        for r in results:
            self._event("check_recorded", task_id=task["id"], data=r, outcome=r["status"])
        return results

    def _load_check_results(self, task_id: str) -> List[dict]:
        store = self.checks_dir / (task_id + ".results.jsonl")
        if not store.exists():
            return []
        out = []
        with open(store, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    # ---------- scheduler ----------

    def run_eligible(self, max_jobs: Optional[int] = None,
                     force_serial_reason: Optional[str] = None) -> List[RunOutcome]:
        cfg = self.config()
        jobs = max_jobs if max_jobs is not None else int(cfg.get("max_jobs", 1))
        tasks = self.load_tasks()
        sched = Scheduler(max_jobs=jobs)
        return sched.dispatch(tasks, runner=lambda t: self.run_task(t["id"], parallel=jobs > 1),
                              max_jobs=jobs, force_serial_reason=force_serial_reason)

    # ---------- checkpoint / resume ----------

    def checkpoint(self, note: str = "") -> dict:
        tasks = self.load_tasks()
        mission = self.mission()
        commit = gitops.head_commit(self.root)
        cp = {
            "schema_version": 1,
            "created_at": utc_now(),
            "note": note,
            "mission": mission,
            "tasks": {t["id"]: {"status": t["status"], "revision": t["revision"],
                                "current_execution_id": t["current_execution_id"]}
                      for t in tasks},
            "git_head": commit,
            "next_action": self._next_action(mission, tasks,
                                             [t["id"] for t in eligible_tasks(tasks)]),
        }
        name = "cp-%s.json" % utc_now().replace(":", "").replace("-", "")
        write_json(self.checkpoints_dir / name, cp)
        self._event("checkpoint", data={"file": name, "next_action": cp["next_action"]})
        return cp

    def resume(self) -> dict:
        """Reconcile state after restart; never trusts conversation history."""
        self.config()  # ensure initialized
        tasks = self.load_tasks()
        recovered = []
        for t in tasks:
            if t["status"] == "in_progress":
                # Interrupted run: mark failed so it can be retried explicitly.
                self._update_task(t["id"], lambda task: task.update(status="failed"))
                recovered.append(t["id"])
                self._event("resume_recovered", task_id=t["id"],
                            data={"from": "in_progress", "to": "failed"},
                            outcome="recovered")
        status = self.status()
        return {"recovered": recovered, "status": status}

    # ---------- events ----------

    def events(self, limit: int = 50) -> List[dict]:
        return read_events(self.events_path)[-limit:]
