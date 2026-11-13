"""Minimal contract between the Juicer core and an agent harness.

The contract is deliberately smaller than any harness API:

* ``discover`` reports only capabilities that were actually probed.
* ``run`` executes one prompt in one workspace and normalizes the outcome.

The core owns mission state, gates, evidence, scope and integration. Harness
adapters only execute and report; they never decide whether a task is done.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable


HARNESS_STATUSES = ("PASS", "FAIL", "BLOCKED")


@dataclass(frozen=True)
class ExecutionRequest:
    """One harness execution request.

    ``session_id`` is optional because not every harness version supports
    resuming a session. Adapters that do not support it must report that
    capability as false instead of silently ignoring it.
    """

    prompt: str
    cwd: Path
    agent: Optional[str] = None
    timeout: int = 900
    session_id: Optional[str] = None
    extra_args: Tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(self.cwd, (str, Path)) or not str(self.cwd):
            raise ValueError("cwd must be a non-empty path")
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        if self.agent is not None and not isinstance(self.agent, str):
            raise ValueError("agent must be a string or None")
        if self.session_id is not None and not isinstance(self.session_id, str):
            raise ValueError("session_id must be a string or None")
        if self.extra_args is None:
            object.__setattr__(self, "extra_args", ())
        elif not isinstance(self.extra_args, tuple):
            object.__setattr__(self, "extra_args", tuple(self.extra_args))
        if not isinstance(self.cwd, Path):
            object.__setattr__(self, "cwd", Path(self.cwd))


@dataclass
class ExecutionResult:
    """Normalized result returned by every harness adapter."""

    ok: bool
    status: str
    exit_code: Optional[int]
    session_id: Optional[str]
    output: str
    detail: str
    command: Optional[List[str]] = None
    agent: Optional[str] = None
    cwd: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.ok, bool):
            raise ValueError("ok must be a boolean")
        if self.status not in HARNESS_STATUSES:
            raise ValueError("status must be one of %s" % (HARNESS_STATUSES,))
        if self.ok != (self.status == "PASS"):
            raise ValueError("ok must be true exactly when status is PASS")

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@runtime_checkable
class Harness(Protocol):
    """Internal adapter protocol used by the orchestration core."""

    name: str

    def discover(self, explicit: Optional[str] = None, timeout: int = 20) -> Dict[str, object]:
        ...

    def run(self, request: ExecutionRequest, binary: Optional[str] = None) -> ExecutionResult:
        ...
