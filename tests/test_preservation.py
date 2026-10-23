"""Preservation: approved docs, pre-existing changes, overwrite protection."""

import pytest

from juicer import gitops
from juicer.errors import GateBlockedError, JuicerError
from conftest import fake_ok_executor, simple_task_specs


def test_mission_not_overwritten_silently(juicer):
    with pytest.raises(JuicerError) as exc:
        juicer.set_mission(title="Other", objective="other objective")
    assert "force" in str(exc.value)
    # explicit force works and is auditable via revision/event trail
    doc = juicer.set_mission(title="Other", objective="other objective", force=True)
    assert doc["title"] == "Other"


def test_integration_refuses_dirty_working_tree(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"a.txt": "x\n"})
    juicer.run_task("TASK-001")
    # pre-existing uncommitted change by the user
    (juicer.root / "user_work.py").write_text("precious = True\n", encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "uncommitted changes" in str(exc.value)
    # user's file is untouched and the merge did not happen
    assert (juicer.root / "user_work.py").read_text(encoding="utf-8") == "precious = True\n"
    assert gitops.head_commit(juicer.root) == gitops.head_commit(juicer.root)
    assert not (juicer.root / "a.txt").exists()
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_merge_conflict_is_blocking_not_overwriting(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"app.py": "VALUE = 2\n"})
    juicer.run_task("TASK-001")
    # concurrent change on main after the task branched
    (juicer.root / "app.py").write_text("VALUE = 999\n", encoding="utf-8")
    gitops.git(["add", "-A"], juicer.root)
    gitops.git(["commit", "-m", "concurrent change"], juicer.root)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "conflict" in str(exc.value).lower()
    # concurrent version preserved
    assert (juicer.root / "app.py").read_text(encoding="utf-8") == "VALUE = 999\n"
    assert juicer.load_task("TASK-001")["status"] == "blocked"
    # branch preserved for inspection
    branches = gitops.git(["branch", "--list", "juicer/TASK-001"], juicer.root).stdout
    assert "juicer/TASK-001" in branches


def test_scope_guard_blocks_out_of_scope_writes(juicer):
    juicer.add_tasks([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [],
        "scope": {"paths": ["docs/**"], "constraints": []},
    }])
    juicer._executor = fake_ok_executor(write_files={"secrets.env": "TOKEN=1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    # the out-of-scope file never reached the main tree
    assert not (juicer.root / "secrets.env").exists()


def test_init_does_not_clobber_existing_config(juicer):
    cfg_path = juicer.config_path
    cfg_path.write_text('{"schema_version": 1, "custom": true}\n', encoding="utf-8")
    juicer.init()  # no force
    import json
    assert json.loads(cfg_path.read_text(encoding="utf-8")).get("custom") is True
