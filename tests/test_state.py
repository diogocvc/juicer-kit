"""State persistence: CRUD, restart resume, revision fence, events."""

import json

import pytest

from juicer.errors import StaleRevisionError
from juicer.model import new_mission, new_task, validate_mission, validate_task
from juicer.state import (
    append_event, atomic_write_text, fenced_update, read_events, read_json,
    write_json,
)


def test_mission_crud_roundtrip(juicer):
    doc = juicer.mission()
    assert doc["status"] == "ready"
    assert doc["title"] == "Demo mission"
    # read after "restart": a brand-new instance sees the same state
    fresh = type(juicer)(juicer.root)
    fresh.init()
    assert fresh.mission()["id"] == doc["id"]
    assert fresh.mission()["revision"] == doc["revision"]


def test_task_crud_and_revision_monotonic(juicer):
    juicer.add_tasks([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [], "depends_on": [],
    }])
    t1 = juicer.load_task("TASK-001")
    assert t1["status"] == "ready"
    assert t1["revision"] == 0
    updated = juicer._update_task("TASK-001", lambda t: t.update(status="in_progress"))
    assert updated["status"] == "in_progress"
    assert updated["revision"] == 1
    assert juicer.load_task("TASK-001")["revision"] == 1


def test_resume_after_restart_recovers_interrupted_tasks(juicer):
    juicer.add_tasks([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [], "depends_on": [],
    }])
    juicer._update_task("TASK-001", lambda t: t.update(status="in_progress"))
    # simulate process death + restart
    fresh = type(juicer)(juicer.root)
    fresh.init()
    report = fresh.resume()
    assert report["recovered"] == ["TASK-001"]
    assert fresh.load_task("TASK-001")["status"] == "failed"
    # failed -> ready is an explicit, audited retry
    fresh.retry_task("TASK-001")
    assert fresh.load_task("TASK-001")["status"] == "ready"


def test_stale_write_is_rejected(tmp_path):
    path = tmp_path / "rec.json"
    write_json(path, {"revision": 3, "value": "a"})

    def mut(cur):
        cur["value"] = "b"

    with pytest.raises(StaleRevisionError):
        fenced_update(path, mut, expect_revision=2)


def test_fenced_update_bumps_revision(tmp_path):
    path = tmp_path / "rec.json"
    write_json(path, {"revision": 3, "value": "a"})

    def mut(cur):
        cur["value"] = "b"

    out = fenced_update(path, mut, expect_revision=3)
    assert out["revision"] == 4
    assert read_json(path)["value"] == "b"


def test_events_are_append_only_trail(juicer):
    juicer.add_tasks([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [], "depends_on": [],
    }])
    events = juicer.events()
    types = [e["type"] for e in events]
    assert "init" in types
    assert "mission_set" in types
    assert "task_added" in types
    raw = juicer.events_path.read_text(encoding="utf-8").splitlines()
    assert all(json.loads(line)["schema_version"] == 1 for line in raw if line.strip())


def test_atomic_write_no_partial_file(tmp_path):
    target = tmp_path / "x.json"
    atomic_write_text(target, '{"a": 1}\n')
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    leftovers = [p for p in tmp_path.iterdir() if p.name != "x.json"]
    assert leftovers == []


def test_validate_task_rejects_bad_records():
    with pytest.raises(Exception):
        validate_task({"schema_version": 1, "id": "bad id", "mission_id": "M-1",
                       "title": "t", "description": "d", "status": "nope",
                       "depends_on": [], "acceptance_criteria": [], "scope": {},
                       "approval_policy": {}, "revision": 0,
                       "created_at": "x", "updated_at": "x"})
    ok = new_task("TASK-001", "MISSION-001", "t", "d")
    validate_task(ok)
    m = new_mission("MISSION-001", "t", "o")
    validate_mission(m)
