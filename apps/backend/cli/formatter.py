"""
Rich Terminal Formatter for God Mode Output.

Part of Claude God Code - Autonomous Excellence

This module provides rich terminal formatting for displaying:
- Impact Analysis reports with severity coloring
- QA Loop status with progress indicators
- Self-Healing results with fix summaries
- Session status and metrics
"""

import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TextIO

from spec.models import ImpactAnalysis, ImpactSeverity, BreakingChange, ComplexityAssessment, Complexity
from qa.criteria import QAStatus, QAIssue, QASignoff, IssueSeverity
from qa.fixer import FixResult, Fix, FixStrategy
from qa.loop import QAPhase, QALoopState


class Color(Enum):
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"

    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"


class Style:
    """Pre-defined styles for God Mode output."""

    HEADER = f"{Color.BOLD.value}{Color.BRIGHT_CYAN.value}"
    SUCCESS = f"{Color.BOLD.value}{Color.BRIGHT_GREEN.value}"
    WARNING = f"{Color.BOLD.value}{Color.BRIGHT_YELLOW.value}"
    ERROR = f"{Color.BOLD.value}{Color.BRIGHT_RED.value}"
    INFO = f"{Color.CYAN.value}"
    DIM = f"{Color.DIM.value}"
    CRITICAL = f"{Color.BOLD.value}{Color.BG_RED.value}{Color.WHITE.value}"


@dataclass
class FormatterConfig:
    """Configuration for terminal formatter."""

    use_colors: bool = True
    use_unicode: bool = True
    terminal_width: int = 80
    verbose: bool = False
    stream: TextIO = sys.stdout

    @classmethod
    def auto_detect(cls) -> "FormatterConfig":
        """Auto-detect terminal capabilities."""
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        width = shutil.get_terminal_size().columns

        return cls(
            use_colors=is_tty,
            use_unicode=is_tty,
            terminal_width=width,
            stream=sys.stdout,
        )


class TerminalFormatter:
    """Rich terminal formatter for God Mode output."""

    def __init__(self, config: Optional[FormatterConfig] = None) -> None:
        """Initialize formatter with configuration."""
        self.config = config or FormatterConfig.auto_detect()

        self.ICONS = {
            "check": "✓" if self.config.use_unicode else "[OK]",
            "cross": "✗" if self.config.use_unicode else "[X]",
            "warning": "⚠" if self.config.use_unicode else "[!]",
            "info": "ℹ" if self.config.use_unicode else "[i]",
            "arrow": "→" if self.config.use_unicode else "->",
            "bullet": "•" if self.config.use_unicode else "*",
            "gear": "⚙" if self.config.use_unicode else "[*]",
            "lightning": "⚡" if self.config.use_unicode else "[!]",
            "shield": "🛡" if self.config.use_unicode else "[S]",
            "fire": "🔥" if self.config.use_unicode else "[!!]",
            "package": "📦" if self.config.use_unicode else "[P]",
            "magnify": "🔍" if self.config.use_unicode else "[?]",
            "hammer": "🔨" if self.config.use_unicode else "[H]",
            "target": "🎯" if self.config.use_unicode else "[T]",
        }

    def _color(self, text: str, *styles: str) -> str:
        """Apply color/style to text if colors enabled."""
        if not self.config.use_colors:
            return text
        style_codes = "".join(styles)
        return f"{style_codes}{text}{Color.RESET.value}"

    def _icon(self, name: str) -> str:
        """Get icon by name."""
        return self.ICONS.get(name, "")

    def _print(self, *args: Any, **kwargs: Any) -> None:
        """Print to configured stream."""
        print(*args, file=self.config.stream, **kwargs)

    def _divider(self, char: str = "─", width: Optional[int] = None) -> str:
        """Create a divider line."""
        w = width or self.config.terminal_width
        return char * w

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Print a styled header."""
        self._print()
        self._print(self._color(self._divider("═"), Style.HEADER))
        self._print(self._color(f"  {self._icon('lightning')} {title}", Style.HEADER))
        if subtitle:
            self._print(self._color(f"  {subtitle}", Style.DIM))
        self._print(self._color(self._divider("═"), Style.HEADER))
        self._print()

    def section(self, title: str) -> None:
        """Print a section header."""
        self._print()
        self._print(self._color(f"─── {title} ───", Style.INFO))

    def success(self, message: str) -> None:
        """Print success message."""
        self._print(f"  {self._color(self._icon('check'), Style.SUCCESS)} {message}")

    def warning(self, message: str) -> None:
        """Print warning message."""
        self._print(f"  {self._color(self._icon('warning'), Style.WARNING)} {message}")

    def error(self, message: str) -> None:
        """Print error message."""
        self._print(f"  {self._color(self._icon('cross'), Style.ERROR)} {message}")

    def info(self, message: str) -> None:
        """Print info message."""
        self._print(f"  {self._color(self._icon('info'), Style.INFO)} {message}")

    def bullet(self, message: str, indent: int = 2) -> None:
        """Print bullet point."""
        spaces = " " * indent
        self._print(f"{spaces}{self._icon('bullet')} {message}")

    def key_value(self, key: str, value: Any, indent: int = 4) -> None:
        """Print key-value pair."""
        spaces = " " * indent
        self._print(f"{spaces}{self._color(key + ':', Style.DIM)} {value}")

    def format_impact_analysis(self, impact: ImpactAnalysis) -> None:
        """Format and display Impact Analysis report (God Mode feature)."""
        self.header("GOD MODE: Impact Analysis", "Predicting changes before implementation")

        severity_style = self._get_severity_style(impact.severity)
        severity_icon = self._get_severity_icon(impact.severity)

        self._print(f"  {self._color('Severity:', Style.DIM)} {self._color(f'{severity_icon} {impact.severity.value.upper()}', severity_style)}")
        self._print(f"  {self._color('Confidence:', Style.DIM)} {impact.confidence:.0%}")
        self._print(f"  {self._color('Rollback Complexity:', Style.DIM)} {impact.rollback_complexity}")

        if impact.affected_files:
            self.section("Affected Files")
            for f in impact.affected_files[:10]:
                self.bullet(f)
            if len(impact.affected_files) > 10:
                self._print(f"    {self._color(f'... and {len(impact.affected_files) - 10} more', Style.DIM)}")

        if impact.affected_services:
            self.section("Affected Services")
            for svc in impact.affected_services:
                self.bullet(f"{self._icon('package')} {svc}")

        if impact.breaking_changes:
            self.section(f"{self._icon('fire')} Breaking Changes ({len(impact.breaking_changes)})")
            for bc in impact.breaking_changes:
                self._format_breaking_change(bc)

        if impact.test_coverage_gaps:
            self.section("Test Coverage Gaps")
            for gap in impact.test_coverage_gaps:
                self.warning(gap)

        if impact.recommended_mitigations:
            self.section("Recommended Mitigations")
            for i, mitigation in enumerate(impact.recommended_mitigations, 1):
                self._print(f"    {i}. {mitigation}")

        if impact.analysis_reasoning:
            self.section("Analysis Reasoning")
            self._print(f"    {impact.analysis_reasoning}")

        self._print()

    def _format_breaking_change(self, bc: BreakingChange) -> None:
        """Format a single breaking change."""
        self._print(f"    {self._color(f'[{bc.change_type}]', Style.ERROR)} {bc.description}")
        self.key_value("Location", bc.location, indent=6)
        if bc.affected_consumers:
            self.key_value("Affects", ", ".join(bc.affected_consumers), indent=6)
        if bc.migration_required:
            self._print(f"      {self._color('Migration Required', Style.WARNING)}")
        if bc.suggested_fix:
            self.key_value("Fix", bc.suggested_fix, indent=6)

    def _get_severity_style(self, severity: ImpactSeverity) -> str:
        """Get style for severity level."""
        styles = {
            ImpactSeverity.NONE: Style.DIM,
            ImpactSeverity.LOW: Style.INFO,
            ImpactSeverity.MEDIUM: Style.WARNING,
            ImpactSeverity.HIGH: Style.ERROR,
            ImpactSeverity.CRITICAL: Style.CRITICAL,
        }
        return styles.get(severity, Style.INFO)

    def _get_severity_icon(self, severity: ImpactSeverity) -> str:
        """Get icon for severity level."""
        icons = {
            ImpactSeverity.NONE: self._icon("check"),
            ImpactSeverity.LOW: self._icon("info"),
            ImpactSeverity.MEDIUM: self._icon("warning"),
            ImpactSeverity.HIGH: self._icon("fire"),
            ImpactSeverity.CRITICAL: self._icon("fire"),
        }
        return icons.get(severity, self._icon("info"))

    def format_qa_status(self, signoff: QASignoff, state: Optional[QALoopState] = None) -> None:
        """Format and display QA Loop status."""
        self.header("QA Loop Status", f"Session: {signoff.qa_session}")

        status_style, status_icon = self._get_qa_status_style(signoff.status)
        self._print(f"  {self._color('Status:', Style.DIM)} {self._color(f'{status_icon} {signoff.status.value.upper()}', status_style)}")

        if state:
            self._print(f"  {self._color('Iteration:', Style.DIM)} {state.current_iteration}")
            self._print(f"  {self._color('Phase:', Style.DIM)} {state.current_phase.value}")

        if signoff.issues_found:
            self.section(f"Issues Found ({len(signoff.issues_found)})")
            for issue in signoff.issues_found:
                self._format_qa_issue(issue)

        if state and state.history:
            self.section("Iteration History")
            for record in state.history[-5:]:
                phase_icon = self._get_phase_icon(record.phase)
                self._print(f"    {phase_icon} Iteration {record.iteration}: {record.phase.value} - {record.status}")

        self._print()

    def _get_qa_status_style(self, status: QAStatus) -> tuple[str, str]:
        """Get style and icon for QA status."""
        mapping = {
            QAStatus.PENDING: (Style.DIM, self._icon("gear")),
            QAStatus.APPROVED: (Style.SUCCESS, self._icon("check")),
            QAStatus.REJECTED: (Style.ERROR, self._icon("cross")),
            QAStatus.FIXES_APPLIED: (Style.WARNING, self._icon("hammer")),
            QAStatus.ERROR: (Style.ERROR, self._icon("cross")),
        }
        return mapping.get(status, (Style.INFO, self._icon("info")))

    def _format_qa_issue(self, issue: QAIssue) -> None:
        """Format a single QA issue."""
        sev_style = self._get_issue_severity_style(issue.severity)
        sev_icon = self._get_issue_severity_icon(issue.severity)
        self._print(f"    {self._color(f'{sev_icon} [{issue.severity.value}]', sev_style)} {issue.title}")
        if issue.location:
            self.key_value("Location", issue.location, indent=6)
        if issue.description and self.config.verbose:
            self.key_value("Details", issue.description, indent=6)

    def _get_issue_severity_style(self, severity: IssueSeverity) -> str:
        """Get style for issue severity."""
        styles = {
            IssueSeverity.LOW: Style.DIM,
            IssueSeverity.MEDIUM: Style.INFO,
            IssueSeverity.HIGH: Style.WARNING,
            IssueSeverity.CRITICAL: Style.ERROR,
        }
        return styles.get(severity, Style.INFO)

    def _get_issue_severity_icon(self, severity: IssueSeverity) -> str:
        """Get icon for issue severity."""
        icons = {
            IssueSeverity.LOW: self._icon("info"),
            IssueSeverity.MEDIUM: self._icon("warning"),
            IssueSeverity.HIGH: self._icon("fire"),
            IssueSeverity.CRITICAL: self._icon("fire"),
        }
        return icons.get(severity, self._icon("info"))

    def _get_phase_icon(self, phase: QAPhase) -> str:
        """Get icon for QA phase."""
        icons = {
            QAPhase.REVIEW: self._icon("magnify"),
            QAPhase.TEST: self._icon("target"),
            QAPhase.FIX: self._icon("hammer"),
            QAPhase.COMPLETE: self._icon("check"),
            QAPhase.FAILED: self._icon("cross"),
        }
        return icons.get(phase, self._icon("gear"))

    def format_fix_result(self, result: FixResult) -> None:
        """Format and display self-healing fix results."""
        self.header("Self-Healing Results", "Automatic code corrections")

        if result.success:
            self.success(result.message)
        else:
            self.error(result.message)

        if result.fixes_applied:
            self.section(f"{self._icon('check')} Fixes Applied ({len(result.fixes_applied)})")
            for fix in result.fixes_applied:
                self._format_fix(fix, applied=True)

        if result.fixes_failed:
            self.section(f"{self._icon('cross')} Fixes Failed ({len(result.fixes_failed)})")
            for fix in result.fixes_failed:
                self._format_fix(fix, applied=False)

        if result.fixes_skipped:
            self.section(f"{self._icon('warning')} Fixes Skipped ({len(result.fixes_skipped)})")
            for fix in result.fixes_skipped:
                self._format_fix(fix, skipped=True)

        if result.ready_for_revalidation:
            self._print()
            self.info("Ready for re-validation")

        self._print()

    def _format_fix(self, fix: Fix, applied: bool = False, skipped: bool = False) -> None:
        """Format a single fix."""
        status_icon = self._icon("check") if applied else (self._icon("warning") if skipped else self._icon("cross"))
        self._print(f"    {status_icon} {fix.issue.title}")
        self.key_value("Strategy", fix.strategy.value, indent=6)
        self.key_value("Confidence", f"{fix.confidence:.0%}", indent=6)
        if fix.file_path:
            self.key_value("File", f"{fix.file_path}:{fix.line_number or '?'}", indent=6)
        if fix.error:
            self._print(f"      {self._color(f'Error: {fix.error}', Style.ERROR)}")

    def format_complexity(self, assessment: ComplexityAssessment) -> None:
        """Format and display complexity assessment."""
        self.section(f"{self._icon('target')} Complexity Assessment")

        complexity_style = self._get_complexity_style(assessment.complexity)
        self._print(f"  {self._color('Complexity:', Style.DIM)} {self._color(assessment.complexity.value.upper(), complexity_style)}")
        self._print(f"  {self._color('Confidence:', Style.DIM)} {assessment.confidence:.0%}")
        self._print(f"  {self._color('Est. Files:', Style.DIM)} {assessment.estimated_files}")
        self._print(f"  {self._color('Est. Services:', Style.DIM)} {assessment.estimated_services}")

        if assessment.external_integrations:
            self.key_value("External", ", ".join(assessment.external_integrations))

        if assessment.infrastructure_changes:
            self.warning("Infrastructure changes detected")

        phases = assessment.phases_to_run()
        if phases:
            self._print(f"  {self._color('Phases:', Style.DIM)} {' → '.join(phases)}")

    def _get_complexity_style(self, complexity: Complexity) -> str:
        """Get style for complexity level."""
        styles = {
            Complexity.SIMPLE: Style.SUCCESS,
            Complexity.STANDARD: Style.INFO,
            Complexity.COMPLEX: Style.WARNING,
            Complexity.CRITICAL: Style.ERROR,
        }
        return styles.get(complexity, Style.INFO)

    def format_session_status(
        self,
        session_id: str,
        status: str,
        phase: str,
        task: str,
        duration_seconds: float = 0.0,
        metrics: Optional[dict[str, Any]] = None,
    ) -> None:
        """Format and display session status."""
        self.header("Session Status", f"ID: {session_id[:8]}...")

        status_style = self._get_session_status_style(status)
        self._print(f"  {self._color('Status:', Style.DIM)} {self._color(status.upper(), status_style)}")
        self._print(f"  {self._color('Phase:', Style.DIM)} {phase}")
        self._print(f"  {self._color('Task:', Style.DIM)} {task[:60]}{'...' if len(task) > 60 else ''}")
        self._print(f"  {self._color('Duration:', Style.DIM)} {duration_seconds:.1f}s")

        if metrics:
            self.section("Metrics")
            for key, value in metrics.items():
                self.key_value(key, value)

        self._print()

    def _get_session_status_style(self, status: str) -> str:
        """Get style for session status."""
        styles = {
            "pending": Style.DIM,
            "running": Style.INFO,
            "completed": Style.SUCCESS,
            "failed": Style.ERROR,
            "paused": Style.WARNING,
        }
        return styles.get(status.lower(), Style.INFO)

    def prompt_confirmation(self, message: str, default: bool = False) -> bool:
        """Prompt user for confirmation."""
        default_str = "[Y/n]" if default else "[y/N]"
        prompt = f"  {self._icon('warning')} {message} {default_str}: "

        try:
            response = input(prompt).strip().lower()
            if not response:
                return default
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            self._print()
            return False

    def progress_bar(
        self,
        current: int,
        total: int,
        prefix: str = "",
        width: int = 40,
    ) -> None:
        """Display a progress bar."""
        if total == 0:
            pct = 100
        else:
            pct = int(current / total * 100)

        filled = int(width * current / max(total, 1))
        bar = "█" * filled + "░" * (width - filled)

        self._print(f"\r  {prefix} [{bar}] {pct}% ({current}/{total})", end="")
        if current >= total:
            self._print()

    def stream_log(self, message: str, level: str = "info") -> None:
        """Stream a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_style = {
            "debug": Style.DIM,
            "info": Style.INFO,
            "warning": Style.WARNING,
            "error": Style.ERROR,
        }.get(level.lower(), Style.INFO)

        prefix = self._color(f"[{timestamp}]", Style.DIM)
        level_tag = self._color(f"[{level.upper()}]", level_style)
        self._print(f"{prefix} {level_tag} {message}")


def create_formatter(
    use_colors: Optional[bool] = None,
    verbose: bool = False,
) -> TerminalFormatter:
    """Create a terminal formatter with sensible defaults."""
    config = FormatterConfig.auto_detect()

    if use_colors is not None:
        config.use_colors = use_colors

    config.verbose = verbose

    return TerminalFormatter(config)
