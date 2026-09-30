# Handoff

Use this file to make a fresh agent session immediately useful.

## Current state

- Mission: security audit → fix → re-test to reach **Security Baseline /
  Release Candidate v2.4.0** (BLOCKER=0, HIGH=0 or documented non-threats).
  Kit repo session only; `.juicer/mission.md` stays the shipped template
  ("No active mission").
- Status: audit complete, Phase 1 (BLOCKER) and Phase 2 (HIGH) committed.
  159 tests green on 3.12, 158 + 1 skip on 3.8. Version still 2.3.0 —
  the bump to 2.4.0 is Phase 4.
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
| M-01 | generated harness perms from project `agents/*.md` in gitignored dirs | pending |
| M-02 | `status` can create `.juicer/mission.md` | pending |
| M-03 | adapter `contract_version` still 1 after `write_generated(path, content, *, root=)` change | pending |
| M-04 | `.gitignore` blanket-ignores `.opencode/ .claude/ .cursor/ .codex/` | pending |
| M-05 | ship code binding absent without git | fixed `14a0fe4` (`code_binding`) |
| M-06 | `cmd_mission` writes state then `mission.md` outside lock | pending |
| M-07 | security test gaps | in progress (new `tests/test_security_baseline.py`) |
| M-08 | CI hygiene (tag-pinned actions, unpinned pip, `persist-credentials`, no timeout, Linux-only) | pending |
| M-09 | init/render use kit's live `.juicer/mission.md`/`plan.md` as templates instead of `.juicer/templates/` | pending |
| L-01..L-07 | wording, `0644` perms, provenance comment injection, TOCTOU, `fcntl` optional, unverified `capabilities()`/`adapter.yaml` unread, doc drift | pending (Phase 4) |

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
  `docs/security.md` (threat model, trust boundary, approval model,
  filesystem boundary, secrets, harness permissions, prompt injection,
  10 known limitations); README/`docs/GUIDE.md` gates rewritten as
  "enforced vs convention"; `tests/test_symlink_escape.py` (9 tests) +
  B-02 ownership cases in `tests/test_path_confinement.py`.
- PHASE 2 `14a0fe4` — approval bound to plan+mission content; untrusted
  sources guarded; nested `init` opt-in; adapter ownership allowlist
  enforced at write time and manifest load time; `code_binding` recorded
  and warned; `status` prints approval verdicts on stderr;
  `tests/test_security_baseline.py` (29 tests); architecture/security
  docs updated.

## What remains

- Phase 3 (MEDIUM): M-01, M-02, M-03, M-04, M-06, M-07, M-08, M-09.
- Phase 4 (LOW / hardening / docs): L-01..L-07, version 2.4.0 across
  `VERSION`, `kit.yaml`, `bin/juicer`, `.juicer/state.json`, README,
  `docs/GUIDE.md`, `docs/GUIDE.pt-BR.md`, `CHANGELOG.md`, tests,
  `adapter.yaml` (`contract_version` 2), `docs/`; final security
  baseline report.
- Requires explicit approval, do not infer: tag, push, release publish.

## Important files

- `bin/juicer` — CLI; write confinement, state locking, approval binding
  (`_approval_target`, `_approval_target_matches`, `_approval_block_reason`),
  `ship_code_binding`, manifest/ownership validation, `cmd_init` nesting.
- `adapters/_base.py` — `confine_path`, `confine_generated`,
  `confine_manifest_entry`, `require_owned`, `ownership_scope`,
  `write_generated`, `trusted_source`, `mirror_skills`, `iter_workers`,
  `Adapter.owned_paths()`.
- `docs/security.md` — the anti-overclaim document; must match behavior.
- `tests/test_security_baseline.py` — H-01..H-05 + M-05 coverage.
- `tests/test_symlink_escape.py`, `tests/test_path_confinement.py` — B-01/B-02.
- `tests/test_states.py`, `tests/test_root_discovery.py`,
  `tests/test_state_integrity.py` — updated for `APPROVE_FROM`,
  nested init and the `target.parts` record shape.
- `.juicer/decisions.md` — all phase decisions; do not re-litigate.
- `.github/workflows/ci.yml` — pytest matrix 3.8/3.12 + sync idempotency.

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
- `handoff.md` carries the MEDIUM/LOW backlog table; Phase 3 and 4 must
  delete entries as they are fixed so it stays a truthful status surface.

## Next action

- Phase 3 (MEDIUM fixes), then Phase 4 (LOW + version 2.4.0 + docs).
- Report the security baseline result to the user and stop. Only tag,
  push or publish if the user explicitly approves it.

## Verification evidence

- `uv run --python 3.12 --with pytest --with pyyaml python -m pytest -q tests`
  → 159 passed.
- Same under `--python 3.8` → 158 passed, 1 skipped.
- Attack replays after Phase 2: plan edit → `Blocked: the plan or mission
  changed after approval`; planted `victim.py` / `.claude/settings.json`
  manifest entries → `is not owned by this adapter`, files survive;
  nested `init` → refuses with `--nested` hint and leaves the outer
  workspace byte-identical; symlinked worker contract → refused; non-git
  `ship-approve` → `code_binding: none` + stderr warning.
