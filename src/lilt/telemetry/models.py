"""Pydantic models for inference records and token usage metrics."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TokenUsage(BaseModel):
    """Represents token usage for a single inference call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    source: Literal["provider_reported", "locally_estimated"] = "locally_estimated"


class InferenceRecord(BaseModel):
    """Represents a single LLM API call."""

    id: str
    segment_id: str
    namespace: str

    # Context
    provider: str
    model: str
    stage: Literal["draft", "critique", "refine", "sequential"]
    prompt_version: str

    # Timing
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    ttft_ms: int | None = None

    # Consumption
    usage: TokenUsage
    usage_source: str = "locally_estimated"
    finish_reason: str | None = None
    is_heuristic_simple: bool | None = None
    attempt: int = 1
    retry_reason: str | None = None
    pack_context_ms: int | None = None
    checkpoint_ms: int | None = None
    effective_max_tokens: int | None = None
