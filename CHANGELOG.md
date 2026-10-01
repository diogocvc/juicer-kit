# Changelog

## 2.4.0 — 2026-09-30

Security baseline / release candidate. Post-release audit of the kit,
fixed in severity order, one commit per phase:

```text
1a8b7e8   BLOCKER      14a0fe4   HIGH      eb8e264   MEDIUM      b4c0a87   LOW + RC
```

Result: **BLOCKER 0, HIGH 0, MEDIUM 0.** No new features and no
architectural refactors — every change is an audit finding, or a
document brought back in line with the mechanism behind it. The full
threat model, trust boundary and limitation list live in
`docs/security.md`.

The final hardening round below was committed **after** the `v2.4.0`
tag (`ec174d9`); the tag was not moved and no new tag was cut.

### Release flow

- **One canonical order everywhere: `build/package < ship-approve <
  publish/deploy/release`.** `.juicer/workflows/release.md` now builds in
  step 4 and deploys in step 6, `agents/devops.md` splits its old rule 9
  into "build before `ship-approve`" and "verify `ship_approved` before
  deploy/publish/release", and both guides say which `devops` step the
  diagrams mean. The reason is mechanical: `ship-approve` binds
  `git status --porcelain`, so an artifact created after approval
  invalidates it. `docs/security.md` §3 now records that, plus the two
  edges of the binding — ignored paths never bind, a commit invalidates
  by design and a tag does not.
- **`read-only` is documented as a permission level, not a uniform
  capability.** `docs/adapter-contract.md` and `docs/security.md` §6
  carry the per-harness Git-inspection matrix (Claude Code and OpenCode
  have no shell; Codex and Cursor can run non-state-changing commands;
  Zed has no restriction), §8 lists it as a known limitation, and the
  reviewer/debugger/security contracts say to ask the caller for the diff
  when there is no shell. Permission mappings are unchanged.
- **Small fixes:** the CLI docstring still said v2.3, and a sync warning
  was printed once per adapter — four identical lines for `sync all`.
  Both now use the version file's value / print once per process.

### Security

- **Every CLI write is confined.** `bin/juicer` routes its writes through
  `confine_write()` (root, `.juicer/`, `.gitignore`, `AGENTS.md`,
  `copy_missing`, state lock, manifests) and adapter output through
  `confine_generated()`, which additionally refuses `.juicer/`, `.git/`
  and `.gitignore`. A symlink planted in the repository can no longer
  redirect a write outward.
- **`.juicer/` ownership is enforced,** not just documented: only
  manifest-recorded files are ever deleted, and only after every entry
  passes confinement.
- **Adapters own what they write.** `Adapter.owned_paths()` bounds an
  adapter's writes *and* its deletions — checked by `write_generated()`
  during sync, and again when a manifest is loaded, before any read or
  delete. A planted manifest entry cannot remove user source,
  `AGENTS.md` or another harness's settings.
- **Symlinked sources are refused.** A worker or skill resolving outside
  the project and kit roots is refused when a command names it and
  skipped with a warning when `sync` enumerates it, so a committed
  symlink cannot pull outside content into generated harness files.
- **A worker filename is content.** Names must match
  `^[a-z][a-z0-9-]*$` before rendering: the name is embedded in the
  provenance comment and the Codex TOML `name` field, so
  `evil-->inject.md` could otherwise close a comment or inject a key.
- **Permission changes are not silent.** `juicer sync` snapshots the
  permission configuration of every generated file it is about to
  rewrite and warns on stderr when it moves. Those mirrors are
  gitignored, so without this a permission change would be invisible in
  a pull request. The warning reports movement, not direction.

### State integrity

- **`juicer status` is read-only.** It no longer creates
  `.juicer/mission.md` or rewrites `state.json` as a side effect of
  being asked for a status.
- **`juicer mission` writes inside the state lock**, so no reader can
  observe new state with an old mission (or the reverse), and a refused
  mission write leaves the state untouched.

### Approval / gates

- **Approvals are bound to content.** `juicer approve` records the plan
  digest, mission digest and `mission_id`; editing either file
  afterwards invalidates the record until `juicer approve` runs again,
  with the reason reported by `juicer status` and returned by
  `juicer start`. `done` became a valid source state for `approve` so a
  plan edited after `finish` can be re-approved before shipping.
- **Recorded approval ≠ authenticated human approval.** `juicer status`
  prints the plan and ship verdicts on stderr stating what the record
  proves and what it does not. README, both guides and
  `docs/security.md` use the same distinction.
- **Ship approval records `code_binding`** — `sha` in a git repository,
  `failed` when git errors, `none` outside one. The last two are usable
  but warn, in `juicer status` and at approval time: such an approval
  covers plan, mission and unit, not source changes.
- **README no longer claims four enforced gates.** Gates 2 and 3 are
  labelled workflow conventions, with mechanical / convention /
  harness-dependent / recorded-evidence called out per gate.

### Filesystem

- **Nested `init` is refused by default.** The error explains the
  `--nested` opt-in, which creates a separate workspace root on purpose;
  a test asserts the two roots never span.
- **`.gitignore` lists exact generated paths** instead of whole harness
  directories, so `opencode.json`, `.claude/settings.json` and similar
  stay tracked. A stale managed block is rewritten in place and lines
  outside it are never touched.
- **`init` and `render` ship pristine templates** from
  `.juicer/templates/` instead of this repository's live workflow state.

### Adapters

- **`contract_version` 1 → 2** in every kit `adapter.yaml`, with
  `kit.yaml`'s `adapter_contract.version` matching. v2 makes `root=` a
  required keyword on `write_generated()` and binds output to
  `owned_paths()`; `docs/adapter-contract.md` documents the breaking
  change and the migration steps. The field stays metadata —
  `bin/juicer` does not read `adapter.yaml` at runtime.

### CLI

- **Rejection messages say what will not happen.** Manifest failures
  name the deletes and records they prevent instead of the blanket
  "no files touched", which was untrue at one call site.
- **A missing `fcntl` warns once** that the advisory lock is not
  enforced and only the revision fence applies.
- **`juicer capabilities` prints `capabilities (declared)`** — an
  adapter's self-declaration, not a measurement. `discover` is the
  observed half.

### Documentation

- New `docs/security.md`: threat model, trust boundary, approval model
  (targets and invalidation), filesystem boundary, secrets, harness
  permissions with per-harness enforced-vs-convention, prompt-injection
  posture, and 12 known limitations.
- `README.md` gates and security sections rewritten to distinguish
  enforcement, convention, harness dependence and recorded evidence,
  with the trust boundary diagram.
- `docs/GUIDE.md` and `docs/GUIDE.pt-BR.md` are semantically
  synchronized on installation, nested init, approval terminology,
  generated permissions, `status`/`sync` semantics and the security
  model.
- `docs/adapter-contract.md`: contract section retitled, manifest rules
  extended with ownership, v1 → v2 migration added.
- `docs/architecture.md`: sections on locking, root confinement and the
  trust boundary; `security.md` is authoritative where they overlap.
- `docs/installation.md` and `adapters/README.md` reviewed against the
  implementation.

### CI

- Actions pinned to full commit SHA with a version comment,
  `persist-credentials: false`, job timeouts, and `pytest`/`pyyaml`
  pinned to versions supporting 3.8–3.13.
- Matrix is `ubuntu-latest` + `macos-latest` (Python 3.8 excluded on
  macOS — no arm64 build). The sync job still does write-then-check.

### Test suite

183 tests (was 112 at the start of the audit): approval binding, source
trust, ownership, nested-init refusal, read-only status, dry-run purity,
permission-change warnings, template provenance, hostile filenames,
lock-downgrade reporting, gitignore precision and version consistency.

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
