"""
Unit tests for the Skills system.

Part of Claude God Code - Autonomous Excellence

These tests verify that:
1. Skills can be loaded correctly from the filesystem
2. Skill metadata is parsed properly
3. Skills are correctly identified as applicable to tasks
4. The combined prompt generation works
5. Agent skill integration functions properly
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import shutil

from skills import Skill, SkillLoader, SkillMetadata, SkillRegistry
from skills.loader import SkillCategory, SkillApplicability


class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating skill metadata."""
        metadata = SkillMetadata(
            name="test_skill",
            version="1.0.0",
            description="A test skill",
            category=SkillCategory.FRONTEND,
            applicability=SkillApplicability.FRONTEND_TASKS,
            tags=["ui", "test"],
        )

        assert metadata.name == "test_skill"
        assert metadata.version == "1.0.0"
        assert metadata.category == SkillCategory.FRONTEND
        assert "ui" in metadata.tags

    def test_metadata_to_dict(self):
        """Test serialization to dictionary."""
        metadata = SkillMetadata(
            name="test_skill",
            version="1.0.0",
            description="Test",
            category=SkillCategory.DESIGN,
            applicability=SkillApplicability.UI_COMPONENTS,
        )

        data = metadata.to_dict()

        assert data["name"] == "test_skill"
        assert data["category"] == "design"
        assert data["applicability"] == "ui_components"


class TestSkill:
    """Tests for Skill class."""

    @pytest.fixture
    def sample_skill(self):
        """Create a sample skill for testing."""
        metadata = SkillMetadata(
            name="frontend_design",
            version="1.0.0",
            description="Professional Frontend Design",
            category=SkillCategory.DESIGN,
            applicability=SkillApplicability.FRONTEND_TASKS,
            tags=["ui", "tailwind", "accessibility"],
        )

        return Skill(
            metadata=metadata,
            skill_content="# Test Skill Content",
            examples_content="# Test Examples",
            prompt_content="# Test Prompt\nApply these standards...",
            skill_path=Path("/test/skills/frontend_design"),
        )

    def test_get_full_prompt(self, sample_skill):
        """Test getting the full prompt."""
        prompt = sample_skill.get_full_prompt()
        assert "Test Prompt" in prompt
        assert "Apply these standards" in prompt

    def test_get_context_summary(self, sample_skill):
        """Test getting context summary."""
        summary = sample_skill.get_context_summary()
        assert "frontend_design" in summary
        assert "Professional Frontend Design" in summary

    def test_matches_task_frontend_keywords(self, sample_skill):
        """Test skill matching for frontend keywords."""
        assert sample_skill.matches_task("Create a React component", [])
        assert sample_skill.matches_task("Update the button styles", [])
        assert sample_skill.matches_task("Fix UI layout issue", [])
        assert sample_skill.matches_task("Add CSS animations", [])

    def test_matches_task_file_extensions(self, sample_skill):
        """Test skill matching based on file extensions."""
        assert sample_skill.matches_task("Update the file", ["src/Button.tsx"])
        assert sample_skill.matches_task("Update the file", ["styles/main.css"])
        assert sample_skill.matches_task("Update the file", ["components/Card.jsx"])

    def test_does_not_match_backend_tasks(self, sample_skill):
        """Test that skill doesn't match backend tasks."""
        assert not sample_skill.matches_task("Update database schema", [])
        assert not sample_skill.matches_task("Fix API endpoint", ["server.py"])

    def test_to_dict(self, sample_skill):
        """Test serialization."""
        data = sample_skill.to_dict()

        assert data["metadata"]["name"] == "frontend_design"
        assert data["has_examples"] is True
        assert data["has_prompt"] is True


class TestSkillLoader:
    """Tests for SkillLoader class."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary skills directory."""
        temp_dir = tempfile.mkdtemp()
        skills_dir = Path(temp_dir)

        # Create a test skill
        test_skill_dir = skills_dir / "test_skill"
        test_skill_dir.mkdir()

        # Write skill files
        (test_skill_dir / "SKILL.md").write_text(
            "# Test Skill\n\n"
            "**Version:** 1.0.0\n"
            "**Category:** frontend\n"
            "**Applicability:** frontend_tasks\n"
            "**Tags:** test, example\n"
        )
        (test_skill_dir / "EXAMPLES.md").write_text("# Examples\n\nExample content")
        (test_skill_dir / "PROMPT.md").write_text("# Prompt\n\nPrompt content")

        yield skills_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_load_skill(self, temp_skills_dir):
        """Test loading a skill."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test_skill")

        assert skill is not None
        assert skill.metadata.name == "test_skill"
        assert skill.metadata.version == "1.0.0"
        assert "test" in skill.metadata.tags

    def test_load_nonexistent_skill(self, temp_skills_dir):
        """Test loading a skill that doesn't exist."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("nonexistent_skill")

        assert skill is None

    def test_discover_skills(self, temp_skills_dir):
        """Test discovering available skills."""
        loader = SkillLoader(temp_skills_dir)
        skills = loader.discover_skills()

        assert "test_skill" in skills

    def test_parse_metadata(self, temp_skills_dir):
        """Test metadata parsing from SKILL.md content."""
        loader = SkillLoader(temp_skills_dir)
        content = (
            "# My Skill\n\n"
            "**Version:** 2.0.0\n"
            "**Category:** design\n"
            "**Tags:** a, b, c\n"
        )

        metadata = loader._parse_metadata("my_skill", content)

        assert metadata.name == "my_skill"
        assert metadata.version == "2.0.0"
        assert metadata.description == "My Skill"
        assert metadata.category == SkillCategory.DESIGN
        assert metadata.tags == ["a", "b", "c"]


class TestSkillRegistry:
    """Tests for SkillRegistry class."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary skills directory with multiple skills."""
        temp_dir = tempfile.mkdtemp()
        skills_dir = Path(temp_dir)

        # Create frontend_design skill
        frontend_dir = skills_dir / "frontend_design"
        frontend_dir.mkdir()
        (frontend_dir / "SKILL.md").write_text(
            "# Professional Frontend Design\n\n"
            "**Version:** 1.0.0\n"
            "**Category:** design\n"
            "**Applicability:** frontend_tasks\n"
            "**Tags:** ui, tailwind\n"
        )
        (frontend_dir / "EXAMPLES.md").write_text("Examples")
        (frontend_dir / "PROMPT.md").write_text("Prompt content for frontend")

        # Create another skill
        backend_dir = skills_dir / "api_design"
        backend_dir.mkdir()
        (backend_dir / "SKILL.md").write_text(
            "# API Design\n\n"
            "**Version:** 1.0.0\n"
            "**Category:** backend\n"
            "**Applicability:** on_demand\n"
        )
        (backend_dir / "EXAMPLES.md").write_text("Examples")
        (backend_dir / "PROMPT.md").write_text("API design prompt")

        yield skills_dir

        shutil.rmtree(temp_dir)

    def test_load_all(self, temp_skills_dir):
        """Test loading all skills."""
        loader = SkillLoader(temp_skills_dir)
        registry = SkillRegistry(loader)
        registry.load_all()

        skills = registry.list_skills()
        assert len(skills) == 2

    def test_get_skill(self, temp_skills_dir):
        """Test getting a specific skill."""
        loader = SkillLoader(temp_skills_dir)
        registry = SkillRegistry(loader)

        skill = registry.get_skill("frontend_design")
        assert skill is not None
        assert skill.metadata.name == "frontend_design"

    def test_get_applicable_skills(self, temp_skills_dir):
        """Test finding applicable skills for a task."""
        loader = SkillLoader(temp_skills_dir)
        registry = SkillRegistry(loader)

        # Frontend task should match frontend_design
        skills = registry.get_applicable_skills(
            "Create a new React component with Tailwind styling",
            ["src/components/Button.tsx"]
        )

        skill_names = [s.metadata.name for s in skills]
        assert "frontend_design" in skill_names

    def test_get_combined_prompt(self, temp_skills_dir):
        """Test generating combined prompt."""
        loader = SkillLoader(temp_skills_dir)
        registry = SkillRegistry(loader)

        prompt = registry.get_combined_prompt(
            "Build a responsive UI component",
            ["src/Card.tsx"]
        )

        assert "Active Skills Protocol" in prompt
        assert "frontend_design" in prompt


class TestAgentSkillIntegration:
    """Tests for skill integration with agents."""

    @pytest.fixture
    def mock_skill_registry(self):
        """Create a mock skill registry."""
        registry = MagicMock(spec=SkillRegistry)

        # Create a mock skill
        mock_skill = MagicMock(spec=Skill)
        mock_skill.metadata = SkillMetadata(
            name="frontend_design",
            version="1.0.0",
            description="Test",
            category=SkillCategory.DESIGN,
            applicability=SkillApplicability.FRONTEND_TASKS,
        )
        mock_skill.get_full_prompt.return_value = "Frontend design prompt"

        registry.get_skill.return_value = mock_skill
        registry.get_applicable_skills.return_value = [mock_skill]

        return registry

    def test_agent_load_skill(self, mock_skill_registry):
        """Test agent loading a skill."""
        from agents.base import BaseAgent, AgentContext, AgentConfig

        # Reset class-level registry
        BaseAgent._skill_registry = None

        context = AgentContext(
            repo_root=Path("/test"),
            config=AgentConfig(),
        )

        with patch.object(BaseAgent, 'get_skill_registry', return_value=mock_skill_registry):
            agent = BaseAgent(context)
            skill = agent.load_skill("frontend_design")

            assert skill is not None
            assert len(agent.get_loaded_skills()) == 1

    def test_agent_load_applicable_skills(self, mock_skill_registry):
        """Test agent loading applicable skills."""
        from agents.base import BaseAgent, AgentContext, AgentConfig

        BaseAgent._skill_registry = None

        context = AgentContext(
            repo_root=Path("/test"),
            config=AgentConfig(),
        )

        with patch.object(BaseAgent, 'get_skill_registry', return_value=mock_skill_registry):
            agent = BaseAgent(context)
            skills = agent.load_applicable_skills(
                "Create a React component",
                ["src/Button.tsx"]
            )

            assert len(skills) == 1
            mock_skill_registry.get_applicable_skills.assert_called_once()

    def test_agent_get_skills_prompt(self, mock_skill_registry):
        """Test agent generating skills prompt."""
        from agents.base import BaseAgent, AgentContext, AgentConfig

        BaseAgent._skill_registry = None

        context = AgentContext(
            repo_root=Path("/test"),
            config=AgentConfig(),
        )

        with patch.object(BaseAgent, 'get_skill_registry', return_value=mock_skill_registry):
            agent = BaseAgent(context)
            agent.load_skill("frontend_design")
            prompt = agent.get_skills_prompt()

            assert "Active Skills Protocol" in prompt
            assert "frontend_design" in prompt

    def test_agent_clear_skills(self, mock_skill_registry):
        """Test clearing loaded skills."""
        from agents.base import BaseAgent, AgentContext, AgentConfig

        BaseAgent._skill_registry = None

        context = AgentContext(
            repo_root=Path("/test"),
            config=AgentConfig(),
        )

        with patch.object(BaseAgent, 'get_skill_registry', return_value=mock_skill_registry):
            agent = BaseAgent(context)
            agent.load_skill("frontend_design")
            assert len(agent.get_loaded_skills()) == 1

            agent.clear_skills()
            assert len(agent.get_loaded_skills()) == 0


class TestFrontendDesignSkill:
    """Tests specifically for the frontend_design skill."""

    @pytest.fixture
    def skills_dir(self):
        """Get the actual skills directory."""
        return Path(__file__).parent.parent / "skills"

    def test_frontend_design_skill_exists(self, skills_dir):
        """Test that the frontend_design skill exists."""
        skill_dir = skills_dir / "frontend_design"
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "EXAMPLES.md").exists()
        assert (skill_dir / "PROMPT.md").exists()

    def test_frontend_design_skill_loads(self, skills_dir):
        """Test that the frontend_design skill loads correctly."""
        loader = SkillLoader(skills_dir)
        skill = loader.load_skill("frontend_design")

        assert skill is not None
        assert skill.metadata.name == "frontend_design"
        assert skill.metadata.applicability == SkillApplicability.FRONTEND_TASKS

    def test_frontend_design_prompt_content(self, skills_dir):
        """Test that the prompt contains key elements."""
        loader = SkillLoader(skills_dir)
        skill = loader.load_skill("frontend_design")

        prompt = skill.get_full_prompt()

        # Check for key concepts
        assert "accessibility" in prompt.lower() or "a11y" in prompt.lower()
        assert "tailwind" in prompt.lower()
        assert "responsive" in prompt.lower()

    def test_frontend_design_examples_content(self, skills_dir):
        """Test that examples contain code snippets."""
        loader = SkillLoader(skills_dir)
        skill = loader.load_skill("frontend_design")

        examples = skill.examples_content

        # Check for code examples
        assert "```" in examples  # Code blocks
        assert "Button" in examples or "button" in examples  # Component example

    def test_frontend_design_matches_react_tasks(self, skills_dir):
        """Test that skill matches React-related tasks."""
        loader = SkillLoader(skills_dir)
        skill = loader.load_skill("frontend_design")

        assert skill.matches_task("Create a React button component", [])
        assert skill.matches_task("Style the navigation with Tailwind", [])
        assert skill.matches_task("Make the form responsive", [])
        assert skill.matches_task("Add dark mode support", ["theme.css"])

    def test_frontend_design_matches_file_types(self, skills_dir):
        """Test that skill matches frontend file types."""
        loader = SkillLoader(skills_dir)
        skill = loader.load_skill("frontend_design")

        assert skill.matches_task("Update the file", ["components/Header.tsx"])
        assert skill.matches_task("Update the file", ["styles/globals.css"])
        assert skill.matches_task("Update the file", ["app/page.jsx"])
        assert skill.matches_task("Update the file", ["layout.vue"])


class TestSkillPipelineIntegration:
    """Tests for skill integration with the spec pipeline."""

    def test_pipeline_discovers_skills_for_frontend_task(self):
        """Test that pipeline discovers frontend_design skill for UI tasks."""
        from spec.pipeline import SpecPipeline, PipelineConfig, PipelineState
        from unittest.mock import MagicMock, patch

        # Create mock state
        state = PipelineState()
        state.task_description = "Create a responsive React component with Tailwind"

        # Create mock context with frontend files
        mock_context = MagicMock()
        mock_file = MagicMock()
        mock_file.relative_path = "src/components/Button.tsx"
        mock_context.files_to_modify = [mock_file]
        state.context = mock_context

        # Create pipeline
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline = SpecPipeline(Path(temp_dir), PipelineConfig())
            pipeline.state = state

            # Test skill discovery
            pipeline._discover_applicable_skills()

            # Should have discovered at least the frontend_design skill
            skill_names = [s.metadata.name for s in state.applicable_skills]
            assert "frontend_design" in skill_names
