# Tests

Run:

```bash
python -m pytest tests
```

The tests focus on structural guarantees:

- portable core exists
- worker contracts exist
- skills have valid frontmatter
- adapters implement the contract markers
- Codex integration uses the universal entrypoint
- core structure is independent of individual harnesses
