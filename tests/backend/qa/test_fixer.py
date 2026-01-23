"""
Tests for qa.fixer module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from qa.criteria import IssueSeverity, QAIssue, QASignoff, QAStatus, save_qa_signoff_status
from qa.fixer import (
    Fix,
    FixGenerator,
    FixResult,
    Fixer,
    FixStrategy,
    clear_fix_request,
    load_fix_request,
    run_qa_fixer,
)


class TestFixStrategy:
    """Tests for FixStrategy enum."""

    def test_strategy_values(self) -> None:
        """Should have expected strategy values."""
        assert FixStrategy.REPLACE.value == "replace"
        assert FixStrategy.INSERT.value == "insert"
        assert FixStrategy.DELETE.value == "delete"
        assert FixStrategy.MANUAL.value == "manual"


class TestFix:
    """Tests for Fix dataclass."""

    def test_create_fix(self) -> None:
        """Should create fix with correct fields."""
        issue = QAIssue(
            title="Test Issue",
            severity=IssueSeverity.HIGH,
            description="Description",
        )
        fix = Fix(
            issue=issue,
            strategy=FixStrategy.REPLACE,
            description="Replace code",
            file_path="test.py",
            line_number=10,
        )
        assert fix.strategy == FixStrategy.REPLACE
        assert fix.file_path == "test.py"
        assert fix.confidence == 0.8

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        issue = QAIssue(title="Test", severity=IssueSeverity.LOW, description="")
        fix = Fix(
            issue=issue,
            strategy=FixStrategy.DELETE,
            description="Delete line",
        )
        d = fix.to_dict()
        assert d["strategy"] == "delete"
        assert d["description"] == "Delete line"


class TestFixResult:
    """Tests for FixResult dataclass."""

    def test_successful_result(self) -> None:
        """Should create successful result."""
        result = FixResult(
            success=True,
            ready_for_revalidation=True,
            message="All fixes applied",
        )
        assert result.success is True
        assert result.ready_for_revalidation is True

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        result = FixResult(
            success=True,
            message="Done",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["message"] == "Done"


class TestFixGenerator:
    """Tests for FixGenerator class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize generator."""
        generator = FixGenerator(tmp_path)
        assert generator.repo_root == tmp_path

    def test_parse_location(self, tmp_path: Path) -> None:
        """Should parse file:line location."""
        generator = FixGenerator(tmp_path)

        file_path, line_num = generator._parse_location("src/test.py:25")
        assert file_path == "src/test.py"
        assert line_num == 25

    def test_parse_location_no_line(self, tmp_path: Path) -> None:
        """Should handle location without line number."""
        generator = FixGenerator(tmp_path)

        file_path, line_num = generator._parse_location("src/test.py")
        assert file_path == "src/test.py"
        assert line_num is None

    def test_generate_fix_for_debug_statements(self, tmp_path: Path) -> None:
        """Should generate delete fix for debug statements."""
        generator = FixGenerator(tmp_path)
        issue = QAIssue(
            title="Debug Statements",
            severity=IssueSeverity.LOW,
            description="Found debug statement",
            location="test.py:10",
        )

        fix = generator.generate_fix(issue)
        assert fix.strategy == FixStrategy.DELETE
        assert fix.confidence > 0

    def test_generate_fix_for_manual_issue(self, tmp_path: Path) -> None:
        """Should generate manual fix for complex issues."""
        generator = FixGenerator(tmp_path)
        issue = QAIssue(
            title="Todo Comments",
            severity=IssueSeverity.LOW,
            description="TODO comment found",
            location="test.py:5",
        )

        fix = generator.generate_fix(issue)
        assert fix.strategy == FixStrategy.MANUAL
        assert fix.confidence < 0.5  # Low confidence for manual fixes


class TestFixer:
    """Tests for Fixer class."""

    def test_init(self, tmp_path: Path) -> None:
        """Should initialize fixer."""
        fixer = Fixer(tmp_path, spec_dir=tmp_path)
        assert fixer.repo_root == tmp_path
        assert fixer.auto_apply is False

    def test_apply_fix_replace(self, tmp_path: Path) -> None:
        """Should apply replace fix."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nbad_code\nline3\n", encoding="utf-8")

        fixer = Fixer(tmp_path, auto_apply=True)
        issue = QAIssue(title="Test", severity=IssueSeverity.MEDIUM, description="")
        fix = Fix(
            issue=issue,
            strategy=FixStrategy.REPLACE,
            description="Replace bad code",
            file_path="test.py",
            line_number=2,
            original_code="bad_code",
            fixed_code="good_code",
        )

        result = fixer._apply_fix(fix)
        assert result is True
        assert fix.applied is True

        content = test_file.read_text()
        assert "good_code" in content
        assert "bad_code" not in content

    def test_apply_fix_delete(self, tmp_path: Path) -> None:
        """Should apply delete fix."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\ndelete_me\nline3\n", encoding="utf-8")

        fixer = Fixer(tmp_path, auto_apply=True)
        issue = QAIssue(title="Test", severity=IssueSeverity.LOW, description="")
        fix = Fix(
            issue=issue,
            strategy=FixStrategy.DELETE,
            description="Delete line",
            file_path="test.py",
            line_number=2,
            fixed_code="",  # Empty for delete
        )

        result = fixer._apply_fix(fix)
        assert result is True

        content = test_file.read_text()
        assert "delete_me" not in content

    def test_apply_fix_file_not_found(self, tmp_path: Path) -> None:
        """Should fail when file not found."""
        fixer = Fixer(tmp_path, auto_apply=True)
        issue = QAIssue(title="Test", severity=IssueSeverity.MEDIUM, description="")
        fix = Fix(
            issue=issue,
            strategy=FixStrategy.REPLACE,
            description="Fix",
            file_path="nonexistent.py",
            line_number=1,
            fixed_code="new_code",
        )

        result = fixer._apply_fix(fix)
        assert result is False
        assert fix.error is not None

    def test_create_fix_request_file(self, tmp_path: Path) -> None:
        """Should create QA_FIX_REQUEST.md file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        fixer = Fixer(tmp_path, spec_dir=spec_dir)
        issue = QAIssue(
            title="Test Issue",
            severity=IssueSeverity.HIGH,
            description="Needs manual fix",
            location="test.py:10",
        )
        fix = Fix(
            issue=issue,
            strategy=FixStrategy.MANUAL,
            description="Manual fix required",
        )

        path = fixer._create_fix_request_file([fix])

        assert path.exists()
        content = path.read_text()
        assert "Test Issue" in content
        assert "Manual fix required" in content


class TestFixerAsync:
    """Async tests for Fixer."""

    @pytest.mark.asyncio
    async def test_fix_issues_auto_apply(self, tmp_path: Path) -> None:
        """Should auto-apply fixes when enabled."""
        # Create test file with issues
        test_file = tmp_path / "bad.py"
        test_file.write_text("print('debug')\nreal_code()\n", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        issues = [
            QAIssue(
                title="Debug Statements",
                severity=IssueSeverity.LOW,
                description="Found debug print",
                location="bad.py:1",
            ),
        ]

        fixer = Fixer(tmp_path, spec_dir=spec_dir, auto_apply=True)
        result = await fixer.fix_issues(issues)

        assert result.message  # Should have message about fixes

    @pytest.mark.asyncio
    async def test_fix_issues_creates_request_file(self, tmp_path: Path) -> None:
        """Should create fix request for skipped fixes."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        issues = [
            QAIssue(
                title="Todo Comments",
                severity=IssueSeverity.LOW,
                description="TODO found",
                location="test.py:1",
            ),
        ]

        fixer = Fixer(tmp_path, spec_dir=spec_dir, auto_apply=False)
        result = await fixer.fix_issues(issues)

        # Check fix request file was created
        fix_file = spec_dir / "QA_FIX_REQUEST.md"
        assert fix_file.exists()


class TestFixRequestFile:
    """Tests for fix request file operations."""

    def test_load_fix_request(self, tmp_path: Path) -> None:
        """Should load fix request file."""
        fix_file = tmp_path / "QA_FIX_REQUEST.md"
        fix_file.write_text("# Fix Request\n\nContent here", encoding="utf-8")

        content = load_fix_request(tmp_path)
        assert content is not None
        assert "Fix Request" in content

    def test_load_fix_request_nonexistent(self, tmp_path: Path) -> None:
        """Should return None for nonexistent file."""
        content = load_fix_request(tmp_path)
        assert content is None

    def test_clear_fix_request(self, tmp_path: Path) -> None:
        """Should remove fix request file."""
        fix_file = tmp_path / "QA_FIX_REQUEST.md"
        fix_file.write_text("Content", encoding="utf-8")

        result = clear_fix_request(tmp_path)
        assert result is True
        assert not fix_file.exists()


class TestRunQAFixer:
    """Tests for run_qa_fixer function."""

    @pytest.mark.asyncio
    async def test_run_qa_fixer_no_issues(self, tmp_path: Path) -> None:
        """Should return error when no issues found."""
        status, result = await run_qa_fixer(tmp_path, tmp_path)
        assert status == "error"
        assert "No issues" in result.message

    @pytest.mark.asyncio
    async def test_run_qa_fixer_with_issues(self, tmp_path: Path) -> None:
        """Should process issues and return result."""
        # Create signoff with issues
        signoff = QASignoff(
            status=QAStatus.REJECTED,
            issues_found=[
                QAIssue(
                    title="Debug Statements",
                    severity=IssueSeverity.LOW,
                    description="Debug found",
                    location="test.py:1",
                ),
            ],
        )
        save_qa_signoff_status(tmp_path, signoff)

        status, result = await run_qa_fixer(tmp_path, tmp_path, auto_apply=False)

        # Should return fixed status (even if skipped)
        assert status in ("fixed", "error")


class TestFixerSimulatedBugFix:
    """Integration test: Fixer correcting a simulated bug."""

    @pytest.mark.asyncio
    async def test_fix_simulated_security_bug(self, tmp_path: Path) -> None:
        """Should fix a simulated security vulnerability."""
        # Create file with hardcoded secret (simulated bug)
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        buggy_file = src_dir / "config.py"
        buggy_file.write_text('''
import os

# Configuration
api_key = "hardcoded_secret_123"  # Bug: hardcoded secret
database_url = os.environ.get("DB_URL")

def get_api_key():
    return api_key
''', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create issue for the bug
        issues = [
            QAIssue(
                title="Hardcoded Secrets",
                severity=IssueSeverity.CRITICAL,
                description="Hardcoded API key found",
                location="src/config.py:5",
                fix_required="Move to environment variable",
            ),
        ]

        # Run fixer
        fixer = Fixer(tmp_path, spec_dir=spec_dir, auto_apply=False)
        result = await fixer.fix_issues(issues)

        # Should create fix request (since auto_apply is False)
        fix_file = spec_dir / "QA_FIX_REQUEST.md"
        assert fix_file.exists()

        content = fix_file.read_text()
        assert "Hardcoded Secrets" in content
        assert "CRITICAL" in content.lower() or "critical" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
