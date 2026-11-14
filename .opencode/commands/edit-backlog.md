---
description: "Edit a planning-backlog task with validation and dependency checks."
---

# Command: /edit-backlog

**Core integration.** This edits the Markdown planning source only. After a
validated `juicer import-backlog`, `.juicer/` is canonical and there is no
bidirectional sync; changing the Markdown does not change an in-progress
mission. If the task is already in a mission, stop and explain how to create a
new mission or a followed-up task instead of silently editing.

## Steps

1. **Read the task**
   - Load it from `backlog/backlog.md` or `backlog/in-progress.md`.
   - If it is already imported into an active mission, warn before editing.

2. **Show current details**
   - Display every field, including scope if present.

3. **Ask what to edit**
   - Title, description, priority, dependencies, acceptance criteria, scope or
     effort.

4. **Validate the proposed change**
   - **Acceptance criteria**: remain non-empty, observable and verifiable.
   - **Dependencies**: exist; no self-dependency; no duplicates; **re-run the
     cycle check** across the whole backlog.
   - **Scope**: remains non-empty; no protected path.
   - **Priority**: `P0`–`P3`.
   - **Status**: a valid status and a legal transition (do not move a task to
     Done without integration and post-merge checks).
   - If the change would orphan a dependent task or create a cycle, stop and
     show the affected tasks. Do not save an invalid graph.

5. **Update the task**
   - Apply the change in the correct file.
   - Preserve formatting.

6. **Confirm**
   - Show the updated task and the validation result.

## Output Format

```
✏️ Editing Task: TASK-XXX [Title]

**Current Details**:
- Description: [current]
- Priority: [current]
- Dependencies: [current]
- Acceptance Criteria: [current]
- Scope: [current]
- Status: [current]

**Validation of the proposed change**:
- [x] Criteria non-empty and verifiable
- [x] Dependency graph acyclic
- [x] Scope declared
- [x] Status transition allowed

✅ Task Updated

**Updated Details**:
- [Show all updated fields]
```

## Rules

- Show current values before editing.
- Re-validate the whole dependency graph, not just the edited task.
- Allow cancellation at any point; save nothing on cancel.
- Do not edit `.juicer/` state from this command.
- Never mark Done without merge and post-merge evidence.
- Do not invent criteria or dependencies to satisfy validation.
