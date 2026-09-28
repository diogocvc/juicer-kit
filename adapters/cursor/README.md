# Cursor Adapter

Cursor is a Juicer harness adapter.

```bash
./bin/juicer sync cursor
```

Canonical state remains `.juicer/`.

Canonical skills remain `.agents/skills/`.

Cursor-native agent features are optional execution mechanisms.

## Behavior

- Subagents are generated into `.cursor/agents/<file>.md`; `name` is
  omitted (derived from the filename), `readonly` marks read-only agents.
- Skills are **not** mirrored: Cursor reads `.agents/skills` natively.
- Entry point: `AGENTS.md`.

## Sources consulted (2026-09-28)

- https://cursor.com/docs/subagents
- https://cursor.com/docs/skills
