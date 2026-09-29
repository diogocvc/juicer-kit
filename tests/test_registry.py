import os
import subprocess
import textwrap
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"
KIT_ADAPTERS = {"claude-code", "codex", "cursor", "opencode", "zed"}
CAPABILITY_KEYS = ["skills", "subagents", "parallel_agents", "human_approval", "persistent_context"]

FAKE_ADAPTER = textwrap.dedent(
    """
    from _base import Adapter as BaseAdapter, ensure_entrypoint, write_generated

    class Adapter(BaseAdapter):
        id = "fake"
        executable = "juicer-no-such-binary"
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
                write_generated(ctx.root / ".fake" / "generated.txt", "generated\\n",
                                root=ctx.root, dry_run=dry_run)
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
                write_generated(ctx.root / ".zed-override.txt", "project wins\\n",
                                root=ctx.root, dry_run=dry_run)
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


def test_project_adapter_ignored_by_default(tmp_path):
    r = run(tmp_path, "adapters")
    assert r.returncode == 0, r.stderr
    assert set(r.stdout.split()) == KIT_ADAPTERS

    write_adapter(tmp_path, "fake", FAKE_ADAPTER)

    r = run(tmp_path, "adapters")
    assert r.returncode == 0, r.stderr
    assert set(r.stdout.split()) == KIT_ADAPTERS
    assert "project adapters skipped (untrusted)" in r.stderr
    assert "adapters/fake/" in r.stderr

    r = run(tmp_path, "capabilities", "fake")
    assert r.returncode == 1
    assert "untrusted project code" in r.stderr
    assert r.stdout == ""

    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "sync", "fake")
    assert r.returncode == 1
    assert "untrusted project code" in r.stderr
    assert not (tmp_path / ".fake").exists()


def test_project_adapter_loads_with_trust_flag(tmp_path):
    write_adapter(tmp_path, "fake", FAKE_ADAPTER)

    r = run(tmp_path, "adapters", "--trust-project-adapters")
    assert r.returncode == 0, r.stderr
    assert set(r.stdout.split()) == KIT_ADAPTERS | {"fake"}
    assert "skipped" not in r.stderr

    r = run(tmp_path, "capabilities", "fake", "--trust-project-adapters")
    assert r.returncode == 0, r.stderr
    assert "id: fake" in r.stdout
    assert "subagents: false" in r.stdout
    assert "discover:" in r.stdout

    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "sync", "fake", "--trust-project-adapters")
    assert r.returncode == 0, r.stderr
    assert "synced: fake" in r.stdout
    assert (tmp_path / ".fake" / "generated.txt").read_text() == "generated\n"
    assert (tmp_path / "AGENTS.md").exists()


def test_project_adapter_loads_with_env(tmp_path):
    write_adapter(tmp_path, "fake", FAKE_ADAPTER)
    env = dict(os.environ, JUICER_TRUST_PROJECT_ADAPTERS="1")
    r = subprocess.run([str(CLI), "adapters"], cwd=str(tmp_path),
                       text=True, capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    assert set(r.stdout.split()) == KIT_ADAPTERS | {"fake"}
    assert "skipped" not in r.stderr


def test_init_does_not_load_untrusted_project_adapters(tmp_path):
    write_adapter(tmp_path, "fake", FAKE_ADAPTER)
    r = run(tmp_path, "init")
    assert r.returncode == 0, r.stderr
    assert "project adapters skipped (untrusted)" in r.stderr
    assert "adapters/fake/" in r.stderr
    assert not (tmp_path / ".fake").exists()
    assert set(run(tmp_path, "adapters").stdout.split()) == KIT_ADAPTERS


def test_unknown_adapter_exits_one(tmp_path):
    assert run(tmp_path, "init").returncode == 0
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
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "sync", "zed", "--trust-project-adapters")
    assert r.returncode == 0, r.stderr
    assert "synced: zed" in r.stdout
    assert (tmp_path / ".zed-override.txt").read_text() == "project wins\n"


def test_install_writes_marker_but_sync_does_not(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "sync", "codex")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / ".codex" / "juicer-kit.md").exists()

    r = run(tmp_path, "install", "codex")
    assert r.returncode == 0, r.stderr
    assert "installed: codex" in r.stdout
    assert (tmp_path / ".codex" / "juicer-kit.md").exists()


INVOKE_CASES = [
    ("opencode", "native route: @reviewer in chat"),
    ("claude-code", "native route: Agent tool with subagent_type=reviewer"),
    ("cursor", "native route: Task tool, subagent_type=reviewer"),
    ("codex", "native route: Codex custom agent .codex/agents/reviewer.toml"),
    ("zed", "native route: none; Zed has no subagents"),
]


@pytest.mark.parametrize("adapter_id,native", INVOKE_CASES)
def test_invoke_returns_harness_instructions(tmp_path, adapter_id, native):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "invoke", adapter_id, "reviewer", "--unit", "UNIT-001")
    assert r.returncode == 0, r.stderr
    assert f"harness: {adapter_id}" in r.stdout
    assert native in r.stdout
    assert "UNIT-001" in r.stdout
    assert "never calls a model" in r.stdout

    r = run(tmp_path, "invoke", adapter_id, "no-such-worker")
    assert r.returncode == 1
    assert "Unknown worker" in r.stderr


def test_discover_reports_missing_binary(tmp_path):
    write_adapter(tmp_path, "fake", FAKE_ADAPTER)
    r = run(tmp_path, "capabilities", "fake", "--trust-project-adapters")
    assert r.returncode == 0, r.stderr
    assert "discover:" in r.stdout
    assert "  available: false" in r.stdout
    assert "'juicer-no-such-binary' not found on PATH" in r.stdout


def test_kit_adapters_expose_full_contract():
    for adapter_id in sorted(KIT_ADAPTERS):
        r = run(KIT, "capabilities", adapter_id)
        assert r.returncode == 0, f"{adapter_id}: {r.stderr}"
        assert f"id: {adapter_id}" in r.stdout
        for key in CAPABILITY_KEYS:
            assert f"  {key}: " in r.stdout, f"{adapter_id} missing {key}"
        assert "discover:" in r.stdout
