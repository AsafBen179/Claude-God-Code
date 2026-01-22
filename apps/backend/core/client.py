"""
Claude SDK Client Configuration
===============================

Functions for creating and configuring the Claude Agent SDK client.

All AI interactions should use `create_client()` to ensure consistent OAuth
authentication and proper tool/MCP configuration.

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from core.auth import (
    get_sdk_env_vars,
    require_auth_token,
    validate_token_not_encrypted,
)
from core.platform import is_windows, validate_cli_path

logger = logging.getLogger(__name__)

_PROJECT_INDEX_CACHE: dict[str, tuple[dict[str, Any], dict[str, bool], float]] = {}
_CACHE_TTL_SECONDS = 300
_CACHE_LOCK = threading.Lock()


def _get_cached_project_data(
    project_dir: Path,
) -> tuple[dict[str, Any], dict[str, bool]]:
    """
    Get project index and capabilities with caching.

    Args:
        project_dir: Path to the project directory

    Returns:
        Tuple of (project_index, project_capabilities)
    """
    key = str(project_dir.resolve())
    now = time.time()
    debug = os.environ.get("DEBUG", "").lower() in ("true", "1")

    with _CACHE_LOCK:
        if key in _PROJECT_INDEX_CACHE:
            cached_index, cached_capabilities, cached_time = _PROJECT_INDEX_CACHE[key]
            cache_age = now - cached_time
            if cache_age < _CACHE_TTL_SECONDS:
                if debug:
                    print(
                        f"[ClientCache] Cache HIT for project index (age: {cache_age:.1f}s / TTL: {_CACHE_TTL_SECONDS}s)"
                    )
                logger.debug(f"Using cached project index for {project_dir}")
                return copy.deepcopy(cached_index), copy.deepcopy(cached_capabilities)
            elif debug:
                print(
                    f"[ClientCache] Cache EXPIRED for project index (age: {cache_age:.1f}s > TTL: {_CACHE_TTL_SECONDS}s)"
                )

    load_start = time.time()
    logger.debug(f"Loading project index for {project_dir}")
    project_index = load_project_index(project_dir)
    project_capabilities = detect_project_capabilities(project_index)

    if debug:
        load_duration = (time.time() - load_start) * 1000
        print(f"[ClientCache] Cache MISS - loaded project index in {load_duration:.1f}ms")

    with _CACHE_LOCK:
        if key in _PROJECT_INDEX_CACHE:
            cached_index, cached_capabilities, cached_time = _PROJECT_INDEX_CACHE[key]
            cache_age = time.time() - cached_time
            if cache_age < _CACHE_TTL_SECONDS:
                if debug:
                    print("[ClientCache] Cache was populated by another thread, using cached data")
                return copy.deepcopy(cached_index), copy.deepcopy(cached_capabilities)
        _PROJECT_INDEX_CACHE[key] = (project_index, project_capabilities, time.time())

    return project_index, project_capabilities


def invalidate_project_cache(project_dir: Path | None = None) -> None:
    """Invalidate the project index cache."""
    with _CACHE_LOCK:
        if project_dir is None:
            _PROJECT_INDEX_CACHE.clear()
            logger.debug("Cleared all project index cache entries")
        else:
            key = str(project_dir.resolve())
            if key in _PROJECT_INDEX_CACHE:
                del _PROJECT_INDEX_CACHE[key]
                logger.debug(f"Invalidated project index cache for {project_dir}")


def load_project_index(project_dir: Path) -> dict[str, Any]:
    """
    Load project index from .claude-god-code directory.

    Args:
        project_dir: Root directory of the project

    Returns:
        Project index dict or empty dict if not found
    """
    index_path = project_dir / ".claude-god-code" / "project_index.json"
    if index_path.exists():
        try:
            with open(index_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def detect_project_capabilities(project_index: dict[str, Any]) -> dict[str, bool]:
    """
    Detect project capabilities from index.

    Args:
        project_index: Project index dict

    Returns:
        Dict of capability flags
    """
    capabilities = {
        "is_node_project": False,
        "is_python_project": False,
        "is_rust_project": False,
        "is_go_project": False,
        "is_dotnet_project": False,
        "has_tests": False,
        "has_docker": False,
        "has_ci": False,
    }

    tech_stack = project_index.get("tech_stack", {})
    frameworks = tech_stack.get("frameworks", [])
    languages = tech_stack.get("languages", [])

    if "node" in languages or "typescript" in languages or "javascript" in languages:
        capabilities["is_node_project"] = True
    if "python" in languages:
        capabilities["is_python_project"] = True
    if "rust" in languages:
        capabilities["is_rust_project"] = True
    if "go" in languages:
        capabilities["is_go_project"] = True
    if "csharp" in languages or "dotnet" in frameworks:
        capabilities["is_dotnet_project"] = True

    if project_index.get("has_tests"):
        capabilities["has_tests"] = True
    if project_index.get("has_docker"):
        capabilities["has_docker"] = True
    if project_index.get("has_ci"):
        capabilities["has_ci"] = True

    return capabilities


def should_use_claude_md() -> bool:
    """Check if CLAUDE.md instructions should be included in system prompt."""
    return os.environ.get("USE_CLAUDE_MD", "").lower() == "true"


def load_claude_md(project_dir: Path) -> str | None:
    """Load CLAUDE.md content from project root if it exists."""
    claude_md_path = project_dir / "CLAUDE.md"
    if claude_md_path.exists():
        try:
            return claude_md_path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def get_default_allowed_tools() -> list[str]:
    """Get the default list of allowed tools for agents."""
    return [
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
        "LS",
        "WebFetch",
        "WebSearch",
        "TodoRead",
        "TodoWrite",
        "Task",
    ]


def create_client(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    agent_type: str = "coder",
    max_thinking_tokens: int | None = None,
    output_format: dict | None = None,
    agents: dict | None = None,
) -> Any:
    """
    Create a Claude Agent SDK client with multi-layered security.

    Args:
        project_dir: Root directory for the project (working directory)
        spec_dir: Directory containing the spec (for settings file)
        model: Claude model to use
        agent_type: Agent type identifier (e.g., 'coder', 'planner', 'qa_reviewer')
        max_thinking_tokens: Token budget for extended thinking (None = disabled)
        output_format: Optional structured output format for validated JSON responses
        agents: Optional dict of subagent definitions for SDK parallel execution

    Returns:
        Configured ClaudeSDKClient

    Raises:
        ImportError: If claude_agent_sdk is not installed
        ValueError: If authentication fails
    """
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        from claude_agent_sdk.types import HookMatcher
    except ImportError:
        raise ImportError(
            "claude_agent_sdk is not installed. "
            "Install it with: pip install claude-agent-sdk>=0.1.19"
        )

    oauth_token = require_auth_token()
    validate_token_not_encrypted(oauth_token)

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

    sdk_env = get_sdk_env_vars()

    if "CLAUDE_CODE_GIT_BASH_PATH" in sdk_env:
        logger.info(f"Git Bash path found: {sdk_env['CLAUDE_CODE_GIT_BASH_PATH']}")
    elif is_windows():
        logger.warning("Git Bash path not detected on Windows!")

    project_index, project_capabilities = _get_cached_project_data(project_dir)

    allowed_tools_list = get_default_allowed_tools()

    project_path_str = str(project_dir.resolve())
    spec_path_str = str(spec_dir.resolve())

    security_settings = {
        "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True},
        "permissions": {
            "defaultMode": "acceptEdits",
            "allow": [
                "Read(./**)",
                "Write(./**)",
                "Edit(./**)",
                "Glob(./**)",
                "Grep(./**)",
                f"Read({project_path_str}/**)",
                f"Write({project_path_str}/**)",
                f"Edit({project_path_str}/**)",
                f"Glob({project_path_str}/**)",
                f"Grep({project_path_str}/**)",
                f"Read({spec_path_str}/**)",
                f"Write({spec_path_str}/**)",
                f"Edit({spec_path_str}/**)",
                "Bash(*)",
                "WebFetch(*)",
                "WebSearch(*)",
            ],
        },
    }

    settings_file = project_dir / ".claude_settings.json"
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(security_settings, f, indent=2)

    print(f"Security settings: {settings_file}")
    print("   - Sandbox enabled (OS-level bash isolation)")
    print(f"   - Filesystem restricted to: {project_dir.resolve()}")
    if max_thinking_tokens:
        print(f"   - Extended thinking: {max_thinking_tokens:,} tokens")
    else:
        print("   - Extended thinking: disabled")
    print()

    base_prompt = (
        f"You are an expert full-stack developer building production-quality software. "
        f"Your working directory is: {project_dir.resolve()}\n"
        f"Your filesystem access is RESTRICTED to this directory only. "
        f"Use relative paths (starting with ./) for all file operations. "
        f"Never use absolute paths or try to access files outside your working directory.\n\n"
        f"You follow existing code patterns, write clean maintainable code, and verify "
        f"your work through thorough testing. You communicate progress through Git commits "
        f"and build-progress.txt updates."
    )

    if should_use_claude_md():
        claude_md_content = load_claude_md(project_dir)
        if claude_md_content:
            base_prompt = f"{base_prompt}\n\n# Project Instructions (from CLAUDE.md)\n\n{claude_md_content}"
            print("   - CLAUDE.md: included in system prompt")
        else:
            print("   - CLAUDE.md: not found in project root")
    else:
        print("   - CLAUDE.md: disabled by project settings")
    print()

    options_kwargs: dict[str, Any] = {
        "model": model,
        "system_prompt": base_prompt,
        "allowed_tools": allowed_tools_list,
        "mcp_servers": {},
        "max_turns": 1000,
        "cwd": str(project_dir.resolve()),
        "settings": str(settings_file.resolve()),
        "env": sdk_env,
        "max_thinking_tokens": max_thinking_tokens,
        "max_buffer_size": 10 * 1024 * 1024,
        "enable_file_checkpointing": True,
    }

    env_cli_path = os.environ.get("CLAUDE_CLI_PATH")
    if env_cli_path and validate_cli_path(env_cli_path):
        options_kwargs["cli_path"] = env_cli_path
        logger.info(f"Using CLAUDE_CLI_PATH override: {env_cli_path}")

    if output_format:
        options_kwargs["output_format"] = output_format

    if agents:
        options_kwargs["agents"] = agents

    return ClaudeSDKClient(options=ClaudeAgentOptions(**options_kwargs))
