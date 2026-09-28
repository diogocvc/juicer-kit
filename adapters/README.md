# Harness Adapters

Adapters translate Juicer Kit's portable contracts into native harness conventions.

They must remain thin.

## Source of truth

- `.juicer/`
- `agents/`
- `.agents/skills/`

## Generated targets

- OpenCode: `.opencode/`
- Claude Code: `.claude/`
- Cursor: `.cursor/`
- Zed: `.zed/` documentation/config guidance only

Do not put workflow state inside an adapter.
