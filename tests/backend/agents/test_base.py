"""
Tests for agents.base module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from agents.base import (
    AgentConfig,
    AgentContext,
    AgentError,
    AgentMetrics,
    AgentPhase,
    AgentState,
    AgentStatus,
    ErrorSeverity,
)


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = AgentConfig()
        assert config.max_iterations == 50
        assert config.max_retries == 3
        assert config.auto_continue is True
        assert config.use_worktree_isolation is True

    def test_custom_config(self) -> None:
        """Should accept custom values."""
        config = AgentConfig(
            max_iterations=100,
            auto_continue=False,
            temperature=0.5,
        )
        assert config.max_iterations == 100
        assert config.auto_continue is False
        assert config.temperature == 0.5

    def test_validate_valid_config(self) -> None:
        """Should validate correct configuration."""
        config = AgentConfig()
        issues = config.validate()
        assert len(issues) == 0

    def test_validate_invalid_iterations(self) -> None:
        """Should catch invalid max_iterations."""
        config = AgentConfig(max_iterations=0)
        issues = config.validate()
        assert "max_iterations must be at least 1" in issues

    def test_validate_invalid_temperature(self) -> None:
        """Should catch invalid temperature."""
        config = AgentConfig(temperature=3.0)
        issues = config.validate()
        assert "temperature must be between 0 and 2" in issues


class TestAgentError:
    """Tests for AgentError dataclass."""

    def test_create_error(self) -> None:
        """Should create error with correct fields."""
        error = AgentError(
            message="Test error",
            severity=ErrorSeverity.RECOVERABLE,
            phase=AgentPhase.CODING,
        )
        assert error.message == "Test error"
        assert error.severity == ErrorSeverity.RECOVERABLE
        assert error.phase == AgentPhase.CODING

    def test_is_recoverable(self) -> None:
        """Should correctly identify recoverable errors."""
        recoverable = AgentError(
            message="Recoverable",
            severity=ErrorSeverity.RECOVERABLE,
            phase=AgentPhase.CODING,
        )
        fatal = AgentError(
            message="Fatal",
            severity=ErrorSeverity.FATAL,
            phase=AgentPhase.CODING,
        )
        assert recoverable.is_recoverable() is True
        assert fatal.is_recoverable() is False

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        error = AgentError(
            message="Test",
            severity=ErrorSeverity.WARNING,
            phase=AgentPhase.PLANNING,
        )
        d = error.to_dict()
        assert d["message"] == "Test"
        assert d["severity"] == "warning"
        assert d["phase"] == "planning"


class TestAgentMetrics:
    """Tests for AgentMetrics dataclass."""

    def test_default_metrics(self) -> None:
        """Should initialize with zeros."""
        metrics = AgentMetrics()
        assert metrics.iterations == 0
        assert metrics.api_calls == 0
        assert metrics.files_modified == 0

    def test_get_duration(self) -> None:
        """Should calculate duration correctly."""
        metrics = AgentMetrics()
        metrics.start_time = datetime.now()
        duration = metrics.get_duration_seconds()
        assert duration >= 0
        assert duration < 1  # Should be nearly instant

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        metrics = AgentMetrics(
            iterations=10,
            api_calls=5,
            files_modified=3,
        )
        d = metrics.to_dict()
        assert d["iterations"] == 10
        assert d["api_calls"] == 5
        assert d["files_modified"] == 3


class TestAgentState:
    """Tests for AgentState dataclass."""

    def test_default_state(self) -> None:
        """Should have default values."""
        state = AgentState()
        assert state.status == AgentStatus.IDLE
        assert state.phase == AgentPhase.INITIALIZING
        assert state.current_iteration == 0

    def test_add_error(self) -> None:
        """Should add error and update metrics."""
        state = AgentState()
        error = AgentError(
            message="Test error",
            severity=ErrorSeverity.RECOVERABLE,
            phase=AgentPhase.CODING,
        )
        state.add_error(error)
        assert len(state.errors) == 1
        assert state.last_error == error
        assert state.metrics.errors_encountered == 1

    def test_fatal_error_updates_status(self) -> None:
        """Should update status on fatal error."""
        state = AgentState()
        state.status = AgentStatus.RUNNING
        error = AgentError(
            message="Fatal error",
            severity=ErrorSeverity.FATAL,
            phase=AgentPhase.CODING,
        )
        state.add_error(error)
        assert state.status == AgentStatus.FAILED
        assert state.phase == AgentPhase.FAILED

    def test_complete_task(self) -> None:
        """Should move task from pending to completed."""
        state = AgentState()
        state.pending_tasks = ["task1", "task2"]
        state.current_task = "task1"
        state.complete_task("task1")
        assert "task1" not in state.pending_tasks
        assert "task1" in state.completed_tasks
        assert state.current_task is None

    def test_is_running(self) -> None:
        """Should correctly identify running state."""
        state = AgentState()
        assert state.is_running() is False
        state.status = AgentStatus.RUNNING
        assert state.is_running() is True

    def test_is_finished(self) -> None:
        """Should correctly identify finished states."""
        state = AgentState()
        assert state.is_finished() is False
        state.status = AgentStatus.COMPLETED
        assert state.is_finished() is True
        state.status = AgentStatus.FAILED
        assert state.is_finished() is True

    def test_has_fatal_error(self) -> None:
        """Should detect fatal errors."""
        state = AgentState()
        assert state.has_fatal_error() is False
        state.add_error(AgentError(
            message="Warning",
            severity=ErrorSeverity.WARNING,
            phase=AgentPhase.CODING,
        ))
        assert state.has_fatal_error() is False
        state.add_error(AgentError(
            message="Fatal",
            severity=ErrorSeverity.FATAL,
            phase=AgentPhase.CODING,
        ))
        assert state.has_fatal_error() is True


class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_create_context(self, tmp_path: Path) -> None:
        """Should create context with required fields."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test task",
        )
        assert context.repo_root == tmp_path
        assert context.task_description == "Test task"

    def test_get_working_directory_default(self, tmp_path: Path) -> None:
        """Should return repo_root when no worktree."""
        context = AgentContext(repo_root=tmp_path)
        assert context.get_working_directory() == tmp_path

    def test_get_working_directory_worktree(self, tmp_path: Path) -> None:
        """Should return worktree_path when set."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        context = AgentContext(
            repo_root=tmp_path,
            worktree_path=worktree,
        )
        assert context.get_working_directory() == worktree


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
