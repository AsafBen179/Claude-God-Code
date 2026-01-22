"""
Git Worktree Manager - Per-Spec Architecture
=============================================

Each spec gets its own worktree:
- Worktree path: .claude-god-code/worktrees/specs/{spec-name}/
- Branch name: claude-god-code/{spec-name}

This allows:
1. Multiple specs to be worked on simultaneously
2. Each spec's changes are isolated
3. Branches persist until explicitly merged
4. Clear 1:1:1 mapping: spec -> worktree -> branch

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, TypedDict, TypeVar

from core.git_executable import get_git_executable, get_isolated_git_env, run_git

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _is_retryable_network_error(stderr: str) -> bool:
    """Check if an error is a retryable network/connection issue."""
    stderr_lower = stderr.lower()
    return any(
        term in stderr_lower
        for term in ["connection", "network", "timeout", "reset", "refused"]
    )


def _is_retryable_http_error(stderr: str) -> bool:
    """Check if an HTTP error is retryable (5xx errors, timeouts)."""
    stderr_lower = stderr.lower()
    if re.search(r"http[s]?\s*5\d{2}", stderr_lower):
        return True
    if "http" in stderr_lower and "timeout" in stderr_lower:
        return True
    return False


def _with_retry(
    operation: Callable[[], tuple[bool, T | None, str]],
    max_retries: int = 3,
    is_retryable: Callable[[str], bool] | None = None,
    on_retry: Callable[[int, str], None] | None = None,
) -> tuple[T | None, str]:
    """
    Execute an operation with retry logic.

    Args:
        operation: Function that returns (success, result, error)
        max_retries: Maximum number of retry attempts
        is_retryable: Function to check if error is retryable
        on_retry: Optional callback called before each retry

    Returns:
        Tuple of (result, last_error)
    """
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            success, result, error = operation()
            if success:
                return result, ""

            last_error = error

            if is_retryable and attempt < max_retries and is_retryable(error):
                if on_retry:
                    on_retry(attempt, error)
                backoff = 2 ** (attempt - 1)
                time.sleep(backoff)
                continue

            break

        except subprocess.TimeoutExpired:
            last_error = "Operation timed out"
            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt, last_error)
                backoff = 2 ** (attempt - 1)
                time.sleep(backoff)
                continue
            break

    return None, last_error


class PushBranchResult(TypedDict, total=False):
    """Result of pushing a branch to remote."""
    success: bool
    branch: str
    remote: str
    error: str


class PullRequestResult(TypedDict, total=False):
    """Result of creating a pull request."""
    success: bool
    pr_url: str | None
    already_exists: bool
    error: str
    message: str


class PushAndCreatePRResult(TypedDict, total=False):
    """Result of push_and_create_pr operation."""
    success: bool
    pushed: bool
    remote: str
    branch: str
    pr_url: str | None
    already_exists: bool
    error: str
    message: str


class WorktreeError(Exception):
    """Error during worktree operations."""
    pass


@dataclass
class WorktreeInfo:
    """Information about a spec's worktree."""
    path: Path
    branch: str
    spec_name: str
    base_branch: str
    is_active: bool = True
    commit_count: int = 0
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    last_commit_date: datetime | None = None
    days_since_last_commit: int | None = None


class WorktreeManager:
    """
    Manages per-spec Git worktrees.

    Each spec gets its own worktree in .claude-god-code/worktrees/specs/{spec-name}/
    with a corresponding branch claude-god-code/{spec-name}.
    """

    GIT_PUSH_TIMEOUT = 120
    GH_CLI_TIMEOUT = 60
    GH_QUERY_TIMEOUT = 30

    def __init__(self, project_dir: Path, base_branch: str | None = None):
        self.project_dir = project_dir
        self.base_branch = base_branch or self._detect_base_branch()
        self.worktrees_dir = project_dir / ".claude-god-code" / "worktrees" / "specs"
        self._merge_lock = asyncio.Lock()

    def _detect_base_branch(self) -> str:
        """Detect the base branch for worktree creation."""
        env_branch = os.getenv("DEFAULT_BRANCH")
        if env_branch:
            result = run_git(
                ["rev-parse", "--verify", env_branch],
                cwd=self.project_dir,
            )
            if result.returncode == 0:
                return env_branch
            else:
                print(f"Warning: DEFAULT_BRANCH '{env_branch}' not found, auto-detecting...")

        for branch in ["main", "master"]:
            result = run_git(
                ["rev-parse", "--verify", branch],
                cwd=self.project_dir,
            )
            if result.returncode == 0:
                return branch

        current = self._get_current_branch()
        print("Warning: Could not find 'main' or 'master' branch.")
        print(f"Warning: Using current branch '{current}' as base for worktree.")
        print("Tip: Set DEFAULT_BRANCH=your-branch in .env to avoid this.")
        return current

    def _get_current_branch(self) -> str:
        """Get the current git branch."""
        result = run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.project_dir,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to get current branch: {result.stderr}")
        return result.stdout.strip()

    def _run_git(
        self, args: list[str], cwd: Path | None = None, timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """Run a git command and return the result."""
        return run_git(args, cwd=cwd or self.project_dir, timeout=timeout)

    def setup(self) -> None:
        """Create worktrees directory if needed."""
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

    def get_worktree_path(self, spec_name: str) -> Path:
        """Get the worktree path for a spec."""
        new_path = self.worktrees_dir / spec_name
        if new_path.exists():
            return new_path

        legacy_path = self.project_dir / ".worktrees" / spec_name
        if legacy_path.exists():
            return legacy_path

        return new_path

    def get_branch_name(self, spec_name: str) -> str:
        """Get the branch name for a spec."""
        return f"claude-god-code/{spec_name}"

    def worktree_exists(self, spec_name: str) -> bool:
        """Check if a worktree exists for a spec."""
        return self.get_worktree_path(spec_name).exists()

    def get_worktree_info(self, spec_name: str) -> WorktreeInfo | None:
        """Get info about a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return None

        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path)
        if result.returncode != 0:
            return None

        actual_branch = result.stdout.strip()
        stats = self._get_worktree_stats(spec_name)

        return WorktreeInfo(
            path=worktree_path,
            branch=actual_branch,
            spec_name=spec_name,
            base_branch=self.base_branch,
            is_active=True,
            **stats,
        )

    def _check_branch_namespace_conflict(self) -> str | None:
        """Check if a branch named 'claude-god-code' exists."""
        result = self._run_git(["rev-parse", "--verify", "claude-god-code"])
        if result.returncode == 0:
            return "claude-god-code"
        return None

    def _get_worktree_stats(self, spec_name: str) -> dict:
        """Get diff statistics for a worktree."""
        worktree_path = self.get_worktree_path(spec_name)

        stats = {
            "commit_count": 0,
            "files_changed": 0,
            "additions": 0,
            "deletions": 0,
            "last_commit_date": None,
            "days_since_last_commit": None,
        }

        if not worktree_path.exists():
            return stats

        result = self._run_git(
            ["rev-list", "--count", f"{self.base_branch}..HEAD"], cwd=worktree_path
        )
        if result.returncode == 0:
            stats["commit_count"] = int(result.stdout.strip() or "0")

        result = self._run_git(
            ["log", "-1", "--format=%cd", "--date=iso"], cwd=worktree_path
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                date_str = result.stdout.strip()
                parts = date_str.rsplit(" ", 1)
                if len(parts) == 2:
                    date_part, tz_part = parts
                    if len(tz_part) == 5 and (
                        tz_part.startswith("+") or tz_part.startswith("-")
                    ):
                        tz_formatted = f"{tz_part[:3]}:{tz_part[3:]}"
                        iso_str = f"{date_part.replace(' ', 'T')}{tz_formatted}"
                        last_commit_date = datetime.fromisoformat(iso_str)
                        stats["last_commit_date"] = last_commit_date
                        now_aware = datetime.now(last_commit_date.tzinfo)
                        stats["days_since_last_commit"] = (now_aware - last_commit_date).days
            except (ValueError, TypeError):
                pass

        result = self._run_git(
            ["diff", "--shortstat", f"{self.base_branch}...HEAD"], cwd=worktree_path
        )
        if result.returncode == 0 and result.stdout.strip():
            match = re.search(r"(\d+) files? changed", result.stdout)
            if match:
                stats["files_changed"] = int(match.group(1))
            match = re.search(r"(\d+) insertions?", result.stdout)
            if match:
                stats["additions"] = int(match.group(1))
            match = re.search(r"(\d+) deletions?", result.stdout)
            if match:
                stats["deletions"] = int(match.group(1))

        return stats

    def create_worktree(self, spec_name: str) -> WorktreeInfo:
        """
        Create a worktree for a spec.

        Args:
            spec_name: The spec folder name

        Returns:
            WorktreeInfo for the created worktree

        Raises:
            WorktreeError: If creation fails
        """
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)

        conflicting_branch = self._check_branch_namespace_conflict()
        if conflicting_branch:
            raise WorktreeError(
                f"Branch '{conflicting_branch}' exists and blocks creating '{branch_name}'.\n"
                f"\n"
                f"Git branch names work like file paths - a branch named 'claude-god-code' prevents\n"
                f"creating branches under 'claude-god-code/' (like 'claude-god-code/{spec_name}').\n"
                f"\n"
                f"Fix: Rename the conflicting branch:\n"
                f"  git branch -m {conflicting_branch} {conflicting_branch}-backup"
            )

        if worktree_path.exists():
            self._run_git(["worktree", "remove", "--force", str(worktree_path)])

        self._run_git(["branch", "-D", branch_name])

        fetch_result = self._run_git(["fetch", "origin", self.base_branch])
        if fetch_result.returncode != 0:
            print(f"Warning: Could not fetch {self.base_branch} from origin: {fetch_result.stderr}")
            print("Falling back to local branch...")

        remote_ref = f"origin/{self.base_branch}"
        start_point = self.base_branch

        check_remote = self._run_git(["rev-parse", "--verify", remote_ref])
        if check_remote.returncode == 0:
            start_point = remote_ref
            print(f"Creating worktree from remote: {remote_ref}")
        else:
            print(f"Remote ref {remote_ref} not found, using local branch: {self.base_branch}")

        result = self._run_git(
            ["worktree", "add", "-b", branch_name, str(worktree_path), start_point]
        )

        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to create worktree for {spec_name}: {result.stderr}"
            )

        print(f"Created worktree: {worktree_path.name} on branch {branch_name}")

        return WorktreeInfo(
            path=worktree_path,
            branch=branch_name,
            spec_name=spec_name,
            base_branch=self.base_branch,
            is_active=True,
        )

    def get_or_create_worktree(self, spec_name: str) -> WorktreeInfo:
        """Get existing worktree or create a new one for a spec."""
        existing = self.get_worktree_info(spec_name)
        if existing:
            print(f"Using existing worktree: {existing.path}")
            return existing

        return self.create_worktree(spec_name)

    def remove_worktree(self, spec_name: str, delete_branch: bool = False) -> None:
        """Remove a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)

        if worktree_path.exists():
            result = self._run_git(
                ["worktree", "remove", "--force", str(worktree_path)]
            )
            if result.returncode == 0:
                print(f"Removed worktree: {worktree_path.name}")
            else:
                print(f"Warning: Could not remove worktree: {result.stderr}")
                shutil.rmtree(worktree_path, ignore_errors=True)

        if delete_branch:
            self._run_git(["branch", "-D", branch_name])
            print(f"Deleted branch: {branch_name}")

        self._run_git(["worktree", "prune"])

    def merge_worktree(
        self, spec_name: str, delete_after: bool = False, no_commit: bool = False
    ) -> bool:
        """Merge a spec's worktree branch back to base branch."""
        info = self.get_worktree_info(spec_name)
        if not info:
            print(f"No worktree found for spec: {spec_name}")
            return False

        if no_commit:
            print(f"Merging {info.branch} into {self.base_branch} (staged, not committed)...")
        else:
            print(f"Merging {info.branch} into {self.base_branch}...")

        current_branch = self._get_current_branch()
        if current_branch != self.base_branch:
            result = self._run_git(["checkout", self.base_branch])
            if result.returncode != 0:
                new_branch = self._get_current_branch()
                if new_branch != self.base_branch:
                    stderr_msg = result.stderr[:100] if result.stderr else "<no stderr>"
                    print(f"Error: Could not checkout base branch: {stderr_msg}")
                    return False

        merge_args = ["merge", "--no-ff", info.branch]
        if no_commit:
            merge_args.append("--no-commit")
        else:
            merge_args.extend(["-m", f"claude-god-code: Merge {info.branch}"])

        result = self._run_git(merge_args)

        if result.returncode != 0:
            output = (result.stdout + result.stderr).lower()
            if "already up to date" in output or "already up-to-date" in output:
                print(f"Branch {info.branch} is already up to date.")
                if delete_after:
                    self.remove_worktree(spec_name, delete_branch=True)
                return True
            if "conflict" in output:
                print("Merge conflict! Aborting merge...")
                self._run_git(["merge", "--abort"])
                return False
            stderr_msg = (
                result.stderr[:200]
                if result.stderr
                else result.stdout[:200]
                if result.stdout
                else "<no output>"
            )
            print(f"Merge failed: {stderr_msg}")
            self._run_git(["merge", "--abort"])
            return False

        if no_commit:
            print(f"Changes from {info.branch} are now staged in your working directory.")
            print("Review the changes, then commit when ready:")
            print("  git commit -m 'your commit message'")
        else:
            print(f"Successfully merged {info.branch}")

        if delete_after:
            self.remove_worktree(spec_name, delete_branch=True)

        return True

    def commit_in_worktree(self, spec_name: str, message: str) -> bool:
        """Commit all changes in a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return False

        self._run_git(["add", "."], cwd=worktree_path)
        result = self._run_git(["commit", "-m", message], cwd=worktree_path)

        if result.returncode == 0:
            return True
        elif "nothing to commit" in result.stdout + result.stderr:
            return True
        else:
            print(f"Commit failed: {result.stderr}")
            return False

    def list_all_worktrees(self) -> list[WorktreeInfo]:
        """List all spec worktrees."""
        worktrees = []
        seen_specs = set()

        if self.worktrees_dir.exists():
            for item in self.worktrees_dir.iterdir():
                if item.is_dir():
                    info = self.get_worktree_info(item.name)
                    if info:
                        worktrees.append(info)
                        seen_specs.add(item.name)

        legacy_dir = self.project_dir / ".worktrees"
        if legacy_dir.exists():
            for item in legacy_dir.iterdir():
                if item.is_dir() and item.name not in seen_specs:
                    info = self.get_worktree_info(item.name)
                    if info:
                        worktrees.append(info)

        return worktrees

    def list_all_spec_branches(self) -> list[str]:
        """List all claude-god-code branches."""
        result = self._run_git(["branch", "--list", "claude-god-code/*"])
        if result.returncode != 0:
            return []

        branches = []
        for line in result.stdout.strip().split("\n"):
            branch = line.strip().lstrip("* ")
            if branch:
                branches.append(branch)

        return branches

    def get_changed_files(self, spec_name: str) -> list[tuple[str, str]]:
        """Get list of changed files in a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return []

        result = self._run_git(
            ["diff", "--name-status", f"{self.base_branch}...HEAD"], cwd=worktree_path
        )

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append((parts[0], parts[1]))

        return files

    def has_uncommitted_changes(self, spec_name: str | None = None) -> bool:
        """Check if there are uncommitted changes."""
        cwd = None
        if spec_name:
            worktree_path = self.get_worktree_path(spec_name)
            if worktree_path.exists():
                cwd = worktree_path
        result = self._run_git(["status", "--porcelain"], cwd=cwd)
        return bool(result.stdout.strip())

    def cleanup_all(self) -> None:
        """Remove all worktrees and their branches."""
        for worktree in self.list_all_worktrees():
            self.remove_worktree(worktree.spec_name, delete_branch=True)

    def cleanup_stale_worktrees(self) -> None:
        """Remove worktrees that aren't registered with git."""
        if not self.worktrees_dir.exists():
            return

        result = self._run_git(["worktree", "list", "--porcelain"])
        registered_paths = set()
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                registered_paths.add(Path(line.split(" ", 1)[1]))

        for item in self.worktrees_dir.iterdir():
            if item.is_dir() and item not in registered_paths:
                print(f"Removing stale worktree directory: {item.name}")
                shutil.rmtree(item, ignore_errors=True)

        self._run_git(["worktree", "prune"])

    def push_branch(self, spec_name: str, force: bool = False) -> PushBranchResult:
        """Push a spec's branch to the remote origin with retry logic."""
        info = self.get_worktree_info(spec_name)
        if not info:
            return PushBranchResult(
                success=False,
                error=f"No worktree found for spec: {spec_name}",
            )

        push_args = ["push", "-u", "origin", info.branch]
        if force:
            push_args.insert(1, "--force")

        def do_push() -> tuple[bool, PushBranchResult | None, str]:
            try:
                git_executable = get_git_executable()
                result = subprocess.run(
                    [git_executable] + push_args,
                    cwd=info.path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.GIT_PUSH_TIMEOUT,
                    env=get_isolated_git_env(),
                )

                if result.returncode == 0:
                    return (
                        True,
                        PushBranchResult(
                            success=True,
                            branch=info.branch,
                            remote="origin",
                        ),
                        "",
                    )
                return (False, None, result.stderr)
            except FileNotFoundError:
                return (False, None, "git executable not found")

        max_retries = 3
        result, last_error = _with_retry(
            operation=do_push,
            max_retries=max_retries,
            is_retryable=_is_retryable_network_error,
        )

        if result:
            return result

        if last_error == "Operation timed out":
            return PushBranchResult(
                success=False,
                branch=info.branch,
                error=f"Push timed out after {max_retries} attempts.",
            )

        return PushBranchResult(
            success=False,
            branch=info.branch,
            error=f"Failed to push branch: {last_error}",
        )
