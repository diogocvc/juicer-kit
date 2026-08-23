---
description: "Summarize the current session to reduce token usage."
mode: "command"
---

# Command: /compact

When invoked, summarize the current session to reduce token usage.

## Steps

1. **Review Session History**
   - Read all messages in the session.
   - Identify key decisions, action items, and context.

2. **Extract Essentials**
   - Keep:
     - Architectural decisions.
     - Task assignments and status.
     - Important constraints or requirements.
   - Discard:
     - Redundant explanations.
     - Intermediate reasoning.
     - Completed sub-tasks (summarize briefly).

3. **Create Summary**
   - Write a concise summary (max 500 words).
   - Structure with sections (Decisions, Actions, Context, Tasks).

4. **Output Summary**
   - Present the summary.
   - Offer to start a fresh session with this context.

## Output Format

```
## Session Summary

### Decisions Made
- [Decision 1]
- [Decision 2]

### Action Items
- [ ] Action 1
- [ ] Action 2

### Key Context
- [Important context to retain]

### Completed Tasks
- [TASK-XXX] [Title]
- [TASK-YYY] [Title]

### In Progress
- [TASK-ZZZ] [Title] — [Current step]

---
Start a new session with this context? (yes/no)
```

## Rules

- Keep it concise (max 500 words).
- Never lose critical decisions.
- Always preserve action items.
- Offer to start fresh session.
