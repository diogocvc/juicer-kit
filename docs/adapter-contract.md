# Adapter Contract

## Purpose

An adapter connects a development harness to the portable Juicer Kit core.

Adapters are deliberately thin.

They translate:

```text
Juicer concepts
    ↓
harness-specific capabilities
```

They must not redefine:

- mission state
- workflows
- worker responsibilities
- acceptance criteria
- approval semantics
- project architecture

## Contract v1

Every adapter should expose these conceptual operations:

### discover()

Determine whether the harness is available and what Juicer capabilities it can consume.

Returns:

```yaml
available: true
version: "..."
```

### install()

Install or register the adapter's harness-specific files/configuration.

Must not modify `.juicer/` semantics.

### sync()

Synchronize canonical:

```text
agents/
.agents/skills/
AGENTS.md
```

into the harness's native locations when required.

### invoke(worker)

Execute a Juicer worker.

Input:

```yaml
worker: reviewer
mission_state: .juicer/
unit: UNIT-003
```

The adapter decides whether to use:

- native subagent
- agent mode
- command
- skill
- external process
- direct prompt

### capabilities()

Return the adapter's declared capabilities (static metadata; `discover()`
reports the actual environment).

Example:

```yaml
skills: true
subagents: true
parallel_agents: true
human_approval: true
persistent_context: true
```

## Capability rule

Capabilities describe the harness.

They do **not** alter the core workflow.

If a capability is unavailable, the adapter must provide the safest portable fallback.

For example:

```text
native subagent unavailable
        ↓
direct worker invocation
```

not:

```text
native subagent unavailable
        ↓
Juicer workflow breaks
```

## Canonical worker attributes

Canonical worker frontmatter may carry harness-only attributes that
must never be copied into generated files:

```yaml
name: reviewer
description: Code review
role: reviewer
access: read-only   # read-only | edit | full
tier: hot           # hot | warm | cold (canonical planning only)
```

Prohibited in every generated file: `role:`, `access:`, `tier:`,
`model:` (including `model: inherit`).

`access` is the single source for permission mapping:

| harness    | key(s)                          | read-only            | edit              | full     |
|------------|---------------------------------|----------------------|-------------------|----------|
| OpenCode   | `permission` (legacy: `edit`/`bash`) or V2 `permissions` | edit/bash: deny  | edit: allow, bash: ask | edit/bash: allow |
| Claude Code | `tools`                        | read-only tool set   | read + write set  | omitted (all) |
| Cursor     | `readonly`                      | `readonly: true`     | —                 | —        |
| Codex      | `sandbox_mode`                  | `read-only`          | `workspace-write` | `workspace-write` |
| Zed        | none (no subagents)             | —                    | —                 | —        |

`name` rules: required in `.claude/agents/`, prohibited in
`.opencode/agents/`, omitted (filename-derived) in `.cursor/agents/`.

Workers without `access` default to `edit`; invalid `access`/`tier`
values abort `sync` with exit 1.

## Sync safety and the manifest

Every adapter records what it generated in

```text
.juicer/runtime/manifests/<adapter-id>.json
```

```json
{
  "schema": 1,
  "adapter": "opencode",
  "updated_at": "...",
  "files": {".opencode/agents/reviewer.md": "<sha256>"}
}
```

Rules:

1. Only paths recorded in the manifest may be deleted (stale cleanup).
   Every entry is validated first: relative, no `..`, and resolving
   inside the project root — anything else aborts the sync untouched.
2. A recorded file whose disk hash no longer matches the manifest was
   modified by the user: it is kept and reported as a conflict unless
   `--force` is given.
3. Files never recorded (user files, `AGENTS.md`, unknown paths) are
   never touched.
4. Current outputs are regenerated on every sync; if a user had edited
   a current output, the overwrite is reported on stderr.
5. `AGENTS.md` is project-owned (`manifest=False`): never tracked,
   never deleted, never overwritten when present.

CLI flags (both `sync` and `install`):

| flag | behavior |
|------|----------|
| `--dry-run` | print the plan (`write`/`delete`/`keep`), change nothing, exit 0 |
| `--check` | print the plan, change nothing; exit 1 if any action is pending |
| `--force` | also delete user-modified stale files |

`juicer sync all --check` is the CI-friendly drift gate.

## Python contract

Adapters are Python modules loaded by `bin/juicer`:

```text
adapters/
├── _base.py            # shared base class and helpers
└── <id>/
    ├── adapter.py      # class Adapter (required)
    ├── adapter.yaml    # declarative metadata (optional)
    └── README.md       # adapter notes + sources consulted
```

`adapter.py` must expose a class named `Adapter` with an `id`
(`^[a-z][a-z0-9-]*$`) and these methods:

```python
def capabilities(self) -> dict           # harness capability declaration
def discover(self, ctx) -> dict          # available/version/major/notes; never raises
def sync(self, ctx, dry_run=False) -> list  # list of Change (write/skip/delete)
def install(self, ctx, dry_run=False) -> list  # sync() + marker file
def invoke(self, ctx, worker, unit=None) -> str  # instructions; never calls a model
```

`ctx` is a `_base.Ctx`:

```python
Ctx(root=<project>, kit=<kit>, state_dir=".juicer",
    skills_source=".agents/skills", agents_source="agents", options={})
```

Helpers from `_base`: `read_frontmatter`, `render_frontmatter`,
`write_generated`, `resolve_source`, `iter_workers`, `ensure_entrypoint`,
`mirror_skills`, `direct_instructions`.

Rules:

- read canonical sources via `resolve_source()` (project copy first, kit
  fallback)
- never write outside the project root, and never into `.juicer/`
  (`write_generated` enforces this: its ``root=`` keyword is required and
  the target must resolve inside it)
- declare where you write. `agents_dir`, `skills_dir` and `marker_dir`
  feed `Adapter.owned_paths()`, the allowlist a manifest-tracked path
  must fall inside. `write_generated()` rejects anything else while your
  `sync`/`install` runs, and `bin/juicer` rejects the same paths again
  when it loads the manifest — before any read or delete. Files that are
  project-owned (the `AGENTS.md` entrypoint) pass `manifest=False` and
  are exempt.
- `sync` only creates/updates harness mirrors; deletions belong to the
  manifest-based cleanup (see *Sync safety and the manifest* above)
- `discover` must degrade gracefully: missing binary → `available: false`

## adapter.yaml

Optional declarative metadata next to `adapter.py`. Must be a valid
YAML mapping with this schema:

```yaml
id: opencode                 # must equal Adapter.id and the directory name
contract_version: 2
capabilities:                # must equal Adapter.capabilities()
  skills: true
  subagents: true
  parallel_agents: true
  human_approval: true
  persistent_context: true
canonical_state: .juicer
canonical_skills: .agents/skills
canonical_agents: agents
```

`tests/test_adapters.py` parses every kit `adapter.yaml` with PyYAML and
fails CI when it is invalid YAML or its `capabilities` drift from the
Python `capabilities()` output.

### contract_version

Declares which revision of this document the adapter implements. It is
metadata only: `bin/juicer` does not read `adapter.yaml` at runtime, so
a stale value cannot break discovery — it tells a human what the
adapter was written against.

| Version | Meaning |
|---|---|
| `1` | Pre-2.4.0 contract: `write_generated()` had no `root=` keyword and output was not ownership-checked. |
| `2` | `write_generated(..., root=...)` is required; adapters must declare `agents_dir`/`skills_dir`/`marker_dir` so `owned_paths()` can bound what they may write and delete. |

## Discovery

`bin/juicer` discovers adapters from two roots, in this order:

```text
KIT/adapters/     # shipped with the kit — always loaded
ROOT/adapters/    # embedded by the project — only when trusted (see Trust)
```

A directory is an adapter when it contains `adapter.py`. Discovery
imports the module, instantiates `Adapter`, and validates the `id` and
the five methods. No `bin/juicer` edit is ever required to add or
override an adapter.

## Trust

`adapter.py` is executable Python. The `init`, `sync`, `install`,
`invoke`, `adapters` and `capabilities` commands import it with
`importlib.exec_module`, so a project adapter runs with your
privileges — the same trust you give a Makefile or a git hook from that
repository. The trust model is explicit:

- By default only `KIT/adapters` loads. Project adapter directories are
  reported on stderr (`project adapters skipped (untrusted): ...`) and
  never imported.
- Pass `--trust-project-adapters` on any of the six commands above, or
  set `JUICER_TRUST_PROJECT_ADAPTERS=1`, to load `ROOT/adapters`
  (project wins on id collision when trusted, as before).
- Targeting a project-only adapter without trust fails with
  `comes from untrusted project code` instead of a misleading
  "unknown adapter" error.
- State commands (`mission`, `approve`, `start`, `checkpoint`,
  `finish`, `ship-approve`, `status`, `worker`) never load adapters.
- When `ROOT == KIT` (working inside the kit repository itself) both
  roots are the same directories; they are deduplicated by resolved
  path and no warning is emitted.

Only run `juicer init`/`juicer sync` in repositories you trust, or keep
project adapters disabled.

## Adding a new harness

To add Gemini CLI, for example:

```text
adapters/
└── gemini-cli/
    ├── adapter.yaml
    ├── adapter.py
    └── README.md
```

```python
# adapters/gemini-cli/adapter.py
from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
    iter_workers,
    render_frontmatter,
    write_generated,
)


class Adapter(BaseAdapter):
    id = "gemini-cli"
    executable = "gemini"
    marker_dir = ".gemini"
    agents_dir = ".gemini/agents"

    def capabilities(self):
        return {
            "skills": True,
            "subagents": True,
            "parallel_agents": True,
            "human_approval": True,
            "persistent_context": True,
        }

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        for worker in iter_workers(ctx):
            fm = {"description": worker.frontmatter.get("description", worker.name)}
            path = ctx.root / self.agents_dir / f"{worker.name}.md"
            changes.append(write_generated(
                path,
                render_frontmatter(fm) + "\n" + worker.body.rstrip() + "\n",
                root=ctx.root,
                dry_run=dry_run,
            ))
        return changes

    def invoke(self, ctx, worker, unit=None):
        native = f"native route: Gemini custom subagent {self.agents_dir}/{worker}.md"
        return self._invoke(ctx, worker, unit, native=native)
```

```bash
./bin/juicer adapters            # lists gemini-cli
./bin/juicer capabilities gemini-cli
./bin/juicer sync gemini-cli
```

No change to:

```text
.juicer/
agents/
.agents/skills/
workflows/
```

should be required.
