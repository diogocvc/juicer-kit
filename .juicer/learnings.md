# Learnings

Keep durable, reusable engineering knowledge here.

## Format

### YYYY-MM-DD — Topic

**Observation:**  
**Root cause:**  
**Resolution:**  
**Reusable rule:**  

### 2026-09-28 — OpenCode V1/V2 agent config formats

**Observation:**  
OpenCode V2 agent frontmatter documents `permissions:` (ordered rule list) and marks legacy top-level `permission` as a V1 field, yet issue #50598 shows V2 parses but does not apply the new list.

**Root cause:**  
V2 normalizes both formats in memory; enforcement of the new rule list was not wired up at the time of consultation (2026-09-28).

**Resolution:**  
Default generation to the legacy `permission:` map (still applied and accepted by V2), expose `--opencode-format v2` for the native list.

**Reusable rule:**  
Before adopting a newly documented config format, verify the runtime actually applies it — parsing success is not enforcement. Re-check the tracking issue when bumping defaults.

### 2026-09-28 — Legacy config keys must match the schema that reads them

**Observation:**  
The OpenCode legacy permission map was generated with the key `shell`,
but the V1 schema reads `bash`. The file parsed cleanly and every test
passed — shell rules were simply ignored at runtime.

**Root cause:**  
The key was named after the V2 action (`shell`) instead of the V1 tool
name (`bash`); tests and docs were written from the same wrong
assumption, so they validated the bug instead of catching it.

**Resolution:**  
`bash` in the legacy map (V2 rules keep `action: shell`); tests and the
adapter-contract table updated; correction recorded in `decisions.md`.

**Reusable rule:**  
A key that parses is not a key that applies. When mirroring a vendor
schema, verify key names against the schema of the version that
enforces it, and never write a test that only asserts what the generator
emits — assert against the schema source.

### 2026-09-30 — Validation that runs after the write is not a guarantee

**Observation:**
Manifest entries were validated two passes before any read or delete, but
a new ownership rule was initially enforced only in the same place —
after `adapter.sync()` had already created the files. A test asserting
"the adapter cannot generate a path it does not own" failed because the
file existed on disk even though the command exited 1.

**Root cause:**
The safety check lived in the reconciler, which is downstream of the
producer. Reporting `no files touched` was true for deletions only; the
write side had already happened.

**Resolution:**
Move the check to the producer: `write_generated()` validates ownership
under a scoped "current adapter" binding set by `_sync_one`, and the
reconciler repeats it on load for defence in depth.

**Reusable rule:**
Any claim of the form "nothing was touched" must be enforced at the
operation that touches the filesystem, not at a later audit of it. Audit
after the fact proves detection, not prevention — and a test that checks
the exit code will not catch the litter. Assert on the artifact too.

### 2026-09-30 — A flag is not an approval; an approval needs a target

**Observation:**
`state.approved = true` plus a well-formed provenance record stayed
valid after `.juicer/plan.md` was rewritten. `juicer start` happily began
work on a plan nobody had approved; `status` reported `approved: true`.

**Root cause:**
The record bound *who* and *when*, but not *what*. Content was edited
after approval and nothing compared it.

**Resolution:**
`approve` stores plan and mission content digests plus `mission_id`;
every gate re-derives the same parts and compares. Mismatch downgrades
the flag and `status` explains it on stderr while stdout stays pure JSON.

**Reusable rule:**
Binding a decision to an identity and a timestamp only prevents
impersonation of the decision-maker. To prevent substitution of the
*object* of the decision, record a digest of that object at approval
time and re-derive it at use time — and let the user repair the flow
(`done` became a valid source state for `approve`) rather than stranding
the workspace.

### 2026-09-30 — A filename is content

**Observation:**
A file named `evil-->inject.md` in `agents/` was rendered into every
harness mirror. Its provenance comment became
`<!-- juicer-kit: generated from agents/evil-->inject.md sha256:… -->`,
which closes the HTML comment early and leaves the rest of the name as
body text in a file the harness reads as a prompt. The same name also
travels into the Codex TOML `name = "…"` field.

**Root cause:**
The name was validated where the *user* supplied it (`juicer worker
<name>`) but not where the *directory* supplied it (`iter_workers`). One
rule, two entry points, one of them unguarded.

**Resolution:**
`WORKER_NAME = ^[a-z][a-z0-9-]*$` now lives in `adapters/_base.py`
beside the renderer, and `iter_workers` skips non-matching names with a
warning naming the file and the pattern.

**Reusable rule:**
Any string that crosses from the filesystem into a structured document —
comment, string literal, frontmatter, path — is untrusted input.
Validate it at the boundary where it is *embedded*, not only where it
was typed. Attack the file *name*, not just the file *content*.

### 2026-09-30 — Say what will not happen

**Observation:**
A safety failure printed `… (no files touched)`. One of its two call
sites runs *after* `adapter.sync()` has already written the files, so
the message was true for deletions and false for writes.

**Root cause:**
The message was written once for a helper and inherited by every caller,
including one that could not honour it.

**Resolution:**
Each call site now states only what that site controls: the manifest
failure says nothing will be read, deleted or recorded; the change-path
failure says nothing will be recorded in the manifest or deleted.

**Reusable rule:**
A safety message emitted from shared code must be phrased in terms of
the operations that helper owns, or take its context from the caller. A
guarantee stated once and inherited by a caller that cannot honour it is
a false guarantee — the exact category this audit treats as a BLOCKER.

### 2026-09-30 — A security document is a test oracle

**Observation:**
`docs/security.md` claimed "`juicer sync` warns when a worker's access
widens". No such warning existed anywhere in the code.

**Root cause:**
The document was drafted for the intended behaviour during the audit and
never re-read against the implementation before commit.

**Resolution:**
Implemented the warning (it reports *any* permission change; direction
is not inferred) and reworded the document to claim only what the code
does. The wording, the code and the test that asserts the stderr string
now move together.

**Reusable rule:**
Treat every sentence in a security document as an assertion that should
be greppable. Search the repo for the message the sentence implies; if
no string matches, either write the code or delete the claim. Never let
a document be the only place a guarantee exists.

### 2026-09-30 — A list of forbidden actions is not a to-do list

**Observation:**
The v2.4.0 task opened with "no tag, no push, no release publish". When
those were later approved, the third item was treated as a step to
execute, and the absence of `gh` and of a token was reported as a
blocker. The repo has never published a GitHub Release: the public API
returns 0, only `ci.yml` exists, and no doc, worker, skill or workflow
mentions publishing. v2.1.0, v2.2.0 and v2.3.0 are tags only.

**Root cause:**
A prohibition was read as a description of the process. The wording
listed three nouns, so the third was inferred to be outstanding work
rather than a step that never existed.

**Resolution:**
Closed at tag + push, matching every previous version, and recorded in
the handoff that the step does not exist so it is not rediscovered.

**Reusable rule:**
Before scheduling a step, prove it exists: find the script, workflow,
skill or document that performs it. Permission to do X is not evidence
that X belongs to the workflow. The same failure mode applies to carried
forward state — a "known problem" is itself an assertion, so re-run it
against the code before repeating it. The sibling bullet removed from
the handoff today had been false since the templates were introduced.
