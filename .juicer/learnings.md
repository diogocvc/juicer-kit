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
