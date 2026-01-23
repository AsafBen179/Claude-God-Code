"""
QA Layer for Claude God Code.

Part of Claude God Code - Autonomous Excellence

This module provides the quality assurance infrastructure for autonomous
self-healing code validation. It implements the Review -> Test -> Fix
cycle that ensures code quality and spec alignment.

Key Components:
- CodeReviewer: Static analysis and code review with God Mode integration
- Fixer: Self-healing mechanism for automatic fix generation
- QALoop: Master orchestration of the QA cycle
- QAIntegration: Integration with CoderAgent and WorktreeManager

Example usage:
    from qa import run_qa_validation_loop, QALoopConfig

    # Run full QA loop
    approved = await run_qa_validation_loop(
        repo_root=Path("/path/to/repo"),
        spec_dir=Path("/path/to/spec"),
        changed_files=["src/auth.py", "src/utils.py"],
        task_description="Add user authentication",
        impact_analyzer=my_impact_analyzer,
    )

    if approved:
        print("QA passed!")
    else:
        print("QA failed, check QA_FIX_REQUEST.md")
"""

from .criteria import (
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
from .fixer import (
    Fix,
    FixGenerator,
    FixResult,
    Fixer,
    FixStrategy,
    clear_fix_request,
    load_fix_request,
    run_qa_fixer,
)
from .loop import (
    IterationRecord,
    QAIntegration,
    QALoop,
    QALoopConfig,
    QALoopState,
    QAPhase,
    run_qa_validation_loop,
)
from .reviewer import (
    CodeReviewer,
    ReviewCategory,
    ReviewCheck,
    ReviewResult,
    TestRunner,
    run_qa_review,
)

__all__ = [
    # Criteria
    "IssueSeverity",
    "QAIssue",
    "QASignoff",
    "QAStatus",
    "TestResults",
    "get_qa_iteration_count",
    "get_qa_signoff_status",
    "has_blocking_issues",
    "is_fixes_applied",
    "is_qa_approved",
    "is_qa_rejected",
    "load_implementation_plan",
    "save_implementation_plan",
    "save_qa_signoff_status",
    "should_run_fixes",
    "should_run_qa",
    # Fixer
    "Fix",
    "FixGenerator",
    "FixResult",
    "Fixer",
    "FixStrategy",
    "clear_fix_request",
    "load_fix_request",
    "run_qa_fixer",
    # Loop
    "IterationRecord",
    "QAIntegration",
    "QALoop",
    "QALoopConfig",
    "QALoopState",
    "QAPhase",
    "run_qa_validation_loop",
    # Reviewer
    "CodeReviewer",
    "ReviewCategory",
    "ReviewCheck",
    "ReviewResult",
    "TestRunner",
    "run_qa_review",
]
