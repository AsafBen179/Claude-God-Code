"""
Spec Layer Data Models
======================

Strongly-typed data models for specification management, complexity assessment,
context resolution, and impact analysis.

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeAlias

# Type aliases for clarity
RunAgentFn: TypeAlias = Callable[
    [str, str, bool, str | None],
    Coroutine[Any, Any, tuple[bool, str]]
]


class Complexity(Enum):
    """Task complexity tiers that determine workflow and phases."""

    SIMPLE = "simple"      # 1-2 files, single service, no integrations
    STANDARD = "standard"  # 3-10 files, 1-2 services, minimal integrations
    COMPLEX = "complex"    # 10+ files, multiple services, external integrations
    CRITICAL = "critical"  # Infrastructure changes, breaking changes, migrations


class WorkflowType(Enum):
    """Types of development workflows."""

    FEATURE = "feature"            # New functionality
    BUGFIX = "bugfix"              # Bug fixes
    REFACTOR = "refactor"          # Code restructuring
    MIGRATION = "migration"        # Data/schema migrations
    INTEGRATION = "integration"    # External service integration
    INVESTIGATION = "investigation"  # Research/debugging
    DOCUMENTATION = "documentation"  # Docs only


class ImpactSeverity(Enum):
    """Severity levels for impact analysis."""

    NONE = "none"          # No impact
    LOW = "low"            # Minimal risk, easy rollback
    MEDIUM = "medium"      # Moderate risk, testing required
    HIGH = "high"          # Significant risk, careful review needed
    CRITICAL = "critical"  # Breaking changes, requires migration plan


class PhaseStatus(Enum):
    """Status of a pipeline phase."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProjectIndex:
    """Indexed project structure and metadata."""

    project_type: str = "unknown"
    root_path: Path = field(default_factory=Path)
    tech_stack: dict[str, list[str]] = field(default_factory=dict)
    services: dict[str, ServiceInfo] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)
    test_directories: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    dev_dependencies: dict[str, str] = field(default_factory=dict)
    file_count: int = 0
    total_lines: int = 0
    indexed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_type": self.project_type,
            "root_path": str(self.root_path),
            "tech_stack": self.tech_stack,
            "services": {k: v.to_dict() for k, v in self.services.items()},
            "entry_points": self.entry_points,
            "test_directories": self.test_directories,
            "config_files": self.config_files,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
            "indexed_at": self.indexed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectIndex:
        """Create from dictionary."""
        services = {}
        for k, v in data.get("services", {}).items():
            if isinstance(v, dict):
                services[k] = ServiceInfo.from_dict(v)

        return cls(
            project_type=data.get("project_type", "unknown"),
            root_path=Path(data.get("root_path", ".")),
            tech_stack=data.get("tech_stack", {}),
            services=services,
            entry_points=data.get("entry_points", []),
            test_directories=data.get("test_directories", []),
            config_files=data.get("config_files", []),
            dependencies=data.get("dependencies", {}),
            dev_dependencies=data.get("dev_dependencies", {}),
            file_count=data.get("file_count", 0),
            total_lines=data.get("total_lines", 0),
            indexed_at=datetime.fromisoformat(data["indexed_at"])
            if "indexed_at" in data
            else datetime.now(),
        )


@dataclass
class ServiceInfo:
    """Information about a service in a monorepo."""

    name: str
    path: str
    language: str = "unknown"
    framework: str | None = None
    entry_point: str | None = None
    dependencies: list[str] = field(default_factory=list)
    internal_deps: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": self.path,
            "language": self.language,
            "framework": self.framework,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "internal_deps": self.internal_deps,
            "exports": self.exports,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceInfo:
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            path=data.get("path", ""),
            language=data.get("language", "unknown"),
            framework=data.get("framework"),
            entry_point=data.get("entry_point"),
            dependencies=data.get("dependencies", []),
            internal_deps=data.get("internal_deps", []),
            exports=data.get("exports", []),
        )


@dataclass
class FileContext:
    """Context information about a file."""

    path: str
    relative_path: str
    language: str
    size_bytes: int = 0
    line_count: int = 0
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    modification_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "relative_path": self.relative_path,
            "language": self.language,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "imports": self.imports,
            "exports": self.exports,
            "functions": self.functions,
            "classes": self.classes,
            "dependencies": self.dependencies,
            "relevance_score": self.relevance_score,
            "modification_reason": self.modification_reason,
        }


@dataclass
class ContextWindow:
    """Aggregated context for a specification task."""

    task_description: str
    scoped_services: list[str] = field(default_factory=list)
    files_to_modify: list[FileContext] = field(default_factory=list)
    files_to_reference: list[FileContext] = field(default_factory=list)
    related_tests: list[str] = field(default_factory=list)
    memory_insights: list[MemoryInsight] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_description": self.task_description,
            "scoped_services": self.scoped_services,
            "files_to_modify": [f.to_dict() for f in self.files_to_modify],
            "files_to_reference": [f.to_dict() for f in self.files_to_reference],
            "related_tests": self.related_tests,
            "memory_insights": [m.to_dict() for m in self.memory_insights],
            "dependency_graph": self.dependency_graph,
            "created_at": self.created_at.isoformat(),
        }

    def get_total_context_size(self) -> int:
        """Get total size of all context files in bytes."""
        total = sum(f.size_bytes for f in self.files_to_modify)
        total += sum(f.size_bytes for f in self.files_to_reference)
        return total


@dataclass
class MemoryInsight:
    """Insight from the memory system (patterns, gotchas, learnings)."""

    insight_type: str  # pattern, gotcha, session_insight, task_outcome
    content: str
    source: str  # file-based, graphiti, context-cache
    relevance_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insight_type": self.insight_type,
            "content": self.content,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ImpactAnalysis:
    """
    Impact analysis result predicting how changes might affect the codebase.

    This is the "God Mode" feature - analyzing potential breakages before implementation.
    """

    severity: ImpactSeverity
    confidence: float  # 0.0 to 1.0
    affected_files: list[str] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    breaking_changes: list[BreakingChange] = field(default_factory=list)
    test_coverage_gaps: list[str] = field(default_factory=list)
    rollback_complexity: str = "low"  # low, medium, high
    recommended_mitigations: list[str] = field(default_factory=list)
    analysis_reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "confidence": self.confidence,
            "affected_files": self.affected_files,
            "affected_services": self.affected_services,
            "breaking_changes": [bc.to_dict() for bc in self.breaking_changes],
            "test_coverage_gaps": self.test_coverage_gaps,
            "rollback_complexity": self.rollback_complexity,
            "recommended_mitigations": self.recommended_mitigations,
            "analysis_reasoning": self.analysis_reasoning,
        }

    def requires_migration_plan(self) -> bool:
        """Check if changes require a migration plan."""
        return (
            self.severity in (ImpactSeverity.HIGH, ImpactSeverity.CRITICAL)
            or len(self.breaking_changes) > 0
            or self.rollback_complexity == "high"
        )


@dataclass
class BreakingChange:
    """A potential breaking change detected during impact analysis."""

    change_type: str  # api_change, schema_change, removal, signature_change
    location: str  # file:line or service name
    description: str
    affected_consumers: list[str] = field(default_factory=list)
    migration_required: bool = False
    suggested_fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "change_type": self.change_type,
            "location": self.location,
            "description": self.description,
            "affected_consumers": self.affected_consumers,
            "migration_required": self.migration_required,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ComplexityAssessment:
    """Result of analyzing task complexity."""

    complexity: Complexity
    confidence: float  # 0.0 to 1.0
    signals: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    # Detected characteristics
    estimated_files: int = 1
    estimated_services: int = 1
    external_integrations: list[str] = field(default_factory=list)
    infrastructure_changes: bool = False

    # AI-recommended phases (if using AI assessment)
    recommended_phases: list[str] = field(default_factory=list)

    # Flags from AI assessment
    needs_research: bool = False
    needs_self_critique: bool = False
    needs_impact_analysis: bool = False

    def phases_to_run(self) -> list[str]:
        """Return list of phase names to run based on complexity."""
        if self.recommended_phases:
            return self.recommended_phases

        if self.complexity == Complexity.SIMPLE:
            return ["discovery", "quick_spec", "validation"]

        elif self.complexity == Complexity.STANDARD:
            phases = ["discovery", "requirements"]
            if self.needs_research:
                phases.append("research")
            phases.extend(["context", "spec_writing", "planning", "validation"])
            return phases

        elif self.complexity == Complexity.COMPLEX:
            phases = [
                "discovery",
                "requirements",
                "research",
                "context",
                "impact_analysis",
                "spec_writing",
                "self_critique",
                "planning",
                "validation",
            ]
            return phases

        else:  # CRITICAL
            return [
                "discovery",
                "requirements",
                "research",
                "context",
                "impact_analysis",
                "migration_planning",
                "spec_writing",
                "self_critique",
                "planning",
                "validation",
                "rollback_planning",
            ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "complexity": self.complexity.value,
            "confidence": self.confidence,
            "signals": self.signals,
            "reasoning": self.reasoning,
            "estimated_files": self.estimated_files,
            "estimated_services": self.estimated_services,
            "external_integrations": self.external_integrations,
            "infrastructure_changes": self.infrastructure_changes,
            "recommended_phases": self.recommended_phases,
            "needs_research": self.needs_research,
            "needs_self_critique": self.needs_self_critique,
            "needs_impact_analysis": self.needs_impact_analysis,
            "phases_to_run": self.phases_to_run(),
        }


@dataclass
class PhaseResult:
    """Result of executing a pipeline phase."""

    phase_name: str
    status: PhaseStatus
    output_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retries: int = 0
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if phase completed successfully."""
        return self.status == PhaseStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phase_name": self.phase_name,
            "status": self.status.value,
            "output_files": self.output_files,
            "errors": self.errors,
            "warnings": self.warnings,
            "retries": self.retries,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class Requirements:
    """Gathered requirements for a specification."""

    task_description: str
    workflow_type: WorkflowType = WorkflowType.FEATURE
    services_involved: list[str] = field(default_factory=list)
    user_requirements: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_description": self.task_description,
            "workflow_type": self.workflow_type.value,
            "services_involved": self.services_involved,
            "user_requirements": self.user_requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "constraints": self.constraints,
            "out_of_scope": self.out_of_scope,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Requirements:
        """Create from dictionary."""
        workflow = data.get("workflow_type", "feature")
        try:
            workflow_type = WorkflowType(workflow)
        except ValueError:
            workflow_type = WorkflowType.FEATURE

        return cls(
            task_description=data.get("task_description", ""),
            workflow_type=workflow_type,
            services_involved=data.get("services_involved", []),
            user_requirements=data.get("user_requirements", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            constraints=data.get("constraints", []),
            out_of_scope=data.get("out_of_scope", []),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
        )


@dataclass
class Specification:
    """Complete specification document."""

    name: str
    requirements: Requirements
    context: ContextWindow
    complexity: ComplexityAssessment
    impact_analysis: ImpactAnalysis | None = None
    implementation_plan: list[dict[str, Any]] = field(default_factory=list)
    qa_criteria: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    approved: bool = False
    approved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "requirements": self.requirements.to_dict(),
            "context": self.context.to_dict(),
            "complexity": self.complexity.to_dict(),
            "impact_analysis": self.impact_analysis.to_dict()
            if self.impact_analysis
            else None,
            "implementation_plan": self.implementation_plan,
            "qa_criteria": self.qa_criteria,
            "created_at": self.created_at.isoformat(),
            "approved": self.approved,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }


def generate_spec_name(task_description: str) -> str:
    """
    Generate a clean spec name from task description.

    Args:
        task_description: The task description

    Returns:
        A clean, filesystem-safe spec name
    """
    if not task_description:
        return "unnamed-spec"

    name = task_description.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = name.strip("-")
    name = name[:50]

    return name or "unnamed-spec"


def get_specs_dir(project_dir: Path) -> Path:
    """Get the specifications directory for a project."""
    return project_dir / ".claude-god-code" / "specs"


def create_spec_dir(specs_dir: Path, spec_number: int | None = None) -> Path:
    """
    Create a new spec directory with sequential numbering.

    Args:
        specs_dir: The base specs directory
        spec_number: Optional explicit spec number

    Returns:
        Path to the created spec directory
    """
    specs_dir.mkdir(parents=True, exist_ok=True)

    if spec_number is None:
        existing = list(specs_dir.glob("*"))
        numbers = []
        for p in existing:
            match = re.match(r"^(\d+)-", p.name)
            if match:
                numbers.append(int(match.group(1)))
        spec_number = max(numbers, default=0) + 1

    spec_name = f"{spec_number:03d}-pending"
    spec_dir = specs_dir / spec_name
    spec_dir.mkdir(parents=True, exist_ok=True)

    return spec_dir
