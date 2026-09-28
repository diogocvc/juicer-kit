# Juicer Kit v2.3.0

**A harness-agnostic operating system for AI-native software development.**

Juicer is built around a portable core plus thin harness adapters. Adding a new AI development tool should require an adapter, not a rewrite of the workflow.

Juicer Kit provides a portable workflow for planning, executing, reviewing, testing and shipping software with AI agents while keeping the human in control.

The kit is deliberately independent from a specific:

- CLI
- IDE
- agent harness
- model/provider
- MCP configuration
- session or chat history

The repository is the source of truth. Agent sessions are replaceable workers.

## Core principles

1. **Human control is the default**
   - Plans require approval before execution.
   - High-impact actions require explicit approval.
   - The user can stop, redirect, skip or delegate any unit of work.

2. **State lives in the repository**
   - Mission state, plan, decisions, handoffs and learnings are persisted under `.juicer/`.
   - A new session can resume without reconstructing the whole conversation.

3. **Skills are portable**
   - Canonical skills live in `.agents/skills/`.
   - Adapters can mirror them into `.opencode/skills/`, `.claude/skills/` and `.cursor/skills/`.

4. **Agents are workers, not the operating system**
   - Role definitions describe capabilities and responsibilities.
   - The workflow does not depend on one orchestrator being able to spawn another agent.

5. **Direct workers are first-class**
   - Finder, analyst, architect, planner, coder, reviewer, tester, security, debugger, fixer, documenter and DevOps workers can be invoked independently.
   - Native harness delegation is optional.

6. **Every execution unit is checkable**
   - Inputs
   - objective
   - acceptance criteria
   - files/scope
   - verification
   - result
   - next action

## Architecture

```text
                         HUMAN
                           │
                    Mission / Decision
                           │
                           ▼
                    ┌──────────────┐
                    │  .juicer/    │
                    │ source state │
                    └──────┬───────┘
                           │
                 ┌─────────┴─────────┐
                 │                   │
          Portable skills       Worker roles
          .agents/skills/       agents/*.md
                 │                   │
        ┌────────┼─────────┐         │
        ▼        ▼         ▼         ▼
    OpenCode   Claude    Cursor     Zed
      adapter  adapter   adapter   adapter
        │        │         │         │
        └────────┴─────────┴─────────┘
                           │
                           ▼
                       MODEL(S)
```

## Install

Copy the repository into a project, or use the included installer:

```bash
./bin/juicer init
```

Then:

```bash
./bin/juicer status
./bin/juicer mission "Build feature X"
```

The installer creates the runtime state and mirrors workers and portable skills into supported harness locations.

Adapters are executable Python. By default only the adapters bundled
with the kit are loaded; to load adapters from the project's
`adapters/` directory, pass `--trust-project-adapters` or set
`JUICER_TRUST_PROJECT_ADAPTERS=1`. See the `Trust` section of
`docs/adapter-contract.md`.

## Primary workflow

```text
MISSION
  ↓
DISCOVER
  ↓
PLAN
  ↓
HUMAN APPROVAL
  ↓
EXECUTE ONE UNIT
  ↓
VERIFY
  ↓
CHECKPOINT
  ↓
NEXT UNIT
  ↓
REVIEW
  ↓
TEST
  ↓
SHIP APPROVAL
```

The orchestrator is intentionally **not required** for this flow.

## Roles

| Role | Responsibility |
|---|---|
| finder | Fast repository reconnaissance |
| analyst | Deep technical analysis |
| researcher | External technical research |
| architect | Solution architecture |
| planner | Atomic implementation plan |
| coder | New implementation |
| editor | Safe modification of existing code |
| fixer | Minimal bug correction |
| refactorer | Structural improvement without behavior change |
| reviewer | Code quality and regression review |
| tester | Test design and execution |
| debugger | Unknown-cause investigation |
| security | Security review |
| documenter | Documentation |
| devops | CI/CD, infrastructure and release |
| optimizer | Performance investigation |

## Direct subagent usage

The kit does not assume a universal delegation API.

Where the harness supports native subagents, use its native mechanism. Where it does not, run the worker directly with the same role definition and attach the current `.juicer/` state.

Examples:

```text
OpenCode: @finder ...
Claude Code: invoke the finder agent
Cursor: /create-subagent or run the corresponding skill/mode
Zed: use a native or external agent path and provide the worker prompt
```

The important invariant is not the invocation syntax. The invariant is the **role contract + repository state + acceptance criteria**.

## Safety gates

The kit has four mandatory gates:

### Gate 1 — Plan
No implementation starts before the current mission plan is approved.

### Gate 2 — Change
Every implementation unit records its scope and acceptance criteria.

### Gate 3 — Verify
Implementation is not considered complete until the relevant verification has been executed or an explicit exception is recorded.

### Gate 4 — Ship
Production-impacting changes require human confirmation, recorded as `ship_approved: true` in `.juicer/state.json` by `./bin/juicer ship-approve`. The CLI runs no production command itself; release skills and workflows must verify the flag via `./bin/juicer status` and stop while it is `false`.

## Context economy

Workers should not read the entire repository or entire chat history by default.

They should:

1. Read `.juicer/mission.md`.
2. Read the active plan unit.
3. Read only the relevant project instructions.
4. Inspect the smallest useful code scope.
5. Write a concise checkpoint.
6. Leave reusable learning in `.juicer/learnings.md`.

This makes long-running work resumable and reduces token waste.

## Compatibility

Current adapters:

- Codex
- OpenCode
- Claude Code
- Cursor
- Zed

These are examples, not architectural dependencies. A future Gemini CLI, Aider, Windsurf, Kiro or custom harness should be added as an adapter under `adapters/<name>/` without changing `.juicer/`, `agents/`, `.agents/skills/` or the workflows.

OpenCode currently supports project skills under `.opencode/skills` as well as Claude-compatible and `.agents/skills` locations. Claude Code supports filesystem skills under `.claude/skills`. Cursor supports the Agent Skills standard and `.agents/skills`. Zed supports native skills/instructions and external ACP agents. The kit therefore treats the portable filesystem contract as primary and native harness configuration as an adapter. 

## Versioning

Juicer Kit v2 intentionally replaces the v1 architecture instead of incrementally extending it.

Recommended project update:

```bash
rm -rf .juicer .agents/skills
cp -R juicer-kit-v2/.juicer .
cp -R juicer-kit-v2/.agents .
./juicer-kit-v2/bin/juicer init
```

Review the generated adapter files before committing them.

## License

MIT.


## Documentation

- English: `docs/GUIDE.md`
- Português: `docs/GUIDE.pt-BR.md`
- Architecture: `docs/architecture.md`
- Adapter Contract: `docs/adapter-contract.md`
- Installation: `docs/installation.md`
- Worker Protocol: `docs/worker-protocol.md`
- Migration from v1: `docs/migration-v1.md`
- Changelog: `CHANGELOG.md`
