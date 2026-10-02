import json
import subprocess
from pathlib import Path
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "juicer"

def run(*args):
    return subprocess.run([str(CLI), *args], cwd=ROOT, text=True, capture_output=True)

def test_version_files():
    version = (ROOT / "VERSION").read_text().strip()
    assert version == "2.4.0"
    assert yaml.safe_load((ROOT / "kit.yaml").read_text())["version"] == version
    assert json.loads((ROOT / ".juicer" / "state.json").read_text())["kit_version"] == version
    assert json.loads((ROOT / "package.json").read_text())["version"] == version
    cli = (ROOT / "bin" / "juicer").read_text()
    assert f"Juicer Kit v{version} initialized." in cli
    assert f"Juicer Kit v{version} CLI." in cli
    assert cli.count(f'"kit_version":"{version}"') == 2

def test_roles_exist():
    expected = ["finder","analyst","architect","planner","coder","reviewer","tester","security"]
    for role in expected:
        assert (ROOT / "agents" / f"{role}.md").exists()

def test_skills_have_frontmatter():
    for p in (ROOT / ".agents" / "skills").glob("*/SKILL.md"):
        assert p.read_text().startswith("---")

def test_cli_help():
    r = run("--help")
    assert r.returncode == 0
