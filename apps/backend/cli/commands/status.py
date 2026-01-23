"""
Status Command Handler.

Part of Claude God Code - Autonomous Excellence

Handles displaying session and spec status information.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from spec.models import get_specs_dir
from agents.session import SessionOrchestrator, SessionData
from qa.criteria import get_qa_signoff_status

from ..formatter import TerminalFormatter

logger = logging.getLogger(__name__)


@dataclass
class StatusOptions:
    """Options for the status command."""

    project_dir: Path
    session_id: Optional[str] = None
    spec_name: Optional[str] = None
    show_history: bool = False
    limit: int = 10


@dataclass
class StatusResult:
    """Result of the status command."""

    success: bool
    active_sessions: list[SessionData]
    recent_sessions: list[SessionData]
    specs: list[dict[str, Any]]
    message: str = ""


class StatusCommand:
    """Command handler for displaying status information."""

    def __init__(
        self,
        formatter: TerminalFormatter,
        orchestrator: Optional[SessionOrchestrator] = None,
    ) -> None:
        """Initialize status command."""
        self.formatter = formatter
        self._orchestrator = orchestrator

    def _get_orchestrator(self, project_dir: Path) -> SessionOrchestrator:
        """Get or create session orchestrator."""
        if self._orchestrator is None:
            self._orchestrator = SessionOrchestrator(project_dir)
        return self._orchestrator

    async def execute(self, options: StatusOptions) -> StatusResult:
        """Execute the status command."""
        orchestrator = self._get_orchestrator(options.project_dir)

        active_sessions = orchestrator.get_active_sessions()
        recent_sessions = orchestrator.store.get_recent_sessions(limit=options.limit)
        specs = self._gather_spec_status(options.project_dir)

        self.formatter.header("Claude God Code", "System Status")

        if options.session_id:
            session = orchestrator.get_session(options.session_id)
            if session:
                self._display_session_detail(session)
            else:
                self.formatter.error(f"Session not found: {options.session_id}")
                return StatusResult(
                    success=False,
                    active_sessions=active_sessions,
                    recent_sessions=recent_sessions,
                    specs=specs,
                    message="Session not found",
                )

        elif options.spec_name:
            spec_info = self._find_spec(specs, options.spec_name)
            if spec_info:
                self._display_spec_detail(spec_info)
            else:
                self.formatter.error(f"Spec not found: {options.spec_name}")
                return StatusResult(
                    success=False,
                    active_sessions=active_sessions,
                    recent_sessions=recent_sessions,
                    specs=specs,
                    message="Spec not found",
                )

        else:
            self._display_summary(active_sessions, recent_sessions, specs)

        return StatusResult(
            success=True,
            active_sessions=active_sessions,
            recent_sessions=recent_sessions,
            specs=specs,
            message="Status retrieved successfully",
        )

    def _gather_spec_status(self, project_dir: Path) -> list[dict[str, Any]]:
        """Gather status for all specs."""
        specs_dir = get_specs_dir(project_dir)
        if not specs_dir.exists():
            return []

        specs = []
        for spec_path in sorted(specs_dir.glob("*")):
            if spec_path.is_dir():
                signoff = get_qa_signoff_status(spec_path)
                specs.append({
                    "name": spec_path.name,
                    "path": spec_path,
                    "status": signoff.status.value if signoff else "unknown",
                    "qa_session": signoff.qa_session if signoff else 0,
                    "issues_count": len(signoff.issues_found) if signoff else 0,
                })

        return specs

    def _find_spec(self, specs: list[dict[str, Any]], name: str) -> Optional[dict[str, Any]]:
        """Find a spec by name."""
        for spec in specs:
            if spec["name"] == name or name in spec["name"]:
                return spec
        return None

    def _display_summary(
        self,
        active_sessions: list[SessionData],
        recent_sessions: list[SessionData],
        specs: list[dict[str, Any]],
    ) -> None:
        """Display summary status."""
        self.formatter.section(f"Active Sessions ({len(active_sessions)})")
        if active_sessions:
            for session in active_sessions:
                self._display_session_brief(session)
        else:
            self.formatter.info("No active sessions")

        self.formatter.section(f"Recent Sessions")
        if recent_sessions:
            for session in recent_sessions[:5]:
                self._display_session_brief(session)
        else:
            self.formatter.info("No recent sessions")

        self.formatter.section(f"Specifications ({len(specs)})")
        if specs:
            for spec in specs:
                self._display_spec_brief(spec)
        else:
            self.formatter.info("No specifications found")

    def _display_session_brief(self, session: SessionData) -> None:
        """Display brief session info."""
        status_icons = {
            "pending": "○",
            "running": "◐",
            "completed": "✓",
            "failed": "✗",
            "paused": "⏸",
        }
        icon = status_icons.get(session.status, "?")
        duration = f"{session.get_duration_seconds():.1f}s"

        self.formatter.bullet(
            f"{icon} {session.session_id[:8]}... [{session.status}] "
            f"{session.task_description[:40]}... ({duration})"
        )

    def _display_session_detail(self, session: SessionData) -> None:
        """Display detailed session info."""
        self.formatter.format_session_status(
            session_id=session.session_id,
            status=session.status,
            phase=session.phase,
            task=session.task_description,
            duration_seconds=session.get_duration_seconds(),
            metrics=session.metrics,
        )

        if session.errors:
            self.formatter.section("Errors")
            for error in session.errors:
                self.formatter.error(error.get("message", "Unknown error"))

        if session.artifacts:
            self.formatter.section("Artifacts")
            for key in session.artifacts:
                self.formatter.bullet(key)

    def _display_spec_brief(self, spec: dict[str, Any]) -> None:
        """Display brief spec info."""
        status_icons = {
            "unknown": "?",
            "pending": "○",
            "in_progress": "◐",
            "approved": "✓",
            "rejected": "✗",
            "fixes_applied": "⚡",
            "escalated": "⚠",
        }
        icon = status_icons.get(spec["status"], "?")
        issues = f" ({spec['issues_count']} issues)" if spec["issues_count"] else ""

        self.formatter.bullet(f"{icon} {spec['name']} [{spec['status']}]{issues}")

    def _display_spec_detail(self, spec: dict[str, Any]) -> None:
        """Display detailed spec info."""
        self.formatter.section(f"Specification: {spec['name']}")
        self.formatter.key_value("Status", spec["status"])
        self.formatter.key_value("QA Session", spec["qa_session"])
        self.formatter.key_value("Issues", spec["issues_count"])
        self.formatter.key_value("Path", str(spec["path"]))

        signoff = get_qa_signoff_status(spec["path"])
        if signoff and signoff.issues_found:
            self.formatter.section("Issues")
            for issue in signoff.issues_found:
                self.formatter.bullet(f"[{issue.severity.value}] {issue.title}")
