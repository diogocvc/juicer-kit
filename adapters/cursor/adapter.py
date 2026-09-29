"""Cursor harness adapter.

Verified sources (consulted 2026-09-28):

- https://cursor.com/docs/subagents
- https://cursor.com/docs/skills

Rules applied:

- subagents live in ``.cursor/agents/<file>.md``; ``name`` is omitted
  (derived from the filename), ``model`` is never emitted (never
  ``model: inherit``)
- generated frontmatter keys are ``description`` and, for read-only
  workers, ``readonly: true``
- skills are NOT mirrored; Cursor reads ``.agents/skills`` natively
- entrypoint: ``AGENTS.md``
"""

from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
    iter_workers,
    render_agent,
    worker_access,
    write_generated,
)


class Adapter(BaseAdapter):
    id = "cursor"
    executable = "cursor"
    marker_dir = ".cursor"
    agents_dir = ".cursor/agents"
    supports_skills_mirror = False

    def capabilities(self):
        return {
            "skills": True,
            "subagents": True,
            "parallel_agents": True,
            "human_approval": True,
            "persistent_context": True,
        }

    def _frontmatter(self, worker):
        frontmatter = {
            "description": worker.frontmatter.get("description", worker.name),
        }
        if worker_access(worker) == "read-only":
            frontmatter["readonly"] = "true"
        return frontmatter

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        for worker in iter_workers(ctx):
            content = render_agent(self._frontmatter(worker), worker)
            path = ctx.root / self.agents_dir / f"{worker.name}.md"
            changes.append(write_generated(path, content, root=ctx.root, dry_run=dry_run))
        return changes

    def invoke(self, ctx, worker, unit=None):
        native = f"native route: Task tool, subagent_type={worker} (file {self.agents_dir}/{worker}.md)"
        return self._invoke(ctx, worker, unit, native=native)
