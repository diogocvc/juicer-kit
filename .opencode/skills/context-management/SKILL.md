---
name: context-management
description: Use this skill to optimize token usage and manage context efficiently.
---

# Skill: Context Management

Use this skill to optimize token usage and manage context efficiently.

## Strategies

### 1. Context Pruning

- Remove irrelevant files from context.
- Keep only:
  - Files related to current task.
  - Core architecture docs.
  - Active conversation history.

### 2. Summarization

- When session exceeds ~50 messages, use `/compact` to summarize.
- Keep:
  - Key decisions.
  - Action items.
  - Important context.
- Discard:
  - Redundant explanations.
  - Intermediate reasoning.
  - Completed sub-tasks.

### 3. Selective Loading

- Use @finder to load only necessary files.
- Do not load entire codebase unless required.
- For large files, load specific sections (use line ranges if supported).

### 4. Cache Context

- Store frequently-used context in `docs/context/`.
- Reference cached context instead of re-explaining.
- Update cache when architecture changes.

### 5. Avoid Bloat

- Do not repeat information already in backlog or docs.
- Use references: "See `backlog/backlog.md#TASK-XXX`".
- Keep explanations concise.

## Commands

### `/compact`

Summarize the current session:

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
```

## Rules

- Always prune context before it gets too large.
- Summarize proactively, not reactively.
- Never lose critical decisions or action items.
- Document assumptions explicitly.
