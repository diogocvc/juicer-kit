# Tests

Run:

```bash
python -m pytest tests
```

Or with `uv` (pinned interpreter, nothing installed locally):

```bash
uv run --python 3.12 --with pytest --with pyyaml python -m pytest -q tests
```

Suites:

- `test_adapters.py` — adapter contract markers per harness
- `test_cli.py` — version files and CLI surface
- `test_docs.py` — documentation consistency (placeholders, canonical URL, versions, install claims, mirror rules, gitignore alignment)
- `test_frontmatter.py` — skill frontmatter validity
- `test_git_guard.py` — main/master pre-commit guard, escapes, hook chaining
- `test_handoff.py` — handoff freshness marker, checkpoint log, state.json wins
- `test_init.py` — init copies the canonical tree, idempotence, gitignore scoping
- `test_mission_render.py` — mission and plan rendering
- `test_path_confinement.py` — path confinement for state access
- `test_registry.py` — worker registry
- `test_root_discovery.py` — workspace root discovery
- `test_security_baseline.py` — security baseline invariants
- `test_session.py` — read-only session briefing from state.json
- `test_state_integrity.py` — atomic writes, revision fencing, approval provenance
- `test_states.py` — workflow and state documents (including release INVARIANT lines)
- `test_symlink_escape.py` — symlink escape protection
- `test_sync.py` — sync idempotence and mirror generation

The tests focus on structural guarantees:

- portable core exists
- worker contracts exist
- skills have valid frontmatter
- adapters implement the contract markers
- Codex integration uses the universal entrypoint
- core structure is independent of individual harnesses
- documentation stays consistent with the kit's version and install model
