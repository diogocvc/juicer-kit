# Handoff

Use this file to make a fresh agent session immediately useful.

## Current state

- Mission: security audit → fix → re-test to reach **Security Baseline /
  Release Candidate v2.4.0** (BLOCKER=0, HIGH=0, MEDIUM=0). Kit repo
  session only; `.juicer/mission.md` stays the shipped template
  ("No active mission").
- Status: **all four phases complete and tested.** Version is 2.4.0.
  174 tests green on 3.12, 173 + 1 skip on 3.8. Phase 4 is written but
  not yet committed — see "What remains".
- Not done, and explicitly forbidden until told otherwise: no tag, no
  push, no release publish.

## Audit findings and where they stand

Severity rules: BLOCKER includes root escape, arbitrary file access, state
corruption and *false security guarantees in critical areas*. RC requires
BLOCKER=0 and HIGH=0 (or explicitly documented non-threats).

| ID | Finding | Status |
|---|---|---|
| B-01 | core writes unconfined (symlink escape) | fixed `1a8b7e8` |
| B-02 | `.juicer/` ownership not enforced despite doc claim | fixed `1a8b7e8` |
| B-03 | README "four mandatory gates" overclaim; `HUMAN APPROVAL` wording | fixed `1a8b7e8` |
| H-01 | plan approval target unbound | fixed `14a0fe4` |
| H-02 | symlink-following reads in `mirror_skills`/`iter_workers`/`find_worker` | fixed `14a0fe4` |
| H-03 | silent nested `init` | fixed `14a0fe4` (`--nested` opt-in) |
| H-04 | manifest can delete arbitrary user files | fixed `14a0fe4` (ownership allowlist) |
| H-05 | approval model implies identity authentication | fixed `14a0fe4` (status provenance) + `docs/security.md` §3/§8 |
| M-01 | generated harness perms from project `agents/*.md` in gitignored dirs | fixed `eb8e264` (permission snapshot + stderr warning) |
| M-02 | `status` can create `.juicer/mission.md` | fixed `eb8e264` (read-only) |
| M-03 | adapter `contract_version` still 1 after the `root=` change | fixed `eb8e264` (2, documented) |
| M-04 | `.gitignore` blanket-ignores `.opencode/ .claude/ .cursor/ .codex/` | fixed `eb8e264` (exact paths, in-place rewrite) |
| M-05 | ship code binding absent without git | fixed `14a0fe4` (`code_binding`) |
| M-06 | `cmd_mission` writes state then `mission.md` outside lock | fixed `eb8e264` (same lock) |
| M-07 | security test gaps | fixed `eb8e264` + Phase 4 (174-test suite) |
| M-08 | CI hygiene (floating actions, unpinned pip, `persist-credentials`, no timeout, Linux-only) | fixed `eb8e264` |
| M-09 | init/render use the kit's live `.juicer/mission.md`/`plan.md` as templates | fixed `eb8e264` (`.juicer/templates/`) |
| L-01 | "(no files touched)" claims a guarantee one call site cannot make | fixed (Phase 4) — messages state exactly what will not happen |
| L-02 | `.juicer/` files created `0644` | fixed (Phase 4) — documented as a read-permission note, `docs/security.md` §8.11 |
| L-03 | worker filename injected into provenance comment / Codex TOML `name` | fixed (Phase 4) — `WORKER_NAME` enforced in `iter_workers` |
| L-04 | TOCTOU on path confinement | documented, not fixed — `docs/security.md` §4 and §8.6 |
| L-05 | `fcntl` optional, degradation silent | fixed (Phase 4) — one-time stderr warning |
| L-06 | `capabilities()` declared, not measured; `adapter.yaml` unread at runtime | fixed (Phase 4) — `capabilities (declared)` + contract note |
| L-07 | doc drift (structure tree, install, guides, version references) | fixed (Phase 4) |

## What was completed

- Audit — architecture/README/GUIDE/adapter-contract, all adapters
  (`adapters/_base.py` + 5), `bin/juicer`, workers/skills/workflows,
  tests, CI, git history. Baseline 112 passed on 3.12 and 3.8.
- Plan approved with these decisions: nested `init` refuses by default
  with `--nested`; non-git `ship-approve` works with a clear warning and
  `code_binding`; version 2.4.0; **no** `juicer ship --verify`; commits
  grouped per phase with tests green each time; keep
  `docs/GUIDE.pt-BR.md` in sync; no features/refactors beyond the fixes;
  never claim `SECURITY BASELINE: PASS` while a BLOCKER exists.
- PHASE 1 `1a8b7e8` — `confine_write()` choke point for every CLI write;
  `confine_generated()` adds protected `.juicer/`, `.git/`, `.gitignore`
  to adapter writes; `_prune_empty_dirs` root-guarded; new
  `docs/security.md`; README/`docs/GUIDE.md` gates rewritten as
  "enforced vs convention"; `tests/test_symlink_escape.py` (9 tests) +
  B-02 ownership cases in `tests/test_path_confinement.py`.
- PHASE 2 `14a0fe4` — approval bound to plan+mission content; untrusted
  sources guarded; nested `init` opt-in; adapter ownership allowlist
  enforced at write time and manifest load time; `code_binding` recorded
  and warned; `status` prints approval verdicts on stderr;
  `tests/test_security_baseline.py`; architecture/security docs updated.
- WORKFLOW `c6eea2c` — handoff + two learnings committed separately so
  state text never rides along in a code commit.
- PHASE 3 `eb8e264` — permission-change warning, read-only `status`,
  `contract_version` 2, precise `.gitignore`, mission write inside the
  lock, SHA-pinned CI + macos matrix, `.juicer/templates/` sources.
- PHASE 4 (this change) — L-01/L-02/L-03/L-05/L-06/L-07 fixed; version
  2.4.0 across `VERSION`, `kit.yaml`, `bin/juicer`, `.juicer/state.json`,
  README, both guides, `CHANGELOG.md`, `tests/test_cli.py`; `adapter.yaml`
  `contract_version` was already 2; `kit.yaml` `adapter_contract.version`
  1 → 2 to match it.

## What remains

- Commit PHASE 4 (version + LOW/hardening/docs), message pattern
  `chore(security): …`. Nothing else is in flight.
- Report the security baseline result to the user.
- Requires explicit approval, do not infer: tag, push, release publish.

## Important files

- `bin/juicer` — CLI; write confinement, state locking, approval binding
  (`_approval_target`, `_approval_target_matches`, `_approval_block_reason`),
  `ship_code_binding`, manifest/ownership validation, `cmd_init` nesting,
  `PROJECT_MIRRORS`/`GITIGNORE_MARKER`, `MISSION_TEMPLATE`/`PLAN_TEMPLATE`,
  `PERMISSION_KEYS`/`_permission_snapshot`, `capabilities (declared)`.
- `adapters/_base.py` — `confine_path`, `confine_generated`,
  `confine_manifest_entry`, `require_owned`, `ownership_scope`,
  `write_generated`, `trusted_source`, `mirror_skills`, `iter_workers`
  (with `WORKER_NAME` validation), `Adapter.owned_paths()`.
- `docs/security.md` — the anti-overclaim document; must match behavior.
- `docs/GUIDE.md` + `docs/GUIDE.pt-BR.md` — must move together on any
  security/approval change (decision 2026-09-30).
- `tests/test_security_baseline.py` — B/H/M/L coverage; the first place
  to add a regression test for a new security claim.
- `tests/test_symlink_escape.py`, `tests/test_path_confinement.py` — B-01/B-02.
- `tests/test_states.py`, `tests/test_root_discovery.py`,
  `tests/test_state_integrity.py` — updated for `APPROVE_FROM`,
  nested init and the `target.parts` record shape.
- `.juicer/decisions.md` — all phase decisions; do not re-litigate.
- `.github/workflows/ci.yml` — pytest matrix 3.8/3.12 on ubuntu + macos,
  SHA-pinned actions, pinned deps, plus the sync idempotency job.

## Decisions that must not be revisited

- Project adapters are untrusted by default; trust is explicit (flag or
  env), never inferred (decision 2026-09-28 — Project adapters untrusted).
- OpenCode legacy permission map keys are `edit`/`bash` (V1); V2 rules use
  `action: shell`; default stays legacy until issue #50598 applies V2.
- Ship gate = recorded approval + agent-side verification; `finish` does
  not require `ship_approved` (decision 2026-09-28 — Ship gate).
- Manifest-based sync never deletes untracked or user-edited files without
  `--force`; `AGENTS.md` is project-owned and never tracked.
- An adapter may only write/delete inside the paths it declares
  (`agents_dir`, `skills_dir`, marker file); undeclared output is rejected.
- Nested `juicer init` requires `--nested`; root separation is guaranteed
  by test, not by convention.
- Non-git `ship-approve` keeps working, warns, and records
  `code_binding: "none"`/`"failed"`; it is never described as equivalent
  to git-bound approval.
- Generated files must never contain `role:`, `access:`, `tier:`, `model:`.
- State changes only through gated commands; approval is never inferred.
- CI sync gate is write-then-check (mirrors are gitignored).
- The permission warning reports a *change*, not a widen/narrow judgement;
  direction is not inferred (decision 2026-09-30 — Permission warning).
- A worker filename must match `^[a-z][a-z0-9-]*$` before it is rendered,
  because the name is embedded in generated content.
- Never claim `SECURITY BASELINE: PASS` while any BLOCKER is open; never
  turn a limitation into a guarantee.

## Known problems

- `.juicer/handoff.md` (and `decisions.md`) ship to new projects via
  `juicer init` `copy_missing`, so kit-session text lands in project
  templates. Pre-existing pattern; needs a design decision before changing.
- Harness mirrors are gitignored, so CI cannot detect a stale local mirror;
  the write-then-check job only proves determinism.
- V2 OpenCode `permissions:` is parsed but not applied upstream (#50598);
  re-check when bumping the default.
- Path confinement is TOCTOU-prone by construction: the check resolves a
  path that a later write re-resolves. Documented in `docs/security.md`
  §4/§8.6, not solved — solving it needs `O_NOFOLLOW`/`openat` discipline.
- The fcntl-downgrade warning cannot be exercised on POSIX CI; it is
  covered by a test that runs the CLI with `sys.modules['fcntl'] = None`.

## Next action

- Commit Phase 4, then report the security baseline result to the user
  and stop. Only tag, push or publish if the user explicitly approves it.

## Verification evidence

- `uv run --python 3.12 --with pytest --with pyyaml python -m pytest -q tests`
  → 174 passed.
- Same under `--python 3.8` → 173 passed, 1 skipped.
- `./bin/juicer sync all && ./bin/juicer sync all --check` → all five
  adapters up to date, exit 0 (mirrors the CI sync job).
- `pyflakes` on `bin/juicer`, `adapters/*.py`, `tests/*.py` → only the
  five pre-existing warnings carried from before this mission.
- Attack replays after Phase 2: plan edit → `Blocked: the plan or mission
  changed after approval`; planted `victim.py` / `.claude/settings.json`
  manifest entries → `is not owned by this adapter`, files survive;
  nested `init` → refuses with `--nested` hint and leaves the outer
  workspace byte-identical; symlinked worker contract → refused; non-git
  `ship-approve` → `code_binding: none` + stderr warning.
- Attack replays after Phase 4: `agents/evil-->inject.md` → skipped with
  `must match ^[a-z][a-z0-9-]*$`, no harness file and no manifest entry
  for it; `juicer status` creates nothing; changing `access:` on a worker
  → `permission configuration changed: …` on stderr.
