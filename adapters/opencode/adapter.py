"""OpenCode harness adapter.

Verified sources (consulted 2026-09-28):

- https://opencode.ai/v2/docs/agents
- https://opencode.ai/v2/docs/skills
- https://opencode.ai/v2/docs/migrate-v1
- https://github.com/anomalyco/opencode/issues/50598

Rules applied:

- agents are generated into ``.opencode/agents/<id>.md`` (plural)
- generated frontmatter keys are exactly ``description``, ``mode`` and
  ``permission`` (legacy) or ``permissions`` (native V2, opt-in);
  canonical keys (``name``/``role``/``access``/``tier``) are never copied
- default format is the legacy ``permission`` map because V2 parses the
  ``permissions`` list but does not apply it yet (issue #50598); pass
  ``--opencode-format v2`` to emit the native V2 list
- the legacy V1 map is keyed by tool name (``edit``, ``bash``); OpenCode
  translates ``bash`` to the V2 ``shell`` action (migrate-v1 docs), so the
  legacy shell rule MUST use ``bash`` — V2 rules use ``action: shell``
- skills are NOT mirrored; OpenCode reads ``.agents/skills`` (and
  ``.claude/skills``) natively
- the only entrypoint is ``AGENTS.md`` (no per-harness copy)

access → permission mapping (legacy keys):

===========  ========  ========
access       edit      bash
===========  ========  ========
read-only    deny      deny
edit         allow     ask
full         allow     allow
===========  ========  ========
"""

from _base import (
    Adapter as BaseAdapter,
    ensure_entrypoint,
    iter_workers,
    render_agent,
    worker_access,
    write_generated,
)

LEGACY_PERMISSIONS = {
    "read-only": {"edit": "deny", "bash": "deny"},
    "edit": {"edit": "allow", "bash": "ask"},
    "full": {"edit": "allow", "bash": "allow"},
}

V2_PERMISSIONS = {
    "read-only": [("edit", "deny"), ("shell", "deny")],
    "edit": [("edit", "allow"), ("shell", "ask")],
    "full": [("edit", "allow"), ("shell", "allow")],
}


class Adapter(BaseAdapter):
    id = "opencode"
    executable = "opencode"
    marker_dir = ".opencode"
    agents_dir = ".opencode/agents"
    supports_skills_mirror = False

    def capabilities(self):
        return {
            "skills": True,
            "subagents": True,
            "parallel_agents": True,
            "human_approval": True,
            "persistent_context": True,
        }

    def _frontmatter(self, worker, fmt):
        description = worker.frontmatter.get("description", worker.name)
        access = worker_access(worker)
        if fmt == "v2":
            rules = "".join(
                f"\n  - action: {action}\n    resource: \"*\"\n    effect: {effect}"
                for action, effect in V2_PERMISSIONS[access]
            )
            return {"description": description, "mode": "subagent", "permissions": rules}
        perms = LEGACY_PERMISSIONS[access]
        return {
            "description": description,
            "mode": "subagent",
            "permission": f"\n  edit: {perms['edit']}\n  bash: {perms['bash']}",
        }

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        fmt = ctx.options.get("opencode_format") or "legacy"
        if fmt not in ("legacy", "v2"):
            raise ValueError(f"invalid opencode format {fmt!r} (expected legacy or v2)")
        for worker in iter_workers(ctx):
            content = render_agent(self._frontmatter(worker, fmt), worker)
            path = ctx.root / self.agents_dir / f"{worker.name}.md"
            changes.append(write_generated(path, content, dry_run=dry_run))
        return changes

    def invoke(self, ctx, worker, unit=None):
        native = f"native route: @{worker} in chat (subagent file {self.agents_dir}/{worker}.md, mode: subagent)"
        return self._invoke(ctx, worker, unit, native=native)
