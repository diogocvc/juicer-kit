# Changelog

## 2.4.0 — 2026-09-30

Security baseline / release candidate. Post-release audit: three
severity passes plus a hardening pass, one commit per phase
(`1a8b7e8` BLOCKER, `14a0fe4` HIGH, `eb8e264` MEDIUM, plus this one).
**BLOCKER 0, HIGH 0, MEDIUM 0.** No new features; every change is an
audit finding or a document/test that keeps a claim from outrunning the
mechanism behind it.

### Security — BLOCKER

- **Every write is confined.** `bin/juicer` routes all writes through
  `confine_write()` (root, `.juicer/`, `.gitignore`, `AGENTS.md`,
  `copy_missing`, state lock, manifests) and all adapter output through
  `confine_generated()`, which additionally refuses `.juicer/`, `.git/`
  and `.gitignore`. A symlink planted in the repository can no longer
  redirect a write outward.
- **`.juicer/` is owned by Juicer.** Only files recorded in the runtime
  manifests may be deleted, and only after every manifest entry passes
  confinement.
- **README no longer claims four enforced gates.** Gate 2 (scope) and
  Gate 3 (verification) are labelled workflow conventions;
  `docs/security.md` is the authority for what is mechanical.

### Security — HIGH

- **Approvals are bound to content.** `juicer approve` and
  `juicer ship-approve` record the plan and mission digests; editing
  either afterwards invalidates the record until approval runs again,
  with the reason shown by `juicer status`.
- **Symlinked sources are refused.** Workers and skills resolving
  outside the project or kit root are skipped with a warning instead of
  being rendered into harness files.
- **Nested `init` is refused by default.** It explains the `--nested`
  opt-in, which creates a separate workspace root on purpose and never
  spans two roots silently.
- **Adapters own what they write.** `Adapter.owned_paths()` bounds an
  adapter's writes *and* its deletions at write time, at manifest load
  time and at apply time — checked before any read or delete, not after.
- **Approval ≠ authentication.** `juicer status` states plainly what the
  record proves (a process named itself) and what it does not.

### Fixed

- **Ship approval records `code_binding`** (`sha` / `failed` / `none`).
  Outside a git repository it stays usable but warns, and `juicer status`
  repeats the warning: such an approval covers plan, mission and unit,
  not source changes.
- **`juicer status` is read-only** — it no longer creates
  `.juicer/mission.md` or rewrites `state.json` as a side effect of being
  asked for a status.
- **`juicer mission` writes inside the state lock**, so no reader can
  observe new state with an old mission or the reverse, and a refused
  mission write leaves state untouched.
- **`sync` warns when generated permissions change.** Permission-bearing
  lines are snapshotted before every rewrite and reported on stderr;
  generated mirrors are gitignored, so without this a permission change
  would be invisible in a pull request.
- **`.gitignore` lists exact generated paths** instead of whole harness
  directories, so `opencode.json`, `.claude/settings.json` and friends
  stay tracked. A stale managed block is rewritten in place.
- **`init` and `render` ship pristine templates** (`.juicer/templates/`)
  instead of this repository's live workflow state.
- **Adapter `contract_version` 1 → 2**, documented in the adapter
  contract: `write_generated()` requires `root=` and output is bound to
  `owned_paths()`.
- **A hostile filename can no longer reach generated content.** Worker
  names must match `^[a-z][a-z0-9-]*$` before they are rendered — the
  name travels into the provenance comment and the Codex TOML `name`
  field, so it could otherwise close a comment or inject a key.
- **Manifest rejection messages are accurate**: they say what will not
  happen (nothing read, deleted, recorded) rather than the blanket
  "no files touched", which was false for one call site.
- **A missing `fcntl` now warns once** that the advisory lock is not
  enforced and only the revision fence applies.
- **`juicer capabilities` prints `capabilities (declared)`** — the
  values are an adapter's self-declaration, not a measurement;
  `discover` is the observed half.

### Changed

- **CI**: actions pinned to full commit SHA with a version comment,
  `persist-credentials: false`, job timeouts, `pytest`/`pyyaml` pinned to
  versions that support 3.8–3.13, and a `macos-latest` matrix entry
  (3.8 excluded — no arm64 build).
- **Security test coverage** grew to 174 tests: approval binding, source
  trust, ownership, nested-init refusal, read-only status, dry-run
  purity, permission-change warnings, template provenance, hostile
  filenames and lock-downgrade reporting.
- `docs/security.md` states the threat model, trust boundary, approval
  model, harness-permission matrix and the full list of limitations.
- `docs/GUIDE.md` and `docs/GUIDE.pt-BR.md` are synchronized on the
  security and approval model.

### Not in this release

- No `juicer ship --verify`; release verification stays with the release
  skills and workflows.
- No identity authentication, no secret scanner, no network or sandbox
  controls — documented in `docs/security.md` §8, not implied.

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
