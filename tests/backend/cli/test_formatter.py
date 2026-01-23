"""
Tests for cli.formatter module.

Part of Claude God Code - Autonomous Excellence
"""

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from cli.formatter import (
    Color,
    Style,
    FormatterConfig,
    TerminalFormatter,
    create_formatter,
)
from spec.models import ImpactAnalysis, ImpactSeverity, BreakingChange, ComplexityAssessment, Complexity
from qa.criteria import QAStatus, QAIssue, QASignoff, IssueSeverity
from qa.fixer import FixResult, Fix, FixStrategy
from qa.loop import QAPhase, QALoopState


class TestColor:
    """Tests for Color enum."""

    def test_color_values(self) -> None:
        """Should have expected color values."""
        assert Color.RED.value == "\033[31m"
        assert Color.GREEN.value == "\033[32m"
        assert Color.RESET.value == "\033[0m"

    def test_all_colors_are_strings(self) -> None:
        """All color values should be strings."""
        for color in Color:
            assert isinstance(color.value, str)
            assert color.value.startswith("\033[")


class TestStyle:
    """Tests for Style class."""

    def test_style_contains_color_codes(self) -> None:
        """Style strings should contain ANSI codes."""
        assert "\033[" in Style.HEADER
        assert "\033[" in Style.SUCCESS
        assert "\033[" in Style.ERROR


class TestFormatterConfig:
    """Tests for FormatterConfig dataclass."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = FormatterConfig()
        assert config.use_colors is True
        assert config.use_unicode is True
        assert config.terminal_width == 80
        assert config.verbose is False

    def test_auto_detect(self) -> None:
        """Should auto-detect terminal capabilities."""
        config = FormatterConfig.auto_detect()
        assert isinstance(config.terminal_width, int)
        assert config.terminal_width > 0


class TestTerminalFormatter:
    """Tests for TerminalFormatter class."""

    def test_init_default(self) -> None:
        """Should initialize with default config."""
        formatter = TerminalFormatter()
        assert formatter.config is not None

    def test_init_custom_config(self) -> None:
        """Should accept custom config."""
        config = FormatterConfig(use_colors=False, verbose=True)
        formatter = TerminalFormatter(config)
        assert formatter.config.use_colors is False
        assert formatter.config.verbose is True

    def test_color_with_colors_enabled(self) -> None:
        """Should apply colors when enabled."""
        config = FormatterConfig(use_colors=True)
        formatter = TerminalFormatter(config)
        result = formatter._color("test", Style.SUCCESS)
        assert "\033[" in result
        assert "test" in result

    def test_color_with_colors_disabled(self) -> None:
        """Should not apply colors when disabled."""
        config = FormatterConfig(use_colors=False)
        formatter = TerminalFormatter(config)
        result = formatter._color("test", Style.SUCCESS)
        assert result == "test"

    def test_icon_unicode_enabled(self) -> None:
        """Should return unicode icons when enabled."""
        config = FormatterConfig(use_unicode=True)
        formatter = TerminalFormatter(config)
        assert formatter._icon("check") == "✓"

    def test_icon_unicode_disabled(self) -> None:
        """Should return ASCII fallback when unicode disabled."""
        config = FormatterConfig(use_unicode=False)
        formatter = TerminalFormatter(config)
        assert formatter._icon("check") == "[OK]"

    def test_divider(self) -> None:
        """Should create divider of correct width."""
        config = FormatterConfig(terminal_width=40)
        formatter = TerminalFormatter(config)
        divider = formatter._divider("─")
        assert len(divider) == 40


class TestTerminalFormatterOutput:
    """Tests for TerminalFormatter output methods."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer for testing output."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_header_output(self, formatter_with_buffer) -> None:
        """Should output header."""
        formatter, buffer = formatter_with_buffer
        formatter.header("Test Title", "Subtitle")
        output = buffer.getvalue()
        assert "Test Title" in output
        assert "Subtitle" in output

    def test_section_output(self, formatter_with_buffer) -> None:
        """Should output section header."""
        formatter, buffer = formatter_with_buffer
        formatter.section("Test Section")
        output = buffer.getvalue()
        assert "Test Section" in output

    def test_success_output(self, formatter_with_buffer) -> None:
        """Should output success message."""
        formatter, buffer = formatter_with_buffer
        formatter.success("Operation successful")
        output = buffer.getvalue()
        assert "Operation successful" in output
        assert "[OK]" in output

    def test_error_output(self, formatter_with_buffer) -> None:
        """Should output error message."""
        formatter, buffer = formatter_with_buffer
        formatter.error("Something failed")
        output = buffer.getvalue()
        assert "Something failed" in output
        assert "[X]" in output

    def test_warning_output(self, formatter_with_buffer) -> None:
        """Should output warning message."""
        formatter, buffer = formatter_with_buffer
        formatter.warning("Be careful")
        output = buffer.getvalue()
        assert "Be careful" in output
        assert "[!]" in output

    def test_bullet_output(self, formatter_with_buffer) -> None:
        """Should output bullet point."""
        formatter, buffer = formatter_with_buffer
        formatter.bullet("Item one")
        output = buffer.getvalue()
        assert "Item one" in output
        assert "*" in output

    def test_key_value_output(self, formatter_with_buffer) -> None:
        """Should output key-value pair."""
        formatter, buffer = formatter_with_buffer
        formatter.key_value("Name", "Value")
        output = buffer.getvalue()
        assert "Name:" in output
        assert "Value" in output


class TestImpactAnalysisFormatting:
    """Tests for Impact Analysis formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_format_impact_analysis_basic(self, formatter_with_buffer) -> None:
        """Should format basic impact analysis."""
        formatter, buffer = formatter_with_buffer
        impact = ImpactAnalysis(
            severity=ImpactSeverity.MEDIUM,
            confidence=0.85,
            affected_files=["src/api.py", "src/models.py"],
            rollback_complexity="low",
        )
        formatter.format_impact_analysis(impact)
        output = buffer.getvalue()
        assert "Impact Analysis" in output
        assert "MEDIUM" in output
        assert "85%" in output

    def test_format_impact_analysis_with_breaking_changes(self, formatter_with_buffer) -> None:
        """Should format impact analysis with breaking changes."""
        formatter, buffer = formatter_with_buffer
        impact = ImpactAnalysis(
            severity=ImpactSeverity.HIGH,
            confidence=0.9,
            breaking_changes=[
                BreakingChange(
                    change_type="api_change",
                    location="api.py:50",
                    description="Function signature changed",
                ),
            ],
        )
        formatter.format_impact_analysis(impact)
        output = buffer.getvalue()
        assert "Breaking Changes" in output
        assert "api_change" in output
        assert "Function signature changed" in output


class TestQAStatusFormatting:
    """Tests for QA status formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_format_qa_status_approved(self, formatter_with_buffer) -> None:
        """Should format approved QA status."""
        formatter, buffer = formatter_with_buffer
        signoff = QASignoff(status=QAStatus.APPROVED, qa_session=1)
        formatter.format_qa_status(signoff)
        output = buffer.getvalue()
        assert "QA Loop Status" in output
        assert "APPROVED" in output

    def test_format_qa_status_with_issues(self, formatter_with_buffer) -> None:
        """Should format QA status with issues."""
        formatter, buffer = formatter_with_buffer
        signoff = QASignoff(
            status=QAStatus.REJECTED,
            qa_session=2,
            issues_found=[
                QAIssue(
                    title="Security Issue",
                    severity=IssueSeverity.HIGH,
                    description="Hardcoded secret found",
                    location="config.py:10",
                ),
            ],
        )
        formatter.format_qa_status(signoff)
        output = buffer.getvalue()
        assert "REJECTED" in output
        assert "Security Issue" in output


class TestFixResultFormatting:
    """Tests for fix result formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_format_fix_result_success(self, formatter_with_buffer) -> None:
        """Should format successful fix result."""
        formatter, buffer = formatter_with_buffer
        issue = QAIssue(title="Debug", severity=IssueSeverity.LOW, description="")
        result = FixResult(
            success=True,
            fixes_applied=[
                Fix(
                    issue=issue,
                    strategy=FixStrategy.DELETE,
                    description="Removed debug statement",
                    applied=True,
                ),
            ],
            message="1 fix applied",
        )
        formatter.format_fix_result(result)
        output = buffer.getvalue()
        assert "Self-Healing Results" in output
        assert "Fixes Applied" in output


class TestComplexityFormatting:
    """Tests for complexity assessment formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_format_complexity_simple(self, formatter_with_buffer) -> None:
        """Should format simple complexity."""
        formatter, buffer = formatter_with_buffer
        assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=0.9,
            estimated_files=2,
            estimated_services=1,
        )
        formatter.format_complexity(assessment)
        output = buffer.getvalue()
        assert "Complexity Assessment" in output
        assert "SIMPLE" in output
        assert "90%" in output


class TestSessionStatusFormatting:
    """Tests for session status formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_format_session_status(self, formatter_with_buffer) -> None:
        """Should format session status."""
        formatter, buffer = formatter_with_buffer
        formatter.format_session_status(
            session_id="abc12345-test-session-id",
            status="running",
            phase="implementation",
            task="Add authentication",
            duration_seconds=125.5,
        )
        output = buffer.getvalue()
        assert "Session Status" in output
        assert "RUNNING" in output
        assert "implementation" in output
        assert "125.5s" in output


class TestProgressBar:
    """Tests for progress bar formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_progress_bar_zero(self, formatter_with_buffer) -> None:
        """Should show 0% progress."""
        formatter, buffer = formatter_with_buffer
        formatter.progress_bar(0, 10)
        output = buffer.getvalue()
        assert "0%" in output

    def test_progress_bar_complete(self, formatter_with_buffer) -> None:
        """Should show 100% progress."""
        formatter, buffer = formatter_with_buffer
        formatter.progress_bar(10, 10)
        output = buffer.getvalue()
        assert "100%" in output


class TestStreamLog:
    """Tests for stream log formatting."""

    @pytest.fixture
    def formatter_with_buffer(self):
        """Create formatter with string buffer."""
        buffer = io.StringIO()
        config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
        formatter = TerminalFormatter(config)
        return formatter, buffer

    def test_stream_log_info(self, formatter_with_buffer) -> None:
        """Should stream info log."""
        formatter, buffer = formatter_with_buffer
        formatter.stream_log("Processing file", level="info")
        output = buffer.getvalue()
        assert "[INFO]" in output
        assert "Processing file" in output

    def test_stream_log_error(self, formatter_with_buffer) -> None:
        """Should stream error log."""
        formatter, buffer = formatter_with_buffer
        formatter.stream_log("Operation failed", level="error")
        output = buffer.getvalue()
        assert "[ERROR]" in output
        assert "Operation failed" in output


class TestCreateFormatter:
    """Tests for create_formatter function."""

    def test_create_formatter_default(self) -> None:
        """Should create formatter with auto-detected config."""
        formatter = create_formatter()
        assert isinstance(formatter, TerminalFormatter)

    def test_create_formatter_no_colors(self) -> None:
        """Should create formatter without colors."""
        formatter = create_formatter(use_colors=False)
        assert formatter.config.use_colors is False

    def test_create_formatter_verbose(self) -> None:
        """Should create formatter with verbose mode."""
        formatter = create_formatter(verbose=True)
        assert formatter.config.verbose is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
