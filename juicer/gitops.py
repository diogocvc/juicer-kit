"""Git operations for isolated work, explicit integration and evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class GitError(RuntimeError):
    pass


def git(args: List[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git"] + list(args), cwd=str(cwd), capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise GitError("git %s failed (%s): %s" % (" ".join(args), proc.returncode, proc.stderr.strip()))
    return proc


def is_git_repo(path: Path) -> bool:
    proc = git(["rev-parse", "--is-inside-work-tree"], path, check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def repo_root(path: Path) -> Optional[Path]:
    proc = git(["rev-parse", "--show-toplevel"], path, check=False)
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def is_worktree_root(path: Path) -> bool:
    """True when *path* is itself a git worktree root.

    A nested directory of the main repository also answers ``is-inside-work-tree``;
    hiding the worktree's ``.git`` would make git silently fall back to the
    parent repository, so the toplevel must match exactly.
    """
    root = repo_root(path)
    if root is None:
        return False
    try:
        return root.resolve() == Path(path).resolve()
    except OSError:
        return False


def current_branch(path: Path) -> Optional[str]:
    proc = git(["rev-parse", "--abbrev-ref", "HEAD"], path, check=False)
    if proc.returncode != 0:
        return None
    name = proc.stdout.strip()
    return name if name and name != "HEAD" else None


def head_commit(path: Path) -> Optional[str]:
    proc = git(["rev-parse", "HEAD"], path, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def status_porcelain(path: Path, exclude=()) -> List[str]:
    proc = git(["status", "--porcelain"], path, check=False)
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        rel = line[3:].strip()
        # rename lines look like "old -> new"; check the new side
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1].strip()
        if any(rel == ex or rel.startswith(ex.rstrip("/") + "/") for ex in exclude):
            continue
        out.append(line)
    return out


def is_dirty(path: Path, exclude=()) -> bool:
    return bool(status_porcelain(path, exclude=exclude))


def has_tracked_changes(path: Path) -> bool:
    """True when tracked files differ from HEAD (staged or unstaged).

    Untracked files are ignored on purpose: post-commit checks may leave
    artifacts (coverage, logs, snapshots) without changing the reviewed commit.
    Errors are treated as dirty (fail closed).
    """
    unstaged = git(["diff", "--quiet"], path, check=False)
    staged = git(["diff", "--quiet", "--cached"], path, check=False)
    return unstaged.returncode != 0 or staged.returncode != 0


def changed_files(path: Path, base: Optional[str] = None) -> List[str]:
    """Files changed relative to *base* (or HEAD), including untracked ones.

    Rename detection is disabled so the removed path is reported as well; a
    rename must never hide a protected source file.
    """
    ref = base or "HEAD"
    proc = git(["diff", "--name-only", "--no-renames", ref], path, check=False)
    files = set(proc.stdout.splitlines()) if proc.returncode == 0 else set()
    untracked = git(["ls-files", "--others", "--exclude-standard"], path,
                    check=False)
    files |= set(untracked.stdout.splitlines())
    return sorted(f for f in files if f.strip())


def diff_stat(path: Path, base: Optional[str] = None) -> str:
    args = ["diff", "--stat", "--no-renames"]
    args.append(base or "HEAD")
    proc = git(args, path, check=False)
    return proc.stdout.strip()


def ensure_clean(path: Path, allow_dirty: bool = False) -> None:
    if not allow_dirty and is_dirty(path):
        raise GitError(
            "working tree at %s has uncommitted changes; commit or stash before integration"
            % path
        )


def create_branch(path: Path, name: str, start_point: Optional[str] = None) -> None:
    args = ["checkout", "-b", name]
    if start_point:
        args.append(start_point)
    git(args, path)


def create_worktree(repo: Path, branch: str, worktree_path: Path,
                    base: Optional[str] = None, new_branch: bool = True) -> Path:
    worktree_path = Path(worktree_path)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    if new_branch and branch_exists(repo, branch):
        # retry of a failed attempt: the old branch is superseded; the prior
        # attempt remains auditable via its execution record and commit sha
        git(["branch", "-D", branch], repo)
    args = ["worktree", "add"]
    if new_branch:
        args += ["-b", branch]
    args.append(str(worktree_path))
    if base:
        args.append(base)
    git(args, repo)
    return worktree_path


def branch_exists(repo: Path, branch: str) -> bool:
    proc = git(["rev-parse", "--verify", "--quiet", "refs/heads/%s" % branch],
                repo, check=False)
    return proc.returncode == 0


def remove_worktree(repo: Path, worktree_path: Path, force: bool = False) -> None:
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(worktree_path))
    git(args, repo, check=False)
    git(["worktree", "prune"], repo, check=False)


def commit_all(path: Path, message: str, allow_empty: bool = False) -> Optional[str]:
    git(["add", "-A"], path)
    if not status_porcelain(path):
        if allow_empty:
            git(["commit", "--allow-empty", "-m", message], path)
            return head_commit(path)
        return None
    git(["commit", "-m", message], path)
    return head_commit(path)


def stage_all(path: Path) -> None:
    """Stage every change (including deletions) without committing."""
    git(["add", "-A"], path)


def staged_changed(path: Path, base: Optional[str]) -> List[str]:
    """Paths that differ between *base* (or HEAD) and the index."""
    proc = git(["diff", "--cached", "--name-only", "--no-renames",
                base or "HEAD"], path, check=False)
    if proc.returncode != 0:
        return []
    return sorted(f for f in proc.stdout.splitlines() if f.strip())


def commit_index(path: Path, message: str) -> Optional[str]:
    """Commit the staged index only; None when there is nothing to commit."""
    has_staged = git(["diff", "--cached", "--quiet"], path, check=False)
    if has_staged.returncode == 0:
        return None
    git(["commit", "-m", message], path)
    return head_commit(path)


def reset_soft(path: Path, rev: str) -> None:
    """Move HEAD back to *rev* keeping the index/worktree (drop a bad commit)."""
    git(["reset", "--soft", rev], path, check=False)


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """True when *ancestor* is an ancestor of (or equal to) *descendant*."""
    proc = git(["merge-base", "--is-ancestor", ancestor, descendant], repo,
               check=False)
    return proc.returncode == 0


def is_merging(repo: Path) -> bool:
    """True when a merge is in progress (MERGE_HEAD exists)."""
    proc = git(["rev-parse", "--verify", "--quiet", "MERGE_HEAD"], repo,
               check=False)
    return proc.returncode == 0


def merge_no_ff(repo: Path, ref: str, message: Optional[str] = None) -> Tuple[bool, str]:
    """Explicit merge of *ref* (branch or SHA); on conflict abort and report."""
    msg = message or "juicer: merge %s" % ref
    proc = git(["merge", "--no-ff", ref, "-m", msg], repo, check=False)
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    git(["merge", "--abort"], repo, check=False)
    return False, (proc.stderr or proc.stdout).strip()


def diff_against(path: Path, base: str) -> str:
    """Full patch against *base*; untracked files must be intent-to-added."""
    proc = git(["diff", "--no-renames", base], path, check=False)
    return proc.stdout


def tree_hash(path: Path, commit: Optional[str] = None) -> Optional[str]:
    """Return the git tree hash for *commit* (or HEAD when omitted)."""
    ref = "%s^{tree}" % commit if commit else "HEAD^{tree}"
    proc = git(["rev-parse", ref], path, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def branch_tip(repo: Path, branch: str) -> Optional[str]:
    """Return the commit a branch points at, or None when it does not exist."""
    proc = git(["rev-parse", "--verify", "--quiet", "refs/heads/%s" % branch],
               repo, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def changed_between(repo: Path, base: Optional[str], head: Optional[str]) -> List[str]:
    """Files changed between two commits (net tree delta, no renames)."""
    if not base or not head:
        return []
    proc = git(["diff", "--name-only", "--no-renames", base, head], repo,
               check=False)
    if proc.returncode != 0:
        return []
    return sorted(f for f in proc.stdout.splitlines() if f.strip())


def changed_in_range(repo: Path, base: Optional[str], head: Optional[str]) -> List[str]:
    """Every path touched by commits in ``base..head`` (including intermediate
    commits).

    A path added by one commit and deleted by a later one is invisible in the
    net diff, yet the merge still brings that commit into the target history.
    This helper fails closed: an unresolvable range raises ``GitError``.
    """
    if not base or not head:
        raise GitError("changed_in_range requires both base and head commits")
    if base == head:
        return []
    proc = git(["log", "--no-renames", "--name-only", "--format=",
                "%s..%s" % (base, head), "--"], repo, check=False)
    if proc.returncode != 0:
        raise GitError("cannot list committed changes %s..%s: %s"
                       % (base, head, proc.stderr.strip()))
    return sorted({f.strip() for f in proc.stdout.splitlines() if f.strip()})


def is_commit(repo: Path, rev: str) -> bool:
    """True when *rev* resolves to a commit object in *repo*."""
    if not rev:
        return False
    proc = git(["rev-parse", "--verify", "--quiet", "%s^{commit}" % rev],
               repo, check=False)
    return proc.returncode == 0


def parent_commit(repo: Path, rev: str) -> Optional[str]:
    """Parent of *rev*, or None for a root commit / unresolvable rev."""
    proc = git(["rev-parse", "--verify", "--quiet", "%s^" % rev], repo,
               check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def intent_to_add(path: Path) -> None:
    """Mark untracked files as intent-to-add so ``git diff`` shows content."""
    git(["add", "-N", "-A", "."], path, check=False)


def update_ref(repo: Path, ref: str, sha: str) -> bool:
    """Create/update a durable ref; returns True on success."""
    proc = git(["update-ref", ref, sha], repo, check=False)
    return proc.returncode == 0
