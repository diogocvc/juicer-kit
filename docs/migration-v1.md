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
2. Install v2.
3. Convert active v1 backlog items into `.juicer/plan.md`.
4. Convert durable project decisions into `.juicer/decisions.md`.
5. Convert important lessons into `.juicer/learnings.md`.
6. Run `./bin/juicer sync all`.
7. Verify native agent discovery.
8. Test one direct worker invocation.
9. Test resume from a new session.
10. Remove v1 only after verification.
