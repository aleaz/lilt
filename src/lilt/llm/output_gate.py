"""LLM output validation at the provider boundary."""

from lilt.exceptions import LiltDomainError
from lilt.parser.placeholder_contract import normalize_llm_placeholders
from lilt.utils.text_utils import has_linguistic_content


class EmptyLLMOutputError(LiltDomainError):
    """Raised when the LLM returns empty text for linguistic source content."""

    def __init__(self, stage: str) -> None:
        super().__init__(
            f"LLM returned empty output during '{stage}' for translatable content."
        )


def validate_llm_output(text: str, *, source: str, stage: str) -> str:
    """Validate and normalize LLM completion text."""
    normalized = normalize_llm_placeholders(text if text is not None else "", source)
    if has_linguistic_content(source) and not normalized.strip():
        raise EmptyLLMOutputError(stage)
    return normalized
