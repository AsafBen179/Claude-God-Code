"""
QA Validation Loop Orchestration.

Part of Claude God Code - Autonomous Excellence

This module implements the master QA loop that orchestrates the
Review -> Test -> Fix cycle until requirements are met or max
iterations are reached.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .criteria import (
    IssueSeverity,
    QASignoff,
    QAStatus,
    get_qa_iteration_count,
    get_qa_signoff_status,
    is_qa_approved,
    save_qa_signoff_status,
)
from .fixer import clear_fix_request, load_fix_request, run_qa_fixer
from .reviewer import ReviewResult, run_qa_review

logger = logging.getLogger(__name__)


# Configuration
MAX_QA_ITERATIONS = 50
MAX_CONSECUTIVE_ERRORS = 3
RECURRING_ISSUE_THRESHOLD = 3


class QAPhase(Enum):
    """Phases in the QA loop."""

    REVIEW = "review"
    TEST = "test"
    FIX = "fix"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class IterationRecord:
    """Record of a single QA iteration."""

    iteration: int
    phase: QAPhase
    status: str
    duration_seconds: float
    issues_found: list[dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration": self.iteration,
            "phase": self.phase.value,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "issues_found": self.issues_found,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class QALoopState:
    """State of the QA loop execution."""

    current_iteration: int = 0
    current_phase: QAPhase = QAPhase.REVIEW
    consecutive_errors: int = 0
    history: list[IterationRecord] = field(default_factory=list)

    # Results
    is_approved: bool = False
    total_issues_found: int = 0
    total_fixes_applied: int = 0
    escalated_to_human: bool = False

    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def get_duration_seconds(self) -> float:
        """Get total loop duration."""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def add_iteration(self, record: IterationRecord) -> None:
        """Add an iteration to history."""
        self.history.append(record)
        self.total_issues_found += len(record.issues_found)

    def get_recurring_issues(self) -> list[dict[str, Any]]:
        """Get issues that have recurred multiple times."""
        issue_counts: dict[str, int] = {}

        for record in self.history:
            for issue in record.issues_found:
                title = issue.get("title", "Unknown")
                issue_counts[title] = issue_counts.get(title, 0) + 1

        recurring = [
            {"title": title, "occurrences": count}
            for title, count in issue_counts.items()
            if count >= RECURRING_ISSUE_THRESHOLD
        ]

        return sorted(recurring, key=lambda x: x["occurrences"], reverse=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_iteration": self.current_iteration,
            "current_phase": self.current_phase.value,
            "consecutive_errors": self.consecutive_errors,
            "history": [h.to_dict() for h in self.history],
            "is_approved": self.is_approved,
            "total_issues_found": self.total_issues_found,
            "total_fixes_applied": self.total_fixes_applied,
            "escalated_to_human": self.escalated_to_human,
            "duration_seconds": self.get_duration_seconds(),
        }


@dataclass
class QALoopConfig:
    """Configuration for QA loop execution."""

    max_iterations: int = MAX_QA_ITERATIONS
    max_consecutive_errors: int = MAX_CONSECUTIVE_ERRORS
    auto_fix: bool = True
    run_tests: bool = True
    require_impact_analysis: bool = True
    min_fix_confidence: float = 0.7

    # Callbacks
    on_iteration_start: Optional[callable] = None
    on_iteration_end: Optional[callable] = None
    on_phase_change: Optional[callable] = None


class QALoop:
    """Orchestrates the QA validation loop."""

    def __init__(
        self,
        repo_root: Path,
        spec_dir: Path,
        config: Optional[QALoopConfig] = None,
        impact_analyzer: Optional[Any] = None,
    ) -> None:
        """Initialize QA loop."""
        self.repo_root = repo_root
        self.spec_dir = spec_dir
        self.config = config or QALoopConfig()
        self.impact_analyzer = impact_analyzer
        self.state = QALoopState()

    def _notify_phase_change(self, phase: QAPhase, message: str = "") -> None:
        """Notify listeners of phase change."""
        self.state.current_phase = phase
        if self.config.on_phase_change:
            self.config.on_phase_change(phase, message)
        logger.info(f"QA Phase: {phase.value} - {message}")

    def _notify_iteration_start(self, iteration: int) -> None:
        """Notify listeners of iteration start."""
        if self.config.on_iteration_start:
            self.config.on_iteration_start(iteration)
        logger.info(f"Starting QA iteration {iteration}")

    def _notify_iteration_end(self, iteration: int, status: str) -> None:
        """Notify listeners of iteration end."""
        if self.config.on_iteration_end:
            self.config.on_iteration_end(iteration, status)
        logger.info(f"Completed QA iteration {iteration}: {status}")

    async def _run_review_phase(
        self,
        changed_files: Optional[list[str]] = None,
        spec_content: Optional[str] = None,
        task_description: str = "",
    ) -> tuple[str, ReviewResult]:
        """Run the review phase."""
        self._notify_phase_change(QAPhase.REVIEW, "Running code review")

        return await run_qa_review(
            repo_root=self.repo_root,
            spec_dir=self.spec_dir,
            changed_files=changed_files,
            spec_content=spec_content,
            task_description=task_description,
            impact_analyzer=self.impact_analyzer if self.config.require_impact_analysis else None,
            qa_session=self.state.current_iteration,
        )

    async def _run_fix_phase(self) -> tuple[str, Any]:
        """Run the fix phase."""
        self._notify_phase_change(QAPhase.FIX, "Applying fixes")

        status, result = await run_qa_fixer(
            repo_root=self.repo_root,
            spec_dir=self.spec_dir,
            fix_session=self.state.current_iteration,
            auto_apply=self.config.auto_fix,
        )

        if status == "fixed":
            self.state.total_fixes_applied += len(result.fixes_applied)

        return status, result

    async def _check_human_feedback(self) -> bool:
        """Check for pending human feedback and process it."""
        fix_content = load_fix_request(self.spec_dir)
        if not fix_content:
            return False

        logger.info("Human feedback detected, running fixer")
        self._notify_phase_change(QAPhase.FIX, "Processing human feedback")

        status, result = await run_qa_fixer(
            repo_root=self.repo_root,
            spec_dir=self.spec_dir,
            fix_session=0,  # Special session for human feedback
            auto_apply=False,  # Don't auto-apply human feedback
        )

        # Clear fix request after processing
        clear_fix_request(self.spec_dir)

        return status == "fixed"

    def _should_escalate(self) -> bool:
        """Check if loop should escalate to human review."""
        # Check for recurring issues
        recurring = self.state.get_recurring_issues()
        if recurring:
            logger.warning(f"Recurring issues detected: {recurring}")
            return True

        # Check for too many consecutive errors
        if self.state.consecutive_errors >= self.config.max_consecutive_errors:
            logger.warning(f"Max consecutive errors reached: {self.state.consecutive_errors}")
            return True

        return False

    def _create_escalation_report(self) -> Path:
        """Create escalation report for human review."""
        recurring = self.state.get_recurring_issues()

        content = ["# QA Escalation Report", ""]
        content.append(f"**Iterations**: {self.state.current_iteration}")
        content.append(f"**Duration**: {self.state.get_duration_seconds():.1f}s")
        content.append(f"**Total Issues**: {self.state.total_issues_found}")
        content.append("")

        if recurring:
            content.append("## Recurring Issues")
            content.append("")
            for issue in recurring:
                content.append(f"- **{issue['title']}**: {issue['occurrences']} occurrences")
            content.append("")

        content.append("## Iteration History")
        content.append("")
        for record in self.state.history[-10:]:  # Last 10 iterations
            content.append(f"### Iteration {record.iteration}")
            content.append(f"- Status: {record.status}")
            content.append(f"- Issues: {len(record.issues_found)}")
            content.append("")

        content.append("---")
        content.append("Manual intervention required to resolve these issues.")

        report_file = self.spec_dir / "QA_ESCALATION.md"
        report_file.write_text("\n".join(content), encoding="utf-8")

        return report_file

    async def run(
        self,
        changed_files: Optional[list[str]] = None,
        spec_content: Optional[str] = None,
        task_description: str = "",
    ) -> QALoopState:
        """
        Run the full QA validation loop.

        Returns the final state of the loop.
        """
        self.state.start_time = datetime.now()

        # Check if already approved
        if is_qa_approved(self.spec_dir):
            # But check for human feedback first
            if not load_fix_request(self.spec_dir):
                logger.info("QA already approved")
                self.state.is_approved = True
                self.state.current_phase = QAPhase.COMPLETE
                return self.state

        # Process any pending human feedback
        await self._check_human_feedback()

        # Get current iteration count
        self.state.current_iteration = get_qa_iteration_count(self.spec_dir)

        # Main loop
        while self.state.current_iteration < self.config.max_iterations:
            self.state.current_iteration += 1
            iteration_start = time.time()

            self._notify_iteration_start(self.state.current_iteration)

            try:
                # Review phase
                status, result = await self._run_review_phase(
                    changed_files=changed_files,
                    spec_content=spec_content,
                    task_description=task_description,
                )

                iteration_duration = time.time() - iteration_start

                # Record iteration
                record = IterationRecord(
                    iteration=self.state.current_iteration,
                    phase=QAPhase.REVIEW,
                    status=status,
                    duration_seconds=iteration_duration,
                    issues_found=[i.to_dict() for i in result.issues],
                )
                self.state.add_iteration(record)

                if status == "approved":
                    # Success!
                    self.state.is_approved = True
                    self.state.consecutive_errors = 0
                    self._notify_phase_change(QAPhase.COMPLETE, "QA approved")
                    self._notify_iteration_end(self.state.current_iteration, "approved")
                    break

                elif status == "rejected":
                    self.state.consecutive_errors = 0
                    self._notify_iteration_end(self.state.current_iteration, "rejected")

                    # Check for escalation
                    if self._should_escalate():
                        self.state.escalated_to_human = True
                        self._create_escalation_report()
                        self._notify_phase_change(QAPhase.FAILED, "Escalated to human")
                        break

                    # Run fix phase
                    if self.config.auto_fix:
                        fix_status, fix_result = await self._run_fix_phase()
                        if fix_status == "error":
                            logger.warning(f"Fix failed: {fix_result.message}")

                elif status == "error":
                    self.state.consecutive_errors += 1
                    self._notify_iteration_end(self.state.current_iteration, "error")

                    if self.state.consecutive_errors >= self.config.max_consecutive_errors:
                        self.state.escalated_to_human = True
                        self._create_escalation_report()
                        self._notify_phase_change(QAPhase.FAILED, "Max errors reached")
                        break

            except Exception as e:
                logger.exception(f"Error in QA iteration: {e}")
                self.state.consecutive_errors += 1

                record = IterationRecord(
                    iteration=self.state.current_iteration,
                    phase=self.state.current_phase,
                    status="exception",
                    duration_seconds=time.time() - iteration_start,
                    issues_found=[{"title": "Exception", "description": str(e)}],
                )
                self.state.add_iteration(record)

                if self.state.consecutive_errors >= self.config.max_consecutive_errors:
                    break

        # Finalize
        self.state.end_time = datetime.now()

        if not self.state.is_approved and not self.state.escalated_to_human:
            # Max iterations reached
            self.state.escalated_to_human = True
            self._create_escalation_report()
            self._notify_phase_change(QAPhase.FAILED, "Max iterations reached")

        return self.state


async def run_qa_validation_loop(
    repo_root: Path,
    spec_dir: Path,
    changed_files: Optional[list[str]] = None,
    spec_content: Optional[str] = None,
    task_description: str = "",
    impact_analyzer: Optional[Any] = None,
    config: Optional[QALoopConfig] = None,
) -> bool:
    """
    Run the full QA validation loop.

    This is the main entry point for QA validation.

    Args:
        repo_root: Repository root directory
        spec_dir: Specification directory
        changed_files: List of changed files to review
        spec_content: Content of the spec file
        task_description: Description of the task
        impact_analyzer: ImpactAnalyzer for God Mode checks
        config: QA loop configuration

    Returns:
        True if QA approved, False otherwise
    """
    loop = QALoop(
        repo_root=repo_root,
        spec_dir=spec_dir,
        config=config,
        impact_analyzer=impact_analyzer,
    )

    state = await loop.run(
        changed_files=changed_files,
        spec_content=spec_content,
        task_description=task_description,
    )

    logger.info(
        f"QA loop completed: approved={state.is_approved}, "
        f"iterations={state.current_iteration}, "
        f"duration={state.get_duration_seconds():.1f}s"
    )

    return state.is_approved


class QAIntegration:
    """Integration point between CoderAgent and QA Loop."""

    def __init__(
        self,
        repo_root: Path,
        impact_analyzer: Optional[Any] = None,
    ) -> None:
        """Initialize QA integration."""
        self.repo_root = repo_root
        self.impact_analyzer = impact_analyzer

    async def validate_changes(
        self,
        worktree_path: Path,
        spec_dir: Path,
        changed_files: list[str],
        task_description: str = "",
    ) -> bool:
        """
        Validate code changes through QA loop.

        Called automatically after CoderAgent makes changes.
        """
        config = QALoopConfig(
            auto_fix=True,
            require_impact_analysis=self.impact_analyzer is not None,
        )

        return await run_qa_validation_loop(
            repo_root=worktree_path,
            spec_dir=spec_dir,
            changed_files=changed_files,
            task_description=task_description,
            impact_analyzer=self.impact_analyzer,
            config=config,
        )
