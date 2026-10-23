"""Decomposition and dependency graph behaviour."""

import pytest

from juicer.errors import ValidationError
from juicer.graph import build_adjacency, detect_cycle, eligible_tasks, topo_waves


def spec(tid, deps=None):
    return {"id": tid, "title": tid, "description": "d", "depends_on": deps or [],
            "acceptance_criteria": [], "scope": {"paths": [], "constraints": []},
            "approval_policy": {"human_approval_required": False, "required_gates": []},
            "agent": "coder", "checks": []}


def test_decompose_persists_tasks_with_stable_ids(juicer):
    made = juicer.add_tasks([spec("TASK-001"), spec("TASK-002", ["TASK-001"])])
    assert [t["id"] for t in made] == ["TASK-001", "TASK-002"]
    assert juicer.load_task("TASK-002")["depends_on"] == ["TASK-001"]


def test_decompose_rejects_duplicate_ids(juicer):
    juicer.add_tasks([spec("TASK-001")])
    with pytest.raises(ValidationError):
        juicer.add_tasks([spec("TASK-001")])


def test_decompose_rejects_unknown_dependency(juicer):
    with pytest.raises(ValidationError):
        juicer.add_tasks([spec("TASK-001", ["TASK-999"])])


def test_decompose_rejects_cycles(juicer):
    with pytest.raises(ValidationError) as exc:
        juicer.add_tasks([spec("TASK-001", ["TASK-002"]), spec("TASK-002", ["TASK-001"])])
    assert "cycle" in str(exc.value).lower()


def test_detect_cycle_direct_and_indirect():
    assert detect_cycle([spec("A", ["B"]), spec("B", ["A"])]) is not None
    assert detect_cycle([spec("A", ["C"]), spec("B", ["A"]), spec("C", ["B"])]) is not None
    assert detect_cycle([spec("A"), spec("B", ["A"]), spec("C", ["B"])]) is None


def test_eligibility_requires_done_dependencies():
    tasks = [
        dict(spec("TASK-001"), status="ready"),
        dict(spec("TASK-002", ["TASK-001"]), status="ready"),
        dict(spec("TASK-003"), status="ready"),
    ]
    ids = [t["id"] for t in eligible_tasks(tasks)]
    assert ids == ["TASK-001", "TASK-003"]
    tasks[0]["status"] = "done"
    ids = [t["id"] for t in eligible_tasks(tasks)]
    assert ids == ["TASK-002", "TASK-003"]


def test_eligibility_excludes_non_ready():
    tasks = [dict(spec("TASK-001"), status="failed"),
             dict(spec("TASK-002"), status="in_progress")]
    assert eligible_tasks(tasks) == []


def test_topo_waves_order():
    tasks = [spec("TASK-001"), spec("TASK-002", ["TASK-001"]),
             spec("TASK-003", ["TASK-001"]), spec("TASK-004", ["TASK-002", "TASK-003"])]
    waves = topo_waves(tasks)
    assert waves[0] == ["TASK-001"]
    assert sorted(waves[1]) == ["TASK-002", "TASK-003"]
    assert waves[2] == ["TASK-004"]


def test_build_adjacency_maps_dependents():
    deps, dependents = build_adjacency([spec("TASK-001"), spec("TASK-002", ["TASK-001"])])
    assert dependents["TASK-001"] == {"TASK-002"}
    assert deps["TASK-002"] == {"TASK-001"}
