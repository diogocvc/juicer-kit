---
description: "Start a backlog task through the juicer core (preferred) or a manual, gate-equivalent path."
---

# Command: /start

**Core integration.** The preferred path is `juicer run TASK-XXX`. The core
creates the isolated worktree/branch, applies `scope.paths`, runs the agent and
`task.checks`, and enforces the gates. Do **not** call `@orchestrator` directly
to bypass this. The manual path below exists only for work explicitly outside
the mission.

## Preferred Path (task inside the core mission)

1. **Confirm the mission is ready**
   - `juicer status` — the mission must be `ready`/`active`.
   - If the backlog has not been imported into a new/empty mission:
     `juicer import-backlog` (one-way, once per mission).

2. **Validate the task**
   - The task exists in `.juicer/`.
   - Dependencies are resolved.
   - `acceptance_criteria` is non-empty and each criterion has a valid
     `verification`.
   - `scope.paths` is non-empty and does not include protected paths.
   - If any check fails, stop and report the defect; do not "fix" the task in
     the Markdown board after import (there is no bidirectional sync).

3. **Run the core**
   ```bash
   juicer run TASK-XXX
   ```
   In this repository the entrypoint is `bin/juicer`; if `juicer` is not on
   `PATH`, use `python3 bin/juicer run TASK-XXX`.

4. **Read real state**
   - `juicer status --json` and `juicer events`.
   - Do not infer success from agent prose.

5. **Continue the canonical gates**
   ```bash
   juicer review-run TASK-XXX
   juicer security-run TASK-XXX     # only when the security gate applies
   juicer approve TASK-XXX --approver <identity>   # only when required
   juicer integrate TASK-XXX --approve
   ```

6. **Done only after post-merge checks pass** — the core owns the transition.

## Manual Path (work outside the core mission)

Only when the task is explicitly not part of `.juicer/`:

1. Confirm the task exists in `backlog/backlog.md` and its dependencies are
   resolved.
2. Move it to `backlog/in-progress.md`; set **Status: In Progress** in
   `backlog/backlog.md`.
3. Select capabilities per the task (see `/plan`); do not run a fixed pipeline.
4. Execute implementation, then deterministic checks, then review, then
   security (risk only), then human approval (when required), then integrate,
   then post-merge checks.
5. Record evidence with the same rigor as the core; `NOT RUN` is never a pass.
6. Move to `backlog/done/` only after the merge and passing post-merge checks.

## Output Format

```
🚀 Starting: TASK-XXX [Title]

**Execution path**: juicer core | manual (reason)
**Priority**: [P0-P3]
**Dependencies**: [resolved / open]
**Scope**: [scope.paths]

**Command**
```bash
juicer run TASK-XXX
```

**Gate plan**
- [ ] deterministic checks
- [ ] review
- [ ] security (if risk applies)
- [ ] human approval (if required)
- [ ] integrate + post-merge checks

**Manual fallback (only if out of core)**
- Capabilities: [selected activities and why]
```

## Rules

- Do not call `@orchestrator` directly as a shortcut around the core.
- Do not start a task with unresolved dependencies or empty criteria.
- Do not broaden `scope.paths` to make the task runnable.
- Do not mark the task done before integration and post-merge checks.
- If the core blocks the task, report the blocker; do not work around it.
