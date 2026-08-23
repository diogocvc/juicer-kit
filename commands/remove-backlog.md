---
description: "Remove a task from the backlog."
mode: "command"
---

# Command: /remove-backlog

When invoked with a task ID:

1. **Read Task**
   - Load task from `backlog/backlog.md`.

2. **Confirm Removal**
   - Show task details.
   - Ask for confirmation.

3. **Remove Task**
   - Delete from `backlog/backlog.md`.
   - If in `in-progress.md`, remove from there too.

4. **Confirm**
   - Notify user that task was removed.

## Output Format

```
⚠️ Remove Task: TASK-XXX [Title]

**Task Details**:
- Description: [description]
- Priority: [P0-P3]
- Status: [Pending/In Progress/Blocked]

**Are you sure you want to remove this task?** (yes/no)

✅ Task Removed

Task TASK-XXX has been removed from the backlog.
```

## Rules

- Always confirm before removing.
- Remove from both backlog.md and in-progress.md if present.
- Notify user of successful removal.
