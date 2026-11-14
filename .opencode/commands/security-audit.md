---
description: "Audit code for security vulnerabilities (OWASP Top 10 2021, auth, PII, secrets)."
agent: security
---

# Command: /security-audit

**Core integration.** Use `juicer security-run TASK-XXX` (or
`juicer security TASK-XXX --commit <hash> --tree-hash <hash>`) for automated
evidence recorded against the task commit/tree. This command is the **manual**
equivalent for work outside the core; only the structured JSON block is
accepted as core evidence.

When invoked, perform a security audit using the `security-review` skill. It is
the single source of truth for the OWASP Top 10 2021 checklist, severity
rubric and evidence contract; do not restate it from memory.

## Steps

1. **Identify sensitive areas**
   - Authentication/authorization code.
   - Data handling (PII, encryption, retention).
   - External API and outbound-request integrations.
   - Secret management and CI/CD trust boundaries.
   - New or changed dependencies.

2. **Review for vulnerabilities**
   - Use the `security-review` skill checklist.
   - Cover all OWASP Top 10 2021 categories (A01–A10).
   - Reference ASVS/NIST where a control needs a precise criterion.

3. **Confirm scope and evidence**
   - Audit only `scope.paths`; report `UNKNOWN` when a control depends on code
     outside scope.
   - Confirm the commit/tree and that the review gate ran.

4. **Document findings**
   - List vulnerabilities by severity with `file:line`, exploit path and
     required control.
   - Reference the OWASP category.

5. **Give a verdict**
   - Approve, approve with recommendations, or require changes.
   - Never approve with a critical finding.

## Output Format

```
## Security Audit: [Module or Feature]

### Scope and Evidence
- Commit/tree:
- Files reviewed:
- Data classification / trust boundaries:
- Review gate: [declared? evidence?]

### Critical Issues
- [file:line] — [OWASP ID, exploit path and required control]

### High / Medium Issues
- [file:line] — [OWASP ID and impact]

### Recommendations
- [Hardening or defense-in-depth suggestion]

### OWASP Top 10 2021 Coverage
- [ ] A01 Broken Access Control
- [ ] A02 Cryptographic Failures
- [ ] A03 Injection
- [ ] A04 Insecure Design
- [ ] A05 Security Misconfiguration
- [ ] A06 Vulnerable and Outdated Components
- [ ] A07 Identification and Authentication Failures
- [ ] A08 Software and Data Integrity Failures
- [ ] A09 Security Logging and Monitoring Failures
- [ ] A10 Server-Side Request Forgery (SSRF)

### UNKNOWN / Open Questions
- [Control that could not be verified and the evidence needed]

## Verdict
- [ ] Approved (no critical issues)
- [ ] Approved with recommendations
- [ ] Changes required (critical/high issues found)
```

## Rules

- Never approve code with critical vulnerabilities.
- Reference OWASP Top 10 2021 explicitly.
- Never substitute for `/review`; both run when risk applies.
- Never edit files; report findings.
- If unsure, report `UNKNOWN` or `BLOCKED`; never guess.
- For core evidence, emit exactly one fenced `json` block with
  `{"verdict": "...", "findings": [...], "summary": "..."}`.
