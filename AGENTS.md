# Juicer Kit

This repository uses **Juicer Kit** as its agentic development workflow.

## Source of truth

The canonical workflow state is stored in:

- `.juicer/mission.md`
- `.juicer/plan.md`
- `.juicer/state.json`
- `.juicer/handoff.md`
- `.juicer/decisions.md`
- `.juicer/learnings.md`

Do not move workflow state into a harness-specific configuration directory.

## Portable capabilities

Canonical reusable skills live in:

```text
.agents/skills/
```

Canonical worker contracts live in:

```text
agents/
```

## Operating rules

1. Read the active Juicer state before acting.
2. Respect human approval gates.
3. Work within the current unit's scope.
4. Do not silently expand scope.
5. Verify changes before declaring completion.
6. Persist important state in `.juicer/handoff.md`.
7. Record reusable engineering knowledge in `.juicer/learnings.md`.
8. Prefer direct worker invocation over unnecessary orchestration.
9. The current harness is an implementation detail, not the workflow.
10. Never assume a specific model or provider.

## Worker invocation

When asked to perform a specialized task, select the matching Juicer worker from `agents/`.

Examples:

- repository reconnaissance → `finder`
- root-cause debugging → `debugger`
- implementation → `coder`
- code modification → `editor`
- review → `reviewer`
- tests → `tester`
- security → `security`
- deployment → `devops`

If the current harness has native subagents, use them.

If it does not, execute the worker contract directly.

The expected behavior and output remain the same in both cases.

## Human control

The agent may propose plans and execute approved units.

The agent must not infer:

- plan approval
- production approval
- destructive-action approval
- scope expansion approval

## Context economy

Read only the context required for the active unit.

Do not load the entire repository or historical chat by default.
