"""Acceptance criteria: verification types and evidence-linked evaluation.

A criterion declares *how* it is verified (``check:<id>``, ``review``,
``security`` or ``human``). The core evaluates that evidence at integration and
records the per-criterion outcome so the result is auditable.
"""

from __future__ import annotations

import json

import pytest

from juicer import gitops
from juicer.errors import GateBlockedError, ValidationError
from juicer.model import validate_task
from conftest import fake_ok_executor, simple_task_specs


# ---------- model: verification must be a supported form ----------

def _task_doc(criteria):
    return {
        "schema_version": 1,
        "id": "TASK-001",
        "mission_id": "MISSION-001",
        "title": "t",
        "description": "d",
        "status": "ready",
        "depends_on": [],
        "acceptance_criteria": criteria,
        "scope": {"paths": [], "constraints": []},
        "approval_policy": {"human_approval_required": False,
                            "required_gates": ["verification"]},
        "attempt_count": 0,
        "revision": 0,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.mark.parametrize("verification", [
    "check:py-ok", "check:lint.unit", "review", "security", "human",
])
def test_criterion_accepts_supported_verification_forms(verification):
    validate_task(_task_doc([
        {"id": "AC-1", "description": "works", "verification": verification},
    ]))


@pytest.mark.parametrize("verification", [
    "automated_test", "checks", "check:", "check", "Review", "manual", "",
])
def test_criterion_rejects_unsupported_verification_forms(verification):
    with pytest.raises(ValidationError) as exc:
        validate_task(_task_doc([
            {"id": "AC-1", "description": "works", "verification": verification},
        ]))
    assert "verification" in str(exc.value)


def test_criterion_without_verification_is_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_task(_task_doc([{"id": "AC-1", "description": "works"}]))
    assert "verification" in str(exc.value)


# ---------- integration: evidence-linked evaluation ----------

def _spec(criteria, gates=("verification",), checks=None, human=False):
    spec = simple_task_specs("TASK-001")[0]
    spec["acceptance_criteria"] = criteria
    spec["approval_policy"] = {
        "human_approval_required": human,
        "required_gates": list(gates),
    }
    if checks is not None:
        spec["checks"] = checks
    return spec


def _run(juicer, files=None):
    juicer._executor = fake_ok_executor(write_files=files or {"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok, out.detail
    return out


def _record(juicer, kind, verdict="PASS", findings=None):
    task = juicer.load_task("TASK-001")
    result = task["result"]
    tree = gitops.tree_hash(juicer.root, result["commit"])
    kwargs = dict(task_id="TASK-001", execution_id=result["execution_id"],
                  commit=result["commit"], tree_hash=tree,
                  scope=result["changed_files"], findings=findings or [],
                  verdict=verdict)
    if kind == "review":
        return juicer.record_review(agent="@reviewer", **kwargs)
    return juicer.record_security(agent="@security", **kwargs)


def test_check_criterion_passes_and_is_audited(juicer):
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "checks pass", "verification": "check:py-ok"},
    ])])
    _run(juicer)
    integration = juicer.integrate("TASK-001")
    assert integration["pre_merge_gate"]["status"] == "PASS"
    criteria = integration["acceptance_criteria"]
    assert len(criteria) == 1
    assert criteria[0]["id"] == "AC-1"
    assert criteria[0]["verification"] == "check:py-ok"
    assert criteria[0]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"
    # the integration record on disk keeps the audit trail
    doc = json.loads((juicer.jdir / "integration-TASK-001.json")
                     .read_text(encoding="utf-8"))
    assert doc["acceptance_criteria"][0]["status"] == "PASS"


def test_failed_check_criterion_blocks_and_blocks_the_task(juicer):
    juicer.add_tasks([_spec(
        [{"id": "AC-1", "description": "lint clean", "verification": "check:lint"}],
        checks=[
            {"id": "py-ok", "required": True,
             "command": ["python3", "-c", "print('ok')"]},
            {"id": "lint", "required": False,
             "command": ["python3", "-c", "raise SystemExit(1)"]},
        ],
    )])
    _run(juicer)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "FAIL"
    assert "acceptance criteria" in str(exc.value)
    task = juicer.load_task("TASK-001")
    assert task["status"] == "blocked"  # CR-2: FAIL never traps in completed
    assert "acceptance criteria" in task["blocked_reason"]


def test_missing_check_evidence_is_not_run(juicer):
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "unknown check", "verification": "check:absent"},
    ])])
    _run(juicer)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "NOT RUN"
    # missing evidence is recoverable: the task stays completed
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_stale_check_evidence_is_not_run(juicer):
    juicer.add_tasks([_spec(
        [{"id": "AC-1", "description": "lint clean", "verification": "check:lint"}],
        checks=[
            {"id": "py-ok", "required": True,
             "command": ["python3", "-c", "print('ok')"]},
            {"id": "lint", "required": False,
             "command": ["python3", "-c", "print('ok')"]},
        ],
    )])
    _run(juicer)
    # make the non-required check's result point at another commit
    store = juicer.checks_dir / "TASK-001.results.jsonl"
    rows = [json.loads(line) for line in
            store.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if row["check_id"] == "lint":
            row["commit"] = "0ldc0mm1t"
    store.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                     encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "NOT RUN"
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_corrupt_check_status_fails_closed_as_not_run(juicer):
    """Unknown stored statuses are normalized to NOT RUN (never a crash and
    never a pass), matching gates.evaluate_gate."""
    juicer.add_tasks([_spec(
        [{"id": "AC-1", "description": "lint clean", "verification": "check:lint"}],
        checks=[
            {"id": "py-ok", "required": True,
             "command": ["python3", "-c", "print('ok')"]},
            {"id": "lint", "required": False,
             "command": ["python3", "-c", "print('ok')"]},
        ],
    )])
    _run(juicer)
    store = juicer.checks_dir / "TASK-001.results.jsonl"
    rows = [json.loads(line) for line in
            store.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if row["check_id"] == "lint":
            row["status"] = "WEIRD"
    store.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                     encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "NOT RUN"
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_review_criterion_requires_linked_artifact_then_passes(juicer):
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "reviewed", "verification": "review"},
    ])])
    _run(juicer)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"
    assert juicer.load_task("TASK-001")["status"] == "completed"

    _record(juicer, "review")
    integration = juicer.integrate("TASK-001")
    assert integration["acceptance_criteria"][0]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_review_criterion_fails_on_critical_finding(juicer):
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "reviewed", "verification": "review"},
    ])])
    _run(juicer)
    _record(juicer, "review", findings=[
        {"severity": "critical", "description": "hardcoded secret"},
    ])
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "FAIL"
    assert juicer.load_task("TASK-001")["status"] == "blocked"


def test_security_criterion_requires_linked_artifact_then_passes(juicer):
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "audited", "verification": "security"},
    ])])
    _run(juicer)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"

    _record(juicer, "security")
    integration = juicer.integrate("TASK-001")
    assert integration["acceptance_criteria"][0]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_human_criterion_requires_explicit_approval(juicer):
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "human sign-off", "verification": "human"},
    ])])
    _run(juicer)
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert exc.value.gate_status == "BLOCKED"
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["acceptance_criteria"][0]["status"] == "PASS"
    assert juicer.load_task("TASK-001")["status"] == "done"


def test_criteria_audit_is_stored_even_when_blocked(juicer):
    """The evaluation is recorded in the event log so a blocked attempt can be
    audited (why each criterion did not pass)."""
    juicer.add_tasks([_spec([
        {"id": "AC-1", "description": "checks pass", "verification": "check:py-ok"},
        {"id": "AC-2", "description": "reviewed", "verification": "review"},
    ])])
    _run(juicer)
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")
    events = [e for e in juicer.events() if e["type"] == "criteria_evaluated"]
    assert events, "criteria evaluation must be auditable"
    assert events[-1]["data"]["status"] == "BLOCKED"
    assert {c["id"] for c in events[-1]["data"]["criteria"]} == {"AC-1", "AC-2"}
