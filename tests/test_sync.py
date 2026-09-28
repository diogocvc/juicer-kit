import json
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"


def run(cwd, *args):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True, capture_output=True)


def manifest_path(tmp, adapter):
    return tmp / ".juicer" / "runtime" / "manifests" / f"{adapter}.json"


def manifest_files(tmp, adapter):
    return json.loads(manifest_path(tmp, adapter).read_text())["files"]


def test_manifest_written_and_stable(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    files = manifest_files(tmp_path, "opencode")
    assert len(files) == 16
    assert all(key.startswith(".opencode/agents/") for key in files)
    assert all(len(digest) == 64 for digest in files.values())
    assert "AGENTS.md" not in files

    before = manifest_path(tmp_path, "opencode").read_bytes()
    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0, r.stderr
    assert "(0 written, 0 stale removed)" in r.stdout
    assert manifest_path(tmp_path, "opencode").read_bytes() == before


def test_stale_generated_file_removed(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / "agents" / "finder.md").unlink()

    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0, r.stderr
    assert "(0 written, 1 stale removed)" in r.stdout
    assert not (tmp_path / ".opencode" / "agents" / "finder.md").exists()
    assert "finder" not in "".join(manifest_files(tmp_path, "opencode"))


def test_modified_stale_kept_until_force(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / "agents" / "finder.md").unlink()
    stale = tmp_path / ".opencode" / "agents" / "finder.md"
    stale.write_text(stale.read_text() + "\nUSER EDIT\n")

    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0
    assert stale.exists()
    assert "conflict:" in r.stderr
    assert str(stale.relative_to(tmp_path)) in manifest_files(tmp_path, "opencode")

    r = run(tmp_path, "sync", "opencode", "--force")
    assert r.returncode == 0, r.stderr
    assert not stale.exists()
    assert str(stale.relative_to(tmp_path)) not in manifest_files(tmp_path, "opencode")


def test_dry_run_changes_nothing(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / "agents" / "finder.md").unlink()
    reviewer = tmp_path / "agents" / "reviewer.md"
    reviewer.write_text(reviewer.read_text() + "\nNew canonical line.\n")
    before_manifest = manifest_path(tmp_path, "opencode").read_bytes()
    before_generated = (tmp_path / ".opencode" / "agents" / "reviewer.md").read_text()

    r = run(tmp_path, "sync", "opencode", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "sync plan: opencode" in r.stdout
    assert "  write .opencode/agents/reviewer.md" in r.stdout
    assert "  delete .opencode/agents/finder.md (stale)" in r.stdout
    assert (tmp_path / ".opencode" / "agents" / "finder.md").exists()
    assert (tmp_path / ".opencode" / "agents" / "reviewer.md").read_text() == before_generated
    assert manifest_path(tmp_path, "opencode").read_bytes() == before_manifest


def test_check_exit_codes(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "sync", "opencode", "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "up to date" in r.stdout

    target = tmp_path / ".opencode" / "agents" / "reviewer.md"
    target.write_text(target.read_text() + "\ntampered\n")
    r = run(tmp_path, "sync", "opencode", "--check")
    assert r.returncode == 1
    assert "pending" in r.stdout
    assert "tampered" not in r.stdout

    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0
    assert run(tmp_path, "sync", "opencode", "--check").returncode == 0


def test_unmanaged_files_never_deleted(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    custom = tmp_path / ".opencode" / "agents" / "custom.md"
    custom.write_text("---\ndescription: mine\n---\n\nmine\n")
    (tmp_path / "agents" / "finder.md").unlink()

    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0, r.stderr
    assert custom.exists()
    assert not (tmp_path / ".opencode" / "agents" / "finder.md").exists()


def test_claude_skills_mirror_pruned(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert (tmp_path / ".claude" / "skills" / "ship").exists()
    import shutil
    shutil.rmtree(tmp_path / ".agents" / "skills" / "ship")

    r = run(tmp_path, "sync", "claude-code")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / ".claude" / "skills" / "ship").exists()
    files = manifest_files(tmp_path, "claude-code")
    assert not any(".claude/skills/ship" in key for key in files)


def test_entrypoint_is_project_owned(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    files = manifest_files(tmp_path, "opencode")
    assert "AGENTS.md" not in files

    entrypoint = tmp_path / "AGENTS.md"
    entrypoint.write_text(entrypoint.read_text() + "\nMY PROJECT NOTE\n")
    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0, r.stderr
    assert "MY PROJECT NOTE" in entrypoint.read_text()
    assert "AGENTS.md" not in manifest_files(tmp_path, "opencode")
