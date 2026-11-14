---
description: "Create a capability-based implementation plan and emit juicer decompose JSON."
---

# Command: /plan

**Core integration.** After a ready mission, the durable output of this command
is a `tasks.json` consumable by `juicer decompose tasks.json`. When the task is
already in the core, prefer editing the mission through the planner activity
and re-decomposing rather than creating a parallel plan.

## Steps

1. **Understand the task**
   - Restate the outcome and acceptance criteria.
   - Ask only about genuine ambiguity; record it as an Open Question.
   - Identify what is explicitly out of scope.

2. **Select capabilities (not a fixed chain)**
   - Choose only the activities the task actually needs:
     - surface map (`@finder`) when paths are unknown;
     - deep analysis (`@analyst`) when dependencies/blast radius are unclear;
     - diagnosis (`@debugger`) when a cause is unknown;
     - external research (`@researcher`) when a standard/version is unknown;
     - design (`@architect`) when a component/interface/boundary is new;
     - decomposition (`@planner`) to produce the task JSON.
   - State what you skipped and why. A small, understood change may need only
     design-free decomposition.

3. **Gather evidence**
   - Read the relevant files and the accepted decisions.
   - Do not re-derive facts that already exist in an artifact or `.juicer/`.

4. **Design the solution (only if needed)**
   - Components, interfaces, data, integration and trade-offs.
   - API changes state their versioning and compatibility impact.

5. **Decompose**
   - Atomic tasks, dependencies, critical path, criteria, scope, gates.
   - Apply INVEST and Critical Path Method.
   - Every criterion has `check:<id>`, `review`, `security` or `human`
     verification.

6. **Validate before output**
   - Unique ids; no self-dependency or cycle.
   - Non-empty `scope.paths`; no protected paths.
   - `checks` commands are non-interactive and runnable.
   - `required_gates` uses only `verification`, `review`, `security`,
     `approval`; declare `security` explicitly when risk applies.
   - No task without a verification path.

7. **Emit the artifact**
   - Write `tasks.json` (or present it for the user to save).
   - Do not call `juicer decompose` on an unvalidated file.

## Output Format

```
## Plan: [Task Name]

### Outcome and Boundaries
- Outcome:
- In scope:
- Out of scope:
- Open questions:

### Capability Selection
| Activity | Needed? | Why | Skipped alternative |
| --- | --- | --- | --- |

### Design Summary (only if a design activity ran)
- Components:
- Interfaces:
- Data:
- Decisions/trade-offs:

### Task Summary
1. [TASK-XXX] [Title] — depends on [..] — criteria [..]
2. ...

### Critical Path
TASK-XXX → TASK-YYY

### Risks and Blockers
- [Risk, mitigation, owner decision]

### JSON for `juicer decompose`
```json
{
  "tasks": [
    {
      "id": "TASK-XXX",
      "title": "...",
      "description": "...",
      "priority": "P2",
      "depends_on": [],
      "agent": "coder",
      "acceptance_criteria": [
        {"id": "AC-1", "description": "...", "verification": "check:unit"}
      ],
      "scope": {"paths": ["src/..."], "constraints": []},
      "approval_policy": {"human_approval_required": false, "required_gates": ["verification", "review"]},
      "checks": [{"id": "unit", "command": ["uv", "tool", "run", "pytest", "tests/", "-q"]}]
    }
  ]
}
```
```

## Rules

- Do not implement code — planning only.
- Do not use a fixed `finder → analyst → architect → planner` chain.
- Every task must be small enough for one session and independently verifiable.
- Every task must have explicit scope, criteria and verification.
- Never invent requirements; surface ambiguity as an Open Question.
- Do not emit JSON that `juicer decompose` would reject.
