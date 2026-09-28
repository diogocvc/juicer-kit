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
