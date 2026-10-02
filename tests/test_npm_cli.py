"""npm CLI (@juicer-kit/cli): install materialization, root guard, manifest."""

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
PKG = json.loads((KIT / "package.json").read_text())
VERSION = (KIT / "VERSION").read_text().strip()
JS_CLI = KIT / "npm" / "bin" / "juicer-kit.js"
ROOT_GUARD = KIT / "npm" / "lib" / "root-guard.js"
INSTALL_LIB = KIT / "npm" / "lib" / "install.js"
CLI = KIT / "bin" / "juicer"

requires_node = pytest.mark.skipif(shutil.which("node") is None,
                                   reason="node not available")
requires_toolchain = pytest.mark.skipif(
    shutil.which("node") is None or shutil.which("python3") is None,
    reason="node and python3 required")
is_root = hasattr(os, "getuid") and os.getuid() == 0


def load_cli(name="juicer_cli_npm_test"):
    loader = importlib.machinery.SourceFileLoader(name, str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def node_run(cwd, *args):
    return subprocess.run(["node", str(JS_CLI), *args], cwd=str(cwd),
                          capture_output=True, text=True)


def node_expr(expression):
    return subprocess.run(["node", "-e", expression],
                          capture_output=True, text=True)


def test_package_shape():
    assert PKG["name"] == "@juicer-kit/cli"
    assert PKG["version"] == VERSION
    assert PKG["bin"]["juicer-kit"] == "npm/bin/juicer-kit.js"
    assert "postinstall" not in PKG.get("scripts", {})
    assert "scripts" not in PKG or "postinstall" not in str(PKG["scripts"])
    required = {
        "bin", "adapters", "agents", ".agents",
        ".juicer/templates", ".juicer/workflows",
        "AGENTS.md", "VERSION", "kit.yaml", "npm/bin", "npm/lib",
    }
    assert required <= set(PKG["files"])
    for pattern in ("!**/__pycache__", "!**/*.pyc", "!**/.DS_Store"):
        assert pattern in PKG["files"], pattern


@requires_node
def test_payload_plan_splits_and_excludes():
    expression = f"""
      const {{ payloadPlan }} = require({json.dumps(str(INSTALL_LIB))});
      const plan = payloadPlan([
        "bin", "npm/bin", "npm/lib", ".agents",
        "!**/__pycache__", "!**/*.pyc", "!**/.DS_Store",
      ]);
      let failed = 0;
      const check = (ok, label) => {{ if (!ok) {{ failed += 1; console.error("fail:", label); }} }};
      check(JSON.stringify(plan.positives) === JSON.stringify(["bin", ".agents"]),
            "positives: " + JSON.stringify(plan.positives));
      check(plan.isExcluded("bin/__pycache__"), "dir __pycache__");
      check(plan.isExcluded("bin/__pycache__/x.pyc"), "pyc path");
      check(plan.isExcluded("x.pyc"), "root pyc");
      check(plan.isExcluded(".DS_Store"), "DS_Store");
      check(!plan.isExcluded("bin/juicer"), "bin/juicer kept");
      check(!plan.isExcluded(".agents/skills/ship/SKILL.md"), "skill kept");
      process.exit(failed ? 1 : 0);
    """
    r = node_expr(expression)
    assert r.returncode == 0, r.stderr


def test_root_guard_python_case_table():
    module = load_cli()
    assert "refusing to run as root" in module.root_guard_error(False, 0)
    assert "--force-root" in module.root_guard_error(False, 0)
    assert module.root_guard_error(True, 0) is None
    assert module.root_guard_error(False, 1000) is None
    assert module.root_guard_error(False, None) is None
    assert module.root_guard_error(True, None) is None


@requires_node
def test_root_guard_js_case_table():
    expression = f"""
      const {{ rootGuardError }} = require({json.dumps(str(ROOT_GUARD))});
      const cases = [
        [{{ uid: 0 }}, true],
        [{{ uid: 0, forceRoot: true }}, false],
        [{{ uid: 1000 }}, false],
        [{{ uid: null }}, false],
        [{{ uid: undefined }}, false],
        [{{ uid: 0, yes: true }}, true],
        [{{}}, false],
      ];
      let failed = 0;
      for (const [opts, refuse] of cases) {{
        const err = rootGuardError(opts);
        if (Boolean(err) !== refuse) {{
          failed += 1;
          console.error("case failed:", JSON.stringify(opts), "->", err);
        }}
      }}
      process.exit(failed ? 1 : 0);
    """
    r = node_expr(expression)
    assert r.returncode == 0, r.stderr


@requires_node
def test_python_version_gate():
    expression = f"""
      const {{ pythonVersionError }} = require({json.dumps(str(INSTALL_LIB))});
      const cases = [
        ["3.8\\n", null],
        ["3.12\\n", null],
        ["4.0\\n", null],
        ["3.7\\n", true],
        ["2.7\\n", true],
        ["junk\\n", true],
      ];
      let failed = 0;
      for (const [output, refuse] of cases) {{
        const err = pythonVersionError(output);
        if (Boolean(err) !== Boolean(refuse)) {{
          failed += 1;
          console.error("case failed:", JSON.stringify(output), "->", err);
        }}
      }}
      process.exit(failed ? 1 : 0);
    """
    r = node_expr(expression)
    assert r.returncode == 0, r.stderr


def run_install(cwd, *extra):
    args = ["install", *extra]
    if is_root and "--force-root" not in args:
        args.append("--force-root")
    return node_run(cwd, *args)


@requires_toolchain
def test_install_materializes_kit_and_runs_init(tmp_path):
    r = run_install(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr

    kit_bin = tmp_path / ".juicer-kit" / "bin" / "juicer"
    assert kit_bin.is_file()
    assert (tmp_path / ".juicer-kit" / "AGENTS.md").is_file()
    assert (tmp_path / ".juicer-kit" / ".juicer" / "templates" / "mission.md").is_file()
    assert (tmp_path / ".juicer-kit" / ".juicer" / "workflows" / "release.md").is_file()
    assert not (tmp_path / ".juicer-kit" / "npm").exists()
    assert not (tmp_path / ".juicer-kit" / "tests").exists()
    assert not (tmp_path / ".juicer-kit" / "docs").exists()

    # the python side ran against the materialized kit
    assert (tmp_path / ".juicer" / "state.json").is_file()
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".claude" / "skills").is_dir()

    manifest = json.loads((tmp_path / ".juicer" / "install.json").read_text())
    assert manifest["schema"] == 1
    assert manifest["kit_version"] == VERSION
    assert "installed_at" in manifest
    assert manifest["files"]["bin/juicer"] == hashlib.sha256(
        kit_bin.read_bytes()).hexdigest()
    for rel in manifest["files"]:
        assert not rel.startswith("npm/")
        assert "__pycache__" not in rel
        assert not rel.endswith(".pyc")
    assert ".juicer-kit/" in (tmp_path / ".gitignore").read_text().splitlines()


@requires_toolchain
def test_install_is_byte_idempotent(tmp_path):
    first = run_install(tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr
    manifest_file = tmp_path / ".juicer" / "install.json"
    manifest_bytes = manifest_file.read_bytes()
    kit_bin = tmp_path / ".juicer-kit" / "bin" / "juicer"
    payload_bytes = kit_bin.read_bytes()

    second = run_install(tmp_path)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "install manifest: unchanged" in second.stdout
    assert manifest_file.read_bytes() == manifest_bytes
    assert kit_bin.read_bytes() == payload_bytes


@requires_toolchain
def test_install_yes_never_bypasses_root_guard(tmp_path):
    r = node_run(tmp_path, "install", "--yes")
    if is_root:
        assert r.returncode == 1
        assert "refusing to run as root" in r.stderr
        assert "--yes does not bypass" in r.stderr
        assert not (tmp_path / ".juicer-kit").exists()
    else:
        assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not is_root, reason="root refusal needs uid 0")
@requires_toolchain
def test_install_refuses_root_before_any_write(tmp_path):
    r = node_run(tmp_path, "install")
    assert r.returncode == 1
    assert "refusing to run as root" in r.stderr
    assert not (tmp_path / ".juicer-kit").exists()
    assert not (tmp_path / ".juicer" / "install.json").exists()


@requires_toolchain
def test_install_force_root_flag_reaches_python(tmp_path):
    r = node_run(tmp_path, "install", "--force-root")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / ".juicer-kit" / "bin" / "juicer").is_file()


def test_init_force_root_flag_exists():
    r = subprocess.run([str(CLI), "init", "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "--force-root" in r.stdout


@requires_toolchain
def test_init_refuses_root_without_force_root(tmp_path):
    if not is_root:
        pytest.skip("root refusal needs uid 0")
    r = subprocess.run([str(CLI), "init"], cwd=str(tmp_path),
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "refusing to run as root" in r.stderr
    assert "--force-root" in r.stderr


@requires_node
def test_cli_surface(tmp_path):
    help_r = node_run(tmp_path, "--help")
    assert help_r.returncode == 0
    assert "install" in help_r.stdout

    version_r = node_run(tmp_path, "--version")
    assert version_r.returncode == 0
    assert version_r.stdout.strip() == VERSION

    missing_r = node_run(tmp_path)
    assert missing_r.returncode == 1
    assert "usage:" in missing_r.stderr

    unknown_r = node_run(tmp_path, "bogus")
    assert unknown_r.returncode == 1
    assert "unknown command bogus" in unknown_r.stderr
