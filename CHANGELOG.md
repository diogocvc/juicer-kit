# Changelog

## 2.2.0 — 2026-09-28

Correction and hardening release over 2.1.0. Seven phases, one commit each.

### Fixed

- `juicer init` is self-contained: backfills missing canonical files
  (`.juicer/`, `agents/`, `.agents/skills`, `AGENTS.md`) and resolves worker
  paths from the project first, then the kit.
- Shipped `adapters/*/adapter.yaml` were invalid YAML; rewritten with the
  documented schema (`id`, `contract_version`, `capabilities`,
  `canonical_*`) and validated in CI.

### Added

- Registry-driven adapters: discovery from `KIT/adapters` and
  `ROOT/adapters` (project wins on id collision) with no `bin/juicer`
  changes; `juicer install <adapter>` and `juicer invoke <adapter> <worker>`.
- Harness-native frontmatter generated from canonical `access`/`tier` for
  OpenCode, Claude Code, Cursor, Codex (TOML) and Zed; generated files never
  carry `role:`, `access:`, `tier:` or `model:`.
- Manifest-based sync safety: `--dry-run`, `--check` (exit 1 on drift),
  `--force`; user-edited and unmanaged files are never deleted silently.
- Workflow state machine: every gate command validates its source state and
  exits 1 with `Cannot <command> from status=<state>`; `juicer status` lists
  the commands available in the current state (docs/architecture.md §3).
- CI: pytest on Python 3.8 and 3.12 plus a sync determinism job
  (`sync all`, then `sync all --check`); tests parse every `adapter.yaml`
  and fail on capability drift between YAML and Python.

### Changed

- `start` requires state `ready`/`blocked` and is rejected while executing
  (one active unit); approval is still checked first (`Blocked:` message).
- `checkpoint ready|done` clears `current_unit`; `checkpoint` targets have
  explicit source states; `ship-approve` is allowed only from `ready`/`done`.

## 2.1.0 — 2026-09-28

Initial v2 release: harness-agnostic core (`.juicer/`, `agents/`,
`.agents/skills`, `bin/juicer`), five adapters (OpenCode, Claude Code,
Cursor, Codex, Zed), 16 workers and 7 portable skills.
