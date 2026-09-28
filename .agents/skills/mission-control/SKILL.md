---
name: mission-control
description: Run Juicer Kit missions with repository state, human approval gates, checkpoints and resumable execution.
---

# Mission Control

You are operating inside Juicer Kit v2.

Always treat `.juicer/` as the source of truth.

## Rules

- Inspect current mission state before acting.
- Never bypass a human approval gate.
- Work one active unit at a time unless explicit parallel execution is requested.
- Keep the user informed at decision points.
- Persist meaningful state before ending the session.
- A chat ending is not a workflow ending: update `.juicer/handoff.md`.

## Session startup

Read:

1. `.juicer/mission.md`
2. `.juicer/plan.md`
3. `.juicer/handoff.md`

Then report:

- current mission
- current unit
- blockers
- next permitted action

## Session end

Update `.juicer/handoff.md` with:

- what changed
- what was verified
- what remains
- next action
