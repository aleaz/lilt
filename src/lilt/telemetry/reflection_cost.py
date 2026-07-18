"""Reflection cost estimation for pre-flight token budgeting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from lilt.models.segment import StoredSegment
from lilt.parser.linguistic import has_linguistic_content
from lilt.utils.token_utils import count_tokens


@dataclass(frozen=True)
class ReflectionCostParams:
    """Tunable coefficients for reflection cost estimation."""

    s_prompt: int = 600
    r_ratio: float = 0.7
    context_multiplier: float = 1.2
    context_base: float = 2.4


def _context_window_average(context_window: Any) -> float:
    if isinstance(context_window, dict):
        values = [
            float(v) for v in context_window.values() if isinstance(v, (int, float))
        ]
        return sum(values) / len(values) if values else 3.0
    if isinstance(context_window, (int, float)):
        return float(context_window)
    return 3.0


def _reflection_multiplier(translation_mode: str) -> float:
    if translation_mode == "sequential":
        return 2.0
    return 2.0 + ReflectionCostParams.r_ratio


def estimate_reflection_tokens(
    segments: Sequence[StoredSegment],
    config: Mapping[str, Any],
    params: ReflectionCostParams | None = None,
) -> int:
    """Estimate expected inference tokens for a reflection translation run."""
    p = params or ReflectionCostParams()
    llm_cfg = config.get("llm", {}) if isinstance(config.get("llm"), dict) else {}
    translation_mode = str(llm_cfg.get("translation_mode", "workflow"))

    c_avg = _context_window_average(llm_cfg.get("context_window", 3))
    multiplier = _reflection_multiplier(translation_mode)

    translatable = [seg for seg in segments if has_linguistic_content(seg.source_text)]
    n = len(translatable)
    tokens_source = sum(count_tokens(seg.source_text) for seg in translatable)

    prompt_term = n * p.s_prompt * multiplier
    context_term = tokens_source * (
        p.context_multiplier * c_avg * multiplier + p.context_base
    )
    return int(prompt_term + context_term)
