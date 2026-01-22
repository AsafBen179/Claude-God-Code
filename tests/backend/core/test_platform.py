"""
Tests for core.platform module.

Part of Claude God Code - Autonomous Excellence
"""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from core.platform import (
    get_cache_dir,
    get_config_dir,
    get_data_dir,
    get_home_dir,
    get_platform_name,
    get_python_version,
    is_linux,
    is_macos,
    is_python_312_or_higher,
    is_windows,
    validate_cli_path,
)


class TestPlatformDetection:
    """Tests for platform detection functions."""

    def test_get_platform_name_returns_string(self) -> None:
        """Platform name should return a non-empty string."""
        name = get_platform_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_exactly_one_platform_is_true(self) -> None:
        """Exactly one of is_windows, is_macos, is_linux should be true (or none if exotic)."""
        platforms = [is_windows(), is_macos(), is_linux()]
        assert sum(platforms) <= 1  # At most one platform detected

    def test_get_home_dir_returns_path(self) -> None:
        """Home directory should be a valid Path."""
        home = get_home_dir()
        assert isinstance(home, Path)
        assert home.exists()

    def test_python_version_is_tuple(self) -> None:
        """Python version should return a 3-element tuple."""
        version = get_python_version()
        assert isinstance(version, tuple)
        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)

    def test_python_312_check(self) -> None:
        """Python 3.12+ check should match actual version."""
        major, minor, _ = get_python_version()
        expected = major >= 3 and minor >= 12
        assert is_python_312_or_higher() == expected


class TestDirectoryFunctions:
    """Tests for directory path functions."""

    def test_get_config_dir_returns_path(self) -> None:
        """Config dir should return a Path."""
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)
        # Path should contain some reference to claude-god-code
        assert "claude" in str(config_dir).lower()

    def test_get_data_dir_returns_path(self) -> None:
        """Data dir should return a Path."""
        data_dir = get_data_dir()
        assert isinstance(data_dir, Path)

    def test_get_cache_dir_returns_path(self) -> None:
        """Cache dir should return a Path."""
        cache_dir = get_cache_dir()
        assert isinstance(cache_dir, Path)


class TestValidateCLIPath:
    """Tests for CLI path validation."""

    def test_empty_path_returns_false(self) -> None:
        """Empty path should not be valid."""
        assert validate_cli_path("") is False
        assert validate_cli_path(None) is False  # type: ignore

    def test_nonexistent_path_returns_false(self) -> None:
        """Non-existent path should not be valid."""
        assert validate_cli_path("/nonexistent/path/to/cli") is False

    def test_directory_returns_false(self, tmp_path: Path) -> None:
        """Directory path should not be valid (must be file)."""
        assert validate_cli_path(str(tmp_path)) is False

    def test_existing_file_returns_true(self, tmp_path: Path) -> None:
        """Existing file should be valid."""
        test_file = tmp_path / "cli_test"
        test_file.touch()
        assert validate_cli_path(str(test_file)) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
