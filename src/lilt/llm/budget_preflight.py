"""Batch-level token budget preflight before translation loops."""

from __future__ import annotations

import logging
from typing import Any

from lilt.exceptions import BudgetPreflightError
from lilt.llm.provider import LLMProvider
from lilt.llm.token_budget import BudgetPlan
from lilt.utils.token_utils import count_tokens

logger = logging.getLogger(__name__)


def _stage_provider(llm: LLMProvider, stage: str) -> Any:
    from lilt.llm.router_provider import RouterLLMProvider  # noqa: PLC0415

    if isinstance(llm, RouterLLMProvider):
        return llm.stage_provider(stage)
    return llm


def _plan_for_provider(
    provider: Any,
    *,
    stage: str,
    source_text: str,
) -> BudgetPlan | None:
    plan_fn = getattr(provider, "plan_budget", None)
    if not callable(plan_fn):
        return None
    plan = plan_fn(stage=stage, source_text=source_text)
    if not isinstance(plan, BudgetPlan):
        return None
    return plan


def preflight_translation_budget(
    llm: LLMProvider,
    *,
    source_texts: list[str],
    stages: list[str],
) -> list[BudgetPlan]:
    """Abort early when the worst-case segment cannot fit fixed prompts + output.

    For each stage that will run, resolve the stage provider (router-aware),
    measure against the longest source text by token count, and raise
    :class:`BudgetPreflightError` if any plan is infeasible.
    """
    if not source_texts:
        return []

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
    return plans
