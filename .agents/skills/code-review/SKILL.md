---
name: code-review
description: Review a change for correctness, regressions, security, maintainability and missing tests without modifying files.
---

# Code Review

Inspect the current diff and active unit.

Report findings in severity order:

- blocking correctness issue
- security issue
- regression
- missing test
- maintainability issue
- observation

Every finding must include file and line/context when available.

Do not modify files.
