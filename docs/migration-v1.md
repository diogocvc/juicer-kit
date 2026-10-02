# Migration from Juicer Kit v1

v2 is a replacement architecture.

## Preserve

- existing project source code
- existing project documentation
- existing Git history

## Replace

- v1 `.opencode/agents`
- v1 commands
- v1 skill layout
- v1 backlog runtime

## New source of truth

```text
.juicer/
.agents/skills/
agents/
bin/juicer
```

## Migration sequence

1. Back up the project.
2. Install v2: clone or copy the kit into the project (see `docs/installation.md`).
3. Run `./bin/juicer init` to create the `.juicer/` workspace.
4. Convert active v1 backlog items into `.juicer/plan.md`.
5. Convert durable project decisions into `.juicer/decisions.md`.
6. Convert important lessons into `.juicer/learnings.md`.
7. Run `./bin/juicer sync all`.
8. Verify native agent discovery.
9. Test one direct worker invocation.
10. Test resume from a new session.
11. Remove v1 only after verification.
