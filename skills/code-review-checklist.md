# Skill: Code Review Checklist

Use this skill when reviewing code to ensure consistency and quality.

## Checklist

### ✅ Functionality

- [ ] Code does what it's supposed to do.
- [ ] Edge cases are handled (null, empty, max values, etc.).
- [ ] Error handling is implemented (try/catch, error boundaries).
- [ ] No console.logs or debug code left behind.

### ✅ Code Quality

- [ ] Code is readable and self-documenting.
- [ ] Functions are small and focused (single responsibility).
- [ ] No duplication (DRY principle).
- [ ] Naming is clear and consistent (variables, functions, classes).

### ✅ Testing

- [ ] Tests cover happy path, edge cases, and errors.
- [ ] Tests are deterministic (no flakiness).
- [ ] Tests are fast (no unnecessary delays).
- [ ] Test names are descriptive.

### ✅ Security

- [ ] No hardcoded secrets or API keys.
- [ ] User inputs are validated and sanitized.
- [ ] Authentication/authorization checks are in place.
- [ ] No SQL/NoSQL injection vulnerabilities.

### ✅ Performance

- [ ] No obvious performance issues (e.g., N+1 queries, large loops).
- [ ] Expensive operations are cached or optimized.
- [ ] Database queries are indexed appropriately.

### ✅ Documentation

- [ ] JSDoc/TSDoc is present for public APIs.
- [ ] Complex logic has inline comments.
- [ ] README or docs are updated if needed.

### ✅ Consistency

- [ ] Code follows project conventions (linting, formatting).
- [ ] Architecture patterns are respected.
- [ ] Existing tests still pass.

## Output Format

After review, provide:

```
## Code Review Summary

### ✅ Approved
- [What is good about the code]

### 🔴 Issues Found

#### Critical
- [file:line] — [Issue and explanation]

#### Medium
- [file:line] — [Issue and explanation]

#### Suggestions
- [file:line] — [Improvement suggestion]

### 📋 Checklist
- [x] Functionality
- [x] Code Quality
- [ ] Testing (missing edge case coverage)
- [x] Security
- [x] Performance
- [x] Documentation
- [x] Consistency

## Verdict
- [ ] Approved
- [ ] Approved with minor suggestions
- [ ] Changes requested (see critical/medium issues)
```
