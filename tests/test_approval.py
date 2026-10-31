"""Human approval records linked to commit/tree (plan §7 / TASK-006).

Approval is a separate, explicit gate:
- never anonymous: an approver identifier is mandatory;
- never unlinked: valid only for the recorded commit/tree (a new commit
  invalidates it);
- never inferred: `--approve` alone without a recorded approval is refused;
- never a substitute for technical gates: it cannot turn FAIL into PASS.
"""

from __future__ import annotations

import json

import pytest

from juicer import gitops
from juicer.errors import ApprovalError, GateBlockedError
from conftest import fake_ok_executor, simple_task_specs


def _completed(juicer, approval=None, files=None, checks=None):
    spec = simple_task_specs("TASK-001")[0]
    if approval is not None:
        spec["approval_policy"] = approval
    if checks is not None:
        spec["checks"] = checks
    juicer.add_tasks([spec])
    juicer._executor = fake_ok_executor(write_files=files or {"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok, out.detail
    return juicer.load_task("TASK-001")


def _commit_tree(juicer):
    result = juicer.load_task("TASK-001")["result"]
    return result["commit"], gitops.tree_hash(juicer.root, result["commit"])


def _approval_file(juicer, task_id="TASK-001"):
    return juicer.jdir / "approvals" / task_id / "approval.json"


# ---------- record structure ----------

def test_approval_record_contains_required_fields(juicer):
    _completed(juicer, approval={"human_approval_required": True,
                                 "required_gates": ["verification"]})
    commit, tree_hash = _commit_tree(juicer)
    out = juicer.approve("TASK-001", approver="alice",
                         note="reviewed with the release checklist")
    doc = json.loads(_approval_file(juicer).read_text(encoding="utf-8"))
    assert doc["type"] == "approval"
    assert doc["schema_version"] == 1
    assert doc["approver"] == "alice"
    assert doc["task_id"] == "TASK-001"
    assert doc["commit"] == commit
    assert doc["tree_hash"] == tree_hash
    assert doc["approved_at"]
    assert doc["note"] == "reviewed with the release checklist"
    assert "required_by" in doc and doc["required_by"]
    assert out["approver"] == "alice"
    # auditable in the event log too
    events = [e for e in juicer.events()
              if e["type"] == "human_approval_recorded"]
    assert events and events[-1]["data"]["approver"] == "alice"


def test_approval_is_stored_outside_evidence_and_scope(juicer):
    _completed(juicer)
    juicer.approve("TASK-001", approver="alice")
    assert _approval_file(juicer).exists()
    assert not (juicer.evidence_dir / "TASK-001" / "approval.json").exists()


# ---------- no anonymous approvals ----------

@pytest.mark.parametrize("approver", ["", "   ", "anonymous", "ANONYMOUS",
                                      "unknown", None, "anonymous user",
                                      "anon", "​"])
def test_approver_cannot_be_anonymous(juicer, approver):
    _completed(juicer)
    with pytest.raises(ApprovalError):
        juicer.approve("TASK-001", approver=approver)
    assert not _approval_file(juicer).exists()


def test_approve_requires_an_existing_commit(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))  # never run: no commit
    with pytest.raises(GateBlockedError) as exc:
        juicer.approve("TASK-001", approver="alice")
    assert exc.value.gate_status == "BLOCKED"
    assert not _approval_file(juicer).exists()


# ---------- notes must not carry secrets ----------

@pytest.mark.parametrize("note", [
    "password=hunter2",
    "api_key: sk-live-1234567890abcdef",
    "token=ghp_abcdefghijklmnopqrstuv",
    "-----BEGIN RSA PRIVATE KEY-----\nMIIE...",
])
def test_approval_note_rejects_secrets(juicer, note):
    _completed(juicer)
    with pytest.raises(ApprovalError) as exc:
        juicer.approve("TASK-001", approver="alice", note=note)
    assert "secret" in str(exc.value).lower()
    assert not _approval_file(juicer).exists()


def test_approval_reason_rejects_secrets(juicer):
    _completed(juicer)
    with pytest.raises(ApprovalError):
        juicer.approve("TASK-001", approver="alice",
                       reason="client_secret=abc123abc123abc123")


# ---------- merge enforcement ----------

def test_high_risk_policy_requires_approval_before_merge(juicer):
    _completed(juicer, approval={"human_approval_required": False,
                                 "risk_level": "high",
                                 "required_gates": ["verification"]})
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "human approval" in str(exc.value)
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_approve_flag_alone_is_never_enough(juicer):
    """`--approve` without a recorded, commit-linked approval is refused."""
    _completed(juicer, approval={"human_approval_required": True,
                                 "required_gates": ["verification"]})
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert "juicer approve" in str(exc.value)  # tells the user how to record
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_approve_flag_alone_refused_even_when_approval_not_required(juicer):
    _completed(juicer)  # default policy: approval not required
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert exc.value.gate_status == "BLOCKED"
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_recorded_approval_allows_merge_and_is_audited(juicer):
    _completed(juicer, approval={"human_approval_required": True,
                                 "required_gates": ["verification"]})
    commit, _ = _commit_tree(juicer)
    juicer.approve("TASK-001", approver="alice", note="checked the diff")
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["approved"] is True
    assert integration["approval"]["approver"] == "alice"
    assert integration["approval"]["commit"] == commit
    task = juicer.load_task("TASK-001")
    assert task["status"] == "done"
    # the integration record keeps the audit trail of who approved what
    doc = json.loads((juicer.jdir / "integration-TASK-001.json")
                     .read_text(encoding="utf-8"))
    assert doc["approval"]["approver"] == "alice"


def test_new_commit_invalidates_previous_approval(juicer):
    _completed(juicer, approval={"human_approval_required": True,
                                 "required_gates": ["verification"]})
    juicer.approve("TASK-001", approver="alice")
    # equivalent to the task producing a new commit: the stored record still
    # points at the previous commit/tree and must not be reusable
    path = _approval_file(juicer)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["commit"] = "previous_commit"
    doc["tree_hash"] = "previous_tree"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert exc.value.gate_status == "NOT RUN"
    assert "invalidates" in str(exc.value)
    assert juicer.load_task("TASK-001")["status"] == "completed"
    # recovery: re-record the approval for the current commit
    juicer.approve("TASK-001", approver="alice")
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["approved"] is True


def test_approval_gate_declared_in_required_gates_needs_record(juicer):
    _completed(juicer, approval={"human_approval_required": False,
                                 "required_gates": ["verification", "approval"]})
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "approval" in str(exc.value).lower()
    assert juicer.load_task("TASK-001")["status"] == "completed"
    juicer.approve("TASK-001", approver="alice")
    # record exists; the explicit merge intent is still required
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["approved"] is True


def test_approval_does_not_bypass_technical_gate_fail(juicer):
    """A recorded approval never changes a technical gate result (D4)."""
    _completed(
        juicer,
        approval={"human_approval_required": True,
                  "required_gates": ["verification"]},
        checks=[{"id": "failing", "required": True,
                 "command": ["python3", "-c", "raise SystemExit(1)"]}],
    )
    juicer.approve("TASK-001", approver="alice")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert exc.value.gate_status == "FAIL"
    task = juicer.load_task("TASK-001")
    # CR-2: FAIL moves the task to blocked; the approval did not rescue it
    assert task["status"] == "blocked"
    assert "failing" in task["blocked_reason"] or "verification" in task["blocked_reason"]
    # the merge never happened: the feature is not on the target branch
    assert not (juicer.root / "feat.py").exists()
    events = [e["type"] for e in juicer.events()]
    assert "integration_gate_failed" in events


def test_approval_gate_evaluated_after_technical_gates(juicer):
    """Approval comes last in the canonical order; a technical FAIL blocks
    before any approval evaluation result is acted upon."""
    from juicer.orchestrator import Juicer
    order = Juicer.CANONICAL_GATE_ORDER
    assert order.index("approval") == len(order) - 1
    assert order.index("verification") < order.index("approval")


# ---------- read path: tampered records fail closed ----------

def _approval_required_policy():
    return {"human_approval_required": True,
            "required_gates": ["verification"]}


def test_malformed_approval_record_is_blocked(juicer):
    _completed(juicer, approval=_approval_required_policy())
    path = _approval_file(juicer)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert exc.value.gate_status == "BLOCKED"
    assert juicer.load_task("TASK-001")["status"] == "completed"


def test_approval_record_bound_to_another_task_is_blocked(juicer):
    _completed(juicer, approval=_approval_required_policy())
    juicer.approve("TASK-001", approver="alice")
    path = _approval_file(juicer)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["task_id"] = "TASK-999"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert exc.value.gate_status == "BLOCKED"


def test_hand_edited_anonymous_approver_is_blocked_on_read(juicer):
    _completed(juicer, approval=_approval_required_policy())
    juicer.approve("TASK-001", approver="alice")
    path = _approval_file(juicer)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["approver"] = "anonymous"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001", approve=True)
    assert exc.value.gate_status == "BLOCKED"


def test_approval_summary_and_required_flag_are_audited(juicer):
    _completed(juicer, approval=_approval_required_policy())
    juicer.approve("TASK-001", approver="alice", reason="high risk change")
    integration = juicer.integrate("TASK-001", approve=True)
    assert integration["approval_required"] is True
    # required_by reflects the triggers at merge time, not a stale snapshot
    assert "policy:human_approval_required" in integration["approval"]["required_by"]
