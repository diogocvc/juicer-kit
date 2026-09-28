"""Shared base class and helpers for Juicer Kit harness adapters.

Adapters are thin translators. They read canonical state from

    .juicer/   agents/   .agents/skills/   AGENTS.md

and write only harness-native mirrors. They never move workflow state.

This module is importable by any adapter (project or kit) because the
loader in bin/juicer puts this directory on sys.path before executing
an adapter module.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

FRONTMATTER_DELIM = "---"
ACCESS_LEVELS = ("read-only", "edit", "full")
TIER_LEVELS = ("hot", "warm", "cold")


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


def write_generated(path, content, dry_run=False):
    """Write a generated file unless the existing content is identical."""
    if path.exists() and path.read_text() == content:
        return Change(path=path, action="skip", reason="unchanged")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return Change(path=path, action="write")


def resolve_source(ctx, relative):
    """Prefer the project copy of a canonical path, fall back to the kit."""
    candidate = ctx.root / relative
    if candidate.exists():
        return candidate
    return ctx.kit / relative


def iter_workers(ctx):
    """Yield every canonical worker contract, project copy first."""
    agents_dir = resolve_source(ctx, ctx.agents_source)
    if not agents_dir.is_dir():
        return
    for path in sorted(agents_dir.glob("*.md")):
        frontmatter, body = read_frontmatter(path)
        yield Worker(name=path.stem, path=path, frontmatter=frontmatter, body=body)


def ensure_entrypoint(ctx, dry_run=False):
    """Make sure AGENTS.md exists; copy it from the kit when missing."""
    target = ctx.root / "AGENTS.md"
    if target.exists():
        return Change(path=target, action="skip", reason="exists")
    return write_generated(target, (ctx.kit / "AGENTS.md").read_text(), dry_run=dry_run)


def mirror_skills(ctx, destination, dry_run=False):
    """Copy the canonical skills tree into a harness skills directory."""
    source = resolve_source(ctx, ctx.skills_source)
    changes = []
    if not source.is_dir():
        return changes
    for src in sorted(source.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(source)
        dst = destination / rel
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            changes.append(Change(path=dst, action="skip", reason="unchanged"))
            continue
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        changes.append(Change(path=dst, action="write"))
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
    supports_skills_mirror = False

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
            changes.append(write_generated(marker, content, dry_run=dry_run))
        return changes

    def invoke(self, ctx, worker, unit=None):
        """Return harness-native invocation instructions for a worker."""
        raise NotImplementedError

    def _invoke(self, ctx, worker, unit=None, native=None):
        parts = [f"harness: {self.id}", f"worker: {worker}"]
        parts.append(native or "native route: none; use direct execution")
        parts.append(direct_instructions(ctx, worker, unit))
        return "\n".join(parts)
