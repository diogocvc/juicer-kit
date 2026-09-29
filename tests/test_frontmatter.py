import subprocess
from pathlib import Path

import pytest

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
ACCESS_LEVELS = {"read-only", "edit", "full"}
TIER_LEVELS = {"hot", "warm", "cold"}
FORBIDDEN = ("role:", "access:", "tier:", "model:")


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True, capture_output=True)


def frontmatter(path):
    lines = path.read_text().splitlines()
    assert lines[0] == "---", path
    data, seen = {}, False
    for line in lines[1:]:
        if line == "---":
            seen = True
            break
        if line and not line[0].isspace() and ":" in line:
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip()
    assert seen, f"unterminated frontmatter in {path}"
    return data


def assert_no_forbidden(path):
    for line in path.read_text().splitlines():
        for bad in FORBIDDEN:
            assert not line.startswith(bad), f"{path}: forbidden key line {line!r}"


def test_canonical_workers_declare_access_and_tier():
    workers = sorted((KIT / "agents").glob("*.md"))
    assert len(workers) == 16
    for path in workers:
        data = frontmatter(path)
        assert data["access"] in ACCESS_LEVELS, path
        assert data["tier"] in TIER_LEVELS, path
        assert data["role"] == path.stem, path


def test_generated_frontmatter_uses_only_harness_keys(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "sync", "all").returncode == 0

    for path in sorted((tmp_path / ".opencode" / "agents").glob("*.md")):
        assert set(frontmatter(path)) == {"description", "mode", "permission"}, path
        assert_no_forbidden(path)
    for path in sorted((tmp_path / ".claude" / "agents").glob("*.md")):
        keys = set(frontmatter(path))
        assert {"name", "description"} <= keys, path
        assert keys <= {"name", "description", "tools"}, path
        assert_no_forbidden(path)
    for path in sorted((tmp_path / ".cursor" / "agents").glob("*.md")):
        keys = set(frontmatter(path))
        assert "description" in keys, path
        assert keys <= {"description", "readonly"}, path
        assert_no_forbidden(path)


def test_opencode_permission_mapping(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "sync", "opencode").returncode == 0
    reviewer = (tmp_path / ".opencode" / "agents" / "reviewer.md").read_text()
    assert "permission:\n  edit: deny\n  bash: deny" in reviewer
    coder = (tmp_path / ".opencode" / "agents" / "coder.md").read_text()
    assert "permission:\n  edit: allow\n  bash: ask" in coder
    devops = (tmp_path / ".opencode" / "agents" / "devops.md").read_text()
    assert "permission:\n  edit: allow\n  bash: allow" in devops


def test_opencode_v2_format_flag(tmp_path):
    assert run(tmp_path, "init").returncode == 0, "init"
    r = run(tmp_path, "sync", "opencode", "--opencode-format", "v2")
    assert r.returncode == 0, r.stderr
    reviewer = (tmp_path / ".opencode" / "agents" / "reviewer.md").read_text()
    assert "permissions:" in reviewer
    assert "- action: edit" in reviewer
    assert 'resource: "*"' in reviewer
    assert "effect: deny" in reviewer
    assert "permission:" not in reviewer
    assert "shell" in reviewer
    assert_no_forbidden(tmp_path / ".opencode" / "agents" / "reviewer.md")
    assert "name:" not in reviewer.split("---")[1]


def test_claude_tools_mapping(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "sync", "claude-code").returncode == 0
    reviewer = frontmatter(tmp_path / ".claude" / "agents" / "reviewer.md")
    assert reviewer["name"] == "reviewer"
    assert "Read" in reviewer["tools"]
    assert "Write" not in reviewer["tools"]
    assert "Bash" not in reviewer["tools"]

    coder = frontmatter(tmp_path / ".claude" / "agents" / "coder.md")
    assert "Write" in coder["tools"]
    assert "Bash" in coder["tools"]

    devops_text = (tmp_path / ".claude" / "agents" / "devops.md").read_text()
    assert "tools:" not in devops_text.split("---")[1]
    assert "name: devops" in devops_text


def test_cursor_readonly_mapping(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "sync", "cursor").returncode == 0
    reviewer = (tmp_path / ".cursor" / "agents" / "reviewer.md").read_text()
    assert "readonly: true" in reviewer
    assert "name:" not in reviewer.split("---")[1]

    coder_text = (tmp_path / ".cursor" / "agents" / "coder.md").read_text()
    assert "readonly" not in coder_text.split("---")[1]
    assert_no_forbidden(tmp_path / ".cursor" / "agents" / "coder.md")


@pytest.mark.skipif(tomllib is None, reason="tomllib requires Python 3.11+")
def test_codex_toml_uses_documented_keys_only(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "sync", "codex").returncode == 0

    reviewer_path = tmp_path / ".codex" / "agents" / "reviewer.toml"
    parsed = tomllib.loads(reviewer_path.read_text())
    assert parsed["name"] == "reviewer"
    assert parsed["description"] == "Code review"
    assert parsed["sandbox_mode"] == "read-only"
    assert "## Objective" in parsed["developer_instructions"]
    for key in parsed:
        assert key in {"name", "description", "sandbox_mode", "developer_instructions"}

    coder = tomllib.loads((tmp_path / ".codex" / "agents" / "coder.toml").read_text())
    assert coder["sandbox_mode"] == "workspace-write"
    devops = tomllib.loads((tmp_path / ".codex" / "agents" / "devops.toml").read_text())
    assert devops["sandbox_mode"] == "workspace-write"


def test_generated_files_carry_provenance_marker(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "sync", "all").returncode == 0
    opencode = (tmp_path / ".opencode" / "agents" / "reviewer.md").read_text()
    assert "<!-- juicer-kit: generated from agents/reviewer.md sha256:" in opencode
    codex = (tmp_path / ".codex" / "agents" / "reviewer.toml").read_text()
    assert codex.startswith("# juicer-kit: generated from agents/reviewer.md sha256:")
    cursor = (tmp_path / ".cursor" / "agents" / "reviewer.md").read_text()
    assert "sha256:" in cursor
    claude = (tmp_path / ".claude" / "agents" / "reviewer.md").read_text()
    assert "<!-- juicer-kit: generated from agents/reviewer.md sha256:" in claude


WORKER_CONTRACT_LINES = [
    "1. Read `.juicer/mission.md`, `.juicer/plan.md` and `.juicer/handoff.md` before acting.",
    "2. Work only within the active unit scope.",
    "3. Do not silently expand scope.",
    "4. Prefer evidence over assumptions.",
    "5. Keep context narrow: inspect only relevant files.",
    "6. Do not declare completion without verification evidence.",
    "7. Record durable findings in `.juicer/handoff.md` or `.juicer/learnings.md`.",
    "8. Preserve human gates. Never treat a missing approval as implicit approval.",
]
OUTPUT_HEADINGS = ["### Result", "### Evidence", "### Risks", "### Next action"]


def test_workers_share_operating_contract():
    workers = sorted((KIT / "agents").glob("*.md"))
    assert len(workers) == 16
    for path in workers:
        text = path.read_text()
        for line in WORKER_CONTRACT_LINES:
            assert line in text, f"{path}: missing contract line {line!r}"
        for heading in OUTPUT_HEADINGS:
            assert heading in text, f"{path}: missing heading {heading!r}"
