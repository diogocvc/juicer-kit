"""Structured evidence artifacts: review and security evidence validation."""

import json
import os

import pytest

from juicer.evidence import (
    record_review, record_security, load_review, load_security,
    evaluate_review_artifact, evaluate_security_artifact, EvidenceError,
)


def _artifact_dict(kind="review", commit="abc123", tree_hash="tree456",
                   verdict="PASS", findings=None, agent=None, **overrides):
    doc = {
        "schema_version": 1,
        "type": kind,
        "task_id": "TASK-001",
        "execution_id": "RUN-001",
        "commit": commit,
        "tree_hash": tree_hash,
        "agent": agent or ("@reviewer" if kind == "review" else "@security"),
        "scope": ["src/a.py"],
        "findings": findings or [],
        "verdict": verdict,
        "recorded_at": "2026-10-26T10:00:00Z",
    }
    doc.update(overrides)
    return doc


class TestRecordAndLoad:
    def test_record_review_writes_valid_artifact(self, tmp_path):
        path = record_review(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"], [{"severity": "medium", "description": "minor"}],
            "PASS", "@reviewer")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["type"] == "review"
        assert data["commit"] == "abc123"
        assert data["tree_hash"] == "tree456"
        assert data["verdict"] == "PASS"
        assert load_review(tmp_path, "TASK-001", "abc123") == data

    def test_record_security_writes_valid_artifact(self, tmp_path):
        path = record_security(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"], [{"severity": "high", "description": "sql injection"}],
            "PASS", "@security")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["type"] == "security"
        assert data["agent"] == "@security"
        assert load_security(tmp_path, "TASK-001", "abc123") == data

    def test_record_review_rejects_wrong_agent(self, tmp_path):
        with pytest.raises(EvidenceError):
            record_review(tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
                          [], [], "PASS", agent="@security")

    def test_record_security_rejects_wrong_agent(self, tmp_path):
        with pytest.raises(EvidenceError):
            record_security(tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
                            [], [], "PASS", agent="@reviewer")

    def test_record_rejects_invalid_verdict(self, tmp_path):
        with pytest.raises(EvidenceError):
            record_review(tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
                          [], [], "MAYBE", "@reviewer")

    def test_record_rejects_non_integral_line(self, tmp_path):
        for line in (3.9, True):
            with pytest.raises(EvidenceError):
                record_review(
                    tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
                    [], [{"severity": "low", "description": "x", "line": line}],
                    "PASS", "@reviewer")


class TestFailVerdictOverwriteProtection:
    """M-4: a PASS artifact must never silently overwrite a FAIL verdict."""

    def test_pass_cannot_overwrite_fail_without_force(self, tmp_path):
        record_review(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"],
            [{"severity": "critical", "description": "hardcoded secret"}],
            "FAIL", "@reviewer")
        with pytest.raises(EvidenceError) as exc:
            record_review(
                tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
                ["src/a.py"], [], "PASS", "@reviewer")
        assert "FAIL" in str(exc.value)
        # the original FAIL verdict is preserved
        doc = load_review(tmp_path, "TASK-001", "abc123")
        assert doc["verdict"] == "FAIL"

    def test_pass_overwrites_fail_with_explicit_force(self, tmp_path):
        record_review(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"],
            [{"severity": "critical", "description": "hardcoded secret"}],
            "FAIL", "@reviewer")
        path = record_review(
            tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
            ["src/a.py"], [], "PASS", "@reviewer", force=True)
        assert json.loads(path.read_text(encoding="utf-8"))["verdict"] == "PASS"

    def test_pass_cannot_overwrite_derived_fail_from_critical_finding(self, tmp_path):
        """Re-review hardening: an artifact recorded as PASS but carrying a
        critical finding evaluates to gate-FAIL, so re-recording a clean PASS
        over it must also require force."""
        record_review(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"],
            [{"severity": "critical", "description": "hardcoded secret"}],
            "PASS", "@reviewer")
        # sanity: it really evaluates to FAIL (critical forces FAIL)
        from juicer.evidence import evaluate_review_artifact
        status, _ = evaluate_review_artifact(
            load_review(tmp_path, "TASK-001", "abc123"), "abc123", "tree456")
        assert status == "FAIL"
        # so the clean PASS re-record is refused without force
        with pytest.raises(EvidenceError):
            record_review(
                tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
                ["src/a.py"], [], "PASS", "@reviewer")
        record_review(
            tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
            ["src/a.py"], [], "PASS", "@reviewer", force=True)

    def test_security_pass_cannot_overwrite_fail_without_force(self, tmp_path):
        record_security(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"],
            [{"severity": "high", "description": "sql injection"}],
            "FAIL", "@security")
        with pytest.raises(EvidenceError):
            record_security(
                tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
                ["src/a.py"], [], "PASS", "@security")
        assert load_security(tmp_path, "TASK-001", "abc123")["verdict"] == "FAIL"

    def test_fail_verdict_can_be_rerecorded(self, tmp_path):
        # Recording another FAIL (or re-review with findings) stays allowed:
        # the protection targets silent PASS overwrites only.
        record_review(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"], [], "FAIL", "@reviewer")
        path = record_review(
            tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
            ["src/a.py"],
            [{"severity": "medium", "description": "still broken"}],
            "FAIL", "@reviewer")
        assert json.loads(path.read_text(encoding="utf-8"))["verdict"] == "FAIL"

    def test_pass_can_be_rerecorded(self, tmp_path):
        # Re-running a PASS review over an old PASS is a normal refresh.
        record_review(
            tmp_path, "TASK-001", "RUN-001", "abc123", "tree456",
            ["src/a.py"], [], "PASS", "@reviewer")
        path = record_review(
            tmp_path, "TASK-001", "RUN-002", "abc123", "tree456",
            ["src/a.py"], [], "PASS", "@reviewer")
        assert json.loads(path.read_text(encoding="utf-8"))["verdict"] == "PASS"


class TestEvaluateReview:
    def test_missing_artifact_is_blocked(self):
        # M-2: missing artifact means the review never happened -> BLOCKED
        # (NOT RUN is reserved for stale artifacts linked to another commit).
        status, details = evaluate_review_artifact(None, "abc123", "tree456")
        assert status == "BLOCKED"
        assert "not found" in details[0]

    def test_malformed_artifact_is_blocked(self):
        status, details = evaluate_review_artifact({"type": "review"}, "abc123", "tree456")
        assert status == "BLOCKED"
        assert "malformed" in details[0]

    def test_wrong_commit_is_not_run(self):
        doc = _artifact_dict(commit="abc123")
        status, details = evaluate_review_artifact(doc, "xyz999", "tree456")
        assert status == "NOT RUN"
        assert "does not match" in details[0]

    def test_wrong_tree_hash_is_not_run(self):
        doc = _artifact_dict(tree_hash="tree456")
        status, details = evaluate_review_artifact(doc, "abc123", "tree999")
        assert status == "NOT RUN"

    def test_critical_finding_forces_fail(self):
        doc = _artifact_dict(
            verdict="PASS",
            findings=[{"severity": "critical", "description": "bad"}],
        )
        status, details = evaluate_review_artifact(doc, "abc123", "tree456")
        assert status == "FAIL"
        assert "critical" in details[0]

    def test_fail_verdict_is_fail(self):
        doc = _artifact_dict(verdict="FAIL")
        status, _ = evaluate_review_artifact(doc, "abc123", "tree456")
        assert status == "FAIL"

    def test_valid_pass_artifact_is_pass(self):
        doc = _artifact_dict()
        status, details = evaluate_review_artifact(doc, "abc123", "tree456")
        assert status == "PASS"
        assert "validated" in details[0]


class TestEvaluateSecurity:
    def test_missing_artifact_is_blocked(self):
        # M-2: same semantics as review — missing -> BLOCKED.
        status, details = evaluate_security_artifact(None, "abc123", "tree456")
        assert status == "BLOCKED"

    def test_malformed_artifact_is_blocked(self):
        status, details = evaluate_security_artifact(
            {"type": "security"}, "abc123", "tree456")
        assert status == "BLOCKED"

    def test_wrong_agent_is_blocked(self):
        doc = _artifact_dict(kind="security", agent="@reviewer")
        status, _ = evaluate_security_artifact(doc, "abc123", "tree456")
        assert status == "BLOCKED"

    def test_critical_finding_forces_fail(self):
        doc = _artifact_dict(
            kind="security", verdict="PASS",
            findings=[{"severity": "critical", "description": "bad"}],
            agent="@security",
        )
        status, details = evaluate_security_artifact(doc, "abc123", "tree456")
        assert status == "FAIL"
        assert "critical" in details[0]

    def test_valid_pass_artifact_is_pass(self):
        doc = _artifact_dict(kind="security", agent="@security")
        status, _ = evaluate_security_artifact(doc, "abc123", "tree456")
        assert status == "PASS"


class TestArtifactLinkageToCommit:
    """Evidence must be linked to the correct commit/tree; otherwise NOT RUN."""

    def test_review_stale_commit_blocks_integration(self, tmp_path):
        doc = _artifact_dict(commit="old_commit")
        status, _ = evaluate_review_artifact(doc, "new_commit", "tree456")
        assert status == "NOT RUN"

    def test_security_stale_tree_blocks_integration(self, tmp_path):
        doc = _artifact_dict(kind="security", tree_hash="old_tree", agent="@security")
        status, _ = evaluate_security_artifact(doc, "abc123", "new_tree")
        assert status == "NOT RUN"
