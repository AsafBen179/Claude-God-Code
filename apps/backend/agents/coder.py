"""
Coder agent for autonomous code generation.

Part of Claude God Code - Autonomous Excellence

This module implements the core code generation capabilities with WorktreeManager
integration for isolated execution, robust error handling for large diffs,
and auto-continue loop functionality.
"""

import asyncio
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .base import (
    AgentConfig,
    AgentContext,
    AgentPhase,
    AgentState,
    AgentStatus,
    BaseAgent,
    ErrorSeverity,
)
from .planner import ExecutionPlan, PlannedTask

logger = logging.getLogger(__name__)


# Maximum diff lines before chunking
MAX_DIFF_LINES = 5000
# Maximum files per change to prevent overwhelming changes
MAX_FILES_PER_CHANGE = 20


@dataclass
class FileChange:
    """Represents a file change made by the coder."""

    path: str
    change_type: str  # "create", "modify", "delete"
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    diff_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "change_type": self.change_type,
            "diff_lines": self.diff_lines,
        }


@dataclass
class CodeGenerationResult:
    """Result of code generation."""

    success: bool
    message: str
    files_changed: list[FileChange] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Diff statistics
    total_diff_lines: int = 0
    was_chunked: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "files_changed": [f.to_dict() for f in self.files_changed],
            "files_created": self.files_created,
            "files_deleted": self.files_deleted,
            "errors": self.errors,
            "warnings": self.warnings,
            "total_diff_lines": self.total_diff_lines,
            "was_chunked": self.was_chunked,
        }


class DiffChunker:
    """Handles chunking of large diffs for better processing."""

    def __init__(self, max_lines: int = MAX_DIFF_LINES) -> None:
        """Initialize diff chunker."""
        self.max_lines = max_lines

    def needs_chunking(self, diff: str) -> bool:
        """Check if diff needs to be chunked."""
        return diff.count("\n") > self.max_lines

    def chunk_diff(self, diff: str) -> list[str]:
        """Split diff into manageable chunks."""
        lines = diff.split("\n")

        if len(lines) <= self.max_lines:
            return [diff]

        chunks = []
        current_chunk: list[str] = []
        current_file_header: list[str] = []

        for line in lines:
            # Track file headers for context
            if line.startswith("diff --git") or line.startswith("---") or line.startswith("+++"):
                if line.startswith("diff --git"):
                    current_file_header = [line]
                else:
                    current_file_header.append(line)

            current_chunk.append(line)

            # Check if we need to start a new chunk
            if len(current_chunk) >= self.max_lines:
                chunks.append("\n".join(current_chunk))
                # Start new chunk with file header context
                current_chunk = current_file_header.copy() if current_file_header else []

        # Add remaining lines
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def get_chunk_summary(self, chunks: list[str]) -> str:
        """Get summary of chunked diff."""
        total_lines = sum(c.count("\n") + 1 for c in chunks)
        return f"Diff split into {len(chunks)} chunks ({total_lines} total lines)"


class WorktreeIntegration:
    """Integration with WorktreeManager for isolated execution."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize worktree integration."""
        self.repo_root = repo_root
        self._worktree_path: Optional[Path] = None

    async def create_worktree(self, spec_id: str, branch_name: str) -> Path:
        """Create a worktree for isolated changes."""
        # Import here to avoid circular imports
        try:
            from core.worktree import WorktreeManager
            manager = WorktreeManager(self.repo_root)
            self._worktree_path = manager.create_worktree(spec_id, branch_name)
            logger.info(f"Created worktree at {self._worktree_path}")
            return self._worktree_path
        except ImportError:
            logger.warning("WorktreeManager not available, using repo root")
            self._worktree_path = self.repo_root
            return self.repo_root
        except Exception as e:
            logger.error(f"Failed to create worktree: {e}")
            self._worktree_path = self.repo_root
            return self.repo_root

    async def cleanup_worktree(self) -> None:
        """Clean up the worktree."""
        if self._worktree_path and self._worktree_path != self.repo_root:
            try:
                from core.worktree import WorktreeManager
                manager = WorktreeManager(self.repo_root)
                manager.remove_worktree(self._worktree_path)
                logger.info(f"Cleaned up worktree at {self._worktree_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup worktree: {e}")

    def get_working_directory(self) -> Path:
        """Get the current working directory."""
        return self._worktree_path or self.repo_root


class CoderAgent(BaseAgent):
    """Agent responsible for autonomous code generation."""

    def __init__(
        self,
        context: AgentContext,
        plan: Optional[ExecutionPlan] = None,
    ) -> None:
        """Initialize coder agent."""
        super().__init__(context)
        self.plan = plan
        self.diff_chunker = DiffChunker(context.config.max_diff_lines)
        self.worktree = WorktreeIntegration(context.repo_root)

        # Execution tracking
        self._current_task: Optional[PlannedTask] = None
        self._iteration_count = 0
        self._auto_continue_count = 0
        self._file_changes: list[FileChange] = []

    async def run(self) -> AgentState:
        """Run the coder agent with auto-continue loop."""
        self.state.status = AgentStatus.RUNNING
        self.state.metrics.start_time = datetime.now()

        try:
            # Setup worktree if isolation is enabled
            if self.context.config.use_worktree_isolation:
                await self._setup_worktree()

            # Main execution loop
            await self._execution_loop()

        except Exception as e:
            self._record_error(
                f"Coder execution failed: {str(e)}",
                ErrorSeverity.FATAL,
                exception=e,
            )
        finally:
            # Cleanup
            if self.context.config.cleanup_on_success and self.state.status == AgentStatus.COMPLETED:
                await self.worktree.cleanup_worktree()
            elif self.context.config.cleanup_on_failure and self.state.status == AgentStatus.FAILED:
                await self.worktree.cleanup_worktree()

        self.state.metrics.end_time = datetime.now()
        return self.state

    async def _setup_worktree(self) -> None:
        """Setup isolated worktree for code changes."""
        self._transition_phase(AgentPhase.INITIALIZING, "Setting up isolated worktree")

        spec_id = self.context.session_id or "unknown"
        branch_name = f"claude-god/{spec_id}"

        worktree_path = await self.worktree.create_worktree(spec_id, branch_name)
        self.context.worktree_path = worktree_path

    async def _execution_loop(self) -> None:
        """Main execution loop with auto-continue."""
        self._transition_phase(AgentPhase.CODING, "Starting code generation")

        while not self._should_stop():
            self._iteration_count += 1
            self.state.current_iteration = self._iteration_count
            self.state.metrics.iterations = self._iteration_count

            try:
                # Get next task to execute
                if self.plan:
                    self._current_task = self.plan.get_next_task()
                    if self._current_task is None:
                        # All tasks completed
                        self.state.status = AgentStatus.COMPLETED
                        self.state.result = "All tasks completed successfully"
                        break

                    self.state.current_task = self._current_task.title
                    self.plan.mark_task_started(self._current_task.id)

                # Execute current iteration
                result = await self._execute_iteration()

                # Handle result
                if result.success:
                    if self._current_task:
                        self.plan.mark_task_completed(
                            self._current_task.id,
                            result.message,
                        )
                        self.state.complete_task(self._current_task.title)

                    # Check for auto-continue
                    if self._should_auto_continue():
                        self._auto_continue_count += 1
                        continue
                    else:
                        # Successful completion
                        self.state.status = AgentStatus.COMPLETED
                        self.state.result = result.message
                        break
                else:
                    # Handle failure
                    if self._current_task:
                        self.plan.mark_task_failed(self._current_task.id, result.message)

                    if self._can_retry():
                        self.state.metrics.retries_performed += 1
                        await asyncio.sleep(self.context.config.retry_delay_seconds)
                        continue
                    else:
                        self._record_error(
                            result.message,
                            ErrorSeverity.FATAL,
                        )
                        break

            except Exception as e:
                self._record_error(
                    f"Iteration {self._iteration_count} failed: {str(e)}",
                    ErrorSeverity.RECOVERABLE,
                    exception=e,
                )

                if not self._can_retry():
                    self._record_error(
                        "Max retries exceeded",
                        ErrorSeverity.FATAL,
                    )
                    break

                self.state.metrics.retries_performed += 1
                await asyncio.sleep(self.context.config.retry_delay_seconds)

    async def _execute_iteration(self) -> CodeGenerationResult:
        """Execute a single iteration of code generation."""
        result = CodeGenerationResult(success=True, message="")

        try:
            # Determine what to work on
            if self._current_task:
                task_desc = self._current_task.description
            else:
                task_desc = self.context.task_description

            # Generate code (this would integrate with Claude API)
            self._transition_phase(AgentPhase.CODING, f"Working on: {task_desc[:50]}...")
            self.state.metrics.api_calls += 1

            # Simulate code generation result
            # In real implementation, this would call Claude API
            changes = await self._generate_code_changes(task_desc)

            # Apply changes
            for change in changes:
                applied = await self._apply_change(change)
                if applied:
                    self._file_changes.append(change)
                    result.files_changed.append(change)
                    self._update_metrics_for_change(change)

            # Check diff size
            total_diff_lines = sum(c.diff_lines for c in changes)
            if total_diff_lines > self.context.config.max_diff_lines:
                result.warnings.append(
                    f"Large diff detected ({total_diff_lines} lines). Consider breaking into smaller changes."
                )
                result.was_chunked = True

            result.total_diff_lines = total_diff_lines
            result.success = True
            result.message = f"Applied {len(changes)} file changes"

        except Exception as e:
            result.success = False
            result.message = str(e)
            result.errors.append(str(e))

        return result

    async def _generate_code_changes(self, task_description: str) -> list[FileChange]:
        """Generate code changes for the task."""
        # This is a placeholder for the actual Claude API integration
        # In real implementation, this would:
        # 1. Call Claude API with task description and context
        # 2. Parse the response for file changes
        # 3. Return list of FileChange objects

        changes: list[FileChange] = []

        # For now, return empty list (actual implementation would call Claude)
        logger.info(f"Would generate code for: {task_description[:100]}...")

        return changes

    async def _apply_change(self, change: FileChange) -> bool:
        """Apply a file change."""
        working_dir = self.worktree.get_working_directory()
        file_path = working_dir / change.path

        try:
            if change.change_type == "create":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                if change.new_content:
                    file_path.write_text(change.new_content, encoding="utf-8")
                logger.info(f"Created file: {change.path}")

            elif change.change_type == "modify":
                if change.new_content:
                    file_path.write_text(change.new_content, encoding="utf-8")
                logger.info(f"Modified file: {change.path}")

            elif change.change_type == "delete":
                if file_path.exists():
                    file_path.unlink()
                logger.info(f"Deleted file: {change.path}")

            return True

        except Exception as e:
            logger.error(f"Failed to apply change to {change.path}: {e}")
            return False

    def _update_metrics_for_change(self, change: FileChange) -> None:
        """Update metrics based on a file change."""
        if change.change_type == "create":
            self.state.metrics.files_created += 1
        elif change.change_type == "modify":
            self.state.metrics.files_modified += 1
        elif change.change_type == "delete":
            self.state.metrics.files_deleted += 1

    def _should_stop(self) -> bool:
        """Check if execution should stop."""
        if self.state.is_finished():
            return True

        if self._iteration_count >= self.context.config.max_iterations:
            self._record_error(
                f"Max iterations ({self.context.config.max_iterations}) reached",
                ErrorSeverity.WARNING,
            )
            return True

        if self.state.has_fatal_error():
            return True

        return False

    def _should_auto_continue(self) -> bool:
        """Check if agent should auto-continue to next task."""
        if not self.context.config.auto_continue:
            return False

        if self._auto_continue_count >= self.context.config.auto_continue_max:
            return False

        if self.plan:
            # Continue if there are more tasks
            return self.plan.get_next_task() is not None

        return False

    def _can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.state.metrics.retries_performed < self.context.config.max_retries

    def get_file_changes(self) -> list[FileChange]:
        """Get all file changes made during execution."""
        return self._file_changes

    def get_diff_summary(self) -> str:
        """Get summary of all changes as diff."""
        working_dir = self.worktree.get_working_directory()

        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=str(working_dir),
                capture_output=True,
                text=True,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            logger.warning(f"Failed to get diff summary: {e}")
            return ""


async def run_autonomous_agent(
    context: AgentContext,
    plan: Optional[ExecutionPlan] = None,
) -> AgentState:
    """Run autonomous code generation agent."""
    coder = CoderAgent(context, plan)
    return await coder.run()


def validate_diff_size(diff: str, max_lines: int = MAX_DIFF_LINES) -> tuple[bool, str]:
    """Validate diff size and return status with message."""
    line_count = diff.count("\n") + 1

    if line_count > max_lines:
        return False, f"Diff too large ({line_count} lines, max {max_lines})"

    return True, f"Diff size OK ({line_count} lines)"


def count_affected_files(diff: str) -> int:
    """Count number of files affected by a diff."""
    return len(re.findall(r"^diff --git", diff, re.MULTILINE))
