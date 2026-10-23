"""Quality gates over check results.

Technical gate: PASS / FAIL / BLOCKED / NOT RUN.
Human gate stays separate: it is never inferred from technical results.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .errors import GateBlockedError

WORST = {"PASS": 0, "NOT RUN": 1, "BLOCKED": 2, "FAIL": 3}


def evaluate_gate(required: Iterable[dict], commit: Optional[str] = None) -> dict:
    """Aggregate required check results into a gate status.

    A required check with no result for *commit* counts as NOT RUN.
    """
    required = list(required)
    statuses: List[str] = []
    details = []
    for check in required:
        if commit is not None and check.get("commit") not in (None, commit):
            statuses.append("NOT RUN")
            details.append("%s: stale result for commit %s" % (check.get("check_id"), check.get("commit")))
            continue
        status = check.get("status", "NOT RUN")
        if status not in ("PASS", "FAIL", "BLOCKED", "NOT RUN"):
            status = "NOT RUN"
        statuses.append(status)
        details.append("%s: %s" % (check.get("check_id"), status))
    if not statuses:
        gate = "NOT RUN"
        details.append("no required checks configured/executed")
    else:
        worst = max(statuses, key=lambda s: WORST[s])
        gate = worst
    return {"status": gate, "details": details}


def gate_allows(status: str) -> bool:
    return status == "PASS"


def require_gate(status: str, context: str) -> None:
    if not gate_allows(status):
        raise GateBlockedError(
            "gate blocks %s: %s" % (context, status), gate_status=status
        )


def latest_by_check_id(results: Iterable[dict]) -> dict:
    """Last result wins per check_id (list assumed append-ordered)."""
    out = {}
    for r in results:
        out[r["check_id"]] = r
    return out
