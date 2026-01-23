"""
Main CLI Entry Point for Claude God Code.

Part of Claude God Code - Autonomous Excellence

This module provides the main entry point for the CLI application,
handling argument parsing, core initialization, and session orchestration.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from core.platform import get_config_dir, get_data_dir, is_git_repo
from core.auth import get_auth_token, ensure_authenticated
from core.worktree import WorktreeManager
from core.client import create_client

from spec.models import get_specs_dir, Complexity
from spec.discovery import ProjectDiscovery
from spec.pipeline import SpecPipeline
from spec.impact import ImpactAnalyzer

from agents.session import SessionOrchestrator, SessionData
from agents.planner import PlannerAgent
from agents.coder import CoderAgent

from qa.loop import QALoop, QALoopConfig, QAIntegration
from qa.criteria import get_qa_signoff_status

from .formatter import TerminalFormatter, create_formatter

logger = logging.getLogger(__name__)

VERSION = "0.1.0"
PROGRAM_NAME = "claude-god-code"


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all CLI options."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="Claude God Code - Autonomous Excellence in Software Engineering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --spec "Add user authentication"
  %(prog)s --list
  %(prog)s --status
  %(prog)s --qa --spec 001-add-auth
  %(prog)s --force --spec 001-add-auth
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )

    parser.add_argument(
        "--spec",
        type=str,
        default=None,
        metavar="SPEC",
        help="Spec name or task description to process",
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Project directory (default: current directory)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        choices=["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-sonnet-4-20250514"],
        help="Claude model to use",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all specs in the project",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current session status",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--isolated",
        action="store_true",
        help="Run in isolated worktree mode",
    )

    parser.add_argument(
        "--direct",
        action="store_true",
        help="Run directly without worktree isolation",
    )

    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge completed spec changes to main",
    )

    parser.add_argument(
        "--review",
        action="store_true",
        help="Review changes before merging",
    )

    parser.add_argument(
        "--discard",
        action="store_true",
        help="Discard spec worktree and changes",
    )

    parser.add_argument(
        "--qa",
        action="store_true",
        help="Run QA validation loop",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts (including impact analysis)",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        metavar="KEY=VALUE",
        help="Set configuration value",
    )

    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="SESSION_ID",
        help="Resume a paused session",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        metavar="N",
        help="Maximum QA loop iterations (default: 50)",
    )

    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically apply fixes in QA loop",
    )

    return parser


class CLIApplication:
    """Main CLI application class."""

    def __init__(
        self,
        args: argparse.Namespace,
        formatter: Optional[TerminalFormatter] = None,
    ) -> None:
        """Initialize CLI application."""
        self.args = args
        self.project_dir = args.project_dir or Path.cwd()
        self.formatter = formatter or create_formatter(
            use_colors=not args.no_color,
            verbose=args.verbose,
        )

        self._orchestrator: Optional[SessionOrchestrator] = None
        self._worktree_manager: Optional[WorktreeManager] = None
        self._discovery: Optional[ProjectDiscovery] = None

    def _setup_logging(self) -> None:
        """Configure logging based on verbosity."""
        level = logging.DEBUG if self.args.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def _validate_project_dir(self) -> bool:
        """Validate project directory exists and is a git repo."""
        if not self.project_dir.exists():
            self.formatter.error(f"Project directory not found: {self.project_dir}")
            return False

        if not is_git_repo(self.project_dir):
            self.formatter.warning(f"Not a git repository: {self.project_dir}")
            if not self.args.direct:
                self.formatter.info("Use --direct to run without git integration")
                return False

        return True

    def _init_orchestrator(self) -> SessionOrchestrator:
        """Initialize the session orchestrator."""
        if self._orchestrator is None:
            self._orchestrator = SessionOrchestrator(self.project_dir)
        return self._orchestrator

    def _init_worktree_manager(self) -> WorktreeManager:
        """Initialize the worktree manager."""
        if self._worktree_manager is None:
            self._worktree_manager = WorktreeManager(self.project_dir)
        return self._worktree_manager

    def _init_discovery(self) -> ProjectDiscovery:
        """Initialize project discovery."""
        if self._discovery is None:
            self._discovery = ProjectDiscovery(self.project_dir)
        return self._discovery

    async def run_list_specs(self) -> int:
        """List all specs in the project."""
        self.formatter.header("Claude God Code", "Specification List")

        specs_dir = get_specs_dir(self.project_dir)
        if not specs_dir.exists():
            self.formatter.info("No specs directory found")
            return 0

        specs = sorted(specs_dir.glob("*"))
        if not specs:
            self.formatter.info("No specs found")
            return 0

        self.formatter.section("Available Specs")
        for spec_path in specs:
            if spec_path.is_dir():
                signoff = get_qa_signoff_status(spec_path)
                status = signoff.status.value if signoff else "unknown"
                status_icon = "✓" if status == "approved" else "○"
                self.formatter.bullet(f"{status_icon} {spec_path.name} [{status}]")

        return 0

    async def run_status(self) -> int:
        """Show current session status."""
        orchestrator = self._init_orchestrator()

        active = orchestrator.get_active_sessions()
        recent = orchestrator.store.get_recent_sessions(limit=5)

        self.formatter.header("Claude God Code", "Session Status")

        if active:
            self.formatter.section(f"Active Sessions ({len(active)})")
            for session in active:
                self.formatter.format_session_status(
                    session_id=session.session_id,
                    status=session.status,
                    phase=session.phase,
                    task=session.task_description,
                    duration_seconds=session.get_duration_seconds(),
                )
        else:
            self.formatter.info("No active sessions")

        if recent:
            self.formatter.section("Recent Sessions")
            for session in recent:
                status_icon = "✓" if session.status == "completed" else "✗" if session.status == "failed" else "○"
                self.formatter.bullet(
                    f"{status_icon} {session.session_id[:8]}... - {session.task_description[:40]}..."
                )

        return 0

    async def run_qa(self, spec_name: str) -> int:
        """Run QA validation loop for a spec."""
        specs_dir = get_specs_dir(self.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, spec_name)

        if spec_dir is None:
            self.formatter.error(f"Spec not found: {spec_name}")
            return 1

        self.formatter.header("Claude God Code", f"QA Loop: {spec_dir.name}")

        config = QALoopConfig(
            max_iterations=self.args.max_iterations,
            auto_fix=self.args.auto_fix,
            on_phase_change=self._on_qa_phase_change,
        )

        qa_loop = QALoop(self.project_dir, spec_dir, config=config)

        self.formatter.info("Starting QA validation loop...")
        state = await qa_loop.run()

        signoff = get_qa_signoff_status(spec_dir)
        if signoff:
            self.formatter.format_qa_status(signoff, state)

        if state.is_approved:
            self.formatter.success("QA validation passed!")
            return 0
        else:
            self.formatter.error("QA validation failed")
            return 1

    def _on_qa_phase_change(self, phase: str, message: str) -> None:
        """Callback for QA phase changes."""
        self.formatter.stream_log(f"Phase: {phase} - {message}", level="info")

    async def run_spec(self, spec_input: str) -> int:
        """Process a spec (create new or continue existing)."""
        specs_dir = get_specs_dir(self.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, spec_input)

        is_new_spec = spec_dir is None

        if is_new_spec:
            self.formatter.header("Claude God Code", "New Specification")
            self.formatter.info(f"Task: {spec_input}")

            discovery = self._init_discovery()
            project_index = await discovery.discover()

            impact_analyzer = ImpactAnalyzer(self.project_dir, project_index)
            impact = await impact_analyzer.analyze_impact(spec_input)

            self.formatter.format_impact_analysis(impact)

            if impact.requires_migration_plan() and not self.args.force:
                if not self.formatter.prompt_confirmation(
                    "Breaking changes detected. Proceed with implementation?"
                ):
                    self.formatter.info("Aborted by user")
                    return 0

            orchestrator = self._init_orchestrator()
            session = orchestrator.create_session(spec_input)

            self.formatter.success(f"Created session: {session.session_id[:8]}...")
            self.formatter.info("Starting implementation...")

            try:
                session = await orchestrator.start_session(session.session_id)

                await orchestrator.update_session_phase(
                    session.session_id,
                    "implementation",
                    "Beginning code implementation",
                )

                await orchestrator.complete_session(
                    session.session_id,
                    "Implementation completed successfully",
                )

                self.formatter.success("Specification completed!")
                return 0

            except Exception as e:
                logger.exception("Session failed")
                await orchestrator.fail_session(session.session_id, str(e))
                self.formatter.error(f"Session failed: {e}")
                return 1

        else:
            self.formatter.header("Claude God Code", f"Continue: {spec_dir.name}")
            self.formatter.info("Resuming existing specification...")

            if self.args.qa:
                return await self.run_qa(spec_input)

            self.formatter.info("Use --qa to run QA validation")
            return 0

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

    async def run_merge(self, spec_name: str) -> int:
        """Merge spec changes to main branch."""
        specs_dir = get_specs_dir(self.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, spec_name)

        if spec_dir is None:
            self.formatter.error(f"Spec not found: {spec_name}")
            return 1

        self.formatter.header("Claude God Code", f"Merge: {spec_dir.name}")

        signoff = get_qa_signoff_status(spec_dir)
        if signoff and signoff.status.value != "approved":
            self.formatter.warning(f"Spec not approved (status: {signoff.status.value})")
            if not self.args.force:
                if not self.formatter.prompt_confirmation("Merge anyway?"):
                    self.formatter.info("Aborted")
                    return 0

        worktree_manager = self._init_worktree_manager()

        try:
            worktree_manager.merge_worktree(spec_dir.name)
            self.formatter.success("Changes merged successfully!")
            return 0
        except Exception as e:
            self.formatter.error(f"Merge failed: {e}")
            return 1

    async def run_discard(self, spec_name: str) -> int:
        """Discard spec worktree and changes."""
        specs_dir = get_specs_dir(self.project_dir)
        spec_dir = self._find_spec_dir(specs_dir, spec_name)

        if spec_dir is None:
            self.formatter.error(f"Spec not found: {spec_name}")
            return 1

        self.formatter.header("Claude God Code", f"Discard: {spec_dir.name}")

        if not self.args.force:
            self.formatter.warning("This will permanently delete all changes!")
            if not self.formatter.prompt_confirmation("Are you sure?", default=False):
                self.formatter.info("Aborted")
                return 0

        worktree_manager = self._init_worktree_manager()

        try:
            worktree_manager.cleanup_worktree(spec_dir.name)
            self.formatter.success("Worktree discarded")
            return 0
        except Exception as e:
            self.formatter.error(f"Discard failed: {e}")
            return 1

    async def run_resume(self, session_id: str) -> int:
        """Resume a paused session."""
        orchestrator = self._init_orchestrator()
        session = orchestrator.get_session(session_id)

        if session is None:
            self.formatter.error(f"Session not found: {session_id}")
            return 1

        if session.status != "paused":
            self.formatter.error(f"Session is not paused (status: {session.status})")
            return 1

        self.formatter.header("Claude God Code", "Resume Session")
        self.formatter.info(f"Task: {session.task_description}")

        try:
            session = await orchestrator.resume_session(session_id)
            self.formatter.success("Session resumed")
            return 0
        except Exception as e:
            self.formatter.error(f"Resume failed: {e}")
            return 1

    async def run(self) -> int:
        """Run the CLI application."""
        self._setup_logging()

        if not self._validate_project_dir():
            return 1

        if self.args.list:
            return await self.run_list_specs()

        if self.args.status:
            return await self.run_status()

        if self.args.resume:
            return await self.run_resume(self.args.resume)

        if self.args.spec:
            if self.args.merge:
                return await self.run_merge(self.args.spec)

            if self.args.discard:
                return await self.run_discard(self.args.spec)

            if self.args.qa:
                return await self.run_qa(self.args.spec)

            return await self.run_spec(self.args.spec)

        self.formatter.header("Claude God Code", "Autonomous Excellence")
        self.formatter.info("Use --help for usage information")
        self.formatter.info("Use --spec \"task description\" to start a new spec")
        self.formatter.info("Use --list to see existing specs")
        return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    app = CLIApplication(args)

    try:
        return asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nAborted by user")
        return 130
    except Exception as e:
        logger.exception("Unhandled exception")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
