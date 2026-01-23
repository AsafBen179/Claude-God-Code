"""
Start Command Handler.

Part of Claude God Code - Autonomous Excellence

Handles starting new specifications and sessions.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from spec.models import get_specs_dir, create_spec_dir, Specification
from spec.discovery import ProjectDiscovery
from spec.pipeline import SpecPipeline
from spec.impact import ImpactAnalyzer

from agents.session import SessionOrchestrator
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.base import AgentConfig, AgentContext

from core.worktree import WorktreeManager

from ..formatter import TerminalFormatter

logger = logging.getLogger(__name__)


@dataclass
class StartOptions:
    """Options for the start command."""

    task_description: str
    project_dir: Path
    isolated: bool = True
    force: bool = False
    model: Optional[str] = None
    verbose: bool = False


@dataclass
class StartResult:
    """Result of the start command."""

    success: bool
    session_id: Optional[str] = None
    spec_dir: Optional[Path] = None
    message: str = ""
    error: Optional[str] = None


class StartCommand:
    """Command handler for starting new specifications."""

    def __init__(
        self,
        formatter: TerminalFormatter,
        orchestrator: Optional[SessionOrchestrator] = None,
    ) -> None:
        """Initialize start command."""
        self.formatter = formatter
        self._orchestrator = orchestrator

    def _get_orchestrator(self, project_dir: Path) -> SessionOrchestrator:
        """Get or create session orchestrator."""
        if self._orchestrator is None:
            self._orchestrator = SessionOrchestrator(project_dir)
        return self._orchestrator

    async def execute(self, options: StartOptions) -> StartResult:
        """Execute the start command."""
        self.formatter.header("Claude God Code", "New Specification")
        self.formatter.info(f"Task: {options.task_description}")

        try:
            discovery = ProjectDiscovery(options.project_dir)
            project_index = await discovery.discover()

            self.formatter.section("Project Analysis")
            self.formatter.key_value("Type", project_index.project_type)
            self.formatter.key_value("Files", project_index.file_count)

            impact_analyzer = ImpactAnalyzer(options.project_dir, project_index)
            impact = await impact_analyzer.analyze_impact(options.task_description)

            self.formatter.format_impact_analysis(impact)

            if impact.requires_migration_plan() and not options.force:
                self.formatter.warning("Breaking changes detected!")
                if not self.formatter.prompt_confirmation("Proceed with implementation?"):
                    return StartResult(
                        success=False,
                        message="Aborted by user",
                    )

            specs_dir = get_specs_dir(options.project_dir)
            spec_dir = create_spec_dir(specs_dir)

            self.formatter.success(f"Created spec: {spec_dir.name}")

            orchestrator = self._get_orchestrator(options.project_dir)
            session = orchestrator.create_session(
                task_description=options.task_description,
                spec_id=spec_dir.name,
            )

            self.formatter.success(f"Created session: {session.session_id[:8]}...")

            if options.isolated:
                self.formatter.info("Setting up isolated worktree...")
                worktree_manager = WorktreeManager(options.project_dir)
                worktree_path = worktree_manager.setup_worktree(
                    spec_dir.name,
                    f"spec/{spec_dir.name}",
                )
                self.formatter.key_value("Worktree", str(worktree_path))

            session = await orchestrator.start_session(session.session_id)

            await orchestrator.update_session_phase(
                session.session_id,
                "planning",
                "Analyzing task and creating implementation plan",
            )

            self.formatter.info("Implementation started...")

            return StartResult(
                success=True,
                session_id=session.session_id,
                spec_dir=spec_dir,
                message="Specification created successfully",
            )

        except Exception as e:
            logger.exception("Start command failed")
            self.formatter.error(f"Failed: {e}")
            return StartResult(
                success=False,
                error=str(e),
                message=f"Start failed: {e}",
            )

    async def run_implementation(
        self,
        session_id: str,
        spec_dir: Path,
        project_dir: Path,
        options: StartOptions,
    ) -> StartResult:
        """Run the full implementation pipeline."""
        orchestrator = self._get_orchestrator(project_dir)

        try:
            await orchestrator.update_session_phase(
                session_id,
                "implementation",
                "Running coder agent",
            )

            agent_config = AgentConfig(
                model=options.model or "claude-sonnet-4-20250514",
                max_turns=100,
                enable_self_critique=True,
            )

            context = AgentContext(
                repo_root=project_dir,
                spec_dir=spec_dir,
                task_description=options.task_description,
            )

            coder = CoderAgent(config=agent_config, context=context)
            state = await coder.run()

            if state.status.value == "completed":
                await orchestrator.complete_session(
                    session_id,
                    "Implementation completed",
                    state.metrics,
                    state.artifacts,
                )
                self.formatter.success("Implementation completed!")
                return StartResult(
                    success=True,
                    session_id=session_id,
                    spec_dir=spec_dir,
                    message="Implementation completed successfully",
                )
            else:
                error = state.last_error.message if state.last_error else "Unknown error"
                await orchestrator.fail_session(session_id, error)
                return StartResult(
                    success=False,
                    session_id=session_id,
                    spec_dir=spec_dir,
                    error=error,
                    message=f"Implementation failed: {error}",
                )

        except Exception as e:
            logger.exception("Implementation failed")
            await orchestrator.fail_session(session_id, str(e))
            return StartResult(
                success=False,
                session_id=session_id,
                spec_dir=spec_dir,
                error=str(e),
                message=f"Implementation failed: {e}",
            )
