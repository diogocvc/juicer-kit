"""Harness adapter for the locally installed OpenCode CLI.

Validated against the binary actually present in the environment (see
STATUS.md). The reference documents target "OpenCode 2.0"; this environment
provides 1.19.4 — only the integration layer adapts, the core model does not.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

HARNESS_NAME = "opencode"

_ZED_GLOB = os.path.expanduser(
    "~/Library/Application Support/Zed/external_agents/registry/opencode/*/opencode"
)
_SESSION_RE = re.compile(r'"sessionID"\s*:\s*"([^"]+)"')


def find_binary(explicit: Optional[str] = None) -> Optional[str]:
    candidates = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("OPENCODE_BIN")
    if env:
        candidates.append(env)
    which = shutil.which("opencode")
    if which:
        candidates.append(which)
    candidates.extend(sorted(glob.glob(_ZED_GLOB), reverse=True))
    for cand in candidates:
        if cand and Path(cand).exists():
            return cand
    return None


def discover(explicit: Optional[str] = None, timeout: int = 20) -> dict:
    """Report harness capability with an explicit supported/unknown status."""
    binary = find_binary(explicit)
    if binary is None:
        return {
            "harness": HARNESS_NAME,
            "binary": None,
            "version": None,
            "status": "unsupported",
            "detail": "opencode binary not found (OPENCODE_BIN, PATH, Zed registry)",
            "capabilities": {"run_json": False, "agent_flag": False},
        }
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True,
                              timeout=timeout)
        version = (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr) else None
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "harness": HARNESS_NAME, "binary": binary, "version": None,
            "status": "unsupported", "detail": "version probe failed: %s" % exc,
            "capabilities": {"run_json": False, "agent_flag": False},
        }
    return {
        "harness": HARNESS_NAME,
        "binary": binary,
        "version": version,
        "status": "supported",
        "detail": "binary responds to --version",
        "capabilities": {"run_json": True, "agent_flag": True, "worktree": "git-cli"},
    }


def build_command(binary: str, message: str, agent: Optional[str] = None,
                  use_json: bool = True, run_dir: Optional[str] = None) -> List[str]:
    cmd = [binary, "run"]
    if use_json:
        cmd += ["--format", "json"]
    if agent:
        cmd += ["--agent", agent]
    if run_dir:
        # OpenCode resolves the project root itself and may walk up past a
        # git worktree into the main checkout; --dir pins the workspace.
        cmd += ["--dir", str(run_dir)]
    cmd.append(message)
    return cmd


def parse_run_output(text: str) -> dict:
    """Extract session id and assistant-visible text from JSON event stream."""
    session_id = None
    texts = []
    events = 0
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        events += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            m = _SESSION_RE.search(line)
            if m:
                session_id = session_id or m.group(1)
            continue
        if isinstance(obj, dict):
            for key in ("sessionID", "session_id", "sessionId"):
                if isinstance(obj.get(key), str):
                    session_id = session_id or obj[key]
            msg = obj.get("message")
            if isinstance(msg, dict):
                parts = msg.get("parts") or []
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        texts.append(str(part.get("text", "")))
    return {"session_id": session_id, "text": "\n".join(texts), "event_lines": events}


def execute(message: str, cwd: Path, agent: Optional[str] = None,
            binary: Optional[str] = None, timeout: int = 900,
            extra_args: Optional[List[str]] = None) -> dict:
    """Run one OpenCode task; capture exit code, output and session id.

    Never treats affirmative agent text as proof: callers must rely on the
    returned exit code plus deterministic checks and git evidence.
    """
    binary = binary or find_binary()
    if binary is None:
        return {
            "ok": False, "status": "BLOCKED", "exit_code": None,
            "detail": "opencode binary not found", "session_id": None,
            "output": "", "command": None,
        }
    cmd = build_command(binary, message, agent=agent, run_dir=str(cwd))
    if extra_args:
        cmd = cmd[:-1] + list(extra_args) + [cmd[-1]]
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        return {
            "ok": False, "status": "FAIL", "exit_code": None,
            "detail": "timeout after %ss" % timeout, "session_id": None,
            "output": out, "command": cmd,
        }
    except OSError as exc:
        return {
            "ok": False, "status": "BLOCKED", "exit_code": None,
            "detail": str(exc), "session_id": None, "output": "", "command": cmd,
        }
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    parsed = parse_run_output(proc.stdout or "")
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "exit_code": proc.returncode,
        "detail": "opencode run exited %s" % proc.returncode,
        "session_id": parsed["session_id"],
        "output": combined,
        "command": cmd,
        "agent": agent,
        "cwd": str(cwd),
    }
