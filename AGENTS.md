# Project Instructions

Juicer Kit 3.0.0 — a small Markdown kit of OpenCode agents, commands and skills.

## Where things live

- `backlog/` — task board. `backlog/backlog.md` (pending), `backlog/in-progress.md` (running), `backlog/done/` (finished).
- `.opencode/agents/` — the agent team (`@orchestrator`, `@finder`, `@coder`, `@reviewer`, `@tester`, …).
- `.opencode/commands/` — slash commands (`/add-backlog`, `/edit-backlog`, `/remove-backlog`, `/start`, `/plan`, `/review`, `/test`, …).
- `.opencode/skills/` — reusable playbooks (TDD, security review, code review checklist, …).

## Workflow convention

Implementation → review → tests → done.

1. Pick or add a task with `/add-backlog`, select it and move it to `backlog/in-progress.md` with `/start`.
2. Let `@orchestrator` coordinate the work and delegate to the right agents.
3. Always run `@reviewer` after code changes (`/review`).
4. Always run `@tester` after implementation and review (`/test`).
5. Run `@security` for authentication, user data, secrets or external APIs.
6. Move the task to `backlog/done/` and set its status to Done.

Keep tasks small enough to be finished in one session. The Markdown files are the only state: a new session resumes by reading them.
