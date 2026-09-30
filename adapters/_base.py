"""Shared base class and helpers for Juicer Kit harness adapters.

Adapters are thin translators. They read canonical state from

    .juicer/   agents/   .agents/skills/   AGENTS.md

and write only harness-native mirrors. They never move workflow state.

This module is importable by any adapter (project or kit) because the
loader in bin/juicer puts this directory on sys.path before executing
an adapter module.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

FRONTMATTER_DELIM = "---"
ACCESS_LEVELS = ("read-only", "edit", "full")
TIER_LEVELS = ("hot", "warm", "cold")
WORKER_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


@dataclass
class Ctx:
    """Execution context handed to every adapter method."""

    root: Path
    kit: Path
    state_dir: str = ".juicer"
    skills_source: str = ".agents/skills"
    agents_source: str = "agents"
    options: Dict[str, object] = field(default_factory=dict)


@dataclass
class Change:
    """A single file operation produced by sync/install."""

    path: Path
    action: str  # "write" | "delete" | "skip"
    reason: str = ""
    digest: str = ""       # sha256 of the resulting content
    manifest: bool = True  # False => project-owned (e.g. AGENTS.md)


@dataclass
class Worker:
    """A canonical worker contract parsed from agents/*.md."""

    name: str
    path: Path
    frontmatter: Dict[str, str]
    body: str


def read_frontmatter(path):
    """Parse the simple ``key: value`` frontmatter of a canonical file.

    Returns ``(frontmatter_dict, body)``. No YAML library is required;
    canonical worker files only use single-line scalar values.
    """
    text = path.read_text()
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return {}, text
    data = {}
    closing = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIM:
            closing = index
            break
        if ":" in line:
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip()
    if closing is None:
        return {}, text
    body = "\n".join(lines[closing + 1:]).lstrip("\n")
    return data, body


def render_frontmatter(mapping):
    """Render ``mapping`` as frontmatter text ending with a newline.

    Values containing newlines (nested mappings/lists) are emitted as
    ``key:`` followed by the pre-indented block.
    """
    lines = [FRONTMATTER_DELIM]
    for key, value in mapping.items():
        text = str(value)
        if "\n" in text:
            lines.append(f"{key}:{text}")
        else:
            lines.append(f"{key}: {text}")
    lines.append(FRONTMATTER_DELIM)
    return "\n".join(lines) + "\n"


def worker_access(worker):
    """Canonical access level of a worker: read-only, edit or full."""
    value = worker.frontmatter.get("access", "edit")
    if value not in ACCESS_LEVELS:
        raise ValueError(
            f"worker {worker.name}: invalid access {value!r} "
            f"(expected one of {', '.join(ACCESS_LEVELS)})"
        )
    return value


def worker_tier(worker):
    """Canonical invocation tier of a worker: hot, warm or cold."""
    value = worker.frontmatter.get("tier", "warm")
    if value not in TIER_LEVELS:
        raise ValueError(
            f"worker {worker.name}: invalid tier {value!r} "
            f"(expected one of {', '.join(TIER_LEVELS)})"
        )
    return value


def provenance(worker, canonical="agents"):
    """Source path and content hash used to mark generated files."""
    digest = hashlib.sha256(worker.body.encode("utf-8")).hexdigest()[:12]
    return f"{canonical}/{worker.name}.md sha256:{digest}"


def render_agent(frontmatter, worker, canonical="agents"):
    """Render a harness agent file: frontmatter, provenance, canonical body.

    Canonical frontmatter is never copied; only the body travels.
    """
    return (
        render_frontmatter(frontmatter)
        + f"\n<!-- juicer-kit: generated from {provenance(worker, canonical)} -->\n\n"
        + worker.body.rstrip()
        + "\n"
    )


def sha256_file(path):
    """Hex sha256 of a file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def confine_path(root, path, what="path"):
    """Resolve ``path`` and require it to stay strictly inside ``root``.

    Rejects the root itself, anything that escapes after symlink
    resolution, and (via :func:`confine_manifest_entry`) absolute or
    ``..``-bearing manifest entries. Raises ``ValueError`` so the CLI can
    turn it into a clean failure.

    This is the *root* boundary. It is the right check for the CLI's own
    writes (which legitimately target ``.juicer/``). Adapter output must
    go through :func:`confine_generated` instead, which additionally
    protects workflow and VCS ownership.
    """
    root_resolved = Path(root).resolve()
    resolved = Path(path).resolve()
    if resolved == root_resolved:
        raise ValueError(f"{what} {path} resolves to the project root itself")
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        raise ValueError(
            f"{what} {path} resolves outside the project root ({resolved})"
        ) from None
    return resolved


# Directories and files the workflow core owns. No adapter may write or
# record them, so neither generated output nor a tampered manifest can
# reach state, gates or version-control configuration.
PROTECTED_TOP_LEVEL = (".juicer", ".git")
PROTECTED_FILES = (".gitignore",)


def confine_generated(root, path, what="generated path"):
    """Root containment plus ownership: adapters never touch core/VCS files.

    This implements the rule documented in ``docs/adapter-contract.md``:
    adapters never write outside the project root *and never into*
    ``.juicer/``. ``.git/`` and ``.gitignore`` are excluded for the same
    reason — generated mirrors must not alter how the repository tracks
    files.
    """
    root_resolved = Path(root).resolve()
    resolved = confine_path(root_resolved, path, what=what)
    parts = resolved.relative_to(root_resolved).parts
    if parts[0] in PROTECTED_TOP_LEVEL:
        raise ValueError(
            f"{what} {path} targets {parts[0]}/, which is owned by the "
            "workflow core and is never adapter-generated"
        )
    if len(parts) == 1 and parts[0] in PROTECTED_FILES:
        raise ValueError(
            f"{what} {path} targets {parts[0]}, which is project-owned "
            "and is never adapter-generated"
        )
    return resolved


def confine_manifest_entry(root, rel, adapter_id=""):
    """Strict form for manifest entries: relative, no ``..``, inside root.

    Additionally rejects core/VCS paths, so a planted manifest cannot be
    used to delete ``.juicer/`` state or version-control configuration.
    """
    where = f"adapter {adapter_id!r} manifest entry" if adapter_id else "manifest entry"
    entry = Path(rel)
    if entry.is_absolute():
        raise ValueError(f"{where} {rel!r} is an absolute path")
    if ".." in entry.parts:
        raise ValueError(f"{where} {rel!r} contains '..'")
    return confine_generated(root, root / entry, what=where)


def require_owned(adapter_id, rel, owned, what="path"):
    """Reject a path the adapter does not own (H-04).

    Confinement proves the target is inside the root; ownership proves
    the file belongs to this adapter's output. Without it, a trusted or
    tampered adapter could overwrite (and a planted manifest could
    delete) user source, the project entrypoint or harness settings the
    adapter never generates.
    """
    entry = rel.replace("\\", "/")
    for prefix in owned:
        if prefix.endswith("/"):
            if entry.startswith(prefix):
                return
        elif entry == prefix:
            return
    listing = ", ".join(owned) or "nothing"
    raise ValueError(
        f"adapter {adapter_id!r} {what} {rel!r} is not owned by this adapter "
        f"(owned: {listing})"
    )


# Ownership of the adapter currently running its sync/install. Scoped, so
# concurrent use of the module in-process stays deterministic.
_ACTIVE_OWNERSHIP = None


@contextlib.contextmanager
def ownership_scope(adapter):
    """Bind write_generated() to ``adapter``'s declared output for its duration."""
    global _ACTIVE_OWNERSHIP
    previous = _ACTIVE_OWNERSHIP
    _ACTIVE_OWNERSHIP = (adapter.id, tuple(adapter.owned_paths()))
    try:
        yield
    finally:
        _ACTIVE_OWNERSHIP = previous


def write_generated(path, content, *, root, dry_run=False, manifest=True):
    """Write a generated file unless the existing content is identical.

    ``root`` is mandatory and the target must resolve inside it: no
    adapter, trusted or not, can write outside the project root, and no
    adapter can write into ``.juicer/``, ``.git/`` or ``.gitignore``.
    While an adapter sync is running, manifest-tracked writes must also
    land inside the paths that adapter declared as its own.
    """
    confine_generated(root, path, what="generated path")
    if manifest and _ACTIVE_OWNERSHIP is not None:
        adapter_id, owned = _ACTIVE_OWNERSHIP
        try:
            rel = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            rel = str(path)
        require_owned(adapter_id, rel, owned, what="generated path")
    data = content.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    if path.exists() and path.read_bytes() == data:
        return Change(path=path, action="skip", reason="unchanged",
                      digest=digest, manifest=manifest)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return Change(path=path, action="write", digest=digest, manifest=manifest)


def resolve_source(ctx, relative):
    """Prefer the project copy of a canonical path, fall back to the kit."""
    candidate = ctx.root / relative
    if candidate.exists():
        return candidate
    return ctx.kit / relative


def _inside(path, base):
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
    except ValueError:
        return False
    return True


def trusted_source(ctx, path):
    """True when ``path`` resolves inside the project or the kit.

    Canonical sources are read through symlinks. A repository can carry a
    symlink pointing at ``~/.ssh/id_rsa``; following it would copy
    outside content into generated harness files. Sources that resolve
    outside both roots are skipped with a warning instead.
    """
    return _inside(path, ctx.root) or _inside(path, ctx.kit)


def iter_workers(ctx):
    """Yield every canonical worker contract, project copy first."""
    agents_dir = resolve_source(ctx, ctx.agents_source)
    if not agents_dir.is_dir():
        return
    for path in sorted(agents_dir.glob("*.md")):
        if not trusted_source(ctx, path):
            print(f"warning: skipping worker outside the project/kit roots: {path}",
                  file=sys.stderr)
            continue
        if not WORKER_NAME.match(path.stem):
            print(f"warning: skipping {path.name!r}: a worker name must match "
                  "^[a-z][a-z0-9-]*$ (it is embedded in generated files)",
                  file=sys.stderr)
            continue
        frontmatter, body = read_frontmatter(path)
        yield Worker(name=path.stem, path=path, frontmatter=frontmatter, body=body)


def ensure_entrypoint(ctx, dry_run=False):
    """Make sure AGENTS.md exists; copy it from the kit when missing.

    The entrypoint is project-owned: it is never tracked in the sync
    manifest and therefore never deleted as a stale generated file.
    """
    target = confine_generated(ctx.root, ctx.root / "AGENTS.md", what="entrypoint")
    if target.exists():
        return Change(path=target, action="skip", reason="exists",
                      digest=sha256_file(target), manifest=False)
    return write_generated(target, (ctx.kit / "AGENTS.md").read_text(),
                           root=ctx.root, dry_run=dry_run, manifest=False)


def mirror_skills(ctx, destination, dry_run=False):
    """Copy the canonical skills tree into a harness skills directory."""
    source = resolve_source(ctx, ctx.skills_source)
    changes = []
    if not source.is_dir():
        return changes
    for src in sorted(source.rglob("*")):
        if not src.is_file():
            continue
        if not trusted_source(ctx, src):
            print(f"warning: skipping skills source outside the project/kit roots: {src}",
                  file=sys.stderr)
            continue
        rel = src.relative_to(source)
        dst = confine_generated(ctx.root, destination / rel, what="skills mirror path")
        data = src.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if dst.exists() and dst.read_bytes() == data:
            changes.append(Change(path=dst, action="skip", reason="unchanged",
                                  digest=digest))
            continue
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        changes.append(Change(path=dst, action="write", digest=digest))
    return changes


def direct_instructions(ctx, worker, unit=None):
    """Portable fallback: execute the worker contract directly."""
    worker_path = None
    for candidate in (ctx.root / "agents", ctx.kit / "agents"):
        if (candidate / f"{worker}.md").exists():
            worker_path = candidate / f"{worker}.md"
            break
    scope = f"unit {unit}" if unit else "the active unit"
    lines = [
        "Direct execution (portable fallback):",
        f"1. Read the worker contract: {worker_path or f'agents/{worker}.md'}",
        f"2. Read {ctx.state_dir}/mission.md, {ctx.state_dir}/plan.md and {ctx.state_dir}/handoff.md",
        f"3. Execute the contract for {scope} inside the harness",
        f"4. Record progress: juicer checkpoint <executing|blocked|ready|done>",
        "juicer never calls a model; the harness runs the worker.",
    ]
    return "\n".join(lines)


class Adapter:
    """Base class for harness adapters.

    Subclasses set ``id`` and ``executable``, implement ``capabilities``
    and ``sync``, and may override ``discover``, ``install`` and
    ``invoke`` for harness-specific behavior.
    """

    id = "base"
    executable = None          # binary probed by discover()
    marker_dir = None          # harness dir where install() drops its marker
    agents_dir = None          # harness agents target, e.g. ".opencode/agents"
    skills_dir = None          # harness skills mirror target, if any
    supports_skills_mirror = False

    def owned_paths(self):
        """Relative files and directory prefixes this adapter may generate.

        A manifest entry outside this set is rejected before any file is
        read or deleted, so an adapter — or a tampered manifest claiming
        to be its output — can never remove a file it does not own.
        ``AGENTS.md`` is deliberately absent: it is project-owned.
        """
        owned = []
        for directory in (self.agents_dir, self.skills_dir):
            if directory:
                owned.append(str(directory).rstrip("/") + "/")
        if self.marker_dir:
            owned.append(str(self.marker_dir).rstrip("/") + "/juicer-kit.md")
        return owned

    def capabilities(self):
        raise NotImplementedError

    def discover(self, ctx):
        """Report harness availability. Never raises, never fails hard."""
        if not self.executable:
            return {"available": False, "version": None,
                    "notes": "no executable configured"}
        path = shutil.which(self.executable)
        if not path:
            return {"available": False, "version": None,
                    "notes": f"{self.executable!r} not found on PATH"}
        try:
            proc = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return {"available": False, "version": None,
                    "notes": f"version probe failed for {self.executable!r}"}
        output = (proc.stdout or proc.stderr or "").strip().splitlines()
        version = output[0].strip() if output else ""
        match = re.search(r"\d+", version)
        return {
            "available": proc.returncode == 0,
            "version": version or None,
            "major": int(match.group()) if match else None,
            "path": path,
        }

    def sync(self, ctx, dry_run=False):
        """Generate harness-native files from canonical sources."""
        raise NotImplementedError

    def install(self, ctx, dry_run=False):
        """Run sync() and drop the adapter marker."""
        changes = [c for c in self.sync(ctx, dry_run=dry_run) if c is not None]
        if self.marker_dir:
            marker = ctx.root / self.marker_dir / "juicer-kit.md"
            readme = ctx.kit / "adapters" / self.id / "README.md"
            content = readme.read_text() if readme.exists() else f"Juicer Kit adapter: {self.id}\n"
            changes.append(write_generated(marker, content, root=ctx.root,
                                           dry_run=dry_run))
        return changes

    def invoke(self, ctx, worker, unit=None):
        """Return harness-native invocation instructions for a worker."""
        raise NotImplementedError

    def _invoke(self, ctx, worker, unit=None, native=None):
        parts = [f"harness: {self.id}", f"worker: {worker}"]
        parts.append(native or "native route: none; use direct execution")
        parts.append(direct_instructions(ctx, worker, unit))
        return "\n".join(parts)
