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
    monkeypatch.setattr(opencode, "_HOME_BIN", "/nonexistent/opencode")
    info = opencode.discover()
    assert info["status"] == "unsupported"
    assert info["capabilities"]["run_json"] is False


def test_build_command_shape():
    cmd = opencode.build_command("/bin/opencode", "do the thing", agent="coder")
    assert cmd[:4] == ["/bin/opencode", "run", "--format", "json"]
    assert cmd[4:6] == ["--agent", "coder"]
    assert "--standalone" in cmd
    assert "--dir" not in cmd
    assert cmd[-1] == "do the thing"


def test_build_command_pins_dir_only_when_requested():
    cmd = opencode.build_command("/bin/opencode", "msg", agent="coder",
                                 run_dir="/tmp/wt", standalone=False)
    assert "--dir" in cmd
    assert cmd[cmd.index("--dir") + 1] == "/tmp/wt"
    assert "--standalone" not in cmd
    assert cmd[-1] == "msg"


def test_parse_run_output_extracts_session_and_text():
    events = [
        {"type": "text", "sessionID": "ses_abc", "part": {"type": "text", "text": "hello"}},
        {"type": "message", "sessionID": "ses_legacy", "message": {"parts": [{"type": "text", "text": "legacy"}]}},
        {"type": "step", "session_id": "ses_abc"},
        "not json but has \"sessionID\": \"ses_regex\"",
    ]
    text = "\n".join(json.dumps(e) if isinstance(e, dict) else e for e in events)
    parsed = opencode.parse_run_output(text)
    assert parsed["session_id"] == "ses_abc"
    assert "hello" in parsed["text"]
    assert "legacy" in parsed["text"]


def test_execute_uses_fake_binary_and_captures_exit_code(tmp_path):
    fake = tmp_path / "opencode"
    fake.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then echo opencode v2.2.7; exit 0; fi\n"
        "if [ \"$1\" = \"run\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  echo '--format json --agent coder --session ses_x --standalone'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"serve\" ] && [ \"$2\" = \"--help\" ]; then echo serve; exit 0; fi\n"
        "echo '{\"type\":\"text\",\"sessionID\":\"ses_xyz\",\"part\":{\"type\":\"text\",\"text\":\"ran\"}}'\n"
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
    assert "--standalone" in result["command"]
    assert "--dir" not in result["command"]

    import os
    os.environ["FAKE_EXIT"] = "3"
    try:
        result = opencode.execute("please implement", work, agent="coder", binary=str(fake))
    finally:
        del os.environ["FAKE_EXIT"]
    assert result["ok"] is False
    assert result["exit_code"] == 3


def test_execute_pins_pwd_to_workspace(tmp_path, monkeypatch):
    """OpenCode resolves the project from PWD; the adapter must set both.

    A subprocess cwd alone leaves the inherited PWD pointing at the caller's
    repository, so an agent could edit the wrong tree. The fake is Python so
    it reads the environment directly; /bin/sh may recompute PWD itself.
    The relative cwd also checks that the adapter resolves it before use.
    """
    fake = tmp_path / "opencode"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:1] == ['--version']:\n"
        "    print('opencode v2.2.7'); sys.exit(0)\n"
        "if args[:2] == ['run', '--help']:\n"
        "    print('--format json --agent coder --standalone'); sys.exit(0)\n"
        "if args[:2] == ['serve', '--help']:\n"
        "    print('serve'); sys.exit(0)\n"
        "with open('pwd.txt', 'w', encoding='utf-8') as fh:\n"
        "    fh.write(os.environ['PWD'])\n"
        "print('{\"type\":\"text\",\"sessionID\":\"ses_pwd\","
        "\"part\":{\"type\":\"text\",\"text\":\"ok\"}}')\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.chdir(tmp_path)
    work = Path("work")
    work.mkdir()

    result = opencode.execute("please implement", work, agent="coder",
                              binary=str(fake))
    assert result["ok"] is True
    assert result["cwd"] == str(work.resolve())
    assert (work / "pwd.txt").read_text(encoding="utf-8") == str(work.resolve())


def test_execute_reports_blocked_without_binary(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(opencode.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(opencode.glob, "glob", lambda pat: [])
    monkeypatch.setattr(opencode, "_HOME_BIN", "/nonexistent/opencode")
    result = opencode.execute("x", tmp_path, binary=None)
    assert result["ok"] is False
    assert result["status"] == "BLOCKED"
