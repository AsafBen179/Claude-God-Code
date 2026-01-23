"""
QA Reviewer for static analysis and code review.

Part of Claude God Code - Autonomous Excellence

This module implements code review capabilities that check if generated code
aligns with the spec and follows standards. It integrates with the Impact
Analyzer (God Mode) to detect unintended breaking changes.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .criteria import (
    IssueSeverity,
    QAIssue,
    QASignoff,
    QAStatus,
    TestResults,
    save_qa_signoff_status,
)

logger = logging.getLogger(__name__)


class ReviewCategory(Enum):
    """Categories of code review checks."""

    SYNTAX = "syntax"
    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    SPEC_ALIGNMENT = "spec_alignment"
    BREAKING_CHANGE = "breaking_change"
    TEST_COVERAGE = "test_coverage"


@dataclass
class ReviewCheck:
    """A single review check to perform."""

    name: str
    category: ReviewCategory
    description: str
    pattern: Optional[str] = None  # Regex pattern to search
    file_patterns: list[str] = field(default_factory=list)  # File globs to check
    severity: IssueSeverity = IssueSeverity.MEDIUM
    enabled: bool = True

    def matches_file(self, file_path: str) -> bool:
        """Check if this check applies to a file."""
        if not self.file_patterns:
            return True

        from fnmatch import fnmatch
        return any(fnmatch(file_path, p) for p in self.file_patterns)


@dataclass
class ReviewResult:
    """Result of a code review."""

    passed: bool
    issues: list[QAIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_reviewed: int = 0
    checks_performed: int = 0
    duration_seconds: float = 0.0
    breaking_changes_detected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "warnings": self.warnings,
            "files_reviewed": self.files_reviewed,
            "checks_performed": self.checks_performed,
            "duration_seconds": self.duration_seconds,
            "breaking_changes_detected": self.breaking_changes_detected,
        }


# Default review checks
DEFAULT_CHECKS: list[ReviewCheck] = [
    # Security checks
    ReviewCheck(
        name="hardcoded_secrets",
        category=ReviewCategory.SECURITY,
        description="Check for hardcoded secrets or API keys",
        pattern=r"(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]+['\"]",
        severity=IssueSeverity.CRITICAL,
    ),
    ReviewCheck(
        name="sql_injection",
        category=ReviewCategory.SECURITY,
        description="Check for potential SQL injection",
        pattern=r"execute\s*\(\s*['\"].*%.*['\"]",
        file_patterns=["*.py"],
        severity=IssueSeverity.CRITICAL,
    ),
    ReviewCheck(
        name="eval_usage",
        category=ReviewCategory.SECURITY,
        description="Check for dangerous eval() usage",
        pattern=r"\beval\s*\(",
        file_patterns=["*.py", "*.js", "*.ts"],
        severity=IssueSeverity.HIGH,
    ),

    # Style checks
    ReviewCheck(
        name="todo_comments",
        category=ReviewCategory.STYLE,
        description="Check for TODO comments that should be resolved",
        pattern=r"#\s*TODO|//\s*TODO|/\*\s*TODO",
        severity=IssueSeverity.LOW,
    ),
    ReviewCheck(
        name="debug_statements",
        category=ReviewCategory.STYLE,
        description="Check for debug statements left in code",
        pattern=r"\bprint\s*\(|console\.log\s*\(|debugger\b",
        severity=IssueSeverity.LOW,
    ),

    # Correctness checks
    ReviewCheck(
        name="empty_except",
        category=ReviewCategory.CORRECTNESS,
        description="Check for empty except blocks",
        pattern=r"except.*:\s*\n\s*(pass|\.\.\.)\s*$",
        file_patterns=["*.py"],
        severity=IssueSeverity.MEDIUM,
    ),
    ReviewCheck(
        name="unused_imports",
        category=ReviewCategory.STYLE,
        description="Check for potentially unused imports",
        pattern=r"^import\s+\w+\s*$|^from\s+\w+\s+import\s+\*",
        file_patterns=["*.py"],
        severity=IssueSeverity.LOW,
    ),

    # TypeScript/JavaScript checks
    ReviewCheck(
        name="any_type",
        category=ReviewCategory.CORRECTNESS,
        description="Check for excessive 'any' type usage",
        pattern=r":\s*any\b",
        file_patterns=["*.ts", "*.tsx"],
        severity=IssueSeverity.MEDIUM,
    ),
    ReviewCheck(
        name="console_error",
        category=ReviewCategory.CORRECTNESS,
        description="Check for console.error without proper handling",
        pattern=r"console\.error\s*\([^)]*\)\s*;?\s*$",
        file_patterns=["*.js", "*.ts", "*.jsx", "*.tsx"],
        severity=IssueSeverity.LOW,
    ),
]


class CodeReviewer:
    """Performs static analysis and code review."""

    def __init__(
        self,
        repo_root: Path,
        spec_dir: Optional[Path] = None,
        checks: Optional[list[ReviewCheck]] = None,
        impact_analyzer: Optional[Any] = None,  # ImpactAnalyzer from spec layer
    ) -> None:
        """Initialize code reviewer."""
        self.repo_root = repo_root
        self.spec_dir = spec_dir
        self.checks = checks or DEFAULT_CHECKS
        self.impact_analyzer = impact_analyzer

        # Files to always ignore
        self._ignore_patterns = [
            "node_modules",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".claude-god",
            "*.min.js",
            "*.min.css",
        ]

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)
        from fnmatch import fnmatch

        for pattern in self._ignore_patterns:
            if pattern in path_str or fnmatch(path.name, pattern):
                return True
        return False

    def _get_files_to_review(
        self,
        file_extensions: Optional[list[str]] = None,
        changed_files: Optional[list[str]] = None,
    ) -> list[Path]:
        """Get list of files to review."""
        if changed_files:
            return [self.repo_root / f for f in changed_files if not self._should_ignore(Path(f))]

        extensions = file_extensions or [".py", ".ts", ".tsx", ".js", ".jsx", ".go"]
        files = []

        for ext in extensions:
            for file_path in self.repo_root.rglob(f"*{ext}"):
                if not self._should_ignore(file_path):
                    files.append(file_path)

        return files

    def _run_check(self, check: ReviewCheck, content: str, file_path: str) -> list[QAIssue]:
        """Run a single check on file content."""
        issues = []

        if not check.enabled:
            return issues

        if not check.matches_file(file_path):
            return issues

        if check.pattern:
            matches = list(re.finditer(check.pattern, content, re.MULTILINE | re.IGNORECASE))
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count("\n") + 1
                issues.append(QAIssue(
                    title=check.name.replace("_", " ").title(),
                    severity=check.severity,
                    description=check.description,
                    location=f"{file_path}:{line_num}",
                    fix_required=f"Review and fix: {match.group()[:50]}...",
                    category=check.category.value,
                ))

        return issues

    async def review_file(self, file_path: Path) -> list[QAIssue]:
        """Review a single file."""
        issues = []

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return issues

        relative_path = str(file_path.relative_to(self.repo_root))

        for check in self.checks:
            file_issues = self._run_check(check, content, relative_path)
            issues.extend(file_issues)

        return issues

    async def check_spec_alignment(
        self,
        spec_content: str,
        changed_files: list[str],
    ) -> list[QAIssue]:
        """Check if changes align with the spec requirements."""
        issues = []

        # Extract requirements from spec (simple keyword extraction)
        spec_lower = spec_content.lower()

        # Check for mentioned files that weren't modified
        file_mentions = re.findall(r"[a-zA-Z_/]+\.[a-zA-Z]+", spec_content)
        for mentioned_file in file_mentions:
            if mentioned_file not in str(changed_files):
                # Check if it's a real file reference (not extension like .json)
                if "/" in mentioned_file or mentioned_file.count(".") == 1:
                    issues.append(QAIssue(
                        title="Potentially Missing File Modification",
                        severity=IssueSeverity.INFO,
                        description=f"File '{mentioned_file}' is mentioned in spec but not in changed files",
                        category="spec_alignment",
                    ))

        return issues

    async def check_breaking_changes(
        self,
        changed_files: list[str],
        task_description: str,
    ) -> list[str]:
        """Use Impact Analyzer (God Mode) to detect breaking changes."""
        breaking_changes = []

        if not self.impact_analyzer:
            return breaking_changes

        try:
            impact = await self.impact_analyzer.analyze_impact(
                task_description,
                changed_files,
            )

            for bc in impact.breaking_changes:
                breaking_changes.append(
                    f"{bc.change_type} at {bc.location}: {bc.description}"
                )

        except Exception as e:
            logger.warning(f"Impact analysis failed: {e}")

        return breaking_changes

    async def review(
        self,
        changed_files: Optional[list[str]] = None,
        spec_content: Optional[str] = None,
        task_description: str = "",
        run_tests: bool = True,
    ) -> ReviewResult:
        """Perform full code review."""
        start_time = datetime.now()
        result = ReviewResult(passed=True)

        # Get files to review
        files = self._get_files_to_review(changed_files=changed_files)
        result.files_reviewed = len(files)

        # Review each file
        for file_path in files:
            file_issues = await self.review_file(file_path)
            result.issues.extend(file_issues)
            result.checks_performed += len(self.checks)

        # Check spec alignment if spec provided
        if spec_content and changed_files:
            alignment_issues = await self.check_spec_alignment(spec_content, changed_files)
            result.issues.extend(alignment_issues)

        # God Mode: Check for breaking changes
        if changed_files and task_description:
            breaking_changes = await self.check_breaking_changes(changed_files, task_description)
            result.breaking_changes_detected = breaking_changes

            for bc in breaking_changes:
                result.issues.append(QAIssue(
                    title="Breaking Change Detected",
                    severity=IssueSeverity.HIGH,
                    description=bc,
                    category="breaking_change",
                ))

        # Determine if review passed
        critical_issues = [i for i in result.issues if i.severity == IssueSeverity.CRITICAL]
        high_issues = [i for i in result.issues if i.severity == IssueSeverity.HIGH]

        if critical_issues:
            result.passed = False
        elif len(high_issues) >= 3:  # Too many high severity issues
            result.passed = False

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result


class TestRunner:
    """Runs tests and collects results."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize test runner."""
        self.repo_root = repo_root

    def _detect_test_framework(self) -> Optional[str]:
        """Detect which test framework is used."""
        # Check for pytest
        if (self.repo_root / "pytest.ini").exists():
            return "pytest"
        if (self.repo_root / "pyproject.toml").exists():
            content = (self.repo_root / "pyproject.toml").read_text()
            if "pytest" in content:
                return "pytest"

        # Check for Jest
        package_json = self.repo_root / "package.json"
        if package_json.exists():
            content = package_json.read_text()
            if "jest" in content:
                return "jest"
            if "vitest" in content:
                return "vitest"
            if "mocha" in content:
                return "mocha"

        # Check for Go tests
        if list(self.repo_root.glob("**/*_test.go")):
            return "go"

        return None

    async def run_tests(self, test_type: str = "all") -> TestResults:
        """Run tests and return results."""
        import subprocess

        results = TestResults()
        framework = self._detect_test_framework()

        if not framework:
            logger.warning("No test framework detected")
            return results

        try:
            if framework == "pytest":
                cmd = ["python", "-m", "pytest", "--tb=short", "-q"]
                result = subprocess.run(
                    cmd,
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                # Parse pytest output
                output = result.stdout + result.stderr
                passed_match = re.search(r"(\d+) passed", output)
                failed_match = re.search(r"(\d+) failed", output)

                passed = int(passed_match.group(1)) if passed_match else 0
                failed = int(failed_match.group(1)) if failed_match else 0

                results.unit_passed = passed
                results.unit_total = passed + failed

            elif framework in ("jest", "vitest"):
                cmd = ["npm", "test", "--", "--passWithNoTests"]
                result = subprocess.run(
                    cmd,
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                # Parse jest output
                output = result.stdout + result.stderr
                tests_match = re.search(r"Tests:\s+(\d+)\s+passed.*?(\d+)\s+total", output)
                if tests_match:
                    results.unit_passed = int(tests_match.group(1))
                    results.unit_total = int(tests_match.group(2))

            elif framework == "go":
                cmd = ["go", "test", "./...", "-v"]
                result = subprocess.run(
                    cmd,
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                # Parse go test output
                output = result.stdout
                passed = output.count("--- PASS:")
                failed = output.count("--- FAIL:")
                results.unit_passed = passed
                results.unit_total = passed + failed

        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
        except Exception as e:
            logger.error(f"Test execution failed: {e}")

        return results


async def run_qa_review(
    repo_root: Path,
    spec_dir: Path,
    changed_files: Optional[list[str]] = None,
    spec_content: Optional[str] = None,
    task_description: str = "",
    impact_analyzer: Optional[Any] = None,
    qa_session: int = 1,
) -> tuple[str, ReviewResult]:
    """
    Run a complete QA review session.

    Returns:
        (status, result) where status is "approved", "rejected", or "error"
    """
    reviewer = CodeReviewer(
        repo_root=repo_root,
        spec_dir=spec_dir,
        impact_analyzer=impact_analyzer,
    )

    try:
        # Run code review
        result = await reviewer.review(
            changed_files=changed_files,
            spec_content=spec_content,
            task_description=task_description,
        )

        # Run tests
        test_runner = TestRunner(repo_root)
        test_results = await test_runner.run_tests()

        # Create signoff based on results
        if result.passed and test_results.all_passed():
            signoff = QASignoff(
                status=QAStatus.APPROVED,
                qa_session=qa_session,
                test_results=test_results,
            )
            status = "approved"
        else:
            signoff = QASignoff(
                status=QAStatus.REJECTED,
                qa_session=qa_session,
                issues_found=result.issues,
                test_results=test_results,
            )
            status = "rejected"

        # Save signoff status
        save_qa_signoff_status(spec_dir, signoff)

        return status, result

    except Exception as e:
        logger.exception(f"QA review failed: {e}")
        return "error", ReviewResult(passed=False, warnings=[str(e)])
