"""Security baseline: approval binding, source trust, ownership, identity.

Covers audit findings B-01..B-03 (regression), H-01..H-05, M-01, M-02,
M-05..M-07 and L-03/L-05: the approval must cover the content it
approves, generated harness files must never come from outside the
project/kit, an adapter may only delete what it owns, init must not
silently fork the workspace, status must be read-only, generated harness
permissions must follow the declared access level, dry runs must touch
nothing, approval provenance must be visible and honest about what it
does not prove, a hostile filename must not reach generated content, and
a lock that could not be taken must say so.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CLI = KIT / "bin" / "juicer"


def run(cwd, *args, stdin=None):
    return subprocess.run([str(CLI), *args], cwd=str(cwd), text=True,
                          capture_output=True, stdin=stdin)


def state(tmp_path):
    return json.loads((tmp_path / ".juicer" / "state.json").read_text())


def rewrite_state(tmp_path, **changes):
    path = tmp_path / ".juicer" / "state.json"
    data = json.loads(path.read_text())
    data.update(changes)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def ready_project(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Objective under test").returncode == 0
    assert run(tmp_path, "approve", "--by=test").returncode == 0
    return tmp_path


def approval_status(tmp_path):
    """(parsed stdout, plan verdict, ship verdict) from `juicer status`."""
    r = run(tmp_path, "status")
    assert r.returncode == 0, r.stderr
    shown = json.loads(r.stdout.split("\navailable:")[0])
    plan = next(l for l in r.stderr.splitlines()
                if l.startswith("plan approval:")).split()[2]
    ship = next(l for l in r.stderr.splitlines()
                if l.startswith("ship approval:")).split()[2]
    return shown, plan, ship


# --- H-01: approval is bound to the approved content ----------------------

def test_plan_edit_after_approve_invalidates_approval(tmp_path):
    ready_project(tmp_path)
    shown, plan, _ = approval_status(tmp_path)
    assert plan == "valid"

    with open(tmp_path / ".juicer" / "plan.md", "a") as handle:
        handle.write("\n## Extra (not approved)\n")

    shown, plan, _ = approval_status(tmp_path)
    assert plan == "invalid"
    assert shown["approved"] is False
    r = run(tmp_path, "start", "UNIT-001")
    assert r.returncode == 1
    assert "Blocked" in r.stderr


def test_mission_edit_after_approve_invalidates_approval(tmp_path):
    ready_project(tmp_path)
    with open(tmp_path / ".juicer" / "mission.md", "a") as handle:
        handle.write("\nEdited after approval.\n")

    shown, plan, _ = approval_status(tmp_path)
    assert plan == "invalid"
    assert shown["approved"] is False
    assert run(tmp_path, "start", "UNIT-001").returncode == 1


def test_new_mission_drops_the_previous_approval(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "mission", "Rewritten objective").returncode == 0

    _, plan, _ = approval_status(tmp_path)
    assert plan == "none"
    assert state(tmp_path)["approved"] is False
    assert run(tmp_path, "start", "UNIT-001").returncode == 1


def test_unchanged_plan_keeps_approval_valid(tmp_path):
    ready_project(tmp_path)
    shown, plan, _ = approval_status(tmp_path)
    assert plan == "valid"
    assert shown["approved"] is True
    assert run(tmp_path, "start", "UNIT-001").returncode == 0


@pytest.mark.parametrize("changes", [
    {"via": "hacked"},
    {"by": ""},
    {"by": None},
    {"at": ""},
    {"at": None},
    {"revision": -1},
    {"revision": 0},
    {"revision": "3"},
    {"revision": True},
    {"target": None},
    {"target": {}},
    {"target": {"parts": {}}},
])
def test_forged_approval_record_is_rejected(tmp_path, changes):
    ready_project(tmp_path)
    record = state(tmp_path)["approval"]
    record.update(changes)
    rewrite_state(tmp_path, approval=record)

    shown, plan, _ = approval_status(tmp_path)
    assert plan == "invalid"
    assert shown["approved"] is False
    assert run(tmp_path, "start", "UNIT-001").returncode == 1


def test_future_revision_cannot_approve_the_present(tmp_path):
    ready_project(tmp_path)
    record = state(tmp_path)["approval"]
    record["revision"] = record["revision"] + 100
    rewrite_state(tmp_path, approval=record)

    _, plan, _ = approval_status(tmp_path)
    assert plan == "invalid"


def test_approve_requires_identity_without_tty(tmp_path):
    ready_project(tmp_path)
    r = run(tmp_path, "approve", stdin=subprocess.DEVNULL)
    assert r.returncode == 1
    assert "identity" in r.stderr and "--by" in r.stderr


def test_status_stdout_stays_machine_readable(tmp_path):
    ready_project(tmp_path)
    r = run(tmp_path, "status")
    assert r.returncode == 0, r.stderr
    json.loads(r.stdout.split("\navailable:")[0])          # stdout is pure JSON
    assert "plan approval: valid by=test via=automation" in r.stderr
    assert "ship approval: none" in r.stderr


def test_status_reports_invalid_verdict_with_provenance(tmp_path):
    ready_project(tmp_path)
    with open(tmp_path / ".juicer" / "plan.md", "a") as handle:
        handle.write("\nchanged\n")
    r = run(tmp_path, "status")
    verdict = next(l for l in r.stderr.splitlines()
                   if l.startswith("plan approval:"))
    assert "invalid" in verdict and "by=test" in verdict
    assert any("plan or mission changed" in l for l in r.stderr.splitlines())


# --- H-02: generated files never come from outside the roots ---------------

def test_symlinked_worker_contract_is_refused(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    outside = tmp_path.parent / "stolen-worker.md"
    outside.write_text("SSH-PRIVATE-KEY material\n")
    (tmp_path / "agents").mkdir(exist_ok=True)
    (tmp_path / "agents" / "evil.md").symlink_to(outside)

    r = run(tmp_path, "worker", "evil")
    assert r.returncode == 1
    assert "outside the project and the kit" in r.stderr
    assert outside.read_text() not in r.stdout


def test_symlinked_skills_source_is_skipped(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    secrets = tmp_path.parent / "stolen-skill.md"
    secrets.write_text("# stolen\n")
    skill = tmp_path / ".agents" / "skills" / "code-review" / "SKILL.md"
    skill.unlink()
    skill.symlink_to(secrets)

    r = run(tmp_path, "sync", "claude-code")
    assert r.returncode == 0, r.stderr
    assert "outside the project/kit roots" in r.stderr
    copied = tmp_path / ".claude" / "skills" / "code-review" / "SKILL.md"
    assert not copied.exists()


# --- H-04: an adapter may only delete what it owns -------------------------

def manifest_file(project, adapter="opencode"):
    return project / ".juicer" / "runtime" / "manifests" / f"{adapter}.json"


def tamper_manifest(project, adapter, entry):
    path = manifest_file(project, adapter)
    data = json.loads(path.read_text())
    data["files"].update(entry)
    path.write_text(json.dumps(data, indent=2) + "\n")


def test_manifest_cannot_delete_user_source(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert run(project, "init").returncode == 0
    victim = project / "main.py"
    victim.write_text("print('keep me')\n")
    digest = hashlib.sha256(victim.read_bytes()).hexdigest()
    tamper_manifest(project, "opencode", {"main.py": digest})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1
    assert "not owned by this adapter" in r.stderr
    assert victim.exists()
    assert victim.read_text() == "print('keep me')\n"


def test_manifest_cannot_delete_unrelated_harness_settings(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert run(project, "init").returncode == 0
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(exist_ok=True)
    settings.write_text('{"permissions": "allow-all"}\n')
    digest = hashlib.sha256(settings.read_bytes()).hexdigest()
    tamper_manifest(project, "claude-code", {".claude/settings.json": digest})

    r = run(project, "sync", "claude-code")
    assert r.returncode == 1
    assert "not owned by this adapter" in r.stderr
    assert settings.exists()


def test_manifest_cannot_delete_entrypoint(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert run(project, "init").returncode == 0
    agents_md = project / "AGENTS.md"
    agents_md.write_text("# mine\n")
    digest = hashlib.sha256(agents_md.read_bytes()).hexdigest()
    tamper_manifest(project, "opencode", {"AGENTS.md": digest})

    r = run(project, "sync", "opencode")
    assert r.returncode == 1
    assert "project-owned" in r.stderr or "not owned" in r.stderr
    assert agents_md.exists()


def test_adapter_cannot_generate_paths_it_does_not_own(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert run(project, "init").returncode == 0
    outside_adapter = (project / "adapters" / "stray")
    outside_adapter.mkdir(parents=True)
    (outside_adapter / "adapter.yaml").write_text("contract_version: 1\n")
    (outside_adapter / "adapter.py").write_text(textwrap_dedent_adapter())

    r = run(project, "sync", "stray", "--trust-project-adapters")
    assert r.returncode == 1
    assert "not owned by this adapter" in r.stderr
    assert not (project / "surprise.txt").exists()


def textwrap_dedent_adapter():
    return '''
from _base import Adapter as BaseAdapter, ensure_entrypoint, write_generated

class Adapter(BaseAdapter):
    id = "stray"

    def capabilities(self):
        return {"skills": True, "subagents": False, "parallel_agents": False,
                "human_approval": True, "persistent_context": False}

    def sync(self, ctx, dry_run=False):
        changes = [ensure_entrypoint(ctx, dry_run=dry_run)]
        changes.append(write_generated(ctx.root / "surprise.txt", "surprise\\n",
                                       root=ctx.root, dry_run=dry_run))
        return changes
'''


# --- M-05: ship approval states its own strength ---------------------------

def test_ship_approve_records_code_binding_outside_git(tmp_path):
    ready_project(tmp_path)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    assert run(tmp_path, "checkpoint", "ready").returncode == 0

    r = run(tmp_path, "ship-approve", "--by=test")
    assert r.returncode == 0, r.stderr
    assert "code binding: none" in r.stderr
    assert "NOT bound to a specific commit" in r.stderr
    assert state(tmp_path)["ship_approval"]["code_binding"] == "none"

    # the same limitation is visible in status, not only at approval time
    r = run(tmp_path, "status")
    assert "code_binding=none" in r.stderr
    assert "must not be read as an attestation" in r.stderr


def test_ship_approve_records_code_binding_inside_git(tmp_path):
    ready_project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True,
                   capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], cwd=tmp_path, check=True,
                   capture_output=True)
    assert run(tmp_path, "start", "UNIT-001").returncode == 0
    assert run(tmp_path, "checkpoint", "ready").returncode == 0

    r = run(tmp_path, "ship-approve", "--by=test")
    assert r.returncode == 0, r.stderr
    assert state(tmp_path)["ship_approval"]["code_binding"] == "sha"


# --- H-03: nested init is an explicit decision (see also test_root_discovery)

def test_nested_init_leaves_outer_workspace_untouched(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    assert run(tmp_path, "mission", "Outer").returncode == 0
    before = (tmp_path / ".juicer" / "state.json").read_bytes()
    inner = tmp_path / "sub"
    inner.mkdir()

    r = run(inner, "init")
    assert r.returncode == 1
    assert "--nested" in r.stderr
    assert (tmp_path / ".juicer" / "state.json").read_bytes() == before
    assert not (inner / ".juicer").exists()


# --- M-01: generated harness permissions come from the project's workers ---

def _project_worker(path, access):
    path.write_text(
        "---\n"
        "name: locked\n"
        "description: restricted worker\n"
        "role: locked\n"
        f"access: {access}\n"
        "tier: warm\n"
        "---\n\n"
        "# Locked\n\nBody.\n"
    )


def test_generated_permissions_match_declared_access(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    _project_worker(tmp_path / "agents" / "locked.md", "read-only")

    assert run(tmp_path, "sync", "opencode").returncode == 0
    generated = (tmp_path / ".opencode" / "agents" / "locked.md").read_text()
    assert "edit: deny" in generated and "bash: deny" in generated
    assert "access:" not in generated

    assert run(tmp_path, "sync", "opencode", "--opencode-format", "v2").returncode == 0
    generated = (tmp_path / ".opencode" / "agents" / "locked.md").read_text()
    assert "effect: deny" in generated


def test_invalid_project_worker_access_is_rejected(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    _project_worker(tmp_path / "agents" / "locked.md", "root")

    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 1
    assert "invalid access" in r.stderr
    assert not (tmp_path / ".opencode" / "agents" / "locked.md").exists()


# --- M-02: status is read-only ---------------------------------------------

def test_status_creates_no_files(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    mission = tmp_path / ".juicer" / "mission.md"
    state_file = tmp_path / ".juicer" / "state.json"
    mission.unlink()
    before = state_file.read_bytes()

    r = run(tmp_path, "status")
    assert r.returncode == 0, r.stderr
    assert not mission.exists(), "status recreated .juicer/mission.md"
    assert state_file.read_bytes() == before, "status rewrote .juicer/state.json"


# --- M-07: sync must not write outside a dry run ---------------------------

def test_dry_run_creates_nothing(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    for name in ("agents", ".opencode/agents", ".claude/agents", ".cursor/agents",
                 ".codex/agents", ".claude/skills"):
        target = tmp_path / name
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
    shutil.rmtree(tmp_path / ".juicer" / "runtime", ignore_errors=True)
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))

    r = run(tmp_path, "sync", "all", "--dry-run")
    assert r.returncode == 0, r.stderr
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    assert after == before, f"dry run wrote: {set(after) - set(before)}"


# --- M-01: permission changes must not be silent ---------------------------

def test_sync_warns_when_generated_permissions_change(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    before = (tmp_path / ".opencode" / "agents" / "coder.md").read_text()
    assert "edit: allow" in before

    worker = tmp_path / "agents" / "coder.md"
    worker.write_text(worker.read_text().replace("access: edit",
                                                 "access: read-only"))

    r = run(tmp_path, "sync", "all")
    assert r.returncode == 0, r.stderr
    assert "permission configuration changed: .opencode/agents/coder.md" in r.stderr
    assert "generated mirrors are gitignored" in r.stderr
    after = (tmp_path / ".opencode" / "agents" / "coder.md").read_text()
    assert "edit: deny" in after
    # the canonical source is untouched by the warning path
    assert "access: read-only" in worker.read_text()


def test_sync_is_quiet_when_permissions_are_unchanged(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    r = run(tmp_path, "sync", "all")
    assert r.returncode == 0, r.stderr
    assert "permission configuration changed" not in r.stderr


# --- L-03: a filename must not be able to break out of generated text ----

def test_hostile_worker_name_is_skipped_and_never_rendered(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    hostile = tmp_path / "agents" / "evil-->inject.md"
    hostile.write_text((tmp_path / "agents" / "reviewer.md").read_text())

    r = run(tmp_path, "sync", "all")
    assert r.returncode == 0, r.stderr
    assert "must match ^[a-z][a-z0-9-]*$" in r.stderr
    assert "evil-->inject.md" in r.stderr

    rendered = []
    for harness in (".opencode", ".claude", ".cursor", ".codex"):
        directory = tmp_path / harness / "agents"
        if directory.is_dir():
            rendered += [p.name for p in directory.iterdir()]
    assert not [name for name in rendered if name.startswith("evil")], rendered

    for manifest in (tmp_path / ".juicer" / "runtime" / "manifests").glob("*.json"):
        assert "evil" not in manifest.read_text(), manifest.name
    assert not [p for p in tmp_path.glob("**/*inject*")
                if ".opencode" in p.parts or ".claude" in p.parts
                or ".cursor" in p.parts or ".codex" in p.parts]


def test_valid_worker_names_still_render(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    (tmp_path / "agents" / "my-worker-2.md").write_text(
        (tmp_path / "agents" / "reviewer.md").read_text())
    r = run(tmp_path, "sync", "opencode")
    assert r.returncode == 0, r.stderr
    assert "must match" not in r.stderr
    assert (tmp_path / ".opencode" / "agents" / "my-worker-2.md").exists()


# --- L-05: a lock that could not be taken must say so --------------------

def test_missing_fcntl_warns_that_locking_is_downgraded(tmp_path):
    assert run(tmp_path, "init").returncode == 0
    code = ("import sys, runpy; sys.modules['fcntl'] = None; "
            "sys.argv = ['juicer', 'mission', 'Lock probe']; "
            f"runpy.run_path({str(CLI)!r}, run_name='__main__')")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path),
                       text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    assert "state locking is not enforced" in r.stderr
    assert "docs/security.md" in r.stderr
    assert state(tmp_path)["status"] == "planning"
