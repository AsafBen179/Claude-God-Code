"""
Tests for cli.entry module.

Part of Claude God Code - Autonomous Excellence
"""

import argparse
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from cli.entry import (
    create_parser,
    CLIApplication,
    main,
    VERSION,
)


class TestCreateParser:
    """Tests for create_parser function."""

    def test_creates_parser(self) -> None:
        """Should create argument parser."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_spec_argument(self) -> None:
        """Should parse --spec argument."""
        parser = create_parser()
        args = parser.parse_args(["--spec", "Add auth"])
        assert args.spec == "Add auth"

    def test_project_dir_argument(self) -> None:
        """Should parse --project-dir argument."""
        parser = create_parser()
        args = parser.parse_args(["--project-dir", "/tmp/project"])
        assert args.project_dir == Path("/tmp/project")

    def test_list_argument(self) -> None:
        """Should parse --list flag."""
        parser = create_parser()
        args = parser.parse_args(["--list"])
        assert args.list is True

    def test_status_argument(self) -> None:
        """Should parse --status flag."""
        parser = create_parser()
        args = parser.parse_args(["--status"])
        assert args.status is True

    def test_verbose_argument(self) -> None:
        """Should parse --verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose is True

    def test_isolated_argument(self) -> None:
        """Should parse --isolated flag."""
        parser = create_parser()
        args = parser.parse_args(["--isolated"])
        assert args.isolated is True

    def test_direct_argument(self) -> None:
        """Should parse --direct flag."""
        parser = create_parser()
        args = parser.parse_args(["--direct"])
        assert args.direct is True

    def test_merge_argument(self) -> None:
        """Should parse --merge flag."""
        parser = create_parser()
        args = parser.parse_args(["--merge"])
        assert args.merge is True

    def test_review_argument(self) -> None:
        """Should parse --review flag."""
        parser = create_parser()
        args = parser.parse_args(["--review"])
        assert args.review is True

    def test_discard_argument(self) -> None:
        """Should parse --discard flag."""
        parser = create_parser()
        args = parser.parse_args(["--discard"])
        assert args.discard is True

    def test_qa_argument(self) -> None:
        """Should parse --qa flag."""
        parser = create_parser()
        args = parser.parse_args(["--qa"])
        assert args.qa is True

    def test_force_argument(self) -> None:
        """Should parse --force flag."""
        parser = create_parser()
        args = parser.parse_args(["--force"])
        assert args.force is True

    def test_no_color_argument(self) -> None:
        """Should parse --no-color flag."""
        parser = create_parser()
        args = parser.parse_args(["--no-color"])
        assert args.no_color is True

    def test_model_argument(self) -> None:
        """Should parse --model argument."""
        parser = create_parser()
        args = parser.parse_args(["--model", "claude-3-5-sonnet-20241022"])
        assert args.model == "claude-3-5-sonnet-20241022"

    def test_resume_argument(self) -> None:
        """Should parse --resume argument."""
        parser = create_parser()
        args = parser.parse_args(["--resume", "session-123"])
        assert args.resume == "session-123"

    def test_max_iterations_argument(self) -> None:
        """Should parse --max-iterations argument."""
        parser = create_parser()
        args = parser.parse_args(["--max-iterations", "25"])
        assert args.max_iterations == 25

    def test_auto_fix_argument(self) -> None:
        """Should parse --auto-fix flag."""
        parser = create_parser()
        args = parser.parse_args(["--auto-fix"])
        assert args.auto_fix is True

    def test_combined_arguments(self) -> None:
        """Should parse multiple arguments together."""
        parser = create_parser()
        args = parser.parse_args([
            "--spec", "Add feature",
            "--verbose",
            "--force",
            "--max-iterations", "10",
        ])
        assert args.spec == "Add feature"
        assert args.verbose is True
        assert args.force is True
        assert args.max_iterations == 10


class TestCLIApplication:
    """Tests for CLIApplication class."""

    @pytest.fixture
    def basic_args(self) -> argparse.Namespace:
        """Create basic args namespace."""
        return argparse.Namespace(
            spec=None,
            project_dir=None,
            model=None,
            list=False,
            status=False,
            verbose=False,
            isolated=False,
            direct=False,
            merge=False,
            review=False,
            discard=False,
            qa=False,
            force=False,
            no_color=True,
            config=None,
            resume=None,
            max_iterations=50,
            auto_fix=False,
        )

    def test_init(self, basic_args, tmp_path: Path) -> None:
        """Should initialize application."""
        basic_args.project_dir = tmp_path
        app = CLIApplication(basic_args)
        assert app.project_dir == tmp_path

    def test_init_default_project_dir(self, basic_args) -> None:
        """Should use current directory as default."""
        app = CLIApplication(basic_args)
        assert app.project_dir == Path.cwd()

    def test_validate_project_dir_exists(self, basic_args, tmp_path: Path) -> None:
        """Should validate existing directory."""
        basic_args.project_dir = tmp_path
        basic_args.direct = True
        app = CLIApplication(basic_args)
        assert app._validate_project_dir() is True

    def test_validate_project_dir_not_exists(self, basic_args) -> None:
        """Should fail for non-existent directory."""
        basic_args.project_dir = Path("/nonexistent/path")
        app = CLIApplication(basic_args)
        assert app._validate_project_dir() is False


class TestCLIApplicationAsync:
    """Async tests for CLIApplication."""

    @pytest.fixture
    def basic_args(self) -> argparse.Namespace:
        """Create basic args namespace."""
        return argparse.Namespace(
            spec=None,
            project_dir=None,
            model=None,
            list=False,
            status=False,
            verbose=False,
            isolated=False,
            direct=False,
            merge=False,
            review=False,
            discard=False,
            qa=False,
            force=False,
            no_color=True,
            config=None,
            resume=None,
            max_iterations=50,
            auto_fix=False,
        )

    @pytest.mark.asyncio
    async def test_run_no_args(self, basic_args, tmp_path: Path) -> None:
        """Should show help when no args provided."""
        basic_args.project_dir = tmp_path
        basic_args.direct = True
        app = CLIApplication(basic_args)
        result = await app.run()
        assert result == 0

    @pytest.mark.asyncio
    async def test_run_list_specs(self, basic_args, tmp_path: Path) -> None:
        """Should list specs."""
        basic_args.project_dir = tmp_path
        basic_args.direct = True
        basic_args.list = True
        app = CLIApplication(basic_args)
        result = await app.run_list_specs()
        assert result == 0

    @pytest.mark.asyncio
    async def test_run_status(self, basic_args, tmp_path: Path) -> None:
        """Should show status."""
        basic_args.project_dir = tmp_path
        basic_args.direct = True
        app = CLIApplication(basic_args)
        result = await app.run_status()
        assert result == 0

    @pytest.mark.asyncio
    async def test_run_qa_spec_not_found(self, basic_args, tmp_path: Path) -> None:
        """Should fail when spec not found."""
        basic_args.project_dir = tmp_path
        basic_args.direct = True
        app = CLIApplication(basic_args)
        result = await app.run_qa("nonexistent-spec")
        assert result == 1


class TestFindSpecDir:
    """Tests for _find_spec_dir method."""

    @pytest.fixture
    def basic_args(self) -> argparse.Namespace:
        """Create basic args namespace."""
        return argparse.Namespace(
            spec=None,
            project_dir=None,
            model=None,
            list=False,
            status=False,
            verbose=False,
            isolated=False,
            direct=True,
            merge=False,
            review=False,
            discard=False,
            qa=False,
            force=False,
            no_color=True,
            config=None,
            resume=None,
            max_iterations=50,
            auto_fix=False,
        )

    def test_find_exact_match(self, basic_args, tmp_path: Path) -> None:
        """Should find spec by exact name."""
        basic_args.project_dir = tmp_path
        specs_dir = tmp_path / ".claude-god-code" / "specs"
        spec_dir = specs_dir / "001-add-auth"
        spec_dir.mkdir(parents=True)

        app = CLIApplication(basic_args)
        result = app._find_spec_dir(specs_dir, "001-add-auth")
        assert result == spec_dir

    def test_find_partial_match(self, basic_args, tmp_path: Path) -> None:
        """Should find spec by partial name."""
        basic_args.project_dir = tmp_path
        specs_dir = tmp_path / ".claude-god-code" / "specs"
        spec_dir = specs_dir / "001-add-auth"
        spec_dir.mkdir(parents=True)

        app = CLIApplication(basic_args)
        result = app._find_spec_dir(specs_dir, "001")
        assert result == spec_dir

    def test_find_not_found(self, basic_args, tmp_path: Path) -> None:
        """Should return None when spec not found."""
        basic_args.project_dir = tmp_path
        specs_dir = tmp_path / ".claude-god-code" / "specs"
        specs_dir.mkdir(parents=True)

        app = CLIApplication(basic_args)
        result = app._find_spec_dir(specs_dir, "nonexistent")
        assert result is None


class TestMainFunction:
    """Tests for main function."""

    def test_main_help(self) -> None:
        """Should show help and exit."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_main_version(self) -> None:
        """Should show version and exit."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0


class TestVersion:
    """Tests for version constant."""

    def test_version_format(self) -> None:
        """Version should be in semver format."""
        parts = VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
