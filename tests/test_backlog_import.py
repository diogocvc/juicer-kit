"""One-way backlog Markdown import: validation, safety and idempotency."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import juicer.orchestrator as orchestrator_mod
from juicer.backlog import archived_task_ids, parse_backlog
from juicer.errors import GateBlockedError, JuicerError, ValidationError
from conftest import simple_task_specs

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "juicer"


def run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(BIN)] + args,
        cwd=str(cwd), capture_output=True, text=True,
    )


def task_block(task_id, title=None, *, description="Do the work.",
               priority="P1-High", status="Pending", dependencies="None",
               criteria=("- [ ] works",), extra=""):
    lines = [
        "### Task: [%s] %s" % (task_id, title or ("Task %s" % task_id)),
        "",
        "**Description**: %s" % description,
        "",
        "**Priority**: %s" % priority,
        "",
        "**Status**: %s" % status,
        "",
        "**Dependencies**: %s" % dependencies,
        "",
        "**Acceptance Criteria**:",
    ]
    lines.extend(criteria)
    lines.append("")
    if extra:
        lines.extend(extra.splitlines())
        lines.append("")
    return "\n".join(lines)


def write_backlog(repo, text, name="backlog/backlog.md"):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def task_snapshot(juicer):
    return {p.name: p.read_bytes()
            for p in juicer.tasks_dir.glob("*.json")}


def test_import_valid_backlog_is_one_way(juicer, repo):
    text = (task_block("TASK-001", "First")
            + "\n"
            + task_block("TASK-002", "Second", dependencies="TASK-001"))
    path = write_backlog(repo, text)
    backlog_before = path.read_bytes()
    mission_before = juicer.mission()

    result = juicer.import_backlog()

    assert result["status"] == "imported"
    assert result["source"] == "backlog/backlog.md"
    assert result["sha256"] == hashlib.sha256(backlog_before).hexdigest()
    assert result["task_ids"] == ["TASK-001", "TASK-002"]

    tasks = {task["id"]: task for task in juicer.load_tasks()}
    assert tasks["TASK-001"]["title"] == "First"
    assert tasks["TASK-001"]["priority"] == "P1"
    assert tasks["TASK-001"]["status"] == "ready"
    assert tasks["TASK-001"]["origin"]["source_status"] == "pending"
    assert tasks["TASK-001"]["origin"]["priority_label"] == "P1-High"
    assert tasks["TASK-001"]["acceptance_criteria"][0]["verification"] == "human"
    assert tasks["TASK-002"]["depends_on"] == ["TASK-001"]

    # One-way: neither the backlog nor the mission is rewritten.
    assert path.read_bytes() == backlog_before
    assert juicer.mission() == mission_before

    record = json.loads((juicer.jdir / "imports" / "backlog.json").read_text())
    assert record["type"] == "backlog_import"
    assert record["task_ids"] == ["TASK-001", "TASK-002"]
    assert Path(record["artifact_ref"]).is_absolute() is False
    assert (juicer.root / record["artifact_ref"]).read_bytes() == backlog_before


def test_repeated_import_is_idempotent(juicer, repo):
    write_backlog(repo, task_block("TASK-001"))
    first = juicer.import_backlog()
    assert first["status"] == "imported"
    snapshot = task_snapshot(juicer)

    second = juicer.import_backlog()

    assert second["status"] == "unchanged"
    assert second["task_ids"] == first["task_ids"]
    assert task_snapshot(juicer) == snapshot


def test_changed_backlog_never_overwrites_mission(juicer, repo):
    path = write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    snapshot = task_snapshot(juicer)

    path.write_text(path.read_text() + "\n" + task_block("TASK-002"),
                    encoding="utf-8")

    with pytest.raises(JuicerError, match="changed since the one-way import"):
        juicer.import_backlog()
    assert task_snapshot(juicer) == snapshot
    assert not (juicer.tasks_dir / "TASK-002.json").exists()


def test_import_refuses_mission_with_existing_tasks(juicer, repo):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    write_backlog(repo, task_block("TASK-900"))

    with pytest.raises(JuicerError, match="already has tasks"):
        juicer.import_backlog()
    assert [task["id"] for task in juicer.load_tasks()] == ["TASK-001"]


def test_duplicate_task_ids_are_rejected():
    text = task_block("TASK-001") + "\n" + task_block("TASK-001", "Again")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "duplicate task id TASK-001" in str(exc.value)


def test_unknown_dependency_is_rejected():
    text = task_block("TASK-001", dependencies="TASK-999")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "depends on unknown task TASK-999" in str(exc.value)


@pytest.mark.parametrize("priority, expected", [
    ("P9-High", "invalid priority"),
    ("P1-Low", "inconsistent label"),
    ("urgent", "invalid priority"),
])
def test_invalid_priority_is_rejected(priority, expected):
    text = task_block("TASK-001", priority=priority)

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert expected in str(exc.value)


def test_missing_priority_is_rejected():
    text = task_block("TASK-001").replace("**Priority**: P1-High\n\n", "")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "missing priority" in str(exc.value)


@pytest.mark.parametrize("status", ["Done", "Blocked", "Failed", "Unknown"])
def test_non_importable_status_is_rejected(status):
    text = task_block("TASK-001", status=status)

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "task TASK-001" in str(exc.value)
    assert "status" in str(exc.value)


def test_in_progress_status_is_mapped_to_ready(juicer, repo):
    write_backlog(repo, task_block("TASK-001", status="In Progress"))

    juicer.import_backlog()

    task = juicer.load_task("TASK-001")
    assert task["status"] == "ready"
    assert task["origin"]["source_status"] == "in_progress"


def test_missing_acceptance_criteria_is_rejected():
    text = task_block("TASK-001", criteria=())

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "at least one acceptance criterion is required" in str(exc.value)


def test_malformed_acceptance_criterion_is_rejected():
    text = task_block("TASK-001", criteria=("not a checkbox",))

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "malformed acceptance criterion" in str(exc.value)


def test_missing_description_is_rejected():
    text = task_block("TASK-001").replace(
        "**Description**: Do the work.\n\n", "")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "description is required" in str(exc.value)


def test_fenced_template_block_is_ignored():
    fenced = "\n".join([
        "```markdown",
        "### Task: [TASK-999] Template example",
        "**Priority**: not-a-priority",
        "```",
        "",
    ])
    specs = parse_backlog(fenced + task_block("TASK-001"))

    assert [spec["id"] for spec in specs] == ["TASK-001"]


def test_cycle_is_rejected():
    text = (task_block("TASK-001", dependencies="TASK-002")
            + "\n"
            + task_block("TASK-002", dependencies="TASK-001"))

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "dependency cycle" in str(exc.value)


def test_self_dependency_is_rejected():
    text = task_block("TASK-001", dependencies="TASK-001")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "cannot depend on itself" in str(exc.value)


def test_done_dependency_is_treated_as_satisfied(juicer, repo):
    done = write_backlog(
        repo, "# Task: [TASK-000] Archived task\n", name="backlog/done/TASK-000.md")
    assert "TASK-000" in archived_task_ids([done])
    write_backlog(repo, task_block("TASK-001", dependencies="TASK-000"))

    juicer.import_backlog()

    task = juicer.load_task("TASK-001")
    assert task["depends_on"] == []
    assert task["origin"]["completed_dependencies"] == ["TASK-000"]


def test_archived_duplicate_is_rejected(juicer, repo):
    write_backlog(
        repo, "# Task: [TASK-001] Archived\n", name="backlog/done/TASK-001.md")
    write_backlog(repo, task_block("TASK-001"))

    with pytest.raises(ValidationError, match="already archived"):
        juicer.import_backlog()


def test_replaced_mission_cannot_reuse_import(juicer, repo):
    write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    juicer.set_mission(title="Other", objective="Different", force=True)

    with pytest.raises(JuicerError, match="belongs to a different mission"):
        juicer.import_backlog()


def test_unreadable_backlog_is_reported(juicer, repo):
    path = repo / "backlog" / "backlog.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(JuicerError, match="cannot read backlog file"):
        juicer.import_backlog()


def test_waiting_human_mission_blocks_import(juicer, repo):
    juicer.set_mission(
        title="Blocked", objective="Ship it",
        gaps=[{"id": "GAP-001", "question": "Which DB?", "resolution": None}],
        force=True,
    )
    write_backlog(repo, task_block("TASK-001"))

    with pytest.raises(GateBlockedError, match="GAP-001"):
        juicer.import_backlog()
    assert juicer.load_tasks() == []


def test_source_outside_project_root_is_rejected(juicer, repo, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text(task_block("TASK-001"), encoding="utf-8")

    with pytest.raises(JuicerError, match="inside the project root"):
        juicer.import_backlog(outside)


def test_scope_escaping_project_is_rejected():
    text = task_block("TASK-001", extra="**Scope**: ../secrets")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "cannot escape the project" in str(exc.value)


def test_inconsistent_import_record_fails_safely(juicer, repo):
    write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    (juicer.tasks_dir / "TASK-001.json").unlink()

    with pytest.raises(JuicerError, match="inconsistent"):
        juicer.import_backlog()


def test_failed_import_rolls_back_partial_tasks(juicer, repo, monkeypatch):
    write_backlog(repo, task_block("TASK-001") + "\n" + task_block("TASK-002"))
    real_write_json = orchestrator_mod.write_json

    def flaky(path, data):
        if Path(path).name == "TASK-002.json":
            raise OSError("disk full")
        return real_write_json(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(orchestrator_mod, "write_json", flaky)
        with pytest.raises(OSError, match="disk full"):
            juicer.import_backlog()

    assert juicer.load_tasks() == []
    assert not (juicer.jdir / "imports" / "backlog.json").exists()
    assert list(juicer.evidence_dir.glob("backlog-*.md")) == []

    result = juicer.import_backlog()
    assert result["status"] == "imported"
    assert result["task_ids"] == ["TASK-001", "TASK-002"]


def test_pending_import_resumes_missing_tasks(juicer, repo):
    write_backlog(repo, task_block("TASK-001") + "\n" + task_block("TASK-002"))
    juicer.import_backlog()
    record_path = juicer.jdir / "imports" / "backlog.json"
    record = json.loads(record_path.read_text())
    record["state"] = "pending"
    record.pop("completed_at", None)
    record_path.write_text(json.dumps(record), encoding="utf-8")
    (juicer.tasks_dir / "TASK-002.json").unlink()

    result = juicer.import_backlog()

    assert result["status"] == "resumed"
    assert sorted(task["id"] for task in juicer.load_tasks()) == [
        "TASK-001", "TASK-002"]
    record = json.loads(record_path.read_text())
    assert record["state"] == "complete"


def test_corrupt_import_record_is_reported(juicer, repo):
    write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    (juicer.jdir / "imports" / "backlog.json").write_text("{", encoding="utf-8")

    with pytest.raises(JuicerError, match="corrupt"):
        juicer.import_backlog()


def test_missing_evidence_is_regenerated_on_repeat(juicer, repo):
    path = write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    record_path = juicer.jdir / "imports" / "backlog.json"
    evidence = juicer.root / json.loads(record_path.read_text())["artifact_ref"]
    evidence.unlink()

    result = juicer.import_backlog()

    assert result["status"] == "unchanged"
    assert evidence.read_bytes() == path.read_bytes()


def test_extra_task_after_import_is_informational(juicer, repo):
    write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    juicer.add_tasks(simple_task_specs("TASK-900"))

    result = juicer.import_backlog()

    assert result["status"] == "unchanged"
    assert result["extra_task_ids"] == ["TASK-900"]


def test_import_record_is_bound_to_source_path(juicer, repo):
    write_backlog(repo, task_block("TASK-001"))
    juicer.import_backlog()
    write_backlog(repo, task_block("TASK-001"), name="backlog/other.md")

    with pytest.raises(JuicerError, match="bound to"):
        juicer.import_backlog(repo / "backlog" / "other.md")


def test_malformed_task_header_is_rejected():
    text = "### Task: TASK-001 Missing brackets\n"

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "malformed task header" in str(exc.value)


def test_unterminated_fence_is_rejected():
    text = "```markdown\n" + task_block("TASK-001")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "unterminated fenced code block" in str(exc.value)


@pytest.mark.parametrize("field", ["Status", "Dependencies"])
def test_required_fields_are_enforced(field):
    text = task_block("TASK-001")
    line = "**%s**: %s\n\n" % (
        field, "Pending" if field == "Status" else "None")
    text = text.replace(line, "")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "missing %s" % field.lower() in str(exc.value)


def test_checked_criterion_is_recorded_as_satisfied():
    specs = parse_backlog(task_block(
        "TASK-001", criteria=("- [x] done", "- [ ] open")))

    assert [c["satisfied"] for c in specs[0]["acceptance_criteria"]] == [
        True, False]


def test_notes_and_effort_are_preserved(juicer, repo):
    text = task_block(
        "TASK-001", extra="**Estimated Effort**: M\n\n**Notes**: Use bcrypt.")
    write_backlog(repo, text)

    juicer.import_backlog()

    task = juicer.load_task("TASK-001")
    assert "Notes: Use bcrypt." in task["description"]
    assert task["origin"]["estimated_effort"] == "M"


def test_windows_scope_separator_cannot_escape():
    text = task_block("TASK-001", extra="**Scope**: ..\\secrets")

    with pytest.raises(ValidationError) as exc:
        parse_backlog(text)
    assert "cannot escape the project" in str(exc.value)


def test_symlinked_done_file_outside_root_is_ignored(juicer, repo, tmp_path):
    outside = tmp_path / "outside-done.md"
    outside.write_text("# Task: [TASK-000] Archived\n", encoding="utf-8")
    done_dir = repo / "backlog" / "done"
    done_dir.mkdir(parents=True)
    (done_dir / "TASK-000.md").symlink_to(outside)
    write_backlog(repo, task_block("TASK-001", dependencies="TASK-000"))

    with pytest.raises(ValidationError, match="unknown task TASK-000"):
        juicer.import_backlog()


def test_non_utf8_archived_file_is_ignored(juicer, repo):
    done = repo / "backlog" / "done"
    done.mkdir(parents=True)
    (done / "BROKEN.md").write_bytes(b"\xff\xfe")
    write_backlog(repo, task_block("TASK-001"))

    result = juicer.import_backlog()

    assert result["task_ids"] == ["TASK-001"]


def test_gitignore_is_merged_on_existing_project(juicer):
    gitignore = juicer.jdir / ".gitignore"
    gitignore.write_text("worktrees/\n", encoding="utf-8")

    juicer.init()

    assert "imports/" in gitignore.read_text(encoding="utf-8").splitlines()


def test_missing_backlog_file_is_reported(juicer, repo):
    with pytest.raises(JuicerError, match="backlog file not found"):
        juicer.import_backlog()


def test_cli_import_backlog(repo):
    assert run_cli(["init"], repo).returncode == 0
    assert run_cli([
        "mission", "--title", "M", "--objective", "O",
        "--criterion", "c1 passes",
    ], repo).returncode == 0
    write_backlog(repo, task_block("TASK-001"))

    proc = run_cli(["import-backlog", "--file", "backlog/backlog.md"], repo)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["status"] == "imported"
    assert data["task_ids"] == ["TASK-001"]

    again = run_cli(["import-backlog"], repo)
    assert again.returncode == 0, again.stderr
    assert json.loads(again.stdout)["status"] == "unchanged"
