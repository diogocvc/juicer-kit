---
description: "Review code changes with a structured checklist."
mode: "command"
---

# Command: /review

When invoked, review the given code changes using the code-review-checklist skill.

## Steps

1. **Read the Changes**
   - Review all modified and new files.
   - Understand the context and purpose.

2. **Apply the Checklist**
   - Use the `code-review-checklist` skill.
   - Check functionality, quality, testing, security, performance, documentation, and consistency.

3. **Document Findings**
   - List issues by severity (critical, medium, suggestions).
   - Provide actionable recommendations.

4. **Give a Verdict**
   - Approve, approve with suggestions, or request changes.

## Output Format

```
## Code Review: [PR or Commit]

### Summary
[Overall assessment]

### Issues Found

#### 🔴 Critical
- [file:line] — [Issue and explanation]

#### 🟡 Medium
- [file:line] — [Issue and explanation]

#### 🟢 Suggestions
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

## Rules

- Be constructive, not critical.
- Prioritize issues by severity.
- Never approve code with critical issues.
- Always check for security and data integrity.
