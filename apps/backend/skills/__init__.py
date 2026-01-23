"""
Skills system for Claude God Code.

Part of Claude God Code - Autonomous Excellence

This module provides a modular skill system that allows agents to load
domain-specific protocols and standards on demand. Skills are self-contained
packages that include definitions, examples, and prompt injections.
"""

from .loader import Skill, SkillLoader, SkillMetadata, SkillRegistry

__all__ = [
    "Skill",
    "SkillLoader",
    "SkillMetadata",
    "SkillRegistry",
]
