"""Local persistence primitives: atomic writes, locks, revision fences, events.

Patterns extracted from the archived v2.5.0 ``bin/juicer`` (state_lock,
_atomic_write_text, revision fence) and simplified for the 4.0.0 core.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .errors import PathConfinementError, StaleRevisionError

try:  # pragma: no cover - platform specific
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def confine(root: Path, path: Path) -> Path:
    """Resolve *path* and require it to live under *root*."""
    root = Path(root).resolve()
    resolved = (root / Path(path)).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if resolved != root and root not in resolved.parents:
        raise PathConfinementError("path escapes root: %s" % resolved)
    return resolved


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def read_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


@contextmanager
def state_lock(root: Path, name: str = "state"):
    """Advisory exclusive lock; degrades to a no-op without fcntl."""
    ensure_dir(root)
    lock_path = Path(root) / ("%s.lock" % name)
    fh = open(lock_path, "a+")
    try:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def bump_revision(record: dict) -> int:
    rev = int(record.get("revision", 0)) + 1
    record["revision"] = rev
    record["updated_at"] = utc_now()
    return rev


def fenced_update(path: Path, mutator, expect_revision=None, create=None):
    """Read-modify-write with an optimistic revision fence.

    *mutator* receives the current record and mutates it in place.
    *create* is used when the file does not exist yet.
    Returns the updated record.
    """
    current = read_json(path, default=None)
    if current is None:
        if create is None:
            raise FileNotFoundError(str(path))
        current = create
    elif expect_revision is not None and int(current.get("revision", 0)) != int(expect_revision):
        raise StaleRevisionError(
            "stale revision for %s: expected %s, found %s"
            % (path, expect_revision, current.get("revision"))
        )
    mutator(current)
    bump_revision(current)
    write_json(path, current)
    return current


def append_event(events_path: Path, event: dict) -> None:
    """Append one JSONL event (append-only audit trail)."""
    events_path = Path(events_path)
    ensure_dir(events_path.parent)
    line = json.dumps(event, sort_keys=True) + "\n"
    with open(events_path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def read_events(events_path: Path):
    events_path = Path(events_path)
    if not events_path.exists():
        return []
    out = []
    with open(events_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
