"""
Tests for agents.coder module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from agents.base import AgentConfig, AgentContext, AgentStatus
from agents.coder import (
    CodeGenerationResult,
    CoderAgent,
    DiffChunker,
    FileChange,
    WorktreeIntegration,
    count_affected_files,
    validate_diff_size,
)
from agents.planner import ExecutionPlan, PlannedTask, TaskPriority, TaskType


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_create_file_change(self) -> None:
        """Should create file change with correct fields."""
        change = FileChange(
            path="src/auth.py",
            change_type="modify",
            original_content="old",
            new_content="new",
            diff_lines=10,
        )
        assert change.path == "src/auth.py"
        assert change.change_type == "modify"
        assert change.diff_lines == 10

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        change = FileChange(
            path="src/test.py",
            change_type="create",
            diff_lines=50,
        )
        d = change.to_dict()
        assert d["path"] == "src/test.py"
        assert d["change_type"] == "create"
        assert d["diff_lines"] == 50


class TestCodeGenerationResult:
    """Tests for CodeGenerationResult dataclass."""

    def test_successful_result(self) -> None:
        """Should create successful result."""
        result = CodeGenerationResult(
            success=True,
            message="Changes applied",
            files_created=["new.py"],
        )
        assert result.success is True
        assert "new.py" in result.files_created

    def test_failed_result(self) -> None:
        """Should create failed result with errors."""
        result = CodeGenerationResult(
            success=False,
            message="Failed",
            errors=["Syntax error"],
        )
        assert result.success is False
        assert "Syntax error" in result.errors

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        result = CodeGenerationResult(
            success=True,
            message="OK",
            total_diff_lines=100,
            was_chunked=True,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["total_diff_lines"] == 100
        assert d["was_chunked"] is True


class TestDiffChunker:
    """Tests for DiffChunker class."""

    def test_needs_chunking_small_diff(self) -> None:
        """Should not need chunking for small diff."""
        chunker = DiffChunker(max_lines=100)
        small_diff = "line1\nline2\nline3"
        assert chunker.needs_chunking(small_diff) is False

    def test_needs_chunking_large_diff(self) -> None:
        """Should need chunking for large diff."""
        chunker = DiffChunker(max_lines=10)
        large_diff = "\n".join([f"line{i}" for i in range(100)])
        assert chunker.needs_chunking(large_diff) is True

    def test_chunk_small_diff(self) -> None:
        """Should return single chunk for small diff."""
        chunker = DiffChunker(max_lines=100)
        diff = "line1\nline2\nline3"
        chunks = chunker.chunk_diff(diff)
        assert len(chunks) == 1
        assert chunks[0] == diff

    def test_chunk_large_diff(self) -> None:
        """Should split large diff into multiple chunks."""
        chunker = DiffChunker(max_lines=10)
        diff = "\n".join([f"line{i}" for i in range(50)])
        chunks = chunker.chunk_diff(diff)
        assert len(chunks) > 1

    def test_get_chunk_summary(self) -> None:
        """Should provide chunk summary."""
        chunker = DiffChunker(max_lines=10)
        chunks = ["chunk1\nline2", "chunk2\nline2"]
        summary = chunker.get_chunk_summary(chunks)
        assert "2 chunks" in summary


class TestWorktreeIntegration:
    """Tests for WorktreeIntegration class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize with repo root."""
        integration = WorktreeIntegration(tmp_path)
        assert integration.repo_root == tmp_path

    def test_get_working_directory_no_worktree(self, tmp_path: Path) -> None:
        """Should return repo root when no worktree."""
        integration = WorktreeIntegration(tmp_path)
        assert integration.get_working_directory() == tmp_path


class TestValidateDiffSize:
    """Tests for validate_diff_size function."""

    def test_valid_size(self) -> None:
        """Should validate small diff."""
        valid, msg = validate_diff_size("small diff", max_lines=100)
        assert valid is True
        assert "OK" in msg

    def test_invalid_size(self) -> None:
        """Should reject large diff."""
        large_diff = "\n".join([f"line{i}" for i in range(6000)])
        valid, msg = validate_diff_size(large_diff, max_lines=5000)
        assert valid is False
        assert "too large" in msg


class TestCountAffectedFiles:
    """Tests for count_affected_files function."""

    def test_count_single_file(self) -> None:
        """Should count single file in diff."""
        diff = "diff --git a/file.py b/file.py\n+new line"
        count = count_affected_files(diff)
        assert count == 1

    def test_count_multiple_files(self) -> None:
        """Should count multiple files in diff."""
        diff = """diff --git a/file1.py b/file1.py
+change1
diff --git a/file2.py b/file2.py
+change2
diff --git a/file3.py b/file3.py
+change3"""
        count = count_affected_files(diff)
        assert count == 3


class TestCoderAgent:
    """Tests for CoderAgent class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize with context."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test task",
        )
        coder = CoderAgent(context)
        assert coder.context == context
        assert coder._iteration_count == 0

    def test_init_with_plan(self, tmp_path: Path) -> None:
        """Should initialize with execution plan."""
        context = AgentContext(repo_root=tmp_path, task_description="Test")
        plan = ExecutionPlan(spec_id="test", task_description="Test plan")
        coder = CoderAgent(context, plan)
        assert coder.plan == plan

    def test_should_stop_when_finished(self, tmp_path: Path) -> None:
        """Should stop when state is finished."""
        context = AgentContext(repo_root=tmp_path, task_description="Test")
        coder = CoderAgent(context)
        coder.state.status = AgentStatus.COMPLETED
        assert coder._should_stop() is True

    def test_should_stop_max_iterations(self, tmp_path: Path) -> None:
        """Should stop at max iterations."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test",
            config=AgentConfig(max_iterations=5),
        )
        coder = CoderAgent(context)
        coder._iteration_count = 5
        assert coder._should_stop() is True

    def test_can_retry(self, tmp_path: Path) -> None:
        """Should allow retry when under limit."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test",
            config=AgentConfig(max_retries=3),
        )
        coder = CoderAgent(context)
        coder.state.metrics.retries_performed = 1
        assert coder._can_retry() is True

    def test_cannot_retry_after_max(self, tmp_path: Path) -> None:
        """Should not allow retry after max."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test",
            config=AgentConfig(max_retries=3),
        )
        coder = CoderAgent(context)
        coder.state.metrics.retries_performed = 3
        assert coder._can_retry() is False

    def test_should_auto_continue_disabled(self, tmp_path: Path) -> None:
        """Should not auto-continue when disabled."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test",
            config=AgentConfig(auto_continue=False),
        )
        coder = CoderAgent(context)
        assert coder._should_auto_continue() is False

    def test_should_auto_continue_with_remaining_tasks(self, tmp_path: Path) -> None:
        """Should auto-continue when tasks remain."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Test",
            config=AgentConfig(auto_continue=True, auto_continue_max=10),
        )
        plan = ExecutionPlan(spec_id="test", task_description="Test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH),
        ]
        coder = CoderAgent(context, plan)
        assert coder._should_auto_continue() is True

    def test_get_file_changes(self, tmp_path: Path) -> None:
        """Should return file changes."""
        context = AgentContext(repo_root=tmp_path, task_description="Test")
        coder = CoderAgent(context)
        coder._file_changes = [
            FileChange(path="test.py", change_type="create"),
        ]
        changes = coder.get_file_changes()
        assert len(changes) == 1


class TestCoderAgentAsync:
    """Async tests for CoderAgent."""

    @pytest.mark.asyncio
    async def test_apply_change_create(self, tmp_path: Path) -> None:
        """Should create new file."""
        context = AgentContext(repo_root=tmp_path, task_description="Test")
        coder = CoderAgent(context)

        change = FileChange(
            path="new_file.py",
            change_type="create",
            new_content="print('hello')",
        )

        result = await coder._apply_change(change)
        assert result is True
        assert (tmp_path / "new_file.py").exists()
        assert (tmp_path / "new_file.py").read_text() == "print('hello')"

    @pytest.mark.asyncio
    async def test_apply_change_modify(self, tmp_path: Path) -> None:
        """Should modify existing file."""
        # Create file first
        test_file = tmp_path / "existing.py"
        test_file.write_text("old content")

        context = AgentContext(repo_root=tmp_path, task_description="Test")
        coder = CoderAgent(context)

        change = FileChange(
            path="existing.py",
            change_type="modify",
            new_content="new content",
        )

        result = await coder._apply_change(change)
        assert result is True
        assert test_file.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_apply_change_delete(self, tmp_path: Path) -> None:
        """Should delete file."""
        # Create file first
        test_file = tmp_path / "to_delete.py"
        test_file.write_text("delete me")

        context = AgentContext(repo_root=tmp_path, task_description="Test")
        coder = CoderAgent(context)

        change = FileChange(
            path="to_delete.py",
            change_type="delete",
        )

        result = await coder._apply_change(change)
        assert result is True
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_update_metrics_for_change(self, tmp_path: Path) -> None:
        """Should update metrics correctly."""
        context = AgentContext(repo_root=tmp_path, task_description="Test")
        coder = CoderAgent(context)

        coder._update_metrics_for_change(FileChange(path="a.py", change_type="create"))
        assert coder.state.metrics.files_created == 1

        coder._update_metrics_for_change(FileChange(path="b.py", change_type="modify"))
        assert coder.state.metrics.files_modified == 1

        coder._update_metrics_for_change(FileChange(path="c.py", change_type="delete"))
        assert coder.state.metrics.files_deleted == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
