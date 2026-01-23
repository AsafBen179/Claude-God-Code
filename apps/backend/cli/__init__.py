"""
CLI Layer for Claude God Code.

Part of Claude God Code - Autonomous Excellence

This package provides the command-line interface for the application,
including the main entry point, command handlers, and terminal formatting.
"""

from .entry import main, create_parser, CLIApplication, VERSION
from .formatter import (
    TerminalFormatter,
    FormatterConfig,
    Color,
    Style,
    create_formatter,
)
from .commands import (
    StartCommand,
    StatusCommand,
    ConfigCommand,
    QACommand,
)

__all__ = [
    "main",
    "create_parser",
    "CLIApplication",
    "VERSION",
    "TerminalFormatter",
    "FormatterConfig",
    "Color",
    "Style",
    "create_formatter",
    "StartCommand",
    "StatusCommand",
    "ConfigCommand",
    "QACommand",
]
