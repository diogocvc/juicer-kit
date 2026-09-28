# Zed Adapter

Zed is a Juicer harness adapter.

Juicer can run through Zed's agent environment or an external ACP agent.

Canonical state remains `.juicer/`.

Canonical skills remain `.agents/skills/`.

Zed-specific execution is optional and must not become a Juicer dependency.

## Behavior

- Skills are **not** mirrored: Zed reads `.agents/skills` natively.
- Entry point: `AGENTS.md` is the primary context file.
- Zed has no subagents; the portable fallback is direct worker
  invocation in the agent panel (or an external ACP agent).

## Sources consulted (2026-09-28)

- https://zed.dev/docs/ai/skills
- https://zed.dev/docs/ai/instructions
