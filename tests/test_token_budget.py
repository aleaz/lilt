"""Unit tests for provider-agnostic token budget planning."""

from math import ceil

from lilt.llm.token_budget import (
    OutputTokenMode,
    call_footprint,
    plan_token_budget,
    safety_margin_tokens,
)


def test_shared_budget_reserved_equals_max_tokens() -> None:
    plan = plan_token_budget(
        context_limit=8192,
        max_tokens=2048,
        fixed_prompt_tokens=500,
        output_token_mode=OutputTokenMode.SHARED_BUDGET,
        reasoning_reserve=512,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
    )
    assert plan.reserved_output == 2048
    assert plan.ok
    assert not plan.infeasible


def test_split_budget_adds_reasoning_reserve() -> None:
    plan = plan_token_budget(
        context_limit=8192,
        max_tokens=2048,
        fixed_prompt_tokens=500,
        output_token_mode=OutputTokenMode.SPLIT_BUDGET,
        reasoning_reserve=512,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
    )
    assert plan.reserved_output == 2048 + 512


def test_fudge_reduces_neighbor_budget() -> None:
    base = plan_token_budget(
        context_limit=8192,
        max_tokens=1024,
        fixed_prompt_tokens=1000,
        tokenizer_fudge=1.0,
        chat_template_overhead=0,
    )
    fudged = plan_token_budget(
        context_limit=8192,
        max_tokens=1024,
        fixed_prompt_tokens=1000,
        tokenizer_fudge=1.1,
        chat_template_overhead=0,
    )
    assert fudged.neighbor_budget < base.neighbor_budget
    assert fudged.effective_fixed_tokens == ceil(1000 * 1.1)


def test_infeasible_when_fixed_prompt_too_large() -> None:
    plan = plan_token_budget(
        context_limit=2048,
        max_tokens=1024,
        fixed_prompt_tokens=2000,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
    )
    assert plan.infeasible
    assert not plan.ok
    assert plan.neighbor_budget <= 0


def test_safety_margin_floor() -> None:
    assert safety_margin_tokens(1000) == 64
    assert safety_margin_tokens(10_000) == 200


def test_call_footprint_includes_reserved_output() -> None:
    plan = plan_token_budget(
        context_limit=1000,
        max_tokens=400,
        fixed_prompt_tokens=100,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
    )
    effective, total = call_footprint(700, plan)
    assert effective == 700
    assert total == 700 + 48 + 400
    assert total > plan.context_limit
