---
description: "Add a task to the backlog with automatic ID generation and prioritization."
---

# Command: /add-backlog

When invoked, add the described task to the backlog.

## Steps

1. **Extract Task Details**
   - Title: Summarize the task in one line.
   - Description: Full description from user input.
   - Priority: Infer from context (P0-P3) or ask user.
   - Dependencies: Check if task depends on existing tasks.
   - Acceptance Criteria: Extract from user input or ask.
   - Estimated Effort: Infer from complexity (S/M/L).

2. **Generate Task ID**
   - Read `backlog/backlog.md` to find the last task ID.
   - Increment: TASK-001 → TASK-002 → TASK-003.

3. **Add to Backlog**
   - Append task to `backlog/backlog.md` under "Pending Tasks".
   - Use the task template format.

4. **Confirm with User**
   - Show the added task details.
   - Ask if user wants to:
     - Start now
     - Leave as pending
     - Edit details

## Output Format

```
✅ Task Added to Backlog

### Task: [TASK-XXX] [Title]

**Description**: [What needs to be done]
**Priority**: [P0-P3]
**Dependencies**: [List or None]
**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
**Estimated Effort**: [S/M/L]

**Next Steps**:
- Type `/start TASK-XXX` to start now
- Type `/edit-backlog TASK-XXX` to modify
- Or continue conversation
```

## Rules

- Auto-generate task ID (do not ask user).
- Infer priority from context:
  - P0: Critical bug, security issue, production down
  - P1: High priority feature, blocker for other work
  - P2: Normal feature, improvement
  - P3: Nice to have, low priority
- Ask for clarification if acceptance criteria are unclear.
- Always confirm before starting a task.
