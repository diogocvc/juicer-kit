"""Mission intake: gap detection blocks work until human resolution."""

import pytest

from juicer.errors import GateBlockedError, JuicerError
from conftest import simple_task_specs


def test_gap_blocks_until_resolved(juicer):
    # replace mission with one that has gaps
    juicer.set_mission(title="With gaps", objective="Ship it",
                       gaps=[{"id": "GAP-001", "question": "Which DB?", "resolution": None}],
                       force=True)
    assert juicer.mission()["status"] == "waiting_human"
    with pytest.raises(GateBlockedError) as exc:
        juicer.add_tasks(simple_task_specs("TASK-001"))
    assert "GAP-001" in str(exc.value)
    juicer.resolve_gap("GAP-001", "SQLite, decided by user")
    assert juicer.mission()["status"] == "ready"
    made = juicer.add_tasks(simple_task_specs("TASK-001"))
    assert made[0]["id"] == "TASK-001"


def test_unknown_gap_rejected(juicer):
    with pytest.raises(JuicerError):
        juicer.resolve_gap("GAP-999", "x")


def test_mission_without_gaps_is_ready_immediately(juicer):
    assert juicer.mission()["status"] == "ready"
