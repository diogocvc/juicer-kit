# Project Instructions

Juicer Kit 4.0.0 — Markdown kit (agents, commands, skills) plus the Python
orchestration core (`juicer/` + `bin/juicer`).

**Target harness**: OpenCode 2.x/V2. The environment-measured version is
`opencode v2.1.4` (`~/.opencode/bin/opencode`). A V1 binary may be detected for
diagnostics, but it is `degraded` and is not a compatibility promise. See
`STATUS.md` for measured capabilities versus planned gaps.

## Where things live

- `backlog/` — planning task board. `backlog/backlog.md` (pending),
  `backlog/in-progress.md` (running), `backlog/done/` (finished).
- `docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md` — approved implementation plan,
  gates, phases and backlog mapping.
- `docs/HARNESS_CONTRACT.md` — minimal `discover`/`run` contract between core
  and harness adapters (V2-first; V1 references are historical).
- `.opencode/agents/` — the agent team (`@orchestrator`, `@finder`, `@coder`,
  `@reviewer`, `@tester`, `@security`, …).
- `.opencode/commands/` — slash commands (`/add-backlog`, `/edit-backlog`,
  `/remove-backlog`, `/start`, `/plan`, `/review`, `/test`, …).
- `.opencode/skills/` — reusable playbooks (TDD, security review, code review
  checklist, …).
- `juicer/` — orchestration core. `bin/juicer` is the CLI entrypoint.
- `.juicer/` — operational state after a validated mission import (mission,
  tasks, executions, evidence, checks, events). The core is the owner of state,
  scope, evidence, gates and integration.

## Canonical workflow order

Implementation → deterministic checks → review → security (when applicable) →
human approval (when applicable) → merge/integrate → post-merge checks → done.

1. Pick or add a task with `/add-backlog`, select it and move it to
   `backlog/in-progress.md` with `/start`.
2. Let `@orchestrator` coordinate the work and delegate to the right agents.
3. Run `@tester` after implementation to create/execute tests and deterministic
   checks. `NOT RUN` is never a pass, and agent prose is not evidence.
4. Always run `@reviewer` after code changes and checks (`/review`), before any
   merge. Critical findings block until fixed.
5. Run `@security` for authentication, user data, secrets, external APIs,
   permissions or other high-risk changes. Security does not replace review.
6. Require the task's technical gates and human approval before integration;
   never treat approval as a substitute for tests or review.
7. Only after an explicit `juicer integrate`/merge and passing post-merge checks
   move the task to `backlog/done/`.

Keep tasks small enough to be finished in one session. The backlog Markdown is
the planning source; after a validated import into a mission, `.juicer/` is the
canonical operational state. There is no bidirectional sync, and later backlog
edits do not overwrite an in-progress mission.

## Gates and permissions

- The core enforces technical gates, scope, evidence links, human approval and
  post-merge checks. Agents may advise; they do not waive core gates.
- OpenCode V2 permissions (`allow`/`ask`/`deny`) are an additional execution
  barrier, not a substitute for the core's gates, evidence or approval.
- A task reaches `done` only after technical gate PASS, explicit integration and
  post-merge check PASS. `completed` (pre-merge) is not `done`.
