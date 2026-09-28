# Decisions

Record durable decisions here.

Format:

## YYYY-MM-DD — Decision title

**Decision:**  
What was decided.

**Why:**  
Reasoning and constraints.

**Alternatives considered:**  
Only record alternatives that were actually considered.

**Impact:**  
What this changes for future work.

## 2026-09-28 — Canonical worker access and tier

**Decision:**  
Every canonical worker in `agents/` declares `access` (`read-only`, `edit`, `full`) and `tier` (`hot`, `warm`, `cold`). Adapters map `access` to harness permission keys and never emit `access`/`tier`/`role`/`model` in generated files.

Mapping: OpenCode `permission` (edit/shell → deny/ask/allow), Claude Code `tools` (read set → +write set → inherit all), Cursor `readonly` (true iff read-only), Codex `sandbox_mode` (`read-only`/`workspace-write`). `tier` is canonical-only (hot = core unit loop: coder/tester/reviewer; warm = regular support; cold = occasional specialist) and maps to no harness key.

**Why:**  
Harness frontmatter formats disagree on how permissions are expressed; a single canonical attribute keeps worker contracts harness-agnostic while each adapter emits only the keys its harness documents.

**Alternatives considered:**  
- Deriving permissions per harness ad hoc: rejected, duplicated policy.  
- Mapping `tier` to model choice: rejected, canonical state must not pick models.

**Impact:**  
Workers without `access` default to `edit`; invalid values abort sync with exit 1. Generated files are reproducible from canonical sources plus this mapping.

## 2026-09-28 — OpenCode permission format default

**Decision:**  
Generated OpenCode agents default to the legacy `permission:` map (edit/shell); `juicer sync/install --opencode-format v2` emits the native V2 `permissions:` rule list.

**Why:**  
V2 parses the `permissions` list but does not apply it yet (github.com/anomalyco/opencode/issues/50598), while the legacy map is still applied; V2 accepts both. Default must actually enforce permissions.

**Alternatives considered:**  
- V2 list by default: rejected until the runtime applies it.  
- Emitting both forms: rejected, conflicting values warn at load.

**Impact:**  
When issue #50598 is fixed, flip the default in `adapters/opencode/adapter.py`.
