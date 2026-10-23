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


def changed_files(path: Path, base: Optional[str] = None) -> List[str]:
    """Files changed relative to HEAD, including untracked ones."""
    if base:
        proc = git(["diff", "--name-only", base + "...HEAD"], path, check=False)
        if proc.returncode != 0:
            proc = git(["diff", "--name-only", base], path, check=False)
        committed = set(proc.stdout.splitlines())
        working = set(git(["diff", "--name-only"], path, check=False).stdout.splitlines())
        staged = set(git(["diff", "--name-only", "--cached"], path, check=False).stdout.splitlines())
        untracked = set(git(["ls-files", "--others", "--exclude-standard"], path,
                            check=False).stdout.splitlines())
        return sorted(f for f in (committed | working | staged | untracked) if f.strip())
    proc = git(["diff", "--name-only", "HEAD"], path, check=False)
    staged = git(["diff", "--name-only", "--cached"], path, check=False)
    untracked = git(["ls-files", "--others", "--exclude-standard"], path, check=False)
    files = set(proc.stdout.splitlines()) | set(staged.stdout.splitlines()) | set(
        untracked.stdout.splitlines())
    return sorted(f for f in files if f.strip())


def diff_stat(path: Path, base: Optional[str] = None) -> str:
    args = ["diff", "--stat"]
    if base:
        args.append(base + "...HEAD")
    else:
        args.append("HEAD")
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


def merge_no_ff(repo: Path, branch: str, message: Optional[str] = None) -> Tuple[bool, str]:
    """Explicit merge; on conflict abort and report, never overwrite silently."""
    msg = message or "juicer: merge %s" % branch
    proc = git(["merge", "--no-ff", branch, "-m", msg], repo, check=False)
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    git(["merge", "--abort"], repo, check=False)
    return False, (proc.stderr or proc.stdout).strip()


def diff_against(path: Path, base: str) -> str:
    proc = git(["diff", base], path, check=False)
    return proc.stdout
