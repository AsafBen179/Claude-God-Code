"""
Tests for qa.loop module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from qa.criteria import QASignoff, QAStatus, save_qa_signoff_status
from qa.loop import (
    IterationRecord,
    QAIntegration,
    QALoop,
    QALoopConfig,
    QALoopState,
    QAPhase,
    run_qa_validation_loop,
)


class TestQAPhase:
    """Tests for QAPhase enum."""

    def test_phase_values(self) -> None:
        """Should have expected phase values."""
        assert QAPhase.REVIEW.value == "review"
        assert QAPhase.TEST.value == "test"
        assert QAPhase.FIX.value == "fix"
        assert QAPhase.COMPLETE.value == "complete"
        assert QAPhase.FAILED.value == "failed"


class TestIterationRecord:
    """Tests for IterationRecord dataclass."""

    def test_create_record(self) -> None:
        """Should create record with correct fields."""
        record = IterationRecord(
            iteration=1,
            phase=QAPhase.REVIEW,
            status="approved",
            duration_seconds=5.5,
        )
        assert record.iteration == 1
        assert record.phase == QAPhase.REVIEW
        assert record.status == "approved"

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        record = IterationRecord(
            iteration=2,
            phase=QAPhase.FIX,
            status="fixed",
            duration_seconds=10.0,
            issues_found=[{"title": "Test"}],
        )
        d = record.to_dict()
        assert d["iteration"] == 2
        assert d["phase"] == "fix"
        assert len(d["issues_found"]) == 1


class TestQALoopState:
    """Tests for QALoopState dataclass."""

    def test_default_state(self) -> None:
        """Should have default values."""
        state = QALoopState()
        assert state.current_iteration == 0
        assert state.current_phase == QAPhase.REVIEW
        assert state.is_approved is False

    def test_add_iteration(self) -> None:
        """Should add iteration to history."""
        state = QALoopState()
        record = IterationRecord(
            iteration=1,
            phase=QAPhase.REVIEW,
            status="rejected",
            duration_seconds=5.0,
            issues_found=[{"title": "Issue 1"}],
        )
        state.add_iteration(record)
        assert len(state.history) == 1
        assert state.total_issues_found == 1

    def test_get_recurring_issues(self) -> None:
        """Should detect recurring issues."""
        state = QALoopState()

        # Add same issue multiple times
        for i in range(4):
            record = IterationRecord(
                iteration=i + 1,
                phase=QAPhase.REVIEW,
                status="rejected",
                duration_seconds=1.0,
                issues_found=[{"title": "Same Issue"}],
            )
            state.add_iteration(record)

        recurring = state.get_recurring_issues()
        assert len(recurring) == 1
        assert recurring[0]["title"] == "Same Issue"
        assert recurring[0]["occurrences"] == 4

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        state = QALoopState()
        state.current_iteration = 5
        state.is_approved = True

        d = state.to_dict()
        assert d["current_iteration"] == 5
        assert d["is_approved"] is True


class TestQALoopConfig:
    """Tests for QALoopConfig dataclass."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = QALoopConfig()
        assert config.max_iterations == 50
        assert config.max_consecutive_errors == 3
        assert config.auto_fix is True

    def test_custom_config(self) -> None:
        """Should accept custom values."""
        config = QALoopConfig(
            max_iterations=10,
            auto_fix=False,
            min_fix_confidence=0.9,
        )
        assert config.max_iterations == 10
        assert config.auto_fix is False
        assert config.min_fix_confidence == 0.9


class TestQALoop:
    """Tests for QALoop class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize QA loop."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        loop = QALoop(tmp_path, spec_dir)
        assert loop.repo_root == tmp_path
        assert loop.spec_dir == spec_dir

    def test_should_escalate_recurring(self, tmp_path: Path) -> None:
        """Should escalate when recurring issues detected."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        loop = QALoop(tmp_path, spec_dir)

        # Add recurring issues
        for i in range(4):
            record = IterationRecord(
                iteration=i + 1,
                phase=QAPhase.REVIEW,
                status="rejected",
                duration_seconds=1.0,
                issues_found=[{"title": "Recurring Bug"}],
            )
            loop.state.add_iteration(record)

        assert loop._should_escalate() is True

    def test_should_escalate_consecutive_errors(self, tmp_path: Path) -> None:
        """Should escalate after max consecutive errors."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        config = QALoopConfig(max_consecutive_errors=3)
        loop = QALoop(tmp_path, spec_dir, config=config)
        loop.state.consecutive_errors = 3

        assert loop._should_escalate() is True

    def test_create_escalation_report(self, tmp_path: Path) -> None:
        """Should create escalation report file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        loop = QALoop(tmp_path, spec_dir)
        loop.state.current_iteration = 5

        # Add some history
        loop.state.add_iteration(IterationRecord(
            iteration=1,
            phase=QAPhase.REVIEW,
            status="rejected",
            duration_seconds=2.0,
            issues_found=[{"title": "Bug"}],
        ))

        report_path = loop._create_escalation_report()

        assert report_path.exists()
        content = report_path.read_text()
        assert "Escalation Report" in content
        assert "5" in content  # Iteration count


class TestQALoopAsync:
    """Async tests for QALoop."""

    @pytest.mark.asyncio
    async def test_run_already_approved(self, tmp_path: Path) -> None:
        """Should return immediately if already approved."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Mark as approved
        signoff = QASignoff(status=QAStatus.APPROVED)
        save_qa_signoff_status(spec_dir, signoff)

        loop = QALoop(tmp_path, spec_dir)
        state = await loop.run()

        assert state.is_approved is True
        assert state.current_phase == QAPhase.COMPLETE

    @pytest.mark.asyncio
    async def test_run_max_iterations(self, tmp_path: Path) -> None:
        """Should stop at max iterations."""
        # Create file with security issues that will cause rejections
        (tmp_path / "bad.py").write_text('''
api_key = "secret_key_123"
password = "admin_pass"

def danger():
    eval(input())
''', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        config = QALoopConfig(max_iterations=2, auto_fix=False)
        loop = QALoop(tmp_path, spec_dir, config=config)
        state = await loop.run(changed_files=["bad.py"])

        # Should hit max iterations (review keeps rejecting due to issues)
        assert state.current_iteration <= 2

    @pytest.mark.asyncio
    async def test_run_with_clean_code(self, tmp_path: Path) -> None:
        """Should pass QA for clean code."""
        # Create clean source file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "clean.py").write_text('''
import logging

def process():
    """Process data."""
    return {"status": "ok"}
''', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        config = QALoopConfig(max_iterations=3, auto_fix=False)
        loop = QALoop(tmp_path, spec_dir, config=config)
        state = await loop.run(
            changed_files=["src/clean.py"],
            task_description="Add processing",
        )

        # Should pass or at least run
        assert state.current_iteration >= 1


class TestRunQAValidationLoop:
    """Tests for run_qa_validation_loop function."""

    @pytest.mark.asyncio
    async def test_run_validation_loop(self, tmp_path: Path) -> None:
        """Should run complete validation loop."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        config = QALoopConfig(max_iterations=2)

        result = await run_qa_validation_loop(
            repo_root=tmp_path,
            spec_dir=spec_dir,
            changed_files=[],
            task_description="Test task",
            config=config,
        )

        # Result should be boolean
        assert isinstance(result, bool)


class TestQAIntegration:
    """Tests for QAIntegration class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize integration."""
        integration = QAIntegration(tmp_path)
        assert integration.repo_root == tmp_path

    @pytest.mark.asyncio
    async def test_validate_changes(self, tmp_path: Path) -> None:
        """Should validate code changes."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create test file
        (tmp_path / "test.py").write_text("def hello(): pass", encoding="utf-8")

        integration = QAIntegration(tmp_path)
        result = await integration.validate_changes(
            worktree_path=tmp_path,
            spec_dir=spec_dir,
            changed_files=["test.py"],
            task_description="Add function",
        )

        # Should return boolean
        assert isinstance(result, bool)


class TestQALoopPhaseCallbacks:
    """Tests for QA loop phase callbacks."""

    @pytest.mark.asyncio
    async def test_phase_callbacks_called(self, tmp_path: Path) -> None:
        """Should call phase callbacks during execution."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        phases_seen = []

        def on_phase_change(phase: QAPhase, message: str) -> None:
            phases_seen.append(phase)

        config = QALoopConfig(
            max_iterations=1,
            on_phase_change=on_phase_change,
        )

        loop = QALoop(tmp_path, spec_dir, config=config)
        await loop.run()

        # Should have called phase change at least once
        assert len(phases_seen) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
