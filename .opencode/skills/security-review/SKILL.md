---
name: security-review
description: Use this skill when auditing code for security vulnerabilities, especially before merging to production.
---

# Skill: Security Review

Use this skill when auditing code for security vulnerabilities, especially before merging to production.

## Checklist

### 🔴 Critical (Must Fix)

- [ ] **Injection**: No SQL, NoSQL, OS, or LDAP injection vulnerabilities.
  - All user inputs are validated and sanitized.
  - Parameterized queries or ORM are used (no string concatenation for SQL).
- [ ] **Authentication**: Auth flow is secure.
  - Passwords are hashed with bcrypt/argon2 (never plain text or MD5/SHA1).
  - JWT tokens have short expiration and are stored securely (not in localStorage).
  - Rate limiting is implemented on auth endpoints.
- [ ] **Sensitive Data**: PII and secrets are protected.
  - No hardcoded API keys, passwords, or secrets in code.
  - Secrets are loaded from environment variables.
  - Sensitive data is encrypted at rest and in transit (HTTPS/TLS).
- [ ] **Access Control**: Authorization is enforced.
  - Every endpoint checks user permissions.
  - No direct object references (e.g., `/api/user/:id` without ownership check).

### 🟡 Medium (Should Fix)

- [ ] **XSS**: Output is escaped/encoded.
  - No `innerHTML` or `dangerouslySetInnerHTML` with user input.
  - Framework's built-in escaping is used (React, Vue, etc.).
- [ ] **CSRF**: CSRF tokens are implemented on state-changing operations.
  - Especially for cookie-based auth.
- [ ] **Error Handling**: Errors do not leak sensitive information.
  - No stack traces in production responses.
  - Generic error messages for users, detailed logs for developers.
- [ ] **Dependencies**: No known vulnerabilities in dependencies.
  - Run `npm audit` or equivalent.
  - Update packages with critical vulnerabilities.

### 🟢 Recommendations (Nice to Have)

- [ ] **Security Headers**: Headers like `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security` are set.
- [ ] **Logging**: Security events are logged (failed logins, permission denials, etc.).
- [ ] **Input Validation**: All inputs are validated with a schema library (Zod, Yup, Joi).
- [ ] **Rate Limiting**: Rate limiting is implemented on public endpoints.

## Output Format

After review, provide:

```
## Security Review Report

### 🔴 Critical Issues
- [Issue with file:line and explanation]
- [OWASP reference if applicable]

### 🟡 Medium Issues
- [Issue with file:line and explanation]

### 🟢 Recommendations
- [Security improvement suggestion]

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
