"""Human approval records linked to commit/tree (plan §7).

Approval is a separate, explicit gate:

- never anonymous: an approver identifier is mandatory (no defaults);
- never unlinked: valid only for the recorded commit and tree — a new commit
  invalidates the previous approval;
- never inferred: nothing in the technical result (checks, review, security,
  agent text) can produce an approval;
- never a substitute: an approval does not change any technical gate result.

The record is written under ``.juicer/approvals/<task>/approval.json`` (core
state, protected from agents) and mirrored in the event log for audit.
Notes/reasons must not carry secrets.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .errors import ApprovalError
from .state import atomic_write_text, utc_now

APPROVAL_SCHEMA_VERSION = 1

# Identifiers that say nothing about who approved; refused explicitly.
ANONYMOUS_APPROVERS = ("", "anonymous", "unknown", "none", "n/a", "system")
# Same set as prefixes, so "anonymous user" or "anon-bot" are refused too.
ANONYMOUS_PREFIXES = ("anonymous", "unknown", "none", "n/a", "system", "anon")


def _approver_is_valid(approver) -> bool:
    """Shared by write and read paths so a hand-edited record cannot smuggle
    in an anonymous or invisible identity."""
    if not isinstance(approver, str):
        return False
    name = approver.strip()
    if not name or name.lower() in ANONYMOUS_APPROVERS:
        return False
    if name.lower().startswith(ANONYMOUS_PREFIXES):
        return False
    return any(ch.isalnum() for ch in name)

# Credentials must never live in approval notes/reasons (fail fast).
# Heuristic best-effort pattern: it aims to refuse obvious credential shapes,
# not to be a guarantee — treat any rejected note as "put it in a secret store".
_SECRET_RE = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|password\s*[=:]\s*\S+"
    r"|passwd\s*[=:]\s*\S+"
    r"|api[_-]?key\s*[=:]\s*\S+"
    r"|client[_-]?secret\s*[=:]\s*\S+"
    r"|access[_-]?token\s*[=:]\s*\S+"
    r"|token\s*[=:]\s*\S+"
    r"|AKIA[0-9A-Z]{16}"
    r"|sk-[A-Za-z0-9]{16,}"
    r"|ghp_[A-Za-z0-9]{20,})",
    re.IGNORECASE)


def validate_approver(approver) -> str:
    """Return the normalized approver id or raise (never anonymous)."""
    if not isinstance(approver, str):
        raise ApprovalError(
            "approver must be a non-empty identifier (approvals are never "
            "anonymous)")
    name = approver.strip()
    if not _approver_is_valid(name):
        raise ApprovalError(
            "approver %r is not a valid identity; approvals are never "
            "anonymous — pass --approver with a real name" % approver)
    return name


def validate_free_text(field: str, value: Optional[str]) -> str:
    """Validate a note/reason string; refuse anything secret-shaped."""
    text = value or ""
    if not isinstance(text, str):
        raise ApprovalError("%s must be a string" % field)
    if _SECRET_RE.search(text):
        raise ApprovalError(
            "%s looks like it contains a secret (credential pattern); "
            "secrets must never be stored in approval records" % field)
    return text.strip()


def _approvals_dir(root: Path, task_id: str) -> Path:
    return Path(root) / ".juicer" / "approvals" / task_id


def approval_path(root: Path, task_id: str) -> Path:
    """Single record per task: the latest approval (history lives in events)."""
    return _approvals_dir(root, task_id) / "approval.json"


def record_approval(root: Path, task_id: str, approver: str, commit: str,
                    tree_hash: str, required_by: Optional[List[str]] = None,
                    reason: Optional[str] = None,
                    note: Optional[str] = None) -> Path:
    """Write the approval record for *commit*/*tree_hash* and return its path.

    Overwriting with a new approval is allowed (re-approval after a new
    commit); the previous record is replaced atomically.
    """
    approver = validate_approver(approver)
    if not isinstance(commit, str) or not commit:
        raise ApprovalError("approval needs the commit it applies to")
    if not isinstance(tree_hash, str) or not tree_hash:
        raise ApprovalError("approval needs the tree hash it applies to")
    reason = validate_free_text("reason", reason)
    note = validate_free_text("note", note)
    doc = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "type": "approval",
        "task_id": task_id,
        "approver": approver,
        "commit": commit,
        "tree_hash": tree_hash,
        "required_by": list(required_by or []),
        "reason": reason,
        "note": note,
        "approved_at": utc_now(),
    }
    path = approval_path(root, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    atomic_write_text(tmp, json.dumps(doc, indent=2, sort_keys=True))
    tmp.replace(path)
    return path


def load_approval(root: Path, task_id: str) -> Optional[dict]:
    """Load the approval record for a task; missing/malformed -> None."""
    path = approval_path(root, task_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(doc, dict):
        return None
    return doc


def _valid_envelope(doc: dict, task_id: str) -> bool:
    return (
        doc.get("schema_version") == APPROVAL_SCHEMA_VERSION
        and doc.get("type") == "approval"
        and isinstance(doc.get("task_id"), str) and doc.get("task_id") == task_id
        and isinstance(doc.get("approver"), str)
        and _approver_is_valid(doc.get("approver"))
        and isinstance(doc.get("commit"), str) and bool(doc.get("commit"))
        and isinstance(doc.get("tree_hash"), str) and bool(doc.get("tree_hash"))
        and isinstance(doc.get("approved_at"), str) and bool(doc.get("approved_at"))
    )


def evaluate_approval(doc: Optional[dict], task_id: str, commit: str,
                      tree_hash: str) -> Tuple[str, List[str], Optional[dict]]:
    """Evaluate the approval record into a gate status.

    Returns (status, details, record). Missing/malformed -> BLOCKED;
    recorded for another commit/tree (new commit) -> NOT RUN.
    """
    if doc is None or not _valid_envelope(doc, task_id):
        return ("BLOCKED",
                ["no valid human approval recorded for %s "
                 "(record with `juicer approve %s --approver <name>`)"
                 % (task_id, task_id)], None)
    if doc.get("commit") != commit or doc.get("tree_hash") != tree_hash:
        return ("NOT RUN",
                ["approval by %s at %s is for commit %s, not the integration "
                 "commit %s — a new commit invalidates the approval"
                 % (doc.get("approver"), doc.get("approved_at"),
                    doc.get("commit"), commit)], doc)
    details = ["approved by %s at %s for commit %s"
               % (doc.get("approver"), doc.get("approved_at"), commit)]
    if doc.get("reason"):
        details.append("reason: %s" % doc["reason"])
    return "PASS", details, doc
