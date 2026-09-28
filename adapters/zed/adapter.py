"""Zed harness adapter.

Verified sources (consulted 2026-09-28):

- https://zed.dev/docs/ai/skills
- https://zed.dev/docs/ai/instructions

Rules applied:

- skills are NOT mirrored; Zed reads ``.agents/skills`` natively
- entrypoint: ``AGENTS.md`` is the primary context file
- Zed has no subagents (``subagents: false``); the portable fallback
  is direct worker invocation in the agent panel
"""

from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
)


class Adapter(BaseAdapter):
    id = "zed"
    executable = "zed"
    marker_dir = None
    agents_dir = None
    supports_skills_mirror = False

    def capabilities(self):
        return {
            "skills": True,
            "subagents": False,
            "parallel_agents": False,
            "human_approval": True,
            "persistent_context": True,
        }

    def discover(self, ctx):
        info = super().discover(ctx)
        info.setdefault(
            "notes",
            "Zed reads .agents/skills and AGENTS.md natively; no subagents",
        )
        return info

    def sync(self, ctx, dry_run=False):
        return [ensure_entrypoint(ctx, dry_run=dry_run)]

    def invoke(self, ctx, worker, unit=None):
        native = "native route: none; Zed has no subagents — run the contract in the agent panel (or an external ACP agent)"
        return self._invoke(ctx, worker, unit, native=native)
