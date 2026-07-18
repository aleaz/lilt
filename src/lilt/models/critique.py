"""Pydantic models for LLM critique output and translation issues."""

from typing import Literal

from pydantic import BaseModel, Field


class TranslationIssue(BaseModel):
    """Represents a specific issue found in a translation draft."""

    category: Literal["fluency", "consistency", "accuracy", "other"] = Field(
        ..., description="The category of the translation error"
    )
    description: str = Field(
        ..., description="A short, actionable description of the issue"
    )


class CritiqueResult(BaseModel):
    """The structured JSON response expected from the critique phase."""

    requires_refine: bool = Field(
        ...,
        description="True if the draft needs revision, False if it is acceptable as is",
    )
    issues: list[TranslationIssue] = Field(
        default_factory=list,
        description=(
            "List of specific issues found. Empty if requires_refine is false. "
            "Reserved for future refine-stage prompting; only requires_refine is "
            "consumed by the workflow today."
        ),
    )
