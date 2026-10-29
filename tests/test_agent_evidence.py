"""Core-triggered @reviewer/@security agents.

The core invokes the existing agents through the harness, requires a strict
JSON block in the output, validates it, and records the evidence artifact
itself. Agent prose is never evidence; the core owns commit/tree linkage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from juicer import gitops
from juicer.errors import GateBlockedError
from juicer.evidence import EvidenceError
from juicer.harness import opencode
from juicer.orchestrator import extract_structured_evidence
from test_harness_contract import write_fake
from conftest import fake_ok_executor, simple_task_specs


def _completed_task(juicer, files=None):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files=files or {"feat.py": "X = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok, out.detail
    return juicer.load_task("TASK-001")


def _fenced(doc, preamble="Review notes\n"):
    return "%s\n```json\n%s\n```\n" % (preamble, json.dumps(doc))


def _agent_executor(payload, ok=True, detail="agent done", calls=None):
    def run(prompt, cwd, agent, timeout):
        if calls is not None:
            calls.append({"prompt": prompt, "cwd": str(cwd),
                          "agent": agent, "timeout": timeout})
        return {"ok": ok, "status": "PASS" if ok else "FAIL",
                "exit_code": 0 if ok else 1, "detail": detail,
                "session_id": "ses_agent", "output": payload}
    return run


def _artifact(juicer, kind, commit):
    return juicer.evidence_dir / "TASK-001" / ("%s-%s.json" % (kind, commit))


def test_run_review_records_core_owned_artifact(juicer):
    task = _completed_task(juicer)
    commit = task["result"]["commit"]
    calls = []
    juicer._executor = _agent_executor(_fenced({
        "verdict": "PASS",
        "findings": [{"severity": "medium", "description": "minor nit",
                      "file": "feat.py", "line": "7"}],
        "summary": "looks fine",
    }), calls=calls)

    out = juicer.run_review("TASK-001")

    artifact = json.loads(_artifact(juicer, "review", commit)
                          .read_text(encoding="utf-8"))
    assert artifact["type"] == "review"
    assert artifact["agent"] == "@reviewer"
    assert artifact["task_id"] == "TASK-001"
    assert artifact["commit"] == commit
    assert artifact["tree_hash"] == gitops.tree_hash(juicer.root, commit)
    assert artifact["scope"] == task["result"]["changed_files"]
    assert artifact["verdict"] == "PASS"
    assert artifact["findings"][0]["severity"] == "medium"
    assert artifact["findings"][0]["line"] == 7  # normalized to int

    assert out["verdict"] == "PASS"
    assert out["agent"] == "@reviewer"
    assert out["artifact_ref"] == artifact["artifact_ref"]
    # the existing @reviewer agent was the one triggered, in the task worktree
    assert calls[0]["agent"] == "reviewer"  # bare harness name, no @mention
    execution = juicer.load_execution(task["result"]["execution_id"])
    assert calls[0]["cwd"] == execution["workspace"]["worktree"]
    assert "TASK-001" in calls[0]["prompt"]
    assert "json" in calls[0]["prompt"].lower()
    # raw agent output is kept for audit
    assert Path(out["output_ref"]).read_text(
        encoding="utf-8").startswith("Review notes")

    events = [e["type"] for e in juicer.events()]
    assert "review_agent_started" in events
    assert "review_agent_recorded" in events


def test_run_review_rejects_prose_output(juicer):
    task = _completed_task(juicer)
    commit = task["result"]["commit"]
    juicer._executor = _agent_executor("Looks good to me. Approved!")
    with pytest.raises(EvidenceError) as exc:
        juicer.run_review("TASK-001")
    assert "structured" in str(exc.value).lower() or "json" in str(exc.value).lower()
    # prose is not evidence: no artifact is written
    assert not _artifact(juicer, "review", commit).exists()


def test_run_review_normalizes_critical_finding_to_fail(juicer):
    _completed_task(juicer)
    juicer._executor = _agent_executor(_fenced({
        "verdict": "PASS",  # agent contradiction: critical forces FAIL
        "findings": [{"severity": "critical", "description": "hardcoded secret",
                      "file": "feat.py"}],
    }))
    out = juicer.run_review("TASK-001")
    assert out["verdict"] == "FAIL"
    assert out["normalized_fail"] is True
    artifact = json.loads(Path(out["artifact_ref"]).read_text(encoding="utf-8"))
    assert artifact["verdict"] == "FAIL"


def test_run_review_rejects_invalid_severity(juicer):
    task = _completed_task(juicer)
    juicer._executor = _agent_executor(_fenced({
        "verdict": "PASS",
        "findings": [{"severity": "blocker", "description": "vague"}],
    }))
    with pytest.raises(EvidenceError):
        juicer.run_review("TASK-001")
    assert not _artifact(juicer, "review", task["result"]["commit"]).exists()


def test_agent_failure_is_not_evidence(juicer):
    _completed_task(juicer)
    juicer._executor = _agent_executor("boom", ok=False, detail="model unavailable")
    with pytest.raises(EvidenceError) as exc:
        juicer.run_review("TASK-001")
    assert "failed" in str(exc.value).lower()


def test_run_security_uses_security_agent_and_artifact(juicer):
    _completed_task(juicer)
    calls = []
    juicer._executor = _agent_executor(_fenced({
        "verdict": "PASS",
        "findings": [{"severity": "low", "description": "consider rate limiting"}],
    }), calls=calls)
    out = juicer.run_security("TASK-001")
    assert calls[0]["agent"] == "security"  # bare harness name
    assert out["verdict"] == "PASS"
    artifact = json.loads(Path(out["artifact_ref"]).read_text(encoding="utf-8"))
    assert artifact["type"] == "security"
    assert artifact["agent"] == "@security"
    assert "OWASP" in calls[0]["prompt"]


def test_run_review_requires_completed_task(juicer):
    juicer.add_tasks(simple_task_specs("TASK-001"))
    calls = []
    juicer._executor = _agent_executor(
        _fenced({"verdict": "PASS", "findings": []}), calls=calls)
    with pytest.raises(GateBlockedError) as exc:
        juicer.run_review("TASK-001")
    assert exc.value.gate_status == "BLOCKED"
    assert calls == []  # the core never spends an agent run on a ready task


def test_run_review_requires_commit(juicer):
    _completed_task(juicer)
    juicer._update_task("TASK-001", lambda t: t["result"].update(commit=None))
    juicer._executor = _agent_executor(
        _fenced({"verdict": "PASS", "findings": []}))
    with pytest.raises(GateBlockedError) as exc:
        juicer.run_review("TASK-001")
    assert exc.value.gate_status == "BLOCKED"


def test_clean_pass_after_fail_still_requires_force(juicer):
    """M-4 applies to core-triggered runs too: a clean PASS cannot silently
    overwrite a recorded FAIL."""
    _completed_task(juicer)
    juicer._executor = _agent_executor(_fenced({
        "verdict": "FAIL",
        "findings": [{"severity": "high", "description": "unsafe"}],
    }))
    juicer.run_review("TASK-001")
    juicer._executor = _agent_executor(_fenced({"verdict": "PASS",
                                                "findings": []}))
    with pytest.raises(EvidenceError):
        juicer.run_review("TASK-001")
    out = juicer.run_review("TASK-001", force=True)
    assert out["verdict"] == "PASS"


def test_run_review_uses_parsed_agent_text_from_event_stream(juicer):
    """V2 prints NDJSON events; the adapter exposes the assistant text in
    ``agent_output`` and the evidence parser must use it."""
    _completed_task(juicer)
    fenced = _fenced({"verdict": "PASS", "findings": []})
    event_stream = "\n".join([
        json.dumps({"type": "step_start"}),
        json.dumps({"type": "text", "part": {"type": "text", "text": fenced}}),
        json.dumps({"type": "step_finish"}),
    ])

    def run(prompt, cwd, agent, timeout):
        return {"ok": True, "status": "PASS", "exit_code": 0,
                "detail": "done", "session_id": "ses_agent",
                "output": event_stream, "agent_output": fenced}

    juicer._executor = run
    out = juicer.run_review("TASK-001")
    assert out["verdict"] == "PASS"
    # the raw event stream is still what lands in the audit file
    raw = Path(out["output_ref"]).read_text(encoding="utf-8")
    assert "step_start" in raw and "step_finish" in raw


def test_run_review_through_harness_wrapper_parses_v2_event_stream(
        juicer, monkeypatch, tmp_path):
    """End-to-end through the production wrapper (no injected agent_output):
    a V2 NDJSON stream from the binary must become a valid review artifact."""
    from conftest import fake_ok_executor, simple_task_specs

    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"feat.py": "X = 1\n"})
    assert juicer.run_task("TASK-001").ok

    event = json.dumps({
        "type": "text",
        "sessionID": "ses_v2_wrapper",
        "part": {
            "type": "text",
            "text": "```json\n{\"verdict\": \"PASS\", \"findings\": []}\n```",
        },
    })
    body = ("if [ \"$1\" = \"run\" ]; then\n"
            "  cat <<'EOF'\n" + event + "\nEOF\n"
            "  exit 0\n"
            "fi\n")
    fake = write_fake(tmp_path, body=body)
    monkeypatch.setenv("OPENCODE_BIN", str(fake))
    monkeypatch.setattr(opencode, "_HOME_BIN", str(tmp_path / "no-home"))
    juicer._executor = None  # force the real adapter wrapper + fake binary

    out = juicer.run_review("TASK-001", timeout=30)
    assert out["verdict"] == "PASS"
    assert "ses_v2_wrapper" in Path(out["output_ref"]).read_text(encoding="utf-8")


def test_run_review_refuses_when_worktree_is_missing(juicer):
    """Fail closed: never audit the base checkout as a fallback."""
    task = _completed_task(juicer)
    execution = juicer.load_execution(task["result"]["execution_id"])
    worktree = Path(execution["workspace"]["worktree"])
    worktree.rename(worktree.with_name(worktree.name + "-moved"))
    calls = []
    juicer._executor = _agent_executor(
        _fenced({"verdict": "PASS", "findings": []}), calls=calls)
    with pytest.raises(GateBlockedError) as exc:
        juicer.run_review("TASK-001")
    assert exc.value.gate_status == "BLOCKED"
    assert calls == []  # the agent is never run against the wrong tree
    events = [e for e in juicer.events()
              if e["type"] == "review_agent_blocked"]
    assert events and "worktree is missing" in events[-1]["data"]["reason"]


def test_run_review_refuses_tracked_worktree_changes(juicer):
    task = _completed_task(juicer)
    execution = juicer.load_execution(task["result"]["execution_id"])
    (Path(execution["workspace"]["worktree"]) / "feat.py").write_text(
        "TAMPERED = 1\n", encoding="utf-8")
    juicer._executor = _agent_executor(
        _fenced({"verdict": "PASS", "findings": []}))
    with pytest.raises(GateBlockedError) as exc:
        juicer.run_review("TASK-001")
    assert exc.value.gate_status == "BLOCKED"


def test_run_review_tolerates_untracked_check_artifacts(juicer):
    """Post-commit checks may leave untracked artifacts; the reviewed commit is
    unchanged, so the review is allowed."""
    task = _completed_task(juicer)
    execution = juicer.load_execution(task["result"]["execution_id"])
    (Path(execution["workspace"]["worktree"]) / "coverage.xml").write_text(
        "<coverage/>", encoding="utf-8")
    juicer._executor = _agent_executor(
        _fenced({"verdict": "PASS", "findings": []}))
    out = juicer.run_review("TASK-001")
    assert out["verdict"] == "PASS"


def test_run_review_refuses_mismatched_worktree_head(juicer):
    task = _completed_task(juicer)
    execution = juicer.load_execution(task["result"]["execution_id"])
    worktree = Path(execution["workspace"]["worktree"])
    (worktree / "post.py").write_text("P = 1\n", encoding="utf-8")
    gitops.commit_all(worktree, "post-task commit")
    calls = []
    juicer._executor = _agent_executor(
        _fenced({"verdict": "PASS", "findings": []}), calls=calls)
    with pytest.raises(GateBlockedError) as exc:
        juicer.run_review("TASK-001")
    assert exc.value.gate_status == "BLOCKED"
    assert "HEAD" in str(exc.value)
    assert calls == []


def test_agent_mutating_worktree_is_rejected(juicer):
    _completed_task(juicer)

    def mutating(prompt, cwd, agent, timeout):
        (Path(cwd) / "feat.py").write_text("TAMPERED = 1\n", encoding="utf-8")
        return {"ok": True, "status": "PASS", "exit_code": 0,
                "detail": "done", "session_id": "ses_agent",
                "output": _fenced({"verdict": "PASS", "findings": []})}

    juicer._executor = mutating
    with pytest.raises(EvidenceError) as exc:
        juicer.run_review("TASK-001")
    assert "workspace" in str(exc.value)
    events = [e for e in juicer.events()
              if e["type"] == "review_agent_rejected"]
    assert events and "worktree changed" in events[-1]["data"]["reason"]


def test_invalid_verdict_is_rejected_with_audit_event(juicer):
    _completed_task(juicer)
    juicer._executor = _agent_executor(
        _fenced({"verdict": "MAYBE", "findings": []}))
    with pytest.raises(EvidenceError):
        juicer.run_review("TASK-001")
    events = [e for e in juicer.events()
              if e["type"] == "review_agent_rejected"]
    assert events
    assert "invalid verdict" in events[-1]["data"]["reason"]


def test_executor_exception_is_not_evidence(juicer):
    _completed_task(juicer)

    def boom(prompt, cwd, agent, timeout):
        raise RuntimeError("harness crashed")

    juicer._executor = boom
    with pytest.raises(EvidenceError) as exc:
        juicer.run_review("TASK-001")
    assert "harness crashed" in str(exc.value)


# ---------- strict extraction ----------

def test_extract_accepts_last_valid_fenced_block():
    text = ('notes\n```json\n{"verdict": "FAIL"}\n```\nmore\n'
            '```json\n{"verdict": "PASS", "findings": []}\n```\n')
    assert extract_structured_evidence(text)["verdict"] == "PASS"


def test_extract_accepts_bare_json_object():
    doc = extract_structured_evidence('{"verdict": "PASS", "findings": []}')
    assert doc == {"verdict": "PASS", "findings": []}


def test_extract_rejects_prose_and_non_object_json():
    assert extract_structured_evidence("Looks good to me.") is None
    assert extract_structured_evidence("```json\nnot json\n```") is None
    assert extract_structured_evidence("```json\n[1, 2]\n```") is None
    assert extract_structured_evidence("") is None
