"""Harness adapter for the locally installed OpenCode CLI (MVP target: V2).

Validated against OpenCode 2.x in this environment (see STATUS.md). The core
model does not depend on the OpenCode version; only this integration layer
does. The adapter implements the minimal ``Harness`` contract in
``juicer.harness.contract``.

V2 notes (measured on 2.1.4):

* ``run`` has no ``--dir``; the process CWD selects the project/worktree.
* ``--standalone`` runs a private server and is the default here so concurrent
  worktree executions do not share session state.
* Events are NDJSON with ``sessionID`` and a top-level ``part`` (text parts
  carry assistant-visible text).
* ``--auto`` exists but is never added by default.

A V1 binary may still be discovered for diagnostics; it is not the MVP target
and ``discover`` reports ``v2: false`` for it.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .contract import ExecutionRequest, ExecutionResult

HARNESS_NAME = "opencode"

_ZED_GLOB = os.path.expanduser(
    "~/Library/Application Support/Zed/external_agents/registry/opencode/*/opencode"
)
_HOME_BIN = os.path.expanduser("~/.opencode/bin/opencode")
_SESSION_RE = re.compile(r'"sessionID"\s*:\s*"([^"]+)"')
# Explicit major-version parse: any version whose MAJOR component is >= 2 is
# V2. A naive substring search would misclassify "1.2.4" or "10.2.3" as V2.
_VERSION_MAJOR_RE = re.compile(r"(?:^|\s)v?(\d+)\.", re.IGNORECASE)


def _version_is_v2(version: Optional[str]) -> bool:
    if not version:
        return False
    m = _VERSION_MAJOR_RE.search(version.strip())
    return bool(m and int(m.group(1)) >= 2)


def find_binary(explicit: Optional[str] = None) -> Optional[str]:
    """Locate an OpenCode binary, preferring V2 when scanning defaults.

    Order: explicit, OPENCODE_BIN, then PATH / ~/.opencode/bin / Zed registry
    with a V2-looking binary preferred among those defaults.
    """
    if explicit:
        return explicit if Path(explicit).exists() else None
    env = os.environ.get("OPENCODE_BIN")
    if env and Path(env).exists():
        return env
    candidates = []
    which = shutil.which("opencode")
    if which:
        candidates.append(which)
    if Path(_HOME_BIN).exists():
        candidates.append(_HOME_BIN)
    candidates.extend(sorted(glob.glob(_ZED_GLOB), reverse=True))
    existing = []
    seen = set()
    for cand in candidates:
        if cand and cand not in seen and Path(cand).exists():
            existing.append(cand)
            seen.add(cand)
    if not existing:
        return None
    if len(existing) == 1:
        return existing[0]
    for cand in existing:
        try:
            proc = subprocess.run([cand, "--version"], capture_output=True,
                                  text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        version = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if proc.returncode == 0 and _version_is_v2(version.splitlines()[0] if version else None):
            return cand
    return existing[0]


def _empty_capabilities() -> Dict[str, object]:
    return {
        "version_probe": False,
        "run": False,
        "run_json": False,
        "agent_flag": False,
        "dir_flag": False,
        "session_flag": False,
        "session_resume": False,
        "continue_flag": False,
        "standalone_flag": False,
        "server": False,
        "auto_flag": False,
        "permissions": "unknown",
        "cancel": "process-timeout",
        "events": "none",
        "worktree": "git-cli",
        "v2": False,
    }


def _probe_help(binary: str, args: List[str], timeout: int) -> Tuple[bool, str]:
    try:
        proc = subprocess.run([binary] + args, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def discover(explicit: Optional[str] = None, timeout: int = 20) -> dict:
    """Report harness capabilities that were actually probed.

    ``--version`` proves the binary exists and whether it is V2. ``run
    --help`` proves which CLI flags are available. It does not prove
    model/provider availability, so a successful smoke execution remains a
    separate check.
    """
    binary = find_binary(explicit)
    caps = _empty_capabilities()
    if binary is None:
        return {
            "harness": HARNESS_NAME,
            "binary": None,
            "version": None,
            "status": "unsupported",
            "detail": "opencode binary not found (OPENCODE_BIN, PATH, ~/.opencode/bin, Zed registry)",
            "capabilities": caps,
        }
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True,
                              timeout=timeout)
        lines = (proc.stdout or proc.stderr).strip().splitlines()
        version = lines[0] if lines else None
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "harness": HARNESS_NAME, "binary": binary, "version": None,
            "status": "unsupported", "detail": "version probe failed: %s" % exc,
            "capabilities": caps,
        }
    if not version or proc.returncode != 0:
        return {
            "harness": HARNESS_NAME, "binary": binary, "version": version,
            "status": "unsupported", "detail": "version probe returned %s" % proc.returncode,
            "capabilities": caps,
        }

    caps["version_probe"] = True
    caps["v2"] = _version_is_v2(version)
    run_ok, run_help = _probe_help(binary, ["run", "--help"], timeout)
    if run_ok:
        caps.update({
            "run": True,
            "run_json": "--format" in run_help and "json" in run_help,
            "agent_flag": "--agent" in run_help,
            "dir_flag": "--dir" in run_help,
            "session_flag": "--session" in run_help,
            "continue_flag": "--continue" in run_help,
            "standalone_flag": "--standalone" in run_help,
            "auto_flag": "--auto" in run_help,
        })
        # Flag presence is not proof that session resumption works. Keep this
        # false until a real resume probe exists.
        caps["session_resume"] = False
        caps["events"] = "jsonl-stream" if caps["run_json"] else "none"
    serve_ok, serve_help = _probe_help(binary, ["serve", "--help"], timeout)
    caps["server"] = bool(serve_ok and serve_help.strip())

    if not run_ok:
        status = "degraded"
        detail = "binary responds to --version; run --help probe failed"
    elif not caps["run_json"]:
        status = "degraded"
        detail = "binary responds to --version; run --format json not detected"
    elif not caps["v2"]:
        status = "degraded"
        detail = (
            "binary responds to --version but is not V2 (%s); MVP target is OpenCode 2.x"
            % version
        )
    elif not caps["standalone_flag"] and not caps["dir_flag"]:
        status = "degraded"
        detail = (
            "V2 binary lacks both --standalone and --dir; worktree isolation not pinned"
        )
    else:
        status = "supported"
        detail = "V2 binary responds to --version and run --help"
    return {
        "harness": HARNESS_NAME,
        "binary": binary,
        "version": version,
        "status": status,
        "detail": detail,
        "capabilities": caps,
    }


def build_command(binary: str, message: str, agent: Optional[str] = None,
                  use_json: bool = True, run_dir: Optional[str] = None,
                  session_id: Optional[str] = None,
                  standalone: bool = True) -> List[str]:
    cmd = [binary, "run"]
    if use_json:
        cmd += ["--format", "json"]
    if agent:
        cmd += ["--agent", agent]
    if session_id:
        cmd += ["--session", session_id]
    if standalone:
        # Private server keeps concurrent worktree runs from sharing sessions.
        cmd += ["--standalone"]
    if run_dir:
        # V1 only: V2 has no --dir; callers pin the workspace via process CWD.
        # Passing the flag when the binary does not support it would fail, so
        # only include it when the caller explicitly requests a dir pin and
        # the binary is expected to accept it.
        cmd += ["--dir", str(run_dir)]
    cmd += ["--", message]
    return cmd


def parse_run_output(text: str) -> dict:
    """Extract session id and assistant-visible text from JSON event stream.

    Supports V2 events (``part`` at top level) and the older V1 message/parts
    shape still seen in fixtures.
    """
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
            part = obj.get("part")
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(str(part.get("text", "")))
    return {"session_id": session_id, "text": "\n".join(texts), "event_lines": events}


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run(request: ExecutionRequest, binary: Optional[str] = None) -> ExecutionResult:
    """Execute one request and return a normalized result.

    Affirmative agent text is never proof of success. Callers must use the
    exit code, deterministic checks and git evidence.

    The subprocess runs with ``cwd=request.cwd`` so V2 associates the correct
    project/worktree without ``--dir``.
    """
    binary = binary or find_binary()
    if binary is None:
        return ExecutionResult(
            ok=False, status="BLOCKED", exit_code=None, session_id=None,
            output="", detail="opencode binary not found", command=None,
            agent=request.agent, cwd=str(request.cwd),
        )
    info = discover(explicit=binary)
    if info["status"] == "unsupported":
        return ExecutionResult(
            ok=False, status="BLOCKED", exit_code=None, session_id=None,
            output="", detail="opencode harness unavailable: %s" % info["detail"],
            command=None, agent=request.agent, cwd=str(request.cwd),
        )
    caps = info["capabilities"]
    is_v2 = bool(caps.get("v2"))
    required = ["run", "run_json"]
    if request.agent:
        required.append("agent_flag")
    if request.session_id:
        required.append("session_flag")
    # V1 needs --dir to pin worktrees; V2 pins via process CWD instead.
    if not is_v2:
        required.append("dir_flag")
    missing = [name for name in required if not caps.get(name)]
    if missing:
        return ExecutionResult(
            ok=False, status="BLOCKED", exit_code=None, session_id=None,
            output="", detail="opencode missing capabilities: %s" % ", ".join(missing),
            command=None, agent=request.agent, cwd=str(request.cwd),
        )
    use_standalone = bool(caps.get("standalone_flag"))
    use_dir = (not is_v2) and bool(caps.get("dir_flag"))
    cmd = build_command(
        binary, request.prompt, agent=request.agent,
        run_dir=str(request.cwd) if use_dir else None,
        session_id=request.session_id,
        standalone=use_standalone,
    )
    if request.extra_args:
        cmd = cmd[:-2] + list(request.extra_args) + cmd[-2:]
    try:
        proc = subprocess.run(cmd, cwd=str(request.cwd), capture_output=True,
                              text=True, timeout=request.timeout)
    except subprocess.TimeoutExpired as exc:
        out = _text(exc.stdout)
        err = _text(exc.stderr)
        combined = out + ("\n" + err if err else "")
        parsed = parse_run_output(out)
        return ExecutionResult(
            ok=False, status="FAIL", exit_code=None,
            session_id=parsed["session_id"], output=combined,
            detail="timeout after %ss" % request.timeout,
            command=cmd, agent=request.agent, cwd=str(request.cwd),
        )
    except (OSError, ValueError, TypeError) as exc:
        return ExecutionResult(
            ok=False, status="BLOCKED", exit_code=None, session_id=None,
            output="", detail=str(exc), command=cmd,
            agent=request.agent, cwd=str(request.cwd),
        )
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    parsed = parse_run_output(proc.stdout or "")
    ok = proc.returncode == 0
    return ExecutionResult(
        ok=ok,
        status="PASS" if ok else "FAIL",
        exit_code=proc.returncode,
        session_id=parsed["session_id"],
        output=combined,
        detail="opencode run exited %s" % proc.returncode,
        command=cmd,
        agent=request.agent,
        cwd=str(request.cwd),
    )


def execute(message: str, cwd: Path, agent: Optional[str] = None,
            binary: Optional[str] = None, timeout: int = 900,
            extra_args: Optional[List[str]] = None,
            session_id: Optional[str] = None) -> dict:
    """Compatibility wrapper around the normalized ``run`` contract."""
    request = ExecutionRequest(
        prompt=message, cwd=Path(cwd), agent=agent, timeout=timeout,
        session_id=session_id, extra_args=tuple(extra_args or ()),
    )
    return run(request, binary=binary).to_dict()


class OpenCodeHarness:
    """Adapter implementing ``juicer.harness.contract.Harness`` for OpenCode V2."""

    name = HARNESS_NAME

    def discover(self, explicit: Optional[str] = None, timeout: int = 20) -> dict:
        return discover(explicit=explicit, timeout=timeout)

    def run(self, request: ExecutionRequest, binary: Optional[str] = None) -> ExecutionResult:
        return run(request, binary=binary)
