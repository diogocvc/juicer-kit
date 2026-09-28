# Installation

## From the repository

Copy Juicer Kit into your project and run:

```bash
./juicer-kit/bin/juicer init
```

Or copy `bin/juicer` somewhere on your PATH.

## OpenCode

```bash
./bin/juicer sync opencode
```

Use native agent invocation for individual workers.

## Claude Code

```bash
./bin/juicer sync claude-code
```

Workers are installed under `.claude/agents/`.

## Cursor

```bash
./bin/juicer sync cursor
```

Cursor can also consume `.agents/skills/` directly.

## Zed

Use either Zed Agent with the portable skills or an external ACP agent. Do not move mission state into Zed-specific configuration.

## Model independence

No role definition hardcodes a model.

Model choice belongs to the harness/session/provider layer.

This is intentional: changing Claude, GPT, Gemini, local models or another provider must not require rewriting the workflow.
