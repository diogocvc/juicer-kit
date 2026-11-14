---
description: "Review code changes with the code-review-checklist skill."
agent: reviewer
---

# Command: /review

**Core integration.** Use `juicer review-run TASK-XXX` (or
`juicer review TASK-XXX --commit <hash> --tree-hash <hash>`) for automated
evidence recorded against the task commit/tree. This command is the **manual**
equivalent for work outside the core; the structured JSON block is the only
format the core accepts as evidence.

When invoked, review the given code changes using the `code-review-checklist`
skill. It is the single source of truth for dimensions and severity; do not
restate it from memory. Run after deterministic checks and before merge; this
command is read-only.

## Steps

1. **Read the changes**
   - Review all modified and new files.
   - Confirm which commit/tree is being reviewed.
   - Confirm the changed files are inside `scope.paths`.

2. **Apply the checklist**
   - Use the `code-review-checklist` skill (Google Engineering Practices).
   - Check design, functionality, complexity, tests, naming, comments, style,
     documentation and consistency.
   - Cross-check security-relevant changes against OWASP Top 10 2021 and the
     `security-review` skill; do not perform the security audit yourself.

3. **Verify evidence**
   - Confirm tests/checks ran against the same commit/tree.
   - Treat missing, stale or `NOT RUN` evidence as a blocker, never a pass.
   - Confirm whether the `security` gate is declared and evidenced when risk
     applies.

4. **Document findings**
   - List issues by severity (critical, high, medium, low).
   - Cite `file:line`, impact and the required change.

5. **Give a verdict**
   - Approve, approve with suggestions, or request changes.
   - Critical findings require changes.

## Output Format

```
## Code Review: [Commit/Tree]

### Scope and Evidence
- Commit/tree:
- Files reviewed:
- Deterministic checks: [status and source]
- Security gate: [declared? evidence?]

### Findings

#### Critical
- [file:line] — [Issue, impact and required change]

#### High / Medium
- [file:line] — [Issue and impact]

#### Low / Suggestions
- [file:line] — [Improvement]

### Checklist
- [x] Functionality
- [x] Code quality
- [ ] Testing (missing edge case coverage)
- [x] Security cross-check
- [x] Performance
- [x] Documentation
- [x] Consistency

### UNKNOWN / Open Questions
- [What could not be verified and why]

## Verdict
- [ ] Approved
- [ ] Approved with minor suggestions
- [ ] Changes requested (see critical/medium issues)
```

## Rules

- Be constructive and specific; prioritize by severity.
- Never approve code with critical issues.
- Never convert `NOT RUN` or missing evidence into a pass.
- Never edit files; report findings.
- Never waive a core gate; this command produces evidence only.
- For core evidence, emit exactly one fenced `json` block with
  `{"verdict": "...", "findings": [...], "summary": "..."}`.
