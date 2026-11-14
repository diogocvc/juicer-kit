---
name: tdd-workflow
description: Use this skill when implementing new features or fixing bugs with a test-driven approach, including legacy code and characterization tests.
---

# Skill: TDD Workflow

Use this skill when implementing new behavior or fixing a defect with a
test-driven approach. It follows red → green → refactor and Michael Feathers'
legacy-code techniques (*Working Effectively with Legacy Code*).

## When to Use

- New feature or behavior with an observable contract.
- Bug fix that needs a regression test.
- Refactoring legacy code that lacks tests.
- Any change where "it works" must be demonstrated, not asserted.

The agent writes tests and runs commands. **The core owns `PASS`/`FAIL`**; the
agent's prose is not evidence.

## Red → Green → Refactor

### 1. Understand the requirement

- Read the task and acceptance criteria.
- Identify the observable behavior, inputs, outputs and errors.
- List edge cases and failure modes before writing code.
- If the behavior is ambiguous, stop and report an Open Question.

### 2. Write a failing test (red)

- Create the smallest test that describes the expected behavior.
- Run it; it **must fail for the right reason** (not a typo or import error).
- If it passes, either the behavior already exists or the test is wrong.
- Capture the raw failure.

### 3. Implement the minimum (green)

- Write only enough code to make the test pass.
- Do not optimize, generalize or refactor yet.
- Do not add unrelated functionality.

### 4. Verify

- Run the new test and the surrounding suite.
- Confirm no existing behavior broke.
- The core re-runs the declared checks; do not self-certify.

### 5. Refactor

- Improve names, structure and duplication.
- **Do not change observable behavior**; tests stay green.
- Use the `code-review-checklist` dimensions as a guide.

### 6. Repeat

- One behavior per cycle.
- Keep the suite fast and deterministic.

## Test Design Rules

- Deterministic: no sleeps, real clocks, network, random seeds or ordering
  assumptions.
- Isolated: each test owns its state and fixtures.
- Behavioral: assert the contract, not private internals.
- Readable: Arrange / Act / Assert; one behavior per test.
- Descriptive names: `returns_401_when_token_is_expired`.
- Fast: unit tests in-process; integration tests cross one real boundary.
- Honest: never skip, weaken or delete a failing test to get green.
- Regression: the test must fail before the fix and succeed after it.

## Legacy Code

Legacy code is code without tests. Do not refactor it blind.

### 1. Find a seam

A **seam** is a place where behavior can be changed without editing in place:
dependency injection, a wrapper, a factory, a subclass, a build-time switch.
Identify the smallest seam that lets you observe the behavior.

### 2. Write characterization tests

Characterization tests document what the code **actually does**, not what it
should do:

- Feed realistic inputs and assert the current output, including quirks.
- If the output is hard to assert, capture a **golden master** (snapshot) and
  review the diff deliberately.
- Use **approval tests** for large or structured output.
- Do not "fix" surprising behavior in a characterization test; record it and
  raise a separate change.

### 3. Pin the behavior you will touch

- Cover the path you are about to change, plus its callers.
- Prefer a few high-value characterization tests over broad, brittle ones.
- Keep them deterministic: freeze time, stub I/O, seed randomness.

### 4. Change in small steps

- Refactor first, then add the feature or fix.
- Keep the characterization suite green between steps.
- If a step cannot be made behavior-preserving, stop and split the change.

### 5. Techniques

- **Sprout method/class** — add new behavior in a new, tested unit and call it
  from the legacy code.
- **Wrap method** — rename the legacy method and add a tested wrapper.
- **Extract and override** — isolate a dependency behind a seam.
- **Introduce a seam** only as wide as needed; avoid a rewrite.

### 6. Exit criteria

- The changed behavior has focused tests.
- The characterization suite still passes.
- The refactor is behavior-preserving, with any intentional behavior change
  routed through the compatible-change activity.

Reference: Michael Feathers, *Working Effectively with Legacy Code* (2004).

## Anti-patterns

- Writing implementation first and tests after as a formality.
- Tests that assert implementation details and break on refactor.
- A regression test that passes before the fix.
- Mocking the thing under test.
- Sharing mutable state between tests.
- Treating coverage percentage as correctness.

## Example

```
Task: validate email format.

1. Red: expect validateEmail("test@example.com") is true;
         expect validateEmail("invalid") is false; run → fails.
2. Green: implement the minimum validation; run → passes.
3. Refactor: clarify the regex and add edge cases; run → still passes.
4. Repeat for the next requirement.
```

For a legacy function with no tests:

```
1. Characterization: call the current function with real inputs; assert the
   current outputs, quirks included.
2. Seam: wrap the I/O dependency so the test is deterministic.
3. Refactor in small steps, suite green.
4. Add the new behavior with a new failing test.
```
