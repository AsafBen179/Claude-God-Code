"""
Tests for spec.pipeline module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from spec.models import WorkflowType
from spec.pipeline import PipelineConfig, PipelineState, SpecPipeline


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = PipelineConfig()
        assert config.interactive is True
        assert config.auto_approve is False
        assert config.complexity_override is None
        assert config.max_retries == 2

    def test_custom_config(self) -> None:
        """Should accept custom values."""
        config = PipelineConfig(
            interactive=False,
            complexity_override="simple",
            max_retries=5,
        )
        assert config.interactive is False
        assert config.complexity_override == "simple"
        assert config.max_retries == 5


class TestPipelineState:
    """Tests for PipelineState dataclass."""

    def test_is_successful_empty(self) -> None:
        """Empty state should be successful."""
        state = PipelineState()
        assert state.is_successful() is True

    def test_get_total_duration(self) -> None:
        """Should calculate duration."""
        state = PipelineState()
        duration = state.get_total_duration()
        assert duration >= 0


class TestSpecPipeline:
    """Tests for SpecPipeline class."""

    def test_infer_workflow_bugfix(self, tmp_path: Path) -> None:
        """Should infer bugfix workflow from description."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Fix the login bug that crashes on mobile")
        assert workflow == WorkflowType.BUGFIX

    def test_infer_workflow_refactor(self, tmp_path: Path) -> None:
        """Should infer refactor workflow from description."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Refactor the user service for better performance")
        assert workflow == WorkflowType.REFACTOR

    def test_infer_workflow_migration(self, tmp_path: Path) -> None:
        """Should infer migration workflow from description."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Migrate database from MySQL to PostgreSQL")
        assert workflow == WorkflowType.MIGRATION

    def test_infer_workflow_integration(self, tmp_path: Path) -> None:
        """Should infer integration workflow from description."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Integrate Stripe payment API")
        assert workflow == WorkflowType.INTEGRATION

    def test_infer_workflow_investigation(self, tmp_path: Path) -> None:
        """Should infer investigation workflow from description."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Research the best caching strategy")
        assert workflow == WorkflowType.INVESTIGATION

    def test_infer_workflow_documentation(self, tmp_path: Path) -> None:
        """Should infer documentation workflow from description."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Add documentation for the auth module")
        assert workflow == WorkflowType.DOCUMENTATION

    def test_infer_workflow_feature_default(self, tmp_path: Path) -> None:
        """Should default to feature workflow."""
        pipeline = SpecPipeline(tmp_path)
        workflow = pipeline._infer_workflow_type("Add user profile page")
        assert workflow == WorkflowType.FEATURE

    def test_get_remaining_phases_standard(self, tmp_path: Path) -> None:
        """Should get remaining phases for standard complexity."""
        from spec.models import Complexity, ComplexityAssessment

        pipeline = SpecPipeline(tmp_path)
        pipeline.state.complexity = ComplexityAssessment(
            complexity=Complexity.STANDARD,
            confidence=0.8,
        )
        pipeline.state.phases_executed = ["discovery", "requirements", "complexity_assessment"]

        remaining = pipeline._get_remaining_phases()
        assert "context" in remaining
        assert "spec_writing" in remaining
        # Already executed phases should not be included
        assert "discovery" not in remaining


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
