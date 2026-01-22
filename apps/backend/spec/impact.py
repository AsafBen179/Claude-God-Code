"""
Impact Analysis Module - God Mode
==================================

Predicts how changes might break other modules BEFORE implementation starts.
Analyzes dependency chains, API contracts, and potential breaking changes.

This is the "God Mode" feature - seeing the future impact of code changes.

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from spec.models import (
    BreakingChange,
    ContextWindow,
    FileContext,
    ImpactAnalysis,
    ImpactSeverity,
    PhaseResult,
    PhaseStatus,
    ProjectIndex,
    Requirements,
)
from spec.discovery import load_project_index
from spec.context import load_context

logger = logging.getLogger(__name__)


@dataclass
class DependencyNode:
    """A node in the dependency graph."""

    path: str
    exports: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)  # Files that depend on this
    dependencies: list[str] = field(default_factory=list)  # Files this depends on


class ImpactAnalyzer:
    """
    Analyzes potential impact of code changes.

    God Mode Features:
    1. Dependency Chain Analysis - What files depend on the files being changed?
    2. API Contract Validation - Will changes break existing consumers?
    3. Test Coverage Gap Detection - Are there untested paths?
    4. Rollback Complexity Assessment - How hard to revert if things go wrong?
    5. Breaking Change Detection - Identifies potential breaking changes
    """

    # Patterns that indicate breaking changes
    BREAKING_PATTERNS = {
        "api_change": [
            r"export\s+(?:async\s+)?function\s+(\w+)",  # Function signature
            r"export\s+interface\s+(\w+)",  # Interface definition
            r"export\s+type\s+(\w+)",  # Type definition
            r"export\s+class\s+(\w+)",  # Class definition
            r"@app\.(?:get|post|put|delete|patch)\(",  # Flask/FastAPI routes
            r"router\.(?:get|post|put|delete|patch)\(",  # Express routes
        ],
        "schema_change": [
            r"CREATE\s+TABLE",
            r"ALTER\s+TABLE",
            r"DROP\s+TABLE",
            r"ADD\s+COLUMN",
            r"DROP\s+COLUMN",
            r"class\s+\w+\(.*?Model\)",  # ORM models
            r"@Entity\(",  # JPA entities
        ],
        "config_change": [
            r"process\.env\.",
            r"os\.environ",
            r"\.env",
            r"config\.",
        ],
    }

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        project_index: ProjectIndex | None = None,
        context: ContextWindow | None = None,
    ):
        self.project_dir = project_dir.resolve()
        self.spec_dir = spec_dir
        self.project_index = project_index or load_project_index(spec_dir)
        self.context = context or load_context(spec_dir)

        # Build dependency graph
        self._dependency_graph: dict[str, DependencyNode] = {}

    def analyze(self, requirements: Requirements | None = None) -> ImpactAnalysis:
        """
        Perform comprehensive impact analysis.

        Args:
            requirements: Task requirements for additional context

        Returns:
            ImpactAnalysis with severity, affected files, and recommendations
        """
        logger.info("Starting God Mode impact analysis...")

        if not self.context:
            logger.warning("No context available, returning minimal analysis")
            return ImpactAnalysis(
                severity=ImpactSeverity.LOW,
                confidence=0.3,
                analysis_reasoning="No context available for impact analysis",
            )

        # Step 1: Build dependency graph from context
        self._build_dependency_graph()

        # Step 2: Find all affected files (direct and transitive)
        affected_files = self._find_affected_files()

        # Step 3: Find affected services
        affected_services = self._find_affected_services(affected_files)

        # Step 4: Detect potential breaking changes
        breaking_changes = self._detect_breaking_changes()

        # Step 5: Identify test coverage gaps
        test_gaps = self._identify_test_coverage_gaps()

        # Step 6: Assess rollback complexity
        rollback_complexity = self._assess_rollback_complexity(
            affected_files, breaking_changes
        )

        # Step 7: Calculate overall severity
        severity, confidence = self._calculate_severity(
            affected_files,
            affected_services,
            breaking_changes,
            test_gaps,
            rollback_complexity,
        )

        # Step 8: Generate mitigation recommendations
        mitigations = self._generate_mitigations(
            severity, breaking_changes, test_gaps, rollback_complexity
        )

        # Step 9: Build reasoning string
        reasoning = self._build_analysis_reasoning(
            affected_files,
            affected_services,
            breaking_changes,
            test_gaps,
        )

        analysis = ImpactAnalysis(
            severity=severity,
            confidence=confidence,
            affected_files=affected_files,
            affected_services=affected_services,
            breaking_changes=breaking_changes,
            test_coverage_gaps=test_gaps,
            rollback_complexity=rollback_complexity,
            recommended_mitigations=mitigations,
            analysis_reasoning=reasoning,
        )

        logger.info(
            f"Impact analysis complete: {severity.value} severity, "
            f"{len(affected_files)} affected files, "
            f"{len(breaking_changes)} breaking changes"
        )

        return analysis

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from context."""
        if not self.context:
            return

        # Add nodes for files to modify
        for file_ctx in self.context.files_to_modify:
            self._dependency_graph[file_ctx.relative_path] = DependencyNode(
                path=file_ctx.relative_path,
                exports=file_ctx.exports,
                imports=file_ctx.imports,
            )

        # Add nodes for reference files
        for file_ctx in self.context.files_to_reference:
            self._dependency_graph[file_ctx.relative_path] = DependencyNode(
                path=file_ctx.relative_path,
                exports=file_ctx.exports,
                imports=file_ctx.imports,
            )

        # Build dependency relationships
        for path, node in self._dependency_graph.items():
            for imp in node.imports:
                # Find the file this import resolves to
                resolved = self._resolve_import(imp, path)
                if resolved and resolved in self._dependency_graph:
                    node.dependencies.append(resolved)
                    self._dependency_graph[resolved].dependents.append(path)

    def _resolve_import(self, import_path: str, from_file: str) -> str | None:
        """Resolve an import path to a file path."""
        # Handle relative imports
        if import_path.startswith("."):
            from_dir = str(Path(from_file).parent)
            if import_path == ".":
                resolved = from_dir
            elif import_path == "..":
                resolved = str(Path(from_dir).parent)
            elif import_path.startswith("./"):
                resolved = f"{from_dir}/{import_path[2:]}"
            elif import_path.startswith("../"):
                resolved = str(Path(from_dir).parent / import_path[3:])
            else:
                resolved = import_path

            # Try common extensions
            for ext in [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]:
                candidate = resolved + ext
                if candidate in self._dependency_graph:
                    return candidate

        # Handle project aliases
        if import_path.startswith("@/") or import_path.startswith("~/"):
            # Common patterns: @/ -> src/, ~/ -> src/
            base = import_path[2:]
            for prefix in ["src/", ""]:
                for ext in [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]:
                    candidate = f"{prefix}{base}{ext}"
                    if candidate in self._dependency_graph:
                        return candidate

        return None

    def _find_affected_files(self) -> list[str]:
        """Find all files affected by changes (direct and transitive dependents)."""
        if not self.context:
            return []

        affected: set[str] = set()

        # Start with files being modified
        to_process = [f.relative_path for f in self.context.files_to_modify]
        affected.update(to_process)

        # Traverse dependents (files that depend on modified files)
        while to_process:
            current = to_process.pop(0)
            if current in self._dependency_graph:
                for dependent in self._dependency_graph[current].dependents:
                    if dependent not in affected:
                        affected.add(dependent)
                        to_process.append(dependent)

        return sorted(affected)

    def _find_affected_services(self, affected_files: list[str]) -> list[str]:
        """Determine which services are affected by the changes."""
        if not self.project_index:
            return []

        affected_services: set[str] = set()

        for file_path in affected_files:
            for svc_name, svc_info in self.project_index.services.items():
                if file_path.startswith(svc_info.path):
                    affected_services.add(svc_name)

        return sorted(affected_services)

    def _detect_breaking_changes(self) -> list[BreakingChange]:
        """Detect potential breaking changes in files being modified."""
        breaking_changes: list[BreakingChange] = []

        if not self.context:
            return breaking_changes

        for file_ctx in self.context.files_to_modify:
            file_path = Path(self.project_dir) / file_ctx.relative_path

            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Check for API changes
            for change_type, patterns in self.BREAKING_PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    if matches:
                        for match in matches:
                            # Find consumers of this export
                            consumers = self._find_consumers(file_ctx.relative_path, match)

                            if consumers:
                                breaking_changes.append(BreakingChange(
                                    change_type=change_type,
                                    location=f"{file_ctx.relative_path}",
                                    description=f"Potential {change_type}: {match}",
                                    affected_consumers=consumers[:10],  # Limit
                                    migration_required=change_type == "schema_change",
                                    suggested_fix=self._suggest_fix(change_type, match),
                                ))

        # Deduplicate
        seen = set()
        unique = []
        for bc in breaking_changes:
            key = (bc.change_type, bc.location, bc.description)
            if key not in seen:
                seen.add(key)
                unique.append(bc)

        return unique

    def _find_consumers(self, file_path: str, export_name: str) -> list[str]:
        """Find files that consume a specific export."""
        consumers: list[str] = []

        if file_path in self._dependency_graph:
            for dependent in self._dependency_graph[file_path].dependents:
                if dependent in self._dependency_graph:
                    dep_node = self._dependency_graph[dependent]
                    # Check if this file imports the export
                    # (Simplified - in reality would need AST analysis)
                    consumers.append(dependent)

        return consumers

    def _suggest_fix(self, change_type: str, entity_name: str) -> str | None:
        """Suggest a fix for a breaking change."""
        if change_type == "api_change":
            return (
                f"Consider adding deprecation notice before removing/changing "
                f"'{entity_name}'. Create a new version if signature changes."
            )
        elif change_type == "schema_change":
            return (
                f"Create a migration script for schema change. "
                f"Consider backward-compatible approach first."
            )
        elif change_type == "config_change":
            return (
                f"Document new configuration requirements. "
                f"Provide sensible defaults for backward compatibility."
            )
        return None

    def _identify_test_coverage_gaps(self) -> list[str]:
        """Identify files being modified that lack test coverage."""
        gaps: list[str] = []

        if not self.context:
            return gaps

        test_patterns = {"test", "spec", "__tests__"}
        related_tests = set(self.context.related_tests)

        for file_ctx in self.context.files_to_modify:
            file_path = file_ctx.relative_path

            # Skip test files themselves
            if any(p in file_path.lower() for p in test_patterns):
                continue

            # Check if there's a corresponding test file
            has_test = False
            stem = Path(file_path).stem

            for test_path in related_tests:
                if stem in test_path:
                    has_test = True
                    break

            if not has_test:
                gaps.append(file_path)

        return gaps

    def _assess_rollback_complexity(
        self,
        affected_files: list[str],
        breaking_changes: list[BreakingChange],
    ) -> str:
        """Assess how complex it would be to rollback changes."""
        # Simple heuristics
        if any(bc.migration_required for bc in breaking_changes):
            return "high"

        if len(affected_files) > 20:
            return "high"

        if len(affected_files) > 10:
            return "medium"

        if len(breaking_changes) > 3:
            return "medium"

        return "low"

    def _calculate_severity(
        self,
        affected_files: list[str],
        affected_services: list[str],
        breaking_changes: list[BreakingChange],
        test_gaps: list[str],
        rollback_complexity: str,
    ) -> tuple[ImpactSeverity, float]:
        """Calculate overall impact severity and confidence."""
        score = 0
        confidence = 0.7

        # Affected files score
        if len(affected_files) > 30:
            score += 4
        elif len(affected_files) > 15:
            score += 3
        elif len(affected_files) > 5:
            score += 2
        elif len(affected_files) > 0:
            score += 1

        # Affected services score
        if len(affected_services) > 3:
            score += 3
        elif len(affected_services) > 1:
            score += 2
        elif len(affected_services) == 1:
            score += 1

        # Breaking changes score
        if any(bc.migration_required for bc in breaking_changes):
            score += 4
        elif len(breaking_changes) > 5:
            score += 3
        elif len(breaking_changes) > 2:
            score += 2
        elif len(breaking_changes) > 0:
            score += 1

        # Test gaps score
        if len(test_gaps) > 5:
            score += 2
        elif len(test_gaps) > 2:
            score += 1

        # Rollback complexity score
        if rollback_complexity == "high":
            score += 2
        elif rollback_complexity == "medium":
            score += 1

        # Map score to severity
        if score >= 10:
            return ImpactSeverity.CRITICAL, confidence
        elif score >= 7:
            return ImpactSeverity.HIGH, confidence
        elif score >= 4:
            return ImpactSeverity.MEDIUM, confidence
        elif score >= 1:
            return ImpactSeverity.LOW, confidence
        else:
            return ImpactSeverity.NONE, confidence

    def _generate_mitigations(
        self,
        severity: ImpactSeverity,
        breaking_changes: list[BreakingChange],
        test_gaps: list[str],
        rollback_complexity: str,
    ) -> list[str]:
        """Generate recommended mitigations based on analysis."""
        mitigations: list[str] = []

        if severity in (ImpactSeverity.HIGH, ImpactSeverity.CRITICAL):
            mitigations.append("Create a detailed rollback plan before implementation")
            mitigations.append("Consider implementing changes in phases")

        if test_gaps:
            mitigations.append(f"Add tests for {len(test_gaps)} uncovered file(s): {', '.join(test_gaps[:3])}")

        if any(bc.migration_required for bc in breaking_changes):
            mitigations.append("Create database migration scripts with rollback support")
            mitigations.append("Schedule deployment during low-traffic period")

        if len(breaking_changes) > 0:
            mitigations.append("Notify affected teams of API changes")
            mitigations.append("Consider versioning for backward compatibility")

        if rollback_complexity == "high":
            mitigations.append("Implement feature flags for gradual rollout")
            mitigations.append("Set up monitoring alerts for quick issue detection")

        return mitigations

    def _build_analysis_reasoning(
        self,
        affected_files: list[str],
        affected_services: list[str],
        breaking_changes: list[BreakingChange],
        test_gaps: list[str],
    ) -> str:
        """Build human-readable analysis reasoning."""
        parts: list[str] = []

        parts.append(f"Analyzed {len(self.context.files_to_modify if self.context else 0)} files to modify.")

        if affected_files:
            parts.append(f"{len(affected_files)} files affected by transitive dependencies.")

        if affected_services:
            parts.append(f"Services affected: {', '.join(affected_services)}.")

        if breaking_changes:
            types = set(bc.change_type for bc in breaking_changes)
            parts.append(f"Detected {len(breaking_changes)} potential breaking changes ({', '.join(types)}).")

        if test_gaps:
            parts.append(f"{len(test_gaps)} file(s) lack test coverage.")

        return " ".join(parts)


def run_impact_analysis(
    project_dir: Path,
    spec_dir: Path,
    requirements: Requirements | None = None,
) -> PhaseResult:
    """
    Run impact analysis phase (God Mode).

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        requirements: Task requirements

    Returns:
        PhaseResult indicating success or failure
    """
    impact_path = spec_dir / "impact_analysis.json"

    # Check for existing analysis
    if impact_path.exists():
        return PhaseResult(
            phase_name="impact_analysis",
            status=PhaseStatus.COMPLETED,
            output_files=[str(impact_path)],
            metadata={"cached": True},
        )

    try:
        analyzer = ImpactAnalyzer(project_dir, spec_dir)
        analysis = analyzer.analyze(requirements)

        # Save analysis
        spec_dir.mkdir(parents=True, exist_ok=True)
        with open(impact_path, "w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, indent=2)

        return PhaseResult(
            phase_name="impact_analysis",
            status=PhaseStatus.COMPLETED,
            output_files=[str(impact_path)],
            metadata={
                "severity": analysis.severity.value,
                "affected_files": len(analysis.affected_files),
                "breaking_changes": len(analysis.breaking_changes),
                "requires_migration": analysis.requires_migration_plan(),
            },
        )

    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        return PhaseResult(
            phase_name="impact_analysis",
            status=PhaseStatus.FAILED,
            errors=[str(e)],
        )


def load_impact_analysis(spec_dir: Path) -> ImpactAnalysis | None:
    """Load impact analysis from spec directory."""
    impact_path = spec_dir / "impact_analysis.json"
    if not impact_path.exists():
        return None

    try:
        with open(impact_path, encoding="utf-8") as f:
            data = json.load(f)

        breaking_changes = [
            BreakingChange(**bc) for bc in data.get("breaking_changes", [])
        ]

        return ImpactAnalysis(
            severity=ImpactSeverity(data.get("severity", "low")),
            confidence=data.get("confidence", 0.7),
            affected_files=data.get("affected_files", []),
            affected_services=data.get("affected_services", []),
            breaking_changes=breaking_changes,
            test_coverage_gaps=data.get("test_coverage_gaps", []),
            rollback_complexity=data.get("rollback_complexity", "low"),
            recommended_mitigations=data.get("recommended_mitigations", []),
            analysis_reasoning=data.get("analysis_reasoning", ""),
        )

    except Exception as e:
        logger.error(f"Failed to load impact analysis: {e}")
        return None
