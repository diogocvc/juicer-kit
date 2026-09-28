# Codex Adapter

Codex is a first-class Juicer harness adapter.

## Canonical integration

Codex consumes:

```text
AGENTS.md
.agents/skills/
```

Juicer state remains:

```text
.juicer/
```

Worker contracts remain:

```text
agents/
```

## Native capabilities

The adapter can use Codex's native agent/subagent capabilities where available.

The Juicer core does not depend on them.

## Sync

```bash
./bin/juicer sync codex
```

The adapter is intentionally thin: it should not duplicate the Juicer workflow state.

## Behavior

- Skills are **not** mirrored: Codex reads `.agents/skills` natively.
- Entry point: `AGENTS.md` is native to Codex.
- Custom agents are TOML files under `.codex/agents/` using only the
  documented keys: `name`, `description`, `developer_instructions`,
  `sandbox_mode`. `model` is never emitted.
- `access` maps to `sandbox_mode`:

  | access  | sandbox_mode |
  |---------|--------------|
  | read-only | read-only |
  | edit    | workspace-write |
  | full    | workspace-write |

## Sources consulted (2026-09-28)

- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/guides/agents-md
