---
description: "Audit code for security vulnerabilities (OWASP, auth, PII, secrets)."
mode: "command"
---

# Command: /security-audit

When invoked, perform a security audit using the `security-review` skill.

## Steps

1. **Identify Sensitive Areas**
   - Authentication/authorization code.
   - Data handling (PII, encryption).
   - External API integrations.
   - Secret management.

2. **Review for Vulnerabilities**
   - Use the `security-review` skill checklist.
   - Check for OWASP Top 10 issues.

3. **Document Findings**
   - List vulnerabilities by severity.
   - Reference OWASP when applicable.

4. **Give a Verdict**
   - Approve, approve with recommendations, or require changes.

## Output Format

```
## Security Audit: [Module or Feature]

### 🔴 Critical Issues
- [file:line] — [Issue and OWASP reference]
- [file:line] — [Issue and OWASP reference]

### 🟡 Medium Issues
- [file:line] — [Issue and explanation]

### 🟢 Recommendations
- [Security improvement suggestion]

### Compliance
- [ ] OWASP Top 10 addressed
- [ ] PII protection verified
- [ ] Secrets management secure

## Verdict
- [ ] Approved (no critical issues)
- [ ] Approved with recommendations
- [ ] Changes required (critical issues found)
```

## Rules

- Never approve code with critical vulnerabilities.
- Reference OWASP Top 10 when applicable.
- Be thorough — security is not optional.
- If unsure, flag it and ask for clarification.
