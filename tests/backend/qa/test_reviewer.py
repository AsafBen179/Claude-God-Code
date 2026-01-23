"""
Tests for qa.reviewer module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from qa.criteria import IssueSeverity
from qa.reviewer import (
    CodeReviewer,
    ReviewCategory,
    ReviewCheck,
    ReviewResult,
    TestRunner,
)


class TestReviewCheck:
    """Tests for ReviewCheck dataclass."""

    def test_create_check(self) -> None:
        """Should create check with correct fields."""
        check = ReviewCheck(
            name="test_check",
            category=ReviewCategory.SECURITY,
            description="Test check",
            pattern=r"test_pattern",
        )
        assert check.name == "test_check"
        assert check.category == ReviewCategory.SECURITY

    def test_matches_file_no_patterns(self) -> None:
        """Should match all files when no patterns specified."""
        check = ReviewCheck(
            name="test",
            category=ReviewCategory.STYLE,
            description="",
        )
        assert check.matches_file("any/file.py") is True
        assert check.matches_file("another.ts") is True

    def test_matches_file_with_patterns(self) -> None:
        """Should only match specified patterns."""
        check = ReviewCheck(
            name="test",
            category=ReviewCategory.STYLE,
            description="",
            file_patterns=["*.py"],
        )
        assert check.matches_file("test.py") is True
        assert check.matches_file("test.ts") is False


class TestReviewResult:
    """Tests for ReviewResult dataclass."""

    def test_create_passed_result(self) -> None:
        """Should create passed result."""
        result = ReviewResult(passed=True)
        assert result.passed is True
        assert len(result.issues) == 0

    def test_create_failed_result(self) -> None:
        """Should create failed result with issues."""
        from qa.criteria import QAIssue

        issues = [
            QAIssue(title="Test", severity=IssueSeverity.HIGH, description=""),
        ]
        result = ReviewResult(passed=False, issues=issues)
        assert result.passed is False
        assert len(result.issues) == 1

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        result = ReviewResult(
            passed=True,
            files_reviewed=10,
            checks_performed=50,
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["files_reviewed"] == 10


class TestCodeReviewer:
    """Tests for CodeReviewer class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize reviewer with repo root."""
        reviewer = CodeReviewer(tmp_path)
        assert reviewer.repo_root == tmp_path

    def test_should_ignore_node_modules(self, tmp_path: Path) -> None:
        """Should ignore node_modules directory."""
        reviewer = CodeReviewer(tmp_path)
        node_path = tmp_path / "node_modules" / "package" / "index.js"
        assert reviewer._should_ignore(node_path) is True

    def test_should_not_ignore_src(self, tmp_path: Path) -> None:
        """Should not ignore src directory."""
        reviewer = CodeReviewer(tmp_path)
        src_path = tmp_path / "src" / "index.py"
        assert reviewer._should_ignore(src_path) is False

    def test_run_check_finds_pattern(self, tmp_path: Path) -> None:
        """Should find issues matching pattern."""
        reviewer = CodeReviewer(tmp_path)
        check = ReviewCheck(
            name="hardcoded_secret",
            category=ReviewCategory.SECURITY,
            description="Found hardcoded secret",
            pattern=r"api_key\s*=\s*['\"]",
            severity=IssueSeverity.CRITICAL,
        )

        content = '''
        def connect():
            api_key = "secret123"
            return api_key
        '''

        issues = reviewer._run_check(check, content, "test.py")
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.CRITICAL

    def test_run_check_no_match(self, tmp_path: Path) -> None:
        """Should return empty when no pattern match."""
        reviewer = CodeReviewer(tmp_path)
        check = ReviewCheck(
            name="hardcoded_secret",
            category=ReviewCategory.SECURITY,
            description="",
            pattern=r"api_key\s*=\s*['\"]",
        )

        content = '''
        def connect():
            api_key = os.environ.get("API_KEY")
            return api_key
        '''

        issues = reviewer._run_check(check, content, "test.py")
        assert len(issues) == 0


class TestCodeReviewerAsync:
    """Async tests for CodeReviewer."""

    @pytest.mark.asyncio
    async def test_review_file_with_issues(self, tmp_path: Path) -> None:
        """Should detect issues in file."""
        # Create test file with security issue
        test_file = tmp_path / "test.py"
        test_file.write_text('''
api_key = "hardcoded_secret"
password = "admin123"

def login():
    eval(user_input)  # Dangerous
''', encoding="utf-8")

        reviewer = CodeReviewer(tmp_path)
        issues = await reviewer.review_file(test_file)

        # Should find hardcoded secrets and eval usage
        assert len(issues) >= 2
        issue_names = [i.title.lower() for i in issues]
        assert any("secret" in name or "eval" in name for name in issue_names)

    @pytest.mark.asyncio
    async def test_review_file_clean(self, tmp_path: Path) -> None:
        """Should pass clean file."""
        test_file = tmp_path / "clean.py"
        test_file.write_text('''
import os

def get_config():
    api_key = os.environ.get("API_KEY", "")
    return {"key": api_key}
''', encoding="utf-8")

        reviewer = CodeReviewer(tmp_path)
        issues = await reviewer.review_file(test_file)

        # Should have no critical/high issues
        critical = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical) == 0

    @pytest.mark.asyncio
    async def test_review_detects_breaking_changes(self, tmp_path: Path) -> None:
        """Should detect breaking changes with impact analyzer."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock impact analyzer
        mock_analyzer = MagicMock()
        mock_impact = MagicMock()
        mock_impact.breaking_changes = [
            MagicMock(change_type="api_change", location="api.py", description="Function signature changed")
        ]
        mock_analyzer.analyze_impact = AsyncMock(return_value=mock_impact)

        reviewer = CodeReviewer(tmp_path, impact_analyzer=mock_analyzer)
        breaking = await reviewer.check_breaking_changes(
            ["api.py"],
            "Update API endpoint"
        )

        assert len(breaking) == 1
        assert "api_change" in breaking[0]


class TestCodeReviewerFullReview:
    """Full review tests."""

    @pytest.mark.asyncio
    async def test_full_review_passes_clean_code(self, tmp_path: Path) -> None:
        """Should pass review for clean code."""
        # Create clean code file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text('''
import logging

logger = logging.getLogger(__name__)

def process_data(data: dict) -> dict:
    """Process input data."""
    try:
        result = {"processed": True, "data": data}
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
''', encoding="utf-8")

        reviewer = CodeReviewer(tmp_path)
        result = await reviewer.review(
            changed_files=["src/main.py"],
            task_description="Add data processing",
        )

        # Should pass (no critical/high issues)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_full_review_fails_bad_code(self, tmp_path: Path) -> None:
        """Should fail review for bad code."""
        # Create bad code file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "bad.py").write_text('''
api_key = "super_secret_key_123"
password = "admin"

def dangerous():
    user_input = input()
    eval(user_input)  # Very dangerous!

def handle_error():
    try:
        risky_operation()
    except:
        pass  # Silent failure
''', encoding="utf-8")

        reviewer = CodeReviewer(tmp_path)
        result = await reviewer.review(
            changed_files=["src/bad.py"],
        )

        # Should fail due to security issues
        assert result.passed is False
        critical_issues = [i for i in result.issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical_issues) >= 1


class TestTestRunner:
    """Tests for TestRunner class."""

    def test_detect_pytest(self, tmp_path: Path) -> None:
        """Should detect pytest framework."""
        (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        runner = TestRunner(tmp_path)
        assert runner._detect_test_framework() == "pytest"

    def test_detect_jest(self, tmp_path: Path) -> None:
        """Should detect jest framework."""
        (tmp_path / "package.json").write_text('{"devDependencies": {"jest": "^29.0.0"}}', encoding="utf-8")
        runner = TestRunner(tmp_path)
        assert runner._detect_test_framework() == "jest"

    def test_detect_no_framework(self, tmp_path: Path) -> None:
        """Should return None when no framework detected."""
        runner = TestRunner(tmp_path)
        assert runner._detect_test_framework() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
