---
name: security-review
description: Use this skill when auditing code for security vulnerabilities, especially before merging to production. Single source of truth for OWASP Top 10 2021 coverage and security evidence.
---

# Skill: Security Review

This is the **single source of truth** for security auditing in the Juicer Kit.
Agents and commands reference it; they do not duplicate it. It covers OWASP Top
10 2021, OWASP ASVS-style control checks and the structured evidence contract
enforced by the core.

## When to Use

Trigger by **risk**, not only by user choice:

- authentication, authorization, sessions, tokens;
- user data, PII, payments, health or regulated data;
- secrets, keys, certificates, CI/CD trust boundaries;
- external APIs, webhooks, outbound requests, file uploads;
- permission changes, new dependencies, deserialization, crypto;
- infrastructure and deployment configuration.

Run after code review and before merge. Security audit does **not** replace
review; both run when risk applies.

## Severity and Exploitability

| Severity | Definition | Examples |
| --- | --- | --- |
| `critical` | Remotely exploitable with high impact, or a direct secret/data exposure | Auth bypass, SQL injection with data access, leaked private key, RCE |
| `high` | Exploitable with meaningful preconditions or significant data exposure | Stored XSS, IDOR, weak password hashing, SSRF to metadata |
| `medium` | Requires unusual conditions or has limited impact | Missing rate limit, verbose errors, weak session invalidation |
| `low` | Hardening or defense-in-depth gap | Missing security header, verbose log field |

Consider **impact × likelihood**. A theoretical issue with no reachable path is
not `critical`; a reachable auth bypass is never `low`.

## OWASP Top 10 2021 — Required Checklist

### A01 Broken Access Control
- [ ] Every endpoint/command authenticates and authorizes.
- [ ] Object-level authorization (ownership/tenant) is enforced server-side.
- [ ] No IDOR, path traversal, forced browsing or missing function-level check.
- [ ] Deny by default; no client-side-only enforcement.

### A02 Cryptographic Failures
- [ ] No plaintext secrets or sensitive data at rest.
- [ ] Passwords hashed with bcrypt/argon2/scrypt (never MD5/SHA1/plain).
- [ ] Strong, current algorithms and key sizes; no ECB or static IV.
- [ ] TLS for data in transit; no certificate verification bypass.
- [ ] Key rotation and separation of duties defined.

### A03 Injection
- [ ] Parameterized queries/ORM; no string-built SQL.
- [ ] No shell/command injection from user input.
- [ ] No NoSQL/LDAP/XPath/template injection.
- [ ] Output encoded for the correct context (HTML, attribute, JS, URL).
- [ ] Deserialization of untrusted data avoided or constrained.

### A04 Insecure Design
- [ ] Threat model and abuse cases exist for the change.
- [ ] Business-logic limits (quantity, price, sequence) enforced.
- [ ] Rate limits and anti-automation on sensitive flows.
- [ ] Fail closed; least privilege; no trust in client input.

### A05 Security Misconfiguration
- [ ] No debug mode, default credentials or permissive CORS in production.
- [ ] Security headers set (CSP, HSTS, X-Content-Type-Options,
      X-Frame-Options/frame-ancestors, Referrer-Policy).
- [ ] Error responses do not leak stack traces or internals.
- [ ] Cloud/storage permissions are least privilege.

### A06 Vulnerable and Outdated Components
- [ ] New/changed dependencies are pinned and maintained.
- [ ] No known critical advisory for the version in use.
- [ ] Lockfile updated and reviewed.
- [ ] Unmaintained packages have a migration plan.

### A07 Identification and Authentication Failures
- [ ] Credential storage and comparison are safe.
- [ ] Session/token lifetime, rotation and revocation are defined.
- [ ] MFA available for sensitive operations.
- [ ] Brute-force/credential-stuffing protections exist.
- [ ] Password reset and account recovery are not bypassable.

### A08 Software and Data Integrity Failures
- [ ] CI/CD artifacts and actions pinned by digest/SHA.
- [ ] Updates and plugins are signature/integrity checked.
- [ ] No unsafe deserialization or unsigned code execution.
- [ ] Supply-chain provenance is known (SLSA-style where applicable).

### A09 Security Logging and Monitoring Failures
- [ ] Auth failures, authorization denials and sensitive changes are logged.
- [ ] Logs exclude secrets, tokens and unnecessary PII.
- [ ] Alerts exist for the new failure modes.
- [ ] Log integrity and retention meet policy.

### A10 Server-Side Request Forgery (SSRF)
- [ ] Outbound URLs are allowlisted/validated.
- [ ] Private IPs, localhost, link-local and cloud metadata endpoints blocked.
- [ ] Redirects constrained; DNS rebinding considered.
- [ ] Response size/time bounded.

## Additional Control Checks

- **Secrets**: none hardcoded, committed, logged or passed on command lines;
  environment/secret store used; rotation path documented.
- **Input validation**: schema validation at the trust boundary; allowlist over
  denylist.
- **Rate limiting**: public and auth endpoints; `429` with retry guidance.
- **CSRF**: state-changing cookie-auth requests protected.
- **File upload**: type/size/content checks; stored outside the web root;
  malware scanning where applicable.
- **Multi-tenancy**: tenant isolation in queries, caches and jobs.
- **Privacy**: data minimization, retention, deletion and consent honored.

## Evidence Contract

The core accepts only a structured verdict linked to the commit/tree:

```json
{"verdict": "PASS", "findings": [{"severity": "medium", "description": "A05 Security Misconfiguration: ...", "file": "...", "line": 0}], "summary": "..."}
```

- `verdict`: `PASS` or `FAIL`.
- `severity`: `critical`, `high`, `medium`, `low`.
- Include the OWASP category in each finding description.
- Any `critical` finding forces `FAIL`.
- If scope, diff or threat context is missing, return `FAIL` with a `critical`
  finding starting with `BLOCKED:`.
- `NOT RUN`, stale or malformed evidence is not a pass.
- Prose outside the JSON block is ignored by the core.

## Scope and Uncertainty

- Audit only `scope.paths`. A control that depends on out-of-scope code is
  `UNKNOWN`, with the exact path that would be needed.
- "No finding" means "no finding in this diff", not "the system is secure".
- State the limits: files reviewed, data classification, threat assumptions.
- Never invent a threat model, compliance obligation or data classification.
- Report `UNKNOWN` or `BLOCKED`; never guess.

## Output Format

```
## Security Review Report

### Scope and Evidence
- Commit/tree:
- Files reviewed:
- Data classification / trust boundaries:
- Limits of this review:

### Critical Issues
- [file:line] — [OWASP ID, exploit path, required control]

### High / Medium Issues
- [file:line] — [OWASP ID and impact]

### Recommendations
- [Hardening or defense-in-depth]

### OWASP Top 10 2021 Coverage
- [ ] A01 ... A10 (list each)

### UNKNOWN / Open Questions
- [Control not verified and the evidence needed]

## Verdict
- [ ] Approved (no critical issues)
- [ ] Approved with recommendations
- [ ] Changes required
```

## References

- OWASP Top 10 2021 — https://owasp.org/Top10/
- OWASP ASVS — https://owasp.org/www-project-application-security-verification-standard/
- OWASP Cheat Sheet Series — https://cheatsheetseries.owasp.org/
- NIST Secure Software Development Framework (SSDF), SP 800-218.
- CIS Benchmarks for infrastructure.
