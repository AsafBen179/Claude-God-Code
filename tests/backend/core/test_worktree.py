"""
Tests for core.worktree module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from core.worktree import (
    WorktreeError,
    WorktreeInfo,
    WorktreeManager,
    _is_retryable_http_error,
    _is_retryable_network_error,
)


class TestRetryableErrors:
    """Tests for retry error detection."""

    def test_network_error_detection(self) -> None:
        """Should detect network-related errors."""
        assert _is_retryable_network_error("Connection refused")
        assert _is_retryable_network_error("Network timeout")
        assert _is_retryable_network_error("connection reset by peer")
        assert not _is_retryable_network_error("Permission denied")
        assert not _is_retryable_network_error("File not found")

    def test_http_error_detection(self) -> None:
        """Should detect retryable HTTP errors (5xx)."""
        assert _is_retryable_http_error("HTTP 500 Internal Server Error")
        assert _is_retryable_http_error("http 503 service unavailable")
        assert _is_retryable_http_error("HTTP timeout error")
        assert not _is_retryable_http_error("HTTP 404 Not Found")
        assert not _is_retryable_http_error("HTTP 401 Unauthorized")


class TestWorktreeInfo:
    """Tests for WorktreeInfo dataclass."""

    def test_create_worktree_info(self, tmp_path: Path) -> None:
        """Should create WorktreeInfo with correct fields."""
        info = WorktreeInfo(
            path=tmp_path / "worktree",
            branch="claude-god-code/test-spec",
            spec_name="test-spec",
            base_branch="main",
            is_active=True,
        )
        assert info.spec_name == "test-spec"
        assert info.branch == "claude-god-code/test-spec"
        assert info.base_branch == "main"
        assert info.is_active is True
        assert info.commit_count == 0

    def test_worktree_info_default_stats(self, tmp_path: Path) -> None:
        """Default stats should be zero."""
        info = WorktreeInfo(
            path=tmp_path,
            branch="test",
            spec_name="test",
            base_branch="main",
        )
        assert info.commit_count == 0
        assert info.files_changed == 0
        assert info.additions == 0
        assert info.deletions == 0


class TestWorktreeManager:
    """Tests for WorktreeManager class."""

    def test_get_worktree_path(self, tmp_path: Path) -> None:
        """Should return correct worktree path."""
        manager = WorktreeManager(tmp_path, base_branch="main")
        path = manager.get_worktree_path("test-spec")
        assert "test-spec" in str(path)
        assert ".claude-god-code" in str(path)

    def test_get_branch_name(self, tmp_path: Path) -> None:
        """Should return correct branch name."""
        manager = WorktreeManager(tmp_path, base_branch="main")
        branch = manager.get_branch_name("test-spec")
        assert branch == "claude-god-code/test-spec"

    def test_worktree_exists_false_when_not_created(self, tmp_path: Path) -> None:
        """Should return False when worktree doesn't exist."""
        manager = WorktreeManager(tmp_path, base_branch="main")
        assert manager.worktree_exists("nonexistent-spec") is False

    def test_setup_creates_directory(self, tmp_path: Path) -> None:
        """Setup should create worktrees directory."""
        manager = WorktreeManager(tmp_path, base_branch="main")
        manager.setup()
        assert manager.worktrees_dir.exists()
        assert manager.worktrees_dir.is_dir()


class TestWorktreeError:
    """Tests for WorktreeError exception."""

    def test_worktree_error_message(self) -> None:
        """Should store error message."""
        error = WorktreeError("Test error message")
        assert str(error) == "Test error message"

    def test_worktree_error_inheritance(self) -> None:
        """Should inherit from Exception."""
        error = WorktreeError("Test")
        assert isinstance(error, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
