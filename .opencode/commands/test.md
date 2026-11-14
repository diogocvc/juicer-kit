---
description: "Write and run deterministic tests for the current code; the core owns PASS/FAIL."
agent: tester
---

# Command: /test

**Core integration.** Use `juicer run TASK-XXX` so the core executes
`task.checks` and records `PASS`/`FAIL`/`BLOCKED`/`NOT RUN` against the commit.
This command is the **manual** path for work outside the core. The agent writes
tests and reports raw command output; it does not classify the result.

When invoked, create and run deterministic tests for the current code. Run
after implementation and before review; the core's checks remain
authoritative.

## Steps

1. **Understand the code**
   - Read the implementation and the acceptance criteria.
   - Identify behavior, edge cases and error scenarios.

2. **Design tests**
   - Happy path.
   - Boundaries (null, empty, max, concurrency).
   - Error scenarios (invalid input, dependency failure).
   - Regression case for a fixed defect.

3. **Write tests**
   - Follow project conventions; use the `tdd-workflow` skill.
   - Keep tests deterministic, isolated, fast and behavior-focused.
   - Do not weaken, skip or delete a failing test to get green.

4. **Run tests**
   - Execute the suite (this repository:
     `uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py`).
   - Record the command, exit code and raw short output.
   - Do not report `PASS`/`FAIL`; the core owns that classification.

5. **Report artifacts and gaps**
   - List created/modified test files.
   - Report measured coverage only when a coverage tool produced it; otherwise
     `UNKNOWN`.
   - `NOT RUN` or skipped is never a pass.

## Output Format

```
## Test Report: [Module or Feature]

### Artifacts
- Created: `tests/...`
- Modified: `tests/...`

### Commands Run
- `command` → exit code and short raw output

### Coverage
- Lines: [measured or UNKNOWN]
- Branches: [measured or UNKNOWN]

### Uncovered Behavior
- [What is still untested and why]

### Blockers / Open Questions
- [Missing runtime, fixture or ambiguous behavior]

### Handoff
- The core must run `task.checks`; this report is not a verdict.
```

## Rules

- Tests must be deterministic and fast.
- Cover edge cases and error scenarios.
- Do not skip failing tests; fix or report the blocker.
- Never report `PASS`/`FAIL`; the core owns check results.
- Never edit production code to force a test to pass.
- Report coverage gaps honestly; `NOT RUN` is never a pass.
