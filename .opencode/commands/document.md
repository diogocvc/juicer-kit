---
description: "Create or update technical documentation (README, API docs, guides)."
---

# Command: /document

**Core integration.** Documentation is not a core gate. This command may run
manually at any point; when a task declares documentation as an acceptance
criterion, the core still validates the underlying behavior and checks. Do not
document behavior that is not implemented or verified.

## Steps

1. **Understand the feature**
   - Read the code and the accepted change set.
   - Identify the audience (developer, operator, end user) and the task.

2. **Confirm scope**
   - Write only inside `scope.paths` (normally `docs/`, `README.md` or
     docstrings in changed files).
   - If a doc lives outside scope, report `BLOCKED` instead of editing it.

3. **Choose documentation type**
   - README: setup, usage, examples.
   - API reference: endpoints, schemas, errors, auth, versioning.
   - Guide: task-oriented tutorial or how-to.
   - ADR/decision log: context and consequences.

4. **Write documentation**
   - Lead with the user outcome; keep examples runnable.
   - Follow the project's existing style and terminology.
   - State versions, prerequisites and limitations.
   - Add migration notes for user-visible changes.

5. **Verify accuracy**
   - Every command and code sample must match the current code.
   - Do not invent flags, responses or defaults.
   - If behavior is ambiguous or unverified, mark it `UNKNOWN` and ask.

6. **Update related docs**
   - README for new features.
   - API docs for endpoint/schema changes.
   - Guides for changed workflows.
   - Changelog for user-visible changes.

## Output Format

```
## Documentation: [Feature or Module]

### Files Created/Updated
- `README.md` — [What was added]
- `docs/api/endpoint.md` — [API documentation]
- `docs/guides/feature.md` — [Tutorial or guide]

### Key Sections
- Overview:
- Setup:
- Usage:
- Examples:
- Limitations:

### Verification
- Commands/examples checked against:
- Behavior not verified / UNKNOWN:

### Notes
- [Follow-up documentation needed]
```

## Rules

- Write for the target audience.
- Include runnable examples and code snippets.
- Keep documentation consistent with the current code.
- Never document unverified behavior as fact.
- Never leave `scope.paths` without reporting `BLOCKED`.
- Use clear, simple language.
