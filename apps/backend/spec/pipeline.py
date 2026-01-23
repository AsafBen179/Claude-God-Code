"""
Spec Pipeline Orchestrator
==========================

Orchestrates the spec creation process from initial user intent
to a finalized technical specification.

Pipeline Phases:
1. Discovery - Project structure analysis
2. Requirements - User intent gathering
3. Complexity Assessment - Determine workflow
4. Context Resolution - Build context window
5. Impact Analysis - God Mode prediction
6. Spec Writing - Generate specification
7. Validation - Verify completeness

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from spec.models import (
    Complexity,
    ComplexityAssessment,
    ContextWindow,
    ImpactAnalysis,
    PhaseResult,
    PhaseStatus,
    Requirements,
    Specification,
    WorkflowType,
    create_spec_dir,
    generate_spec_name,
    get_specs_dir,
)
from spec.discovery import run_discovery, load_project_index
from spec.context import run_context_discovery, load_context
from spec.complexity import run_complexity_assessment, load_assessment
from spec.impact import run_impact_analysis, load_impact_analysis

try:
    from skills import SkillRegistry, Skill
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False
    SkillRegistry = None
    Skill = None

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the spec pipeline."""

    interactive: bool = True
    auto_approve: bool = False
    complexity_override: str | None = None
    skip_impact_analysis: bool = False
    max_retries: int = 2
    thinking_level: str = "medium"


@dataclass
class PipelineState:
    """State tracking for pipeline execution."""

    spec_dir: Path | None = None
    task_description: str = ""
    requirements: Requirements | None = None
    complexity: ComplexityAssessment | None = None
    context: ContextWindow | None = None
    impact: ImpactAnalysis | None = None
    phase_results: list[PhaseResult] = field(default_factory=list)
    phases_executed: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    applicable_skills: list[Any] = field(default_factory=list)

    def add_result(self, result: PhaseResult) -> None:
        """Add a phase result to the state."""
        self.phase_results.append(result)
        self.phases_executed.append(result.phase_name)

    def is_successful(self) -> bool:
        """Check if all phases completed successfully."""
        return all(r.success for r in self.phase_results)

    def get_total_duration(self) -> float:
        """Get total pipeline duration in seconds."""
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()


class SpecPipeline:
    """
    Orchestrates the spec creation pipeline.

    Dynamically selects phases based on complexity assessment
    and executes them in sequence with proper error handling.
    """

    def __init__(
        self,
        project_dir: Path,
        config: PipelineConfig | None = None,
    ):
        self.project_dir = project_dir.resolve()
        self.config = config or PipelineConfig()
        self.state = PipelineState()

        # Get specs directory
        self.specs_dir = get_specs_dir(self.project_dir)

        # Phase registry
        self._phases: dict[str, Callable[[], PhaseResult]] = {
            "discovery": self._phase_discovery,
            "requirements": self._phase_requirements,
            "complexity_assessment": self._phase_complexity,
            "context": self._phase_context,
            "impact_analysis": self._phase_impact,
            "spec_writing": self._phase_spec_writing,
            "validation": self._phase_validation,
        }

    async def run(
        self,
        task_description: str | None = None,
        spec_name: str | None = None,
        spec_dir: Path | None = None,
    ) -> PipelineState:
        """
        Run the spec creation pipeline.

        Args:
            task_description: Initial task description
            spec_name: Optional spec name
            spec_dir: Optional existing spec directory

        Returns:
            PipelineState with execution results
        """
        logger.info("Starting spec pipeline...")

        # Initialize state
        self.state.task_description = task_description or ""

        # Create or use spec directory
        if spec_dir:
            self.state.spec_dir = spec_dir
        elif spec_name:
            self.state.spec_dir = self.specs_dir / spec_name
        else:
            self.state.spec_dir = create_spec_dir(self.specs_dir)

        self.state.spec_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Spec directory: {self.state.spec_dir}")

        try:
            # Phase 1: Discovery (always runs)
            result = await self._run_phase("discovery")
            if not result.success:
                return self._finalize_state()

            # Phase 2: Requirements (if interactive)
            if self.config.interactive:
                result = await self._run_phase("requirements")
                if not result.success:
                    return self._finalize_state()

            # Phase 3: Complexity Assessment
            result = await self._run_phase("complexity_assessment")
            if not result.success:
                return self._finalize_state()

            # Determine remaining phases based on complexity
            phases_to_run = self._get_remaining_phases()

            # Execute remaining phases
            for phase_name in phases_to_run:
                if phase_name not in self._phases:
                    logger.warning(f"Unknown phase: {phase_name}, skipping")
                    continue

                result = await self._run_phase(phase_name)
                if not result.success:
                    logger.error(f"Phase {phase_name} failed, stopping pipeline")
                    break

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.state.phase_results.append(PhaseResult(
                phase_name="pipeline",
                status=PhaseStatus.FAILED,
                errors=[str(e)],
            ))

        return self._finalize_state()

    async def _run_phase(self, phase_name: str) -> PhaseResult:
        """Run a single phase with retry logic."""
        logger.info(f"Running phase: {phase_name}")
        start_time = time.time()

        for attempt in range(self.config.max_retries + 1):
            try:
                phase_fn = self._phases[phase_name]
                result = phase_fn()

                # Update duration
                result.duration_seconds = time.time() - start_time
                result.retries = attempt

                self.state.add_result(result)
                return result

            except Exception as e:
                logger.warning(f"Phase {phase_name} attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(1)  # Brief delay before retry
                else:
                    result = PhaseResult(
                        phase_name=phase_name,
                        status=PhaseStatus.FAILED,
                        errors=[str(e)],
                        retries=attempt,
                        duration_seconds=time.time() - start_time,
                    )
                    self.state.add_result(result)
                    return result

        # Should not reach here
        return PhaseResult(
            phase_name=phase_name,
            status=PhaseStatus.FAILED,
            errors=["Max retries exceeded"],
        )

    def _get_remaining_phases(self) -> list[str]:
        """Get list of phases to run based on complexity."""
        if not self.state.complexity:
            return ["context", "spec_writing", "validation"]

        all_phases = self.state.complexity.phases_to_run()

        # Filter out already executed phases
        executed = set(self.state.phases_executed)
        remaining = [p for p in all_phases if p not in executed]

        # Apply config overrides
        if self.config.skip_impact_analysis and "impact_analysis" in remaining:
            remaining.remove("impact_analysis")

        return remaining

    def _phase_discovery(self) -> PhaseResult:
        """Execute discovery phase."""
        return run_discovery(
            self.project_dir,
            self.state.spec_dir,
        )

    def _phase_requirements(self) -> PhaseResult:
        """Execute requirements gathering phase."""
        # For now, create a basic requirements file
        # In full implementation, this would use an agent dialog

        requirements = Requirements(
            task_description=self.state.task_description,
            workflow_type=self._infer_workflow_type(self.state.task_description),
            user_requirements=[self.state.task_description] if self.state.task_description else [],
            acceptance_criteria=[],
            constraints=[],
        )

        self.state.requirements = requirements

        # Save requirements
        req_path = self.state.spec_dir / "requirements.json"
        with open(req_path, "w", encoding="utf-8") as f:
            json.dump(requirements.to_dict(), f, indent=2)

        return PhaseResult(
            phase_name="requirements",
            status=PhaseStatus.COMPLETED,
            output_files=[str(req_path)],
        )

    def _phase_complexity(self) -> PhaseResult:
        """Execute complexity assessment phase."""
        result = run_complexity_assessment(
            self.state.spec_dir,
            self.state.task_description,
            self.state.requirements,
            self.config.complexity_override,
        )

        if result.success:
            self.state.complexity = load_assessment(self.state.spec_dir)

        return result

    def _phase_context(self) -> PhaseResult:
        """Execute context resolution phase."""
        services = []
        if self.state.requirements:
            services = self.state.requirements.services_involved

        result = run_context_discovery(
            self.project_dir,
            self.state.spec_dir,
            self.state.task_description,
            services,
        )

        if result.success:
            self.state.context = load_context(self.state.spec_dir)

        return result

    def _phase_impact(self) -> PhaseResult:
        """Execute impact analysis phase (God Mode)."""
        result = run_impact_analysis(
            self.project_dir,
            self.state.spec_dir,
            self.state.requirements,
        )

        if result.success:
            self.state.impact = load_impact_analysis(self.state.spec_dir)

        return result

    def _phase_spec_writing(self) -> PhaseResult:
        """Execute spec writing phase."""
        # Discover applicable skills before generating spec
        self._discover_applicable_skills()

        # Generate specification document
        spec_path = self.state.spec_dir / "spec.md"

        try:
            spec_content = self._generate_spec_content()

            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(spec_content)

            # Save skills configuration if any skills are applicable
            if self.state.applicable_skills:
                skills_path = self.state.spec_dir / "skills.json"
                skills_data = {
                    "applicable_skills": [
                        s.metadata.to_dict() if hasattr(s, 'metadata') else {"name": str(s)}
                        for s in self.state.applicable_skills
                    ],
                    "task_description": self.state.task_description,
                }
                with open(skills_path, "w", encoding="utf-8") as f:
                    json.dump(skills_data, f, indent=2)

            return PhaseResult(
                phase_name="spec_writing",
                status=PhaseStatus.COMPLETED,
                output_files=[str(spec_path)],
            )

        except Exception as e:
            return PhaseResult(
                phase_name="spec_writing",
                status=PhaseStatus.FAILED,
                errors=[str(e)],
            )

    def _discover_applicable_skills(self) -> None:
        """Discover and load skills applicable to this task."""
        if not SKILLS_AVAILABLE:
            logger.debug("Skills system not available")
            return

        try:
            registry = SkillRegistry()

            # Get file paths from context
            file_paths = []
            if self.state.context:
                file_paths.extend(
                    f.relative_path for f in (self.state.context.files_to_modify or [])
                )

            # Discover applicable skills
            skills = registry.get_applicable_skills(
                self.state.task_description,
                file_paths,
            )

            self.state.applicable_skills = skills

            if skills:
                logger.info(
                    f"Discovered {len(skills)} applicable skill(s): "
                    f"{', '.join(s.metadata.name for s in skills)}"
                )

        except Exception as e:
            logger.warning(f"Failed to discover skills: {e}")

    def _phase_validation(self) -> PhaseResult:
        """Execute validation phase."""
        errors: list[str] = []
        warnings: list[str] = []

        # Check required files exist
        required_files = [
            "project_index.json",
            "complexity_assessment.json",
        ]

        if self.state.complexity and self.state.complexity.complexity != Complexity.SIMPLE:
            required_files.extend(["context.json", "requirements.json", "spec.md"])

        for filename in required_files:
            file_path = self.state.spec_dir / filename
            if not file_path.exists():
                errors.append(f"Missing required file: {filename}")

        # Validate spec content
        spec_path = self.state.spec_dir / "spec.md"
        if spec_path.exists():
            content = spec_path.read_text(encoding="utf-8")
            if len(content) < 100:
                warnings.append("Spec content seems too short")

        # Check impact analysis for critical changes
        if self.state.impact:
            if self.state.impact.requires_migration_plan():
                warnings.append("Changes require migration plan - review before proceeding")

        status = PhaseStatus.COMPLETED if not errors else PhaseStatus.FAILED

        return PhaseResult(
            phase_name="validation",
            status=status,
            output_files=[],
            errors=errors,
            warnings=warnings,
        )

    def _infer_workflow_type(self, task_description: str) -> WorkflowType:
        """Infer workflow type from task description."""
        task_lower = task_description.lower()

        if any(kw in task_lower for kw in ["fix", "bug", "error", "issue", "broken"]):
            return WorkflowType.BUGFIX
        elif any(kw in task_lower for kw in ["refactor", "restructure", "reorganize", "clean"]):
            return WorkflowType.REFACTOR
        elif any(kw in task_lower for kw in ["migrate", "migration", "upgrade", "convert"]):
            return WorkflowType.MIGRATION
        elif any(kw in task_lower for kw in ["integrate", "integration", "connect", "api"]):
            return WorkflowType.INTEGRATION
        elif any(kw in task_lower for kw in ["investigate", "research", "analyze", "debug"]):
            return WorkflowType.INVESTIGATION
        elif any(kw in task_lower for kw in ["document", "readme", "docs", "comment"]):
            return WorkflowType.DOCUMENTATION
        else:
            return WorkflowType.FEATURE

    def _generate_spec_content(self) -> str:
        """Generate specification markdown content."""
        lines: list[str] = []

        # Header
        spec_name = generate_spec_name(self.state.task_description)
        lines.append(f"# Specification: {spec_name}")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().isoformat()}*")
        lines.append("")

        # Overview
        lines.append("## Overview")
        lines.append("")
        lines.append(self.state.task_description or "No task description provided.")
        lines.append("")

        # Requirements
        if self.state.requirements:
            lines.append("## Requirements")
            lines.append("")
            lines.append(f"**Workflow Type**: {self.state.requirements.workflow_type.value}")
            lines.append("")

            if self.state.requirements.user_requirements:
                lines.append("### User Requirements")
                for req in self.state.requirements.user_requirements:
                    lines.append(f"- {req}")
                lines.append("")

            if self.state.requirements.acceptance_criteria:
                lines.append("### Acceptance Criteria")
                for criteria in self.state.requirements.acceptance_criteria:
                    lines.append(f"- [ ] {criteria}")
                lines.append("")

            if self.state.requirements.constraints:
                lines.append("### Constraints")
                for constraint in self.state.requirements.constraints:
                    lines.append(f"- {constraint}")
                lines.append("")

        # Complexity Assessment
        if self.state.complexity:
            lines.append("## Complexity Assessment")
            lines.append("")
            lines.append(f"**Level**: {self.state.complexity.complexity.value.upper()}")
            lines.append(f"**Confidence**: {self.state.complexity.confidence:.0%}")
            lines.append(f"**Reasoning**: {self.state.complexity.reasoning}")
            lines.append("")
            lines.append(f"**Estimated Files**: {self.state.complexity.estimated_files}")
            lines.append(f"**Estimated Services**: {self.state.complexity.estimated_services}")
            lines.append("")

        # Context
        if self.state.context:
            lines.append("## Context")
            lines.append("")

            if self.state.context.files_to_modify:
                lines.append("### Files to Modify")
                for f in self.state.context.files_to_modify[:15]:
                    reason = f" - {f.modification_reason}" if f.modification_reason else ""
                    lines.append(f"- `{f.relative_path}`{reason}")
                lines.append("")

            if self.state.context.files_to_reference:
                lines.append("### Reference Files")
                for f in self.state.context.files_to_reference[:10]:
                    lines.append(f"- `{f.relative_path}`")
                lines.append("")

            if self.state.context.related_tests:
                lines.append("### Related Tests")
                for test in self.state.context.related_tests[:10]:
                    lines.append(f"- `{test}`")
                lines.append("")

        # Impact Analysis
        if self.state.impact:
            lines.append("## Impact Analysis (God Mode)")
            lines.append("")
            lines.append(f"**Severity**: {self.state.impact.severity.value.upper()}")
            lines.append(f"**Rollback Complexity**: {self.state.impact.rollback_complexity}")
            lines.append("")

            if self.state.impact.affected_services:
                lines.append(f"**Affected Services**: {', '.join(self.state.impact.affected_services)}")
                lines.append("")

            if self.state.impact.breaking_changes:
                lines.append("### Breaking Changes")
                for bc in self.state.impact.breaking_changes[:10]:
                    lines.append(f"- **{bc.change_type}** at `{bc.location}`: {bc.description}")
                lines.append("")

            if self.state.impact.test_coverage_gaps:
                lines.append("### Test Coverage Gaps")
                for gap in self.state.impact.test_coverage_gaps[:10]:
                    lines.append(f"- `{gap}`")
                lines.append("")

            if self.state.impact.recommended_mitigations:
                lines.append("### Recommended Mitigations")
                for mitigation in self.state.impact.recommended_mitigations:
                    lines.append(f"- {mitigation}")
                lines.append("")

        # Active Skills
        if self.state.applicable_skills:
            lines.append("## Active Skills")
            lines.append("")
            lines.append("The following skills are automatically applied for this task:")
            lines.append("")
            for skill in self.state.applicable_skills:
                if hasattr(skill, 'metadata'):
                    lines.append(f"- **{skill.metadata.name}**: {skill.metadata.description}")
                    if skill.metadata.tags:
                        lines.append(f"  - Tags: {', '.join(skill.metadata.tags)}")
            lines.append("")
            lines.append("*Skill protocols will be injected into agent prompts during build phase.*")
            lines.append("")

        # Implementation Plan placeholder
        lines.append("## Implementation Plan")
        lines.append("")
        lines.append("*To be generated during planning phase*")
        lines.append("")

        # QA Criteria placeholder
        lines.append("## QA Criteria")
        lines.append("")
        lines.append("*To be defined based on acceptance criteria*")
        lines.append("")

        return "\n".join(lines)

    def _finalize_state(self) -> PipelineState:
        """Finalize pipeline state."""
        self.state.completed_at = datetime.now()

        # Log summary
        duration = self.state.get_total_duration()
        success = self.state.is_successful()
        status = "SUCCESS" if success else "FAILED"

        logger.info(
            f"Pipeline {status}: {len(self.state.phases_executed)} phases "
            f"executed in {duration:.1f}s"
        )

        return self.state


async def create_spec(
    project_dir: Path,
    task_description: str,
    interactive: bool = True,
    complexity_override: str | None = None,
) -> PipelineState:
    """
    Convenience function to create a spec.

    Args:
        project_dir: Project root directory
        task_description: Task description
        interactive: Whether to run in interactive mode
        complexity_override: Optional complexity override

    Returns:
        PipelineState with execution results
    """
    config = PipelineConfig(
        interactive=interactive,
        complexity_override=complexity_override,
    )

    pipeline = SpecPipeline(project_dir, config)
    return await pipeline.run(task_description)
