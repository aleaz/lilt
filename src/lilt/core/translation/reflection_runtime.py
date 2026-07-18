"""Domain-facing reflection helpers used by translation strategies.

Strategies import stage orchestration and budget preflight through this module
instead of reaching into concrete ``llm.*`` implementation packages. The LLM
provider port (``LLMProvider`` / ``LLMResponse``) remains a direct dependency.
"""

from lilt.exceptions import EmptyLLMOutputError
from lilt.llm.budget_preflight import preflight_translation_budget
from lilt.llm.reflection_pass import (
    REFINE_MAX_VALIDATION_RETRIES,
    run_critique,
    run_draft,
    run_refine,
    run_reflection_pass,
    validation_retries_for_source,
)

__all__ = [
    "EmptyLLMOutputError",
    "REFINE_MAX_VALIDATION_RETRIES",
    "preflight_translation_budget",
    "run_critique",
    "run_draft",
    "run_refine",
    "run_reflection_pass",
    "validation_retries_for_source",
]
