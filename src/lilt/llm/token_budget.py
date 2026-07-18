"""Provider-agnostic token budget planning for LLM context packing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import ceil


class OutputTokenMode(str, Enum):
    """How completion tokens are reserved against the model context limit."""

    SHARED_BUDGET = "shared_budget"
    SPLIT_BUDGET = "split_budget"


@dataclass(frozen=True)
class BudgetPlan:
    """Immutable result of a token budget calculation."""

    context_limit: int
    reserved_output: int
    fixed_prompt_tokens: int
    neighbor_budget: int
    safety_margin: int
    chat_template_overhead: int
    fudge: float
    ok: bool
    infeasible: bool
    domain_truncated: bool = False
    neighbors_truncated: bool = False

    @property
    def effective_fixed_tokens(self) -> int:
        """Fixed prompt tokens after tokenizer fudge."""
        return ceil(self.fixed_prompt_tokens * self.fudge)


def safety_margin_tokens(context_limit: int) -> int:
    """Return safety margin for a context window size."""
    return max(64, context_limit // 50)


class TokenBudgetPlanner:
    """Compute neighbor budget from measured fixed prompts and output reservation."""

    @staticmethod
    def plan(
        *,
        context_limit: int,
        max_tokens: int,
        fixed_prompt_tokens: int,
        output_token_mode: OutputTokenMode | str = OutputTokenMode.SHARED_BUDGET,
        reasoning_reserve: int = 0,
        tokenizer_fudge: float = 1.1,
        chat_template_overhead: int = 48,
        domain_truncated: bool = False,
    ) -> BudgetPlan:
        """Build a :class:`BudgetPlan` for one OpenAI-compatible endpoint profile."""
        mode = OutputTokenMode(output_token_mode)
        if mode == OutputTokenMode.SPLIT_BUDGET:
            reserved_output = max_tokens + max(0, reasoning_reserve)
        else:
            reserved_output = max_tokens

        fudge = max(1.0, float(tokenizer_fudge))
        overhead = max(0, int(chat_template_overhead))
        margin = safety_margin_tokens(context_limit)
        effective_fixed = ceil(max(0, fixed_prompt_tokens) * fudge)

        neighbor_budget = (
            context_limit - reserved_output - effective_fixed - overhead - margin
        )
        infeasible = neighbor_budget < 0 or (
            effective_fixed + overhead + reserved_output + margin > context_limit
        )
        if infeasible:
            neighbor_budget = min(0, neighbor_budget)

        return BudgetPlan(
            context_limit=context_limit,
            reserved_output=reserved_output,
            fixed_prompt_tokens=max(0, fixed_prompt_tokens),
            neighbor_budget=neighbor_budget,
            safety_margin=margin,
            chat_template_overhead=overhead,
            fudge=fudge,
            ok=not infeasible,
            infeasible=infeasible,
            domain_truncated=domain_truncated,
        )

    @staticmethod
    def call_footprint(prompt_tokens: int, plan: BudgetPlan) -> tuple[int, int]:
        """Return ``(effective_prompt_tokens, total_reserved_footprint)`` for a call gate."""
        effective = ceil(max(0, prompt_tokens) * plan.fudge)
        total = effective + plan.chat_template_overhead + plan.reserved_output
        return effective, total
