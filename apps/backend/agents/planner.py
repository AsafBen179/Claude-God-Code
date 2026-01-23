"""
Planner agent for task decomposition and planning.

Part of Claude God Code - Autonomous Excellence

This module implements the God Mode planning capabilities, transforming
specifications into executable tasks while integrating Impact Analysis
to prioritize safety during code changes.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .base import (
    AgentConfig,
    AgentContext,
    AgentPhase,
    AgentState,
    AgentStatus,
    BaseAgent,
    ErrorSeverity,
)

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Priority levels for planned tasks."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(Enum):
    """Types of tasks in a plan."""

    ANALYSIS = "analysis"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENTATION = "documentation"
    MIGRATION = "migration"
    REVIEW = "review"


@dataclass
class PlannedTask:
    """A single task in the execution plan."""

    id: str
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority

    # Execution details
    estimated_complexity: str = "medium"  # simple, medium, complex
    files_to_modify: list[str] = field(default_factory=list)
    files_to_create: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    # Safety information from Impact Analysis
    impact_severity: Optional[str] = None
    breaking_changes: list[str] = field(default_factory=list)
    rollback_notes: Optional[str] = None

    # Status tracking
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "estimated_complexity": self.estimated_complexity,
            "files_to_modify": self.files_to_modify,
            "files_to_create": self.files_to_create,
            "dependencies": self.dependencies,
            "impact_severity": self.impact_severity,
            "breaking_changes": self.breaking_changes,
            "rollback_notes": self.rollback_notes,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan for a specification."""

    spec_id: str
    task_description: str
    created_at: datetime = field(default_factory=datetime.now)

    # Tasks
    tasks: list[PlannedTask] = field(default_factory=list)

    # Impact Analysis results (God Mode)
    overall_impact_severity: Optional[str] = None
    impact_summary: Optional[str] = None
    requires_migration: bool = False
    migration_plan: Optional[str] = None

    # Execution order
    execution_phases: list[list[str]] = field(default_factory=list)

    # Metadata
    estimated_total_complexity: str = "medium"
    risk_factors: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    def get_tasks_by_phase(self) -> list[list[PlannedTask]]:
        """Get tasks organized by execution phase."""
        task_map = {t.id: t for t in self.tasks}
        phases = []

        for phase_ids in self.execution_phases:
            phase_tasks = [task_map[tid] for tid in phase_ids if tid in task_map]
            if phase_tasks:
                phases.append(phase_tasks)

        return phases

    def get_pending_tasks(self) -> list[PlannedTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks if t.status == "pending"]

    def get_next_task(self) -> Optional[PlannedTask]:
        """Get next task to execute based on dependencies."""
        completed_ids = {t.id for t in self.tasks if t.status == "completed"}

        for task in self.tasks:
            if task.status != "pending":
                continue

            # Check if all dependencies are satisfied
            deps_satisfied = all(d in completed_ids for d in task.dependencies)
            if deps_satisfied:
                return task

        return None

    def mark_task_started(self, task_id: str) -> None:
        """Mark a task as started."""
        for task in self.tasks:
            if task.id == task_id:
                task.status = "in_progress"
                task.started_at = datetime.now()
                break

    def mark_task_completed(self, task_id: str, result: str = "") -> None:
        """Mark a task as completed."""
        for task in self.tasks:
            if task.id == task_id:
                task.status = "completed"
                task.completed_at = datetime.now()
                task.result = result
                break

    def mark_task_failed(self, task_id: str, reason: str) -> None:
        """Mark a task as failed."""
        for task in self.tasks:
            if task.id == task_id:
                task.status = "failed"
                task.completed_at = datetime.now()
                task.result = f"Failed: {reason}"
                break

    def get_progress(self) -> dict[str, int]:
        """Get progress statistics."""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.status == "completed")
        failed = sum(1 for t in self.tasks if t.status == "failed")
        in_progress = sum(1 for t in self.tasks if t.status == "in_progress")
        pending = total - completed - failed - in_progress

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "percentage": int((completed / total) * 100) if total > 0 else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "task_description": self.task_description,
            "created_at": self.created_at.isoformat(),
            "tasks": [t.to_dict() for t in self.tasks],
            "overall_impact_severity": self.overall_impact_severity,
            "impact_summary": self.impact_summary,
            "requires_migration": self.requires_migration,
            "migration_plan": self.migration_plan,
            "execution_phases": self.execution_phases,
            "estimated_total_complexity": self.estimated_total_complexity,
            "risk_factors": self.risk_factors,
            "prerequisites": self.prerequisites,
            "progress": self.get_progress(),
        }


class PlannerAgent(BaseAgent):
    """Agent responsible for planning task execution with God Mode integration."""

    def __init__(
        self,
        context: AgentContext,
        impact_analyzer: Optional[Any] = None,  # ImpactAnalyzer from spec layer
    ) -> None:
        """Initialize planner agent."""
        super().__init__(context)
        self.impact_analyzer = impact_analyzer
        self._plan: Optional[ExecutionPlan] = None

    async def run(self) -> AgentState:
        """Run the planner to create an execution plan."""
        self.state.status = AgentStatus.RUNNING
        self.state.metrics.start_time = datetime.now()
        self._transition_phase(AgentPhase.PLANNING, "Starting plan generation")

        try:
            # Parse the task description
            self._transition_phase(AgentPhase.PLANNING, "Analyzing task requirements")
            tasks = self._decompose_task(self.context.task_description)

            # Run God Mode Impact Analysis if available
            if self.impact_analyzer and self.context.config.require_impact_analysis:
                self._transition_phase(AgentPhase.PLANNING, "Running God Mode Impact Analysis")
                await self._apply_impact_analysis(tasks)

            # Organize tasks into execution phases
            self._transition_phase(AgentPhase.PLANNING, "Organizing execution phases")
            phases = self._organize_phases(tasks)

            # Create execution plan
            self._plan = ExecutionPlan(
                spec_id=self.context.session_id or "unknown",
                task_description=self.context.task_description,
                tasks=tasks,
                execution_phases=phases,
            )

            # Set overall metrics
            self._calculate_plan_metrics()

            self.state.status = AgentStatus.COMPLETED
            self.state.result = f"Created plan with {len(tasks)} tasks in {len(phases)} phases"
            self.state.artifacts["plan"] = self._plan.to_dict()
            self._transition_phase(AgentPhase.COMPLETING, "Plan generation complete")

        except Exception as e:
            self._record_error(
                f"Planning failed: {str(e)}",
                ErrorSeverity.FATAL,
                exception=e,
            )

        self.state.metrics.end_time = datetime.now()
        return self.state

    def get_plan(self) -> Optional[ExecutionPlan]:
        """Get the generated execution plan."""
        return self._plan

    def _decompose_task(self, description: str) -> list[PlannedTask]:
        """Decompose task description into individual tasks."""
        tasks: list[PlannedTask] = []
        task_counter = 0

        # Detect task type from description
        task_type = self._infer_task_type(description)
        priority = self._infer_priority(description)

        # Generate tasks based on task type
        if task_type == TaskType.IMPLEMENTATION:
            tasks.extend(self._plan_implementation(description, task_counter))
        elif task_type == TaskType.REFACTOR:
            tasks.extend(self._plan_refactor(description, task_counter))
        elif task_type == TaskType.TEST:
            tasks.extend(self._plan_testing(description, task_counter))
        elif task_type == TaskType.MIGRATION:
            tasks.extend(self._plan_migration(description, task_counter))
        else:
            # Default decomposition for generic tasks
            tasks.extend(self._plan_generic(description, task_counter, task_type, priority))

        return tasks

    def _infer_task_type(self, description: str) -> TaskType:
        """Infer task type from description."""
        desc_lower = description.lower()

        type_patterns = [
            (TaskType.MIGRATION, r"\b(migrat|upgrad|convert)\w*\b"),
            (TaskType.REFACTOR, r"\b(refactor|restructur|reorganiz|clean\s*up)\w*\b"),
            (TaskType.TEST, r"\b(test|spec|coverage|assert)\w*\b"),
            (TaskType.DOCUMENTATION, r"\b(document|readme|docs|comment)\w*\b"),
            (TaskType.ANALYSIS, r"\b(analyz|investigat|research|explor)\w*\b"),
            (TaskType.DESIGN, r"\b(design|architect|plan|propos)\w*\b"),
        ]

        for task_type, pattern in type_patterns:
            if re.search(pattern, desc_lower):
                return task_type

        return TaskType.IMPLEMENTATION

    def _infer_priority(self, description: str) -> TaskPriority:
        """Infer task priority from description."""
        desc_lower = description.lower()

        if any(word in desc_lower for word in ["critical", "urgent", "emergency", "asap"]):
            return TaskPriority.CRITICAL
        if any(word in desc_lower for word in ["important", "high", "priority"]):
            return TaskPriority.HIGH
        if any(word in desc_lower for word in ["low", "minor", "when possible"]):
            return TaskPriority.LOW

        return TaskPriority.MEDIUM

    def _plan_implementation(self, description: str, start_id: int) -> list[PlannedTask]:
        """Plan tasks for a new implementation."""
        tasks = []

        # Analysis task
        tasks.append(PlannedTask(
            id=f"task_{start_id + 1}",
            title="Analyze requirements and existing code",
            description=f"Analyze the codebase to understand where and how to implement: {description}",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.HIGH,
            estimated_complexity="simple",
        ))

        # Design task
        tasks.append(PlannedTask(
            id=f"task_{start_id + 2}",
            title="Design implementation approach",
            description="Design the implementation approach, identifying files to modify and create",
            task_type=TaskType.DESIGN,
            priority=TaskPriority.HIGH,
            estimated_complexity="medium",
            dependencies=[f"task_{start_id + 1}"],
        ))

        # Implementation task
        tasks.append(PlannedTask(
            id=f"task_{start_id + 3}",
            title="Implement changes",
            description=f"Implement the required changes for: {description}",
            task_type=TaskType.IMPLEMENTATION,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="complex",
            dependencies=[f"task_{start_id + 2}"],
        ))

        # Testing task
        tasks.append(PlannedTask(
            id=f"task_{start_id + 4}",
            title="Write and run tests",
            description="Write unit tests and verify implementation",
            task_type=TaskType.TEST,
            priority=TaskPriority.HIGH,
            estimated_complexity="medium",
            dependencies=[f"task_{start_id + 3}"],
        ))

        # Review task
        tasks.append(PlannedTask(
            id=f"task_{start_id + 5}",
            title="Review and finalize",
            description="Review changes, ensure code quality, and prepare for commit",
            task_type=TaskType.REVIEW,
            priority=TaskPriority.MEDIUM,
            estimated_complexity="simple",
            dependencies=[f"task_{start_id + 4}"],
        ))

        return tasks

    def _plan_refactor(self, description: str, start_id: int) -> list[PlannedTask]:
        """Plan tasks for a refactoring operation."""
        tasks = []

        tasks.append(PlannedTask(
            id=f"task_{start_id + 1}",
            title="Identify refactoring scope",
            description="Analyze code to identify all areas affected by refactoring",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.HIGH,
            estimated_complexity="medium",
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 2}",
            title="Ensure test coverage",
            description="Verify existing tests cover refactoring scope, add tests if needed",
            task_type=TaskType.TEST,
            priority=TaskPriority.HIGH,
            estimated_complexity="medium",
            dependencies=[f"task_{start_id + 1}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 3}",
            title="Perform refactoring",
            description=f"Execute refactoring: {description}",
            task_type=TaskType.REFACTOR,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="complex",
            dependencies=[f"task_{start_id + 2}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 4}",
            title="Verify tests pass",
            description="Run all tests to ensure refactoring didn't break functionality",
            task_type=TaskType.TEST,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="simple",
            dependencies=[f"task_{start_id + 3}"],
        ))

        return tasks

    def _plan_testing(self, description: str, start_id: int) -> list[PlannedTask]:
        """Plan tasks for testing work."""
        tasks = []

        tasks.append(PlannedTask(
            id=f"task_{start_id + 1}",
            title="Analyze test requirements",
            description="Identify what needs to be tested and current coverage gaps",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.HIGH,
            estimated_complexity="simple",
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 2}",
            title="Write tests",
            description=f"Write tests for: {description}",
            task_type=TaskType.TEST,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="medium",
            dependencies=[f"task_{start_id + 1}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 3}",
            title="Run and verify tests",
            description="Execute tests and ensure they pass",
            task_type=TaskType.TEST,
            priority=TaskPriority.HIGH,
            estimated_complexity="simple",
            dependencies=[f"task_{start_id + 2}"],
        ))

        return tasks

    def _plan_migration(self, description: str, start_id: int) -> list[PlannedTask]:
        """Plan tasks for a migration."""
        tasks = []

        tasks.append(PlannedTask(
            id=f"task_{start_id + 1}",
            title="Analyze migration scope",
            description="Identify all components affected by migration",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="complex",
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 2}",
            title="Create migration plan",
            description="Design step-by-step migration approach with rollback strategy",
            task_type=TaskType.DESIGN,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="complex",
            dependencies=[f"task_{start_id + 1}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 3}",
            title="Implement migration",
            description=f"Execute migration: {description}",
            task_type=TaskType.MIGRATION,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="complex",
            dependencies=[f"task_{start_id + 2}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 4}",
            title="Verify migration",
            description="Test all migrated components and verify functionality",
            task_type=TaskType.TEST,
            priority=TaskPriority.CRITICAL,
            estimated_complexity="medium",
            dependencies=[f"task_{start_id + 3}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 5}",
            title="Document migration",
            description="Document changes and update any affected documentation",
            task_type=TaskType.DOCUMENTATION,
            priority=TaskPriority.MEDIUM,
            estimated_complexity="simple",
            dependencies=[f"task_{start_id + 4}"],
        ))

        return tasks

    def _plan_generic(
        self,
        description: str,
        start_id: int,
        task_type: TaskType,
        priority: TaskPriority,
    ) -> list[PlannedTask]:
        """Plan tasks for generic work."""
        tasks = []

        tasks.append(PlannedTask(
            id=f"task_{start_id + 1}",
            title="Analyze and prepare",
            description=f"Analyze requirements for: {description}",
            task_type=TaskType.ANALYSIS,
            priority=priority,
            estimated_complexity="simple",
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 2}",
            title="Execute task",
            description=description,
            task_type=task_type,
            priority=priority,
            estimated_complexity="medium",
            dependencies=[f"task_{start_id + 1}"],
        ))

        tasks.append(PlannedTask(
            id=f"task_{start_id + 3}",
            title="Verify and complete",
            description="Verify task completion and finalize",
            task_type=TaskType.REVIEW,
            priority=TaskPriority.MEDIUM,
            estimated_complexity="simple",
            dependencies=[f"task_{start_id + 2}"],
        ))

        return tasks

    async def _apply_impact_analysis(self, tasks: list[PlannedTask]) -> None:
        """Apply God Mode Impact Analysis to tasks."""
        if not self.impact_analyzer:
            return

        try:
            # Collect all files that might be affected
            all_files = set()
            for task in tasks:
                all_files.update(task.files_to_modify)
                all_files.update(task.files_to_create)

            # Run impact analysis
            impact = await self.impact_analyzer.analyze_impact(
                self.context.task_description,
                list(all_files),
            )

            # Update plan with impact information
            if self._plan:
                self._plan.overall_impact_severity = impact.severity.value
                self._plan.impact_summary = impact.summary
                self._plan.requires_migration = impact.requires_migration_plan()

                if impact.breaking_changes:
                    self._plan.risk_factors.extend(
                        [bc.description for bc in impact.breaking_changes]
                    )

            # Update tasks with impact severity
            for task in tasks:
                if task.task_type in (TaskType.IMPLEMENTATION, TaskType.REFACTOR, TaskType.MIGRATION):
                    task.impact_severity = impact.severity.value
                    task.breaking_changes = [
                        bc.description for bc in impact.breaking_changes
                        if any(f in task.files_to_modify for f in [bc.location])
                    ]

            logger.info(f"Impact Analysis: severity={impact.severity.value}, migration_required={impact.requires_migration_plan()}")

        except Exception as e:
            logger.warning(f"Impact analysis failed: {e}")
            self._record_error(
                f"Impact analysis warning: {e}",
                ErrorSeverity.WARNING,
                exception=e,
            )

    def _organize_phases(self, tasks: list[PlannedTask]) -> list[list[str]]:
        """Organize tasks into execution phases based on dependencies."""
        phases: list[list[str]] = []
        remaining = {t.id: t for t in tasks}
        completed: set[str] = set()

        while remaining:
            # Find tasks with all dependencies satisfied
            phase_tasks = []
            for task_id, task in list(remaining.items()):
                if all(d in completed for d in task.dependencies):
                    phase_tasks.append(task_id)

            if not phase_tasks:
                # Circular dependency - add remaining tasks in a single phase
                logger.warning("Circular dependency detected, adding remaining tasks")
                phase_tasks = list(remaining.keys())

            phases.append(phase_tasks)

            # Mark tasks as completed for next phase
            for task_id in phase_tasks:
                completed.add(task_id)
                del remaining[task_id]

        return phases

    def _calculate_plan_metrics(self) -> None:
        """Calculate overall plan metrics."""
        if not self._plan:
            return

        # Calculate complexity
        complexity_scores = {"simple": 1, "medium": 2, "complex": 3}
        total_score = sum(
            complexity_scores.get(t.estimated_complexity, 2)
            for t in self._plan.tasks
        )

        avg_score = total_score / len(self._plan.tasks) if self._plan.tasks else 2

        if avg_score < 1.5:
            self._plan.estimated_total_complexity = "simple"
        elif avg_score < 2.5:
            self._plan.estimated_total_complexity = "medium"
        else:
            self._plan.estimated_total_complexity = "complex"


async def run_followup_planner(
    context: AgentContext,
    completed_spec: dict[str, Any],
    impact_analyzer: Optional[Any] = None,
) -> ExecutionPlan:
    """Run planner to add followup tasks to a completed spec."""
    planner = PlannerAgent(context, impact_analyzer)
    await planner.run()

    plan = planner.get_plan()
    if plan is None:
        raise ValueError("Planner failed to create execution plan")

    return plan
