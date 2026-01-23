"""
Tests for cli.commands module.

Part of Claude God Code - Autonomous Excellence
"""

import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from cli.commands.start import StartCommand, StartOptions, StartResult
from cli.commands.status import StatusCommand, StatusOptions, StatusResult
from cli.commands.config import ConfigCommand, ConfigOptions, ConfigResult, ConfigManager, DEFAULT_CONFIG
from cli.commands.qa import QACommand, QAOptions, QAResult
from cli.formatter import TerminalFormatter, FormatterConfig


@pytest.fixture
def formatter():
    """Create formatter with string buffer for testing."""
    buffer = io.StringIO()
    config = FormatterConfig(use_colors=False, use_unicode=False, stream=buffer)
    return TerminalFormatter(config)


class TestStartCommand:
    """Tests for StartCommand class."""

    def test_init(self, formatter) -> None:
        """Should initialize command."""
        cmd = StartCommand(formatter)
        assert cmd.formatter is formatter

    @pytest.mark.asyncio
    async def test_execute_success(self, formatter, tmp_path: Path) -> None:
        """Should execute start command."""
        cmd = StartCommand(formatter)

        with patch.object(cmd, '_get_orchestrator') as mock_orch:
            mock_session = MagicMock()
            mock_session.session_id = "test-session-123"
            mock_orch.return_value.create_session.return_value = mock_session
            mock_orch.return_value.start_session = AsyncMock(return_value=mock_session)

            with patch('cli.commands.start.ProjectDiscovery') as mock_discovery:
                mock_discovery.return_value.discover = AsyncMock(return_value=MagicMock())

                with patch('cli.commands.start.ImpactAnalyzer') as mock_analyzer:
                    mock_impact = MagicMock()
                    mock_impact.requires_migration_plan.return_value = False
                    mock_analyzer.return_value.analyze_impact = AsyncMock(return_value=mock_impact)

                    options = StartOptions(
                        task_description="Add feature",
                        project_dir=tmp_path,
                        isolated=False,
                    )
                    result = await cmd.execute(options)

        assert isinstance(result, StartResult)


class TestStartOptions:
    """Tests for StartOptions dataclass."""

    def test_create_options(self, tmp_path: Path) -> None:
        """Should create options."""
        options = StartOptions(
            task_description="Add authentication",
            project_dir=tmp_path,
            isolated=True,
            force=True,
        )
        assert options.task_description == "Add authentication"
        assert options.isolated is True
        assert options.force is True


class TestStartResult:
    """Tests for StartResult dataclass."""

    def test_successful_result(self) -> None:
        """Should create successful result."""
        result = StartResult(
            success=True,
            session_id="session-123",
            message="Done",
        )
        assert result.success is True
        assert result.session_id == "session-123"

    def test_failed_result(self) -> None:
        """Should create failed result."""
        result = StartResult(
            success=False,
            error="Something went wrong",
            message="Failed",
        )
        assert result.success is False
        assert result.error == "Something went wrong"


class TestStatusCommand:
    """Tests for StatusCommand class."""

    def test_init(self, formatter) -> None:
        """Should initialize command."""
        cmd = StatusCommand(formatter)
        assert cmd.formatter is formatter

    @pytest.mark.asyncio
    async def test_execute(self, formatter, tmp_path: Path) -> None:
        """Should execute status command."""
        cmd = StatusCommand(formatter)

        with patch.object(cmd, '_get_orchestrator') as mock_orch:
            mock_orch.return_value.get_active_sessions.return_value = []
            mock_orch.return_value.store.get_recent_sessions.return_value = []

            options = StatusOptions(project_dir=tmp_path)
            result = await cmd.execute(options)

        assert isinstance(result, StatusResult)
        assert result.success is True

    def test_gather_spec_status_empty(self, formatter, tmp_path: Path) -> None:
        """Should return empty list when no specs."""
        cmd = StatusCommand(formatter)
        specs = cmd._gather_spec_status(tmp_path)
        assert specs == []

    def test_gather_spec_status_with_specs(self, formatter, tmp_path: Path) -> None:
        """Should gather spec status."""
        cmd = StatusCommand(formatter)

        specs_dir = tmp_path / ".claude-god-code" / "specs"
        (specs_dir / "001-test").mkdir(parents=True)

        specs = cmd._gather_spec_status(tmp_path)
        assert len(specs) == 1
        assert specs[0]["name"] == "001-test"


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize manager."""
        manager = ConfigManager(tmp_path)
        assert manager.config_dir == tmp_path

    def test_load_default(self, tmp_path: Path) -> None:
        """Should return defaults when no config file."""
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config == DEFAULT_CONFIG

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Should save and load config."""
        manager = ConfigManager(tmp_path)
        test_config = {"model": "test-model", "verbose": True}
        manager.save(test_config)

        manager2 = ConfigManager(tmp_path)
        loaded = manager2.load()
        assert loaded["model"] == "test-model"
        assert loaded["verbose"] is True

    def test_get(self, tmp_path: Path) -> None:
        """Should get config value."""
        manager = ConfigManager(tmp_path)
        value = manager.get("model")
        assert value == DEFAULT_CONFIG["model"]

    def test_get_with_default(self, tmp_path: Path) -> None:
        """Should return default for missing key."""
        manager = ConfigManager(tmp_path)
        value = manager.get("nonexistent", "default")
        assert value == "default"

    def test_set(self, tmp_path: Path) -> None:
        """Should set config value."""
        manager = ConfigManager(tmp_path)
        manager.set("verbose", True)
        assert manager.get("verbose") is True

    def test_reset(self, tmp_path: Path) -> None:
        """Should reset to defaults."""
        manager = ConfigManager(tmp_path)
        manager.set("verbose", True)
        manager.reset()
        config = manager.load()
        assert config == DEFAULT_CONFIG


class TestConfigCommand:
    """Tests for ConfigCommand class."""

    def test_init(self, formatter) -> None:
        """Should initialize command."""
        cmd = ConfigCommand(formatter)
        assert cmd.formatter is formatter

    @pytest.mark.asyncio
    async def test_execute_list(self, formatter, tmp_path: Path) -> None:
        """Should list config."""
        manager = ConfigManager(tmp_path)
        cmd = ConfigCommand(formatter, manager)

        options = ConfigOptions(project_dir=tmp_path, list_all=True)
        result = await cmd.execute(options)

        assert result.success is True
        assert "model" in result.config

    @pytest.mark.asyncio
    async def test_execute_get(self, formatter, tmp_path: Path) -> None:
        """Should get config value."""
        manager = ConfigManager(tmp_path)
        cmd = ConfigCommand(formatter, manager)

        options = ConfigOptions(project_dir=tmp_path, key="model")
        result = await cmd.execute(options)

        assert result.success is True
        assert "model" in result.config

    @pytest.mark.asyncio
    async def test_execute_set(self, formatter, tmp_path: Path) -> None:
        """Should set config value."""
        manager = ConfigManager(tmp_path)
        cmd = ConfigCommand(formatter, manager)

        options = ConfigOptions(project_dir=tmp_path, key="verbose", value="true")
        result = await cmd.execute(options)

        assert result.success is True
        assert manager.get("verbose") is True

    @pytest.mark.asyncio
    async def test_execute_reset(self, formatter, tmp_path: Path) -> None:
        """Should reset config."""
        manager = ConfigManager(tmp_path)
        manager.set("verbose", True)
        cmd = ConfigCommand(formatter, manager)

        options = ConfigOptions(project_dir=tmp_path, reset=True)
        result = await cmd.execute(options)

        assert result.success is True
        assert manager.get("verbose") == DEFAULT_CONFIG["verbose"]

    def test_parse_value_bool(self, formatter) -> None:
        """Should parse boolean values."""
        cmd = ConfigCommand(formatter)
        assert cmd._parse_value("true") is True
        assert cmd._parse_value("false") is False

    def test_parse_value_int(self, formatter) -> None:
        """Should parse integer values."""
        cmd = ConfigCommand(formatter)
        assert cmd._parse_value("42") == 42

    def test_parse_value_float(self, formatter) -> None:
        """Should parse float values."""
        cmd = ConfigCommand(formatter)
        assert cmd._parse_value("3.14") == 3.14

    def test_parse_value_string(self, formatter) -> None:
        """Should keep string values."""
        cmd = ConfigCommand(formatter)
        assert cmd._parse_value("hello") == "hello"


class TestQACommand:
    """Tests for QACommand class."""

    def test_init(self, formatter) -> None:
        """Should initialize command."""
        cmd = QACommand(formatter)
        assert cmd.formatter is formatter

    @pytest.mark.asyncio
    async def test_execute_spec_not_found(self, formatter, tmp_path: Path) -> None:
        """Should fail when spec not found."""
        cmd = QACommand(formatter)
        options = QAOptions(
            project_dir=tmp_path,
            spec_name="nonexistent",
        )
        result = await cmd.execute(options)

        assert result.success is False
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_show_status_no_signoff(self, formatter, tmp_path: Path) -> None:
        """Should handle missing QA status."""
        cmd = QACommand(formatter)

        specs_dir = tmp_path / ".claude-god-code" / "specs"
        (specs_dir / "001-test").mkdir(parents=True)

        options = QAOptions(project_dir=tmp_path, spec_name="001-test")
        result = await cmd.show_status(options)

        assert result.success is True

    def test_find_spec_dir_exact(self, formatter, tmp_path: Path) -> None:
        """Should find spec by exact name."""
        cmd = QACommand(formatter)

        specs_dir = tmp_path / ".claude-god-code" / "specs"
        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        result = cmd._find_spec_dir(specs_dir, "001-test")
        assert result == spec_dir

    def test_find_spec_dir_partial(self, formatter, tmp_path: Path) -> None:
        """Should find spec by partial name."""
        cmd = QACommand(formatter)

        specs_dir = tmp_path / ".claude-god-code" / "specs"
        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        result = cmd._find_spec_dir(specs_dir, "001")
        assert result == spec_dir


class TestQAOptions:
    """Tests for QAOptions dataclass."""

    def test_create_options(self, tmp_path: Path) -> None:
        """Should create options."""
        options = QAOptions(
            project_dir=tmp_path,
            spec_name="001-test",
            max_iterations=25,
            auto_fix=True,
        )
        assert options.spec_name == "001-test"
        assert options.max_iterations == 25
        assert options.auto_fix is True


class TestQAResult:
    """Tests for QAResult dataclass."""

    def test_success_result(self) -> None:
        """Should create success result."""
        result = QAResult(
            success=True,
            approved=True,
            iterations=5,
            issues_found=2,
            fixes_applied=2,
            message="Passed",
        )
        assert result.success is True
        assert result.approved is True

    def test_failed_result(self) -> None:
        """Should create failed result."""
        result = QAResult(
            success=False,
            message="Error occurred",
        )
        assert result.success is False
        assert result.approved is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
