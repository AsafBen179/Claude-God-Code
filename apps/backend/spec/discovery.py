"""
Project Discovery Module
========================

Analyzes project structure, detects tech stack, maps services and dependencies.
Creates a comprehensive project index for context resolution.

Part of Claude God Code - Autonomous Excellence
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from spec.models import (
    PhaseResult,
    PhaseStatus,
    ProjectIndex,
    ServiceInfo,
)

logger = logging.getLogger(__name__)

# File patterns to ignore during scanning
IGNORE_PATTERNS = {
    "node_modules",
    ".git",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".venv",
    "venv",
    ".env",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    "coverage",
    ".claude-god-code",
    ".auto-claude",
    ".worktrees",
    "target",  # Rust
    "vendor",  # Go
    "Pods",  # iOS
}

# Language detection patterns
LANGUAGE_PATTERNS: dict[str, list[str]] = {
    "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
    "javascript": ["*.js", "*.jsx", "*.mjs", "*.cjs"],
    "python": ["*.py", "pyproject.toml", "setup.py", "requirements.txt"],
    "rust": ["*.rs", "Cargo.toml"],
    "go": ["*.go", "go.mod"],
    "java": ["*.java", "pom.xml", "build.gradle"],
    "csharp": ["*.cs", "*.csproj", "*.sln"],
    "ruby": ["*.rb", "Gemfile"],
    "php": ["*.php", "composer.json"],
}

# Framework detection patterns
FRAMEWORK_PATTERNS: dict[str, dict[str, Any]] = {
    "react": {"files": ["package.json"], "content": ["react", "react-dom"]},
    "vue": {"files": ["package.json"], "content": ["vue"]},
    "angular": {"files": ["angular.json", "package.json"], "content": ["@angular/core"]},
    "next": {"files": ["next.config.js", "next.config.ts", "next.config.mjs"]},
    "express": {"files": ["package.json"], "content": ["express"]},
    "fastapi": {"files": ["requirements.txt", "pyproject.toml"], "content": ["fastapi"]},
    "django": {"files": ["manage.py", "requirements.txt"], "content": ["django"]},
    "flask": {"files": ["requirements.txt", "pyproject.toml"], "content": ["flask"]},
    "electron": {"files": ["package.json"], "content": ["electron"]},
    "dotnet": {"files": ["*.csproj", "*.sln"]},
    "spring": {"files": ["pom.xml", "build.gradle"], "content": ["spring"]},
}


class ProjectDiscovery:
    """
    Discovers and indexes project structure.

    Scans the project directory to build a comprehensive index including:
    - Tech stack detection (languages, frameworks)
    - Service mapping (for monorepos)
    - Dependency analysis
    - Entry point detection
    - Test directory identification
    """

    def __init__(self, project_dir: Path, max_depth: int = 10):
        self.project_dir = project_dir.resolve()
        self.max_depth = max_depth
        self._file_cache: dict[str, list[Path]] = {}

    def discover(self) -> ProjectIndex:
        """
        Run full project discovery.

        Returns:
            ProjectIndex with complete project structure information
        """
        logger.info(f"Starting project discovery for {self.project_dir}")

        # Detect project type
        project_type = self._detect_project_type()

        # Detect languages
        languages = self._detect_languages()

        # Detect frameworks
        frameworks = self._detect_frameworks()

        # Build service map (for monorepos)
        services = self._discover_services()

        # Find entry points
        entry_points = self._find_entry_points()

        # Find test directories
        test_dirs = self._find_test_directories()

        # Find config files
        config_files = self._find_config_files()

        # Parse dependencies
        deps, dev_deps = self._parse_dependencies()

        # Count files
        file_count, total_lines = self._count_files_and_lines()

        index = ProjectIndex(
            project_type=project_type,
            root_path=self.project_dir,
            tech_stack={
                "languages": languages,
                "frameworks": frameworks,
            },
            services=services,
            entry_points=entry_points,
            test_directories=test_dirs,
            config_files=config_files,
            dependencies=deps,
            dev_dependencies=dev_deps,
            file_count=file_count,
            total_lines=total_lines,
            indexed_at=datetime.now(),
        )

        logger.info(
            f"Discovery complete: {project_type}, {len(languages)} languages, "
            f"{len(services)} services, {file_count} files"
        )

        return index

    def _detect_project_type(self) -> str:
        """Detect if project is monorepo, single-service, or library."""
        # Check for monorepo indicators
        monorepo_files = ["lerna.json", "pnpm-workspace.yaml", "nx.json", "turbo.json"]
        for f in monorepo_files:
            if (self.project_dir / f).exists():
                return "monorepo"

        # Check for packages/apps directories
        if (self.project_dir / "packages").is_dir():
            return "monorepo"
        if (self.project_dir / "apps").is_dir():
            return "monorepo"

        # Check for library indicators
        if (self.project_dir / "src" / "index.ts").exists():
            return "library"
        if (self.project_dir / "lib").is_dir():
            return "library"

        return "application"

    def _detect_languages(self) -> list[str]:
        """Detect programming languages used in the project."""
        detected = set()

        for lang, patterns in LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if pattern.startswith("*"):
                    files = list(self.project_dir.rglob(pattern))
                    filtered = [f for f in files if not self._should_ignore(f)]
                    if filtered:
                        detected.add(lang)
                        break
                else:
                    if (self.project_dir / pattern).exists():
                        detected.add(lang)
                        break

        return sorted(detected)

    def _detect_frameworks(self) -> list[str]:
        """Detect frameworks used in the project."""
        detected = set()

        for framework, detection in FRAMEWORK_PATTERNS.items():
            file_patterns = detection.get("files", [])
            content_patterns = detection.get("content", [])

            for file_pattern in file_patterns:
                if file_pattern.startswith("*"):
                    files = list(self.project_dir.rglob(file_pattern))
                    if files:
                        detected.add(framework)
                        break
                else:
                    file_path = self.project_dir / file_pattern
                    if file_path.exists():
                        if content_patterns:
                            try:
                                content = file_path.read_text(encoding="utf-8")
                                if any(p in content for p in content_patterns):
                                    detected.add(framework)
                                    break
                            except Exception:
                                pass
                        else:
                            detected.add(framework)
                            break

        return sorted(detected)

    def _discover_services(self) -> dict[str, ServiceInfo]:
        """Discover services in a monorepo structure."""
        services: dict[str, ServiceInfo] = {}

        # Check common monorepo layouts
        service_dirs = []

        for subdir in ["packages", "apps", "services", "libs"]:
            check_dir = self.project_dir / subdir
            if check_dir.is_dir():
                for item in check_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        service_dirs.append(item)

        # If no monorepo structure, treat root as single service
        if not service_dirs:
            pkg_json = self.project_dir / "package.json"
            pyproject = self.project_dir / "pyproject.toml"
            cargo = self.project_dir / "Cargo.toml"

            name = self.project_dir.name
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text(encoding="utf-8"))
                    name = data.get("name", name)
                except Exception:
                    pass

            services["root"] = ServiceInfo(
                name=name,
                path=".",
                language=self._detect_primary_language(self.project_dir),
                entry_point=self._find_service_entry_point(self.project_dir),
            )
            return services

        # Process each service directory
        for svc_dir in service_dirs:
            svc_name = svc_dir.name
            language = self._detect_primary_language(svc_dir)
            entry_point = self._find_service_entry_point(svc_dir)
            deps = self._get_service_dependencies(svc_dir)

            services[svc_name] = ServiceInfo(
                name=svc_name,
                path=str(svc_dir.relative_to(self.project_dir)),
                language=language,
                entry_point=entry_point,
                dependencies=deps,
            )

        return services

    def _detect_primary_language(self, directory: Path) -> str:
        """Detect primary language for a directory."""
        counts: dict[str, int] = {}

        for lang, patterns in LANGUAGE_PATTERNS.items():
            count = 0
            for pattern in patterns:
                if pattern.startswith("*."):
                    files = list(directory.rglob(pattern))
                    count += len([f for f in files if not self._should_ignore(f)])
            counts[lang] = count

        if counts:
            return max(counts, key=lambda k: counts[k])
        return "unknown"

    def _find_service_entry_point(self, directory: Path) -> str | None:
        """Find the entry point for a service."""
        common_entry_points = [
            "src/index.ts",
            "src/index.js",
            "src/main.ts",
            "src/main.js",
            "index.ts",
            "index.js",
            "main.py",
            "app.py",
            "src/main.py",
            "src/app.py",
            "main.go",
            "cmd/main.go",
            "src/main.rs",
            "src/lib.rs",
        ]

        for ep in common_entry_points:
            if (directory / ep).exists():
                return ep

        return None

    def _get_service_dependencies(self, directory: Path) -> list[str]:
        """Get dependencies for a service."""
        deps = []

        pkg_json = directory / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps.extend(data.get("dependencies", {}).keys())
            except Exception:
                pass

        return deps[:20]  # Limit to 20 most important

    def _find_entry_points(self) -> list[str]:
        """Find all entry points in the project."""
        entry_points = []

        patterns = [
            "src/index.*",
            "src/main.*",
            "index.*",
            "main.*",
            "app.*",
            "server.*",
            "cli.*",
        ]

        for pattern in patterns:
            for ext in ["ts", "tsx", "js", "jsx", "py", "go", "rs"]:
                full_pattern = pattern.replace("*", ext)
                if (self.project_dir / full_pattern).exists():
                    entry_points.append(full_pattern)

        return entry_points

    def _find_test_directories(self) -> list[str]:
        """Find test directories."""
        test_dirs = []
        patterns = ["test", "tests", "__tests__", "spec", "specs", "e2e"]

        for pattern in patterns:
            for item in self.project_dir.rglob(pattern):
                if item.is_dir() and not self._should_ignore(item):
                    test_dirs.append(str(item.relative_to(self.project_dir)))

        return test_dirs[:10]  # Limit results

    def _find_config_files(self) -> list[str]:
        """Find configuration files."""
        config_patterns = [
            "*.config.js",
            "*.config.ts",
            "*.config.json",
            ".eslintrc*",
            ".prettierrc*",
            "tsconfig*.json",
            "package.json",
            "pyproject.toml",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            "docker-compose*.yml",
            "Dockerfile*",
            ".env.example",
        ]

        configs = []
        for pattern in config_patterns:
            for f in self.project_dir.glob(pattern):
                if f.is_file():
                    configs.append(str(f.relative_to(self.project_dir)))

        return configs

    def _parse_dependencies(self) -> tuple[dict[str, str], dict[str, str]]:
        """Parse project dependencies."""
        deps: dict[str, str] = {}
        dev_deps: dict[str, str] = {}

        # Parse package.json
        pkg_json = self.project_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps.update(data.get("dependencies", {}))
                dev_deps.update(data.get("devDependencies", {}))
            except Exception:
                pass

        # Parse pyproject.toml (simplified)
        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8")
                # Simple regex extraction
                dep_match = re.search(
                    r'\[project\]\s*dependencies\s*=\s*\[(.*?)\]',
                    content, re.DOTALL
                )
                if dep_match:
                    for line in dep_match.group(1).split("\n"):
                        line = line.strip().strip(",").strip('"').strip("'")
                        if line:
                            deps[line.split(">=")[0].split("==")[0]] = "*"
            except Exception:
                pass

        return deps, dev_deps

    def _count_files_and_lines(self) -> tuple[int, int]:
        """Count source files and total lines."""
        file_count = 0
        total_lines = 0

        source_extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".cs", ".rb", ".php"}

        for ext in source_extensions:
            for f in self.project_dir.rglob(f"*{ext}"):
                if self._should_ignore(f):
                    continue
                file_count += 1
                try:
                    total_lines += sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
                except Exception:
                    pass

        return file_count, total_lines

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        parts = path.relative_to(self.project_dir).parts
        return any(part in IGNORE_PATTERNS for part in parts)


def run_discovery(
    project_dir: Path,
    spec_dir: Path,
    force_refresh: bool = False,
) -> PhaseResult:
    """
    Run project discovery phase.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory to store results
        force_refresh: Force re-discovery even if index exists

    Returns:
        PhaseResult indicating success or failure
    """
    index_path = spec_dir / "project_index.json"
    global_index = project_dir / ".claude-god-code" / "project_index.json"

    # Check for existing index
    if not force_refresh:
        if index_path.exists():
            return PhaseResult(
                phase_name="discovery",
                status=PhaseStatus.COMPLETED,
                output_files=[str(index_path)],
                metadata={"cached": True},
            )

        if global_index.exists():
            # Copy global index to spec
            import shutil
            spec_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(global_index, index_path)
            return PhaseResult(
                phase_name="discovery",
                status=PhaseStatus.COMPLETED,
                output_files=[str(index_path)],
                metadata={"copied_from_global": True},
            )

    try:
        discovery = ProjectDiscovery(project_dir)
        index = discovery.discover()

        # Save to spec directory
        spec_dir.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index.to_dict(), f, indent=2)

        # Also save to global location
        global_index.parent.mkdir(parents=True, exist_ok=True)
        with open(global_index, "w", encoding="utf-8") as f:
            json.dump(index.to_dict(), f, indent=2)

        return PhaseResult(
            phase_name="discovery",
            status=PhaseStatus.COMPLETED,
            output_files=[str(index_path)],
            metadata={
                "file_count": index.file_count,
                "project_type": index.project_type,
                "languages": index.tech_stack.get("languages", []),
            },
        )

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return PhaseResult(
            phase_name="discovery",
            status=PhaseStatus.FAILED,
            errors=[str(e)],
        )


def load_project_index(spec_dir: Path) -> ProjectIndex | None:
    """Load project index from spec directory."""
    index_path = spec_dir / "project_index.json"
    if not index_path.exists():
        return None

    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        return ProjectIndex.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to load project index: {e}")
        return None


def get_project_stats(spec_dir: Path) -> dict[str, Any]:
    """Get statistics from project index."""
    index = load_project_index(spec_dir)
    if not index:
        return {}

    return {
        "file_count": index.file_count,
        "total_lines": index.total_lines,
        "project_type": index.project_type,
        "languages": index.tech_stack.get("languages", []),
        "frameworks": index.tech_stack.get("frameworks", []),
        "service_count": len(index.services),
    }
