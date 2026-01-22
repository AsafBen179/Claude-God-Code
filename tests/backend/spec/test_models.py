"""
Tests for spec.models module.

Part of Claude God Code - Autonomous Excellence
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "backend"))

from spec.models import (
    BreakingChange,
    Complexity,
    ComplexityAssessment,
    ContextWindow,
    FileContext,
    ImpactAnalysis,
    ImpactSeverity,
    MemoryInsight,
    PhaseResult,
    PhaseStatus,
    ProjectIndex,
    Requirements,
    ServiceInfo,
    WorkflowType,
    create_spec_dir,
    generate_spec_name,
    get_specs_dir,
)


class TestComplexity:
    """Tests for Complexity enum."""

    def test_complexity_values(self) -> None:
        """Should have expected complexity levels."""
        assert Complexity.SIMPLE.value == "simple"
        assert Complexity.STANDARD.value == "standard"
        assert Complexity.COMPLEX.value == "complex"
        assert Complexity.CRITICAL.value == "critical"


class TestComplexityAssessment:
    """Tests for ComplexityAssessment dataclass."""

    def test_simple_phases(self) -> None:
        """Simple complexity should have minimal phases."""
        assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=0.9,
        )
        phases = assessment.phases_to_run()
        assert "discovery" in phases
        assert "quick_spec" in phases
        assert "validation" in phases
        assert "impact_analysis" not in phases

    def test_standard_phases(self) -> None:
        """Standard complexity should have moderate phases."""
        assessment = ComplexityAssessment(
            complexity=Complexity.STANDARD,
            confidence=0.75,
        )
        phases = assessment.phases_to_run()
        assert "discovery" in phases
        assert "requirements" in phases
        assert "context" in phases
        assert "spec_writing" in phases
        assert "validation" in phases

    def test_complex_phases(self) -> None:
        """Complex complexity should include impact analysis."""
        assessment = ComplexityAssessment(
            complexity=Complexity.COMPLEX,
            confidence=0.85,
        )
        phases = assessment.phases_to_run()
        assert "impact_analysis" in phases
        assert "self_critique" in phases

    def test_custom_phases_override(self) -> None:
        """Recommended phases should override defaults."""
        custom_phases = ["discovery", "custom_phase", "validation"]
        assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=0.9,
            recommended_phases=custom_phases,
        )
        phases = assessment.phases_to_run()
        assert phases == custom_phases


class TestFileContext:
    """Tests for FileContext dataclass."""

    def test_create_file_context(self) -> None:
        """Should create FileContext with correct fields."""
        ctx = FileContext(
            path="/project/src/index.ts",
            relative_path="src/index.ts",
            language="typescript",
            size_bytes=1024,
            line_count=50,
            imports=["react", "./utils"],
            exports=["App", "default"],
        )
        assert ctx.language == "typescript"
        assert ctx.size_bytes == 1024
        assert "react" in ctx.imports

    def test_file_context_to_dict(self) -> None:
        """Should convert to dictionary."""
        ctx = FileContext(
            path="/project/src/index.ts",
            relative_path="src/index.ts",
            language="typescript",
        )
        d = ctx.to_dict()
        assert d["language"] == "typescript"
        assert "path" in d


class TestContextWindow:
    """Tests for ContextWindow dataclass."""

    def test_get_total_context_size(self) -> None:
        """Should calculate total context size."""
        ctx = ContextWindow(
            task_description="test task",
            files_to_modify=[
                FileContext(path="a.ts", relative_path="a.ts", language="ts", size_bytes=100),
                FileContext(path="b.ts", relative_path="b.ts", language="ts", size_bytes=200),
            ],
            files_to_reference=[
                FileContext(path="c.ts", relative_path="c.ts", language="ts", size_bytes=150),
            ],
        )
        assert ctx.get_total_context_size() == 450


class TestImpactAnalysis:
    """Tests for ImpactAnalysis dataclass."""

    def test_requires_migration_plan_high_severity(self) -> None:
        """High severity should require migration plan."""
        analysis = ImpactAnalysis(
            severity=ImpactSeverity.HIGH,
            confidence=0.8,
        )
        assert analysis.requires_migration_plan()

    def test_requires_migration_plan_with_breaking_changes(self) -> None:
        """Breaking changes should require migration plan."""
        analysis = ImpactAnalysis(
            severity=ImpactSeverity.MEDIUM,
            confidence=0.8,
            breaking_changes=[
                BreakingChange(
                    change_type="api_change",
                    location="src/api.ts",
                    description="Function signature changed",
                )
            ],
        )
        assert analysis.requires_migration_plan()

    def test_no_migration_for_low_severity(self) -> None:
        """Low severity without breaking changes should not require migration."""
        analysis = ImpactAnalysis(
            severity=ImpactSeverity.LOW,
            confidence=0.8,
            rollback_complexity="low",
        )
        assert not analysis.requires_migration_plan()


class TestRequirements:
    """Tests for Requirements dataclass."""

    def test_requirements_to_dict(self) -> None:
        """Should convert to dictionary."""
        req = Requirements(
            task_description="Add login feature",
            workflow_type=WorkflowType.FEATURE,
            services_involved=["backend", "frontend"],
            user_requirements=["Users can login"],
        )
        d = req.to_dict()
        assert d["workflow_type"] == "feature"
        assert "backend" in d["services_involved"]

    def test_requirements_from_dict(self) -> None:
        """Should create from dictionary."""
        data = {
            "task_description": "Fix bug",
            "workflow_type": "bugfix",
            "user_requirements": ["Fix the crash"],
        }
        req = Requirements.from_dict(data)
        assert req.workflow_type == WorkflowType.BUGFIX
        assert req.task_description == "Fix bug"


class TestGenerateSpecName:
    """Tests for generate_spec_name function."""

    def test_basic_name(self) -> None:
        """Should generate clean name from description."""
        name = generate_spec_name("Add user authentication")
        assert name == "add-user-authentication"

    def test_special_characters(self) -> None:
        """Should remove special characters."""
        name = generate_spec_name("Fix bug #123 in auth!")
        assert "#" not in name
        assert "!" not in name

    def test_long_description(self) -> None:
        """Should truncate long descriptions."""
        long_desc = "This is a very long task description that should be truncated to a reasonable length"
        name = generate_spec_name(long_desc)
        assert len(name) <= 50

    def test_empty_description(self) -> None:
        """Should handle empty description."""
        name = generate_spec_name("")
        assert name == "unnamed-spec"


class TestCreateSpecDir:
    """Tests for create_spec_dir function."""

    def test_creates_numbered_dir(self, tmp_path: Path) -> None:
        """Should create numbered directory."""
        specs_dir = tmp_path / "specs"
        spec_dir = create_spec_dir(specs_dir)
        assert spec_dir.name.startswith("001-")
        assert "pending" in spec_dir.name

    def test_increments_number(self, tmp_path: Path) -> None:
        """Should increment number for subsequent specs."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        # Create first spec
        (specs_dir / "001-first").mkdir()

        # Create second spec
        spec_dir = create_spec_dir(specs_dir)
        assert spec_dir.name.startswith("002-")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
