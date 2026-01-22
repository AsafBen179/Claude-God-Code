"""
Claude God Code - Core Module
=============================

Foundation layer providing authentication, git operations, and workspace management.

Part of Claude God Code - Autonomous Excellence
"""

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

from core.git_executable import (
    get_git_executable,
    get_isolated_git_env,
    invalidate_git_cache,
    run_git,
)

from core.auth import (
    ensure_authenticated,
    ensure_claude_code_oauth_token,
    get_auth_token,
    get_auth_token_source,
    get_sdk_env_vars,
    is_encrypted_token,
    require_auth_token,
    validate_token_not_encrypted,
)

from core.worktree import (
    PushAndCreatePRResult,
    PushBranchResult,
    PullRequestResult,
    WorktreeError,
    WorktreeInfo,
    WorktreeManager,
)

from core.client import (
    create_client,
    detect_project_capabilities,
    get_default_allowed_tools,
    invalidate_project_cache,
    load_claude_md,
    load_project_index,
    should_use_claude_md,
)

__all__ = [
    # Platform utilities
    "is_windows",
    "is_macos",
    "is_linux",
    "get_platform_name",
    "get_home_dir",
    "get_config_dir",
    "get_data_dir",
    "get_cache_dir",
    "validate_cli_path",
    "get_python_version",
    "is_python_312_or_higher",
    # Git utilities
    "get_git_executable",
    "get_isolated_git_env",
    "invalidate_git_cache",
    "run_git",
    # Authentication
    "get_auth_token",
    "get_auth_token_source",
    "require_auth_token",
    "is_encrypted_token",
    "validate_token_not_encrypted",
    "get_sdk_env_vars",
    "ensure_claude_code_oauth_token",
    "ensure_authenticated",
    # Worktree management
    "WorktreeManager",
    "WorktreeInfo",
    "WorktreeError",
    "PushBranchResult",
    "PullRequestResult",
    "PushAndCreatePRResult",
    # Client
    "create_client",
    "load_project_index",
    "detect_project_capabilities",
    "invalidate_project_cache",
    "load_claude_md",
    "should_use_claude_md",
    "get_default_allowed_tools",
]
