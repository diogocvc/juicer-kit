"""Claude Code harness adapter.

Verified sources (consulted 2026-09-28):

- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/skills

Rules applied:

- subagents live in ``.claude/agents/<name>.md`` and require a ``name``
  frontmatter key; ``role``/``access``/``tier`` are rejected
- skills ARE mirrored into ``.claude/skills`` (Claude Code does not
  read ``.agents/skills`` natively)
- entrypoint: AGENTS.md is read natively by Claude Code >= 2.1.277
  when no CLAUDE.md exists; never overwrite a user CLAUDE.md
"""

from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
    iter_workers,
    mirror_skills,
    render_frontmatter,
    write_generated,
)


class Adapter(BaseAdapter):
    id = "claude-code"
    executable = "claude"
    marker_dir = ".claude"
    agents_dir = ".claude/agents"
    supports_skills_mirror = True

    def capabilities(self):
        return {
            "skills": True,
            "subagents": True,
            "parallel_agents": True,
            "human_approval": True,
            "persistent_context": True,
        }

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        changes += mirror_skills(ctx, ctx.root / ".claude" / "skills", dry_run=dry_run)
        for worker in iter_workers(ctx):
            frontmatter = {
                "name": worker.name,
                "description": worker.frontmatter.get("description", worker.name),
            }
            content = render_frontmatter(frontmatter) + "\n" + worker.body.rstrip() + "\n"
            path = ctx.root / self.agents_dir / f"{worker.name}.md"
            changes.append(write_generated(path, content, dry_run=dry_run))
        return changes

    def invoke(self, ctx, worker, unit=None):
        native = f"native route: Agent tool with subagent_type={worker} (file {self.agents_dir}/{worker}.md)"
        return self._invoke(ctx, worker, unit, native=native)
