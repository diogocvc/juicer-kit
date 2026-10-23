"""Deterministic checks: run project-configured commands, classify results.

Statuses: PASS, FAIL, BLOCKED, NOT RUN. NOT RUN never equals PASS.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .model import CHECK_STATUS, new_check_result
from .state import atomic_write_text, ensure_dir


def classify_exit(returncode: Optional[int], timed_out: bool = False) -> str:
    if timed_out:
        return "FAIL"
    if returncode is None:
        return "BLOCKED"
    return "PASS" if returncode == 0 else "FAIL"


def run_command(command: List[str], cwd: Path, timeout: int = 600,
                env=None) -> dict:
    """Execute one command; never raises for command failures."""
    cwd = Path(cwd)
    if not command:
        return {"status": "BLOCKED", "exit_code": None, "output": "empty command", "timed_out": False}
    exe = command[0]
    if shutil.which(exe, path=None) is None and not Path(exe).exists():
        return {"status": "BLOCKED", "exit_code": None,
                "output": "executable not found: %s" % exe, "timed_out": False}
    if not cwd.exists():
        return {"status": "BLOCKED", "exit_code": None,
                "output": "working directory missing: %s" % cwd, "timed_out": False}
    try:
        proc = subprocess.run(
            list(command), cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "") if isinstance(exc.stdout, str) else ""
        return {"status": "FAIL", "exit_code": None,
                "output": out + "\ntimeout after %ss" % timeout, "timed_out": True}
    except OSError as exc:
        return {"status": "BLOCKED", "exit_code": None, "output": str(exc), "timed_out": False}
    output = (proc.stdout or "") + (proc.stderr or "")
    return {"status": classify_exit(proc.returncode), "exit_code": proc.returncode,
            "output": output, "timed_out": False}


def run_check(check_id: str, command: List[str], task_id: str, cwd: Path,
              commit: Optional[str] = None, timeout: int = 600,
              log_dir: Optional[Path] = None, phase: str = "pre_merge") -> dict:
    result = run_command(command, cwd, timeout=timeout)
    log_ref = None
    if log_dir is not None:
        ensure_dir(log_dir)
        log_path = Path(log_dir) / ("%s.log" % check_id)
        atomic_write_text(log_path, result.get("output") or "")
        log_ref = str(log_path)
    summary = (result.get("output") or "").strip().splitlines()
    summary_text = summary[-1] if summary else ""
    return new_check_result(
        check_id=check_id, task_id=task_id, command=command,
        status=result["status"], commit=commit, exit_code=result["exit_code"],
        log_ref=log_ref, summary=summary_text[:300], phase=phase,
    )


def run_checks(checks, task_id: str, cwd: Path, commit: Optional[str] = None,
               timeout: int = 600, log_dir: Optional[Path] = None,
               phase: str = "pre_merge") -> List[dict]:
    out = []
    for spec in checks:
        out.append(run_check(
            spec["id"], spec["command"], task_id, cwd, commit=commit,
            timeout=timeout, log_dir=log_dir, phase=phase,
        ))
    return out
