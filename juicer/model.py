"""Record models: Mission, Task, Execution, CheckResult.

Contracts follow the approved structural document (Task B.12, Execution B.13),
trimmed to the MVP: local single-project operation, no distributed lease.
"""

from __future__ import annotations

import re
import uuid

from .errors import InvalidTransitionError, ValidationError
from .state import utc_now

SCHEMA_VERSION = 1

MISSION_STATUS = ("draft", "waiting_human", "ready", "active", "done")
TASK_STATUS = ("ready", "in_progress", "blocked", "failed", "completed", "done")
EXECUTION_STATUS = ("claimed", "running", "succeeded", "failed", "cancelled")
CHECK_STATUS = ("PASS", "FAIL", "BLOCKED", "NOT RUN")

TASK_TRANSITIONS = {
    ("ready", "in_progress"),
    ("ready", "blocked"),
    ("in_progress", "completed"),
    ("in_progress", "failed"),
    ("in_progress", "blocked"),
    ("blocked", "ready"),
    ("failed", "ready"),
    ("completed", "done"),
    ("completed", "blocked"),
}

EXECUTION_TRANSITIONS = {
    ("claimed", "running"),
    ("claimed", "failed"),
    ("claimed", "cancelled"),
    ("running", "succeeded"),
    ("running", "failed"),
    ("running", "cancelled"),
}

_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$")


def new_run_id() -> str:
    return "RUN-" + uuid.uuid4().hex[:8]


def check_transition(entity: str, current: str, target: str, allowed) -> None:
    if (current, target) not in allowed:
        raise InvalidTransitionError("%s: transition %s -> %s not allowed" % (entity, current, target))


def _require(errors, cond, msg):
    if not cond:
        errors.append(msg)


def validate_mission(doc: dict):
    errors = []
    _require(errors, isinstance(doc, dict), "mission must be an object")
    if not isinstance(doc, dict):
        raise ValidationError(errors)
    _require(errors, doc.get("schema_version") == SCHEMA_VERSION, "schema_version must be %s" % SCHEMA_VERSION)
    _require(errors, bool(doc.get("id")) and bool(_ID_RE.match(str(doc.get("id", "")))), "invalid mission id")
    _require(errors, bool(doc.get("title")), "title is required")
    _require(errors, bool(doc.get("objective")), "objective is required")
    _require(errors, doc.get("status") in MISSION_STATUS, "invalid mission status")
    _require(errors, isinstance(doc.get("dependencies", []), list), "dependencies must be a list")
    _require(errors, isinstance(doc.get("gaps", []), list), "gaps must be a list")
    _require(errors, isinstance(doc.get("acceptance_criteria", []), list), "acceptance_criteria must be a list")
    _require(errors, "revision" in doc, "revision is required")
    _require(errors, bool(doc.get("created_at")), "created_at is required")
    _require(errors, bool(doc.get("updated_at")), "updated_at is required")
    if errors:
        raise ValidationError(errors)
    return doc


def new_mission(mission_id: str, title: str, objective: str, scope=None, constraints=None,
                acceptance_criteria=None, gaps=None, dependencies=None, status="draft") -> dict:
    now = utc_now()
    doc = {
        "schema_version": SCHEMA_VERSION,
        "id": mission_id,
        "title": title,
        "objective": objective,
        "scope": scope or {},
        "constraints": constraints or [],
        "acceptance_criteria": acceptance_criteria or [],
        "gaps": gaps or [],
        "dependencies": dependencies or [],
        "status": status,
        "revision": 0,
        "created_at": now,
        "updated_at": now,
    }
    validate_mission(doc)
    return doc


def validate_task(doc: dict):
    errors = []
    _require(errors, isinstance(doc, dict), "task must be an object")
    if not isinstance(doc, dict):
        raise ValidationError(errors)
    _require(errors, doc.get("schema_version") == SCHEMA_VERSION, "schema_version must be %s" % SCHEMA_VERSION)
    _require(errors, bool(doc.get("id")) and bool(_ID_RE.match(str(doc.get("id", "")))), "invalid task id")
    _require(errors, bool(doc.get("mission_id")), "mission_id is required")
    _require(errors, bool(doc.get("title")), "title is required")
    _require(errors, bool(doc.get("description")), "description is required")
    _require(errors, doc.get("status") in TASK_STATUS, "invalid task status")
    deps = doc.get("depends_on")
    _require(errors, isinstance(deps, list), "depends_on must be a list")
    if isinstance(deps, list):
        _require(errors, len(deps) == len(set(deps)), "depends_on has duplicates")
        _require(errors, doc.get("id") not in deps, "task cannot depend on itself")
    criteria = doc.get("acceptance_criteria", [])
    _require(errors, isinstance(criteria, list), "acceptance_criteria must be a list")
    if isinstance(criteria, list):
        seen = set()
        for c in criteria:
            if not isinstance(c, dict) or not c.get("id") or not c.get("description"):
                errors.append("acceptance criterion must have id and description")
                continue
            if c["id"] in seen:
                errors.append("duplicate acceptance criterion id %s" % c["id"])
            seen.add(c["id"])
            _require(errors, bool(c.get("verification")), "criterion %s needs verification" % c["id"])
    scope = doc.get("scope", {})
    _require(errors, isinstance(scope, dict) and isinstance(scope.get("paths", []), list),
             "scope.paths must be a list")
    policy = doc.get("approval_policy", {})
    _require(errors, isinstance(policy, dict), "approval_policy must be an object")
    _require(errors, isinstance(doc.get("depends_on", []), list), "depends_on must be a list")
    _require(errors, "revision" in doc, "revision is required")
    _require(errors, isinstance(doc.get("attempt_count", 0), int) and doc.get("attempt_count", 0) >= 0,
             "attempt_count must be a non-negative integer")
    _require(errors, bool(doc.get("created_at")), "created_at is required")
    _require(errors, bool(doc.get("updated_at")), "updated_at is required")
    if errors:
        raise ValidationError(errors)
    return doc


def new_task(task_id: str, mission_id: str, title: str, description: str,
             depends_on=None, acceptance_criteria=None, scope=None,
             approval_policy=None, agent="coder", checks=None, status="ready") -> dict:
    now = utc_now()
    doc = {
        "schema_version": SCHEMA_VERSION,
        "id": task_id,
        "mission_id": mission_id,
        "title": title,
        "description": description,
        "status": status,
        "depends_on": depends_on or [],
        "acceptance_criteria": acceptance_criteria or [],
        "scope": scope or {"paths": [], "constraints": []},
        "approval_policy": approval_policy or {"human_approval_required": False, "required_gates": ["verification"]},
        "agent": agent,
        "checks": checks or [],
        "current_execution_id": None,
        "result": None,
        "replaces_task_id": None,
        "attempt_count": 0,
        "revision": 0,
        "created_at": now,
        "updated_at": now,
    }
    validate_task(doc)
    return doc


def validate_execution(doc: dict):
    errors = []
    _require(errors, isinstance(doc, dict), "execution must be an object")
    if not isinstance(doc, dict):
        raise ValidationError(errors)
    _require(errors, doc.get("schema_version") == SCHEMA_VERSION, "schema_version must be %s" % SCHEMA_VERSION)
    _require(errors, bool(doc.get("id")), "id is required")
    _require(errors, bool(doc.get("task_id")), "task_id is required")
    _require(errors, doc.get("status") in EXECUTION_STATUS, "invalid execution status")
    _require(errors, isinstance(doc.get("worker", {}), dict), "worker must be an object")
    _require(errors, "revision" in doc, "revision is required")
    _require(errors, bool(doc.get("created_at")), "created_at is required")
    _require(errors, bool(doc.get("updated_at")), "updated_at is required")
    if errors:
        raise ValidationError(errors)
    return doc


def new_execution(execution_id: str, task_id: str, worker=None, workspace=None) -> dict:
    now = utc_now()
    doc = {
        "schema_version": SCHEMA_VERSION,
        "id": execution_id,
        "task_id": task_id,
        "status": "claimed",
        "worker": worker or {"id": "local", "harness": "opencode"},
        "attempt": 1,
        "workspace": workspace or {"branch": None, "base_commit": None, "worktree": None},
        "started_at": None,
        "finished_at": None,
        "result": None,
        "failure": None,
        "revision": 0,
        "created_at": now,
        "updated_at": now,
    }
    validate_execution(doc)
    return doc


def validate_check_result(doc: dict):
    errors = []
    _require(errors, isinstance(doc, dict), "check result must be an object")
    if not isinstance(doc, dict):
        raise ValidationError(errors)
    _require(errors, doc.get("status") in CHECK_STATUS, "invalid check status")
    _require(errors, bool(doc.get("check_id")), "check_id is required")
    _require(errors, bool(doc.get("command")), "command is required")
    _require(errors, bool(doc.get("task_id")), "task_id is required")
    if errors:
        raise ValidationError(errors)
    return doc


def new_check_result(check_id: str, task_id: str, command, status, commit=None,
                     exit_code=None, log_ref=None, summary=None, phase="pre_merge"):
    doc = {
        "schema_version": SCHEMA_VERSION,
        "check_id": check_id,
        "task_id": task_id,
        "command": list(command) if isinstance(command, (list, tuple)) else [str(command)],
        "status": status if status in CHECK_STATUS else "NOT RUN",
        "commit": commit,
        "exit_code": exit_code,
        "log_ref": log_ref,
        "summary": summary,
        "phase": phase,
        "recorded_at": utc_now(),
    }
    validate_check_result(doc)
    return doc
