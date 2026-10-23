"""OpenCode harness adapter: discovery, command building, JSON parsing.

Real-binary smoke is environment dependent and isolated in
test_opencode_smoke.py; these tests use doubles only.
"""

import json
import stat
from pathlib import Path

from juicer.harness import opencode


def test_find_binary_prefers_env(tmp_path, monkeypatch):
    fake = tmp_path / "opencode"
    fake.write_text("#!/bin/sh\necho 9.9.9\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("OPENCODE_BIN", str(fake))
    monkeypatch.setattr(opencode.shutil, "which", lambda name, path=None: None)
    assert opencode.find_binary() == str(fake)


def test_discover_reports_unsupported_when_missing(monkeypatch):
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(opencode.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(opencode.glob, "glob", lambda pat: [])
    info = opencode.discover()
    assert info["status"] == "unsupported"
    assert info["capabilities"]["run_json"] is False


def test_build_command_shape():
    cmd = opencode.build_command("/bin/opencode", "do the thing", agent="coder")
    assert cmd[:4] == ["/bin/opencode", "run", "--format", "json"]
    assert cmd[4:6] == ["--agent", "coder"]
    assert cmd[-1] == "do the thing"


def test_build_command_pins_dir_for_worktrees():
    cmd = opencode.build_command("/bin/opencode", "msg", agent="coder",
                                 run_dir="/tmp/wt")
    assert cmd[6:8] == ["--dir", "/tmp/wt"]
    assert cmd[-1] == "msg"


def test_parse_run_output_extracts_session_and_text():
    events = [
        {"type": "message", "sessionID": "ses_abc", "message": {"parts": [{"type": "text", "text": "hello"}]}},
        {"type": "step", "session_id": "ses_abc"},
        "not json but has \"sessionID\": \"ses_legacy\"",
    ]
    text = "\n".join(json.dumps(e) if isinstance(e, dict) else e for e in events)
    parsed = opencode.parse_run_output(text)
    assert parsed["session_id"] == "ses_abc"
    assert "hello" in parsed["text"]


def test_execute_uses_fake_binary_and_captures_exit_code(tmp_path):
    fake = tmp_path / "opencode"
    fake.write_text(
        "#!/bin/sh\n"
        "echo '{\"type\":\"message\",\"sessionID\":\"ses_xyz\",\"message\":{\"parts\":[{\"type\":\"text\",\"text\":\"ran\"}]}}'\n"
        "exit ${FAKE_EXIT:-0}\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    work = tmp_path / "work"
    work.mkdir()

    result = opencode.execute("please implement", work, agent="coder", binary=str(fake))
    assert result["ok"] is True
    assert result["exit_code"] == 0
    assert result["session_id"] == "ses_xyz"

    import os
    os.environ["FAKE_EXIT"] = "3"
    try:
        result = opencode.execute("please implement", work, agent="coder", binary=str(fake))
    finally:
        del os.environ["FAKE_EXIT"]
    assert result["ok"] is False
    assert result["exit_code"] == 3


def test_execute_reports_blocked_without_binary(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(opencode.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(opencode.glob, "glob", lambda pat: [])
    result = opencode.execute("x", tmp_path, binary=None)
    assert result["ok"] is False
    assert result["status"] == "BLOCKED"
