"""
Tests for agents.planner module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from agents.base import AgentConfig, AgentContext
from agents.planner import (
    ExecutionPlan,
    PlannedTask,
    PlannerAgent,
    TaskPriority,
    TaskType,
)


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_values(self) -> None:
        """Should have expected priority levels."""
        assert TaskPriority.CRITICAL.value == "critical"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self) -> None:
        """Should have expected task types."""
        assert TaskType.IMPLEMENTATION.value == "implementation"
        assert TaskType.REFACTOR.value == "refactor"
        assert TaskType.TEST.value == "test"
        assert TaskType.MIGRATION.value == "migration"


class TestPlannedTask:
    """Tests for PlannedTask dataclass."""

    def test_create_task(self) -> None:
        """Should create task with correct fields."""
        task = PlannedTask(
            id="task_1",
            title="Implement feature",
            description="Add new feature",
            task_type=TaskType.IMPLEMENTATION,
            priority=TaskPriority.HIGH,
        )
        assert task.id == "task_1"
        assert task.title == "Implement feature"
        assert task.task_type == TaskType.IMPLEMENTATION
        assert task.priority == TaskPriority.HIGH
        assert task.status == "pending"

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        task = PlannedTask(
            id="task_1",
            title="Test task",
            description="Description",
            task_type=TaskType.TEST,
            priority=TaskPriority.MEDIUM,
            files_to_modify=["file1.py"],
        )
        d = task.to_dict()
        assert d["id"] == "task_1"
        assert d["task_type"] == "test"
        assert d["priority"] == "medium"
        assert "file1.py" in d["files_to_modify"]


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""

    def test_create_plan(self) -> None:
        """Should create plan with correct fields."""
        plan = ExecutionPlan(
            spec_id="spec_001",
            task_description="Add authentication",
        )
        assert plan.spec_id == "spec_001"
        assert plan.task_description == "Add authentication"
        assert len(plan.tasks) == 0

    def test_get_pending_tasks(self) -> None:
        """Should return only pending tasks."""
        plan = ExecutionPlan(spec_id="test", task_description="test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH, status="completed"),
            PlannedTask(id="2", title="T2", description="", task_type=TaskType.IMPLEMENTATION, priority=TaskPriority.HIGH, status="pending"),
            PlannedTask(id="3", title="T3", description="", task_type=TaskType.TEST, priority=TaskPriority.MEDIUM, status="pending"),
        ]
        pending = plan.get_pending_tasks()
        assert len(pending) == 2
        assert all(t.status == "pending" for t in pending)

    def test_get_next_task_no_dependencies(self) -> None:
        """Should return task with no dependencies."""
        plan = ExecutionPlan(spec_id="test", task_description="test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH),
            PlannedTask(id="2", title="T2", description="", task_type=TaskType.IMPLEMENTATION, priority=TaskPriority.HIGH, dependencies=["1"]),
        ]
        next_task = plan.get_next_task()
        assert next_task is not None
        assert next_task.id == "1"

    def test_get_next_task_with_dependencies(self) -> None:
        """Should respect task dependencies."""
        plan = ExecutionPlan(spec_id="test", task_description="test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH, status="completed"),
            PlannedTask(id="2", title="T2", description="", task_type=TaskType.IMPLEMENTATION, priority=TaskPriority.HIGH, dependencies=["1"]),
        ]
        next_task = plan.get_next_task()
        assert next_task is not None
        assert next_task.id == "2"

    def test_mark_task_started(self) -> None:
        """Should update task status to in_progress."""
        plan = ExecutionPlan(spec_id="test", task_description="test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH),
        ]
        plan.mark_task_started("1")
        assert plan.tasks[0].status == "in_progress"
        assert plan.tasks[0].started_at is not None

    def test_mark_task_completed(self) -> None:
        """Should update task status to completed."""
        plan = ExecutionPlan(spec_id="test", task_description="test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH),
        ]
        plan.mark_task_completed("1", "Done")
        assert plan.tasks[0].status == "completed"
        assert plan.tasks[0].completed_at is not None
        assert plan.tasks[0].result == "Done"

    def test_get_progress(self) -> None:
        """Should calculate progress correctly."""
        plan = ExecutionPlan(spec_id="test", task_description="test")
        plan.tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH, status="completed"),
            PlannedTask(id="2", title="T2", description="", task_type=TaskType.IMPLEMENTATION, priority=TaskPriority.HIGH, status="in_progress"),
            PlannedTask(id="3", title="T3", description="", task_type=TaskType.TEST, priority=TaskPriority.MEDIUM, status="pending"),
            PlannedTask(id="4", title="T4", description="", task_type=TaskType.REVIEW, priority=TaskPriority.LOW, status="pending"),
        ]
        progress = plan.get_progress()
        assert progress["total"] == 4
        assert progress["completed"] == 1
        assert progress["in_progress"] == 1
        assert progress["pending"] == 2
        assert progress["percentage"] == 25


class TestPlannerAgent:
    """Tests for PlannerAgent class."""

    def test_infer_task_type_implementation(self, tmp_path: Path) -> None:
        """Should infer implementation task type."""
        context = AgentContext(repo_root=tmp_path, task_description="Add user login feature")
        planner = PlannerAgent(context)
        task_type = planner._infer_task_type("Add user login feature")
        assert task_type == TaskType.IMPLEMENTATION

    def test_infer_task_type_refactor(self, tmp_path: Path) -> None:
        """Should infer refactor task type."""
        context = AgentContext(repo_root=tmp_path, task_description="Refactor authentication module")
        planner = PlannerAgent(context)
        task_type = planner._infer_task_type("Refactor authentication module")
        assert task_type == TaskType.REFACTOR

    def test_infer_task_type_migration(self, tmp_path: Path) -> None:
        """Should infer migration task type."""
        context = AgentContext(repo_root=tmp_path, task_description="Migrate database to PostgreSQL")
        planner = PlannerAgent(context)
        task_type = planner._infer_task_type("Migrate database to PostgreSQL")
        assert task_type == TaskType.MIGRATION

    def test_infer_task_type_test(self, tmp_path: Path) -> None:
        """Should infer test task type."""
        context = AgentContext(repo_root=tmp_path, task_description="Add unit tests for auth module")
        planner = PlannerAgent(context)
        task_type = planner._infer_task_type("Add unit tests for auth module")
        assert task_type == TaskType.TEST

    def test_infer_task_type_documentation(self, tmp_path: Path) -> None:
        """Should infer documentation task type."""
        context = AgentContext(repo_root=tmp_path, task_description="Document API endpoints")
        planner = PlannerAgent(context)
        task_type = planner._infer_task_type("Document API endpoints")
        assert task_type == TaskType.DOCUMENTATION

    def test_infer_priority_critical(self, tmp_path: Path) -> None:
        """Should infer critical priority."""
        context = AgentContext(repo_root=tmp_path, task_description="Critical security fix needed urgently")
        planner = PlannerAgent(context)
        priority = planner._infer_priority("Critical security fix needed urgently")
        assert priority == TaskPriority.CRITICAL

    def test_infer_priority_high(self, tmp_path: Path) -> None:
        """Should infer high priority."""
        context = AgentContext(repo_root=tmp_path, task_description="Important feature for release")
        planner = PlannerAgent(context)
        priority = planner._infer_priority("Important feature for release")
        assert priority == TaskPriority.HIGH

    def test_infer_priority_low(self, tmp_path: Path) -> None:
        """Should infer low priority."""
        context = AgentContext(repo_root=tmp_path, task_description="Minor cleanup when possible")
        planner = PlannerAgent(context)
        priority = planner._infer_priority("Minor cleanup when possible")
        assert priority == TaskPriority.LOW

    def test_decompose_implementation_task(self, tmp_path: Path) -> None:
        """Should decompose implementation task into subtasks."""
        context = AgentContext(repo_root=tmp_path, task_description="Add user profile page")
        planner = PlannerAgent(context)
        tasks = planner._decompose_task("Add user profile page")

        assert len(tasks) >= 3
        task_types = [t.task_type for t in tasks]
        assert TaskType.ANALYSIS in task_types
        assert TaskType.IMPLEMENTATION in task_types

    def test_decompose_refactor_task(self, tmp_path: Path) -> None:
        """Should decompose refactor task with test verification."""
        context = AgentContext(repo_root=tmp_path, task_description="Refactor user service")
        planner = PlannerAgent(context)
        tasks = planner._decompose_task("Refactor user service")

        assert len(tasks) >= 3
        task_types = [t.task_type for t in tasks]
        assert TaskType.REFACTOR in task_types
        assert TaskType.TEST in task_types

    def test_organize_phases(self, tmp_path: Path) -> None:
        """Should organize tasks into execution phases."""
        context = AgentContext(repo_root=tmp_path, task_description="Test")
        planner = PlannerAgent(context)

        tasks = [
            PlannedTask(id="1", title="T1", description="", task_type=TaskType.ANALYSIS, priority=TaskPriority.HIGH),
            PlannedTask(id="2", title="T2", description="", task_type=TaskType.IMPLEMENTATION, priority=TaskPriority.HIGH, dependencies=["1"]),
            PlannedTask(id="3", title="T3", description="", task_type=TaskType.TEST, priority=TaskPriority.MEDIUM, dependencies=["2"]),
        ]

        phases = planner._organize_phases(tasks)

        assert len(phases) == 3
        assert "1" in phases[0]
        assert "2" in phases[1]
        assert "3" in phases[2]


class TestPlannerAgentAsync:
    """Async tests for PlannerAgent."""

    @pytest.mark.asyncio
    async def test_run_creates_plan(self, tmp_path: Path) -> None:
        """Should create execution plan."""
        context = AgentContext(
            repo_root=tmp_path,
            task_description="Add user authentication",
            config=AgentConfig(require_impact_analysis=False),
        )
        planner = PlannerAgent(context)
        state = await planner.run()

        assert state.status.value == "completed"
        plan = planner.get_plan()
        assert plan is not None
        assert len(plan.tasks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
