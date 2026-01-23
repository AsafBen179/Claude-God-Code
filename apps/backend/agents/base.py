"""
Base agent configuration and types.

Part of Claude God Code - Autonomous Excellence

This module defines the foundational types and configurations for all agents
in the system. It provides a unified interface for agent behavior, error
handling, and state management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Protocol


class AgentPhase(Enum):
    """Phases an agent can be in during execution."""

    INITIALIZING = "initializing"
    PLANNING = "planning"
    CODING = "coding"
    REVIEWING = "reviewing"
    TESTING = "testing"
    COMPLETING = "completing"
    FAILED = "failed"
    PAUSED = "paused"


class AgentStatus(Enum):
    """Overall status of an agent."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorSeverity(Enum):
    """Severity levels for agent errors."""

    WARNING = "warning"
    RECOVERABLE = "recoverable"
    FATAL = "fatal"


@dataclass
class AgentError:
    """Represents an error that occurred during agent execution."""

    message: str
    severity: ErrorSeverity
    phase: AgentPhase
    timestamp: datetime = field(default_factory=datetime.now)
    exception: Optional[Exception] = None
    context: dict[str, Any] = field(default_factory=dict)

    def is_recoverable(self) -> bool:
        """Check if the error can be recovered from."""
        return self.severity != ErrorSeverity.FATAL

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 16384
    temperature: float = 0.7

    # Execution settings
    max_iterations: int = 50
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 300.0

    # Auto-continue settings
    auto_continue: bool = True
    auto_continue_max: int = 10

    # Safety settings
    require_impact_analysis: bool = True
    max_files_per_change: int = 20
    max_diff_lines: int = 5000

    # Memory settings
    use_session_memory: bool = True
    use_context_cache: bool = True

    # Worktree settings
    use_worktree_isolation: bool = True
    cleanup_on_success: bool = False
    cleanup_on_failure: bool = False

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if self.max_iterations < 1:
            issues.append("max_iterations must be at least 1")
        if self.max_retries < 0:
            issues.append("max_retries cannot be negative")
        if self.timeout_seconds <= 0:
            issues.append("timeout_seconds must be positive")
        if self.max_files_per_change < 1:
            issues.append("max_files_per_change must be at least 1")
        if not 0 <= self.temperature <= 2:
            issues.append("temperature must be between 0 and 2")

        return issues


@dataclass
class AgentMetrics:
    """Metrics collected during agent execution."""

    iterations: int = 0
    api_calls: int = 0
    tokens_used: int = 0
    files_modified: int = 0
    files_created: int = 0
    files_deleted: int = 0
    errors_encountered: int = 0
    retries_performed: int = 0

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def get_duration_seconds(self) -> float:
        """Get total execution duration in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "iterations": self.iterations,
            "api_calls": self.api_calls,
            "tokens_used": self.tokens_used,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "files_deleted": self.files_deleted,
            "errors_encountered": self.errors_encountered,
            "retries_performed": self.retries_performed,
            "duration_seconds": self.get_duration_seconds(),
        }


@dataclass
class AgentState:
    """Current state of an agent during execution."""

    status: AgentStatus = AgentStatus.IDLE
    phase: AgentPhase = AgentPhase.INITIALIZING

    # Execution tracking
    current_iteration: int = 0
    current_task: Optional[str] = None
    pending_tasks: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)

    # Error tracking
    errors: list[AgentError] = field(default_factory=list)
    last_error: Optional[AgentError] = None

    # Results
    result: Optional[str] = None
    artifacts: dict[str, Any] = field(default_factory=dict)

    # Metrics
    metrics: AgentMetrics = field(default_factory=AgentMetrics)

    def add_error(self, error: AgentError) -> None:
        """Add an error to the state."""
        self.errors.append(error)
        self.last_error = error
        self.metrics.errors_encountered += 1

        if error.severity == ErrorSeverity.FATAL:
            self.status = AgentStatus.FAILED
            self.phase = AgentPhase.FAILED

    def complete_task(self, task: str) -> None:
        """Mark a task as completed."""
        if task in self.pending_tasks:
            self.pending_tasks.remove(task)
        if task not in self.completed_tasks:
            self.completed_tasks.append(task)
        self.current_task = None

    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self.status == AgentStatus.RUNNING

    def is_finished(self) -> bool:
        """Check if agent has finished (success or failure)."""
        return self.status in (AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED)

    def has_fatal_error(self) -> bool:
        """Check if a fatal error has occurred."""
        return any(e.severity == ErrorSeverity.FATAL for e in self.errors)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "phase": self.phase.value,
            "current_iteration": self.current_iteration,
            "current_task": self.current_task,
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
            "errors": [e.to_dict() for e in self.errors],
            "result": self.result,
            "metrics": self.metrics.to_dict(),
        }


class AgentCallback(Protocol):
    """Protocol for agent callbacks."""

    def __call__(
        self,
        agent_id: str,
        phase: AgentPhase,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Called when agent state changes."""
        ...


@dataclass
class AgentContext:
    """Context provided to agents for execution."""

    # Paths
    repo_root: Path
    worktree_path: Optional[Path] = None
    spec_dir: Optional[Path] = None

    # Task information
    task_description: str = ""
    spec_content: Optional[str] = None

    # Configuration
    config: AgentConfig = field(default_factory=AgentConfig)

    # Callbacks
    on_progress: Optional[AgentCallback] = None
    on_error: Optional[AgentCallback] = None

    # Session data
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Memory context
    memory_context: dict[str, Any] = field(default_factory=dict)

    def get_working_directory(self) -> Path:
        """Get the directory where agent should work."""
        return self.worktree_path or self.repo_root

    def notify_progress(
        self,
        agent_id: str,
        phase: AgentPhase,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Notify progress if callback is set."""
        if self.on_progress:
            self.on_progress(agent_id, phase, message, data)

    def notify_error(
        self,
        agent_id: str,
        phase: AgentPhase,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Notify error if callback is set."""
        if self.on_error:
            self.on_error(agent_id, phase, message, data)


class BaseAgent:
    """Base class for all agents in Claude God Code."""

    def __init__(self, context: AgentContext) -> None:
        """Initialize agent with context."""
        self.context = context
        self.state = AgentState()
        self._agent_id = f"{self.__class__.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    @property
    def agent_id(self) -> str:
        """Get unique agent identifier."""
        return self._agent_id

    def _transition_phase(self, new_phase: AgentPhase, message: str = "") -> None:
        """Transition to a new phase."""
        old_phase = self.state.phase
        self.state.phase = new_phase

        self.context.notify_progress(
            self.agent_id,
            new_phase,
            message or f"Transitioned from {old_phase.value} to {new_phase.value}",
        )

    def _record_error(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE,
        exception: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentError:
        """Record an error during execution."""
        error = AgentError(
            message=message,
            severity=severity,
            phase=self.state.phase,
            exception=exception,
            context=context or {},
        )
        self.state.add_error(error)

        self.context.notify_error(
            self.agent_id,
            self.state.phase,
            message,
            {"severity": severity.value, "context": context},
        )

        return error

    async def run(self) -> AgentState:
        """Run the agent. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement run()")

    async def cancel(self) -> None:
        """Cancel the agent execution."""
        self.state.status = AgentStatus.CANCELLED
        self._transition_phase(AgentPhase.FAILED, "Agent cancelled")

    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.state

    def get_metrics(self) -> AgentMetrics:
        """Get current metrics."""
        return self.state.metrics
