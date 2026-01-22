"""
Context Resolution Module
=========================

Builds high-fidelity context windows using the Three-Layer Memory architecture:
1. Context Cache (in-memory) - Active session data
2. Session Memory (file-based) - Per-session patterns and gotchas
3. Knowledge Graph (Graphiti) - Long-term cross-project learnings

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
    ContextWindow,
    FileContext,
    MemoryInsight,
    PhaseResult,
    PhaseStatus,
    ProjectIndex,
)
from spec.discovery import load_project_index

logger = logging.getLogger(__name__)

# File extensions to consider for context
SOURCE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".pyi",
    ".go",
    ".rs",
    ".java", ".kt",
    ".cs",
    ".rb",
    ".php",
    ".vue", ".svelte",
}

# Maximum context size in bytes (to avoid overwhelming the agent)
MAX_CONTEXT_BYTES = 500_000  # 500KB


class ContextResolver:
    """
    Resolves relevant context for a task using three-layer memory.

    Architecture:
    - Layer 1: Context Cache - In-memory relevance-scored file list
    - Layer 2: Session Memory - File-based patterns, gotchas, codebase map
    - Layer 3: Knowledge Graph - Graphiti long-term memory (if available)
    """

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        project_index: ProjectIndex | None = None,
    ):
        self.project_dir = project_dir.resolve()
        self.spec_dir = spec_dir
        self.project_index = project_index or load_project_index(spec_dir)

        # Layer 1: Context cache (in-memory)
        self._context_cache: dict[str, FileContext] = {}

        # Layer 2: Session memory paths
        self._memory_dir = spec_dir / "memory"
        self._patterns_file = self._memory_dir / "patterns.json"
        self._gotchas_file = self._memory_dir / "gotchas.json"
        self._codebase_map_file = self._memory_dir / "codebase_map.json"

    def resolve(
        self,
        task_description: str,
        services: list[str] | None = None,
        max_files: int = 50,
    ) -> ContextWindow:
        """
        Resolve context for a task.

        Args:
            task_description: Description of the task
            services: List of services involved (for monorepos)
            max_files: Maximum number of files to include

        Returns:
            ContextWindow with relevant files and memory insights
        """
        logger.info(f"Resolving context for task: {task_description[:100]}...")

        services = services or []

        # Step 1: Extract keywords and concepts from task
        keywords = self._extract_keywords(task_description)
        logger.debug(f"Extracted keywords: {keywords}")

        # Step 2: Find candidate files
        candidates = self._find_candidate_files(keywords, services)
        logger.debug(f"Found {len(candidates)} candidate files")

        # Step 3: Score files by relevance
        scored_files = self._score_files(candidates, keywords, task_description)

        # Step 4: Select top files respecting size limits
        files_to_modify, files_to_reference = self._select_files(
            scored_files, max_files
        )

        # Step 5: Find related tests
        related_tests = self._find_related_tests(files_to_modify)

        # Step 6: Build dependency graph
        dependency_graph = self._build_dependency_graph(files_to_modify)

        # Step 7: Gather memory insights (three-layer memory)
        memory_insights = self._gather_memory_insights(task_description, keywords)

        context = ContextWindow(
            task_description=task_description,
            scoped_services=services,
            files_to_modify=files_to_modify,
            files_to_reference=files_to_reference,
            related_tests=related_tests,
            memory_insights=memory_insights,
            dependency_graph=dependency_graph,
            created_at=datetime.now(),
        )

        logger.info(
            f"Context resolved: {len(files_to_modify)} files to modify, "
            f"{len(files_to_reference)} reference files, {len(memory_insights)} insights"
        )

        return context

    def _extract_keywords(self, task_description: str) -> list[str]:
        """Extract relevant keywords from task description."""
        # Normalize text
        text = task_description.lower()

        # Remove common words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too",
            "very", "just", "also", "now", "and", "but", "or", "if", "because",
            "this", "that", "these", "those", "it", "its", "i", "me", "my",
            "we", "our", "you", "your", "he", "him", "his", "she", "her",
            "they", "them", "their", "what", "which", "who", "whom",
            "add", "create", "make", "implement", "fix", "update", "change",
            "need", "want", "like", "please", "help",
        }

        # Extract words
        words = re.findall(r'\b[a-z][a-z0-9_-]{2,}\b', text)
        keywords = [w for w in words if w not in stop_words]

        # Also extract camelCase/PascalCase identifiers
        camel_matches = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', task_description)
        for match in camel_matches:
            # Split camelCase into words
            parts = re.findall(r'[A-Z][a-z]+', match)
            keywords.extend([p.lower() for p in parts])

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:30]  # Limit to 30 keywords

    def _find_candidate_files(
        self,
        keywords: list[str],
        services: list[str],
    ) -> list[Path]:
        """Find candidate files based on keywords and services."""
        candidates: set[Path] = set()

        # If services specified, limit to those directories
        search_dirs = [self.project_dir]
        if services and self.project_index:
            search_dirs = []
            for svc_name in services:
                if svc_name in self.project_index.services:
                    svc = self.project_index.services[svc_name]
                    search_dirs.append(self.project_dir / svc.path)

        # Search for files matching keywords
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for ext in SOURCE_EXTENSIONS:
                for f in search_dir.rglob(f"*{ext}"):
                    if self._should_ignore(f):
                        continue

                    # Check if filename contains keywords
                    fname = f.stem.lower()
                    if any(kw in fname for kw in keywords):
                        candidates.add(f)
                        continue

                    # Check file content for keyword matches (limited)
                    if len(candidates) < 200:  # Don't scan too many files
                        try:
                            content = f.read_text(encoding="utf-8", errors="ignore")[:5000]
                            content_lower = content.lower()
                            if sum(1 for kw in keywords if kw in content_lower) >= 2:
                                candidates.add(f)
                        except Exception:
                            pass

        return list(candidates)

    def _score_files(
        self,
        candidates: list[Path],
        keywords: list[str],
        task_description: str,
    ) -> list[tuple[Path, float, str | None]]:
        """
        Score candidate files by relevance.

        Returns list of (path, score, modification_reason) tuples.
        """
        scored: list[tuple[Path, float, str | None]] = []

        task_lower = task_description.lower()

        for path in candidates:
            score = 0.0
            reason = None

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            content_lower = content.lower()
            fname = path.stem.lower()

            # Filename match (high weight)
            filename_matches = sum(1 for kw in keywords if kw in fname)
            score += filename_matches * 10

            # Content keyword matches
            content_matches = sum(1 for kw in keywords if kw in content_lower)
            score += content_matches * 2

            # File type bonuses
            if path.suffix in {".ts", ".tsx", ".py"}:
                score += 5  # Prefer TypeScript/Python

            # Entry point bonus
            if path.name in {"index.ts", "index.js", "main.py", "app.py"}:
                score += 8

            # Test file handling
            if "test" in fname or "spec" in fname:
                score *= 0.5  # Lower priority for test files in modify list

            # Determine if file should be modified
            if "fix" in task_lower or "update" in task_lower or "change" in task_lower:
                if filename_matches > 0:
                    reason = f"Likely modification target (matches: {', '.join(kw for kw in keywords if kw in fname)})"

            # Check for specific patterns in task
            if "component" in task_lower and path.suffix in {".tsx", ".vue", ".svelte"}:
                score += 10
                reason = "Component file matching task"

            if "api" in task_lower and ("api" in fname or "route" in fname or "controller" in fname):
                score += 10
                reason = "API-related file"

            if "database" in task_lower and ("model" in fname or "schema" in fname or "migration" in fname):
                score += 10
                reason = "Database-related file"

            if score > 0:
                scored.append((path, score, reason))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _select_files(
        self,
        scored_files: list[tuple[Path, float, str | None]],
        max_files: int,
    ) -> tuple[list[FileContext], list[FileContext]]:
        """Select files respecting count and size limits."""
        files_to_modify: list[FileContext] = []
        files_to_reference: list[FileContext] = []
        total_size = 0

        for path, score, reason in scored_files:
            if len(files_to_modify) + len(files_to_reference) >= max_files:
                break

            if total_size >= MAX_CONTEXT_BYTES:
                break

            try:
                stat = path.stat()
                file_size = stat.st_size

                # Skip files that are too large
                if file_size > 100_000:  # 100KB
                    continue

                content = path.read_text(encoding="utf-8", errors="ignore")
                line_count = content.count("\n") + 1

                # Parse imports/exports (simplified)
                imports = self._extract_imports(content, path.suffix)
                exports = self._extract_exports(content, path.suffix)

                file_ctx = FileContext(
                    path=str(path),
                    relative_path=str(path.relative_to(self.project_dir)),
                    language=self._detect_language(path.suffix),
                    size_bytes=file_size,
                    line_count=line_count,
                    imports=imports,
                    exports=exports,
                    relevance_score=score,
                    modification_reason=reason,
                )

                # Files with modification reason go to modify list
                if reason:
                    files_to_modify.append(file_ctx)
                else:
                    files_to_reference.append(file_ctx)

                total_size += file_size

            except Exception as e:
                logger.debug(f"Error processing {path}: {e}")
                continue

        return files_to_modify, files_to_reference

    def _find_related_tests(self, files_to_modify: list[FileContext]) -> list[str]:
        """Find test files related to files being modified."""
        related_tests: list[str] = []

        for file_ctx in files_to_modify:
            path = Path(file_ctx.path)
            stem = path.stem

            # Common test file patterns
            test_patterns = [
                f"{stem}.test.*",
                f"{stem}.spec.*",
                f"test_{stem}.*",
                f"{stem}_test.*",
            ]

            for pattern in test_patterns:
                for test_file in self.project_dir.rglob(pattern):
                    if test_file.suffix in SOURCE_EXTENSIONS:
                        related_tests.append(str(test_file.relative_to(self.project_dir)))

        return list(set(related_tests))[:20]  # Limit and dedupe

    def _build_dependency_graph(
        self,
        files: list[FileContext],
    ) -> dict[str, list[str]]:
        """Build dependency graph for selected files."""
        graph: dict[str, list[str]] = {}

        for file_ctx in files:
            deps = []
            for imp in file_ctx.imports:
                # Resolve relative imports
                if imp.startswith("."):
                    # Relative import - resolve to path
                    deps.append(imp)
                elif imp.startswith("@/") or imp.startswith("~/"):
                    # Project alias
                    deps.append(imp)
                # Skip external package imports

            if deps:
                graph[file_ctx.relative_path] = deps

        return graph

    def _gather_memory_insights(
        self,
        task_description: str,
        keywords: list[str],
    ) -> list[MemoryInsight]:
        """
        Gather insights from three-layer memory system.

        Layer 1: Context Cache (in-memory) - Already in _context_cache
        Layer 2: Session Memory (file-based) - patterns.json, gotchas.json
        Layer 3: Knowledge Graph (Graphiti) - Long-term memory
        """
        insights: list[MemoryInsight] = []

        # Layer 2: Load session memory
        insights.extend(self._load_session_memory_insights(keywords))

        # Layer 3: Query knowledge graph (if available)
        insights.extend(self._query_knowledge_graph(task_description, keywords))

        # Sort by relevance
        insights.sort(key=lambda x: x.relevance_score, reverse=True)

        return insights[:10]  # Limit to top 10 insights

    def _load_session_memory_insights(self, keywords: list[str]) -> list[MemoryInsight]:
        """Load relevant insights from session memory files."""
        insights: list[MemoryInsight] = []

        # Load patterns
        if self._patterns_file.exists():
            try:
                with open(self._patterns_file, encoding="utf-8") as f:
                    patterns = json.load(f)

                for pattern in patterns.get("patterns", []):
                    content = pattern.get("description", "")
                    relevance = self._calculate_relevance(content, keywords)
                    if relevance > 0.3:
                        insights.append(MemoryInsight(
                            insight_type="pattern",
                            content=content,
                            source="file-based",
                            relevance_score=relevance,
                            metadata=pattern,
                        ))
            except Exception as e:
                logger.debug(f"Failed to load patterns: {e}")

        # Load gotchas
        if self._gotchas_file.exists():
            try:
                with open(self._gotchas_file, encoding="utf-8") as f:
                    gotchas = json.load(f)

                for gotcha in gotchas.get("gotchas", []):
                    content = gotcha.get("description", "")
                    relevance = self._calculate_relevance(content, keywords)
                    if relevance > 0.3:
                        insights.append(MemoryInsight(
                            insight_type="gotcha",
                            content=content,
                            source="file-based",
                            relevance_score=relevance,
                            metadata=gotcha,
                        ))
            except Exception as e:
                logger.debug(f"Failed to load gotchas: {e}")

        return insights

    def _query_knowledge_graph(
        self,
        task_description: str,
        keywords: list[str],
    ) -> list[MemoryInsight]:
        """Query knowledge graph for relevant insights."""
        insights: list[MemoryInsight] = []

        # Check if Graphiti is available
        try:
            from core.platform import is_python_312_or_higher
            if not is_python_312_or_higher():
                return insights

            # TODO: Implement Graphiti integration
            # This would query the knowledge graph for relevant episodes
            # For now, return empty list
            pass

        except ImportError:
            pass

        return insights

    def _calculate_relevance(self, content: str, keywords: list[str]) -> float:
        """Calculate relevance score based on keyword overlap."""
        if not content or not keywords:
            return 0.0

        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)

        return min(1.0, matches / len(keywords))

    def _extract_imports(self, content: str, suffix: str) -> list[str]:
        """Extract import statements from file content."""
        imports: list[str] = []

        if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
            # ES6 imports
            matches = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
            imports.extend(matches)
            # Dynamic imports
            matches = re.findall(r'import\([\'"]([^\'"]+)[\'"]\)', content)
            imports.extend(matches)

        elif suffix == ".py":
            # Python imports
            matches = re.findall(r'^(?:from\s+(\S+)\s+)?import', content, re.MULTILINE)
            imports.extend([m for m in matches if m])

        elif suffix == ".go":
            # Go imports
            matches = re.findall(r'import\s+["\']([^"\']+)["\']', content)
            imports.extend(matches)

        return imports[:20]  # Limit

    def _extract_exports(self, content: str, suffix: str) -> list[str]:
        """Extract export statements from file content."""
        exports: list[str] = []

        if suffix in {".ts", ".tsx", ".js", ".jsx"}:
            # Named exports
            matches = re.findall(r'export\s+(?:const|let|var|function|class|interface|type|enum)\s+(\w+)', content)
            exports.extend(matches)
            # Default export
            if re.search(r'export\s+default', content):
                exports.append("default")

        elif suffix == ".py":
            # Python __all__
            match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                names = re.findall(r'[\'"](\w+)[\'"]', match.group(1))
                exports.extend(names)

        return exports[:20]  # Limit

    def _detect_language(self, suffix: str) -> str:
        """Detect language from file suffix."""
        mapping = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".py": "python",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".vue": "vue",
            ".svelte": "svelte",
        }
        return mapping.get(suffix, "unknown")

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", "out", ".next", ".nuxt", "coverage",
            ".claude-god-code", ".auto-claude", ".worktrees",
        }
        parts = path.relative_to(self.project_dir).parts
        return any(part in ignore_patterns for part in parts)


def run_context_discovery(
    project_dir: Path,
    spec_dir: Path,
    task_description: str,
    services: list[str] | None = None,
) -> PhaseResult:
    """
    Run context discovery phase.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        task_description: Task description
        services: List of services involved

    Returns:
        PhaseResult indicating success or failure
    """
    context_path = spec_dir / "context.json"

    # Check for existing context
    if context_path.exists():
        return PhaseResult(
            phase_name="context",
            status=PhaseStatus.COMPLETED,
            output_files=[str(context_path)],
            metadata={"cached": True},
        )

    try:
        resolver = ContextResolver(project_dir, spec_dir)
        context = resolver.resolve(task_description, services)

        # Save context
        spec_dir.mkdir(parents=True, exist_ok=True)
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context.to_dict(), f, indent=2)

        return PhaseResult(
            phase_name="context",
            status=PhaseStatus.COMPLETED,
            output_files=[str(context_path)],
            metadata={
                "files_to_modify": len(context.files_to_modify),
                "files_to_reference": len(context.files_to_reference),
                "memory_insights": len(context.memory_insights),
            },
        )

    except Exception as e:
        logger.error(f"Context discovery failed: {e}")
        return PhaseResult(
            phase_name="context",
            status=PhaseStatus.FAILED,
            errors=[str(e)],
        )


def load_context(spec_dir: Path) -> ContextWindow | None:
    """Load context from spec directory."""
    context_path = spec_dir / "context.json"
    if not context_path.exists():
        return None

    try:
        with open(context_path, encoding="utf-8") as f:
            data = json.load(f)

        files_to_modify = [
            FileContext(**fd) for fd in data.get("files_to_modify", [])
        ]
        files_to_reference = [
            FileContext(**fd) for fd in data.get("files_to_reference", [])
        ]
        memory_insights = [
            MemoryInsight(**mi) for mi in data.get("memory_insights", [])
        ]

        return ContextWindow(
            task_description=data.get("task_description", ""),
            scoped_services=data.get("scoped_services", []),
            files_to_modify=files_to_modify,
            files_to_reference=files_to_reference,
            related_tests=data.get("related_tests", []),
            memory_insights=memory_insights,
            dependency_graph=data.get("dependency_graph", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
        )

    except Exception as e:
        logger.error(f"Failed to load context: {e}")
        return None


def get_context_stats(spec_dir: Path) -> dict[str, Any]:
    """Get statistics from context file."""
    context = load_context(spec_dir)
    if not context:
        return {}

    return {
        "files_to_modify": len(context.files_to_modify),
        "files_to_reference": len(context.files_to_reference),
        "related_tests": len(context.related_tests),
        "memory_insights": len(context.memory_insights),
        "total_context_size": context.get_total_context_size(),
    }
