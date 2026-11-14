---
description: "Add a task to the planning backlog with validation, ID generation and prioritization."
---

# Command: /add-backlog

**Core integration.** `backlog/*.md` is the planning source. After a validated
`juicer import-backlog`, `.juicer/` is canonical and there is no bidirectional
sync; new Markdown entries do not enter an existing mission. Import only into a
new/empty mission.

## Steps

1. **Extract task details**
   - Title: one line, imperative, outcome-oriented.
   - Description: what and why, with boundaries.
   - Priority: infer from context (P0–P3) or ask.
   - Dependencies: existing task ids only.
   - Acceptance criteria: observable and verifiable.
   - Scope: repository paths the task may change.
   - Estimated effort: S/M/L (relative, not a commitment).

2. **Generate task ID**
   - Read `backlog/backlog.md` and existing ids across `backlog/`.
   - Increment the highest id; never reuse an id.
   - Do not ask the user for the ID.

3. **Validate the task**
   - **Acceptance criteria**: at least one, non-empty, each checkable by a
     deterministic check, review, security evidence or human approval.
   - **Dependencies**: exist in the backlog or are explicitly marked external;
     no self-dependency; no duplicates; **no cycle**.
   - **Scope**: at least one path; no protected path (`.juicer/`, `.git/`,
     secrets, policy).
   - **Priority**: exactly one of `P0`, `P1`, `P2`, `P3`.
   - **Uniqueness**: id and title do not duplicate an existing task.
   - If validation fails, stop and ask for the missing information. Do not
     invent criteria or dependencies.

4. **Add to backlog**
   - Append under "Pending Tasks" using the template.
   - Preserve the existing formatting and ordering.

5. **Confirm**
   - Show the added task and the validation result.
   - Ask whether to start, leave pending or edit.

## Output Format

```
✅ Task Added to Backlog

### Task: [TASK-XXX] [Title]

**Description**: [What needs to be done]
**Priority**: [P0-P3]
**Status**: Pending
**Dependencies**: [List or None]
**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
**Scope**: [paths]
**Estimated Effort**: [S/M/L]

**Validation**
- [x] Criteria non-empty and verifiable
- [x] Dependencies exist and are acyclic
- [x] Scope declared, no protected paths
- [x] ID unique

**Next Steps**:
- `juicer import-backlog` (only for a new/empty mission), then `juicer run TASK-XXX`
- Type `/edit-backlog TASK-XXX` to modify
- Or continue conversation
```

## Rules

- Auto-generate the task id; do not ask.
- Infer priority from context:
  - P0: critical bug, security incident, production down
  - P1: high-priority feature or blocker for other work
  - P2: normal feature or improvement
  - P3: nice to have
- Never create a task without verification-ready acceptance criteria.
- Never create a dependency cycle.
- Always confirm before starting a task.
- Do not claim the task is imported into the core; report the Markdown change
  only.
