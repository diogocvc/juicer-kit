# Security model

This document states what Juicer Kit protects, what it delegates, and
what it cannot protect at all. It exists so that no claim in the README
or the guides outruns the mechanism behind it.

Wording rule used throughout: a control is **mechanical** only when
`bin/juicer` (or the harness, or the OS) refuses the operation. Anything
that depends on an agent or a human choosing to comply is labelled a
**convention**.

### What Juicer controls

Exactly four things:

- which paths the CLI and adapters are allowed to write;
- which files a sync is allowed to delete;
- which state transitions are legal;
- what gets recorded when a command claims an approval.

Everything else — the OS boundary, the harness's permission system,
whether a person is at the keyboard, what an agent decides to do with
file contents — is outside Juicer. It is either delegated explicitly
(§2) or listed as a limitation (§8). This document does not describe
intended behaviour; every sentence here is meant to be greppable in
`bin/juicer`, `adapters/_base.py` or `tests/`.

---

## 1. Threat model

| Actor | Description | What Juicer does about it |
|---|---|---|
| A — cooperative agent | follows the documented workflow | state machine + manifest safety keep ordinary mistakes contained |
| B — erratic agent | wrong command, wrong path, prompt injection | path confinement, state fencing, gate transitions, approval records |
| C — malicious agent | deliberately forges state, bypasses gates, escalates | revision fence + approval records detect tampering *after the fact*; nothing stops a process that can write the file outright |
| D — compromised project | hostile content already in the repository | symlink and traversal confinement, adapter trust default-deny, manifest ownership rules |
| E — concurrent process | two `juicer` runs at once | `flock` + atomic rename + monotonic revision |

Assets: files outside `.juicer/`, workflow state and its approval gates,
generated harness permission configuration, secrets reachable from the
project, and the host environment.

## 2. Trust boundary

```text
┌──────────────────────────────────────┐
│ HUMAN / EXTERNAL AUTHORITY           │  decides what is approved
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│ HARNESS / OS / ENVIRONMENT           │  isolation, shell perms, OS boundary
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│ JUICER CORE                          │  state, workflow, gates, audit
└──────────────────┬───────────────────┘
                   ▼
                PROJECT
```

### Juicer core guarantees

- Every file the CLI writes resolves strictly inside the project root.
  Symlinks planted in the repository cannot redirect a write outward
  (`.juicer/`, `.gitignore`, `AGENTS.md`, `copy_missing` targets, the
  state lock and the manifest are all checked before the write).
- `state.json` is written atomically (tmp + fsync + rename) under an
  exclusive `flock`, with a monotonic revision fence: a stale writer
  fails instead of silently resurrecting old state.
- Gate commands validate the transition table before writing; illegal
  transitions exit 1.
- Adapters (including trusted project adapters) may write only inside
  the root, and never into `.juicer/`, `.git/` or `.gitignore`.
- Only manifest-recorded files are ever deleted, and only after every
  manifest entry passes confinement.
- Project `adapters/*.py` is executable Python and is **not imported**
  unless `--trust-project-adapters` or `JUICER_TRUST_PROJECT_ADAPTERS=1`
  is given.

### Harness / environment guarantees (not Juicer's)

- OS-level isolation, container/sandbox boundaries, network egress.
- Filesystem permissions outside the working directory.
- Whether a shell command is allowed, prompted or denied.
- Whether a worker marked `read-only` can actually write.

Juicer writes configuration that many harnesses honour (see §6), but it
cannot verify that the harness applies it.

### Human guarantees

- The decision to approve. Juicer records `by`, `at`, `via` and a target
  digest; it does **not** authenticate the person behind `by`.

## 3. Approval model

`juicer approve` (a **Recorded Plan Approval**) and `juicer ship-approve`
(a **Recorded Ship Approval**) write a provenance record:

```json
{ "by": "<id>", "at": "<iso8601>", "via": "interactive|automation",
  "revision": <int>, "target": { "parts": { … }, "digest": "sha256…" } }
```

- `via: interactive` is only used when stdin is a TTY and `--by` was not
  given; the OS username becomes `by`.
- `via: automation` is used whenever `--by=<id>` is passed.
- With no TTY and no `--by`, the command exits 1. Nothing is recorded.

### The approved target

The record does not float: it names the exact content it covers.

| Approval | `target.parts` |
|---|---|
| Plan (`juicer approve`) | `plan` = sha256 of `.juicer/plan.md`, `mission` = sha256 of `.juicer/mission.md`, `mission_id` |
| Ship (`juicer ship-approve`) | `plan`, `mission`, `current_unit`, and — inside a git repository — `git_head` + a digest of `git status --porcelain` with `.juicer/` artifacts removed |

### Invalidation

- Editing `.juicer/plan.md` or `.juicer/mission.md` after `approve`
  changes the digests, so the approval no longer matches. `juicer status`
  reports `approved invalidated: plan or mission changed after approval`
  and `juicer start` refuses with `the plan or mission changed after
  approval`.
- `approve` re-records against the current content; there is no override
  flag.
- Ship approval is re-checked before every state write while
  `ship_approved` is true (`_refresh_ship_approval`): if plan, mission,
  active unit or the git state moved, the flag is set back to `false`
  before the write.
- A missing or malformed record has the same effect as an invalidated
  one — the flag is ignored, never trusted on its own.
- `.juicer/` itself is excluded from the git-dirty component, so Juicer's
  own persistence can never invalidate an approval by itself.

**What a record proves:** that a process identifying itself as `by`
produced an approval for a specific target, at a specific state revision,
through a valid transition.

**What it does not prove:** that a human was at the keyboard. Anyone who
can run `./bin/juicer approve --by=<anybody>` and write to the repository
can produce a syntactically valid record. `.juicer/state.json` is an
ordinary working-tree file with no signature; its integrity is the OS
file permission on the repository, nothing more.

### Recorded approval vs. authenticated human approval

A **recorded** approval is data Juicer wrote and can re-verify
afterwards. An **authenticated** approval would require proving who
attested — a signature, an SSO assertion, a hardware key. Juicer does
neither. The `by` field is a declared identity, `via` says only how the
value was supplied, and neither is checked against an identity provider.
Adding out-of-band confirmation belongs to the harness (§6).

Treat `via: automation` and unexpected `by` values as signals to review,
not as authorization.

## 4. Filesystem boundary

- **Root discovery** walks up from the working directory looking for
  `.juicer/state.json`. Gate commands fail cleanly when there is no
  workspace; they never create one as a side effect.
- `juicer init` targets the current directory. Creating a workspace
  underneath an existing one requires `--nested`.
- Every CLI write goes through `confine_write()` → `confine_path()`,
  which resolves the destination and rejects anything outside the root.
- Adapter output additionally goes through `confine_generated()`, which
  rejects `.juicer/`, `.git/` and `.gitignore`.
- Adapter output must also sit inside the paths that adapter declares
  as its own (`agents_dir`, `skills_dir`, its marker file). The rule is
  enforced at **write** time by `write_generated()` and again at **load**
  time for manifest entries, before any read or delete. An adapter can
  therefore only generate inside its own directories, and a planted
  manifest entry cannot remove user source, `AGENTS.md` or another
  harness's settings. (`AGENTS.md` itself is `manifest=False`:
  project-owned, never recorded, never deleted by sync.)
- Worker contracts and mirrored skills are read through symlinks. A
  source that resolves outside the project and the kit is refused when a
  command names it (`juicer worker <name>`) and skipped with a warning
  when `sync` enumerates workers or mirrors skills, so a committed
  symlink cannot pull outside content into a generated file.
- A worker filename must match `^[a-z][a-z0-9-]*$` before it is
  rendered. The name is embedded in generated content — the provenance
  comment and the Codex TOML `name` field — so a name like
  `evil-->inject.md` could otherwise close a comment or inject a key.
  Non-matching names are skipped with a warning.
- `juicer init` writes a managed `.gitignore` block listing the exact
  paths Juicer generates, never whole harness directories, so
  configuration the project owns (`opencode.json`,
  `.claude/settings.json`, …) stays tracked. A stale block is rewritten
  in place; lines outside it are untouched.
- Known limit: confinement resolves symlinks and then writes. A process
  that swaps a path component for a symlink in that window can still win
  (TOCTOU). Defeating that requires `O_NOFOLLOW`/directory-fd discipline
  or an OS sandbox, which is the harness's job.

## 5. Secrets

Juicer reads exactly one environment variable,
`JUICER_TRUST_PROJECT_ADAPTERS`. It does not load `.env` files, does not
read credentials, and does not copy environment values into
`state.json`, `handoff.md`, `decisions.md`, `learnings.md` or CLI output.

Nothing stops an *agent* from writing a secret it found elsewhere into a
`.juicer/*.md` file — those files are agent-authored content. Keep them
out of commits, or scan before committing. There is no secret scanner in
this repository.

## 6. Harness permissions

Juicer generates per-worker permission configuration from the canonical
`access:` field in `agents/*.md`. What each harness does with it:

| Harness | Artefact | Enforced by the harness? |
|---|---|---|
| OpenCode (legacy, default) | `permission: {edit, bash}` frontmatter | yes |
| OpenCode (V2, `--opencode-format v2`) | `permissions:` list | **no** — parsed but not applied upstream (opencode issue #50598) |
| Claude Code | `tools:` frontmatter | yes |
| Cursor | `readonly: true` | yes |
| Codex | `sandbox_mode` | yes |
| Zed | none | **no** — no subagent permission support |

Two caveats:

1. The source of `access:` is `agents/*.md`, which is project-owned
   content. Changing it changes the generated permissions; `juicer sync`
   snapshots the permission configuration of every file it is about to
   rewrite and warns when it moves. The warning does not judge direction
   — widening and narrowing look the same, so read the change yourself.
2. The generated artefacts are gitignored, so they are not reviewed in a
   pull request. Review `agents/*.md` instead; the sync warning is the
   in-repo signal that the effective configuration changed.

To make `juicer approve` / `juicer ship-approve` require an out-of-band
confirmation, configure it in the harness — for example a Claude Code
`permissions` rule that asks before running those exact commands, or an
OpenCode agent whose `permission.bash` is `ask`. Juicer does not write
that configuration for you; substituting harness config is out of scope.

## 7. Prompt injection and untrusted content

Untrusted input (anything a compromised repository can control):

```text
agents/*.md          .agents/skills/**        AGENTS.md
.juicer/*.md         .juicer/workflows/*.md   adapters/*/adapter.py
```

### Mechanical protections

- A worker's canonical frontmatter is never copied into generated files.
  `role:`, `access:`, `tier:` and `model:` are refused in every generated
  artefact (`tests/test_frontmatter.py`), so repository content cannot
  smuggle keys into a harness's permission surface. `access:` is the only
  permission input, and it is re-rendered into each harness's fixed
  schema rather than passed through.
- A worker filename must match `^[a-z][a-z0-9-]*$` before rendering, so
  a name cannot break out of the provenance comment or the Codex TOML
  `name` field.
- Sources resolving outside the project and the kit are refused or
  skipped (§4), so a committed symlink cannot exfiltrate outside content
  into a generated file.
- Project `adapters/*/adapter.py` is not imported unless
  `--trust-project-adapters` or `JUICER_TRUST_PROJECT_ADAPTERS=1` is
  given.

### What a recorded approval gates

- `juicer start` refuses without a valid Recorded Plan Approval.
- Release skills and workflows must read `ship_approved` from
  `juicer status` before a production-impacting step.

Neither stops an agent that is already following instructions it found
in a file: a prompt can ask an agent to run `juicer approve` itself, and
`juicer approve` will happily record it (§3). A recorded approval binds
*what* was approved; it never establishes *who* approved it.

### Harness-protected

Anything the harness's own permission model gates — shell, edit, network
— is where a real barrier lives. Juicer writes configuration for several
of those surfaces (§6) but cannot verify that the harness applies it.

### Residual

Juicer cannot stop an agent from treating file contents as
instructions. Separating data from instruction is the harness's and the
operator's responsibility.

## 8. Known limitations

1. **No identity authentication.** `by` is self-declared. A human and an
   agent can produce equally valid records.
2. **`state.json` is unsigned.** Any process with write access can forge
   `approved: true` plus a matching record. Detection exists (revision
   binding, target digests) but is not tamper-proof against a writer.
3. **Gate 2 and Gate 3 are conventions.** The CLI does not verify scope
   or test evidence.
4. **The ship gate is advisory to consumers.** The CLI prints the flag;
   it cannot make another process stop.
5. **Code binding requires git.** Outside a git repository — or when
   `git` fails — ship approval records `code_binding: "none"` /
   `"failed"` and `juicer status` warns. Such an approval covers plan,
   mission and unit only, **not** source changes.
6. **TOCTOU on path confinement.** See §4.
7. **Locking is POSIX-only.** Without `fcntl` the advisory lock degrades
   to a no-op; concurrent writers then rely on the revision fence alone.
8. **No network or sandbox controls.** Juicer runs with your privileges.
9. **No secret scanning.** See §5.
10. **OpenCode V2 `permissions` is not applied upstream.** The legacy
    `permission` map is the only enforced form today.
11. **Workflow files are created with the process umask** (typically
    `0644`): other local users can *read* `state.json`, the approval
    records and the mission/plan, but cannot write them. None of these
    files is treated as secret — see §5.
