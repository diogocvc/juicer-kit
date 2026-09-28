# Changelog

## 2.3.0 — 2026-09-28

Security and coverage release over 2.2.0 (post-release audit). Three
phases, one commit each.

### Security

- Project adapters are untrusted by default: `ROOT/adapters` loads only
  with `--trust-project-adapters` or `JUICER_TRUST_PROJECT_ADAPTERS=1`.
  Without trust, project `adapter.py` files are never imported (stderr
  warning lists them) and targeting one fails with `untrusted project
  code`; `juicer init` in an untrusted repository no longer executes
  project code. Deduplicated by resolved path, so `ROOT == KIT` is silent.

### Fixed

- OpenCode legacy `permission:` map used the key `shell`, which no schema
  reads; it now uses the V1 key `bash` (V1→V2 maps `bash` → `shell`), so
  shell rules (`read-only deny`, `edit ask`) are applied again after
  re-sync. Docs table and `test_frontmatter` corrected with it.
- Corrupt `.juicer/state.json` exits 1 with `Invalid state file …` instead
  of a Python traceback.

### Changed

- Ship gate is now verifiable: the `ship` skill, the release workflow and
  `agents/devops.md` require `ship_approved: true` (via `juicer status`)
  before production-impacting steps, with the release approval moved
  before `devops`; README Gate 4 and GUIDE §7 document the
  recorded-approval model. `finish` remains independent of ship approval.

### Added

- State-machine tests for blocked branches, idempotent gates,
  `ship-approve` from blocked/done and unknown status rejection.
- Adapter tests: `invoke` for all five harnesses, missing-binary
  `discover`, drift check for every manifest-tracked adapter, Claude
  provenance marker.
- Invariants: all 16 workers share the operating contract and Output
  block; ship-gate consumers mention `ship_approved`.
- Trust tests: default skip + warning, flag and env opt-in, targeted
  failure, `init` security regression (72 tests total).

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
