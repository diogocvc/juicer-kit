"""One-way backlog Markdown import: strict parser and validation.

The backlog is the planning source. Importing copies validated tasks into a
mission; after that ``.juicer/`` is canonical. This module only reads Markdown
and never writes back to the backlog, so later backlog edits cannot mutate an
existing mission.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .errors import ValidationError
from .graph import detect_cycle

_TASK_HEADER_RE = re.compile(r"^###\s+Task:\s*\[([^\]]+)\]\s*(.*)$")
_ARCHIVE_HEADER_RE = re.compile(r"^#+\s+Task:\s*\[([^\]]+)\]")
_FIELD_RE = re.compile(r"^\*\*([^*]+)\*\*\s*:\s*(.*)$")
_CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(.+?)\s*$")
_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$")
_PRIORITY_RE = re.compile(
    r"^P([0-3])(?:-(Critical|High|Medium|Low))?$", re.IGNORECASE)
_PRIORITY_LABELS = {
    "0": "critical", "1": "high", "2": "medium", "3": "low",
}
_TEMPLATE_IDS = {"TASK-XXX"}
_NO_DEPS = {"", "-", "—", "–", "none", "n/a", "n.a."}
_FIELD_ALIASES = {
    "description": "description",
    "priority": "priority",
    "status": "status",
    "dependencies": "dependencies",
    "acceptance criteria": "acceptance_criteria",
    "estimated effort": "effort",
    "notes": "notes",
    "scope": "scope",
    "scope paths": "scope",
    "constraints": "constraints",
}


def _join(lines: List[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip()).strip()


def _parse_priority(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None, None, "missing priority (use P0, P1, P2 or P3)"
    match = _PRIORITY_RE.match(raw)
    if not match:
        return None, None, (
            "invalid priority %r (use P0, P1, P2 or P3, optionally with "
            "-Critical/-High/-Medium/-Low)" % raw)
    level = "P%s" % match.group(1)
    label = match.group(2)
    if label and label.lower() != _PRIORITY_LABELS[match.group(1)]:
        return None, None, (
            "priority %r has an inconsistent label (P%s is %s)"
            % (raw, match.group(1), _PRIORITY_LABELS[match.group(1)].title()))
    return level, raw, None


def _parse_dependencies(raw: str, task_id: str):
    raw = (raw or "").strip()
    if raw.lower() in _NO_DEPS:
        return [], None
    tokens = [t.strip("`") for t in re.split(r"[,\s]+", raw) if t.strip()]
    deps = []
    for token in tokens:
        if not _ID_RE.match(token):
            return None, "invalid dependency token %r" % token
        if token in deps:
            return None, "duplicate dependency %s" % token
        deps.append(token)
    if task_id in deps:
        return None, "task cannot depend on itself"
    return deps, None


def _parse_scope(raw: str):
    raw = (raw or "").strip()
    if raw.lower().startswith("paths:"):
        raw = raw.split(":", 1)[1]
    if not raw:
        return [], None
    paths = []
    for token in re.split(r"[,;]+", raw):
        path = token.strip().strip("`").strip().replace("\\", "/")
        if not path:
            continue
        if path.startswith("/") or path.startswith("~"):
            return None, "scope path %r must be relative" % path
        if ".." in path.split("/"):
            return None, "scope path %r cannot escape the project" % path
        paths.append(path)
    return paths, None


def _parse_constraints(lines: List[str]):
    raw = _join(lines)
    if not raw:
        return []
    return [part.strip() for part in re.split(r";+", raw) if part.strip()]


def _parse_task(task_id: str, title: str, line_no: int, body: List[str],
                errors: List[str]):
    fields = {}
    current = None
    for line in body:
        stripped = line.strip()
        match = _FIELD_RE.match(line)
        if match:
            name = match.group(1).strip().lower()
            current = _FIELD_ALIASES.get(name, "__ignore__")
            if current != "__ignore__":
                fields.setdefault(current, [])
                if match.group(2).strip():
                    fields[current].append(match.group(2))
            continue
        if current in (None, "__ignore__"):
            continue
        if stripped in ("---", "***", "___") or stripped.startswith("#"):
            continue
        fields[current].append(line)

    title = (title or "").strip()
    if not title:
        errors.append("line %s: task %s has no title" % (line_no, task_id))
    if not _ID_RE.match(task_id):
        errors.append("line %s: invalid task id %r" % (line_no, task_id))

    priority, priority_label, error = _parse_priority(_join(fields.get("priority", [])))
    if error:
        errors.append("task %s: %s" % (task_id, error))

    raw_status = _join(fields.get("status", [])).lower()
    if not raw_status:
        errors.append(
            "task %s: missing status (use Pending or In Progress)" % task_id)
        origin_status = ""
    elif raw_status in ("pending", "in progress", "in-progress", "in_progress"):
        origin_status = "pending" if raw_status == "pending" else "in_progress"
    elif raw_status in ("done", "completed"):
        errors.append(
            "task %s: status %r is already done; backlog/done is not imported"
            % (task_id, raw_status))
        origin_status = raw_status
    elif raw_status in ("blocked", "failed"):
        errors.append(
            "task %s: status %r is not importable from backlog.md "
            "(planning source accepts pending/in-progress)" % (task_id, raw_status))
        origin_status = raw_status
    else:
        errors.append("task %s: invalid status %r" % (task_id, raw_status))
        origin_status = raw_status

    description = _join(fields.get("description", []))
    if not description:
        errors.append("task %s: description is required" % task_id)
    notes = _join(fields.get("notes", []))
    if notes:
        description = "%s\n\nNotes: %s" % (description, notes) if description else notes

    if "dependencies" not in fields or not _join(fields.get("dependencies", [])):
        errors.append(
            "task %s: missing dependencies (use 'None' when there are none)"
            % task_id)
    deps, error = _parse_dependencies(
        _join(fields.get("dependencies", [])), task_id)
    if error:
        errors.append("task %s: %s" % (task_id, error))
        deps = []

    raw_criteria = fields.get("acceptance_criteria", [])
    criteria = []
    for raw in raw_criteria:
        if not raw.strip():
            continue
        match = _CHECKBOX_RE.match(raw)
        if not match:
            errors.append(
                "task %s: malformed acceptance criterion %r "
                "(expected '- [ ] text')" % (task_id, raw.strip()))
            continue
        text = match.group(2).strip()
        if not text:
            errors.append("task %s: empty acceptance criterion" % task_id)
            continue
        criteria.append({
            "id": "AC-%03d" % (len(criteria) + 1),
            "description": text,
            "verification": "human",
            "required": True,
            "satisfied": match.group(1).strip().lower() == "x",
        })
    if not criteria:
        errors.append("task %s: at least one acceptance criterion is required" % task_id)

    paths, error = _parse_scope(_join(fields.get("scope", [])))
    if error:
        errors.append("task %s: %s" % (task_id, error))
        paths = []

    return {
        "id": task_id,
        "title": title,
        "description": description,
        "priority": priority,
        "priority_label": priority_label,
        "depends_on": deps,
        "acceptance_criteria": criteria,
        "scope": {"paths": paths or [],
                  "constraints": _parse_constraints(fields.get("constraints", []))},
        "origin_status": origin_status,
        "line": line_no,
        "effort": _join(fields.get("effort", [])) or None,
    }


def archived_task_ids(paths) -> set:
    """Collect task IDs already archived (e.g. backlog/done/*.md)."""
    ids = set()
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            match = _ARCHIVE_HEADER_RE.match(line)
            if not match:
                continue
            task_id = match.group(1).strip()
            if task_id not in _TEMPLATE_IDS and _ID_RE.match(task_id):
                ids.add(task_id)
    return ids


def parse_backlog(text: str, completed_ids=None) -> List[dict]:
    """Parse pending tasks from backlog Markdown with strict validation.

    Fenced code blocks (including the task template) are ignored. The parser is
    read-only; it never rewrites the source text. Dependencies found in
    ``completed_ids`` (tasks already archived under ``backlog/done``) are
    recorded as satisfied and removed from ``depends_on``; every other
    dependency must be present in the same backlog file.
    """
    lines = (text or "").splitlines()
    errors: List[str] = []
    blocks = []
    current = None
    in_fence = False
    fence = None
    fence_start = None

    for index, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence, fence_start = True, marker, index
            elif marker == fence:
                in_fence, fence, fence_start = False, None, None
            continue
        if in_fence:
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if re.match(r"^#{1,6}\s+Task:", line):
                match = _TASK_HEADER_RE.match(line) if level == 3 else None
                if not match:
                    errors.append(
                        "line %s: malformed task header %r "
                        "(expected '### Task: [ID] title')"
                        % (index, stripped))
                    current = None
                    continue
                task_id = match.group(1).strip()
                if task_id in _TEMPLATE_IDS:
                    current = None
                    continue
                current = {"id": task_id, "title": match.group(2),
                           "line": index, "body": []}
                blocks.append(current)
                continue
            current = None
            continue
        if current is not None:
            current["body"].append(line)

    if in_fence:
        errors.append(
            "unterminated fenced code block starting at line %s" % fence_start)

    specs = []
    seen = set()
    for block in blocks:
        task_id = block["id"]
        if task_id in seen:
            errors.append("duplicate task id %s" % task_id)
            _parse_task(task_id, block["title"], block["line"],
                        block["body"], errors)
            continue
        seen.add(task_id)
        specs.append(_parse_task(task_id, block["title"], block["line"],
                                 block["body"], errors))

    if not specs and not errors:
        errors.append("no backlog tasks found")

    ids = {spec["id"] for spec in specs if spec.get("id")}
    completed = set(completed_ids or ())
    for spec in specs:
        if spec.get("id") in completed:
            errors.append(
                "task %s is already archived under backlog/done; remove the "
                "duplicate pending entry" % spec["id"])
        kept = []
        satisfied = []
        for dep in spec.get("depends_on", []):
            if dep in ids:
                kept.append(dep)
            elif dep in completed:
                satisfied.append(dep)
            else:
                errors.append(
                    "task %s depends on unknown task %s" % (spec["id"], dep))
        spec["depends_on"] = kept
        spec["completed_dependencies"] = satisfied

    if not errors and specs:
        cycle = detect_cycle(specs)
        if cycle:
            errors.append("dependency cycle: %s" % " -> ".join(cycle))

    if errors:
        raise ValidationError(errors)
    return specs
