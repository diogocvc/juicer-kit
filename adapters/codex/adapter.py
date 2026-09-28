"""Codex harness adapter.

Verified sources (consulted 2026-09-28):

- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/guides/agents-md

Rules applied:

- skills are NOT mirrored; Codex reads ``.agents/skills`` natively
- entrypoint: ``AGENTS.md`` is native to Codex
- custom agents are TOML files in ``.codex/agents/`` (generated in a
  later phase); this adapter keeps sync minimal until then
"""

from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
)


class Adapter(BaseAdapter):
    id = "codex"
    executable = "codex"
    marker_dir = ".codex"
    agents_dir = ".codex/agents"
    supports_skills_mirror = False

    def capabilities(self):
        return {
            "skills": True,
            "subagents": True,
            "parallel_agents": True,
            "human_approval": True,
            "persistent_context": True,
        }

    def sync(self, ctx, dry_run=False):
        return [ensure_entrypoint(ctx, dry_run=dry_run)]

    def invoke(self, ctx, worker, unit=None):
        native = (
            "native route: Codex custom agent "
            f"(declare {self.agents_dir}/{worker}.toml) or /agent; "
            "Codex subagents are experimental"
        )
        return self._invoke(ctx, worker, unit, native=native)
