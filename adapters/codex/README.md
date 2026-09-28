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
