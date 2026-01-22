"""
Claude God Code - Spec Layer
============================

Specification creation pipeline with discovery, context resolution,
impact analysis, and complexity assessment.

Part of Claude God Code - Autonomous Excellence
"""

# Models
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
    Specification,
    WorkflowType,
    create_spec_dir,
    generate_spec_name,
    get_specs_dir,
)

# Discovery
from spec.discovery import (
    ProjectDiscovery,
    get_project_stats,
    load_project_index,
    run_discovery,
)

# Context
from spec.context import (
    ContextResolver,
    get_context_stats,
    load_context,
    run_context_discovery,
)

# Impact Analysis (God Mode)
from spec.impact import (
    ImpactAnalyzer,
    load_impact_analysis,
    run_impact_analysis,
)

# Complexity
from spec.complexity import (
    ComplexityAnalyzer,
    load_assessment,
    run_complexity_assessment,
    save_assessment,
)

# Pipeline
from spec.pipeline import (
    PipelineConfig,
    PipelineState,
    SpecPipeline,
    create_spec,
)

__all__ = [
    # Models
    "Complexity",
    "ComplexityAssessment",
    "ContextWindow",
    "FileContext",
    "ImpactAnalysis",
    "ImpactSeverity",
    "BreakingChange",
    "MemoryInsight",
    "PhaseResult",
    "PhaseStatus",
    "ProjectIndex",
    "Requirements",
    "ServiceInfo",
    "Specification",
    "WorkflowType",
    "create_spec_dir",
    "generate_spec_name",
    "get_specs_dir",
    # Discovery
    "ProjectDiscovery",
    "run_discovery",
    "load_project_index",
    "get_project_stats",
    # Context
    "ContextResolver",
    "run_context_discovery",
    "load_context",
    "get_context_stats",
    # Impact Analysis
    "ImpactAnalyzer",
    "run_impact_analysis",
    "load_impact_analysis",
    # Complexity
    "ComplexityAnalyzer",
    "run_complexity_assessment",
    "save_assessment",
    "load_assessment",
    # Pipeline
    "SpecPipeline",
    "PipelineConfig",
    "PipelineState",
    "create_spec",
]
