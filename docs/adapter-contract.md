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

Return the adapter's actual capabilities.

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

## Adding a new harness

To add Gemini CLI, for example:

```text
adapters/
└── gemini-cli/
    ├── README.md
    └── ...
```

No change to:

```text
.juicer/
agents/
.agents/skills/
workflows/
```

should be required.
