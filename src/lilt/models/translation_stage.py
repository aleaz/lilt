"""Workflow stage enum for draft, critique, and refine reflection passes."""

from enum import Enum


class TranslationStage(str, Enum):
    """Enumeration of possible workflow stages in the translation pipeline."""

    DRAFT = "draft"
    CRITIQUE = "critique"
    REFINE = "refine"
