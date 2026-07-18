"""Tests for batch token-budget preflight."""

import logging

import pytest
from pydantic import ValidationError

from lilt.exceptions import BudgetPreflightError
from lilt.llm.budget_preflight import preflight_translation_budget
from lilt.llm.openai_provider import OpenAIProvider
from lilt.models.config import LiltConfig


def test_config_rejects_impossible_context_vs_max_tokens() -> None:
    with pytest.raises(ValidationError, match="model_context_limit"):
        LiltConfig.model_validate(
            {
                "llm": {
                    "max_tokens": 8192,
                    "model_context_limit": 8192,
                }
            }
        )


def test_config_rejects_split_without_headroom() -> None:
    with pytest.raises(ValidationError, match="reserved output"):
        LiltConfig.model_validate(
            {
                "llm": {
                    "max_tokens": 4000,
                    "reasoning_reserve": 2000,
                    "output_token_mode": "split_budget",
                    "model_context_limit": 5000,
                }
            }
        )


def test_preflight_aborts_when_infeasible() -> None:
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=800,
        max_tokens=700,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
    )
    with pytest.raises(BudgetPreflightError, match="infeasible"):
        preflight_translation_budget(
            provider,
            source_texts=["word " * 200],
            stages=["draft"],
        )


def test_preflight_ok_with_headroom() -> None:
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=1024,
        tokenizer_fudge=1.0,
    )
    plans = preflight_translation_budget(
        provider,
        source_texts=["Hello"],
        stages=["draft"],
    )
    assert len(plans) == 1
    assert plans[0].ok


def test_preflight_warns_when_domain_context_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=1024,
        tokenizer_fudge=1.0,
        domain_context=None,
    )
    with caplog.at_level(logging.WARNING, logger="lilt.llm.budget_preflight"):
        preflight_translation_budget(
            provider,
            source_texts=["Hello"],
            stages=["draft"],
        )
    assert any("domain_context is empty" in r.message for r in caplog.records)


def test_preflight_no_domain_warn_when_set(caplog: pytest.LogCaptureFixture) -> None:
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=1024,
        tokenizer_fudge=1.0,
        domain_context="Operating systems textbook terminology.",
    )
    with caplog.at_level(logging.WARNING, logger="lilt.llm.budget_preflight"):
        preflight_translation_budget(
            provider,
            source_texts=["Hello"],
            stages=["draft"],
        )
    assert not any("domain_context is empty" in r.message for r in caplog.records)
