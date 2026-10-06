---
description: "Edit a task in the backlog."
---

# Command: /edit-backlog

When invoked with a task ID:

1. **Read Task**
   - Load task from `backlog/backlog.md`.

2. **Show Current Details**
   - Display all fields.

3. **Ask What to Edit**
   - Title, description, priority, dependencies, criteria, effort.

4. **Update Task**
   - Edit `backlog/backlog.md` with new values.

5. **Confirm**
   - Show updated task.

## Output Format

```
✏️ Editing Task: TASK-XXX [Title]

**Current Details**:
- Description: [current]
- Priority: [current]
- Dependencies: [current]
- Acceptance Criteria: [current]
- Effort: [current]

**What would you like to edit?**
- Type the field name and new value
- Or type 'cancel' to abort

✅ Task Updated

**Updated Details**:
- [Show all updated fields]
```

## Rules

- Show current values before editing.
- Confirm changes before saving.
- Allow cancellation at any point.
