"""
Tests for qa.criteria module.

Part of Claude God Code - Autonomous Excellence
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from qa.criteria import (
    IssueSeverity,
    QAIssue,
    QASignoff,
    QAStatus,
    TestResults,
    get_qa_iteration_count,
    get_qa_signoff_status,
    has_blocking_issues,
    is_fixes_applied,
    is_qa_approved,
    is_qa_rejected,
    load_implementation_plan,
    save_implementation_plan,
    save_qa_signoff_status,
    should_run_fixes,
    should_run_qa,
)


class TestQAStatus:
    """Tests for QAStatus enum."""

    def test_status_values(self) -> None:
        """Should have expected status values."""
        assert QAStatus.PENDING.value == "pending"
        assert QAStatus.APPROVED.value == "approved"
        assert QAStatus.REJECTED.value == "rejected"
        assert QAStatus.FIXES_APPLIED.value == "fixes_applied"


class TestIssueSeverity:
    """Tests for IssueSeverity enum."""

    def test_severity_values(self) -> None:
        """Should have expected severity values."""
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"


class TestQAIssue:
    """Tests for QAIssue dataclass."""

    def test_create_issue(self) -> None:
        """Should create issue with correct fields."""
        issue = QAIssue(
            title="Test Issue",
            severity=IssueSeverity.HIGH,
            description="Test description",
            location="src/test.py:10",
        )
        assert issue.title == "Test Issue"
        assert issue.severity == IssueSeverity.HIGH
        assert issue.location == "src/test.py:10"

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        issue = QAIssue(
            title="Test",
            severity=IssueSeverity.MEDIUM,
            description="Description",
        )
        d = issue.to_dict()
        assert d["title"] == "Test"
        assert d["severity"] == "medium"

    def test_from_dict(self) -> None:
        """Should create from dictionary."""
        data = {
            "title": "Test Issue",
            "severity": "high",
            "description": "Description",
            "location": "file.py:5",
        }
        issue = QAIssue.from_dict(data)
        assert issue.title == "Test Issue"
        assert issue.severity == IssueSeverity.HIGH


class TestTestResults:
    """Tests for TestResults dataclass."""

    def test_all_passed_true(self) -> None:
        """Should return True when all tests pass."""
        results = TestResults(
            unit_passed=10, unit_total=10,
            integration_passed=5, integration_total=5,
            e2e_passed=3, e2e_total=3,
        )
        assert results.all_passed() is True

    def test_all_passed_false(self) -> None:
        """Should return False when some tests fail."""
        results = TestResults(
            unit_passed=9, unit_total=10,
            integration_passed=5, integration_total=5,
        )
        assert results.all_passed() is False

    def test_summary(self) -> None:
        """Should generate summary string."""
        results = TestResults(
            unit_passed=10, unit_total=12,
            integration_passed=5, integration_total=5,
        )
        summary = results.summary()
        assert "10/12" in summary
        assert "5/5" in summary


class TestQASignoff:
    """Tests for QASignoff dataclass."""

    def test_create_approved_signoff(self) -> None:
        """Should create approved signoff."""
        signoff = QASignoff(
            status=QAStatus.APPROVED,
            qa_session=3,
        )
        assert signoff.status == QAStatus.APPROVED
        assert signoff.qa_session == 3

    def test_create_rejected_signoff_with_issues(self) -> None:
        """Should create rejected signoff with issues."""
        issues = [
            QAIssue(title="Issue 1", severity=IssueSeverity.HIGH, description="Desc"),
        ]
        signoff = QASignoff(
            status=QAStatus.REJECTED,
            issues_found=issues,
        )
        assert signoff.status == QAStatus.REJECTED
        assert len(signoff.issues_found) == 1

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        signoff = QASignoff(
            status=QAStatus.APPROVED,
            qa_session=2,
        )
        d = signoff.to_dict()
        assert d["status"] == "approved"
        assert d["qa_session"] == 2

    def test_from_dict(self) -> None:
        """Should create from dictionary."""
        data = {
            "status": "rejected",
            "qa_session": 5,
            "timestamp": datetime.now().isoformat(),
            "issues_found": [
                {"title": "Issue", "severity": "high", "description": "Desc"}
            ],
        }
        signoff = QASignoff.from_dict(data)
        assert signoff.status == QAStatus.REJECTED
        assert signoff.qa_session == 5
        assert len(signoff.issues_found) == 1


class TestImplementationPlan:
    """Tests for implementation plan I/O."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Should save and load implementation plan."""
        plan = {"name": "Test Plan", "tasks": []}
        assert save_implementation_plan(tmp_path, plan) is True

        loaded = load_implementation_plan(tmp_path)
        assert loaded is not None
        assert loaded["name"] == "Test Plan"

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Should return None for nonexistent plan."""
        result = load_implementation_plan(tmp_path)
        assert result is None

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Should return None for invalid JSON."""
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text("invalid json{", encoding="utf-8")

        result = load_implementation_plan(tmp_path)
        assert result is None


class TestQASignoffStatus:
    """Tests for QA signoff status functions."""

    def test_get_signoff_status(self, tmp_path: Path) -> None:
        """Should get signoff status from plan."""
        plan = {
            "qa_signoff": {
                "status": "approved",
                "qa_session": 3,
                "timestamp": datetime.now().isoformat(),
            }
        }
        save_implementation_plan(tmp_path, plan)

        signoff = get_qa_signoff_status(tmp_path)
        assert signoff is not None
        assert signoff.status == QAStatus.APPROVED

    def test_save_signoff_status(self, tmp_path: Path) -> None:
        """Should save signoff status to plan."""
        signoff = QASignoff(status=QAStatus.REJECTED, qa_session=2)
        assert save_qa_signoff_status(tmp_path, signoff) is True

        loaded = get_qa_signoff_status(tmp_path)
        assert loaded is not None
        assert loaded.status == QAStatus.REJECTED

    def test_is_qa_approved(self, tmp_path: Path) -> None:
        """Should correctly check if QA approved."""
        signoff = QASignoff(status=QAStatus.APPROVED)
        save_qa_signoff_status(tmp_path, signoff)
        assert is_qa_approved(tmp_path) is True

    def test_is_qa_rejected(self, tmp_path: Path) -> None:
        """Should correctly check if QA rejected."""
        signoff = QASignoff(status=QAStatus.REJECTED)
        save_qa_signoff_status(tmp_path, signoff)
        assert is_qa_rejected(tmp_path) is True

    def test_get_qa_iteration_count(self, tmp_path: Path) -> None:
        """Should return correct iteration count."""
        signoff = QASignoff(status=QAStatus.REJECTED, qa_session=5)
        save_qa_signoff_status(tmp_path, signoff)
        assert get_qa_iteration_count(tmp_path) == 5


class TestQAReadinessChecks:
    """Tests for QA readiness check functions."""

    def test_should_run_qa_not_approved(self, tmp_path: Path) -> None:
        """Should return True if not approved."""
        assert should_run_qa(tmp_path) is True

    def test_should_run_qa_already_approved(self, tmp_path: Path) -> None:
        """Should return False if already approved."""
        signoff = QASignoff(status=QAStatus.APPROVED)
        save_qa_signoff_status(tmp_path, signoff)
        assert should_run_qa(tmp_path) is False

    def test_should_run_fixes_when_rejected(self, tmp_path: Path) -> None:
        """Should return True when rejected and under max iterations."""
        signoff = QASignoff(status=QAStatus.REJECTED, qa_session=5)
        save_qa_signoff_status(tmp_path, signoff)
        assert should_run_fixes(tmp_path, max_iterations=50) is True

    def test_should_not_run_fixes_at_max(self, tmp_path: Path) -> None:
        """Should return False when at max iterations."""
        signoff = QASignoff(status=QAStatus.REJECTED, qa_session=50)
        save_qa_signoff_status(tmp_path, signoff)
        assert should_run_fixes(tmp_path, max_iterations=50) is False


class TestBlockingIssues:
    """Tests for blocking issue detection."""

    def test_has_blocking_issues_critical(self) -> None:
        """Should detect critical issues as blocking."""
        signoff = QASignoff(
            status=QAStatus.REJECTED,
            issues_found=[
                QAIssue(title="Critical", severity=IssueSeverity.CRITICAL, description=""),
            ],
        )
        assert has_blocking_issues(signoff) is True

    def test_has_blocking_issues_high(self) -> None:
        """Should detect high severity issues as blocking."""
        signoff = QASignoff(
            status=QAStatus.REJECTED,
            issues_found=[
                QAIssue(title="High", severity=IssueSeverity.HIGH, description=""),
            ],
        )
        assert has_blocking_issues(signoff) is True

    def test_no_blocking_issues_low(self) -> None:
        """Should not flag low severity issues as blocking."""
        signoff = QASignoff(
            status=QAStatus.REJECTED,
            issues_found=[
                QAIssue(title="Low", severity=IssueSeverity.LOW, description=""),
            ],
        )
        assert has_blocking_issues(signoff) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
