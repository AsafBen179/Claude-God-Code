"""
QA Criteria and Status Tracking.

Part of Claude God Code - Autonomous Excellence

This module handles acceptance criteria validation and QA status tracking.
It provides utilities for loading/saving QA state and determining
when QA validation should run.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class QAStatus(Enum):
    """QA validation status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FIXES_APPLIED = "fixes_applied"
    ERROR = "error"


class IssueSeverity(Enum):
    """Severity levels for QA issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QAIssue:
    """Represents an issue found during QA review."""

    title: str
    severity: IssueSeverity
    description: str
    location: Optional[str] = None
    fix_required: Optional[str] = None
    category: str = "general"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "fix_required": self.fix_required,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QAIssue":
        """Create from dictionary."""
        severity_str = data.get("severity", "medium")
        try:
            severity = IssueSeverity(severity_str)
        except ValueError:
            severity = IssueSeverity.MEDIUM

        return cls(
            title=data.get("title", "Unknown issue"),
            severity=severity,
            description=data.get("description", ""),
            location=data.get("location"),
            fix_required=data.get("fix_required"),
            category=data.get("category", "general"),
        )


@dataclass
class TestResults:
    """Test execution results."""

    unit_passed: int = 0
    unit_total: int = 0
    integration_passed: int = 0
    integration_total: int = 0
    e2e_passed: int = 0
    e2e_total: int = 0

    def all_passed(self) -> bool:
        """Check if all tests passed."""
        unit_ok = self.unit_passed == self.unit_total
        integration_ok = self.integration_passed == self.integration_total
        e2e_ok = self.e2e_passed == self.e2e_total
        return unit_ok and integration_ok and e2e_ok

    def summary(self) -> str:
        """Get summary string."""
        return (
            f"Unit: {self.unit_passed}/{self.unit_total}, "
            f"Integration: {self.integration_passed}/{self.integration_total}, "
            f"E2E: {self.e2e_passed}/{self.e2e_total}"
        )

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "unit": f"{self.unit_passed}/{self.unit_total}",
            "integration": f"{self.integration_passed}/{self.integration_total}",
            "e2e": f"{self.e2e_passed}/{self.e2e_total}",
        }


@dataclass
class QASignoff:
    """QA signoff status."""

    status: QAStatus
    timestamp: datetime = field(default_factory=datetime.now)
    qa_session: int = 1
    issues_found: list[QAIssue] = field(default_factory=list)
    test_results: Optional[TestResults] = None
    verified_by: str = "qa_agent"
    ready_for_revalidation: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "qa_session": self.qa_session,
            "verified_by": self.verified_by,
        }

        if self.issues_found:
            result["issues_found"] = [i.to_dict() for i in self.issues_found]

        if self.test_results:
            result["tests_passed"] = self.test_results.to_dict()

        if self.ready_for_revalidation:
            result["ready_for_qa_revalidation"] = True

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QASignoff":
        """Create from dictionary."""
        status_str = data.get("status", "pending")
        try:
            status = QAStatus(status_str)
        except ValueError:
            status = QAStatus.PENDING

        # Parse timestamp
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Parse issues
        issues = []
        for issue_data in data.get("issues_found", []):
            issues.append(QAIssue.from_dict(issue_data))

        # Parse test results
        test_results = None
        tests_data = data.get("tests_passed", {})
        if tests_data:
            test_results = TestResults()
            # Parse format like "5/5"
            for key, value in [("unit", "unit"), ("integration", "integration"), ("e2e", "e2e")]:
                if key in tests_data and "/" in str(tests_data[key]):
                    parts = str(tests_data[key]).split("/")
                    passed = int(parts[0])
                    total = int(parts[1])
                    setattr(test_results, f"{value}_passed", passed)
                    setattr(test_results, f"{value}_total", total)

        return cls(
            status=status,
            timestamp=timestamp,
            qa_session=data.get("qa_session", 1),
            issues_found=issues,
            test_results=test_results,
            verified_by=data.get("verified_by", "qa_agent"),
            ready_for_revalidation=data.get("ready_for_qa_revalidation", False),
        )


def load_implementation_plan(spec_dir: Path) -> Optional[dict[str, Any]]:
    """Load the implementation plan JSON."""
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return None
    try:
        with open(plan_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to load implementation plan: {e}")
        return None


def save_implementation_plan(spec_dir: Path, plan: dict[str, Any]) -> bool:
    """Save the implementation plan JSON."""
    plan_file = spec_dir / "implementation_plan.json"
    try:
        spec_dir.mkdir(parents=True, exist_ok=True)
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        return True
    except OSError as e:
        logger.error(f"Failed to save implementation plan: {e}")
        return False


def get_qa_signoff_status(spec_dir: Path) -> Optional[QASignoff]:
    """Get the current QA sign-off status from implementation plan."""
    plan = load_implementation_plan(spec_dir)
    if not plan:
        return None

    signoff_data = plan.get("qa_signoff")
    if not signoff_data:
        return None

    return QASignoff.from_dict(signoff_data)


def save_qa_signoff_status(spec_dir: Path, signoff: QASignoff) -> bool:
    """Save QA signoff status to implementation plan."""
    plan = load_implementation_plan(spec_dir) or {}
    plan["qa_signoff"] = signoff.to_dict()
    return save_implementation_plan(spec_dir, plan)


def is_qa_approved(spec_dir: Path) -> bool:
    """Check if QA has approved the build."""
    signoff = get_qa_signoff_status(spec_dir)
    if not signoff:
        return False
    return signoff.status == QAStatus.APPROVED


def is_qa_rejected(spec_dir: Path) -> bool:
    """Check if QA has rejected the build."""
    signoff = get_qa_signoff_status(spec_dir)
    if not signoff:
        return False
    return signoff.status == QAStatus.REJECTED


def is_fixes_applied(spec_dir: Path) -> bool:
    """Check if fixes have been applied and ready for re-validation."""
    signoff = get_qa_signoff_status(spec_dir)
    if not signoff:
        return False
    return signoff.status == QAStatus.FIXES_APPLIED and signoff.ready_for_revalidation


def get_qa_iteration_count(spec_dir: Path) -> int:
    """Get the number of QA iterations so far."""
    signoff = get_qa_signoff_status(spec_dir)
    if not signoff:
        return 0
    return signoff.qa_session


def should_run_qa(spec_dir: Path, check_build_complete: bool = True) -> bool:
    """
    Determine if QA validation should run.

    QA should run when:
    - All subtasks are completed (if check_build_complete)
    - QA has not yet approved
    """
    if is_qa_approved(spec_dir):
        return False

    return True


def should_run_fixes(spec_dir: Path, max_iterations: int = 50) -> bool:
    """
    Determine if QA fixes should run.

    Fixes should run when:
    - QA has rejected the build
    - Max iterations not reached
    """
    if not is_qa_rejected(spec_dir):
        return False

    iterations = get_qa_iteration_count(spec_dir)
    if iterations >= max_iterations:
        return False

    return True


def get_critical_issues(signoff: QASignoff) -> list[QAIssue]:
    """Get all critical issues from signoff."""
    return [i for i in signoff.issues_found if i.severity == IssueSeverity.CRITICAL]


def has_blocking_issues(signoff: QASignoff) -> bool:
    """Check if there are any blocking (critical/high) issues."""
    blocking = [
        i for i in signoff.issues_found
        if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)
    ]
    return len(blocking) > 0
