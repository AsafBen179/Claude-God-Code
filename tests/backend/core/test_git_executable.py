"""
Tests for core.git_executable module.

Part of Claude God Code - Autonomous Excellence
"""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from core.git_executable import (
    GIT_ENV_VARS_TO_CLEAR,
    get_git_executable,
    get_isolated_git_env,
    invalidate_git_cache,
    run_git,
)


class TestGetIsolatedGitEnv:
    """Tests for environment isolation."""

    def test_clears_git_env_vars(self) -> None:
        """Should clear all git-related environment variables."""
        base_env = {
            "PATH": "/usr/bin",
            "GIT_DIR": "/some/dir",
            "GIT_WORK_TREE": "/some/tree",
            "GIT_INDEX_FILE": "/some/index",
            "HOME": "/home/user",
        }
        isolated = get_isolated_git_env(base_env)

        # Git vars should be removed
        for var in GIT_ENV_VARS_TO_CLEAR:
            assert var not in isolated

        # Non-git vars should be preserved
        assert isolated["PATH"] == "/usr/bin"
        assert isolated["HOME"] == "/home/user"

    def test_sets_husky_disabled(self) -> None:
        """Should disable Husky hooks."""
        isolated = get_isolated_git_env({})
        assert isolated["HUSKY"] == "0"

    def test_uses_os_environ_by_default(self) -> None:
        """Should use os.environ when no base_env provided."""
        with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}, clear=False):
            isolated = get_isolated_git_env()
            assert "TEST_VAR" in isolated


class TestGetGitExecutable:
    """Tests for git executable discovery."""

    def test_returns_string(self) -> None:
        """Should return a string path."""
        git_path = get_git_executable()
        assert isinstance(git_path, str)
        assert len(git_path) > 0

    def test_caches_result(self) -> None:
        """Should cache the git path."""
        invalidate_git_cache()
        path1 = get_git_executable()
        path2 = get_git_executable()
        assert path1 == path2

    def test_invalidate_cache(self) -> None:
        """Cache invalidation should work."""
        # Just test it doesn't raise
        invalidate_git_cache()
        get_git_executable()


class TestRunGit:
    """Tests for git command execution."""

    def test_version_command(self) -> None:
        """Should successfully run git --version."""
        result = run_git(["--version"])
        assert result.returncode == 0
        assert "git version" in result.stdout.lower()

    def test_invalid_command(self) -> None:
        """Invalid command should fail gracefully."""
        result = run_git(["invalid-command-that-does-not-exist"])
        assert result.returncode != 0

    def test_timeout_parameter(self) -> None:
        """Should accept timeout parameter."""
        result = run_git(["--version"], timeout=30)
        assert result.returncode == 0

    def test_cwd_parameter(self, tmp_path: Path) -> None:
        """Should accept working directory parameter."""
        result = run_git(["rev-parse", "--is-inside-work-tree"], cwd=tmp_path)
        # May fail if tmp_path is not a git repo, but shouldn't crash
        assert result.returncode in (0, 128)

    def test_isolate_env_true(self) -> None:
        """Should isolate environment by default."""
        with mock.patch.dict(os.environ, {"GIT_DIR": "/bad/dir"}, clear=False):
            result = run_git(["--version"], isolate_env=True)
            assert result.returncode == 0

    def test_isolate_env_false(self) -> None:
        """Should allow custom env when isolate_env=False."""
        custom_env = os.environ.copy()
        result = run_git(["--version"], env=custom_env, isolate_env=False)
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
