"""Codex harness adapter.

Verified sources (consulted 2026-09-28):

- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/guides/agents-md

Rules applied:

- custom agents are TOML files in ``.codex/agents/`` with the documented
  keys only: ``name``, ``description``, ``developer_instructions`` and
  ``sandbox_mode``; no ``model`` / ``model_reasoning_effort``
- skills are NOT mirrored; Codex reads ``.agents/skills`` natively
- entrypoint: ``AGENTS.md`` is native to Codex

access → sandbox_mode mapping:

===========  ==================
access       sandbox_mode
===========  ==================
read-only    read-only
edit         workspace-write
full         workspace-write
===========  ==================
"""

from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
    iter_workers,
    provenance,
    worker_access,
    write_generated,
)

SANDBOX_MODES = {
    "read-only": "read-only",
    "edit": "workspace-write",
    "full": "workspace-write",
}


def _toml_basic(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_multiline(value):
    text = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return text.rstrip("\n")


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

    def _render(self, worker):
        access = worker_access(worker)
        description = worker.frontmatter.get("description", worker.name)
        return (
            f"# juicer-kit: generated from {provenance(worker)}\n"
            f'name = "{_toml_basic(worker.name)}"\n'
            f'description = "{_toml_basic(description)}"\n'
            f'sandbox_mode = "{SANDBOX_MODES[access]}"\n'
            f'developer_instructions = """\n{_toml_multiline(worker.body)}\n"""\n'
        )

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        for worker in iter_workers(ctx):
            path = ctx.root / self.agents_dir / f"{worker.name}.toml"
            changes.append(write_generated(path, self._render(worker), root=ctx.root,
                                           dry_run=dry_run))
        return changes

    def invoke(self, ctx, worker, unit=None):
        native = (
            f"native route: Codex custom agent {self.agents_dir}/{worker}.toml "
            "(ask Codex to spawn it, or use /agent); Codex subagents are experimental"
        )
        return self._invoke(ctx, worker, unit, native=native)
