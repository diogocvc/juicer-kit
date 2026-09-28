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
