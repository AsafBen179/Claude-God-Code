"""
Platform Detection Utilities
============================

Cross-platform utilities for detecting the operating system and
platform-specific paths and capabilities.

Part of Claude God Code - Autonomous Excellence
"""

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or os.name == "nt"


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def get_platform_name() -> str:
    """Get a human-readable platform name."""
    if is_windows():
        return "Windows"
    elif is_macos():
        return "macOS"
    elif is_linux():
        return "Linux"
    else:
        return sys.platform


def get_home_dir() -> Path:
    """Get the user's home directory."""
    return Path.home()


def get_config_dir() -> Path:
    """
    Get the Claude God Code configuration directory.

    Returns:
        Platform-appropriate config directory path
    """
    if is_windows():
        app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(app_data) / "ClaudeGodCode"
    elif is_macos():
        return Path.home() / "Library" / "Application Support" / "ClaudeGodCode"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg_config) / "claude-god-code"


def get_data_dir() -> Path:
    """
    Get the Claude God Code data directory.

    Returns:
        Platform-appropriate data directory path
    """
    if is_windows():
        app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(app_data) / "ClaudeGodCode" / "data"
    elif is_macos():
        return Path.home() / "Library" / "Application Support" / "ClaudeGodCode" / "data"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        return Path(xdg_data) / "claude-god-code"


def get_cache_dir() -> Path:
    """
    Get the Claude God Code cache directory.

    Returns:
        Platform-appropriate cache directory path
    """
    if is_windows():
        app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(app_data) / "ClaudeGodCode" / "cache"
    elif is_macos():
        return Path.home() / "Library" / "Caches" / "ClaudeGodCode"
    else:
        xdg_cache = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
        return Path(xdg_cache) / "claude-god-code"


def validate_cli_path(cli_path: str) -> bool:
    """
    Validate that a CLI path is safe to use.

    Args:
        cli_path: Path to validate

    Returns:
        True if path is valid and safe
    """
    if not cli_path:
        return False

    try:
        path = Path(cli_path)
        if not path.exists():
            return False
        if not path.is_file():
            return False
        return True
    except (OSError, ValueError):
        return False


def get_python_version() -> tuple[int, int, int]:
    """Get the current Python version as a tuple."""
    return sys.version_info[:3]


def is_python_312_or_higher() -> bool:
    """Check if Python version is 3.12 or higher (required for Graphiti)."""
    major, minor, _ = get_python_version()
    return major >= 3 and minor >= 12


def is_git_repo(path: Path) -> bool:
    """
    Check if a directory is a git repository.

    Args:
        path: Directory to check

    Returns:
        True if directory is a git repository
    """
    git_dir = path / ".git"
    return git_dir.exists() and (git_dir.is_dir() or git_dir.is_file())
