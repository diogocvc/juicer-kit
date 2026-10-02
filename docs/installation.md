# Installation

Requires Python 3.8 or newer (CI runs the test suite on 3.8 and 3.12).

## From the repository

Clone Juicer Kit into your project:

```bash
git clone https://github.com/diogocvc/juicer-kit
```

Then run:

```bash
./juicer-kit/bin/juicer init
```

The initializer refuses to run in a subdirectory of an existing Juicer
workspace; pass `--nested` to create a separate workspace root there on
purpose. It writes a managed `.gitignore` block that lists only the
paths Juicer generates, so harness configuration you own stays tracked.

To run `juicer` from any directory, add the kit's `bin/` directory to
your `PATH`. The CLI imports `adapters/` relative to its own location,
so `bin/juicer` must stay inside the kit.

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
