import subprocess
import textwrap
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
KIT_ADAPTERS = {"claude-code", "codex", "cursor", "opencode", "zed"}
CAPABILITY_KEYS = ["skills", "subagents", "parallel_agents", "human_approval", "persistent_context"]

FAKE_ADAPTER = textwrap.dedent(
    """
    from _base import Adapter as BaseAdapter, ensure_entrypoint, write_generated

    class Adapter(BaseAdapter):
        id = "fake"
        marker_dir = ".fake"

        def capabilities(self):
            return {
                "skills": True,
                "subagents": False,
                "parallel_agents": False,
                "human_approval": True,
                "persistent_context": False,
            }

        def sync(self, ctx, dry_run=False):
            changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
            changes.append(
                write_generated(ctx.root / ".fake" / "generated.txt", "generated\\n", dry_run=dry_run)
            )
            return changes
    """
)

OVERRIDE_ZED = textwrap.dedent(
    """
    from _base import Adapter as BaseAdapter, ensure_entrypoint, write_generated

    class Adapter(BaseAdapter):
        id = "zed"
        marker_dir = None

        def capabilities(self):
            return {
                "skills": True,
                "subagents": False,
                "parallel_agents": False,
                "human_approval": True,
                "persistent_context": True,
            }

        def sync(self, ctx, dry_run=False):
            changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
            changes.append(
                write_generated(ctx.root / ".zed-override.txt", "project wins\\n", dry_run=dry_run)
            )
            return changes
    """
)


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True, capture_output=True)


def write_adapter(root, name, source):
    directory = root / "adapters" / name
    directory.mkdir(parents=True)
    (directory / "adapter.py").write_text(source)
    (directory / "adapter.yaml").write_text("contract_version: 1\n")
    return directory


def test_kit_adapters_discovered():
    r = run(KIT, "adapters")
    assert r.returncode == 0, r.stderr
    assert set(r.stdout.split()) == KIT_ADAPTERS


def test_project_adapter_discovered_without_cli_change(tmp_path):
    assert run(tmp_path, "adapters").returncode == 0
    assert set(run(tmp_path, "adapters").stdout.split()) == KIT_ADAPTERS

    write_adapter(tmp_path, "fake", FAKE_ADAPTER)
    assert set(run(tmp_path, "adapters").stdout.split()) == KIT_ADAPTERS | {"fake"}

    r = run(tmp_path, "capabilities", "fake")
    assert r.returncode == 0, r.stderr
    assert "id: fake" in r.stdout
    assert "subagents: false" in r.stdout
    assert "discover:" in r.stdout

    r = run(tmp_path, "sync", "fake")
    assert r.returncode == 0, r.stderr
    assert "synced: fake" in r.stdout
    assert (tmp_path / ".fake" / "generated.txt").read_text() == "generated\n"
    assert (tmp_path / "AGENTS.md").exists()


def test_unknown_adapter_exits_one(tmp_path):
    r = run(tmp_path, "sync", "nope")
    assert r.returncode == 1
    assert "Unknown adapter: nope" in r.stderr
    assert r.stdout == ""

    r = run(tmp_path, "capabilities", "nope")
    assert r.returncode == 1
    assert "Unknown adapter: nope" in r.stderr
    assert r.stdout == ""


def test_project_adapter_overrides_kit_id(tmp_path):
    write_adapter(tmp_path, "zed", OVERRIDE_ZED)
    r = run(tmp_path, "sync", "zed")
    assert r.returncode == 0, r.stderr
    assert "synced: zed" in r.stdout
    assert (tmp_path / ".zed-override.txt").read_text() == "project wins\n"


def test_install_writes_marker_but_sync_does_not(tmp_path):
    r = run(tmp_path, "sync", "codex")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / ".codex" / "juicer-kit.md").exists()

    r = run(tmp_path, "install", "codex")
    assert r.returncode == 0, r.stderr
    assert "installed: codex" in r.stdout
    assert (tmp_path / ".codex" / "juicer-kit.md").exists()


def test_invoke_returns_harness_instructions(tmp_path):
    r = run(tmp_path, "invoke", "opencode", "reviewer", "--unit", "UNIT-001")
    assert r.returncode == 0, r.stderr
    assert "harness: opencode" in r.stdout
    assert "@reviewer" in r.stdout
    assert "UNIT-001" in r.stdout
    assert "never calls a model" in r.stdout

    r = run(tmp_path, "invoke", "opencode", "no-such-worker")
    assert r.returncode == 1
    assert "Unknown worker" in r.stderr


def test_kit_adapters_expose_full_contract():
    for adapter_id in sorted(KIT_ADAPTERS):
        r = run(KIT, "capabilities", adapter_id)
        assert r.returncode == 0, f"{adapter_id}: {r.stderr}"
        assert f"id: {adapter_id}" in r.stdout
        for key in CAPABILITY_KEYS:
            assert f"  {key}: " in r.stdout, f"{adapter_id} missing {key}"
        assert "discover:" in r.stdout
