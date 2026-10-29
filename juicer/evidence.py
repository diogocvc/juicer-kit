"""Structured evidence artifacts for review and security gates.

Artifacts are JSON files stored under ``.juicer/evidence/<task_id>/`` and are
the only valid evidence for the ``review`` and ``security`` gates. Agent
prose is never evidence: the core validates structure, commit/tree linkage,
verdict and severity of findings.

Artifact schema (review and security share the same envelope):

{
  "schema_version": 1,
  "type": "review" | "security",
  "task_id": "TASK-001",
  "execution_id": "RUN-abc123",
  "commit": "abc123def456",
  "tree_hash": "def456ghi789",
  "agent": "@reviewer",           # or "@security"
  "scope": ["src/auth.py", ...],
  "findings": [
    {"severity": "critical|high|medium|low", "description": "...", "file": "...", "line": 42}
  ],
  "verdict": "PASS" | "FAIL",
  "recorded_at": "2026-10-26T10:00:00Z",
  "artifact_ref": ".juicer/evidence/TASK-001/review-abc123.json"
}

Rules:
- Missing or malformed artifact -> gate BLOCKED.
- Any finding with severity "critical" forces verdict FAIL -> gate FAIL.
- Artifact linked to a different commit/tree -> gate NOT RUN.
- A PASS never overwrites a recorded FAIL unless explicitly forced (M-4).
- Findings are validated (severity/description/line) before an artifact is
  written; invalid evidence is rejected instead of evaluated.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errors import JuicerError
from .state import atomic_write_text, ensure_dir, utc_now


REVIEW_DIR_NAME = "reviews"
SECURITY_DIR_NAME = "security"

REQUIRED_FIELDS = (
    "schema_version",
    "type",
    "task_id",
    "execution_id",
    "commit",
    "tree_hash",
    "agent",
    "scope",
    "findings",
    "verdict",
    "recorded_at",
)

VALID_TYPES = ("review", "security")
VALID_VERDICTS = ("PASS", "FAIL")
VALID_SEVERITIES = ("critical", "high", "medium", "low")


class EvidenceError(JuicerError):
    """Raised when an evidence artifact is missing, malformed or invalid."""


def _evidence_dir(root: Path) -> Path:
    return root / ".juicer" / "evidence"


def _task_evidence_dir(root: Path, task_id: str) -> Path:
    return _evidence_dir(root) / task_id


def _artifact_path(root: Path, task_id: str, kind: str, commit: str) -> Path:
    safe_commit = commit.replace("/", "_").replace("\\", "_")
    return _task_evidence_dir(root, task_id) / ("%s-%s.json" % (kind, safe_commit))


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _validate_envelope(doc: Any, kind: str) -> List[str]:
    """Return a list of validation errors (empty when valid)."""
    errors: List[str] = []
    if not isinstance(doc, dict):
        errors.append("evidence artifact must be a JSON object")
        return errors
    if doc.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if doc.get("type") != kind:
        errors.append("artifact type must be %r" % kind)
    for field in REQUIRED_FIELDS:
        if field not in doc:
            errors.append("missing required field: %s" % field)
    if not isinstance(doc.get("task_id"), str) or not doc["task_id"]:
        errors.append("task_id must be a non-empty string")
    if not isinstance(doc.get("execution_id"), str) or not doc["execution_id"]:
        errors.append("execution_id must be a non-empty string")
    if not isinstance(doc.get("commit"), str) or not doc["commit"]:
        errors.append("commit must be a non-empty string")
    if not isinstance(doc.get("tree_hash"), str) or not doc["tree_hash"]:
        errors.append("tree_hash must be a non-empty string")
    agent = doc.get("agent")
    if kind == "review" and agent != "@reviewer":
        errors.append("review artifact agent must be @reviewer")
    if kind == "security" and agent != "@security":
        errors.append("security artifact agent must be @security")
    if not isinstance(doc.get("scope"), list):
        errors.append("scope must be a list")
    findings = doc.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for i, f in enumerate(findings):
            if not isinstance(f, dict):
                errors.append("finding %d must be an object" % i)
                continue
            sev = f.get("severity")
            if sev not in VALID_SEVERITIES:
                errors.append("finding %d has invalid severity: %s" % (i, sev))
    verdict = doc.get("verdict")
    if verdict not in VALID_VERDICTS:
        errors.append("verdict must be PASS or FAIL")
    if not isinstance(doc.get("recorded_at"), str) or not doc["recorded_at"]:
        errors.append("recorded_at must be a non-empty string")
    return errors


def _validate_linkage(doc: Dict[str, Any], commit: str, tree_hash: str) -> List[str]:
    errors: List[str] = []
    if doc.get("commit") != commit:
        errors.append("artifact commit %s does not match integration commit %s"
                      % (doc.get("commit"), commit))
    if doc.get("tree_hash") != tree_hash:
        errors.append("artifact tree_hash %s does not match integration tree %s"
                      % (doc.get("tree_hash"), tree_hash))
    return errors


def _critical_finding(findings: List[dict]) -> bool:
    return any(isinstance(f, dict) and f.get("severity") == "critical" for f in findings)


def validate_findings(findings) -> List[dict]:
    """Validate and normalize structured findings (fail fast, never guess).

    Severity must be one of critical/high/medium/low and every finding needs a
    description; ``line`` is normalized to int when present. Invalid findings
    are rejected before an artifact is written so gates never evaluate
    malformed evidence.
    """
    if findings is None:
        return []
    if not isinstance(findings, list):
        raise EvidenceError("findings must be a list")
    normalized = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise EvidenceError("each finding must be an object")
        severity = str(finding.get("severity") or "").lower()
        if severity not in VALID_SEVERITIES:
            raise EvidenceError(
                "finding severity must be one of %s (got %r)"
                % (", ".join(VALID_SEVERITIES), finding.get("severity")))
        description = str(finding.get("description") or "").strip()
        if not description:
            raise EvidenceError("finding description is required")
        item = dict(finding)
        item["severity"] = severity
        item["description"] = description
        if item.get("line") is not None:
            raw_line = item["line"]
            if isinstance(raw_line, bool) or (
                    isinstance(raw_line, float) and not raw_line.is_integer()):
                raise EvidenceError("finding line must be an integer")
            try:
                item["line"] = int(raw_line)
            except (TypeError, ValueError):
                raise EvidenceError("finding line must be an integer")
        normalized.append(item)
    return normalized


def evaluate_review_artifact(doc: Optional[dict], commit: str,
                             tree_hash: str) -> Tuple[str, List[str]]:
    """Evaluate a review artifact into a gate status.

    Returns (status, details) where status is PASS, FAIL, BLOCKED or NOT RUN.

    Semantics (M-2, aligned with TASK-005):
    - missing artifact -> BLOCKED (review never happened; blocks merge)
    - malformed artifact -> BLOCKED (cannot be trusted; blocks merge)
    - linked to a different commit/tree -> NOT RUN (evidence exists but is
      stale for this commit; blocks merge until a fresh review is recorded)
    """
    details: List[str] = []
    if doc is None:
        return "BLOCKED", ["review artifact not found for commit %s" % commit]
    errors = _validate_envelope(doc, "review")
    if errors:
        return "BLOCKED", ["malformed review artifact: %s" % "; ".join(errors)]
    link_errors = _validate_linkage(doc, commit, tree_hash)
    if link_errors:
        return "NOT RUN", link_errors
    verdict = doc.get("verdict")
    findings = doc.get("findings") or []
    if _critical_finding(findings):
        return "FAIL", ["review artifact has critical finding; verdict forced to FAIL"]
    if verdict == "FAIL":
        return "FAIL", ["review artifact verdict is FAIL"]
    details.append("review artifact validated; verdict=%s" % verdict)
    if findings:
        details.append("%d finding(s) recorded" % len(findings))
    return "PASS", details


def evaluate_security_artifact(doc: Optional[dict], commit: str,
                               tree_hash: str) -> Tuple[str, List[str]]:
    """Evaluate a security artifact into a gate status.

    Returns (status, details) where status is PASS, FAIL, BLOCKED or NOT RUN.

    Semantics (M-2, aligned with TASK-005): missing/malformed -> BLOCKED;
    stale linkage (different commit/tree) -> NOT RUN.
    """
    details: List[str] = []
    if doc is None:
        return "BLOCKED", ["security artifact not found for commit %s" % commit]
    errors = _validate_envelope(doc, "security")
    if errors:
        return "BLOCKED", ["malformed security artifact: %s" % "; ".join(errors)]
    link_errors = _validate_linkage(doc, commit, tree_hash)
    if link_errors:
        return "NOT RUN", link_errors
    verdict = doc.get("verdict")
    findings = doc.get("findings") or []
    if _critical_finding(findings):
        return "FAIL", ["security artifact has critical finding; verdict forced to FAIL"]
    if verdict == "FAIL":
        return "FAIL", ["security artifact verdict is FAIL"]
    details.append("security artifact validated; verdict=%s" % verdict)
    if findings:
        details.append("%d finding(s) recorded" % len(findings))
    return "PASS", details


def _guard_fail_overwrite(root: Path, task_id: str, kind: str, commit: str,
                          new_verdict: str, force: bool) -> None:
    """M-4: refuse to silently overwrite a FAIL verdict with PASS.

    A recorded FAIL represents real review/audit work with findings. Turning
    it into a PASS requires an explicit ``force`` so the change is deliberate
    and auditable. FAIL->FAIL and PASS->PASS re-records are normal refreshes.
    """
    if new_verdict != "PASS" or force:
        return
    existing = _load_json_file(_artifact_path(root, task_id, kind, commit))
    if existing is None:
        return
    # FAIL either as recorded verdict or derived from a critical finding
    # (evaluate_* forces FAIL for critical findings regardless of verdict).
    recorded_fail = existing.get("verdict") == "FAIL"
    derived_fail = any(
        str(f.get("severity", "")).lower() == "critical"
        for f in (existing.get("findings") or []))
    if recorded_fail or derived_fail:
        raise EvidenceError(
            "refusing to overwrite %s FAIL verdict for commit %s with PASS; "
            "re-record as FAIL or pass force=True to override explicitly"
            % (kind, commit))


def record_review(root: Path, task_id: str, execution_id: str, commit: str,
                  tree_hash: str, scope: List[str], findings: List[dict],
                  verdict: str, agent: str = "@reviewer",
                  force: bool = False) -> Path:
    """Write a structured review evidence artifact and return its path."""
    if verdict not in VALID_VERDICTS:
        raise EvidenceError("verdict must be PASS or FAIL")
    if agent != "@reviewer":
        raise EvidenceError("review artifact agent must be @reviewer")
    findings = validate_findings(findings)
    _guard_fail_overwrite(root, task_id, "review", commit, verdict, force)
    doc = {
        "schema_version": 1,
        "type": "review",
        "task_id": task_id,
        "execution_id": execution_id,
        "commit": commit,
        "tree_hash": tree_hash,
        "agent": agent,
        "scope": list(scope or []),
        "findings": findings,
        "verdict": verdict,
        "recorded_at": utc_now(),
    }
    doc["artifact_ref"] = str(_artifact_path(root, task_id, "review", commit))
    path = _artifact_path(root, task_id, "review", commit)
    _atomic_write_json(path, doc)
    return path


def record_security(root: Path, task_id: str, execution_id: str, commit: str,
                    tree_hash: str, scope: List[str], findings: List[dict],
                    verdict: str, agent: str = "@security",
                    force: bool = False) -> Path:
    """Write a structured security evidence artifact and return its path."""
    if verdict not in VALID_VERDICTS:
        raise EvidenceError("verdict must be PASS or FAIL")
    if agent != "@security":
        raise EvidenceError("security artifact agent must be @security")
    findings = validate_findings(findings)
    _guard_fail_overwrite(root, task_id, "security", commit, verdict, force)
    doc = {
        "schema_version": 1,
        "type": "security",
        "task_id": task_id,
        "execution_id": execution_id,
        "commit": commit,
        "tree_hash": tree_hash,
        "agent": agent,
        "scope": list(scope or []),
        "findings": findings,
        "verdict": verdict,
        "recorded_at": utc_now(),
    }
    doc["artifact_ref"] = str(_artifact_path(root, task_id, "security", commit))
    path = _artifact_path(root, task_id, "security", commit)
    _atomic_write_json(path, doc)
    return path


def load_review(root: Path, task_id: str, commit: str) -> Optional[dict]:
    """Load the review artifact for a task/commit, if any."""
    return _load_json_file(_artifact_path(root, task_id, "review", commit))


def load_security(root: Path, task_id: str, commit: str) -> Optional[dict]:
    """Load the security artifact for a task/commit, if any."""
    return _load_json_file(_artifact_path(root, task_id, "security", commit))
