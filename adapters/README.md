# Harness Adapters

Adapters translate Juicer Kit's portable contracts into native harness conventions.

They must remain thin.

## Source of truth

- `.juicer/`
- `agents/`
- `.agents/skills/`
- `AGENTS.md`

## Generated targets

- OpenCode: `.opencode/` (agents only; skills are read natively)
- Claude Code: `.claude/` (agents + skills mirror)
- Cursor: `.cursor/` (agents only; skills are read natively)
- Codex: `AGENTS.md` entrypoint only
- Zed: `AGENTS.md` guidance only (no subagents)

Do not put workflow state inside an adapter.

## Discovery

`bin/juicer` loads adapters from:

```text
KIT/adapters/<id>/adapter.py     # shipped with the kit
ROOT/adapters/<id>/adapter.py    # embedded by the project (wins on collision)
```

A directory with an `adapter.py` exposing `class Adapter` is a valid
adapter. Adding or overriding one never requires editing `bin/juicer`.

See `docs/adapter-contract.md` for the Python contract
(`capabilities`, `discover`, `sync`, `install`, `invoke`).

## Notes per adapter

Each adapter README documents the harness behavior it targets and the
official sources it was verified against, with the consultation date.
