"""
Professional Frontend Design Skill

Part of Claude God Code - Autonomous Excellence

This skill enables creation of distinctive, production-grade frontend
interfaces with high design quality. It enforces standards for:

- Aesthetic Excellence (typography, color, motion, spatial composition)
- Accessibility (WCAG AA compliance, keyboard navigation, screen readers)
- Tailwind CSS Best Practices
- Responsive Mobile-First Design
- Performance Guidelines (Core Web Vitals)

The skill is automatically applied to frontend tasks detected by:
- Task keywords: frontend, ui, component, react, vue, css, tailwind, etc.
- File extensions: .tsx, .jsx, .vue, .svelte, .css, .scss, .html

Usage:
    from skills import SkillRegistry

    registry = SkillRegistry()
    skill = registry.get_skill("frontend_design")
    prompt = skill.get_full_prompt()
"""

SKILL_NAME = "frontend_design"
SKILL_VERSION = "1.0.0"
