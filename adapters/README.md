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
KIT/adapters/<id>/adapter.py     # shipped with the kit — always loaded
ROOT/adapters/<id>/adapter.py    # embedded by the project — only when trusted
```

A directory with an `adapter.py` exposing `class Adapter` is a valid
adapter. Adding or overriding one never requires editing `bin/juicer`.

`adapter.py` is executable Python: project adapters are imported only
with `--trust-project-adapters` or `JUICER_TRUST_PROJECT_ADAPTERS=1`;
without trust they are skipped with a stderr warning and never
imported. See the `Trust` section of `docs/adapter-contract.md`.

See `docs/adapter-contract.md` for the Python contract
(`capabilities`, `discover`, `sync`, `install`, `invoke`) and for the
sync-safety rules (manifest, stale cleanup, `--dry-run`/`--check`/
`--force`).

## Notes per adapter

Each adapter README documents the harness behavior it targets and the
official sources it was verified against, with the consultation date.
