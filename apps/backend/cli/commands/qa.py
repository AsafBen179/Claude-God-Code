"""
QA Command Handler.

Part of Claude God Code - Autonomous Excellence

Handles running QA validation loops and displaying QA status.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from spec.models import get_specs_dir
from qa.loop import QALoop, QALoopConfig, QALoopState, QAPhase
from qa.criteria import get_qa_signoff_status, QASignoff
from qa.fixer import run_qa_fixer

from ..formatter import TerminalFormatter

logger = logging.getLogger(__name__)


@dataclass
class QAOptions:
    """Options for the QA command."""

    project_dir: Path
    spec_name: str
    max_iterations: int = 50
    auto_fix: bool = False
    verbose: bool = False


@dataclass
class QAResult:
    """Result of the QA command."""

    success: bool
    approved: bool = False
    iterations: int = 0
    issues_found: int = 0
    fixes_applied: int = 0
    message: str = ""
    state: Optional[QALoopState] = None


class QACommand:
    """Command handler for QA validation."""

    def __init__(
        self,
        formatter: TerminalFormatter,
    ) -> None:
        """Initialize QA command."""
        self.formatter = formatter

    async def execute(self, options: QAOptions) -> QAResult:
        """Execute the QA command."""
        specs_dir = get_specs_dir(options.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, options.spec_name)

        if spec_dir is None:
            self.formatter.error(f"Spec not found: {options.spec_name}")
            return QAResult(
                success=False,
                message=f"Spec not found: {options.spec_name}",
            )

        self.formatter.header("Claude God Code", f"QA Validation: {spec_dir.name}")

        config = QALoopConfig(
            max_iterations=options.max_iterations,
            auto_fix=options.auto_fix,
            verbose=options.verbose,
            on_phase_change=self._create_phase_callback(),
            on_iteration_complete=self._create_iteration_callback(),
        )

        qa_loop = QALoop(options.project_dir, spec_dir, config=config)

        self.formatter.info("Starting QA validation loop...")
        self.formatter.section("Progress")

        try:
            state = await qa_loop.run()

            signoff = get_qa_signoff_status(spec_dir)
            if signoff:
                self.formatter.format_qa_status(signoff, state)

            if state.is_approved:
                self.formatter.success("QA validation passed!")
                return QAResult(
                    success=True,
                    approved=True,
                    iterations=state.current_iteration,
                    issues_found=state.total_issues_found,
                    fixes_applied=state.total_fixes_applied,
                    message="QA validation passed",
                    state=state,
                )
            else:
                self.formatter.error("QA validation failed")
                return QAResult(
                    success=True,
                    approved=False,
                    iterations=state.current_iteration,
                    issues_found=state.total_issues_found,
                    fixes_applied=state.total_fixes_applied,
                    message="QA validation failed",
                    state=state,
                )

        except Exception as e:
            logger.exception("QA validation failed")
            self.formatter.error(f"QA validation error: {e}")
            return QAResult(
                success=False,
                message=f"QA validation error: {e}",
            )

    def _find_spec_dir(self, specs_dir: Path, spec_name: str) -> Optional[Path]:
        """Find a spec directory by name or number."""
        if not specs_dir.exists():
            return None

        for spec_path in specs_dir.glob("*"):
            if spec_path.is_dir():
                if spec_path.name == spec_name:
                    return spec_path
                if spec_path.name.startswith(f"{spec_name}-"):
                    return spec_path
                if spec_name in spec_path.name:
                    return spec_path

        return None

    def _create_phase_callback(self) -> Callable[[QAPhase, str], None]:
        """Create callback for phase changes."""
        def on_phase_change(phase: QAPhase, message: str) -> None:
            level = "info"
            if phase == QAPhase.FAILED:
                level = "error"
            elif phase == QAPhase.COMPLETE:
                level = "info"
            self.formatter.stream_log(f"[{phase.value}] {message}", level=level)

        return on_phase_change

    def _create_iteration_callback(self) -> Callable[[int, str], None]:
        """Create callback for iteration completions."""
        def on_iteration_complete(iteration: int, status: str) -> None:
            self.formatter.stream_log(
                f"Iteration {iteration} complete: {status}",
                level="info",
            )

        return on_iteration_complete

    async def run_fix_only(self, options: QAOptions) -> QAResult:
        """Run only the fix phase without full QA loop."""
        specs_dir = get_specs_dir(options.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, options.spec_name)

        if spec_dir is None:
            self.formatter.error(f"Spec not found: {options.spec_name}")
            return QAResult(
                success=False,
                message=f"Spec not found: {options.spec_name}",
            )

        self.formatter.header("Claude God Code", f"Fix Issues: {spec_dir.name}")

        signoff = get_qa_signoff_status(spec_dir)
        if not signoff or not signoff.issues_found:
            self.formatter.info("No issues found to fix")
            return QAResult(
                success=True,
                approved=True,
                message="No issues to fix",
            )

        self.formatter.info(f"Found {len(signoff.issues_found)} issues to fix")

        try:
            status, fix_result = await run_qa_fixer(
                repo_root=options.project_dir,
                spec_dir=spec_dir,
                auto_apply=options.auto_fix,
            )

            self.formatter.format_fix_result(fix_result)

            return QAResult(
                success=fix_result.success,
                approved=fix_result.ready_for_revalidation,
                fixes_applied=len(fix_result.fixes_applied),
                issues_found=len(signoff.issues_found),
                message=fix_result.message,
            )

        except Exception as e:
            logger.exception("Fix operation failed")
            self.formatter.error(f"Fix operation failed: {e}")
            return QAResult(
                success=False,
                message=f"Fix operation failed: {e}",
            )

    async def show_status(self, options: QAOptions) -> QAResult:
        """Show QA status without running the loop."""
        specs_dir = get_specs_dir(options.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, options.spec_name)

        if spec_dir is None:
            self.formatter.error(f"Spec not found: {options.spec_name}")
            return QAResult(
                success=False,
                message=f"Spec not found: {options.spec_name}",
            )

        signoff = get_qa_signoff_status(spec_dir)
        if signoff:
            self.formatter.format_qa_status(signoff)
            return QAResult(
                success=True,
                approved=signoff.status.value == "approved",
                issues_found=len(signoff.issues_found) if signoff.issues_found else 0,
                message=f"QA status: {signoff.status.value}",
            )
        else:
            self.formatter.info("No QA status found for this spec")
            return QAResult(
                success=True,
                message="No QA status found",
            )
