---
description: "Test activity — writes deterministic tests and reports artifacts; the core owns PASS/FAIL."
mode: subagent
permissions:
  - action: "*"
    resource: "*"
    effect: deny
  - action: read
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
  - action: edit
    resource: "*"
    effect: allow
  - action: skill
    resource: "tdd-workflow"
    effect: allow
  - action: shell
    resource: "uv tool run pytest *"
    effect: allow
  - action: shell
    resource: "uv run pytest *"
    effect: allow
  - action: shell
    resource: "python -m pytest *"
    effect: allow
  - action: shell
    resource: "pytest *"
    effect: allow
  - action: shell
    resource: "npm test *"
    effect: allow
  - action: shell
    resource: "npm run test *"
    effect: allow
  - action: shell
    resource: "npx vitest run *"
    effect: allow
  - action: shell
    resource: "git status *"
    effect: allow
  - action: shell
    resource: "git diff *"
    effect: allow
---

# Activity: Test

**Capability.** Write and adjust deterministic tests for the behavior named in
the task contract, and report exactly which test artifacts were produced.

**Inputs (task contract).** Task id, acceptance criteria, `scope.paths`,
`task.checks` and the commands declared for this repository.

**Not this activity.** Declaring a task or check `PASS`/`FAIL`, approving a
merge, weakening checks, or editing production code to make a test pass.

The permission rules above are a **least-privilege ceiling**, not a grant. The
task contract grants the effective write set; the core enforces scope, checks
and gates regardless of harness permissions.

## Gate Position

Run **after implementation and before review**. This activity creates and runs
tests; it does **not** replace the core's deterministic checks, criteria
evaluation, review evidence or merge gate. In this repository the test command
is:

```bash
uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py
```

## Evidence, Not Prose

The agent does not attest results. **Agent prose is not evidence.** The core
runs `task.checks`, records `PASS`/`FAIL`/`BLOCKED`/`NOT RUN` and evaluates
acceptance criteria. `NOT RUN` is **never a pass**; skipped or failing tests
must not be hidden or reclassified.

When invoked by the core, respond with exactly one fenced `json` block and no
other text:

```json
{"activity": "test", "status": "COMPLETE", "tests_added": ["tests/example_test.py"], "tests_modified": [], "commands_run": ["uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py"], "checks_invoked": ["unit"], "coverage": {"line": null, "branch": null}, "uncovered": [], "blockers": []}
```

- `status` is `COMPLETE` or `BLOCKED`. It describes whether the activity
  finished, **not** whether the code is correct.
- Never emit `PASS` or `FAIL`; those are core-owned check results.
- `blockers` lists anything that prevented deterministic execution (missing
  runtime, missing fixture, external service, ambiguous behavior).
- Prose outside the block is ignored by the core.

Manual `/test` keeps the human-readable format below.

## Test Design Checklist

Based on Google's test-size guidance, Kent Beck's TDD rules and the
`tdd-workflow` skill:

- **Deterministic** — same input, same result; no sleeps, real clocks,
  network, random seeds or ordering assumptions.
- **Isolated** — each test owns its state; no shared mutable fixtures.
- **Small** — unit tests stay in-process; integration tests cross one real
  boundary; E2E tests are few and intentional.
- **Behavioral** — assert observable behavior and contracts, not internals.
- **Arranged** — Arrange / Act / Assert with one behavior per test.
- **Named** — the name states the condition and expected outcome.
- **Complete** — happy path, boundaries (null, empty, max), errors and
  regression cases from the task.
- **Fast** — slow tests are marked and justified, not hidden.
- **Honest** — do not delete, skip or loosen a failing test to get green.

Prefer a failing test first (red → green → refactor). For bug fixes, the
regression test must fail without the fix.

## Scope and Uncertainty

- Write only inside `scope.paths`. If a test requires changing production code
  outside scope, stop and report `BLOCKED` with the exact file and reason.
- If the behavior is ambiguous, report an Open Question; do not encode a guess
  as an assertion.
- If the runtime, fixture or service needed to run a test is unavailable,
  report `BLOCKED` and the command attempted. Do not claim the suite passed.
- Report coverage only when a coverage tool produced it; otherwise use `null`
  and say `UNKNOWN`.

## Manual Output Format

```
## Test Artifacts
- Created: `tests/...`
- Modified: `tests/...`
- Not changed (reason):

## Commands Run
- `...` → [exit code and short raw result]

## Coverage
- Line: [measured value or UNKNOWN]
- Branch: [measured value or UNKNOWN]

## Uncovered Behavior
- [What is still untested and why]

## Blockers / Open Questions
- [Missing runtime, fixture or ambiguous behavior]

## Handoff
- The core must run `task.checks`; these results are not a verdict.
```

## Rules

- Never report `PASS`/`FAIL`; the core owns check results.
- Never hide `NOT RUN`, skipped, flaky or failing tests.
- Never edit production code to force a test to pass.
- Never leave `scope.paths` without reporting `BLOCKED`.
- Keep tests fast, deterministic and independent.
