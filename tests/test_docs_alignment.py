"""Documentation and agent/command alignment with the 4.0 core gate order.

These tests are intentional documentation contracts (TASK-010): they fail when
an agent, command or doc drifts away from the order and guarantees enforced by
the core. They do not execute agents or the OpenCode binary.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / ".opencode" / "agents"
COMMANDS_DIR = ROOT / ".opencode" / "commands"

# The kit's documented team is fixed; TASK-010 must not create agents.
EXPECTED_AGENTS = {
    "analyst",
    "architect",
    "coder",
    "commenter",
    "debugger",
    "devops",
    "documenter",
    "editor",
    "finder",
    "fixer",
    "optimizer",
    "orchestrator",
    "planner",
    "refactorer",
    "researcher",
    "reviewer",
    "security",
    "tester",
}

# Order enforced by the core: implementation -> checks -> review -> security ->
# approval -> merge -> post-merge -> done. Documentation uses "when applicable"
# variants, so match the keywords instead of the full sentence.
CANONICAL_TOKENS = [
    "implementation",
    "deterministic checks",
    "review",
    "security",
    "human approval",
    "merge",
    "post-merge",
    "done",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """Lowercase and collapse wrapping so assertions survive line breaks."""
    return " ".join(text.lower().split())


def section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    stop = text.index(end, begin)
    return text[begin:stop]


def frontmatter(relative: str) -> str:
    text = read(relative)
    assert text.startswith("---\n"), "%s missing frontmatter" % relative
    block, separator, _ = text[3:].partition("\n---\n")
    assert separator, "%s has unterminated frontmatter" % relative
    return block


def scalar(relative: str, key: str) -> str:
    for line in frontmatter(relative).splitlines():
        if line.startswith("%s:" % key):
            return line.split(":", 1)[1].strip().strip('"')
    raise AssertionError("%s missing frontmatter key %s" % (relative, key))


def permission_rules(relative: str) -> list[dict[str, str]]:
    """Parse the V2 ``permissions`` list from an agent frontmatter."""
    rules: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_permissions = False
    for line in frontmatter(relative).splitlines():
        if line.rstrip() == "permissions:":
            in_permissions = True
            continue
        if not in_permissions:
            continue
        if not line.startswith(" "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                rules.append(current)
            current = {}
            key, _, value = stripped[2:].partition(":")
            current[key.strip()] = value.strip().strip('"')
        elif current is not None and ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip().strip('"')
    if current:
        rules.append(current)
    return rules


def effective(relative: str, action: str, resource: str = "*") -> str:
    """Last matching rule wins; no match defaults to ``ask``."""
    result = "ask"
    for rule in permission_rules(relative):
        if (fnmatch.fnmatchcase(action, rule.get("action", ""))
                and fnmatch.fnmatchcase(resource, rule.get("resource", ""))):
            result = rule.get("effect", "ask")
    return result


def assert_canonical_order(text: str, label: str) -> None:
    lowered = text.lower()
    positions = []
    for token in CANONICAL_TOKENS:
        index = lowered.find(token)
        assert index != -1, "%s does not mention %r" % (label, token)
        positions.append(index)
    assert positions == sorted(positions), (
        "%s does not follow the canonical order %s" % (label, CANONICAL_TOKENS)
    )


def test_agents_md_declares_version_order_and_state_ownership():
    text = read("AGENTS.md")
    assert "4.1.0" in text
    assert ".juicer/" in text
    assert "backlog/" in text
    workflow = section(text, "## Canonical workflow order", "## Gates and permissions")
    assert_canonical_order(workflow, "AGENTS.md canonical workflow")
    normalized = flat(text)
    assert "planning source" in normalized
    assert "canonical operational state" in normalized
    assert "no bidirectional sync" in normalized


def test_agents_md_does_not_treat_permissions_as_core_gates():
    normalized = flat(read("AGENTS.md"))
    assert "additional execution barrier" in normalized
    assert "not a substitute for the core's gates" in normalized
    assert "agents may advise; they do not waive core gates" in normalized


def test_orchestrator_follows_core_order_and_does_not_promise_extra_gates():
    text = read(".opencode/agents/orchestrator.md")
    order = section(text, "## Canonical Gate Order", "## Backlog Management")
    assert_canonical_order(order, "orchestrator canonical order")
    normalized = flat(text)
    assert "never promise a gate the core does not enforce" in normalized
    assert "explicit merge/integration and passing post-merge checks" in normalized
    assert "only after the merge" in normalized


def test_orchestrator_selects_capabilities_instead_of_fixed_pipelines():
    text = read(".opencode/agents/orchestrator.md")
    normalized = flat(text)
    assert "## capability selection (not fixed pipelines)" in normalized
    assert "juicer run task-xxx" in normalized
    assert "juicer integrate" in normalized
    assert "## pipelines" not in normalized
    assert "@finder → @analyst" not in text
    assert "call `@orchestrator` to execute" not in normalized
    for line in text.splitlines():
        if line.strip().startswith("@") and line.count("→") >= 3:
            raise AssertionError("rigid pipeline reintroduced: %s" % line)


def test_reviewer_is_read_only_and_runs_before_merge():
    agent = ".opencode/agents/reviewer.md"
    assert effective(agent, "read") == "allow"
    assert effective(agent, "edit") == "deny"
    assert effective(agent, "subagent") == "deny"
    assert effective(agent, "shell") == "deny"
    normalized = flat(read(agent))
    assert "read-only" in normalized
    assert "after deterministic checks" in normalized
    assert "before merge" in normalized
    assert "critical findings block the merge until fixed" in normalized
    assert "does not replace tests" in normalized
    assert "code-review-checklist" in normalized
    assert '{"verdict": "pass", "findings"' in normalized


def test_security_is_risk_triggered_and_does_not_replace_review():
    agent = ".opencode/agents/security.md"
    assert effective(agent, "read") == "allow"
    assert effective(agent, "edit") == "deny"
    assert effective(agent, "subagent") == "deny"
    assert effective(agent, "shell") == "deny"
    normalized = flat(read(agent))
    assert "trigger security by **risk**" in normalized
    assert "authentication" in normalized and "secrets" in normalized
    assert "does **not** replace `@reviewer`" in normalized
    assert "review still runs" in normalized
    assert "never substitute for `@reviewer`" in normalized
    assert "security-review" in normalized
    assert '{"verdict": "pass", "findings"' in normalized


def test_read_only_design_and_planning_activities_cannot_edit():
    for agent in ("architect", "planner", "reviewer", "security"):
        relative = ".opencode/agents/%s.md" % agent
        assert effective(relative, "edit") == "deny", relative


def test_devops_and_debugger_have_no_blanket_shell_allow():
    for agent in ("devops", "debugger"):
        relative = ".opencode/agents/%s.md" % agent
        rules = permission_rules(relative)
        assert not any(
            rule.get("action") == "shell"
            and rule.get("resource") == "*"
            and rule.get("effect") == "allow"
            for rule in rules
        ), relative
        assert effective(relative, "shell", "git status --short") == "allow"


def test_all_agents_declare_scope_and_uncertainty():
    for path in sorted(AGENTS_DIR.glob("*.md")):
        normalized = flat(path.read_text(encoding="utf-8"))
        assert "scope" in normalized, path.name
        assert "unknown" in normalized or "blocked" in normalized, path.name


def test_agents_do_not_self_attest_test_results():
    for path in sorted(AGENTS_DIR.glob("*.md")):
        normalized = flat(path.read_text(encoding="utf-8"))
        assert "- [x]" not in normalized, path.name
        assert "tests passed" not in normalized, path.name


def test_tester_reports_deterministic_evidence_before_review():
    text = read(".opencode/agents/tester.md")
    normalized = flat(text)
    assert "after implementation and before review" in normalized
    assert "not run" in normalized
    assert "never a pass" in normalized
    assert "agent prose is not evidence" in normalized
    assert "uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py" in text


def test_review_and_test_commands_stay_compatible():
    assert scalar(".opencode/commands/review.md", "agent") == "reviewer"
    assert scalar(".opencode/commands/test.md", "agent") == "tester"
    assert scalar(".opencode/commands/security-audit.md", "agent") == "security"

    review = flat(read(".opencode/commands/review.md"))
    assert "before merge" in review
    assert "commit/tree" in review
    assert "not run" in review
    assert "critical findings require changes" in review

    test_command = flat(read(".opencode/commands/test.md"))
    assert "before review" in test_command
    assert "uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py" in test_command
    assert "not run" in test_command


def test_backlog_templates_include_status():
    add_backlog = read(".opencode/commands/add-backlog.md")
    assert "**Status**: Pending" in add_backlog
    assert "**Status**: [Pending | In Progress | Blocked | Done]" in read("backlog/backlog.md")


def test_planner_emits_juicer_decompose_contract():
    normalized = flat(read(".opencode/agents/planner.md"))
    assert "juicer decompose" in normalized
    assert "invest" in normalized
    assert "critical path" in normalized
    for token in ("acceptance_criteria", "verification", "depends_on", "scope", "checks"):
        assert token in normalized


def test_start_command_delegates_to_the_core():
    normalized = flat(read(".opencode/commands/start.md"))
    assert "juicer run task-xxx" in normalized
    assert "juicer integrate" in normalized
    assert "do not call `@orchestrator` directly" in normalized
    assert "call `@orchestrator` to execute" not in normalized


def test_skills_are_the_single_source_of_truth():
    review = flat(read(".opencode/skills/code-review-checklist/SKILL.md"))
    security = flat(read(".opencode/skills/security-review/SKILL.md"))
    assert "single source of truth" in review
    assert "google engineering practices" in review
    assert "single source of truth" in security
    assert "owasp top 10 2021" in security
    for category in (
        "a01 broken access control",
        "a02 cryptographic failures",
        "a03 injection",
        "a04 insecure design",
        "a05 security misconfiguration",
        "a06 vulnerable and outdated components",
        "a07 identification and authentication failures",
        "a08 software and data integrity failures",
        "a09 security logging and monitoring failures",
        "a10 server-side request forgery",
    ):
        assert category in security

    context = flat(read(".opencode/skills/context-management/SKILL.md"))
    assert "## handoffs" in context
    assert "section 16" in context
    api = flat(read(".opencode/skills/api-design/SKILL.md"))
    assert "## versioning" in api
    assert "breaking change requires a new major version" in api
    tdd = flat(read(".opencode/skills/tdd-workflow/SKILL.md"))
    assert "## legacy code" in tdd
    assert "characterization" in tdd
    prd = flat(read(".opencode/skills/prd-template/SKILL.md"))
    assert "@architect" in prd
    assert "high-level" in prd


def test_no_agents_were_added_or_removed():
    actual = {path.stem for path in AGENTS_DIR.glob("*.md")}
    assert actual == EXPECTED_AGENTS


def test_readme_points_to_plan_and_distinguishes_measured_from_planned():
    text = read("README.md")
    normalized = flat(text)
    assert "docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md" in text
    assert "OpenCode 2.x/V2" in text
    assert "v2.2.7" in text
    assert "degraded" in normalized
    assert "compatibility with v1 is not promised" in normalized
    assert "measured capabilities versus planned gaps" in normalized
    assert "not a substitute for these gates" in normalized


def test_readme_quality_gates_match_core_order():
    text = read("README.md")
    gates = section(text, "### Quality Gates", "If you don't use `@orchestrator`")
    assert_canonical_order(gates, "README quality gates")


def test_readme_does_not_promise_implicit_review_or_security_gates():
    normalized = flat(read("README.md"))
    assert "when the task policy requires them" in normalized
    assert "missing, stale or malformed evidence blocks the merge when the corresponding gate is declared" in normalized
    assert "security is not added implicitly, including for high-risk tasks" in normalized
    assert "declare `security` in `required_gates`" in normalized
    assert "high risk always requires recorded human approval" in normalized
    assert "high-risk tasks require security" not in normalized


def test_readme_agent_table_documents_test_before_review():
    lines = read("README.md").splitlines()
    tester = [line for line in lines if line.startswith("| `@tester`")]
    reviewer = [line for line in lines if line.startswith("| `@reviewer`")]
    assert len(tester) == 1 and len(reviewer) == 1
    assert "after implementation, before review" in tester[0].lower()
    assert "after deterministic checks and before merge" in reviewer[0].lower()


def test_guide_uses_capability_selection_not_fixed_pipelines():
    text = read("docs/GUIDE.md")
    normalized = flat(text)
    assert "4.1.0" in text
    assert "capability model" in normalized
    assert "## capability selection" in normalized
    assert "no mandatory agent chain" in normalized
    assert "selects only the capabilities" in normalized
    assert "simple bug" in normalized and "@fixer" in text
    assert "@finder" in text and "@architect" in text and "@coder" in text
    assert "follows pipeline automatically" not in normalized
    assert "starts the agent pipeline" not in normalized
    assert "complete development team" not in normalized
    assert "product owner" not in normalized
    assert "each agent is a **specialist**" not in normalized
    for line in text.splitlines():
        assert not re.match(r"\s*\d+\.\s+@[a-z]+\s*→", line), (
            "rigid GUIDE pipeline reintroduced: %s" % line
        )


def test_agents_are_capabilities_and_do_not_pin_models():
    for path in sorted(AGENTS_DIR.glob("*.md")):
        normalized = flat(path.read_text(encoding="utf-8"))
        assert "**capability.**" in normalized or "**capability**:" in normalized, path.name
    for agent in ("commenter", "documenter"):
        assert "model:" not in frontmatter(".opencode/agents/%s.md" % agent), agent
        assert "the task contract grants the effective write set" in flat(
            read(".opencode/agents/%s.md" % agent)
        ), agent


def test_reviewer_and_security_defer_checklists_to_skills():
    reviewer = flat(read(".opencode/agents/reviewer.md"))
    security = flat(read(".opencode/agents/security.md"))
    assert "code-review-checklist" in reviewer
    assert "single source of truth" in reviewer
    assert "## google code review checklist" not in reviewer
    assert "a01 broken access control" not in reviewer
    assert '{"verdict": "pass", "findings"' in reviewer

    assert "security-review" in security
    assert "single source of truth" in security
    assert "## owasp top 10 2021 — required coverage" not in security
    assert "| a01 | broken access control |" not in security
    assert '{"verdict": "pass", "findings"' in security


def test_status_separates_measured_capability_from_planned_gap():
    text = read("STATUS.md")
    normalized = flat(text)
    assert "docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md" in text
    assert "OpenCode 2.x/V2" in text
    assert "opencode v2.2.7" in text
    assert "capacidade **medida**" in normalized
    assert "lacuna planejada" in normalized
    assert "compatibilidade v1 como alvo" in normalized
    assert "não prometida" in normalized
    assert "permissões v2 ≠ gates" in normalized
    assert "barreira adicional" in normalized
    assert "tests/test_docs_alignment.py" in text


def test_harness_contract_is_v2_aligned_and_marks_v1_as_history():
    text = read("docs/HARNESS_CONTRACT.md")
    normalized = flat(text)
    assert "OpenCode 2.x/V2" in text
    assert "histórico" in normalized
    assert "promessa de compatibilidade" in normalized
    assert "ausente na v2 medida" in normalized
    assert "standalone_flag" in text
    assert "não substituem gates" in normalized
    assert "barreira" in normalized
    assert "política granular documental" in normalized
    assert "política granular medida" not in normalized


def test_adapter_comments_mark_remaining_v1_references_as_historical():
    text = read("juicer/harness/opencode.py")
    assert "V1 references in this module are historical" in text
    v1_lines = [line for line in text.splitlines() if "V1" in line]
    assert v1_lines, "expected adapter to retain historical V1 notes"
    for line in v1_lines:
        lowered = line.lower()
        assert "historical" in lowered or "legacy" in lowered, line
