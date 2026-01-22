"""
Tests for spec.context module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from spec.context import ContextResolver


class TestContextResolver:
    """Tests for ContextResolver class."""

    def test_extract_keywords_basic(self, tmp_path: Path) -> None:
        """Should extract keywords from task description."""
        resolver = ContextResolver(tmp_path, tmp_path)
        keywords = resolver._extract_keywords("Add user authentication with OAuth")
        assert "user" in keywords
        assert "authentication" in keywords
        assert "oauth" in keywords
        # Stop words should be removed
        assert "with" not in keywords
        assert "add" not in keywords

    def test_extract_keywords_removes_stop_words(self, tmp_path: Path) -> None:
        """Should remove common stop words."""
        resolver = ContextResolver(tmp_path, tmp_path)
        keywords = resolver._extract_keywords("the user should be able to login")
        assert "the" not in keywords
        assert "should" not in keywords
        assert "user" in keywords
        assert "login" in keywords

    def test_extract_keywords_handles_camel_case(self, tmp_path: Path) -> None:
        """Should extract words from camelCase identifiers."""
        resolver = ContextResolver(tmp_path, tmp_path)
        keywords = resolver._extract_keywords("Update UserAuthenticationService")
        assert "user" in keywords
        assert "authentication" in keywords
        assert "service" in keywords

    def test_calculate_relevance(self, tmp_path: Path) -> None:
        """Should calculate relevance score correctly."""
        resolver = ContextResolver(tmp_path, tmp_path)

        # High relevance
        score = resolver._calculate_relevance(
            "user authentication login oauth",
            ["user", "authentication", "login"]
        )
        assert score > 0.5

        # Low relevance
        score = resolver._calculate_relevance(
            "unrelated content about databases",
            ["user", "authentication", "login"]
        )
        assert score < 0.3

    def test_detect_language(self, tmp_path: Path) -> None:
        """Should detect language from file suffix."""
        resolver = ContextResolver(tmp_path, tmp_path)
        assert resolver._detect_language(".ts") == "typescript"
        assert resolver._detect_language(".py") == "python"
        assert resolver._detect_language(".go") == "go"
        assert resolver._detect_language(".unknown") == "unknown"

    def test_should_ignore_node_modules(self, tmp_path: Path) -> None:
        """Should ignore node_modules directory."""
        resolver = ContextResolver(tmp_path, tmp_path)

        # Create node_modules path
        node_modules = tmp_path / "node_modules" / "package" / "index.js"
        node_modules.parent.mkdir(parents=True)
        node_modules.touch()

        assert resolver._should_ignore(node_modules) is True

    def test_should_not_ignore_src(self, tmp_path: Path) -> None:
        """Should not ignore src directory."""
        resolver = ContextResolver(tmp_path, tmp_path)

        src_file = tmp_path / "src" / "index.ts"
        src_file.parent.mkdir(parents=True)
        src_file.touch()

        assert resolver._should_ignore(src_file) is False


class TestExtractImports:
    """Tests for import extraction."""

    def test_extract_typescript_imports(self, tmp_path: Path) -> None:
        """Should extract TypeScript/JavaScript imports."""
        resolver = ContextResolver(tmp_path, tmp_path)

        content = '''
import React from 'react';
import { useState } from 'react';
import type { User } from './types';
import utils from '../utils';
'''

        imports = resolver._extract_imports(content, ".ts")
        assert "react" in imports
        assert "./types" in imports
        assert "../utils" in imports

    def test_extract_python_imports(self, tmp_path: Path) -> None:
        """Should extract Python imports."""
        resolver = ContextResolver(tmp_path, tmp_path)

        content = '''
import os
from pathlib import Path
from typing import Any, Dict
from .utils import helper
'''

        imports = resolver._extract_imports(content, ".py")
        assert "pathlib" in imports
        assert "typing" in imports


class TestExtractExports:
    """Tests for export extraction."""

    def test_extract_typescript_exports(self, tmp_path: Path) -> None:
        """Should extract TypeScript exports."""
        resolver = ContextResolver(tmp_path, tmp_path)

        content = '''
export const API_URL = 'https://api.example.com';
export function fetchUser() {}
export class UserService {}
export interface User {}
export type UserId = string;
export default App;
'''

        exports = resolver._extract_exports(content, ".ts")
        assert "API_URL" in exports
        assert "fetchUser" in exports
        assert "UserService" in exports
        assert "User" in exports
        assert "UserId" in exports
        assert "default" in exports


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
