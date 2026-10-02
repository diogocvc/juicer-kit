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

## With npm

```bash
npx @juicer-kit/cli install
```

The installer materializes an allowlisted kit payload under
`.juicer-kit/` (gitignored, byte-for-byte idempotent), writes the kit
version and per-file SHA-256 hashes to `.juicer/install.json`, then runs
`python3 .juicer-kit/bin/juicer init`. Python 3.8 or newer is required.
The package ships no `postinstall` scripts; the installer refuses to run
as root unless you pass `--force-root`, and `--yes` does not bypass that
guard.

To move an installed project to a newer kit:

```bash
npx @juicer-kit/cli update
```

Update is manifest-driven: files the manifest proves untouched are
refreshed, files you edited are kept and reported on stderr (`--force`
overwrites them), stale kit files are pruned only while their recorded
hash still matches, and a version downgrade is warned about. A project
without a manifest is adopted conservatively — nothing is overwritten or
pruned. From inside the project, `juicer update` delegates to the same
updater through `npx`. There is no state-schema migration: `.juicer/`
state files keep their current shape across kit updates (documented
limitation).

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
