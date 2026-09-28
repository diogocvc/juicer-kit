# Claude Code Adapter

Claude Code is a Juicer harness adapter.

```bash
./bin/juicer sync claude-code
```

Canonical state remains `.juicer/`.

Canonical skills remain `.agents/skills/`.

Native Claude subagents are only an execution adapter.

## Behavior

- Subagents are generated into `.claude/agents/<name>.md`; the `name`
  frontmatter key is required, and `role`/`access`/`tier`/`model` are
  rejected.
- `access` maps to `tools`:

  | access  | tools |
  |---------|-------|
  | read-only | Read, Grep, Glob, WebFetch, WebSearch |
  | edit    | read set + Edit, Write, NotebookEdit, Bash, Task, TodoWrite |
  | full    | omitted (inherits every session tool) |

- Skills **are** mirrored into `.claude/skills` (Claude Code does not
  read `.agents/skills` natively).
- Entry point: `AGENTS.md` is read natively by Claude Code >= 2.1.277
  when no `CLAUDE.md` exists; a user `CLAUDE.md` is never overwritten.

## Sources consulted (2026-09-28)

- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/skills
