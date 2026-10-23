"""Dependency graph: cycle detection, eligibility, topological waves."""

from __future__ import annotations

from collections import defaultdict, deque

from .errors import ValidationError


def build_adjacency(tasks):
    """Return (deps, dependents) maps of task_id -> set(ids). Validates references."""
    ids = {t["id"] for t in tasks}
    deps = {}
    dependents = defaultdict(set)
    for t in tasks:
        for d in t.get("depends_on", []):
            if d not in ids:
                raise ValidationError(["task %s depends on unknown task %s" % (t["id"], d)])
        deps[t["id"]] = set(t.get("depends_on", []))
        for d in t.get("depends_on", []):
            dependents[d].add(t["id"])
    return deps, dependents


def detect_cycle(tasks):
    """Return a cycle path (list of ids) or None if the graph is acyclic."""
    deps, _ = build_adjacency(tasks)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in deps}
    stack = []

    def visit(node):
        color[node] = GRAY
        stack.append(node)
        for parent in sorted(deps[node]):
            if color[parent] == GRAY:
                idx = stack.index(parent)
                return stack[idx:] + [parent]
            if color[parent] == WHITE:
                found = visit(parent)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for tid in sorted(deps):
        if color[tid] == WHITE:
            found = visit(tid)
            if found:
                return found
    return None


def eligible_tasks(tasks, status_of=None):
    """Tasks that are ready and whose dependencies are all done."""
    status_of = status_of or (lambda t: t["status"])
    deps, _ = build_adjacency(tasks)
    by_id = {t["id"]: t for t in tasks}
    out = []
    for t in tasks:
        if status_of(t) != "ready":
            continue
        if all(status_of(by_id[d]) == "done" for d in deps[t["id"]]):
            out.append(t)
    return sorted(out, key=lambda t: t["id"])


def topo_waves(tasks):
    """Kahn layering of ready-path tasks; raises on cycles.

    Returns a list of waves (lists of task ids) covering every task once.
    Only depends_on ordering is used; statuses are ignored.
    """
    if detect_cycle(tasks):
        raise ValidationError(["dependency cycle detected: %s" % " -> ".join(detect_cycle(tasks))])
    deps, dependents = build_adjacency(tasks)
    remaining = {tid: set(parents) for tid, parents in deps.items()}
    waves = []
    ready = deque(sorted(tid for tid, parents in remaining.items() if not parents))
    seen = 0
    while ready:
        wave = sorted(ready)
        ready.clear()
        waves.append(wave)
        seen += len(wave)
        for tid in wave:
            for child in sorted(dependents.get(tid, ())):
                remaining[child].discard(tid)
                if not remaining[child]:
                    ready.append(child)
    if seen != len(tasks):
        raise ValidationError(["dependency cycle detected among remaining tasks"])
    return waves
