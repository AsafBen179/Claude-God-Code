"""
Authentication Helpers for Claude God Code
==========================================

Provides centralized authentication token resolution with fallback support
for multiple environment variables, and SDK environment variable passthrough
for custom API endpoints.

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from core.platform import is_linux, is_macos, is_windows

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import secretstorage
else:
    try:
        import secretstorage
    except ImportError:
        secretstorage = None

AUTH_TOKEN_ENV_VARS = [
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
]

SDK_ENV_VARS = [
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "NO_PROXY",
    "DISABLE_TELEMETRY",
    "DISABLE_COST_WARNINGS",
    "API_TIMEOUT_MS",
    "CLAUDE_CODE_GIT_BASH_PATH",
    "CLAUDE_CLI_PATH",
    "CLAUDE_CONFIG_DIR",
]


def is_encrypted_token(token: str | None) -> bool:
    """Check if a token is encrypted (has 'enc:' prefix)."""
    return bool(token and token.startswith("enc:"))


def validate_token_not_encrypted(token: str) -> None:
    """
    Validate that a token is not in encrypted format.

    Args:
        token: Token string to validate

    Raises:
        ValueError: If token is in encrypted format (enc:...)
    """
    if is_encrypted_token(token):
        raise ValueError(
            "Authentication token is in encrypted format and cannot be used.\n\n"
            "The token decryption process failed or was not attempted.\n\n"
            "To fix this issue:\n"
            "  1. Re-authenticate with Claude Code CLI: claude setup-token\n"
            "  2. Or set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in your .env file\n\n"
            "Note: Encrypted tokens require the Claude Code CLI to be installed\n"
            "and properly configured with system keychain access."
        )


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt Claude Code encrypted token.

    Args:
        encrypted_token: Token with 'enc:' prefix from Claude Code CLI

    Returns:
        Decrypted token in format 'sk-ant-oat01-...'

    Raises:
        ValueError: If token format is invalid or decryption fails
    """
    if not isinstance(encrypted_token, str):
        raise ValueError(
            f"Invalid token type. Expected string, got: {type(encrypted_token).__name__}"
        )

    if not encrypted_token.startswith("enc:"):
        raise ValueError(
            "Invalid encrypted token format. Token must start with 'enc:' prefix."
        )

    encrypted_data = encrypted_token[4:]

    if not encrypted_data:
        raise ValueError("Empty encrypted token data after 'enc:' prefix")

    if len(encrypted_data) < 10:
        raise ValueError(
            "Encrypted token data is too short. The token may be corrupted."
        )

    if not all(c.isalnum() or c in "+-_/=" for c in encrypted_data):
        raise ValueError(
            "Encrypted token contains invalid characters. "
            "Expected base64-encoded data. The token may be corrupted."
        )

    try:
        if is_macos():
            return _decrypt_token_macos(encrypted_data)
        elif is_linux():
            return _decrypt_token_linux(encrypted_data)
        elif is_windows():
            return _decrypt_token_windows(encrypted_data)
        else:
            raise ValueError("Unsupported platform for token decryption")

    except NotImplementedError as e:
        logger.warning(
            "Token decryption failed: %s. Users must use plaintext tokens.", str(e)
        )
        raise ValueError(
            f"Encrypted token decryption is not yet implemented: {str(e)}\n\n"
            "To fix this issue:\n"
            "  1. Set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token (without 'enc:' prefix)\n"
            "  2. Or re-authenticate with: claude setup-token"
        )
    except ValueError:
        raise
    except FileNotFoundError as e:
        raise ValueError(
            f"Failed to decrypt token - required file not found: {str(e)}\n\n"
            "To fix this issue:\n"
            "  1. Re-authenticate with Claude Code CLI: claude setup-token\n"
            "  2. Or set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in your .env file"
        )
    except PermissionError as e:
        raise ValueError(
            f"Failed to decrypt token - permission denied: {str(e)}\n\n"
            "To fix this issue:\n"
            "  1. Grant keychain/credential manager access to this application\n"
            "  2. Or set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in your .env file"
        )
    except subprocess.TimeoutExpired:
        raise ValueError(
            "Failed to decrypt token - operation timed out.\n\n"
            "This may indicate a problem with system keychain access.\n\n"
            "To fix this issue:\n"
            "  1. Re-authenticate with Claude Code CLI: claude setup-token\n"
            "  2. Or set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in your .env file"
        )
    except Exception as e:
        error_type = type(e).__name__
        raise ValueError(
            f"Failed to decrypt token ({error_type}): {str(e)}\n\n"
            "To fix this issue:\n"
            "  1. Re-authenticate with Claude Code CLI: claude setup-token\n"
            "  2. Or set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in your .env file\n\n"
            "Note: Encrypted tokens (enc:...) require the Claude Code CLI to be installed\n"
            "and properly configured with system keychain access."
        )


def _decrypt_token_macos(encrypted_data: str) -> str:
    """Decrypt token on macOS using Keychain."""
    if not shutil.which("claude"):
        raise ValueError(
            "Claude Code CLI not found. Please install it from https://code.claude.com"
        )

    raise NotImplementedError(
        "Encrypted tokens in environment variables are not supported. "
        "Please use one of these options:\n"
        "  1. Run 'claude setup-token' to store token in system keychain\n"
        "  2. Set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in .env file\n\n"
        "Note: This requires Claude Agent SDK >= 0.1.19"
    )


def _decrypt_token_linux(encrypted_data: str) -> str:
    """Decrypt token on Linux using Secret Service API."""
    if secretstorage is None:
        raise ValueError(
            "secretstorage library not found. Install it with: pip install secretstorage"
        )

    raise NotImplementedError(
        "Encrypted tokens in environment variables are not supported. "
        "Please use one of these options:\n"
        "  1. Run 'claude setup-token' to store token in system keychain\n"
        "  2. Set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in .env file\n\n"
        "Note: This requires Claude Agent SDK >= 0.1.19"
    )


def _decrypt_token_windows(encrypted_data: str) -> str:
    """Decrypt token on Windows using Credential Manager."""
    raise NotImplementedError(
        "Encrypted tokens in environment variables are not supported. "
        "Please use one of these options:\n"
        "  1. Run 'claude setup-token' to store token in system keychain\n"
        "  2. Set CLAUDE_CODE_OAUTH_TOKEN to a plaintext token in .env file\n\n"
        "Note: This requires Claude Agent SDK >= 0.1.19"
    )


def _try_decrypt_token(token: str | None) -> str | None:
    """
    Attempt to decrypt an encrypted token, returning original if decryption fails.
    """
    if not token:
        return None

    if is_encrypted_token(token):
        try:
            return decrypt_token(token)
        except ValueError:
            return token

    return token


def get_token_from_keychain() -> str | None:
    """
    Get authentication token from system credential store.

    Returns:
        Token string if found, None otherwise
    """
    if is_macos():
        return _get_token_from_macos_keychain()
    elif is_windows():
        return _get_token_from_windows_credential_files()
    else:
        return _get_token_from_linux_secret_service()


def _get_token_from_macos_keychain() -> str | None:
    """Get token from macOS Keychain."""
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                "Claude Code-credentials",
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        credentials_json = result.stdout.strip()
        if not credentials_json:
            return None

        data = json.loads(credentials_json)
        token = data.get("claudeAiOauth", {}).get("accessToken")

        if not token:
            return None

        if not token.startswith("sk-ant-oat01-"):
            return None

        return token

    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, Exception):
        return None


def _get_token_from_windows_credential_files() -> str | None:
    """Get token from Windows credential files."""
    try:
        cred_paths = [
            os.path.expandvars(r"%USERPROFILE%\.claude\.credentials.json"),
            os.path.expandvars(r"%USERPROFILE%\.claude\credentials.json"),
            os.path.expandvars(r"%LOCALAPPDATA%\Claude\credentials.json"),
            os.path.expandvars(r"%APPDATA%\Claude\credentials.json"),
        ]

        for cred_path in cred_paths:
            if os.path.exists(cred_path):
                with open(cred_path, encoding="utf-8") as f:
                    data = json.load(f)
                    token = data.get("claudeAiOauth", {}).get("accessToken")
                    if token and token.startswith("sk-ant-oat01-"):
                        return token

        return None

    except (json.JSONDecodeError, KeyError, FileNotFoundError, Exception):
        return None


def _get_token_from_linux_secret_service() -> str | None:
    """Get token from Linux Secret Service API via DBus."""
    if secretstorage is None:
        return None

    try:
        try:
            collection = secretstorage.get_default_collection(None)
        except (
            AttributeError,
            secretstorage.exceptions.SecretServiceNotAvailableException,
        ):
            return None

        if collection.is_locked():
            try:
                collection.unlock()
            except secretstorage.exceptions.SecretStorageException:
                return None

        items = collection.search_items({"application": "claude-code"})

        for item in items:
            label = item.get_label()
            if label == "Claude Code-credentials":
                secret = item.get_secret()
                if not secret:
                    continue

                try:
                    if isinstance(secret, bytes):
                        secret = secret.decode("utf-8")
                    data = json.loads(secret)
                    token = data.get("claudeAiOauth", {}).get("accessToken")

                    if token and token.startswith("sk-ant-oat01-"):
                        return token
                except json.JSONDecodeError:
                    continue

        return None

    except (
        secretstorage.exceptions.SecretStorageException,
        json.JSONDecodeError,
        KeyError,
        AttributeError,
        TypeError,
    ):
        return None


def _get_token_from_config_dir(config_dir: str) -> str | None:
    """Read token from a custom config directory's credentials file."""
    expanded_dir = os.path.expanduser(config_dir)

    cred_files = [
        os.path.join(expanded_dir, ".credentials.json"),
        os.path.join(expanded_dir, "credentials.json"),
    ]

    for cred_path in cred_files:
        if os.path.exists(cred_path):
            try:
                with open(cred_path, encoding="utf-8") as f:
                    data = json.load(f)

                oauth_data = data.get("claudeAiOauth") or data.get("oauthAccount") or {}
                token = oauth_data.get("accessToken")

                if token and (
                    token.startswith("sk-ant-oat01-") or token.startswith("enc:")
                ):
                    logger.debug(f"Found token in {cred_path}")
                    return token
            except (json.JSONDecodeError, KeyError, Exception) as e:
                logger.debug(f"Failed to read {cred_path}: {e}")
                continue

    return None


def get_auth_token(config_dir: str | None = None) -> str | None:
    """
    Get authentication token from environment variables or credential store.

    Args:
        config_dir: Optional custom config directory (profile's configDir).

    Returns:
        Token string if found, None otherwise
    """
    for var in AUTH_TOKEN_ENV_VARS:
        token = os.environ.get(var)
        if token:
            return _try_decrypt_token(token)

    env_config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    effective_config_dir = config_dir or env_config_dir

    if effective_config_dir:
        token = _get_token_from_config_dir(effective_config_dir)
        if token:
            return _try_decrypt_token(token)

    return _try_decrypt_token(get_token_from_keychain())


def get_auth_token_source(config_dir: str | None = None) -> str | None:
    """Get the name of the source that provided the auth token."""
    for var in AUTH_TOKEN_ENV_VARS:
        if os.environ.get(var):
            return var

    env_config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    effective_config_dir = config_dir or env_config_dir
    if effective_config_dir and _get_token_from_config_dir(effective_config_dir):
        return "CLAUDE_CONFIG_DIR"

    if get_token_from_keychain():
        if is_macos():
            return "macOS Keychain"
        elif is_windows():
            return "Windows Credential Files"
        else:
            return "Linux Secret Service"

    return None


def require_auth_token(config_dir: str | None = None) -> str:
    """
    Get authentication token or raise ValueError.

    Raises:
        ValueError: If no auth token is found in any supported source
    """
    token = get_auth_token(config_dir)
    if not token:
        error_msg = (
            "No OAuth token found.\n\n"
            "Claude God Code requires Claude Code OAuth authentication.\n"
            "Direct API keys (ANTHROPIC_API_KEY) are not supported.\n\n"
        )
        if is_macos():
            error_msg += (
                "To authenticate:\n"
                "  1. Run: claude\n"
                "  2. Type: /login\n"
                "  3. Press Enter to open browser\n"
                "  4. Complete OAuth login in browser\n\n"
                "The token will be saved to macOS Keychain automatically."
            )
        elif is_windows():
            error_msg += (
                "To authenticate:\n"
                "  1. Run: claude\n"
                "  2. Type: /login\n"
                "  3. Press Enter to open browser\n"
                "  4. Complete OAuth login in browser\n\n"
                "The token will be saved to Windows Credential Manager."
            )
        else:
            error_msg += (
                "To authenticate:\n"
                "  1. Run: claude\n"
                "  2. Type: /login\n"
                "  3. Press Enter to open browser\n"
                "  4. Complete OAuth login in browser\n\n"
                "Or set CLAUDE_CODE_OAUTH_TOKEN in your .env file."
            )
        raise ValueError(error_msg)
    return token


def _find_git_bash_path() -> str | None:
    """Find git-bash (bash.exe) path on Windows."""
    if not is_windows():
        return None

    existing = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if existing and os.path.exists(existing):
        return existing

    git_path = None

    try:
        result = subprocess.run(
            ["where.exe", "git"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            git_paths = result.stdout.strip().splitlines()
            if git_paths:
                git_path = git_paths[0].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    if not git_path:
        common_git_paths = [
            os.path.expandvars(r"%PROGRAMFILES%\Git\cmd\git.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Git\bin\git.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Git\cmd\git.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        ]
        for path in common_git_paths:
            if os.path.exists(path):
                git_path = path
                break

    if not git_path:
        return None

    git_dir = os.path.dirname(git_path)
    git_parent = os.path.dirname(git_dir)
    git_grandparent = os.path.dirname(git_parent)

    possible_bash_paths = [
        os.path.join(git_parent, "bin", "bash.exe"),
        os.path.join(git_dir, "bash.exe"),
        os.path.join(git_grandparent, "bin", "bash.exe"),
    ]

    for bash_path in possible_bash_paths:
        if os.path.exists(bash_path):
            return bash_path

    return None


def get_sdk_env_vars() -> dict[str, str]:
    """
    Get environment variables to pass to SDK.

    Returns:
        Dict of env var name -> value for non-empty vars
    """
    env = {}
    for var in SDK_ENV_VARS:
        value = os.environ.get(var)
        if value:
            env[var] = value

    if is_windows() and "CLAUDE_CODE_GIT_BASH_PATH" not in env:
        bash_path = _find_git_bash_path()
        if bash_path:
            env["CLAUDE_CODE_GIT_BASH_PATH"] = bash_path

    env["PYTHONPATH"] = ""

    return env


def ensure_claude_code_oauth_token() -> None:
    """Ensure CLAUDE_CODE_OAUTH_TOKEN is set (for SDK compatibility)."""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return

    token = get_auth_token()
    if token:
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token


def ensure_authenticated() -> str:
    """
    Ensure the user is authenticated, prompting for login if needed.

    Returns:
        The authentication token

    Raises:
        ValueError: If authentication fails after login attempt
    """
    token = get_auth_token()
    if token:
        return token

    print("\nNo OAuth token found. Starting login flow...")
    print("\nTo authenticate, run 'claude' and type '/login'")

    raise ValueError(
        "Authentication required.\n\n"
        "To authenticate:\n"
        "  1. Run: claude\n"
        "  2. Type: /login\n"
        "  3. Press Enter to open browser\n"
        "  4. Complete OAuth login in browser"
    )
