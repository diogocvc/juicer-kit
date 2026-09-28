# Handoff

Use this file to make a fresh agent session immediately useful.

## Current state

- Mission: post-audit correction plan, Juicer Kit v2.2.0 → 2.3.0 —
  **complete** (3 grouped phases, one commit each). Kit repo session only;
  `.juicer/mission.md` stays the shipped template ("No active mission").
- Unit: FASE 3 (docs + release 2.3.0) done in this commit; awaiting user
  decision on tagging/pushing.
- Status: 3 commits on main after `d7695a8` (v2.2.0), all tests green,
  version 2.3.0 everywhere.

## What was completed

- FASE 1 `94d0d2e` — trust model C3 (project adapters untrusted by
  default: `--trust-project-adapters` / `JUICER_TRUST_PROJECT_ADAPTERS=1`,
  stderr warning, `untrusted project code` failure, resolved-path
  dedupe); OpenCode legacy permission key `shell` → `bash`; corrupt state
  fails cleanly; docs `Trust` sections; decisions + learning entries.
- FASE 2 `ce91bd3` — ship gate consumers (`ship` skill, release workflow,
  `agents/devops.md` rule 9) verify `ship_approved`; README Gate 4 and
  GUIDE §7 document the recorded-approval model; state-machine coverage
  (blocked/idempotent/ship/unknown-status); invoke ×5, missing-binary
  discover, drift ×4, claude provenance; worker + ship-consumer
  invariants; decision entry for ship option A.
- FASE 3 (this commit) — adapter-contract `capabilities()` wording
  (declared, `discover()` reports the environment); README init mirrors
  workers + skills; GUIDE EN/pt-BR v2.3 strings; `CHANGELOG.md` 2.3.0;
  version 2.3.0 in `VERSION`, `kit.yaml`, `.juicer/state.json`,
  `bin/juicer` (docstring, two `kit_version` defaults, init banner),
  `test_version_files` pin.

## What remains

- Nothing inside the approved scope. Possible follow-ups (require
  explicit approval, do not infer): tag `v2.3.0`, push to origin,
  publish; upstream OpenCode enforcement of V2 `permissions` (#50598);
  optional worker-contract refactor (out of scope, invariant test now
  guards drift); `handoff.md`-ships-to-projects template concern.

## Important files

- `bin/juicer` — CLI; trust model (`load_adapters`, `_fail_unknown_adapter`,
  `--trust-project-adapters` on the six loader subcommands); state-machine
  constants; version literals in docstring, two `kit_version` defaults and
  the init banner (guarded by `test_version_files`).
- `.github/workflows/ci.yml` — pytest matrix 3.8/3.12 + sync idempotency.
- `tests/` — 72 tests (`pytest -q tests`; 71 + 1 skip under 3.8).
- `CHANGELOG.md` — release history for 2.3.0, 2.2.0 and 2.1.0.
- `.juicer/decisions.md` — all phase decisions; do not re-litigate.

## Decisions that must not be revisited

- Project adapters are untrusted by default; trust is explicit (flag or
  env), never inferred (decision 2026-09-28 — Project adapters untrusted).
- OpenCode legacy permission map keys are `edit`/`bash` (V1); V2 rules use
  `action: shell`; default stays legacy until issue #50598 applies V2.
- Ship gate = recorded approval + agent-side verification; `finish` does
  not require `ship_approved` (decision 2026-09-28 — Ship gate).
- Manifest-based sync never deletes untracked or user-edited files without
  `--force`; `AGENTS.md` is project-owned and never tracked.
- Generated files must never contain `role:`, `access:`, `tier:`, `model:`.
- State changes only through gated commands; approval is never inferred.
- CI sync gate is write-then-check (mirrors are gitignored).

## Known problems

- `.juicer/handoff.md` (and `decisions.md`) ship to new projects via
  `juicer init` `copy_missing`, so kit-session text lands in project
  templates. Pre-existing pattern; needs a design decision before changing.
- Harness mirrors are gitignored, so CI cannot detect a stale local mirror;
  the write-then-check job only proves determinism.
- V2 OpenCode `permissions:` is parsed but not applied upstream (#50598);
  re-check when bumping the default.

## Next action

- Report FASE 3 results to the user and stop. Only proceed with
  tag/push/release if the user explicitly approves it.

## Verification evidence

- `uv run --python 3.12 --with pytest --with pyyaml python -m pytest -q tests`
  → 72 passed.
- Same under `--python 3.8` → 71 passed, 1 skipped.
- `./bin/juicer sync all --check` → all adapters up to date.
- `git grep -I 2.2.0` → no stale version references outside CHANGELOG
  history.
