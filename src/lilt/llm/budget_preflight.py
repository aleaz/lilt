"""Batch-level token budget preflight before translation loops."""

from __future__ import annotations

import logging
from typing import Any

from lilt.exceptions import BudgetPreflightError
from lilt.llm.context_recommend import (
    advise_context_capacity,
    format_capacity_warnings,
)
from lilt.llm.provider import LLMProvider
from lilt.llm.router_provider import RouterLLMProvider
from lilt.llm.token_budget import BudgetPlan
from lilt.models.segment import StoredSegment
from lilt.utils.token_utils import count_tokens

logger = logging.getLogger(__name__)


def _stage_provider(llm: LLMProvider, stage: str) -> LLMProvider:
    if isinstance(llm, RouterLLMProvider):
        return llm.stage_provider(stage)
    return llm


def _plan_for_provider(
    provider: LLMProvider,
    *,
    stage: str,
    source_text: str,
) -> BudgetPlan | None:
    plan_fn = getattr(provider, "plan_budget", None)
    if not callable(plan_fn):
        return None
    try:
        plan = plan_fn(stage=stage, source_text=source_text)
    except NotImplementedError:
        return None
    if not isinstance(plan, BudgetPlan):
        return None
    return plan


def _warn_if_domain_context_empty(llm: LLMProvider) -> None:
    """Log once when project domain_context is unset (recommended, not required)."""
    provider: Any = _stage_provider(llm, "draft")
    domain = getattr(provider, "domain_context", None)
    if domain:
        return
    logger.warning(
        "project.domain_context is empty. Setting it in lilt.yaml is highly "
        "recommended for domain terminology; translation will continue without it."
    )


def warn_context_capacity(
    llm: LLMProvider,
    segments: list[StoredSegment],
    *,
    stages: list[str] | None = None,
) -> list[str]:
    """Log soft capacity advisories (neighbors / undersized limit). Non-blocking."""
    if not segments:
        return []
    report = advise_context_capacity(llm, segments, stages=stages)
    messages = format_capacity_warnings(report)
    for msg in messages:
        logger.warning("%s", msg)
    return messages


def preflight_translation_budget(
    llm: LLMProvider,
    *,
    source_texts: list[str],
    stages: list[str],
    segments: list[StoredSegment] | None = None,
) -> list[BudgetPlan]:
    """Abort early when the worst-case segment cannot fit fixed prompts + output.

    For each stage that will run, resolve the stage provider (router-aware),
    measure against the longest source text by token count, and raise
    :class:`BudgetPreflightError` if any plan is infeasible.

    When ``segments`` is provided, also emits soft warnings if StagePolicy
    neighbor windows will truncate under the configured context limit.
    """
    if not source_texts:
        return []

    _warn_if_domain_context_empty(llm)

    worst = max(source_texts, key=lambda t: count_tokens(t))
    plans: list[BudgetPlan] = []

    for stage in stages:
        provider = _stage_provider(llm, stage)
        plan = _plan_for_provider(provider, stage=stage, source_text=worst)
        if plan is None:
            continue
        plans.append(plan)
        headroom = plan.neighbor_budget
        logger.info(
            "budget_preflight stage=%s mode=%s context_limit=%s reserved_output=%s "
            "fixed_prompt_tokens=%s neighbor_budget=%s infeasible=%s",
            stage,
            getattr(provider, "output_token_mode", "unknown"),
            plan.context_limit,
            plan.reserved_output,
            plan.fixed_prompt_tokens,
            headroom,
            plan.infeasible,
        )
        if plan.infeasible:
            raise BudgetPreflightError(
                f"Token budget infeasible for stage '{stage}' on the largest "
                f"eligible segment ({count_tokens(worst)} source tokens). "
                f"context_limit={plan.context_limit}, "
                f"reserved_output={plan.reserved_output}, "
                f"fixed_prompt_tokens={plan.fixed_prompt_tokens}, "
                f"safety_margin={plan.safety_margin}, "
                f"overhead={plan.chat_template_overhead}. "
                "Raise model_context_limit, lower max_tokens/reasoning_reserve, "
                "or shorten domain_context / source segments."
            )

    if segments:
        warn_context_capacity(llm, segments, stages=stages)
    return plans
