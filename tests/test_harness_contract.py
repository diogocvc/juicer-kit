"""Internal harness contract and OpenCode adapter behavior (V2 target)."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from juicer.harness import opencode
from juicer.harness.contract import (
    ExecutionRequest,
    ExecutionResult,
    Harness,
)

# Fake help mirrors the measured OpenCode 2.1.4 `run --help` / `serve --help`.
V2_HELP = """if [ "$1" = "--version" ]; then
  echo "opencode v2.1.4"
  exit 0
fi
if [ "$1" = "run" ] && [ "$2" = "--help" ]; then
  cat <<'EOF'
--standalone
--server string
--continue, -c
--session, -s string
--fork
--model, -m string
--agent string
--format choice (choices: default, json)
--file, -f string
--title string
--thinking
--auto
EOF
  exit 0
fi
if [ "$1" = "serve" ] && [ "$2" = "--help" ]; then
  echo "Start the v2 API and web server"
  exit 0
fi
"""

V1_HELP = """if [ "$1" = "--version" ]; then
  echo "1.19.4"
  exit 0
fi
if [ "$1" = "run" ] && [ "$2" = "--help" ]; then
  cat <<'EOF'
--format [choices: "default", "json"]
--agent [string]
--dir [string]
-s, --session [string]
-c, --continue [boolean]
--auto [boolean]
EOF
  exit 0
fi
if [ "$1" = "serve" ] && [ "$2" = "--help" ]; then
  echo "starts a headless opencode server"
  exit 0
fi
"""


def write_fake(tmp_path: Path, body: str = "", probe: str = "v2") -> Path:
    fake = tmp_path / "opencode"
    help_block = {"v2": V2_HELP, "v1": V1_HELP, "none": ""}[probe]
    fake.write_text("#!/bin/sh\n" + help_block + body, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return fake


def write_fake_at(path: Path, probe: str = "v2") -> Path:
    """Write a fake opencode binary at an arbitrary path (multi-candidate)."""
    help_block = {"v2": V2_HELP, "v1": V1_HELP, "none": ""}[probe]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + help_block, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def isolate_discovery(monkeypatch, tmp_path: Path):
    """Point every discovery default at empty locations under tmp_path."""
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(opencode.shutil, "which", lambda name: None)
    monkeypatch.setattr(opencode, "_HOME_BIN", str(tmp_path / "no-home" / "opencode"))
    monkeypatch.setattr(opencode, "_ZED_GLOB", str(tmp_path / "no-zed" / "*" / "opencode"))


class TestFindBinary:
    def test_explicit_binary_wins_over_everything(self, monkeypatch, tmp_path):
        isolate_discovery(monkeypatch, tmp_path)
        explicit = write_fake_at(tmp_path / "explicit" / "opencode", "v1")
        env_bin = write_fake_at(tmp_path / "env" / "opencode", "v2")
        monkeypatch.setenv("OPENCODE_BIN", str(env_bin))
        assert opencode.find_binary(str(explicit)) == str(explicit)

    def test_missing_explicit_binary_is_none(self, monkeypatch, tmp_path):
        isolate_discovery(monkeypatch, tmp_path)
        assert opencode.find_binary(str(tmp_path / "missing")) is None

    def test_env_var_beats_path_candidate(self, monkeypatch, tmp_path):
        isolate_discovery(monkeypatch, tmp_path)
        env_bin = write_fake_at(tmp_path / "env" / "opencode", "v2")
        path_bin = write_fake_at(tmp_path / "path" / "opencode", "v2")
        monkeypatch.setattr(opencode.shutil, "which", lambda name: str(path_bin))
        monkeypatch.setenv("OPENCODE_BIN", str(env_bin))
        assert opencode.find_binary() == str(env_bin)

    def test_v2_is_preferred_among_default_candidates(self, monkeypatch, tmp_path):
        """PATH finds a V1 binary; ~/.opencode/bin holds V2 -> V2 wins."""
        isolate_discovery(monkeypatch, tmp_path)
        path_v1 = write_fake_at(tmp_path / "path" / "opencode", "v1")
        home_v2 = write_fake_at(tmp_path / "home" / "opencode", "v2")
        monkeypatch.setattr(opencode.shutil, "which", lambda name: str(path_v1))
        monkeypatch.setattr(opencode, "_HOME_BIN", str(home_v2))
        assert opencode.find_binary() == str(home_v2)

    def test_falls_back_to_first_candidate_when_none_is_v2(self, monkeypatch, tmp_path):
        isolate_discovery(monkeypatch, tmp_path)
        path_v1 = write_fake_at(tmp_path / "path" / "opencode", "v1")
        home_v1 = write_fake_at(tmp_path / "home" / "opencode", "v1")
        monkeypatch.setattr(opencode.shutil, "which", lambda name: str(path_v1))
        monkeypatch.setattr(opencode, "_HOME_BIN", str(home_v1))
        # no V2 anywhere: deterministic first candidate (PATH), not an error
        assert opencode.find_binary() == str(path_v1)

    def test_version_probe_failure_skips_candidate(self, monkeypatch, tmp_path):
        """A candidate that fails --version is skipped, next V2 wins."""
        isolate_discovery(monkeypatch, tmp_path)
        broken = tmp_path / "path" / "opencode"
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
        broken.chmod(broken.stat().st_mode | stat.S_IEXEC)
        home_v2 = write_fake_at(tmp_path / "home" / "opencode", "v2")
        monkeypatch.setattr(opencode.shutil, "which", lambda name: str(broken))
        monkeypatch.setattr(opencode, "_HOME_BIN", str(home_v2))
        assert opencode.find_binary() == str(home_v2)

    def test_returns_none_when_no_candidates_exist(self, monkeypatch, tmp_path):
        isolate_discovery(monkeypatch, tmp_path)
        assert opencode.find_binary() is None


def test_execution_request_normalizes_path_and_rejects_invalid_values(tmp_path):
    request = ExecutionRequest(prompt="do it", cwd=str(tmp_path),
                               agent="coder", session_id="ses_prev")
    assert request.cwd == tmp_path
    assert request.session_id == "ses_prev"
    with pytest.raises(ValueError):
        ExecutionRequest(prompt="", cwd=tmp_path)
    with pytest.raises(ValueError):
        ExecutionRequest(prompt="x", cwd=tmp_path, timeout=0)


def test_execution_result_is_normalized_and_validated():
    result = ExecutionResult(ok=True, status="PASS", exit_code=0,
                             session_id="ses_1", output="ok", detail="done",
                             command=["opencode", "run"], agent="coder",
                             cwd="/tmp/work")
    data = result.to_dict()
    assert data["ok"] is True
    assert data["status"] == "PASS"
    assert data["session_id"] == "ses_1"
    assert data["command"] == ["opencode", "run"]
    with pytest.raises(ValueError):
        ExecutionResult(ok=False, status="OK", exit_code=1,
                        session_id=None, output="", detail="bad")


def test_discovery_reports_v2_capabilities_proven_by_cli(tmp_path):
    fake = write_fake(tmp_path)

    info = opencode.discover(explicit=str(fake))
    assert info["status"] == "supported"
    assert info["version"] == "opencode v2.1.4"
    caps = info["capabilities"]
    assert caps["run"] is True
    assert caps["run_json"] is True
    assert caps["agent_flag"] is True
    assert caps["dir_flag"] is False
    assert caps["session_flag"] is True
    assert caps["session_resume"] is False
    assert caps["standalone_flag"] is True
    assert caps["server"] is True
    assert caps["permissions"] == "unknown"
    assert caps["cancel"] == "process-timeout"
    assert caps["v2"] is True


def test_discovery_marks_v1_binary_as_degraded(tmp_path):
    fake = write_fake(tmp_path, probe="v1")
    info = opencode.discover(explicit=str(fake))
    assert info["status"] == "degraded"
    assert info["version"] == "1.19.4"
    assert info["capabilities"]["v2"] is False
    assert info["capabilities"]["dir_flag"] is True
    assert "V2" in info["detail"] or "v2" in info["detail"]


def test_discovery_is_degraded_when_help_probe_fails(tmp_path):
    fake = write_fake(
        tmp_path,
        """if [ "$1" = "--version" ]; then
  echo "opencode v2.1.4"
  exit 0
fi
exit 3
""",
        probe="none",
    )

    info = opencode.discover(explicit=str(fake))
    assert info["status"] == "degraded"
    assert info["version"] == "opencode v2.1.4"
    assert info["capabilities"]["run_json"] is False
    assert info["capabilities"]["v2"] is True


def test_discovery_handles_blank_version_output(tmp_path):
    fake = write_fake(
        tmp_path,
        """if [ "$1" = "--version" ]; then
  printf "   \\n"
  exit 0
fi
exit 3
""",
        probe="none",
    )

    info = opencode.discover(explicit=str(fake))
    assert info["status"] == "unsupported"
    assert info["version"] is None


def test_run_returns_normalized_result_and_passes_session(tmp_path):
    fake = write_fake(
        tmp_path,
        """echo '{"type":"text","sessionID":"ses_xyz","part":{"type":"text","text":"ran"}}'
exit 0
""",
    )
    work = tmp_path / "work"
    work.mkdir()
    request = ExecutionRequest(prompt="please implement", cwd=work,
                               agent="coder", session_id="ses_prev")
    result = opencode.run(request, binary=str(fake))
    assert isinstance(result, ExecutionResult)
    assert result.ok is True
    assert result.status == "PASS"
    assert result.exit_code == 0
    assert result.session_id == "ses_xyz"
    assert result.agent == "coder"
    assert result.cwd == str(work)
    assert result.command[:4] == [str(fake), "run", "--format", "json"]
    assert "--standalone" in result.command
    assert "--dir" not in result.command
    assert "--session" in result.command
    assert result.command[result.command.index("--session") + 1] == "ses_prev"
    assert result.command[-2:] == ["--", "please implement"]


def test_run_v1_requires_dir_capability(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    fake = write_fake(
        sub,
        """if [ "$1" = "--version" ]; then echo "1.19.4"; exit 0; fi
if [ "$1" = "run" ] && [ "$2" = "--help" ]; then echo "--format json --agent"; exit 0; fi
if [ "$1" = "serve" ] && [ "$2" = "--help" ]; then exit 0; fi
""",
        probe="none",
    )
    result = opencode.run(ExecutionRequest(prompt="x", cwd=tmp_path), binary=str(fake))
    assert result.ok is False
    assert result.status == "BLOCKED"
    assert "dir_flag" in result.detail


def test_run_nonzero_exit_is_fail(tmp_path):
    fake = write_fake(tmp_path, "exit 3\n")
    result = opencode.run(ExecutionRequest(prompt="x", cwd=tmp_path), binary=str(fake))
    assert result.ok is False
    assert result.status == "FAIL"
    assert result.exit_code == 3


def test_run_timeout_returns_fail_detail_and_partial_session(tmp_path):
    fake = write_fake(
        tmp_path,
        """echo '{"type":"text","sessionID":"ses_partial","part":{"type":"text","text":"partial"}}'
sleep 5
""",
    )
    request = ExecutionRequest(prompt="slow", cwd=tmp_path, timeout=1)
    result = opencode.run(request, binary=str(fake))
    assert result.ok is False
    assert result.status == "FAIL"
    assert "timeout" in result.detail
    assert result.session_id == "ses_partial"
    assert "partial" in result.output


def test_run_missing_binary_returns_blocked(tmp_path):
    request = ExecutionRequest(prompt="x", cwd=tmp_path)
    result = opencode.run(request, binary=str(tmp_path / "missing"))
    assert result.ok is False
    assert result.status == "BLOCKED"
    assert "not found" in result.detail


def test_run_blocks_when_required_capability_is_missing(tmp_path):
    fake = write_fake(
        tmp_path,
        """if [ "$1" = "--version" ]; then
  echo "opencode v2.1.4"
  exit 0
fi
if [ "$1" = "run" ] && [ "$2" = "--help" ]; then
  echo "--format json --agent"
  exit 0
fi
if [ "$1" = "serve" ] && [ "$2" = "--help" ]; then
  exit 0
fi
""",
        probe="none",
    )
    result = opencode.run(ExecutionRequest(prompt="x", cwd=tmp_path,
                                           session_id="ses_x"), binary=str(fake))
    assert result.ok is False
    assert result.status == "BLOCKED"
    assert "session_flag" in result.detail


def test_run_validates_extra_args_without_raising(tmp_path):
    fake = write_fake(tmp_path, "exit 0\n")
    request = ExecutionRequest(prompt="x", cwd=tmp_path, extra_args=(1,))
    result = opencode.run(request, binary=str(fake))
    assert result.ok is False
    assert result.status == "BLOCKED"


def test_parse_run_output_extracts_v2_part_text():
    parsed = opencode.parse_run_output(
        '{"type":"text","sessionID":"ses_1","part":{"type":"text","text":"hello"}}'
    )
    assert parsed["session_id"] == "ses_1"
    assert parsed["text"] == "hello"


def test_parse_run_output_extracts_fenced_evidence_from_real_v2_stream():
    """Shape captured from a real opencode v2.1.4 review run: the JSON block is
    escaped inside a ``part.text`` event, not a plain line."""
    stream = (
        '{"type":"step_start","part":{"type":"step-start"}}\n'
        '{"type":"text","sessionID":"ses_real","part":{"type":"text",'
        '"text":"```json\\n{\\"verdict\\": \\"PASS\\", \\"findings\\": []}\\n```"}}\n'
        '{"type":"step_finish","part":{"type":"step-finish"}}'
    )
    parsed = opencode.parse_run_output(stream)
    assert parsed["session_id"] == "ses_real"
    assert parsed["event_lines"] == 3
    from juicer.orchestrator import extract_structured_evidence
    assert extract_structured_evidence(parsed["text"]) == {
        "verdict": "PASS", "findings": []}


def test_parse_run_output_tolerates_invalid_json():
    parsed = opencode.parse_run_output("not json")
    assert parsed == {"session_id": None, "text": "", "event_lines": 1}


def test_opencode_harness_implements_protocol():
    assert isinstance(opencode.OpenCodeHarness(), Harness)


def test_defaults_do_not_use_session_or_auto():
    cmd = opencode.build_command("/bin/opencode", "--auto fake prompt")
    assert "--session" not in cmd
    assert "--auto" not in cmd
    assert "--standalone" in cmd
    assert cmd[-2:] == ["--", "--auto fake prompt"]


def test_session_flag_is_not_used_by_default():
    cmd = opencode.build_command("/bin/opencode", "msg")
    assert "--session" not in cmd
    assert "--auto" not in cmd


def test_version_is_v2_detection():
    assert opencode._version_is_v2("opencode v2.1.4") is True
    assert opencode._version_is_v2("2.0.32") is True
    assert opencode._version_is_v2("1.19.4") is False
    assert opencode._version_is_v2(None) is False
    # false positives of the old substring regex: V1-style versions whose
    # segments contain a ".2.N" part must NOT be classified as V2
    assert opencode._version_is_v2("1.2.4") is False
    assert opencode._version_is_v2("v1.2.0") is False
    assert opencode._version_is_v2("1.2.34") is False
    assert opencode._version_is_v2("opencode 0.2.9") is False
    # major >= 2 is the rule; a future 10.x is not V1 either
    assert opencode._version_is_v2("v2.0.0") is True
    assert opencode._version_is_v2("10.2.3") is True
    assert opencode._version_is_v2("12.0.1") is True
    # non-version garbage never matches
    assert opencode._version_is_v2("dev-build") is False
