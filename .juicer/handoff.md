# Handoff

Use this file to make a fresh agent session immediately useful.

## Current state

- Mission: 7-phase correction plan, Juicer Kit v2.1.0 → 2.2.0 — **complete**.
  Kit repo session only; `.juicer/mission.md` stays the shipped template
  ("No active mission").
- Unit: FASE 7 (docs + version bump) done in this commit; awaiting user
  decision on tagging/pushing.
- Status: 7 commits on main, all tests green, version 2.2.0 everywhere.

## What was completed

- FASE 1 `63f17f4` — self-contained init, worker path resolution (root → kit).
- FASE 2 `0e9949e` — registry-driven adapters, kit/project discovery,
  `install`/`invoke` subcommands.
- FASE 3 `fcd8f19` — harness-native frontmatter from canonical `access`/`tier`.
- FASE 4 `c95b77d` — manifest-based sync safety: `--dry-run`, `--check`,
  `--force`, conflict reporting.
- FASE 5 `8473563` — workflow state machine; every gate validates its source
  state (tables in `docs/architecture.md` §3); `tests/test_states.py`.
- FASE 6 `2c3772e` — CI workflow, valid `adapters/*/adapter.yaml`
  (schema + capability-drift test), `tomllib` test skips below 3.11.
- FASE 7 (this commit) — docs pass (GUIDE EN/pt-BR: CLI `install`/`invoke`,
  state-machine note, adapter tree, v2.2 strings; adapter-contract stale
  note; installation Python floor), `CHANGELOG.md`, version 2.2.0 in
  `VERSION`, `kit.yaml`, `.juicer/state.json`, `bin/juicer` (3 sites +
  docstring), README, strengthened `test_version_files`.

## What remains

- Nothing inside the approved scope. Possible follow-ups (require explicit
  approval, do not infer): tag `v2.2.0`, push to origin, publish, fix the
  `handoff.md`-ships-to-projects template concern.

## Important files

- `bin/juicer` — CLI; state-machine constants at the top of the command
  section; version literals in docstring, two `kit_version` defaults and
  the init banner (guarded by `test_version_files`).
- `.github/workflows/ci.yml` — pytest matrix 3.8/3.12 + sync idempotency.
- `tests/` — 52 tests (`pytest -q tests`; 51 + 1 skip under 3.8).
- `CHANGELOG.md` — release history for 2.2.0 and 2.1.0.
- `.juicer/decisions.md` — all phase decisions; do not re-litigate.

## Decisions that must not be revisited

- Manifest-based sync never deletes untracked or user-edited files without
  `--force`; `AGENTS.md` is project-owned and never tracked.
- OpenCode generation defaults to legacy `permission:` map until issue
  #50598 applies V2 `permissions:`.
- Generated files must never contain `role:`, `access:`, `tier:`, `model:`.
- State changes only through gated commands; approval is never inferred.
- CI sync gate is write-then-check (mirrors are gitignored).

## Known problems

- `.juicer/handoff.md` (and `decisions.md`) ship to new projects via
  `juicer init` `copy_missing`, so kit-session text lands in project
  templates. Pre-existing pattern; needs a design decision before changing.
- Harness mirrors are gitignored, so CI cannot detect a stale local mirror;
  the write-then-check job only proves determinism.

## Next action

- Report FASE 7 results to the user and stop. Only proceed with
  tag/push/release if the user explicitly approves it.

## Verification evidence

- `uv run --python 3.12 --with pytest --with pyyaml python -m pytest -q tests`
  → 52 passed.
- Same under `--python 3.8` → 51 passed, 1 skipped.
- `./bin/juicer sync all --check` → all adapters up to date.
- `git ls-files | xargs grep 2.1.0` → only this handoff's historical note.
