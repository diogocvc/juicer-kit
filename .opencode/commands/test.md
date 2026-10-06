---
description: "Create and run tests for the current code."
agent: tester
---

# Command: /test

When invoked, create and run comprehensive tests for the current code.

## Steps

1. **Understand the Code**
   - Read the implementation to be tested.
   - Identify functionality, edge cases, and error scenarios.

2. **Design Tests**
   - Plan test cases for:
     - Happy path.
     - Edge cases (null, empty, max values).
     - Error scenarios (invalid input, failures).

3. **Write Tests**
   - Create test files (e.g., `*.test.ts`).
   - Use descriptive test names.
   - Follow project testing conventions (Jest, Vitest, etc.).

4. **Run Tests**
   - Execute the test suite.
   - Report results (passed, failed, skipped).
   - Fix flaky tests if any.

5. **Report Coverage**
   - Show line and branch coverage.
   - Identify gaps.

## Output Format

```
## Test Report: [Module or Feature]

### Tests Created
- `tests/file.test.ts`
  - [Test case 1]
  - [Test case 2]

### Test Results
- Total: X
- Passed: Y
- Failed: Z
- Skipped: W

### Coverage
- Lines: XX%
- Branches: XX%

### Issues
- [Any flaky tests or gaps]

### Recommendations
- [What else should be tested]
```

## Rules

- Tests must be deterministic and fast.
- Cover edge cases and error scenarios.
- Do not skip failing tests — fix or investigate.
- Report coverage gaps honestly.
