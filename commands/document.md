---
description: "Create or update technical documentation (README, API docs, guides)."
mode: "command"
---

# Command: /document

When invoked, create or update documentation for the current code.

## Steps

1. **Understand the Feature**
   - Read the code and changes made.
   - Identify the purpose and usage.

2. **Choose Documentation Type**
   - README: Setup, usage, examples.
   - API Docs: Endpoints, schemas, examples.
   - Guides: Tutorials, how-tos.

3. **Write Documentation**
   - Use clear, concise language.
   - Include examples and code snippets.
   - Follow project documentation style.

4. **Update Related Docs**
   - Update README if new features are added.
   - Update API docs if endpoints change.
   - Update guides if workflows change.

## Output Format

```
## Documentation: [Feature or Module]

### Files Created/Updated
- `README.md` — [What was added]
- `docs/api/endpoint.md` — [API documentation]
- `docs/guides/feature.md` — [Tutorial or guide]

### Key Sections
- **Overview**: [What it does]
- **Setup**: [How to configure]
- **Usage**: [How to use]
- **Examples**: [Code snippets]

### Notes
- [Any follow-up documentation needed]
```

## Rules

- Write for the target audience (developers, end-users).
- Include examples and code snippets.
- Keep documentation up-to-date with code.
- Use clear, simple language.
