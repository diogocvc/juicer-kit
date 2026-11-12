"""Mission orchestrator: the vertical MVP flow end to end.

Sequence: mission -> inspect -> decompose -> run (isolated) -> checks ->
review gate -> explicit integrate -> post-merge checks -> done, with
checkpoint/resume throughout. The executor is injectable for tests; production
uses the installed OpenCode V2 binary through the harness contract.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Callable, List, Optional

from . import approval as approval_mod
from . import checks as checks_mod
from . import evidence as evidence_mod
from . import gitops
from . import scope as scope_mod
from .errors import GateBlockedError, JuicerError, ScopeViolationError, ValidationError
from .gates import CHECK_STATUSES, WORST, evaluate_gate, latest_by_check_id, require_gate
from .graph import detect_cycle, eligible_tasks, topo_waves
from .model import (
    EXECUTION_TRANSITIONS, GATE_NAMES, TASK_TRANSITIONS, check_transition,
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

# Core-triggered review/security: the agent answers with one fenced JSON block.
# Prose outside it is ignored; the core validates the structure and records the
# evidence artifact itself (agents never write evidence directly).
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```",
                            re.DOTALL | re.IGNORECASE)

_AGENT_JSON_CONTRACT = """Respond with EXACTLY one fenced json block and no other text:

```json
{{"verdict": "PASS", "findings": [{{"severity": "medium", "description": "...", "file": "...", "line": 0}}], "summary": "..."}}
```

Rules:
- "verdict" must be "PASS" or "FAIL".
- finding "severity" must be one of: critical, high, medium, low.
- any critical finding means the verdict is FAIL.
- do not edit files and do not run shell commands.
- anything outside the json block is ignored and cannot be evidence.
"""

_REVIEW_AGENT_PROMPT = """You are @reviewer, the existing code review subagent of this project.
Review the change below for quality, correctness, tests and regressions.

Task: {task_id} — {title}
Description: {description}
Commit: {commit}
Changed files: {files}

Read the changed files in the current workspace before deciding.
""" + _AGENT_JSON_CONTRACT

_SECURITY_AGENT_PROMPT = """You are @security, the existing security audit subagent of this project.
Audit the change below for vulnerabilities (OWASP Top 10), secrets, auth, data handling and external integrations.

Task: {task_id} — {title}
Description: {description}
Commit: {commit}
Changed files: {files}

Read the changed files in the current workspace before deciding. Reference OWASP when applicable.
""" + _AGENT_JSON_CONTRACT


def extract_structured_evidence(text: str) -> Optional[dict]:
    """Extract the structured evidence object from an agent answer.

    Accepts one fenced JSON block (last valid one wins) or a bare JSON object.
    Returns ``None`` when the output is prose or malformed; prose never becomes
    evidence.
    """
    for raw in reversed(_JSON_FENCE_RE.findall(text or "")):
        try:
            doc = json.loads(raw)
        except ValueError:
            continue
        if isinstance(doc, dict) and "verdict" in doc:
            return doc
    stripped = (text or "").strip()
    if stripped.startswith("{"):
        try:
            doc = json.loads(stripped)
        except ValueError:
            return None
        if isinstance(doc, dict) and "verdict" in doc:
            return doc
    return None


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
                "worktrees/\nevidence/\napprovals/\nexecutions/\nchecks/\ncheckpoints/\nevents.jsonl\n*.lock\n",
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
                allow_agent_commits=spec.get("allow_agent_commits", False),
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
                before_status = cur.get("status")
                mutator(cur)
                after_status = cur.get("status")
                if after_status != before_status:
                    check_transition("task", before_status, after_status,
                                     TASK_TRANSITIONS)
                # Keep the pre-mutation revision so fenced_update bumps once
                # under the lock (single-writer local model).
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
        in_progress = [t for t in tasks if t["status"] == "in_progress"]
        if in_progress:
            return "resume in-progress tasks: %s" % ", ".join(
                t["id"] for t in in_progress)
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

        harness = oc.OpenCodeHarness()

        def run(prompt, cwd, agent, timeout):
            request = oc.ExecutionRequest(
                prompt=prompt, cwd=Path(cwd), agent=agent, timeout=timeout,
            )
            result = harness.run(request)
            data = result.to_dict()
            # V2 returns an NDJSON event stream; expose the assistant-visible
            # text separately so evidence parsing never has to unescape events.
            parsed = oc.parse_run_output(result.output or "")
            data["agent_output"] = parsed.get("text") or ""
            return data
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
        wt_root = self.root / cfg.get("worktree_root", ".juicer/worktrees")

        branch, worktree = self._attempt_names(task_id, 1)
        base_commit = gitops.head_commit(self.root)
        attempt = self._next_attempt(task)
        if attempt != 1:
            # A retry never reuses the previous branch/worktree: evidence from
            # the previous attempt stays intact and the names cannot collide.
            # Dash (not slash) avoids the git ref file/directory conflict with
            # the previous branch `juicer/<task>`.
            branch, worktree = self._attempt_names(task_id, attempt)

        # AC6 (TASK-007): preserve the previous attempt before anything is
        # removed, even though retries now use distinct names. The previous
        # attempt is taken from attempt history/execution; the canonical path
        # is only a fallback for legacy state without a recorded attempt.
        previous = self._previous_attempt(task)
        if previous:
            prev_worktree = (Path(previous["worktree"])
                             if previous.get("worktree") else None)
            self._preserve_attempt_if_any(
                task_id, prev_worktree, previous.get("branch"),
                previous.get("base_commit") or base_commit)
        else:
            legacy_branch, legacy_worktree = self._attempt_names(task_id, 1)
            self._preserve_attempt_if_any(task_id, legacy_worktree,
                                          legacy_branch, base_commit)

        execution = new_execution(
            "RUN-PLACEHOLDER", task_id,
            worker={"id": "local", "harness": cfg.get("harness", "opencode")},
            workspace={"branch": branch, "base_commit": base_commit,
                       "worktree": str(worktree), "agent_head_commit": None,
                       "head_commit": None, "tree_hash": None},
        )
        execution["attempt"] = attempt
        exec_id = self._new_execution_id(task_id, execution)

        self._update_task(task_id, lambda t: t.update(
            status="in_progress", current_execution_id=exec_id))
        self._update_execution(exec_id, lambda e: e.update(
            status="running", started_at=utc_now()))
        try:
            if worktree.exists():
                gitops.remove_worktree(self.root, worktree, force=True)
            ensure_dir(wt_root)
            gitops.create_worktree(self.root, branch, worktree,
                                   base=base_commit, new_branch=True)
        except gitops.GitError as exc:
            # A stale/corrupted worktree must fail cleanly, not leave the task
            # `in_progress` with a dangling `running` execution.
            detail = "worktree setup failed: %s" % exc
            self._update_task(task_id, lambda t: t.update(
                status="failed",
                result={"detail": detail, "branch": branch,
                        "base_commit": base_commit, "workspace_error": True},
                attempt_count=t["attempt_count"] + 1))
            self._update_execution(exec_id, lambda e: e.update(
                status="failed", finished_at=utc_now(),
                failure={"detail": detail, "exit_code": None}))
            self._event("task_failed", task_id=task_id, execution_id=exec_id,
                        data={"detail": detail, "attempt": attempt},
                        outcome="failed")
            return RunOutcome(task_id=task_id, ok=False, detail=detail,
                              data={"branch": branch, "base_commit": base_commit})

        self._event("task_started", task_id=task_id, execution_id=exec_id,
                    data={"branch": branch, "base_commit": base_commit,
                          "attempt": attempt})

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

        # AC1/AC4: sample the agent HEAD before the coordinator commits so an
        # agent-created commit is visible even if another commit is added.
        worktree_ok = gitops.is_worktree_root(worktree)
        agent_head = gitops.head_commit(worktree) if worktree_ok else None
        agent_committed = bool(base_commit and agent_head and agent_head != base_commit)

        # AC10: a deleted/corrupted worktree must fail closed, never be
        # recorded as a successful run without a commit.
        if outcome.get("ok") and not worktree_ok:
            outcome = {
                "ok": False, "status": "FAIL", "exit_code": outcome.get("exit_code"),
                "detail": "worktree %s is missing or not a git repository after "
                          "the agent run; refusing to record evidence"
                          % worktree,
                "session_id": outcome.get("session_id"),
                "output": outcome.get("output", ""),
            }

        if worktree_ok:
            # Intent-to-add makes untracked content visible in the diff/stat
            # evidence; commit_all() stages everything afterwards anyway.
            gitops.intent_to_add(worktree)
        diff = gitops.diff_stat(worktree, base=base_commit) if worktree_ok else ""
        changed = (gitops.changed_files(worktree, base=base_commit)
                   if worktree_ok else [])
        touched: List[str] = []
        commit = None

        if outcome.get("ok") and agent_committed and not scope_mod.agent_commits_allowed(task, cfg):
            outcome = {
                "ok": False, "status": "FAIL", "exit_code": outcome.get("exit_code"),
                "detail": "agent created commit(s) (HEAD %s != base %s); commits by "
                          "the agent are forbidden unless the task policy allows "
                          "them" % (agent_head, base_commit),
                "session_id": outcome.get("session_id"),
                "output": outcome.get("output", ""),
            }

        if outcome.get("ok"):
            coordinator_commit = None
            try:
                # Stage first and validate the exact index that would be
                # committed: a violation never creates a real commit on the
                # task branch. `changed_in_range` also covers intermediate
                # commits (a protected file added and later deleted is still
                # part of the merge history).
                gitops.stage_all(worktree)
                staged = gitops.staged_changed(worktree, base_commit)
                final_changed = gitops.changed_files(worktree, base=base_commit)
                history = (gitops.changed_in_range(worktree, base_commit, agent_head)
                           if agent_committed else [])
                self._check_scope(task, sorted(set(final_changed) | set(staged)
                                               | set(history)), cfg)
                coordinator_commit = gitops.commit_index(
                    worktree, "%s: %s" % (task_id, task["title"]))
                final_head = gitops.head_commit(worktree) or agent_head
                if coordinator_commit:
                    # A commit landing between the agent_head sample and the
                    # coordinator commit would become its parent: that is an
                    # agent-made commit even though HEAD is ours.
                    if gitops.parent_commit(worktree, coordinator_commit) != agent_head:
                        agent_committed = True
                if final_head != (coordinator_commit or agent_head):
                    agent_committed = True
                if agent_committed and not scope_mod.agent_commits_allowed(task, cfg):
                    raise ScopeViolationError(
                        "agent created commit(s) (HEAD %s != base %s); "
                        "commits by the agent are forbidden unless the task "
                        "policy allows them" % (final_head, base_commit))
                # Post-commit guard: the branch may have moved while committing.
                touched = gitops.changed_in_range(worktree, base_commit, final_head)
                self._check_scope(task, sorted(set(touched) | set(final_changed)), cfg)
                changed = final_changed
                commit = final_head
            except (ScopeViolationError, gitops.GitError) as exc:
                # Never leave a coordinator-created commit with rejected
                # content pinned on the task branch.
                if coordinator_commit:
                    gitops.reset_soft(worktree, agent_head)
                outcome = {"ok": False, "status": "FAIL", "exit_code": None,
                           "detail": "scope/commit failure: %s" % exc,
                           "session_id": outcome.get("session_id"),
                           "output": outcome.get("output", "")}

        final_head = gitops.head_commit(worktree) if worktree_ok else agent_head
        tree_hash = gitops.tree_hash(worktree, commit) if commit else None

        check_results = self._run_task_checks(task, worktree, commit) if worktree_ok else []

        no_changes = bool(commit and base_commit and commit == base_commit)
        workspace_state = {
            "branch": branch,
            "base_commit": base_commit,
            "worktree": str(worktree),
            "agent_head_commit": agent_head,
            "head_commit": final_head,
            "tree_hash": tree_hash,
            "touched_files": touched,
            "no_changes": no_changes,
        }
        result = {
            "execution_id": exec_id,
            "attempt": attempt,
            "exit_code": outcome.get("exit_code"),
            "session_id": outcome.get("session_id"),
            "status": outcome.get("status"),
            "detail": outcome.get("detail"),
            "evidence_ref": str(evidence_path),
            "branch": branch,
            "base_commit": base_commit,
            "agent_head_commit": agent_head,
            "head_commit": final_head,
            "tree_hash": tree_hash,
            "commit": commit,
            "no_changes": no_changes,
            "diff_stat": diff,
            "changed_files": changed,
            "touched_files": touched,
            "agent_committed": agent_committed,
            "checks": check_results,
        }
        if outcome.get("ok"):
            self._update_task(task_id, lambda t: t.update(
                status="completed", result=result,
                attempt_count=t["attempt_count"] + 1))
            self._update_execution(exec_id, lambda e: e.update(
                status="succeeded", finished_at=utc_now(), result=result,
                workspace={**e.get("workspace", {}), **workspace_state}))
            self._event("task_completed", task_id=task_id, execution_id=exec_id,
                        data={"commit": commit, "head_commit": final_head,
                              "tree_hash": tree_hash, "attempt": attempt,
                              "checks": [c["status"] for c in check_results]},
                        outcome="completed")
            return RunOutcome(task_id=task_id, ok=True, detail=outcome.get("detail", ""),
                              data=result)
        else:
            self._update_task(task_id, lambda t: t.update(
                status="failed", result=result,
                attempt_count=t["attempt_count"] + 1))
            self._update_execution(exec_id, lambda e: e.update(
                status="failed", finished_at=utc_now(),
                result=result,
                failure={"detail": outcome.get("detail"), "exit_code": outcome.get("exit_code")},
                workspace={**e.get("workspace", {}), **workspace_state}))
            self._event("task_failed", task_id=task_id, execution_id=exec_id,
                        data={"detail": outcome.get("detail"),
                              "head_commit": final_head, "tree_hash": tree_hash,
                              "attempt": attempt},
                        outcome="failed")
            return RunOutcome(task_id=task_id, ok=False, detail=outcome.get("detail", ""),
                              data=result)

    def _new_execution_id(self, task_id: str, execution: dict) -> str:
        from .model import new_run_id
        exec_id = new_run_id()
        execution["id"] = exec_id
        validate_execution(execution)
        write_json(self.executions_dir / ("%s.json" % exec_id), execution)
        return exec_id

    def _attempt_names(self, task_id: str, attempt: int):
        """Canonical branch/worktree names for an attempt (single source)."""
        cfg = self.config()
        wt_root = self.root / cfg.get("worktree_root", ".juicer/worktrees")
        if attempt == 1:
            return "juicer/%s" % task_id, wt_root / task_id
        return ("juicer/%s-attempt-%d" % (task_id, attempt),
                wt_root / ("%s-attempt-%d" % (task_id, attempt)))

    def _next_attempt(self, task: dict) -> int:
        """Return a collision-free attempt number for a new run.

        ``attempt_count`` only advances on terminal runs, so an interrupted
        attempt (resumed from a stale ``in_progress`` state) would otherwise
        reuse the previous branch/worktree name. The attempt history is also
        considered, and existing branches/worktrees are skipped defensively.
        """
        task_id = task["id"]
        attempt = int(task.get("attempt_count", 0) or 0) + 1
        # History can advance the attempt beyond attempt_count (an interrupted
        # run never reached a terminal path), so honor the highest recorded
        # attempt as well.
        for entry in task.get("attempt_history") or []:
            recorded = entry.get("attempt")
            if isinstance(recorded, int) and recorded >= attempt:
                attempt = recorded + 1
        while True:
            branch, worktree = self._attempt_names(task_id, attempt)
            valid_worktree = (worktree.exists()
                              and gitops.is_worktree_root(worktree))
            if (not gitops.branch_exists(self.root, branch)
                    and not valid_worktree):
                return attempt
            attempt += 1

    def _attempt_belongs_to_task(self, task_id: str, entry: dict) -> bool:
        """Reject history/execution records that belong to another task."""
        branch = entry.get("branch")
        if branch and not (branch == "juicer/%s" % task_id
                           or branch.startswith("juicer/%s-attempt-" % task_id)):
            return False
        worktree = entry.get("worktree")
        if worktree:
            name = Path(worktree).name
            if name != task_id and not name.startswith(task_id + "-attempt-"):
                return False
        return True

    def _previous_attempt(self, task: dict) -> Optional[dict]:
        """Locate the previous attempt (history entry or current execution)."""
        for entry in reversed(task.get("attempt_history") or []):
            if not self._attempt_belongs_to_task(task["id"], entry):
                continue
            if entry.get("worktree") or entry.get("branch"):
                return entry
        exec_id = task.get("current_execution_id")
        if not exec_id:
            return None
        try:
            execution = self.load_execution(exec_id)
        except JuicerError:
            return None
        if execution.get("task_id") != task["id"]:
            return None
        workspace = execution.get("workspace") or {}
        result = execution.get("result") or {}
        return {
            "execution_id": exec_id,
            "worktree": workspace.get("worktree"),
            "branch": workspace.get("branch") or result.get("branch"),
            "commit": result.get("commit"),
            "base_commit": workspace.get("base_commit") or result.get("base_commit"),
        }

    def _preserve_attempt_if_any(self, task_id: str,
                                 worktree: Optional[Path], branch: Optional[str],
                                 base_commit: Optional[str]) -> Optional[dict]:
        """Preserve *worktree*/*branch* only when the attempt actually exists."""
        worktree_exists = bool(worktree and worktree.exists())
        branch_exists = bool(branch and gitops.branch_exists(self.root, branch))
        if not worktree_exists and not branch_exists:
            return None
        return self._preserve_prior_attempt(task_id, worktree, branch,
                                            base_commit)

    def _preserve_prior_attempt(self, task_id: str, worktree: Optional[Path],
                                branch: Optional[str],
                                base_commit: Optional[str]) -> dict:
        """Record a previous worktree/branch as evidence before removing it.

        AC6: the core must never delete a worktree or branch before the
        previous attempt is auditable. The record captures HEAD/tree, dirty
        state, changed files, an uncommitted patch (including untracked files)
        and a durable ref to the branch tip, so nothing is orphaned for GC.
        """
        stamp = uuid.uuid4().hex[:12]
        worktree_exists = bool(worktree and worktree.exists())
        record = {
            "schema_version": 1,
            "type": "preserved_attempt",
            "task_id": task_id,
            "recorded_at": utc_now(),
            "branch": branch,
            "base_commit": base_commit,
            "worktree": str(worktree) if worktree else None,
            "worktree_exists": worktree_exists,
        }
        if worktree_exists:
            record["worktree_valid"] = gitops.is_worktree_root(worktree)
        if worktree_exists and record["worktree_valid"]:
            record["head_commit"] = gitops.head_commit(worktree)
            record["tree_hash"] = gitops.tree_hash(worktree)
            record["dirty"] = gitops.is_dirty(worktree)
            record["diff_stat"] = gitops.diff_stat(worktree)
            record["changed_files"] = gitops.changed_files(worktree)
            # intent-to-add makes untracked content visible to `git diff`, so
            # the patch is real evidence instead of a list of names.
            gitops.intent_to_add(worktree)
            patch_path = self.evidence_dir / task_id / ("preserved-%s.diff" % stamp)
            atomic_write_text(patch_path, gitops.diff_against(worktree, "HEAD"))
            record["diff_ref"] = str(patch_path)
        # Anchor the tip so `git gc` cannot orphan the previous attempt. The
        # branch may be unavailable (e.g. resume recorded only a worktree), in
        # which case the worktree HEAD is still a valid anchor.
        tip = None
        if branch and gitops.branch_exists(self.root, branch):
            tip = gitops.branch_tip(self.root, branch)
        elif worktree_exists and record.get("worktree_valid"):
            tip = record.get("head_commit")
        if tip:
            record["branch_tip"] = tip
            ref = "refs/juicer/attempts/%s/%s" % (task_id, stamp)
            if gitops.update_ref(self.root, ref, tip):
                record["preserved_ref"] = ref
            else:
                # Fail closed: keep the SHA and surface the degraded state
                # rather than silently relying on GC eligibility.
                record["preserved_ref_error"] = ref
        path = self.evidence_dir / task_id / ("preserved-%s.json" % stamp)
        write_json(path, record)
        if record.get("preserved_ref_error"):
            self._event(
                "attempt_preservation_degraded", task_id=task_id,
                data={"artifact_ref": str(path), "branch_tip": tip,
                      "ref": record["preserved_ref_error"]},
                outcome="degraded")
        self._event("attempt_preserved", task_id=task_id,
                    data={"artifact_ref": str(path),
                          "branch_tip": record.get("branch_tip"),
                          "preserved_ref": record.get("preserved_ref"),
                          "head_commit": record.get("head_commit")},
                    outcome="preserved")
        return record

    def _update_execution(self, exec_id: str, mutator) -> dict:
        path = self.executions_dir / ("%s.json" % exec_id)
        with state_lock(self.jdir, "executions"):
            def wrapped(cur):
                before_status = cur.get("status")
                mutator(cur)
                after_status = cur.get("status")
                if after_status != before_status:
                    check_transition("execution", before_status, after_status,
                                     EXECUTION_TRANSITIONS)
            return fenced_update(path, wrapped)

    def load_execution(self, exec_id: str) -> dict:
        doc = read_json(self.executions_dir / ("%s.json" % exec_id), default=None)
        if doc is None:
            raise JuicerError("unknown execution %s" % exec_id)
        return doc

    def _check_scope(self, task: dict, changed_files: List[str],
                     config: Optional[dict] = None) -> None:
        # AC3: protected paths are always enforced, even when no scope is
        # declared and regardless of the harness permission policy.
        scope_mod.check_protected(task, changed_files, config)
        paths = (task.get("scope") or {}).get("paths") or []
        if not paths:
            return
        # M-3: prefix matches respect path boundaries so "src/" never matches
        # "srcx/evil.py".
        for f in changed_files:
            if not any(scope_mod.path_matches(f, pat, basename=False) for pat in paths):
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
        """Explicit retry: failed or blocked -> ready, preserving history."""
        task = self.load_task(task_id)
        if task["status"] not in ("failed", "blocked"):
            raise JuicerError(
                "only failed or blocked tasks can be retried (task is %s)"
                % task["status"])
        prev_exec_id = task.get("current_execution_id")
        prev_workspace = {}
        prev_attempt = None
        if prev_exec_id:
            try:
                prev_execution = self.load_execution(prev_exec_id)
            except JuicerError:
                prev_execution = {}
            if prev_execution.get("task_id") != task_id:
                # A dangling/foreign pointer must not leak another task's
                # branch, commit or attempt number into this history.
                prev_execution = {}
            prev_workspace = prev_execution.get("workspace") or {}
            prev_attempt = prev_execution.get("attempt")
        prev_result = task.get("result") or {}
        history = list(task.get("attempt_history") or [])
        history.append({
            "at": utc_now(),
            "from_status": task["status"],
            "execution_id": prev_exec_id,
            "branch": prev_result.get("branch") or prev_workspace.get("branch"),
            "worktree": prev_workspace.get("worktree"),
            "commit": prev_result.get("commit"),
            "base_commit": (prev_workspace.get("base_commit")
                            or prev_result.get("base_commit")),
            "merged_commit": prev_result.get("merged_commit"),
            "attempt": prev_attempt,
            "blocked_reason": task.get("blocked_reason"),
            "action": "retry",
        })
        prior_status = task["status"]
        doc = self._update_task(task_id, lambda t: t.update(
            status="ready",
            attempt_history=history,
            blocked_reason=None,
            current_execution_id=None,
        ))
        self._event("task_retried", task_id=task_id,
                    data={"from": prior_status, "history_len": len(history),
                          "previous_execution_id": prev_exec_id,
                          "previous_branch": history[-1]["branch"],
                          "previous_worktree": history[-1]["worktree"]},
                    outcome="ready")
        return doc

    # ---------- human approval (plan §7) ----------

    def approve(self, task_id: str, approver: str,
                reason: Optional[str] = None,
                note: Optional[str] = None) -> dict:
        """Record a human approval linked to the task's current commit/tree.

        The core computes commit/tree itself (never taken from the caller or
        from agent text). Anonymous approvers and secret-bearing notes are
        rejected. The record is valid only for this commit: a new commit
        invalidates it.
        """
        # Validate the identity first: an anonymous approver is refused even
        # before looking at the task (fail fast on the input itself).
        approver = approval_mod.validate_approver(approver)
        task = self.load_task(task_id)
        result = task.get("result") or {}
        commit = result.get("commit")
        if not commit:
            raise GateBlockedError(
                "%s has no commit to approve (run the task first); approval "
                "is always linked to a commit" % task_id, gate_status="BLOCKED")
        tree_hash = gitops.tree_hash(self.root, commit)
        if not tree_hash:
            raise GateBlockedError(
                "%s cannot be approved: commit %s has no resolvable tree"
                % (task_id, commit), gate_status="BLOCKED")
        required_by = self._approval_triggers(task)
        path = approval_mod.record_approval(
            self.root, task_id, approver, commit, tree_hash,
            required_by=required_by, reason=reason, note=note)
        doc = approval_mod.load_approval(self.root, task_id)
        self._event("human_approval_recorded", task_id=task_id,
                    data={"approver": doc["approver"], "commit": commit,
                          "tree_hash": tree_hash, "reason": doc.get("reason"),
                          "note": doc.get("note"), "required_by": required_by,
                          "record_ref": str(path)},
                    outcome="PASS")
        return doc

    # ---------- integration ----------

    def integrate(self, task_id: str, approve: bool = False,
                  allow_dirty: bool = False) -> dict:
        """Review + multi-gate + explicit merge + post-merge checks.

        Mandatory gate order (canonical): verification -> review -> security
        (when required) -> approval. NOT RUN never allows merge.

        ``approve=True`` only expresses the explicit merge intent; it never
        substitutes the recorded approval (plan §7): a linked, non-anonymous
        record must exist for this exact commit/tree.
        """
        task = self.load_task(task_id)
        if task["status"] != "completed":
            raise GateBlockedError("task %s is %s; only completed tasks integrate"
                                   % (task_id, task["status"]))
        result = task.get("result") or {}
        commit = result.get("commit")
        branch = result.get("branch")
        base_commit = result.get("base_commit")
        if not commit or not branch:
            # M-1: fail cleanly instead of crashing later in merge/parsing.
            raise GateBlockedError(
                "task %s has no commit/branch in result (result=%s); "
                "re-run the task or restore the execution result before "
                "integrating" % (task_id, sorted(result)), gate_status="BLOCKED")
        # Fail closed: the protected/scope re-check needs a verifiable range.
        # A missing or tampered base_commit must block, never skip the check.
        if not base_commit or not gitops.is_commit(self.root, base_commit):
            raise GateBlockedError(
                "task %s has no verifiable base_commit in result (%r); refusing "
                "to integrate without a diff range"
                % (task_id, base_commit), gate_status="BLOCKED")
        if not gitops.is_commit(self.root, commit):
            raise GateBlockedError(
                "task %s evidences commit %r, which does not resolve; refusing "
                "to integrate" % (task_id, commit), gate_status="BLOCKED")

        # The range must be real: base == commit would silently skip the
        # history re-check, and a non-ancestor base would describe a diff the
        # task never produced. `no_changes` must mean exactly commit == base.
        no_changes = bool(result.get("no_changes"))
        if not gitops.is_ancestor(self.root, base_commit, commit):
            raise GateBlockedError(
                "task %s base_commit %s is not an ancestor of the evidenced "
                "commit %s; refusing to integrate an unverifiable range"
                % (task_id, base_commit, commit), gate_status="BLOCKED")
        if no_changes and commit != base_commit:
            raise GateBlockedError(
                "task %s is marked no_changes but commit %s differs from base %s; "
                "refusing to integrate" % (task_id, commit, base_commit),
                gate_status="BLOCKED")
        if not no_changes and commit == base_commit:
            raise GateBlockedError(
                "task %s evidences no commit beyond base %s; refusing to skip "
                "the history re-check" % (task_id, base_commit),
                gate_status="BLOCKED")
        exec_id = result.get("execution_id")
        if exec_id:
            try:
                execution = self.load_execution(exec_id)
            except JuicerError as exc:
                raise GateBlockedError(
                    "task %s references execution %s that cannot be loaded: %s"
                    % (task_id, exec_id, exc), gate_status="BLOCKED")
            workspace = execution.get("workspace") or {}
            recorded_base = workspace.get("base_commit")
            if recorded_base and recorded_base != base_commit:
                raise GateBlockedError(
                    "task %s base_commit %s disagrees with the execution record "
                    "%s; refusing to integrate" % (task_id, base_commit,
                                                   recorded_base),
                    gate_status="BLOCKED")
            if bool(workspace.get("no_changes")) != no_changes:
                raise GateBlockedError(
                    "task %s no_changes flag disagrees with the execution record; "
                    "refusing to integrate" % task_id, gate_status="BLOCKED")
        tree_hash = gitops.tree_hash(self.root, commit)

        # Branch tip vs evidenced commit: a branch that moved after the run
        # must never merge code the evidence/approval does not cover.
        branch_tip = gitops.branch_tip(self.root, branch)
        if branch_tip != commit:
            raise GateBlockedError(
                "branch %s points at %s, not the evidenced commit %s; refusing "
                "to merge an unevidenced commit" % (branch, branch_tip, commit),
                gate_status="BLOCKED")

        # Protected paths and scope are re-checked over every committed path in
        # base..commit at merge time (intermediate commits included); a
        # tampered or stale result cannot bypass the run-time check.
        try:
            committed_changed = sorted(
                set(gitops.changed_in_range(self.root, base_commit, commit))
                | set(gitops.changed_between(self.root, base_commit, commit)))
            self._check_scope(task, committed_changed, self.config())
        except (ScopeViolationError, gitops.GitError) as exc:
            raise GateBlockedError(
                "integration blocked for %s: %s" % (task_id, exc),
                gate_status="BLOCKED")

        # Human approval record for this commit/tree (plan §7): evaluated once,
        # enforced by the approval gate and by the explicit-merge checks below.
        approval_status, approval_details, approval_record = (
            self._evaluate_approval(task, commit, tree_hash))

        # --- multi-gate evaluation (pre-merge, canonical order) ---
        required_gates = self._required_gates(task, result)
        unknown = [g for g in required_gates if g not in GATE_NAMES]
        if unknown:
            raise GateBlockedError(
                "task %s declares unknown required_gates: %s; refusing to "
                "integrate rather than silently ignoring a gate"
                % (task_id, ", ".join(str(g) for g in unknown)),
                gate_status="BLOCKED")
        gate_results = []
        try:
            for gate_name in self.CANONICAL_GATE_ORDER:
                if gate_name not in required_gates:
                    continue
                if gate_name == "verification":
                    all_results = self._load_check_results(task_id)
                    latest = latest_by_check_id(
                        [r for r in all_results if r.get("phase") == "pre_merge"])
                    required_ids = self._required_check_ids(task)
                    required = [latest.get(cid, {"check_id": cid, "status": "NOT RUN"})
                                for cid in required_ids]
                    vgate = evaluate_gate(required, commit=commit)
                    gate_results.append(("verification", vgate["status"],
                                         vgate["details"]))
                    require_gate(vgate["status"], "verification gate for %s" % task_id)
                elif gate_name == "review":
                    rgate, rdetails = self._evaluate_review_gate(task, commit, tree_hash)
                    gate_results.append(("review", rgate, rdetails))
                    require_gate(rgate, "review gate for %s" % task_id)
                elif gate_name == "security":
                    sgate, sdetails = self._evaluate_security_gate(task, commit, tree_hash)
                    gate_results.append(("security", sgate, sdetails))
                    require_gate(sgate, "security gate for %s" % task_id)
                elif gate_name == "approval":
                    # The gate passes only on a recorded approval linked to
                    # this commit/tree; `--approve` alone never produces PASS.
                    gate_results.append(("approval", approval_status,
                                         approval_details))
                    if approval_status != "PASS":
                        hint = (approval_details or [approval_status])[0]
                        raise GateBlockedError(
                            "approval gate for %s: %s — %s"
                            % (task_id, approval_status, hint),
                            gate_status=approval_status)
            # Acceptance criteria are evaluated last: review/security criteria
            # need the artifacts recorded for this commit. A criterion without
            # valid evidence blocks the merge (plan §6).
            criteria = self._evaluate_criteria(task, commit, tree_hash,
                                               approval_status, approval_details)
            cgate = self._criteria_status(criteria)
            cdetails = ["%s (%s): %s" % (c["id"], c["verification"], c["status"])
                        for c in criteria] or ["no acceptance criteria declared"]
            gate_results.append(("acceptance_criteria", cgate, cdetails))
            self._event("criteria_evaluated", task_id=task_id,
                        data={"status": cgate, "criteria": criteria},
                        outcome=cgate)
            require_gate(cgate, "acceptance criteria for %s" % task_id)
        except GateBlockedError as exc:
            if exc.gate_status == "FAIL":
                # CR-2 invariant: `completed` is never a trap state. A FAIL
                # verdict requires rework, so the task goes to `blocked` with
                # an explicit reason and stays retriable (blocked -> ready).
                reason = "pre-merge gate FAIL during integrate: %s" % exc
                self._update_task(task_id, lambda t: t.update(
                    status="blocked", blocked_reason=reason))
                self._event("integration_gate_failed", task_id=task_id,
                            data={"detail": reason, "gate_status": "FAIL"},
                            outcome="FAIL")
            # BLOCKED/NOT RUN leave the task `completed` on purpose: the
            # missing evidence or approval can be supplied and integrate
            # retried without re-running the task.
            raise

        # Human approval is a separate gate (plan §7), enforced independently
        # of required_gates whenever the policy/risk/criteria require it.
        if approve and approval_status != "PASS":
            raise GateBlockedError(
                "--approve for %s has no valid approval record for this "
                "commit (%s); record it with `juicer approve %s --approver "
                "<name>` — approval is never anonymous or unlinked"
                % (task_id, approval_details[0] if approval_details else
                   approval_status, task_id),
                gate_status=approval_status)
        if self._approval_required(task) and not approve:
            raise GateBlockedError(
                "human approval required for %s; record it with `juicer "
                "approve %s --approver <name>` and re-run with --approve"
                % (task_id, task_id), gate_status="BLOCKED")

        if gitops.is_dirty(self.root, exclude=(".juicer",)) and not allow_dirty:
            raise GateBlockedError(
                "integration target has uncommitted changes; commit/stash first "
                "(never overwrite pre-existing changes)", gate_status="BLOCKED")

        if gitops.is_merging(self.root):
            # Never abort a merge we did not start: another process or a human
            # may be resolving it.
            raise GateBlockedError(
                "a merge is already in progress in %s; resolve or abort it "
                "explicitly before integrating %s"
                % (self.root, task_id), gate_status="BLOCKED")

        ok, detail = gitops.merge_no_ff(self.root, commit)
        if not ok:
            partial = gitops.is_merging(self.root)
            if partial:
                reason = ("merge conflict on %s (%s): %s; abort failed, "
                          "repository is still mid-merge — resolve or run "
                          "`git merge --abort` explicitly"
                          % (commit, branch, detail))
                message = reason
            else:
                reason = ("merge conflict on %s (%s): %s; merge aborted"
                          % (commit, branch, detail))
                message = ("merge conflict for %s: %s; merge aborted, explicit "
                           "intervention required" % (task_id, detail))

            def mark_conflict(task, rsn=reason):
                task["status"] = "blocked"
                task["blocked_reason"] = rsn
            self._update_task(task_id, mark_conflict)
            self._event("integration_conflict", task_id=task_id,
                        data={"detail": detail, "commit": commit,
                              "branch": branch, "partial_merge": partial,
                              "reason": reason},
                        outcome="conflict")
            raise GateBlockedError(message)

        merged_commit = gitops.head_commit(self.root)
        post = self._run_task_checks(task, self.root, merged_commit,
                                     phase="post_merge")
        required_ids = self._required_check_ids(task)
        post_gate = evaluate_gate(
            [latest_by_check_id(post).get(cid, {"check_id": cid, "status": "NOT RUN"})
             for cid in required_ids], commit=merged_commit)
        integration = {
            "task_id": task_id,
            "branch": branch,
            "merged_commit": merged_commit,
            "pre_merge_gate": {"status": "PASS", "details": gate_results},
            "post_merge_gate": post_gate,
            "acceptance_criteria": criteria,
            "approval_required": self._approval_required(task),
            "approved": bool(not self._approval_required(task)
                             or (approve and approval_status == "PASS")),
            "approval": (
                {k: (self._approval_triggers(task) if k == "required_by"
                     else approval_record.get(k))
                 for k in
                 ("approver", "commit", "tree_hash", "approved_at",
                  "reason", "note", "required_by")}
                if approval_record else None),
            "integrated_at": utc_now(),
        }
        write_json(self.jdir / ("integration-%s.json" % task_id), integration)
        if post_gate["status"] != "PASS":
            # Invariant: post-merge failure never leaves completed/done, and
            # the integrated commit is recorded for correction/reversion.
            def mark_post_failure(task, m=merged_commit, pg=post_gate):
                task["status"] = "blocked"
                task["blocked_reason"] = ("post-merge checks %s on %s"
                                          % (pg["status"], m))
                result = dict(task.get("result") or {})
                result["merged_commit"] = m
                result["post_merge_gate"] = pg
                task["result"] = result
            self._update_task(task_id, mark_post_failure)
            self._event("integration_post_failed", task_id=task_id,
                        data=integration, outcome="FAIL")
            raise GateBlockedError(
                "post-merge checks %s on %s; task blocked — investigate before "
                "retrying" % (post_gate["status"], merged_commit),
                gate_status=post_gate["status"])
        # Record the integrated commit on success too, so checkpoints of done
        # tasks carry the merge SHA (not only the pre-merge task commit).
        def mark_integrated(task, m=merged_commit, pg=post_gate,
                            ig=integration):
            result = dict(task.get("result") or {})
            result["merged_commit"] = m
            result["post_merge_gate"] = pg
            result["integrated_at"] = ig["integrated_at"]
            task["status"] = "done"
            task["result"] = result
        self._update_task(task_id, mark_integrated)
        self._event("task_integrated", task_id=task_id, data=integration, outcome="PASS")
        return integration

    # ---------- multi-gates ----------

    CANONICAL_GATE_ORDER = ("verification", "review", "security", "approval")

    def _required_gates(self, task: dict, result: dict) -> List[str]:
        """Gates that must PASS before merge.

        Declared gates come from ``approval_policy.required_gates``. The core
        applies exactly what is declared; it does not add implicit gates.
        Implicit requirements (review for code changes, security for high risk)
        are policy decisions expressed through ``required_gates`` and
        ``risk_level``.
        """
        policy = task.get("approval_policy") or {}
        gates = list(policy.get("required_gates") or ["verification"])
        # Deterministic order; duplicates removed while preserving order.
        seen = set()
        ordered = []
        for name in self.CANONICAL_GATE_ORDER:
            if name in gates and name not in seen:
                ordered.append(name)
                seen.add(name)
        for name in gates:
            if name not in seen:
                ordered.append(name)
                seen.add(name)
        return ordered

    def _evaluate_review_gate(self, task: dict, commit: Optional[str],
                              tree_hash: Optional[str]) -> tuple:
        """Evaluate the review gate for a task/commit.

        Returns (status, details). If review is not declared in required_gates,
        returns PASS. Missing/malformed artifact -> BLOCKED; stale artifact
        (different commit/tree) -> NOT RUN.
        """
        policy = task.get("approval_policy") or {}
        if "review" not in (policy.get("required_gates") or []):
            return "PASS", ["review not required by policy"]
        doc = evidence_mod.load_review(self.root, task["id"], commit)
        return evidence_mod.evaluate_review_artifact(doc, commit, tree_hash or "")

    def _evaluate_security_gate(self, task: dict, commit: Optional[str],
                                tree_hash: Optional[str]) -> tuple:
        """Evaluate the security gate for a task/commit.

        Returns (status, details). If security is not required (not high risk
        and not declared), returns PASS. Missing/malformed artifact ->
        BLOCKED; stale artifact (different commit/tree) -> NOT RUN.
        """
        policy = task.get("approval_policy") or {}
        if policy.get("risk_level") != "high" and "security" not in (
                policy.get("required_gates") or []):
            return "PASS", ["security not required by policy"]
        doc = evidence_mod.load_security(self.root, task["id"], commit)
        return evidence_mod.evaluate_security_artifact(doc, commit, tree_hash or "")

    # ---------- human approval gate (plan §7) ----------

    def _approval_triggers(self, task: dict) -> List[str]:
        """Why human approval is required for this task (audit field)."""
        policy = task.get("approval_policy") or {}
        triggers = []
        if policy.get("human_approval_required"):
            triggers.append("policy:human_approval_required")
        if policy.get("risk_level") == "high":
            triggers.append("policy:risk_level=high")
        if "approval" in (policy.get("required_gates") or []):
            triggers.append("gate:approval")
        for criterion in task.get("acceptance_criteria") or []:
            if criterion.get("verification") == "human":
                triggers.append("criterion:%s" % criterion.get("id"))
        return triggers

    def _approval_required(self, task: dict) -> bool:
        """True when this task cannot merge without recorded human approval."""
        return bool(self._approval_triggers(task))

    def _evaluate_approval(self, task: dict, commit: Optional[str],
                           tree_hash: Optional[str]) -> tuple:
        """Evaluate the human approval record.

        Returns (status, details, record). Missing/malformed -> BLOCKED;
        recorded for another commit/tree -> NOT RUN (new commit invalidates).
        """
        doc = approval_mod.load_approval(self.root, task["id"])
        return approval_mod.evaluate_approval(doc, task["id"], commit or "",
                                              tree_hash or "")

    def _evaluate_criteria(self, task: dict, commit: str, tree_hash: str,
                           approval_status: str,
                           approval_details: Optional[List[str]] = None,
                           ) -> List[dict]:
        """Evaluate acceptance criteria against evidence for *commit*.

        ``approval_status`` is required (fail closed): a caller that forgets
        it must fail to compile, never silently satisfy a ``human`` criterion.

        Each criterion declares its verification form (model-validated):

        - ``check:<id>`` -> deterministic check result for this commit
        - ``review``     -> review artifact linked to commit/tree
        - ``security``   -> security artifact linked to commit/tree
        - ``human``      -> explicit human approval (never inferred)

        Returns one audit record per criterion with PASS/FAIL/BLOCKED/NOT RUN.
        Missing evidence is BLOCKED; evidence for another commit is NOT RUN.
        """
        latest = latest_by_check_id(
            [r for r in self._load_check_results(task["id"])
             if r.get("phase") == "pre_merge"])
        records: List[dict] = []
        for criterion in task.get("acceptance_criteria") or []:
            verification = criterion.get("verification") or ""
            record = {
                "id": criterion["id"],
                "description": criterion.get("description", ""),
                "verification": verification,
                "status": "BLOCKED",
                "details": [],
            }
            if verification.startswith("check:"):
                check_id = verification.split(":", 1)[1]
                result = latest.get(check_id)
                if result is None:
                    record["status"] = "NOT RUN"
                    record["details"] = ["no result for check %s" % check_id]
                elif result.get("commit") not in (None, commit):
                    record["status"] = "NOT RUN"
                    record["details"] = [
                        "stale result for check %s (commit %s)"
                        % (check_id, result.get("commit"))]
                else:
                    status = result.get("status", "NOT RUN")
                    if status not in CHECK_STATUSES:
                        # Same normalization as gates.evaluate_gate: corrupt
                        # stored evidence never counts and never crashes.
                        status = "NOT RUN"
                    record["status"] = status
                    record["details"] = ["check %s: %s"
                                         % (check_id, record["status"])]
                    record["evidence_ref"] = result.get("log_ref")
            elif verification == "review":
                doc = evidence_mod.load_review(self.root, task["id"], commit)
                status, details = evidence_mod.evaluate_review_artifact(
                    doc, commit, tree_hash or "")
                record.update(status=status, details=details)
                if doc is not None:
                    record["evidence_ref"] = doc.get("artifact_ref")
            elif verification == "security":
                doc = evidence_mod.load_security(self.root, task["id"], commit)
                status, details = evidence_mod.evaluate_security_artifact(
                    doc, commit, tree_hash or "")
                record.update(status=status, details=details)
                if doc is not None:
                    record["evidence_ref"] = doc.get("artifact_ref")
            elif verification == "human":
                # Only the recorded approval counts; `--approve` without a
                # commit-linked record stays BLOCKED/NOT RUN here as well.
                record.update(
                    status=approval_status,
                    details=list(approval_details or
                                 ["human approval %s" % approval_status]))
            else:
                # Model validation prevents this; the gate stays fail-closed.
                record["details"] = ["invalid verification %r" % verification]
            records.append(record)
        return records

    @staticmethod
    def _criteria_status(records: List[dict]) -> str:
        """Worst status across criteria; no criteria means PASS."""
        if not records:
            return "PASS"
        return max((r["status"] for r in records),
                   key=lambda status: WORST[status])

    def record_review(self, task_id: str, execution_id: str, commit: str,
                      tree_hash: str, scope: List[str], findings: List[dict],
                      verdict: str, agent: str = "@reviewer",
                      force: bool = False) -> dict:
        """Record a structured review evidence artifact (agent @reviewer)."""
        task = self.load_task(task_id)
        path = evidence_mod.record_review(
            self.root, task_id, execution_id, commit, tree_hash,
            scope, findings, verdict, agent, force=force)
        self._event("evidence_review", task_id=task_id,
                    data={"artifact_ref": str(path), "commit": commit,
                          "verdict": verdict, "forced": bool(force)})
        return {"artifact_ref": str(path), "commit": commit, "verdict": verdict}

    def record_security(self, task_id: str, execution_id: str, commit: str,
                        tree_hash: str, scope: List[str], findings: List[dict],
                        verdict: str, agent: str = "@security",
                        force: bool = False) -> dict:
        """Record a structured security evidence artifact (agent @security)."""
        task = self.load_task(task_id)
        path = evidence_mod.record_security(
            self.root, task_id, execution_id, commit, tree_hash,
            scope, findings, verdict, agent, force=force)
        self._event("evidence_security", task_id=task_id,
                    data={"artifact_ref": str(path), "commit": commit,
                          "verdict": verdict, "forced": bool(force)})
        return {"artifact_ref": str(path), "commit": commit, "verdict": verdict}

    # ---------- core-triggered review/security ----------

    def run_review(self, task_id: str, timeout: int = 900,
                   force: bool = False) -> dict:
        """Trigger the existing @reviewer agent and record its evidence.

        The agent output must contain a structured JSON block; the core then
        records the artifact with commit/tree/scope it computed itself.
        """
        return self._run_agent_evidence(task_id, "review", "@reviewer",
                                        timeout, force)

    def run_security(self, task_id: str, timeout: int = 900,
                     force: bool = False) -> dict:
        """Trigger the existing @security agent and record its evidence."""
        return self._run_agent_evidence(task_id, "security", "@security",
                                        timeout, force)

    def _run_agent_evidence(self, task_id: str, kind: str, agent: str,
                            timeout: int, force: bool) -> dict:
        task = self.load_task(task_id)
        if task["status"] != "completed":
            raise GateBlockedError(
                "%s needs a completed task; %s is %s"
                % (agent, task_id, task["status"]), gate_status="BLOCKED")
        result = task.get("result") or {}
        commit = result.get("commit")
        if not commit:
            raise GateBlockedError(
                "%s cannot run for %s: result has no commit"
                % (agent, task_id), gate_status="BLOCKED")

        tree_hash = gitops.tree_hash(self.root, commit)
        if not tree_hash:
            raise GateBlockedError(
                "%s cannot run for %s: commit %s has no resolvable tree"
                % (agent, task_id, commit), gate_status="BLOCKED")
        scope = list(result.get("changed_files") or [])
        exec_id = result.get("execution_id") or (
            "%s-%s" % (kind.upper(), commit[:12]))
        try:
            workspace = self._agent_workspace(task, commit, agent)
        except GateBlockedError as exc:
            self._event("%s_agent_blocked" % kind, task_id=task_id,
                        data={"agent": agent, "reason": str(exc)},
                        outcome="BLOCKED")
            raise
        template = (_REVIEW_AGENT_PROMPT if kind == "review"
                    else _SECURITY_AGENT_PROMPT)
        prompt = template.format(
            task_id=task_id, title=task.get("title", ""),
            description=task.get("description", ""), commit=commit,
            files=", ".join(scope) or "(none recorded)")
        executor = self._resolve_executor()
        # The harness expects the agent name as configured (filename), not the
        # in-prompt @mention syntax. The artifact keeps the @-prefixed identity.
        harness_agent = agent.lstrip("@")
        self._event("%s_agent_started" % kind, task_id=task_id,
                    data={"agent": agent, "harness_agent": harness_agent,
                          "commit": commit, "workspace": str(workspace)})
        try:
            outcome = executor(prompt, workspace, harness_agent, timeout)
        except Exception as exc:  # noqa: BLE001 - never treated as evidence
            outcome = {"ok": False, "detail": str(exc), "output": ""}
        raw = outcome.get("output") or outcome.get("detail") or ""
        raw_path = self.evidence_dir / task_id / (
            "%s-agent-%s.txt" % (kind, Path(str(exec_id)).name))
        atomic_write_text(raw_path, raw)
        try:
            # Permissions never substitute gates: an agent that changed the
            # worktree invalidates the evidence it is about to report.
            self._verify_agent_workspace(workspace, commit, agent, task_id)
        except GateBlockedError as exc:
            self._event("%s_agent_rejected" % kind, task_id=task_id,
                        data={"agent": agent,
                              "reason": "worktree changed during the run: %s"
                                        % exc},
                        outcome="BLOCKED")
            raise evidence_mod.EvidenceError(
                "%s changed the review workspace for %s during the run; "
                "evidence discarded (%s)" % (agent, task_id, exc))
        if not outcome.get("ok"):
            self._event("%s_agent_failed" % kind, task_id=task_id,
                        data={"agent": agent, "detail": outcome.get("detail")},
                        outcome="BLOCKED")
            raise evidence_mod.EvidenceError(
                "%s agent failed for %s: %s"
                % (agent, task_id, outcome.get("detail") or "unknown error"))

        doc = extract_structured_evidence(
            (outcome.get("agent_output") or "").strip() or raw)
        if doc is None:
            self._event("%s_agent_rejected" % kind, task_id=task_id,
                        data={"agent": agent, "reason": "no structured json"},
                        outcome="BLOCKED")
            raise evidence_mod.EvidenceError(
                "%s output for %s is not structured evidence (expected one "
                "fenced json block with verdict/findings); prose is ignored"
                % (agent, task_id))
        try:
            verdict = str(doc.get("verdict") or "").upper()
            if verdict not in evidence_mod.VALID_VERDICTS:
                raise evidence_mod.EvidenceError(
                    "%s returned invalid verdict %r"
                    % (agent, doc.get("verdict")))
            findings = evidence_mod.validate_findings(
                doc.get("findings") or [])
            normalized_fail = False
            if verdict == "PASS" and any(f["severity"] == "critical"
                                         for f in findings):
                verdict = "FAIL"
                normalized_fail = True

            if kind == "review":
                recorded = self.record_review(
                    task_id, exec_id, commit, tree_hash, scope, findings,
                    verdict, agent, force=force)
            else:
                recorded = self.record_security(
                    task_id, exec_id, commit, tree_hash, scope, findings,
                    verdict, agent, force=force)
        except evidence_mod.EvidenceError as exc:
            # One audit trail for every rejection reason: invalid verdict,
            # invalid findings, or the M-4 refusal to overwrite a FAIL.
            self._event("%s_agent_rejected" % kind, task_id=task_id,
                        data={"agent": agent, "reason": str(exc)},
                        outcome="BLOCKED")
            raise
        self._event("%s_agent_recorded" % kind, task_id=task_id,
                    data={"agent": agent, "commit": commit,
                          "verdict": verdict, "findings": len(findings),
                          "normalized_fail": normalized_fail,
                          "artifact_ref": recorded["artifact_ref"],
                          "output_ref": str(raw_path)},
                    outcome=verdict)
        return {
            "kind": kind,
            "agent": agent,
            "task_id": task_id,
            "commit": commit,
            "tree_hash": tree_hash,
            "verdict": verdict,
            "normalized_fail": normalized_fail,
            "findings": findings,
            "artifact_ref": recorded["artifact_ref"],
            "output_ref": str(raw_path),
        }

    def _agent_workspace(self, task: dict, commit: str, agent: str) -> Path:
        """Workspace the reviewing agent must read: the task worktree.

        Fails closed: never fall back to the base checkout, which would let the
        agent audit code that is not the task commit while the core records a
        PASS artifact for that commit.
        """
        result = task.get("result") or {}
        exec_id = result.get("execution_id")
        execution = None
        if exec_id:
            try:
                execution = self.load_execution(exec_id)
            except JuicerError:
                execution = None
        worktree = ((execution or {}).get("workspace") or {}).get("worktree")
        if not worktree or not Path(worktree).exists():
            raise GateBlockedError(
                "%s cannot review %s: task worktree is missing; restore it at "
                "the task commit before running the agent"
                % (agent, task["id"]), gate_status="BLOCKED")
        workspace = Path(worktree)
        self._verify_agent_workspace(workspace, commit, agent, task["id"])
        return workspace

    def _verify_agent_workspace(self, workspace: Path, commit: str,
                                agent: str, task_id: str) -> None:
        """The worktree must still be exactly the reviewed commit.

        Tracked changes are refused; untracked check artifacts are tolerated.
        """
        head = gitops.head_commit(workspace)
        if head != commit:
            raise GateBlockedError(
                "%s cannot review %s: worktree HEAD %s does not match the task "
                "commit %s" % (agent, task_id, head, commit),
                gate_status="BLOCKED")
        if gitops.has_tracked_changes(workspace):
            raise GateBlockedError(
                "%s cannot review %s: worktree has tracked changes; commit or "
                "discard them first" % (agent, task_id),
                gate_status="BLOCKED")

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

    def _task_next_step(self, task: dict) -> str:
        return {
            "ready": "run",
            "in_progress": "resume",
            "blocked": "inspect block, then retry",
            "failed": "retry",
            "completed": "integrate",
            "done": "none",
        }.get(task.get("status"), "inspect")

    def checkpoint(self, note: str = "") -> dict:
        tasks = self.load_tasks()
        mission = self.mission()
        commit = gitops.head_commit(self.root)
        task_state = {}
        for t in tasks:
            result = t.get("result") or {}
            task_state[t["id"]] = {
                "status": t["status"],
                "revision": t["revision"],
                "current_execution_id": t["current_execution_id"],
                "next_step": self._task_next_step(t),
                "blocked_reason": t.get("blocked_reason"),
                "evidence": {
                    "execution_id": result.get("execution_id"),
                    "branch": result.get("branch"),
                    "commit": result.get("commit"),
                    "tree_hash": result.get("tree_hash"),
                    "evidence_ref": result.get("evidence_ref"),
                    "merged_commit": result.get("merged_commit"),
                },
            }
        cp = {
            "schema_version": 1,
            "created_at": utc_now(),
            "note": note,
            "mission": mission,
            "tasks": task_state,
            "git_head": commit,
            "next_action": self._next_action(mission, tasks,
                                             [t["id"] for t in eligible_tasks(tasks)]),
        }
        name = "cp-%s-%s.json" % (
            utc_now().replace(":", "").replace("-", ""), uuid.uuid4().hex[:8])
        write_json(self.checkpoints_dir / name, cp)
        self._event("checkpoint", data={"file": name,
                                        "next_action": cp["next_action"],
                                        "next_steps": {tid: s["next_step"]
                                                       for tid, s in task_state.items()}})
        return cp

    def resume(self) -> dict:
        """Reconcile state after restart; never trusts conversation history.

        For each ``in_progress`` task:

        - Load the current execution and its worktree (falling back to the
          canonical path for legacy records).
        - If the execution already finished, align the task with it
          (succeeded -> completed, otherwise failed) when the transition is
          legal.
        - If the run was interrupted (execution still claimed/running),
          cancel the execution with a recorded reason, then mark the task
          ``blocked`` when a worktree still holds evidence, or ``failed``
          when there is nothing to preserve.
        - Record the reconciliation in ``attempt_history`` and in a resume
          report artifact under ``.juicer/evidence/``.
        - Attempt to resolve every ``in_progress`` task; a failed update is
          recorded as ``resume_error`` and left for explicit intervention, and
          no duplicate run is started while reconciling.
        """
        self.config()  # ensure initialized
        cfg = self.config()
        tasks = self.load_tasks()
        recovered: List[str] = []
        reconciled: List[dict] = []
        wt_root = self.root / cfg.get("worktree_root", ".juicer/worktrees")
        for t in tasks:
            if t["status"] != "in_progress":
                continue
            exec_id = t.get("current_execution_id")
            exec_doc = None
            if exec_id:
                try:
                    exec_doc = self.load_execution(exec_id)
                except JuicerError:
                    exec_doc = None
            if exec_doc is not None and exec_doc.get("task_id") != t["id"]:
                # Never align a task with another task's execution/result.
                self._event("resume_execution_mismatch", task_id=t["id"],
                            execution_id=exec_id,
                            data={"execution_task_id": exec_doc.get("task_id")},
                            outcome="ignored")
                exec_doc = None
                exec_id = None
            workspace = (exec_doc or {}).get("workspace") or {}
            exec_attempt = (exec_doc or {}).get("attempt")
            worktree = (Path(workspace["worktree"])
                        if workspace.get("worktree") else wt_root / t["id"])
            worktree_exists = worktree.exists()

            if exec_doc is not None and exec_doc.get("status") in (
                    "succeeded", "failed", "cancelled"):
                # Execution already terminal: align the task, do not invent a
                # second failure.
                target = ("completed" if exec_doc["status"] == "succeeded"
                          else "failed")
                carried = exec_doc.get("result") or {}
                reason = ("execution %s already %s; task aligned"
                          % (exec_id, exec_doc["status"]))

                def align(task, tgt=target, res=carried, rsn=reason,
                          ex=exec_id, br=workspace.get("branch"),
                          bc=workspace.get("base_commit"), at=exec_attempt):
                    task["status"] = tgt
                    if res:
                        task["result"] = res
                    history = list(task.get("attempt_history") or [])
                    history.append({
                        "at": utc_now(), "action": "resume",
                        "from_status": "in_progress", "to_status": tgt,
                        "execution_id": ex, "reason": rsn,
                        "branch": br, "base_commit": bc, "attempt": at,
                    })
                    task["attempt_history"] = history
                try:
                    self._update_task(t["id"], align)
                    recovered.append(t["id"])
                    reconciled.append({
                        "task_id": t["id"], "action": "aligned",
                        "from_status": "in_progress", "to_status": target,
                        "execution_id": exec_id,
                        "execution_status": exec_doc["status"],
                        "reason": reason, "worktree_exists": worktree_exists,
                    })
                    self._event(
                        "resume_reconciled", task_id=t["id"], execution_id=exec_id,
                        data={"from": "in_progress", "to": target,
                              "execution_status": exec_doc["status"],
                              "worktree_exists": worktree_exists},
                        outcome="reconciled")
                except Exception as exc:  # noqa: BLE001 - record and continue
                    self._event("resume_error", task_id=t["id"],
                                data={"detail": str(exc)}, outcome="error")
                continue

            # Interrupted mid-run (or missing/stale execution record).
            execution_status = (exec_doc or {}).get("status")
            if exec_doc is not None and execution_status in (
                    "claimed", "running"):
                reason = "interrupted: reconciled by resume"
                self._update_execution(
                    exec_id,
                    lambda e: e.update(
                        status="cancelled",
                        finished_at=utc_now(),
                        failure={"detail": reason, "exit_code": None},
                    ))
                self._event("execution_cancelled", task_id=t["id"],
                            execution_id=exec_id,
                            data={"detail": reason}, outcome="cancelled")

            if worktree_exists:
                target = "blocked"
                reason = ("interrupted run; worktree preserved at %s"
                          % worktree)
            else:
                target = "failed"
                reason = "interrupted run; no worktree to preserve"

            def recover(task, tgt=target, rsn=reason, wt=worktree,
                        ex=exec_id, wexists=worktree_exists, at=exec_attempt):
                prior = dict(task.get("result") or {})
                prior.update({
                    "resumed": True,
                    "execution_id": ex,
                    "detail": rsn,
                    "worktree": str(wt) if wexists else None,
                })
                task["status"] = tgt
                task["blocked_reason"] = rsn if tgt == "blocked" else None
                task["current_execution_id"] = ex
                task["result"] = prior
                history = list(task.get("attempt_history") or [])
                history.append({
                    "at": utc_now(), "action": "resume",
                    "from_status": "in_progress", "to_status": tgt,
                    "execution_id": ex, "reason": rsn,
                    "worktree": str(wt) if wexists else None,
                    "branch": workspace.get("branch"),
                    "base_commit": workspace.get("base_commit"),
                    "attempt": at,
                })
                task["attempt_history"] = history
            self._update_task(t["id"], recover)
            recovered.append(t["id"])
            reconciled.append({
                "task_id": t["id"], "action": "recovered",
                "from_status": "in_progress", "to_status": target,
                "execution_id": exec_id,
                "execution_status": execution_status,
                "reason": reason, "worktree": str(worktree) if worktree_exists else None,
            })
            self._event(
                "resume_recovered", task_id=t["id"], execution_id=exec_id,
                data={"from": "in_progress", "to": target, "detail": reason,
                      "worktree_exists": worktree_exists},
                outcome="recovered")

        artifact_ref = None
        if reconciled:
            path = self.evidence_dir / ("resume-%s.json" % uuid.uuid4().hex[:12])
            write_json(path, {
                "schema_version": 1,
                "type": "resume_report",
                "created_at": utc_now(),
                "reconciled": reconciled,
            })
            artifact_ref = str(path)
            self._event("resume_report", data={"artifact_ref": artifact_ref,
                                               "recovered": list(recovered)},
                        outcome="reconciled")
        out = {"recovered": recovered, "status": self.status()}
        if artifact_ref:
            out["artifact_ref"] = artifact_ref
        return out

    # ---------- events ----------

    def events(self, limit: int = 50) -> List[dict]:
        return read_events(self.events_path)[-limit:]
