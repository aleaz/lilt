"""LLM output validation at the provider boundary."""

from lilt.exceptions import EmptyLLMOutputError
from lilt.parser.linguistic import has_linguistic_content
from lilt.parser.placeholder_contract import normalize_llm_placeholders

__all__ = ["EmptyLLMOutputError", "validate_llm_output"]


def validate_llm_output(text: str, *, source: str, stage: str) -> str:
    """Validate and normalize LLM completion text."""
    normalized = normalize_llm_placeholders(text if text is not None else "", source)
    if has_linguistic_content(source) and not normalized.strip():
        raise EmptyLLMOutputError(stage)
    return normalized
