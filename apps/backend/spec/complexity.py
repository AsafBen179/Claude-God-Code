"""
Complexity Assessment Module
============================

AI and heuristic-based task complexity analysis.
Determines which phases should run based on task scope.

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from spec.models import (
    Complexity,
    ComplexityAssessment,
    PhaseResult,
    PhaseStatus,
    ProjectIndex,
    Requirements,
)
from spec.discovery import load_project_index

logger = logging.getLogger(__name__)


class ComplexityAnalyzer:
    """
    Analyzes task description and context to determine complexity.

    Uses both heuristic analysis and optional AI assessment.
    """

    # Keywords that suggest different complexity levels
    SIMPLE_KEYWORDS = [
        "fix", "typo", "update", "change", "rename", "remove", "delete",
        "adjust", "tweak", "correct", "modify", "style", "color", "text",
        "label", "button", "margin", "padding", "font", "size", "hide", "show",
        "comment", "readme", "docs", "documentation",
    ]

    STANDARD_KEYWORDS = [
        "add", "create", "implement", "feature", "component", "page", "form",
        "validation", "handler", "endpoint", "route", "service", "helper",
        "utility", "hook", "context", "state", "store",
    ]

    COMPLEX_KEYWORDS = [
        "integrate", "integration", "api", "sdk", "library", "package",
        "database", "migrate", "migration", "docker", "kubernetes", "deploy",
        "authentication", "oauth", "graphql", "websocket", "queue", "cache",
        "redis", "postgres", "mongo", "elasticsearch", "kafka", "rabbitmq",
        "microservice", "refactor", "architecture", "infrastructure",
        "performance", "optimization", "security", "encryption",
    ]

    CRITICAL_KEYWORDS = [
        "breaking", "major", "migration", "schema", "rollback", "downtime",
        "production", "critical", "urgent", "emergency", "security", "vulnerability",
        "data loss", "corruption", "recovery",
    ]

    MULTI_SERVICE_KEYWORDS = [
        "backend", "frontend", "worker", "service", "api", "client", "server",
        "database", "queue", "cache", "proxy", "gateway", "microservice",
    ]

    def __init__(self, project_index: ProjectIndex | None = None):
        self.project_index = project_index

    def analyze(
        self,
        task_description: str,
        requirements: Requirements | None = None,
    ) -> ComplexityAssessment:
        """
        Analyze task and return complexity assessment.

        Args:
            task_description: Description of the task
            requirements: Optional requirements for additional context

        Returns:
            ComplexityAssessment with complexity level and signals
        """
        task_lower = task_description.lower()
        signals: dict[str, Any] = {}

        # 1. Keyword analysis
        simple_matches = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in task_lower)
        standard_matches = sum(1 for kw in self.STANDARD_KEYWORDS if kw in task_lower)
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task_lower)
        critical_matches = sum(1 for kw in self.CRITICAL_KEYWORDS if kw in task_lower)
        multi_service_matches = sum(1 for kw in self.MULTI_SERVICE_KEYWORDS if kw in task_lower)

        signals["simple_keywords"] = simple_matches
        signals["standard_keywords"] = standard_matches
        signals["complex_keywords"] = complex_matches
        signals["critical_keywords"] = critical_matches
        signals["multi_service_keywords"] = multi_service_matches

        # 2. External integrations detection
        integrations = self._detect_integrations(task_lower)
        signals["external_integrations"] = len(integrations)

        # 3. Infrastructure changes detection
        infra_changes = self._detect_infrastructure_changes(task_lower)
        signals["infrastructure_changes"] = infra_changes

        # 4. Estimate files and services
        estimated_files = self._estimate_files(task_lower, requirements)
        estimated_services = self._estimate_services(task_lower, requirements)
        signals["estimated_files"] = estimated_files
        signals["estimated_services"] = estimated_services

        # 5. Requirements-based signals (if available)
        if requirements:
            services_involved = requirements.services_involved
            signals["explicit_services"] = len(services_involved)
            estimated_services = max(estimated_services, len(services_involved))

            # Boost complexity if many acceptance criteria
            if len(requirements.acceptance_criteria) > 5:
                signals["acceptance_criteria_count"] = len(requirements.acceptance_criteria)
                complex_matches += 1

        # 6. Determine complexity
        complexity, confidence, reasoning = self._calculate_complexity(
            signals,
            integrations,
            infra_changes,
            estimated_files,
            estimated_services,
            critical_matches,
        )

        # 7. Determine flags
        needs_research = self._needs_research(task_lower, integrations)
        needs_self_critique = complexity in (Complexity.COMPLEX, Complexity.CRITICAL)
        needs_impact_analysis = (
            estimated_files > 5
            or estimated_services > 1
            or len(integrations) > 0
            or infra_changes
        )

        return ComplexityAssessment(
            complexity=complexity,
            confidence=confidence,
            signals=signals,
            reasoning=reasoning,
            estimated_files=estimated_files,
            estimated_services=estimated_services,
            external_integrations=integrations,
            infrastructure_changes=infra_changes,
            needs_research=needs_research,
            needs_self_critique=needs_self_critique,
            needs_impact_analysis=needs_impact_analysis,
        )

    def _detect_integrations(self, task_lower: str) -> list[str]:
        """Detect external integrations mentioned in task."""
        integration_patterns = [
            (r"\b(graphiti|graphql|apollo)\b", "graphql"),
            (r"\b(stripe|paypal|payment)\b", "payment"),
            (r"\b(auth0|okta|oauth|jwt)\b", "auth"),
            (r"\b(aws|gcp|azure|s3|lambda)\b", "cloud"),
            (r"\b(redis|memcached)\b", "cache"),
            (r"\b(postgres|mysql|mongodb|database)\b", "database"),
            (r"\b(elasticsearch|algolia)\b", "search"),
            (r"\b(kafka|rabbitmq|sqs)\b", "queue"),
            (r"\b(docker|kubernetes|k8s)\b", "container"),
            (r"\b(openai|anthropic|claude|llm|ai)\b", "ai"),
            (r"\b(sendgrid|twilio)\b", "messaging"),
            (r"\b(github|gitlab|bitbucket)\b", "vcs"),
        ]

        found: set[str] = set()
        for pattern, category in integration_patterns:
            if re.search(pattern, task_lower):
                found.add(category)

        return list(found)

    def _detect_infrastructure_changes(self, task_lower: str) -> bool:
        """Detect if task involves infrastructure changes."""
        infra_patterns = [
            r"\bdocker\b",
            r"\bkubernetes\b",
            r"\bk8s\b",
            r"\bdeploy\b",
            r"\binfrastructure\b",
            r"\bci/cd\b",
            r"\benvironment\b",
            r"\bconfig\b",
            r"\b\.env\b",
            r"\bdatabase migration\b",
            r"\bschema\b",
            r"\bterraform\b",
            r"\bansible\b",
            r"\bhelm\b",
        ]

        for pattern in infra_patterns:
            if re.search(pattern, task_lower):
                return True
        return False

    def _estimate_files(
        self,
        task_lower: str,
        requirements: Requirements | None,
    ) -> int:
        """Estimate number of files to be modified."""
        # Base estimate from task description
        if any(kw in task_lower for kw in ["single", "one file", "one component", "this file"]):
            return 1

        # Check for explicit file mentions
        file_mentions = len(re.findall(r"\.(tsx?|jsx?|py|go|rs|java|rb|php|vue|svelte)\b", task_lower))
        if file_mentions > 0:
            return max(1, file_mentions)

        # Heuristic based on task scope
        if any(kw in task_lower for kw in self.SIMPLE_KEYWORDS):
            return 2
        elif any(kw in task_lower for kw in self.STANDARD_KEYWORDS):
            return 5
        elif any(kw in task_lower for kw in self.COMPLEX_KEYWORDS):
            return 15
        elif any(kw in task_lower for kw in self.CRITICAL_KEYWORDS):
            return 25

        return 5  # Default estimate

    def _estimate_services(
        self,
        task_lower: str,
        requirements: Requirements | None,
    ) -> int:
        """Estimate number of services involved."""
        service_count = sum(1 for kw in self.MULTI_SERVICE_KEYWORDS if kw in task_lower)

        # If project is a monorepo, check project_index
        if self.project_index and self.project_index.project_type == "monorepo":
            services = self.project_index.services
            if services:
                # Check which services are mentioned
                mentioned = sum(1 for svc in services if svc.lower() in task_lower)
                if mentioned > 0:
                    return mentioned

        return max(1, min(service_count, 5))

    def _needs_research(self, task_lower: str, integrations: list[str]) -> bool:
        """Determine if task needs a research phase."""
        research_triggers = [
            "investigate", "research", "explore", "analyze", "understand",
            "figure out", "find out", "determine", "evaluate", "compare",
            "best practice", "how to", "should we", "recommendation",
        ]

        if any(trigger in task_lower for trigger in research_triggers):
            return True

        # New integrations often need research
        if len(integrations) > 0:
            return True

        return False

    def _calculate_complexity(
        self,
        signals: dict[str, Any],
        integrations: list[str],
        infra_changes: bool,
        estimated_files: int,
        estimated_services: int,
        critical_matches: int,
    ) -> tuple[Complexity, float, str]:
        """Calculate final complexity based on all signals."""
        reasons: list[str] = []

        # CRITICAL indicators
        if (
            critical_matches >= 2
            or (infra_changes and estimated_services >= 3)
            or (len(integrations) >= 3 and estimated_files >= 15)
        ):
            reasons.append("Critical change detected")
            if critical_matches > 0:
                reasons.append(f"{critical_matches} critical keyword(s)")
            if infra_changes:
                reasons.append("infrastructure changes")
            return Complexity.CRITICAL, 0.85, "; ".join(reasons)

        # COMPLEX indicators
        if (
            len(integrations) >= 2
            or infra_changes
            or estimated_services >= 3
            or estimated_files >= 10
            or signals.get("complex_keywords", 0) >= 3
        ):
            reasons.append(f"{len(integrations)} integrations, {estimated_services} services, {estimated_files} files")
            if infra_changes:
                reasons.append("infrastructure changes detected")
            return Complexity.COMPLEX, 0.85, "; ".join(reasons)

        # SIMPLE indicators
        if (
            estimated_files <= 2
            and estimated_services == 1
            and len(integrations) == 0
            and not infra_changes
            and signals.get("simple_keywords", 0) > 0
            and signals.get("complex_keywords", 0) == 0
        ):
            reasons.append(f"Single service, {estimated_files} file(s), no integrations")
            return Complexity.SIMPLE, 0.9, "; ".join(reasons)

        # Default to STANDARD
        reasons.append(f"{estimated_files} files, {estimated_services} service(s)")
        if len(integrations) > 0:
            reasons.append(f"{len(integrations)} integration(s)")

        return Complexity.STANDARD, 0.75, "; ".join(reasons)


def run_complexity_assessment(
    spec_dir: Path,
    task_description: str,
    requirements: Requirements | None = None,
    override: str | None = None,
) -> PhaseResult:
    """
    Run complexity assessment phase.

    Args:
        spec_dir: Spec directory
        task_description: Task description
        requirements: Optional requirements
        override: Optional complexity override (simple, standard, complex, critical)

    Returns:
        PhaseResult indicating success or failure
    """
    assessment_path = spec_dir / "complexity_assessment.json"

    # Check for existing assessment
    if assessment_path.exists():
        return PhaseResult(
            phase_name="complexity_assessment",
            status=PhaseStatus.COMPLETED,
            output_files=[str(assessment_path)],
            metadata={"cached": True},
        )

    try:
        if override:
            # Manual override
            complexity = Complexity(override.lower())
            assessment = ComplexityAssessment(
                complexity=complexity,
                confidence=1.0,
                reasoning=f"Manual override: {override}",
            )
        else:
            # Run heuristic assessment
            project_index = load_project_index(spec_dir)
            analyzer = ComplexityAnalyzer(project_index)
            assessment = analyzer.analyze(task_description, requirements)

        # Save assessment
        save_assessment(spec_dir, assessment)

        return PhaseResult(
            phase_name="complexity_assessment",
            status=PhaseStatus.COMPLETED,
            output_files=[str(assessment_path)],
            metadata={
                "complexity": assessment.complexity.value,
                "confidence": assessment.confidence,
                "estimated_files": assessment.estimated_files,
                "phases_to_run": assessment.phases_to_run(),
            },
        )

    except Exception as e:
        logger.error(f"Complexity assessment failed: {e}")
        return PhaseResult(
            phase_name="complexity_assessment",
            status=PhaseStatus.FAILED,
            errors=[str(e)],
        )


def save_assessment(spec_dir: Path, assessment: ComplexityAssessment) -> Path:
    """Save complexity assessment to file."""
    assessment_path = spec_dir / "complexity_assessment.json"

    spec_dir.mkdir(parents=True, exist_ok=True)
    with open(assessment_path, "w", encoding="utf-8") as f:
        data = assessment.to_dict()
        data["created_at"] = datetime.now().isoformat()
        json.dump(data, f, indent=2)

    return assessment_path


def load_assessment(spec_dir: Path) -> ComplexityAssessment | None:
    """Load complexity assessment from spec directory."""
    assessment_path = spec_dir / "complexity_assessment.json"
    if not assessment_path.exists():
        return None

    try:
        with open(assessment_path, encoding="utf-8") as f:
            data = json.load(f)

        return ComplexityAssessment(
            complexity=Complexity(data.get("complexity", "standard")),
            confidence=data.get("confidence", 0.75),
            signals=data.get("signals", {}),
            reasoning=data.get("reasoning", ""),
            estimated_files=data.get("estimated_files", 5),
            estimated_services=data.get("estimated_services", 1),
            external_integrations=data.get("external_integrations", []),
            infrastructure_changes=data.get("infrastructure_changes", False),
            recommended_phases=data.get("phases_to_run", []),
            needs_research=data.get("needs_research", False),
            needs_self_critique=data.get("needs_self_critique", False),
            needs_impact_analysis=data.get("needs_impact_analysis", False),
        )

    except Exception as e:
        logger.error(f"Failed to load assessment: {e}")
        return None
