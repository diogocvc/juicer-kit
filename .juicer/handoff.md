# Handoff

Use this file to make a fresh agent session immediately useful.

## Current state

- Mission: 7-phase correction plan, Juicer Kit v2.1.0 → 2.2.0 (init/paths,
  adapter registry, frontmatter generation, sync safety, state machine,
  tests+CI, docs+version). Kit repo session only; `.juicer/mission.md` stays
  the shipped template ("No active mission").
- Unit: FASE 6 complete, awaiting user approval for FASE 7.
- Status: 5 commits on main, all tests green.

## What was completed

- FASE 1 `63f17f4` — self-contained init, worker path resolution (root → kit).
- FASE 2 `0e9949e` — registry-driven adapters, kit/project discovery,
  `install`/`invoke` subcommands.
- FASE 3 `fcd8f19` — harness-native frontmatter from canonical `access`/`tier`.
- FASE 4 `c95b77d` — manifest-based sync safety: `--dry-run`, `--check`,
  `--force`, conflict reporting.
- FASE 5 `8473563` — workflow state machine; every gate validates its source
  state (tables in `docs/architecture.md` §3); `tests/test_states.py`.
- FASE 6 (this commit) — CI workflow, valid `adapters/*/adapter.yaml`
  (schema + capability-drift test), `tomllib` test skips below 3.11.

## What remains

- FASE 7 — docs pass (GUIDE, adapter-contract stale notes), bump VERSION,
  `kit.yaml`, `CHANGELOG.md` and `kit_version` in `state.json`/`bin/juicer`
  to 2.2.0. Stop for approval afterwards.

## Important files

- `bin/juicer` — CLI, state machine constants near the top of command section.
- `.github/workflows/ci.yml` — pytest matrix 3.8/3.12 + sync idempotency.
- `tests/` — 52 tests (`pytest -q tests`; 51 + 1 skip under 3.8).
- `.juicer/decisions.md` — all phase decisions; do not re-litigate.

## Decisions that must not be revisited

- Manifest-based sync never deletes untracked or user-edited files without
  `--force`; `AGENTS.md` is project-owned and never tracked.
- OpenCode generation defaults to legacy `permission:` map until issue
  #50598 applies V2 `permissions:`.
- Generated files must never contain `role:`, `access:`, `tier:`, `model:`.
- State changes only through gated commands; approval is never inferred.

## Known problems

- `docs/adapter-contract.md` still says "manifest-based cleanup (later
  phase)" although FASE 4 shipped it — fix in FASE 7.
- Harness mirrors are gitignored, so CI cannot detect a stale local mirror;
  the write-then-check job only proves determinism.

## Next action

- Request approval for FASE 7; then execute it: docs sweep, 2.2.0 version
  bump (`VERSION`, `kit.yaml`, `.juicer/state.json`, `bin/juicer` banner and
  `ensure_runtime` default), `CHANGELOG.md` entry, full pytest + `sync
  all --check`, single commit.

## Verification evidence

- `uv run --python 3.12 --with pytest --with pyyaml python -m pytest -q tests`
  → 52 passed.
- Same under `--python 3.8` → 51 passed, 1 skipped.
- `./bin/juicer sync all --check` → all adapters up to date.
- Clean `git clone` verified the CI sync flow (write, then check → 0).
