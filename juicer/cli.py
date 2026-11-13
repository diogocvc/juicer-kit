"""Command line interface for the Juicer core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .errors import JuicerError
from .orchestrator import Juicer


def _print(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def _juicer(args) -> Juicer:
    return Juicer(Path(args.root).resolve())


def cmd_init(args):
    j = _juicer(args)
    cfg = j.init(force=args.force)
    print("initialized %s (kit %s)" % (j.jdir, __version__))
    _print(cfg)
    return 0


def cmd_mission(args):
    j = _juicer(args)
    criteria = []
    for i, c in enumerate(args.criterion or [], 1):
        criteria.append({"id": "AC-%03d" % i, "description": c,
                         "verification": "human", "required": True})
    gaps = []
    for i, g in enumerate(args.gap or [], 1):
        gaps.append({"id": "GAP-%03d" % i, "question": g, "resolution": None})
    doc = j.set_mission(
        title=args.title, objective=args.objective,
        scope={"included": args.include or [], "excluded": args.exclude or []},
        constraints=args.constraint or [], acceptance_criteria=criteria,
        gaps=gaps, force=args.force,
    )
    _print(doc)
    return 0


def cmd_gap(args):
    j = _juicer(args)
    _print(j.resolve_gap(args.gap_id, args.answer))
    return 0


def cmd_inspect(args):
    j = _juicer(args)
    _print(j.inspect())
    return 0


def cmd_decompose(args):
    j = _juicer(args)
    spec = json.loads(Path(args.file).read_text(encoding="utf-8"))
    tasks = spec["tasks"] if isinstance(spec, dict) else spec
    made = j.add_tasks(tasks)
    _print([{"id": t["id"], "status": t["status"], "depends_on": t["depends_on"]}
            for t in made])
    return 0


def cmd_import_backlog(args):
    j = _juicer(args)
    _print(j.import_backlog(args.file))
    return 0


def cmd_status(args):
    j = _juicer(args)
    st = j.status()
    if args.json:
        _print(st)
        return 0
    mission = st["mission"]
    if mission:
        print("mission %s [%s]: %s" % (mission["id"], mission["status"], mission["title"]))
    else:
        print("no mission")
    for t in st["tasks"]:
        deps = (" depends_on=%s" % ",".join(t["depends_on"])) if t["depends_on"] else ""
        print("  %s  %-12s %s%s" % (t["id"], t["status"], t["title"], deps))
    if st["eligible"]:
        print("eligible: %s" % ", ".join(st["eligible"]))
    print("next: %s" % st["next_action"])
    return 0


def cmd_run(args):
    j = _juicer(args)
    if args.task:
        out = j.run_task(args.task)
        _print({"task_id": out.task_id, "ok": out.ok, "detail": out.detail,
                "data": out.data})
        return 0 if out.ok else 1
    outcomes = j.run_eligible(max_jobs=args.jobs)
    _print([{"task_id": o.task_id, "ok": o.ok, "detail": o.detail,
             "serialized_reason": o.serialized_reason} for o in outcomes])
    j.checkpoint(note="after run_eligible")
    return 0 if all(o.ok for o in outcomes) else 1


def cmd_retry(args):
    j = _juicer(args)
    _print(j.retry_task(args.task))
    return 0


def cmd_review(args):
    j = _juicer(args)
    findings = []
    if args.finding:
        for f in args.finding:
            parts = f.split(":", 2)
            finding = {"severity": "medium", "description": f}
            if len(parts) >= 2:
                finding["severity"] = parts[0]
                finding["description"] = parts[1]
            if len(parts) >= 3:
                finding["file"] = parts[2]
            findings.append(finding)
    scope = args.scope or []
    out = j.record_review(
        task_id=args.task, execution_id=args.execution_id or "REVIEW-001",
        commit=args.commit, tree_hash=args.tree_hash or "",
        scope=scope, findings=findings, verdict=args.verdict,
        agent=args.agent or "@reviewer", force=args.force)
    _print(out)
    return 0


def cmd_review_run(args):
    j = _juicer(args)
    _print(j.run_review(args.task, timeout=args.timeout, force=args.force))
    return 0


def cmd_security_run(args):
    j = _juicer(args)
    _print(j.run_security(args.task, timeout=args.timeout, force=args.force))
    return 0


def cmd_security(args):
    j = _juicer(args)
    findings = []
    if args.finding:
        for f in args.finding:
            parts = f.split(":", 2)
            finding = {"severity": "medium", "description": f}
            if len(parts) >= 2:
                finding["severity"] = parts[0]
                finding["description"] = parts[1]
            if len(parts) >= 3:
                finding["file"] = parts[2]
            findings.append(finding)
    scope = args.scope or []
    out = j.record_security(
        task_id=args.task, execution_id=args.execution_id or "SECURITY-001",
        commit=args.commit, tree_hash=args.tree_hash or "",
        scope=scope, findings=findings, verdict=args.verdict,
        agent=args.agent or "@security", force=args.force)
    _print(out)
    return 0


def cmd_approve(args):
    j = _juicer(args)
    _print(j.approve(args.task, approver=args.approver,
                     reason=args.reason, note=args.note))
    return 0


def cmd_integrate(args):
    j = _juicer(args)
    out = j.integrate(args.task, approve=args.approve)
    _print(out)
    return 0


def cmd_checkpoint(args):
    j = _juicer(args)
    _print(j.checkpoint(note=args.note or ""))
    return 0


def cmd_resume(args):
    j = _juicer(args)
    _print(j.resume())
    return 0


def cmd_events(args):
    j = _juicer(args)
    _print(j.events(limit=args.limit))
    return 0


def cmd_discover(args):
    from .harness import opencode as oc
    _print(oc.discover())
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="juicer",
                                description="Juicer Kit %s — activity-oriented execution" % __version__)
    p.add_argument("--root", default=".", help="project root (default: cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="initialize .juicer/ state")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("mission", help="define the mission (A01)")
    sp.add_argument("--title", required=True)
    sp.add_argument("--objective", required=True)
    sp.add_argument("--criterion", action="append", help="acceptance criterion (repeatable)")
    sp.add_argument("--gap", action="append", help="open question blocking readiness (repeatable)")
    sp.add_argument("--include", action="append")
    sp.add_argument("--exclude", action="append")
    sp.add_argument("--constraint", action="append")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_mission)

    sp = sub.add_parser("gap", help="resolve a mission gap")
    sp.add_argument("gap_id")
    sp.add_argument("--answer", required=True)
    sp.set_defaults(fn=cmd_gap)

    sp = sub.add_parser("inspect", help="record repository baseline evidence (A03)")
    sp.set_defaults(fn=cmd_inspect)

    sp = sub.add_parser("decompose", help="add tasks from a JSON file")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_decompose)

    sp = sub.add_parser(
        "import-backlog",
        help="import pending tasks from backlog Markdown (one-way, once per mission)")
    sp.add_argument("--file", default=None,
                    help="backlog Markdown path (default: backlog/backlog.md)")
    sp.set_defaults(fn=cmd_import_backlog)

    sp = sub.add_parser("status", help="show mission, tasks, eligibility, next action")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_status)

    sp = sub.add_parser("run", help="run one task or all eligible tasks")
    sp.add_argument("task", nargs="?", help="task id (omit to run eligible set)")
    sp.add_argument("--jobs", type=int, default=None, help="parallel workers")
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("retry", help="return a failed or blocked task to ready")
    sp.add_argument("task")
    sp.set_defaults(fn=cmd_retry)

    sp = sub.add_parser("review", help="record a structured review evidence artifact")
    sp.add_argument("task", help="task id")
    sp.add_argument("--commit", required=True, help="commit hash the review is linked to")
    sp.add_argument("--tree-hash", dest="tree_hash", required=True,
                    help="git tree hash of the commit")
    sp.add_argument("--execution-id", default="REVIEW-001", help="execution id")
    sp.add_argument("--verdict", choices=["PASS", "FAIL"], default="PASS",
                    help="review verdict")
    sp.add_argument("--agent", default="@reviewer", help="reviewing agent")
    sp.add_argument("--scope", action="append", help="reviewed file path (repeatable)")
    sp.add_argument("--finding", action="append",
                    help="finding as severity:description[:file] (repeatable)")
    sp.add_argument("--force", action="store_true",
                    help="allow a PASS verdict to overwrite a recorded FAIL")
    sp.set_defaults(fn=cmd_review)

    sp = sub.add_parser("security", help="record a structured security evidence artifact")
    sp.add_argument("task", help="task id")
    sp.add_argument("--commit", required=True, help="commit hash the audit is linked to")
    sp.add_argument("--tree-hash", dest="tree_hash", required=True,
                    help="git tree hash of the commit")
    sp.add_argument("--execution-id", default="SECURITY-001", help="execution id")
    sp.add_argument("--verdict", choices=["PASS", "FAIL"], default="PASS",
                    help="security verdict")
    sp.add_argument("--agent", default="@security", help="auditing agent")
    sp.add_argument("--scope", action="append", help="audited file path (repeatable)")
    sp.add_argument("--finding", action="append",
                    help="finding as severity:description[:file] (repeatable)")
    sp.add_argument("--force", action="store_true",
                    help="allow a PASS verdict to overwrite a recorded FAIL")
    sp.set_defaults(fn=cmd_security)

    sp = sub.add_parser(
        "review-run",
        help="trigger the existing @reviewer agent and record its evidence")
    sp.add_argument("task", help="completed task id")
    sp.add_argument("--timeout", type=int, default=900,
                    help="agent timeout in seconds (default: 900)")
    sp.add_argument("--force", action="store_true",
                    help="allow a PASS verdict to overwrite a recorded FAIL")
    sp.set_defaults(fn=cmd_review_run)

    sp = sub.add_parser(
        "security-run",
        help="trigger the existing @security agent and record its evidence")
    sp.add_argument("task", help="completed task id")
    sp.add_argument("--timeout", type=int, default=900,
                    help="agent timeout in seconds (default: 900)")
    sp.add_argument("--force", action="store_true",
                    help="allow a PASS verdict to overwrite a recorded FAIL")
    sp.set_defaults(fn=cmd_security_run)

    sp = sub.add_parser(
        "approve",
        help="record a human approval linked to the task commit/tree")
    sp.add_argument("task", help="task id (must have a commit)")
    sp.add_argument("--approver", required=True,
                    help="approver identity (never anonymous)")
    sp.add_argument("--reason", default=None,
                    help="why approval was required (no secrets)")
    sp.add_argument("--note", default=None,
                    help="justification note (no secrets)")
    sp.set_defaults(fn=cmd_approve)

    sp = sub.add_parser("integrate", help="gate + merge + post-merge checks")
    sp.add_argument("task")
    sp.add_argument("--approve", action="store_true",
                    help="explicit merge intent; a `juicer approve` record for "
                         "this commit is still required when approval applies")
    sp.set_defaults(fn=cmd_integrate)

    sp = sub.add_parser("checkpoint", help="write a recovery checkpoint")
    sp.add_argument("--note", default="")
    sp.set_defaults(fn=cmd_checkpoint)

    sp = sub.add_parser("resume", help="reconcile interrupted state after restart")
    sp.set_defaults(fn=cmd_resume)

    sp = sub.add_parser("events", help="show recent events")
    sp.add_argument("--limit", type=int, default=50)
    sp.set_defaults(fn=cmd_events)

    sp = sub.add_parser("discover", help="report harness capabilities")
    sp.set_defaults(fn=cmd_discover)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except JuicerError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
