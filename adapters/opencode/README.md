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
  frontmatter (`description`, `mode`, `permission`); canonical
  frontmatter is never copied verbatim.
- `access` maps to permissions (legacy `permission:` map by default;
  `juicer sync opencode --opencode-format v2` emits the native V2
  `permissions:` rule list):

  | access  | edit  | shell |
  |---------|-------|-------|
  | read-only | deny | deny |
  | edit    | allow | ask   |
  | full    | allow | allow |

- Skills are **not** mirrored: OpenCode reads `.agents/skills` (and
  `.claude/skills`) natively.
- The only entrypoint is `AGENTS.md`.

Default is the legacy map because V2 parses but does not yet apply the
`permissions` list (issue #50598).

## Sources consulted (2026-09-28)

- https://opencode.ai/v2/docs/agents
- https://opencode.ai/v2/docs/skills
- https://opencode.ai/v2/docs/migrate-v1
- https://github.com/anomalyco/opencode/issues/50598
