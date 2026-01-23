"""
Skill loader and registry for Claude God Code.

Part of Claude God Code - Autonomous Excellence

This module provides the infrastructure for loading, validating, and
managing skills. Skills are modular packages that enhance agent capabilities
with domain-specific knowledge and protocols.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """Categories of skills."""

    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    DEVOPS = "devops"
    TESTING = "testing"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    DESIGN = "design"


class SkillApplicability(Enum):
    """When a skill should be applied."""

    ALWAYS = "always"
    FRONTEND_TASKS = "frontend_tasks"
    BACKEND_TASKS = "backend_tasks"
    UI_COMPONENTS = "ui_components"
    API_DESIGN = "api_design"
    ON_DEMAND = "on_demand"


@dataclass
class SkillMetadata:
    """Metadata about a skill."""

    name: str
    version: str
    description: str
    category: SkillCategory
    applicability: SkillApplicability
    author: str = "Claude God Code"
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "applicability": self.applicability.value,
            "author": self.author,
            "tags": self.tags,
            "dependencies": self.dependencies,
        }


@dataclass
class Skill:
    """A loaded skill with all its components."""

    metadata: SkillMetadata
    skill_content: str
    examples_content: str
    prompt_content: str
    skill_path: Path

    def get_full_prompt(self) -> str:
        """Get the complete prompt injection for this skill."""
        return self.prompt_content

    def get_context_summary(self) -> str:
        """Get a brief summary for context windows."""
        return f"[Skill: {self.metadata.name}] {self.metadata.description}"

    def matches_task(self, task_description: str, file_paths: list[str]) -> bool:
        """Determine if this skill should be applied to a task."""
        task_lower = task_description.lower()

        # Check applicability rules
        if self.metadata.applicability == SkillApplicability.ALWAYS:
            return True

        if self.metadata.applicability == SkillApplicability.FRONTEND_TASKS:
            frontend_keywords = [
                "frontend", "ui", "component", "react", "vue", "angular",
                "css", "style", "tailwind", "button", "form", "modal",
                "layout", "responsive", "design", "interface"
            ]
            if any(kw in task_lower for kw in frontend_keywords):
                return True

            # Check file extensions
            frontend_extensions = {".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss", ".html"}
            if any(Path(p).suffix in frontend_extensions for p in file_paths):
                return True

        if self.metadata.applicability == SkillApplicability.UI_COMPONENTS:
            ui_keywords = [
                "button", "card", "form", "input", "modal", "dialog",
                "navbar", "sidebar", "header", "footer", "table", "list",
                "dropdown", "menu", "tab", "accordion", "tooltip"
            ]
            return any(kw in task_lower for kw in ui_keywords)

        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metadata": self.metadata.to_dict(),
            "skill_path": str(self.skill_path),
            "has_examples": bool(self.examples_content),
            "has_prompt": bool(self.prompt_content),
        }


class SkillLoader:
    """Loads skills from the filesystem."""

    def __init__(self, skills_root: Optional[Path] = None) -> None:
        """Initialize skill loader."""
        if skills_root is None:
            skills_root = Path(__file__).parent
        self.skills_root = skills_root

    def load_skill(self, skill_name: str) -> Optional[Skill]:
        """Load a skill by name."""
        skill_dir = self.skills_root / skill_name

        if not skill_dir.exists():
            logger.warning(f"Skill directory not found: {skill_dir}")
            return None

        try:
            # Load required files
            skill_file = skill_dir / "SKILL.md"
            examples_file = skill_dir / "EXAMPLES.md"
            prompt_file = skill_dir / "PROMPT.md"

            skill_content = self._read_file(skill_file)
            examples_content = self._read_file(examples_file)
            prompt_content = self._read_file(prompt_file)

            if not skill_content:
                logger.error(f"SKILL.md not found for skill: {skill_name}")
                return None

            # Parse metadata from skill content
            metadata = self._parse_metadata(skill_name, skill_content)

            return Skill(
                metadata=metadata,
                skill_content=skill_content,
                examples_content=examples_content,
                prompt_content=prompt_content,
                skill_path=skill_dir,
            )

        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")
            return None

    def _read_file(self, path: Path) -> str:
        """Read file content, return empty string if not found."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _parse_metadata(self, skill_name: str, content: str) -> SkillMetadata:
        """Parse metadata from skill content."""
        # Default metadata
        metadata = SkillMetadata(
            name=skill_name,
            version="1.0.0",
            description="",
            category=SkillCategory.DESIGN,
            applicability=SkillApplicability.ON_DEMAND,
        )

        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            if line.startswith("# "):
                # Use first heading as description
                if not metadata.description:
                    metadata.description = line[2:].strip()

            elif line.startswith("**Version:**"):
                metadata.version = line.replace("**Version:**", "").strip()

            elif line.startswith("**Category:**"):
                cat_str = line.replace("**Category:**", "").strip().lower()
                try:
                    metadata.category = SkillCategory(cat_str)
                except ValueError:
                    pass

            elif line.startswith("**Applicability:**"):
                app_str = line.replace("**Applicability:**", "").strip().lower().replace(" ", "_")
                try:
                    metadata.applicability = SkillApplicability(app_str)
                except ValueError:
                    pass

            elif line.startswith("**Tags:**"):
                tags_str = line.replace("**Tags:**", "").strip()
                metadata.tags = [t.strip() for t in tags_str.split(",")]

        return metadata

    def discover_skills(self) -> list[str]:
        """Discover all available skills."""
        skills = []

        for item in self.skills_root.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skills.append(item.name)

        return skills


class SkillRegistry:
    """Registry for managing loaded skills."""

    def __init__(self, loader: Optional[SkillLoader] = None) -> None:
        """Initialize skill registry."""
        self.loader = loader or SkillLoader()
        self._skills: dict[str, Skill] = {}
        self._loaded = False

    def load_all(self) -> None:
        """Load all available skills."""
        if self._loaded:
            return

        skill_names = self.loader.discover_skills()

        for name in skill_names:
            skill = self.loader.load_skill(name)
            if skill:
                self._skills[name] = skill
                logger.info(f"Loaded skill: {name}")

        self._loaded = True

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        if name not in self._skills:
            skill = self.loader.load_skill(name)
            if skill:
                self._skills[name] = skill

        return self._skills.get(name)

    def get_applicable_skills(
        self,
        task_description: str,
        file_paths: Optional[list[str]] = None,
    ) -> list[Skill]:
        """Get all skills applicable to a task."""
        self.load_all()

        file_paths = file_paths or []
        applicable = []

        for skill in self._skills.values():
            if skill.matches_task(task_description, file_paths):
                applicable.append(skill)

        return applicable

    def get_combined_prompt(
        self,
        task_description: str,
        file_paths: Optional[list[str]] = None,
    ) -> str:
        """Get combined prompt from all applicable skills."""
        skills = self.get_applicable_skills(task_description, file_paths)

        if not skills:
            return ""

        parts = []
        parts.append("# Active Skills Protocol")
        parts.append("")

        for skill in skills:
            prompt = skill.get_full_prompt()
            if prompt:
                parts.append(f"## {skill.metadata.name}")
                parts.append(prompt)
                parts.append("")

        return "\n".join(parts)

    def list_skills(self) -> list[SkillMetadata]:
        """List metadata for all skills."""
        self.load_all()
        return [s.metadata for s in self._skills.values()]
