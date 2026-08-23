---
description: "Start a specific task from the backlog."
mode: "command"
---

# Command: /start

When invoked with a task ID (e.g., `/start TASK-001`):

1. **Read Task**
   - Load task from `backlog/backlog.md`.

2. **Move to In-Progress**
   - Add to `backlog/in-progress.md`.
   - Update status in `backlog/backlog.md` to "In Progress".

3. **Delegate to Orchestrator**
   - Call @orchestrator to execute the task.

## Output Format

```
🚀 Starting Task: TASK-XXX [Title]

**Priority**: [P0-P3]
**Dependencies**: [None or TASK-XXX]
**Assigned To**: [@orchestrator]

**Plan**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Next**: @orchestrator will begin execution.
```

## Rules

- Confirm the task exists before starting.
- Update both backlog.md and in-progress.md.
- Notify user that task has started.
