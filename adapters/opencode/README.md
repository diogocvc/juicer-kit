# OpenCode Adapter

OpenCode is a Juicer harness adapter.

```bash
./bin/juicer sync opencode
```

Canonical state remains `.juicer/`.

Canonical skills remain `.agents/skills/`.

Native OpenCode agents are only an execution adapter.

## Behavior

- Agents are generated into `.opencode/agents/<id>.md` with generated
  frontmatter (`description`, `mode: subagent`, `permission`); canonical
  frontmatter is never copied verbatim.
- Skills are **not** mirrored: OpenCode reads `.agents/skills` (and
  `.claude/skills`) natively.
- The only entrypoint is `AGENTS.md`.

## Sources consulted (2026-09-28)

- https://opencode.ai/v2/docs/agents
- https://opencode.ai/v2/docs/skills
- https://opencode.ai/v2/docs/migrate-v1
- https://github.com/anomalyco/opencode/issues/50598
