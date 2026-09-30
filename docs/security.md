# Security model

This document states what Juicer Kit protects, what it delegates, and
what it cannot protect at all. It exists so that no claim in the README
or the guides outruns the mechanism behind it.

Wording rule used throughout: a control is **mechanical** only when
`bin/juicer` (or the harness, or the OS) refuses the operation. Anything
that depends on an agent or a human choosing to comply is labelled a
**convention**.

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
│ HARNESS / ENVIRONMENT                │  isolation, shell perms, OS boundary
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

`juicer approve` and `juicer ship-approve` write a provenance record:

```json
{ "by": "<id>", "at": "<iso8601>", "via": "interactive|automation",
  "revision": <int>, "target": { "digest": "sha256…", … } }
```

- `via: interactive` is only used when stdin is a TTY and `--by` was not
  given; the OS username becomes `by`.
- `via: automation` is used whenever `--by=<id>` is passed.
- With no TTY and no `--by`, the command exits 1. Nothing is recorded.

**What a record proves:** that a process identifying itself as `by`
produced an approval for a specific target, at a specific state revision,
through a valid transition.

**What it does not prove:** that a human was at the keyboard. Anyone who
can run `./bin/juicer approve --by=<anybody>` and write to the repository
can produce a syntactically valid record. `.juicer/state.json` is an
ordinary working-tree file with no signature; its integrity is the OS
file permission on the repository, nothing more.

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
  source that resolves outside the project and the kit is refused (worker
  lookup) or skipped with a warning (skills mirror), so a committed
  symlink cannot exfiltrate arbitrary files into generated output.
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
   warns when a worker's access widens.
2. Generated harness directories are gitignored, so these files are not
   reviewed in a pull request. Review `agents/*.md` instead.

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

Protected operations that require a recorded approval:

```text
juicer approve       juicer ship-approve
```

Harness-protected: anything the harness's own permission model gates
(shell, edit, network), which is where a real barrier lives.

Residual: Juicer cannot stop an agent from treating file contents as
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
