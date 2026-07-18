"""LLM provider protocol, response model, and context data types."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class LLMResponse:
    """Represents the response from an LLM provider."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    duration_ms: int = 0
    ttft_ms: int | None = None
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime = field(default_factory=datetime.now)
    bypass: bool = False


ContextData = Sequence[str] | dict[str, list[str]]


class LLMProvider(Protocol):
    """Protocol defining the interface for LLM translation providers.

    See docs/architecture/05-llm-layer.md (arch-05).
    """

    @property
    def reflection_enabled(self) -> bool:
        """Indicates if reflection/critique loop is enabled for the provider."""
        ...

    def generate_draft(
        self, text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Generates an initial translation draft."""
        ...

    def generate_critique(
        self, draft_text: str, source_text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Evaluates a draft against MQM axes."""
        ...

    def generate_refine(
        self,
        draft_text: str,
        critique_text: str,
        source_text: str,
        context: ContextData | None = None,
    ) -> LLMResponse:
        """Produces a final translation applying critique changes to the draft."""
        ...

    def get_prompt_version(self, stage: str) -> str:
        """Return a content-based version identifier for a given pipeline stage's prompt.

        The version is derived from the SHA-256 hash of the resolved Jinja2 template
        source, ensuring that any change to the prompt file is reflected in telemetry.

        Args:
            stage: One of ``"draft"``, ``"critique"``, ``"refine"``.

        Returns:
            A string like ``"draft:a3f2e1b4"``.
        """
        ...

    def stage_model_name(self, stage: str) -> str:
        """Return the model name used for a workflow stage or sequential pass."""
        ...

    def translate_segment_iter(
        self, text: str, context: ContextData | None = None
    ) -> Iterable[dict]:
        """(Sequential) Translates a masked LaTeX text segment, yielding progress events."""
        ...
