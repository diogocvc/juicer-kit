import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "juicer"
ADAPTERS = ["codex", "opencode", "claude-code", "cursor", "zed"]
CAPABILITY_KEYS = ["skills", "subagents", "parallel_agents", "human_approval", "persistent_context"]


def load_yaml(name):
    path = ROOT / "adapters" / name / "adapter.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict), f"{path} is not a YAML mapping"
    return data


def cli_capabilities(name):
    r = subprocess.run([str(CLI), "capabilities", name], cwd=str(ROOT),
                       text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    caps = {}
    in_block = False
    for line in r.stdout.splitlines():
        if line == "capabilities:":
            in_block = True
            continue
        if in_block:
            if not line.startswith("  "):
                break
            key, value = line.strip().split(": ", 1)
            caps[key] = {"true": True, "false": False}.get(value, value)
    return caps


def test_all_adapters_have_contract():
    for name in ADAPTERS:
        data = load_yaml(name)
        assert data["id"] == name
        assert data["contract_version"] == 1
        assert data["canonical_state"] == ".juicer"
        assert data["canonical_skills"] == ".agents/skills"
        assert data["canonical_agents"] == "agents"
        assert sorted(data["capabilities"]) == sorted(CAPABILITY_KEYS)
        assert all(isinstance(data["capabilities"][k], bool) for k in CAPABILITY_KEYS)


def test_adapter_yaml_matches_python_capabilities():
    for name in ADAPTERS:
        data = load_yaml(name)
        assert data["capabilities"] == cli_capabilities(name), f"{name} yaml/Python capability drift"


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
