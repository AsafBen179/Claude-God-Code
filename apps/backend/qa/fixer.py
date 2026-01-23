"""
QA Fixer for self-healing code corrections.

Part of Claude God Code - Autonomous Excellence

This module implements the self-healing mechanism that automatically
suggests and applies fixes when QA reviews or tests fail. It analyzes
issues and generates targeted corrections.
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
    get_qa_signoff_status,
    save_qa_signoff_status,
)

logger = logging.getLogger(__name__)


class FixStrategy(Enum):
    """Strategies for fixing issues."""

    REPLACE = "replace"  # Replace text
    INSERT = "insert"  # Insert new code
    DELETE = "delete"  # Delete code
    REFACTOR = "refactor"  # Larger refactoring needed
    MANUAL = "manual"  # Requires manual intervention


@dataclass
class Fix:
    """Represents a suggested fix for an issue."""

    issue: QAIssue
    strategy: FixStrategy
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    original_code: Optional[str] = None
    fixed_code: Optional[str] = None
    confidence: float = 0.8  # 0-1 confidence in the fix
    applied: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issue": self.issue.to_dict(),
            "strategy": self.strategy.value,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "original_code": self.original_code,
            "fixed_code": self.fixed_code,
            "confidence": self.confidence,
            "applied": self.applied,
            "error": self.error,
        }


@dataclass
class FixResult:
    """Result of applying fixes."""

    success: bool
    fixes_applied: list[Fix] = field(default_factory=list)
    fixes_failed: list[Fix] = field(default_factory=list)
    fixes_skipped: list[Fix] = field(default_factory=list)
    ready_for_revalidation: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "fixes_applied": [f.to_dict() for f in self.fixes_applied],
            "fixes_failed": [f.to_dict() for f in self.fixes_failed],
            "fixes_skipped": [f.to_dict() for f in self.fixes_skipped],
            "ready_for_revalidation": self.ready_for_revalidation,
            "message": self.message,
        }


class FixGenerator:
    """Generates fixes for QA issues."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize fix generator."""
        self.repo_root = repo_root

        # Fix patterns: issue pattern -> fix template
        self._fix_patterns: dict[str, dict[str, Any]] = {
            "hardcoded_secrets": {
                "strategy": FixStrategy.REPLACE,
                "description": "Move secret to environment variable",
                "fix_template": 'os.environ.get("{var_name}", "")',
            },
            "debug_statements": {
                "strategy": FixStrategy.DELETE,
                "description": "Remove debug statement",
            },
            "empty_except": {
                "strategy": FixStrategy.REPLACE,
                "description": "Add proper exception handling",
                "fix_template": "except {exception} as e:\n    logger.error(f'Error: {e}')",
            },
            "eval_usage": {
                "strategy": FixStrategy.REFACTOR,
                "description": "Replace eval with safer alternative",
            },
            "todo_comments": {
                "strategy": FixStrategy.MANUAL,
                "description": "Review and resolve TODO comment",
            },
            "any_type": {
                "strategy": FixStrategy.REFACTOR,
                "description": "Replace 'any' with proper type",
            },
        }

    def _parse_location(self, location: str) -> tuple[Optional[str], Optional[int]]:
        """Parse file:line location string."""
        if not location:
            return None, None

        parts = location.rsplit(":", 1)
        file_path = parts[0]
        line_num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

        return file_path, line_num

    def _read_file_line(self, file_path: str, line_number: int) -> Optional[str]:
        """Read a specific line from a file."""
        try:
            full_path = self.repo_root / file_path
            lines = full_path.read_text(encoding="utf-8").splitlines()
            if 0 < line_number <= len(lines):
                return lines[line_number - 1]
        except Exception as e:
            logger.warning(f"Could not read line from {file_path}: {e}")
        return None

    def generate_fix(self, issue: QAIssue) -> Fix:
        """Generate a fix for an issue."""
        # Get fix pattern based on issue category/title
        issue_key = issue.title.lower().replace(" ", "_")
        pattern = self._fix_patterns.get(issue_key, {})

        strategy = pattern.get("strategy", FixStrategy.MANUAL)
        description = pattern.get("description", f"Fix {issue.title}")

        # Parse location
        file_path, line_number = self._parse_location(issue.location or "")

        # Get original code if we have location
        original_code = None
        if file_path and line_number:
            original_code = self._read_file_line(file_path, line_number)

        # Generate fixed code if we have a template
        fixed_code = None
        fix_template = pattern.get("fix_template")
        if fix_template and original_code:
            fixed_code = self._apply_fix_template(fix_template, original_code, issue)

        # Determine confidence based on issue severity and strategy
        confidence = self._calculate_confidence(issue, strategy)

        return Fix(
            issue=issue,
            strategy=strategy,
            description=description,
            file_path=file_path,
            line_number=line_number,
            original_code=original_code,
            fixed_code=fixed_code,
            confidence=confidence,
        )

    def _apply_fix_template(
        self,
        template: str,
        original_code: str,
        issue: QAIssue,
    ) -> str:
        """Apply fix template to generate fixed code."""
        # Simple template substitution
        result = template

        # Try to extract variable name from original code
        var_match = re.search(r"(\w+)\s*=", original_code)
        if var_match:
            result = result.replace("{var_name}", var_match.group(1).upper())

        # Extract exception type if present
        exc_match = re.search(r"except\s+(\w+)", original_code)
        if exc_match:
            result = result.replace("{exception}", exc_match.group(1))
        else:
            result = result.replace("{exception}", "Exception")

        return result

    def _calculate_confidence(self, issue: QAIssue, strategy: FixStrategy) -> float:
        """Calculate confidence score for a fix."""
        base_confidence = 0.8

        # Lower confidence for manual fixes
        if strategy == FixStrategy.MANUAL:
            base_confidence = 0.3
        elif strategy == FixStrategy.REFACTOR:
            base_confidence = 0.5

        # Lower confidence for critical issues
        if issue.severity == IssueSeverity.CRITICAL:
            base_confidence *= 0.7
        elif issue.severity == IssueSeverity.HIGH:
            base_confidence *= 0.8

        return round(base_confidence, 2)


class Fixer:
    """Applies fixes to resolve QA issues."""

    def __init__(
        self,
        repo_root: Path,
        spec_dir: Optional[Path] = None,
        auto_apply: bool = False,
        min_confidence: float = 0.7,
    ) -> None:
        """Initialize fixer."""
        self.repo_root = repo_root
        self.spec_dir = spec_dir
        self.auto_apply = auto_apply
        self.min_confidence = min_confidence
        self.generator = FixGenerator(repo_root)

    def _apply_fix(self, fix: Fix) -> bool:
        """Apply a single fix to the codebase."""
        if not fix.file_path:
            return False

        # DELETE doesn't need fixed_code, other strategies do
        if fix.strategy != FixStrategy.DELETE and not fix.fixed_code:
            return False

        if fix.strategy == FixStrategy.MANUAL:
            return False

        try:
            full_path = self.repo_root / fix.file_path
            if not full_path.exists():
                fix.error = f"File not found: {fix.file_path}"
                return False

            content = full_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if fix.strategy == FixStrategy.REPLACE and fix.line_number:
                if 0 < fix.line_number <= len(lines):
                    # Get indentation from original line
                    original = lines[fix.line_number - 1]
                    indent = len(original) - len(original.lstrip())
                    indented_fix = " " * indent + fix.fixed_code.lstrip()
                    lines[fix.line_number - 1] = indented_fix

            elif fix.strategy == FixStrategy.DELETE and fix.line_number:
                if 0 < fix.line_number <= len(lines):
                    lines.pop(fix.line_number - 1)

            elif fix.strategy == FixStrategy.INSERT and fix.line_number:
                if 0 <= fix.line_number <= len(lines):
                    lines.insert(fix.line_number, fix.fixed_code)

            # Write back
            new_content = "\n".join(lines)
            if not new_content.endswith("\n"):
                new_content += "\n"
            full_path.write_text(new_content, encoding="utf-8")

            fix.applied = True
            return True

        except Exception as e:
            fix.error = str(e)
            logger.error(f"Failed to apply fix: {e}")
            return False

    def _create_fix_request_file(self, fixes: list[Fix]) -> Path:
        """Create QA_FIX_REQUEST.md file for manual fixes."""
        if not self.spec_dir:
            raise ValueError("spec_dir required to create fix request file")

        content = ["# QA Fix Request", ""]
        content.append("The following issues require attention:")
        content.append("")

        for i, fix in enumerate(fixes, 1):
            content.append(f"## Issue {i}: {fix.issue.title}")
            content.append(f"- **Severity**: {fix.issue.severity.value}")
            content.append(f"- **Location**: {fix.issue.location or 'N/A'}")
            content.append(f"- **Description**: {fix.issue.description}")
            content.append(f"- **Fix Strategy**: {fix.strategy.value}")
            content.append(f"- **Suggested Fix**: {fix.description}")
            if fix.original_code:
                content.append(f"- **Original Code**: `{fix.original_code}`")
            if fix.fixed_code:
                content.append(f"- **Fixed Code**: `{fix.fixed_code}`")
            if fix.error:
                content.append(f"- **Error**: {fix.error}")
            content.append("")

        content.append("---")
        content.append("After fixing these issues, the QA loop will re-run automatically.")

        fix_file = self.spec_dir / "QA_FIX_REQUEST.md"
        fix_file.write_text("\n".join(content), encoding="utf-8")

        return fix_file

    async def fix_issues(self, issues: list[QAIssue]) -> FixResult:
        """Generate and apply fixes for issues."""
        result = FixResult(success=True)

        # Generate fixes for all issues
        fixes = [self.generator.generate_fix(issue) for issue in issues]

        for fix in fixes:
            # Skip low-confidence fixes if not auto-applying
            if fix.confidence < self.min_confidence:
                fix.error = f"Confidence too low ({fix.confidence} < {self.min_confidence})"
                result.fixes_skipped.append(fix)
                continue

            # Skip manual fixes
            if fix.strategy == FixStrategy.MANUAL:
                result.fixes_skipped.append(fix)
                continue

            # Apply fix if auto_apply is enabled
            if self.auto_apply and fix.fixed_code:
                if self._apply_fix(fix):
                    result.fixes_applied.append(fix)
                else:
                    result.fixes_failed.append(fix)
            else:
                result.fixes_skipped.append(fix)

        # Create fix request file for non-applied fixes
        non_applied = result.fixes_failed + result.fixes_skipped
        if non_applied and self.spec_dir:
            self._create_fix_request_file(non_applied)

        # Determine success
        critical_failed = [
            f for f in result.fixes_failed
            if f.issue.severity == IssueSeverity.CRITICAL
        ]

        if critical_failed:
            result.success = False
            result.message = f"Failed to fix {len(critical_failed)} critical issues"
        else:
            result.ready_for_revalidation = True
            result.message = (
                f"Applied {len(result.fixes_applied)} fixes, "
                f"{len(result.fixes_skipped)} skipped, "
                f"{len(result.fixes_failed)} failed"
            )

        return result


async def run_qa_fixer(
    repo_root: Path,
    spec_dir: Path,
    fix_session: int = 1,
    auto_apply: bool = False,
) -> tuple[str, FixResult]:
    """
    Run QA fixer session.

    Returns:
        (status, result) where status is "fixed" or "error"
    """
    # Get current QA status with issues
    signoff = get_qa_signoff_status(spec_dir)
    if not signoff or not signoff.issues_found:
        return "error", FixResult(
            success=False,
            message="No issues found to fix"
        )

    fixer = Fixer(
        repo_root=repo_root,
        spec_dir=spec_dir,
        auto_apply=auto_apply,
    )

    try:
        result = await fixer.fix_issues(signoff.issues_found)

        # Update QA status
        if result.ready_for_revalidation:
            new_signoff = QASignoff(
                status=QAStatus.FIXES_APPLIED,
                qa_session=signoff.qa_session,
                ready_for_revalidation=True,
            )
            save_qa_signoff_status(spec_dir, new_signoff)
            return "fixed", result
        else:
            return "error", result

    except Exception as e:
        logger.exception(f"QA fixer failed: {e}")
        return "error", FixResult(
            success=False,
            message=str(e)
        )


def load_fix_request(spec_dir: Path) -> Optional[str]:
    """Load the QA_FIX_REQUEST.md file content."""
    fix_file = spec_dir / "QA_FIX_REQUEST.md"
    if not fix_file.exists():
        return None
    try:
        return fix_file.read_text(encoding="utf-8")
    except OSError:
        return None


def clear_fix_request(spec_dir: Path) -> bool:
    """Remove the QA_FIX_REQUEST.md file after fixes are applied."""
    fix_file = spec_dir / "QA_FIX_REQUEST.md"
    try:
        if fix_file.exists():
            fix_file.unlink()
        return True
    except OSError:
        return False
