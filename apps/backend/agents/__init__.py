"""
Agent Layer for Claude God Code.

Part of Claude God Code - Autonomous Excellence

This module provides the agent infrastructure for autonomous code generation,
planning, and session management. It integrates with the Core layer for
worktree isolation and the Spec layer for impact analysis.

Key Components:
- BaseAgent: Foundation class for all agents
- CoderAgent: Autonomous code generation with WorktreeManager integration
- PlannerAgent: Task decomposition with God Mode Impact Analysis
- SessionOrchestrator: Session lifecycle management

Example usage:
    from agents import CoderAgent, PlannerAgent, AgentContext, AgentConfig

    # Create context
    context = AgentContext(
        repo_root=Path("/path/to/repo"),
        task_description="Implement user authentication",
        config=AgentConfig(auto_continue=True),
    )

    # Run planner
    planner = PlannerAgent(context)
    await planner.run()
    plan = planner.get_plan()

    # Run coder with plan
    coder = CoderAgent(context, plan)
    state = await coder.run()
"""

from .base import (
    AgentCallback,
    AgentConfig,
    AgentContext,
    AgentError,
    AgentMetrics,
    AgentPhase,
    AgentState,
    AgentStatus,
    BaseAgent,
    ErrorSeverity,
)
from .coder import (
    CodeGenerationResult,
    CoderAgent,
    DiffChunker,
    FileChange,
    WorktreeIntegration,
    count_affected_files,
    run_autonomous_agent,
    validate_diff_size,
)
from .planner import (
    ExecutionPlan,
    PlannedTask,
    PlannerAgent,
    TaskPriority,
    TaskType,
    run_followup_planner,
)
from .session import (
    ConversationMessage,
    SessionData,
    SessionOrchestrator,
    SessionStore,
    post_session_processing,
    run_agent_session,
)

__all__ = [
    # Base
    "AgentCallback",
    "AgentConfig",
    "AgentContext",
    "AgentError",
    "AgentMetrics",
    "AgentPhase",
    "AgentState",
    "AgentStatus",
    "BaseAgent",
    "ErrorSeverity",
    # Coder
    "CodeGenerationResult",
    "CoderAgent",
    "DiffChunker",
    "FileChange",
    "WorktreeIntegration",
    "count_affected_files",
    "run_autonomous_agent",
    "validate_diff_size",
    # Planner
    "ExecutionPlan",
    "PlannedTask",
    "PlannerAgent",
    "TaskPriority",
    "TaskType",
    "run_followup_planner",
    # Session
    "ConversationMessage",
    "SessionData",
    "SessionOrchestrator",
    "SessionStore",
    "post_session_processing",
    "run_agent_session",
]
