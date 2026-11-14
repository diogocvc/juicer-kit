---
name: code-review-checklist
description: Use this skill when reviewing code to ensure consistency and quality. Single source of truth for review dimensions, severity and evidence.
---

# Skill: Code Review Checklist

This is the **single source of truth** for code review in the Juicer Kit.
Agents and commands reference it; they do not duplicate it. It is based on
Google Engineering Practices — *The Standard of Code Review*, *What to Look for
in a Code Review* and *How to Do a Code Review* — plus the review evidence
contract enforced by the core.

## When to Use

- After deterministic checks and before merge, for every change set.
- Read-only: review produces findings and a verdict, never edits.
- The change set is pinned to a commit/tree and a `scope.paths` list.

## Review Order

1. **Contract** — read the task, acceptance criteria and scope first.
2. **Diff** — read every changed line in context, not only the summary.
3. **Tests** — verify tests exist, are deterministic and actually exercise the
   change.
4. **Evidence** — confirm checks ran against the same commit/tree.
5. **Risk** — apply the security cross-check when the change is sensitive.
6. **Verdict** — classify findings and decide.

## Dimensions (Google Engineering Practices)

### Design
- [ ] Fits the existing architecture and conventions.
- [ ] No premature abstraction; the simplest design that works.
- [ ] No duplicated source of truth or parallel code path.
- [ ] Interfaces and data ownership are explicit.

### Functionality
- [ ] Does what the contract and acceptance criteria say.
- [ ] Edge cases: null, empty, limits, concurrency, retries, partial failure.
- [ ] Error handling is explicit; failures do not corrupt state.
- [ ] No behavior change that the contract did not authorize.

### Complexity
- [ ] Functions and classes are small enough to reason about.
- [ ] No unnecessary indirection, flags or configuration.
- [ ] Control flow is readable; no deeply nested conditionals.

### Tests
- [ ] Tests cover the new behavior, edge cases and errors.
- [ ] Tests are deterministic (no sleeps, clocks, network, ordering).
- [ ] Tests assert behavior, not implementation details.
- [ ] A bug fix has a regression test that fails without the fix.
- [ ] No skipped, weakened or deleted tests to get green.

### Naming
- [ ] Names describe intent and domain meaning.
- [ ] No misleading abbreviations or generic `data`/`manager`/`handle`.
- [ ] Consistent with the surrounding codebase.

### Comments
- [ ] Explain *why* and non-obvious constraints, not *what*.
- [ ] No stale or misleading comments.
- [ ] Public APIs are documented where the project requires it.

### Style
- [ ] Formatter/linter output is clean.
- [ ] Imports, ordering and file layout follow conventions.
- [ ] No debug prints, dead code or commented-out blocks.

### Documentation
- [ ] User-visible behavior and migration notes updated.
- [ ] API/schema changes reflected in reference docs.
- [ ] Changelog updated when the project requires it.

### Every Line and Context
- [ ] Every changed line was read.
- [ ] Callers, consumers and adjacent code were checked.
- [ ] Removed code is understood, not just deleted.

## Correctness and Safety Cross-checks

- [ ] Inputs validated at trust boundaries.
- [ ] Authorization checked at object level, not only authentication.
- [ ] Secrets not hardcoded, logged or exposed in errors.
- [ ] Resource cleanup (files, connections, locks, transactions).
- [ ] Timeouts, retries and idempotency for external calls.
- [ ] Data migrations are backward compatible or gated.

## Security Cross-check (OWASP Top 10 2021)

The `security-review` skill owns the audit. During review, verify that the
`security` gate is **declared and evidenced** when the change touches:

- A01 Broken Access Control
- A02 Cryptographic Failures
- A03 Injection
- A04 Insecure Design
- A05 Security Misconfiguration
- A06 Vulnerable and Outdated Components
- A07 Identification and Authentication Failures
- A08 Software and Data Integrity Failures
- A09 Security Logging and Monitoring Failures
- A10 Server-Side Request Forgery (SSRF)

Do not substitute a review for the security audit.

## Severity Rubric

| Severity | Definition | Examples | Effect |
| --- | --- | --- | --- |
| `critical` | Exploitable vulnerability, data loss, broken core contract, or missing mandatory evidence | Auth bypass, secret leak, destructive migration, `NOT RUN` checks | Forces `FAIL`; blocks merge |
| `high` | Likely production defect or major gap with no workaround | Race condition, unhandled failure path, missing authorization on a secondary path | Should block; requires explicit decision |
| `medium` | Real defect or maintainability risk with a workaround | Missing edge case, unclear error, duplicated logic | Fix before merge or record a tracked follow-up |
| `low` | Improvement or style issue | Naming, comment, small simplification | Optional; never blocks |

Rules:

- Severity reflects **impact and likelihood**, not reviewer preference.
- One critical finding forces `FAIL`, regardless of the number of positives.
- Do not inflate style preferences to `medium`; do not downgrade a security
  issue to avoid blocking.

## Evidence Contract

The core accepts only a structured verdict linked to the commit/tree:

```json
{"verdict": "PASS", "findings": [{"severity": "medium", "description": "...", "file": "...", "line": 0}], "summary": "..."}
```

- `verdict`: `PASS` or `FAIL`.
- `severity`: `critical`, `high`, `medium`, `low`.
- Every finding includes a description; `file`/`line` when applicable.
- Any `critical` finding forces `FAIL`.
- Missing, stale, malformed or `NOT RUN` evidence is not a pass.
- If the commit/tree/diff cannot be established, return `FAIL` with a
  `critical` finding starting with `BLOCKED:`.
- Prose outside the JSON block is ignored by the core.

## What Review Is Not

- Not a substitute for tests, security audit or human approval.
- Not a place to redesign the feature; record a follow-up instead.
- Not a style-only pass; correctness and evidence come first.
- Not an approval by exhaustion; "looks fine" without evidence is not a review.

## Manual Output Format

```
## Review Summary
[Commit/tree, scope, overall assessment]

## Findings

### Critical
- [file:line] — [Finding, impact, required change]

### High / Medium
- [file:line] — [Finding and impact]

### Low / Suggestions
- [file:line] — [Improvement]

## Evidence Checked
- Commit/tree:
- Deterministic checks:
- Security gate:

## UNKNOWN / Open Questions
- [What could not be verified]

## Verdict
- [ ] Approved
- [ ] Approved with minor suggestions
- [ ] Changes requested
```

## References

- Google Engineering Practices: *The Standard of Code Review*, *What to Look
  for in a Code Review*, *How to Do a Code Review*.
- OWASP Top 10 2021 and OWASP ASVS (see `security-review`).
- Project conventions and the task contract.
