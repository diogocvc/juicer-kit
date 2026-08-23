# Skill: TDD Workflow

Use this skill when implementing new features or fixing bugs with a test-driven approach.

## Workflow

### 1. Understand the Requirement

- Read the task description carefully.
- Ask clarifying questions if the expected behavior is ambiguous.
- Identify edge cases and error scenarios.

### 2. Write a Failing Test

- Create a test file (e.g., `*.test.ts`, `*.spec.ts`).
- Write a test that describes the expected behavior.
- Run the test — it **must fail** at this point.
- If the test passes, either the test is wrong or the feature already exists.

### 3. Implement the Minimum Code

- Write only enough code to make the test pass.
- Do not optimize or refactor yet.
- Do not add unrelated functionality.

### 4. Run the Test

- Execute the test suite.
- Verify that the new test passes.
- Ensure no existing tests broke.

### 5. Refactor

- Improve code structure, readability, and performance.
- Remove duplication.
- Apply design patterns if appropriate.
- **Do not change behavior** — all tests must still pass.

### 6. Repeat

- Write another failing test for the next requirement.
- Go through steps 3-5 again.
- Continue until all requirements are covered.

## Rules

- Never write implementation code before a failing test.
- Never skip the refactoring step.
- Keep tests fast, deterministic, and isolated.
- Name tests descriptively (e.g., `should return 401 when token is invalid`).
- Cover happy path, edge cases, and error scenarios.

## Example

```
Task: Create a function that validates email format.

1. Write test:
   - `expect(validateEmail('test@example.com')).toBe(true)`
   - `expect(validateEmail('invalid')).toBe(false)`
   - Run test → fails (function doesn't exist yet).

2. Implement:
   - Create `validateEmail()` function with basic regex.
   - Run test → passes.

3. Refactor:
   - Improve regex for edge cases.
   - Add JSDoc.
   - Run test → still passes.

4. Repeat for next requirement.
```
