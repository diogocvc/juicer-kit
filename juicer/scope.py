"""Scope and isolation policy enforced by the core.

Harness permissions (OpenCode V2 ``permissions[]`` allow/ask/deny) are an
additional execution barrier, never a substitute for the checks here. The core
owns protected paths, scope validation and agent-commit policy regardless of
how permissive the harness is configured (plan §8 / decision D8).
"""

from __future__ import annotations

import fnmatch
import posixpath
from typing import Iterable, List, Sequence, Tuple

from .errors import ScopeViolationError

# Paths a task may never change, even when scope is empty or the harness allows
# everything. These are core-owned state, git internals and classic secret
# shapes. Policy/config can add more; none can remove these.
DEFAULT_PROTECTED_PATHS: Tuple[str, ...] = (
    ".juicer",
    ".git",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "*.jks",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".aws/credentials",
    ".ssh",
)

# Documented templates are safe to commit even though they look like secrets.
SAFE_SECRET_FILES: Tuple[str, ...] = (
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
)

# Only the generic secret globs get the documented-template exemption. A
# directory or operator-declared pattern is never weakened by a filename.
_SAFE_TEMPLATE_PATTERNS: Tuple[str, ...] = (".env", ".env.*")


def _normalize(path: str) -> str:
    raw = str(path).replace("\\", "/").lstrip("/")
    normalized = posixpath.normpath(raw) if raw else raw
    return "" if normalized == "." else normalized


def path_matches(path: str, pattern: str, basename: bool = True) -> bool:
    """True when *path* is matched by a protected/scope *pattern*.

    - glob patterns match the full path; with *basename* they also match the
      basename (``*.pem`` catches ``certs/server.pem``);
    - relative multi-segment patterns also match at any depth
      (``.aws/credentials`` catches ``home/me/.aws/credentials``);
    - a plain name with *basename* matches any path component (``.ssh``);
    - a directory pattern matches the directory itself and everything under
      it, respecting path boundaries (``src/`` never matches ``srcx/evil.py``).

    Scope checks pass ``basename=False``: a scope entry names a repository
    path, not "any file called like this" anywhere in the tree.
    """
    p = _normalize(path)
    raw = str(pattern).replace("\\", "/").lstrip("/").rstrip("/")
    pat = _normalize(raw)
    if not pat or not p:
        return False
    # Full-path glob (``fnmatch`` lets ``*`` cross ``/``).
    if fnmatch.fnmatchcase(p, raw):
        return True
    if p == pat or p.startswith(pat + "/"):
        return True
    if basename and "/" in pat and p.endswith("/" + pat):
        return True
    if basename:
        base = p.rsplit("/", 1)[-1]
        if fnmatch.fnmatchcase(base, raw):
            return True
        if "/" not in pat and fnmatch.fnmatchcase(base, pat):
            return True
        if "/" not in pat and pat in p.split("/"):
            return True
    return False


def _as_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def protected_patterns(task: dict, config: dict = None) -> List[str]:
    """Core defaults plus policy-declared protected paths (never fewer)."""
    patterns = list(DEFAULT_PROTECTED_PATHS)
    scope = (task or {}).get("scope") or {}
    policy = (task or {}).get("approval_policy") or {}
    for source in (
        scope.get("protected_paths"),
        scope.get("protected"),
        policy.get("protected_paths"),
        (config or {}).get("protected_paths"),
    ):
        patterns.extend(_as_list(source))
    # Preserve order, drop duplicates.
    seen = set()
    out = []
    for pat in patterns:
        if pat not in seen:
            out.append(pat)
            seen.add(pat)
    return out


def is_safe_template(path: str) -> bool:
    basename = _normalize(path).rsplit("/", 1)[-1]
    return basename in SAFE_SECRET_FILES


def protected_violations(task: dict, changed_files: Iterable[str],
                         config: dict = None) -> List[Tuple[str, str]]:
    """Return ``(path, pattern)`` pairs for protected files in the change set.

    A documented template (``.env.example``) is exempt only from the generic
    secret globs. An explicit/directory policy pattern still protects it.
    """
    patterns = protected_patterns(task, config)
    violations: List[Tuple[str, str]] = []
    for path in changed_files:
        matched = [pat for pat in patterns if path_matches(path, pat)]
        if not matched:
            continue
        safe = is_safe_template(path)
        unsafe = [pat for pat in matched
                  if not (safe and pat in _SAFE_TEMPLATE_PATTERNS)]
        if unsafe:
            violations.append((path, unsafe[0]))
    return violations


def check_protected(task: dict, changed_files: Sequence[str],
                    config: dict = None) -> None:
    """Raise ``ScopeViolationError`` when a protected path was changed."""
    violations = protected_violations(task, changed_files, config)
    if violations:
        rendered = ", ".join("%s (%s)" % (path, pat) for path, pat in violations)
        raise ScopeViolationError(
            "task %s changed protected path(s): %s"
            % ((task or {}).get("id", "?"), rendered))


def agent_commits_allowed(task: dict, config: dict = None) -> bool:
    """Whether the task policy explicitly permits agent-created commits.

    Default is False: an agent commit fails the run, because the coordinator
    owns evidence capture and commits (plan §8). The opt-in surface is the
    task field or its ``approval_policy``; a global config switch is honoured
    only when it is literally ``true``.
    """
    task = task or {}
    if task.get("allow_agent_commits") is True:
        return True
    policy = task.get("approval_policy") or {}
    if policy.get("allow_agent_commits") is True:
        return True
    return (config or {}).get("allow_agent_commits") is True
