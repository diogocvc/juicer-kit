"""Task execution: success, failure, capture association, retry."""

from pathlib import Path

from conftest import fake_fail_executor, fake_ok_executor, simple_task_specs


def setup_chain(juicer, executor):
    juicer._executor = executor
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002", deps={"TASK-002": ["TASK-001"]}))


def test_run_success_moves_task_to_completed_with_evidence(juicer):
    setup_chain(juicer, fake_ok_executor(write_files={"feature.txt": "new\n"}))
    out = juicer.run_task("TASK-001")
    assert out.ok is True
    task = juicer.load_task("TASK-001")
    assert task["status"] == "completed"
    result = task["result"]
    assert result["session_id"] == "ses_fake"
    assert result["commit"]
    assert "feature.txt" in result["changed_files"]
    assert result["checks"][0]["status"] == "PASS"
    # execution record preserved and terminal
    execution = juicer.load_execution(result["execution_id"])
    assert execution["status"] == "succeeded"
    assert execution["task_id"] == "TASK-001"
    assert execution["workspace"]["branch"] == "juicer/TASK-001"


def test_run_blocked_when_dependencies_not_done(juicer):
    setup_chain(juicer, fake_ok_executor())
    out = juicer.run_task("TASK-002")
    assert out.ok is False
    assert "dependencies not done" in out.detail
    assert juicer.load_task("TASK-002")["status"] == "ready"


def test_task_failure_is_explicit_and_retryable(juicer):
    setup_chain(juicer, fake_fail_executor(detail="boom"))
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    task = juicer.load_task("TASK-001")
    assert task["status"] == "failed"
    assert task["attempt_count"] == 1
    execution = juicer.load_execution(task["current_execution_id"])
    assert execution["status"] == "failed"
    assert execution["failure"]["detail"] == "boom"
    # recovery: explicit retry -> ready, then a good run completes
    juicer.retry_task("TASK-001")
    juicer._executor = fake_ok_executor(write_files={"fixed.txt": "x\n"})
    out2 = juicer.run_task("TASK-001")
    assert out2.ok is True
    task = juicer.load_task("TASK-001")
    assert task["status"] == "completed"
    assert task["attempt_count"] == 2
    # first execution remains for audit
    assert juicer.load_execution(execution["id"])["status"] == "failed"


def test_result_captured_against_correct_task(juicer):
    def executor_for(expected_task):
        def run(prompt, cwd, agent, timeout):
            assert expected_task in prompt, "prompt must carry task identity"
            marker = "%s.marker" % expected_task
            (Path(cwd) / marker).write_text("payload-%s" % expected_task, encoding="utf-8")
            return {"ok": True, "status": "PASS", "exit_code": 0, "detail": "ok",
                    "session_id": "ses-%s" % expected_task, "output": "done"}
        return run

    # two independent tasks run sequentially; each captures only its own marker
    juicer.add_tasks(simple_task_specs("TASK-001", "TASK-002"))
    juicer._executor = executor_for("TASK-001")
    juicer.run_task("TASK-001")
    juicer._executor = executor_for("TASK-002")
    juicer.run_task("TASK-002")
    r1 = juicer.load_task("TASK-001")["result"]
    r2 = juicer.load_task("TASK-002")["result"]
    assert "TASK-001.marker" in r1["changed_files"]
    assert "TASK-002.marker" in r2["changed_files"]
    assert "TASK-002.marker" not in r1["changed_files"]
    assert r1["execution_id"] != r2["execution_id"]


def test_scope_violation_fails_task(juicer):
    juicer.add_tasks([{
        "id": "TASK-001", "title": "T1", "description": "d",
        "acceptance_criteria": [],
        "scope": {"paths": ["docs/**"], "constraints": []},
    }])
    juicer._executor = fake_ok_executor(write_files={"outside.py": "x = 1\n"})
    out = juicer.run_task("TASK-001")
    assert out.ok is False
    task = juicer.load_task("TASK-001")
    assert task["status"] == "failed"
    assert "outside scope" in str(task["result"])
