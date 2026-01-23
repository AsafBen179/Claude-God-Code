"""
Session orchestrator for agent execution.

Part of Claude God Code - Autonomous Excellence

This module manages agent sessions, including state persistence, conversation
management, and post-session processing. It coordinates the lifecycle of
agent execution from initialization to completion.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .base import (
    AgentConfig,
    AgentContext,
    AgentError,
    AgentMetrics,
    AgentPhase,
    AgentState,
    AgentStatus,
    ErrorSeverity,
)

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """A message in the agent conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationMessage":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionData:
    """Data associated with an agent session."""

    session_id: str
    spec_id: Optional[str] = None
    task_description: str = ""

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # State tracking
    status: str = "pending"
    phase: str = "initializing"
    result: Optional[str] = None

    # Conversation
    messages: list[ConversationMessage] = field(default_factory=list)

    # Metrics
    metrics: dict[str, Any] = field(default_factory=dict)

    # Artifacts produced
    artifacts: dict[str, Any] = field(default_factory=dict)

    # Error information
    errors: list[dict[str, Any]] = field(default_factory=list)

    def add_message(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add a message to the conversation."""
        self.messages.append(
            ConversationMessage(
                role=role,
                content=content,
                metadata=metadata or {},
            )
        )

    def get_duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "spec_id": self.spec_id,
            "task_description": self.task_description,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "phase": self.phase,
            "result": self.result,
            "messages": [m.to_dict() for m in self.messages],
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create from dictionary."""
        session = cls(
            session_id=data["session_id"],
            spec_id=data.get("spec_id"),
            task_description=data.get("task_description", ""),
            status=data.get("status", "pending"),
            phase=data.get("phase", "initializing"),
            result=data.get("result"),
            metrics=data.get("metrics", {}),
            artifacts=data.get("artifacts", {}),
            errors=data.get("errors", []),
        )

        session.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            session.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            session.completed_at = datetime.fromisoformat(data["completed_at"])

        session.messages = [
            ConversationMessage.from_dict(m) for m in data.get("messages", [])
        ]

        return session


class SessionStore:
    """Persistent storage for session data."""

    def __init__(self, sessions_dir: Path) -> None:
        """Initialize session store."""
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, SessionData] = {}

    def _get_session_path(self, session_id: str) -> Path:
        """Get path to session file."""
        return self.sessions_dir / f"{session_id}.json"

    def save(self, session: SessionData) -> None:
        """Save session to disk."""
        path = self._get_session_path(session.session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2)
        self._cache[session.session_id] = session

    def load(self, session_id: str) -> Optional[SessionData]:
        """Load session from disk."""
        if session_id in self._cache:
            return self._cache[session_id]

        path = self._get_session_path(session_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            session = SessionData.from_dict(data)
            self._cache[session_id] = session
            return session
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete session from disk."""
        path = self._get_session_path(session_id)
        if path.exists():
            path.unlink()
        self._cache.pop(session_id, None)
        return True

    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        return [p.stem for p in self.sessions_dir.glob("*.json")]

    def get_recent_sessions(self, limit: int = 10) -> list[SessionData]:
        """Get most recent sessions."""
        sessions = []
        for session_id in self.list_sessions():
            session = self.load(session_id)
            if session:
                sessions.append(session)

        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions[:limit]


class SessionOrchestrator:
    """Orchestrates agent sessions from start to finish."""

    def __init__(
        self,
        repo_root: Path,
        sessions_dir: Optional[Path] = None,
        config: Optional[AgentConfig] = None,
    ) -> None:
        """Initialize session orchestrator."""
        self.repo_root = repo_root
        self.sessions_dir = sessions_dir or repo_root / ".claude-god" / "sessions"
        self.store = SessionStore(self.sessions_dir)
        self.config = config or AgentConfig()

        self._active_sessions: dict[str, SessionData] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def create_session(
        self,
        task_description: str,
        spec_id: Optional[str] = None,
    ) -> SessionData:
        """Create a new agent session."""
        session_id = str(uuid.uuid4())

        session = SessionData(
            session_id=session_id,
            spec_id=spec_id,
            task_description=task_description,
        )

        # Add initial system message
        session.add_message(
            "system",
            f"Session initialized for task: {task_description}",
        )

        self.store.save(session)
        logger.info(f"Created session {session_id} for task: {task_description[:50]}...")

        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID."""
        return self.store.load(session_id)

    async def start_session(
        self,
        session_id: str,
        agent_context: Optional[AgentContext] = None,
    ) -> SessionData:
        """Start an agent session."""
        session = self.store.load(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        if session.status not in ("pending", "paused"):
            raise ValueError(f"Session {session_id} cannot be started (status: {session.status})")

        # Get or create lock for this session
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()

        async with self._locks[session_id]:
            session.started_at = datetime.now()
            session.status = "running"
            session.phase = "initializing"

            self._active_sessions[session_id] = session

            session.add_message(
                "system",
                "Session started",
                {"started_at": session.started_at.isoformat()},
            )

            self.store.save(session)

        logger.info(f"Started session {session_id}")
        return session

    async def update_session_phase(
        self,
        session_id: str,
        phase: str,
        message: Optional[str] = None,
    ) -> None:
        """Update session phase."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            return

        session.phase = phase
        if message:
            session.add_message("system", message, {"phase": phase})

        self.store.save(session)

    async def add_agent_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add an assistant message to the session."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            return

        session.add_message("assistant", content, metadata)
        self.store.save(session)

    async def add_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a user message to the session."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            return

        session.add_message("user", content, metadata)
        self.store.save(session)

    async def record_error(
        self,
        session_id: str,
        error: AgentError,
    ) -> None:
        """Record an error in the session."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            return

        session.errors.append(error.to_dict())
        session.add_message(
            "system",
            f"Error: {error.message}",
            {"severity": error.severity.value},
        )

        if error.severity == ErrorSeverity.FATAL:
            session.status = "failed"
            session.phase = "failed"

        self.store.save(session)

    async def complete_session(
        self,
        session_id: str,
        result: str,
        metrics: Optional[AgentMetrics] = None,
        artifacts: Optional[dict[str, Any]] = None,
    ) -> SessionData:
        """Complete a session successfully."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.completed_at = datetime.now()
        session.status = "completed"
        session.phase = "completed"
        session.result = result

        if metrics:
            session.metrics = metrics.to_dict()

        if artifacts:
            session.artifacts = artifacts

        session.add_message(
            "system",
            f"Session completed: {result}",
            {"completed_at": session.completed_at.isoformat()},
        )

        self._active_sessions.pop(session_id, None)
        self.store.save(session)

        logger.info(f"Completed session {session_id}: {result[:50]}...")
        return session

    async def fail_session(
        self,
        session_id: str,
        reason: str,
        metrics: Optional[AgentMetrics] = None,
    ) -> SessionData:
        """Mark a session as failed."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.completed_at = datetime.now()
        session.status = "failed"
        session.phase = "failed"
        session.result = f"Failed: {reason}"

        if metrics:
            session.metrics = metrics.to_dict()

        session.add_message(
            "system",
            f"Session failed: {reason}",
            {"completed_at": session.completed_at.isoformat()},
        )

        self._active_sessions.pop(session_id, None)
        self.store.save(session)

        logger.error(f"Failed session {session_id}: {reason}")
        return session

    async def pause_session(self, session_id: str) -> SessionData:
        """Pause a running session."""
        session = self._active_sessions.get(session_id)
        if session is None:
            session = self.store.load(session_id)

        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.status = "paused"
        session.add_message("system", "Session paused")

        self.store.save(session)
        logger.info(f"Paused session {session_id}")

        return session

    async def resume_session(self, session_id: str) -> SessionData:
        """Resume a paused session."""
        session = self.store.load(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        if session.status != "paused":
            raise ValueError(f"Session {session_id} is not paused (status: {session.status})")

        session.status = "running"
        session.add_message("system", "Session resumed")

        self._active_sessions[session_id] = session
        self.store.save(session)

        logger.info(f"Resumed session {session_id}")
        return session

    def get_active_sessions(self) -> list[SessionData]:
        """Get all active sessions."""
        return list(self._active_sessions.values())

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """Cleanup sessions that have been running too long."""
        cleaned = 0
        cutoff = datetime.now()

        for session in list(self._active_sessions.values()):
            if session.started_at:
                age_hours = (cutoff - session.started_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    session.status = "failed"
                    session.result = "Session timed out"
                    session.completed_at = cutoff
                    self.store.save(session)
                    self._active_sessions.pop(session.session_id, None)
                    cleaned += 1
                    logger.warning(f"Cleaned up stale session {session.session_id}")

        return cleaned


async def run_agent_session(
    orchestrator: SessionOrchestrator,
    session_id: str,
    agent_factory: Any,  # Callable that creates an agent
    context: AgentContext,
) -> SessionData:
    """Run a complete agent session with proper lifecycle management."""
    session = await orchestrator.start_session(session_id)

    try:
        # Create and run agent
        agent = agent_factory(context)
        state = await agent.run()

        # Determine outcome
        if state.status == AgentStatus.COMPLETED:
            session = await orchestrator.complete_session(
                session_id,
                state.result or "Task completed successfully",
                state.metrics,
                state.artifacts,
            )
        else:
            reason = state.last_error.message if state.last_error else "Unknown error"
            session = await orchestrator.fail_session(
                session_id,
                reason,
                state.metrics,
            )

    except Exception as e:
        logger.exception(f"Exception in session {session_id}")
        session = await orchestrator.fail_session(
            session_id,
            str(e),
        )

    return session


async def post_session_processing(
    orchestrator: SessionOrchestrator,
    session_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Perform post-session processing tasks."""
    session = orchestrator.get_session(session_id)
    if session is None:
        return {"error": f"Session {session_id} not found"}

    results: dict[str, Any] = {
        "session_id": session_id,
        "status": session.status,
        "duration_seconds": session.get_duration_seconds(),
    }

    # Only process completed sessions
    if session.status != "completed":
        results["skipped"] = True
        results["reason"] = f"Session not completed (status: {session.status})"
        return results

    # Collect statistics
    results["metrics"] = session.metrics
    results["artifacts"] = list(session.artifacts.keys())
    results["message_count"] = len(session.messages)
    results["error_count"] = len(session.errors)

    # Log summary
    logger.info(
        f"Post-session processing for {session_id}: "
        f"{results['duration_seconds']:.1f}s, "
        f"{results['message_count']} messages, "
        f"{results['error_count']} errors"
    )

    return results
