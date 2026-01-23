"""
Config Command Handler.

Part of Claude God Code - Autonomous Excellence

Handles configuration management for the CLI.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.platform import get_config_dir

from ..formatter import TerminalFormatter

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "max_turns": 100,
    "max_qa_iterations": 50,
    "auto_fix": False,
    "isolated_mode": True,
    "verbose": False,
    "color_output": True,
}


@dataclass
class ConfigOptions:
    """Options for the config command."""

    project_dir: Path
    key: Optional[str] = None
    value: Optional[str] = None
    reset: bool = False
    list_all: bool = False


@dataclass
class ConfigResult:
    """Result of the config command."""

    success: bool
    config: dict[str, Any] = field(default_factory=dict)
    message: str = ""


class ConfigManager:
    """Manages configuration storage and retrieval."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize config manager."""
        self.config_dir = config_dir or get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self._cache: Optional[dict[str, Any]] = None

    def load(self) -> dict[str, Any]:
        """Load configuration from file."""
        if self._cache is not None:
            return self._cache

        if not self.config_file.exists():
            self._cache = DEFAULT_CONFIG.copy()
            return self._cache

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._cache = {**DEFAULT_CONFIG, **loaded}
            return self._cache
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load config: {e}")
            self._cache = DEFAULT_CONFIG.copy()
            return self._cache

    def save(self, config: dict[str, Any]) -> None:
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        self._cache = config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        config = self.load()
        return config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        config = self.load()
        config[key] = value
        self.save(config)

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self.save(DEFAULT_CONFIG.copy())
        self._cache = DEFAULT_CONFIG.copy()


class ConfigCommand:
    """Command handler for configuration management."""

    def __init__(
        self,
        formatter: TerminalFormatter,
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        """Initialize config command."""
        self.formatter = formatter
        self.config_manager = config_manager or ConfigManager()

    async def execute(self, options: ConfigOptions) -> ConfigResult:
        """Execute the config command."""
        self.formatter.header("Claude God Code", "Configuration")

        if options.reset:
            return self._handle_reset()

        if options.key and options.value:
            return self._handle_set(options.key, options.value)

        if options.key:
            return self._handle_get(options.key)

        return self._handle_list()

    def _handle_reset(self) -> ConfigResult:
        """Handle config reset."""
        self.config_manager.reset()
        self.formatter.success("Configuration reset to defaults")

        return ConfigResult(
            success=True,
            config=DEFAULT_CONFIG.copy(),
            message="Configuration reset to defaults",
        )

    def _handle_set(self, key: str, value: str) -> ConfigResult:
        """Handle setting a config value."""
        if key not in DEFAULT_CONFIG:
            self.formatter.warning(f"Unknown configuration key: {key}")

        parsed_value = self._parse_value(value)
        self.config_manager.set(key, parsed_value)
        self.formatter.success(f"Set {key} = {parsed_value}")

        return ConfigResult(
            success=True,
            config={key: parsed_value},
            message=f"Configuration updated: {key} = {parsed_value}",
        )

    def _handle_get(self, key: str) -> ConfigResult:
        """Handle getting a config value."""
        config = self.config_manager.load()

        if key not in config:
            self.formatter.error(f"Unknown configuration key: {key}")
            return ConfigResult(
                success=False,
                message=f"Unknown key: {key}",
            )

        value = config[key]
        self.formatter.key_value(key, value)

        return ConfigResult(
            success=True,
            config={key: value},
            message=f"{key} = {value}",
        )

    def _handle_list(self) -> ConfigResult:
        """Handle listing all config values."""
        config = self.config_manager.load()

        self.formatter.section("Current Configuration")
        for key, value in sorted(config.items()):
            default = DEFAULT_CONFIG.get(key)
            is_default = value == default
            suffix = " (default)" if is_default else ""
            self.formatter.key_value(key, f"{value}{suffix}")

        return ConfigResult(
            success=True,
            config=config,
            message="Configuration listed",
        )

    def _parse_value(self, value: str) -> Any:
        """Parse a string value to appropriate type."""
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value


def get_config_value(key: str, default: Any = None) -> Any:
    """Convenience function to get a config value."""
    manager = ConfigManager()
    return manager.get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """Convenience function to set a config value."""
    manager = ConfigManager()
    manager.set(key, value)
