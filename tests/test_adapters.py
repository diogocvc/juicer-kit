from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_all_adapters_have_contract():
    adapters = ["codex", "opencode", "claude-code", "cursor", "zed"]
    for name in adapters:
        p = ROOT / "adapters" / name / "adapter.yaml"
        assert p.exists()
        text = p.read_text()
        assert "contract_version: 1" in text
        assert "canonical_state: .juicer" in text
        assert "canonical_skills: .agents/skills" in text
        assert "canonical_agents: agents" in text

def test_core_does_not_depend_on_harness():
    core = [
        ROOT / "AGENTS.md",
        ROOT / "agents",
        ROOT / ".agents",
        ROOT / ".juicer",
    ]
    assert all(p.exists() for p in core)

def test_codex_uses_universal_entrypoint():
    assert "AGENTS.md" in (ROOT / "adapters" / "codex" / "README.md").read_text()
