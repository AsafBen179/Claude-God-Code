"""
Tests for agents.session module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from agents.base import AgentError, AgentMetrics, AgentPhase, ErrorSeverity
from agents.session import (
    ConversationMessage,
    SessionData,
    SessionOrchestrator,
    SessionStore,
)


class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""

    def test_create_message(self) -> None:
        """Should create message with correct fields."""
        msg = ConversationMessage(
            role="user",
            content="Hello",
        )
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        msg = ConversationMessage(
            role="assistant",
            content="Response",
            metadata={"key": "value"},
        )
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Response"
        assert d["metadata"]["key"] == "value"

    def test_from_dict(self) -> None:
        """Should create from dictionary."""
        data = {
            "role": "system",
            "content": "System message",
            "timestamp": datetime.now().isoformat(),
            "metadata": {},
        }
        msg = ConversationMessage.from_dict(data)
        assert msg.role == "system"
        assert msg.content == "System message"


class TestSessionData:
    """Tests for SessionData dataclass."""

    def test_create_session(self) -> None:
        """Should create session with correct fields."""
        session = SessionData(
            session_id="test-123",
            task_description="Test task",
        )
        assert session.session_id == "test-123"
        assert session.task_description == "Test task"
        assert session.status == "pending"

    def test_add_message(self) -> None:
        """Should add message to conversation."""
        session = SessionData(session_id="test")
        session.add_message("user", "Hello")
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"

    def test_get_duration(self) -> None:
        """Should calculate duration correctly."""
        session = SessionData(session_id="test")
        session.started_at = datetime.now()
        duration = session.get_duration_seconds()
        assert duration >= 0
        assert duration < 1

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        session = SessionData(
            session_id="test-456",
            spec_id="spec-001",
            task_description="Test",
            status="running",
        )
        session.add_message("user", "Test message")
        d = session.to_dict()
        assert d["session_id"] == "test-456"
        assert d["spec_id"] == "spec-001"
        assert len(d["messages"]) == 1

    def test_from_dict(self) -> None:
        """Should create from dictionary."""
        data = {
            "session_id": "test-789",
            "spec_id": None,
            "task_description": "Test task",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "status": "pending",
            "phase": "initializing",
            "result": None,
            "messages": [],
            "metrics": {},
            "artifacts": {},
            "errors": [],
        }
        session = SessionData.from_dict(data)
        assert session.session_id == "test-789"
        assert session.task_description == "Test task"


class TestSessionStore:
    """Tests for SessionStore class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize and create directory."""
        store = SessionStore(tmp_path / "sessions")
        assert (tmp_path / "sessions").exists()

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Should save and load session."""
        store = SessionStore(tmp_path / "sessions")
        session = SessionData(
            session_id="test-001",
            task_description="Test task",
        )
        store.save(session)

        loaded = store.load("test-001")
        assert loaded is not None
        assert loaded.session_id == "test-001"
        assert loaded.task_description == "Test task"

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Should return None for nonexistent session."""
        store = SessionStore(tmp_path / "sessions")
        loaded = store.load("nonexistent")
        assert loaded is None

    def test_delete(self, tmp_path: Path) -> None:
        """Should delete session."""
        store = SessionStore(tmp_path / "sessions")
        session = SessionData(session_id="to-delete", task_description="")
        store.save(session)

        result = store.delete("to-delete")
        assert result is True
        assert store.load("to-delete") is None

    def test_list_sessions(self, tmp_path: Path) -> None:
        """Should list all session IDs."""
        store = SessionStore(tmp_path / "sessions")
        store.save(SessionData(session_id="session-1", task_description=""))
        store.save(SessionData(session_id="session-2", task_description=""))

        sessions = store.list_sessions()
        assert "session-1" in sessions
        assert "session-2" in sessions

    def test_get_recent_sessions(self, tmp_path: Path) -> None:
        """Should get recent sessions."""
        store = SessionStore(tmp_path / "sessions")
        store.save(SessionData(session_id="old", task_description=""))
        store.save(SessionData(session_id="new", task_description=""))

        recent = store.get_recent_sessions(limit=1)
        assert len(recent) == 1


class TestSessionOrchestrator:
    """Tests for SessionOrchestrator class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize orchestrator."""
        orchestrator = SessionOrchestrator(tmp_path)
        assert orchestrator.repo_root == tmp_path

    def test_create_session(self, tmp_path: Path) -> None:
        """Should create new session."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test task")
        assert session.task_description == "Test task"
        assert session.status == "pending"
        assert len(session.messages) == 1  # Initial system message

    def test_get_session(self, tmp_path: Path) -> None:
        """Should get session by ID."""
        orchestrator = SessionOrchestrator(tmp_path)
        created = orchestrator.create_session("Test")
        retrieved = orchestrator.get_session(created.session_id)
        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    def test_get_active_sessions(self, tmp_path: Path) -> None:
        """Should return active sessions."""
        orchestrator = SessionOrchestrator(tmp_path)
        active = orchestrator.get_active_sessions()
        assert isinstance(active, list)


class TestSessionOrchestratorAsync:
    """Async tests for SessionOrchestrator."""

    @pytest.mark.asyncio
    async def test_start_session(self, tmp_path: Path) -> None:
        """Should start session."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test task")
        started = await orchestrator.start_session(session.session_id)
        assert started.status == "running"
        assert started.started_at is not None

    @pytest.mark.asyncio
    async def test_start_session_invalid_status(self, tmp_path: Path) -> None:
        """Should reject starting completed session."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        session.status = "completed"
        orchestrator.store.save(session)

        with pytest.raises(ValueError):
            await orchestrator.start_session(session.session_id)

    @pytest.mark.asyncio
    async def test_update_session_phase(self, tmp_path: Path) -> None:
        """Should update session phase."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        await orchestrator.start_session(session.session_id)
        await orchestrator.update_session_phase(session.session_id, "coding", "Started coding")

        updated = orchestrator.get_session(session.session_id)
        assert updated.phase == "coding"

    @pytest.mark.asyncio
    async def test_add_agent_message(self, tmp_path: Path) -> None:
        """Should add assistant message."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        await orchestrator.add_agent_message(session.session_id, "Agent response")

        updated = orchestrator.get_session(session.session_id)
        assert any(m.role == "assistant" for m in updated.messages)

    @pytest.mark.asyncio
    async def test_add_user_message(self, tmp_path: Path) -> None:
        """Should add user message."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        await orchestrator.add_user_message(session.session_id, "User input")

        updated = orchestrator.get_session(session.session_id)
        assert any(m.role == "user" and m.content == "User input" for m in updated.messages)

    @pytest.mark.asyncio
    async def test_record_error(self, tmp_path: Path) -> None:
        """Should record error in session."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        error = AgentError(
            message="Test error",
            severity=ErrorSeverity.RECOVERABLE,
            phase=AgentPhase.CODING,
        )
        await orchestrator.record_error(session.session_id, error)

        updated = orchestrator.get_session(session.session_id)
        assert len(updated.errors) == 1

    @pytest.mark.asyncio
    async def test_complete_session(self, tmp_path: Path) -> None:
        """Should complete session successfully."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        await orchestrator.start_session(session.session_id)
        completed = await orchestrator.complete_session(
            session.session_id,
            "Task completed",
            AgentMetrics(iterations=5),
        )
        assert completed.status == "completed"
        assert completed.result == "Task completed"
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_fail_session(self, tmp_path: Path) -> None:
        """Should fail session with reason."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        await orchestrator.start_session(session.session_id)
        failed = await orchestrator.fail_session(session.session_id, "Error occurred")
        assert failed.status == "failed"
        assert "Error occurred" in failed.result

    @pytest.mark.asyncio
    async def test_pause_and_resume_session(self, tmp_path: Path) -> None:
        """Should pause and resume session."""
        orchestrator = SessionOrchestrator(tmp_path)
        session = orchestrator.create_session("Test")
        await orchestrator.start_session(session.session_id)

        paused = await orchestrator.pause_session(session.session_id)
        assert paused.status == "paused"

        resumed = await orchestrator.resume_session(session.session_id)
        assert resumed.status == "running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
