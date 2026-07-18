"""Translation execution mode for the LLM pipeline."""

from enum import Enum


class TranslationMode(str, Enum):
    """How the translator orchestrates LLM reflection across segments."""

    WORKFLOW = "workflow"
    SEQUENTIAL = "sequential"

    @classmethod
    def from_llm_config(cls, llm_config: dict) -> "TranslationMode":
        """Resolve mode from ``translation_mode`` (default: workflow)."""
        raw_mode = llm_config.get("translation_mode", "workflow")
        return cls(str(raw_mode).lower())
