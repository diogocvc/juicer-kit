# Project Instructions

Juicer Kit 4.0.0 — Markdown kit (agents, commands, skills) plus the Python orchestration core.

## Where things live

- `backlog/` — planning task board. `backlog/backlog.md` (pending), `backlog/in-progress.md` (running), `backlog/done/` (finished).
- `docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md` — approved implementation plan, gates, phases and backlog mapping.
- `docs/HARNESS_CONTRACT.md` — minimal `discover`/`run` contract between core and harness adapters.
- `.opencode/agents/` — the agent team (`@orchestrator`, `@finder`, `@coder`, `@reviewer`, `@tester`, …).
- `.opencode/commands/` — slash commands (`/add-backlog`, `/edit-backlog`, `/remove-backlog`, `/start`, `/plan`, `/review`, `/test`, …).
- `.opencode/skills/` — reusable playbooks (TDD, security review, code review checklist, …).
- `juicer/` — orchestration core. `bin/juicer` is the CLI entrypoint.

## Workflow convention

Implementation → deterministic checks → review → security (when applicable) → human approval (when applicable) → merge → post-merge checks → done.

1. Pick or add a task with `/add-backlog`, select it and move it to `backlog/in-progress.md` with `/start`.
2. Let `@orchestrator` coordinate the work and delegate to the right agents.
3. Run `@tester` after implementation to create/execute tests and deterministic checks.
4. Always run `@reviewer` after code changes and checks (`/review`).
5. Run `@security` for authentication, user data, secrets, external APIs or other high-risk changes.
6. Require the task's technical gates and human approval before integration; never treat approval as a substitute for tests or review.
7. Move the task to `backlog/done/` only after explicit merge and post-merge checks pass.

Keep tasks small enough to be finished in one session. The backlog Markdown is the planning source; after a validated import into a mission, `.juicer/` is the canonical operational state. There is no bidirectional sync, and later backlog edits do not overwrite an in-progress mission.
