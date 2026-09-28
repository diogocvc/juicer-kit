# Architecture

## 1. Portable core

The portable core is:

- `.juicer/` — state
- `agents/` — role contracts
- `.agents/skills/` — portable skills
- `bin/juicer` — deterministic state controller

None of these requires an AI provider.

## 2. Harness adapters

Adapters translate native capabilities into the same role contracts.

A harness may provide:

- native subagents
- skills
- slash commands
- modes
- ACP
- MCP
- approval controls

These are accelerators, not dependencies.

## 3. State machine

```text
idle
  ↓
planning
  ↓ approval
ready
  ↓
executing
  ├── checkpoint → executing
  ├── blocker → blocked
  └── verification → ready/done
                         ↓
                      ship approval
                         ↓
                        done
```

## 4. Why this fixes the v1 problem

The previous design made the OpenCode agent layer too central. A failure or behavioral change in the orchestrator could therefore affect the entire workflow.

v2 separates:

- workflow state
- role definitions
- skills
- native delegation
- model selection
- user approval

A broken native orchestrator no longer destroys the underlying workflow.

## 5. Direct worker execution

Every worker is independently addressable.

The worker receives the same state whether it is:

- delegated by another agent
- invoked directly by the user
- started from an IDE mode
- run in an external ACP agent
- run in a CLI session
