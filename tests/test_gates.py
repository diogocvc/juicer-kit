"""Gate semantics: NOT RUN / FAIL / BLOCKED never pass; only PASS advances."""

import pytest

from juicer.errors import GateBlockedError
from juicer.gates import evaluate_gate, gate_allows, latest_by_check_id, require_gate
from juicer.model import new_check_result


def res(status, check_id="tests", commit="abc"):
    return new_check_result(check_id, "TASK-001", ["pytest"], status,
                            commit=commit)


def test_all_pass_is_pass():
    gate = evaluate_gate([res("PASS"), res("PASS", "lint")], commit="abc")
    assert gate["status"] == "PASS"
    assert gate_allows(gate["status"])


def test_not_run_blocks():
    gate = evaluate_gate([res("PASS"), res("NOT RUN", "lint")], commit="abc")
    assert gate["status"] == "NOT RUN"
    assert not gate_allows(gate["status"])
    with pytest.raises(GateBlockedError):
        require_gate(gate["status"], "merge")


def test_fail_blocks_even_with_other_pass():
    gate = evaluate_gate([res("PASS"), res("FAIL", "lint")], commit="abc")
    assert gate["status"] == "FAIL"
    assert not gate_allows(gate["status"])


def test_blocked_blocks():
    gate = evaluate_gate([res("BLOCKED")], commit="abc")
    assert gate["status"] == "BLOCKED"
    assert not gate_allows(gate["status"])


def test_missing_required_check_is_not_run():
    gate = evaluate_gate([], commit="abc")
    assert gate["status"] == "NOT RUN"


def test_stale_commit_result_counts_as_not_run():
    gate = evaluate_gate([res("PASS", commit="old")], commit="new")
    assert gate["status"] == "NOT RUN"


def test_latest_by_check_id_wins():
    results = [res("FAIL"), res("PASS")]
    latest = latest_by_check_id(results)
    assert latest["tests"]["status"] == "PASS"


def test_integrate_refuses_when_checks_not_run(juicer):
    from conftest import fake_ok_executor, simple_task_specs
    # configure a required check that will be overridden to NOT RUN by hand
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"a.txt": "x\n"})
    juicer.run_task("TASK-001")
    # corrupt stored results: mark the required check NOT RUN
    store = juicer.checks_dir / "TASK-001.results.jsonl"
    lines = store.read_text(encoding="utf-8").splitlines()
    fixed = []
    for line in lines:
        import json
        obj = json.loads(line)
        obj["status"] = "NOT RUN"
        fixed.append(json.dumps(obj))
    store.write_text("\n".join(fixed) + "\n", encoding="utf-8")
    with pytest.raises(GateBlockedError) as exc:
        juicer.integrate("TASK-001")
    assert "NOT RUN" in str(exc.value)
    assert juicer.load_task("TASK-001")["status"] == "completed"  # not merged, not done


def test_integrate_refuses_when_checks_fail(juicer):
    from conftest import fake_ok_executor, simple_task_specs
    juicer.add_tasks(simple_task_specs("TASK-001"))
    juicer._executor = fake_ok_executor(write_files={"a.txt": "x\n"})
    juicer.run_task("TASK-001")
    import json
    store = juicer.checks_dir / "TASK-001.results.jsonl"
    lines = store.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[-1])
    obj["status"] = "FAIL"
    store.write_text(json.dumps(obj) + "\n", encoding="utf-8")
    with pytest.raises(GateBlockedError):
        juicer.integrate("TASK-001")
