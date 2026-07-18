from typing import cast

import pytest

from lilt.llm.factory import ProviderFactory
from lilt.llm.openai_provider import OpenAIProvider
from lilt.llm.router_provider import RouterLLMProvider


def test_factory_creates_openai_provider():
    config = {
        "provider": "openai",
        "api_key": "test_key",
        "base_url": "http://test",
        "model": "test-model",
        "temperature": 0.5,
        "max_tokens": 100,
        "reflection_enabled": True,
        "reflection_temperature": 0.1,
    }
    provider = ProviderFactory.create(config)
    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "test_key"
    assert provider.base_url == "http://test"
    assert provider.model == "test-model"
    assert provider.temperature == 0.5
    assert provider.max_tokens == 100
    assert provider.reflection_enabled is True
    assert provider.reflection_temperature == 0.1


def test_factory_default_parameters():
    config: dict[str, str] = {}
    provider = ProviderFactory.create(config)
    assert isinstance(provider, OpenAIProvider)
    assert provider.temperature == 0.3
    assert provider.max_tokens is None
    assert provider.reflection_enabled is True
    assert provider.reflection_temperature == 0.0


def test_factory_passes_model_context_limit():
    config = {"model_context_limit": 32768}
    provider = ProviderFactory.create(config)
    assert isinstance(provider, OpenAIProvider)
    assert provider.model_context_limit == 32768


def test_factory_router_stages_inherit_model_context_limit():
    config = {
        "model_context_limit": 16384,
        "stages": {
            "draft": {"model": "local-model"},
            "critique": {"provider": "openai", "model": "gpt-4o"},
            "refine": {"model": "gpt-4o-mini"},
        },
    }
    provider = ProviderFactory.create(config)
    assert isinstance(provider, RouterLLMProvider)
    assert cast(OpenAIProvider, provider.draft_provider).model_context_limit == 16384
    assert cast(OpenAIProvider, provider.critique_provider).model_context_limit == 16384
    assert cast(OpenAIProvider, provider.refine_provider).model_context_limit == 16384


def test_factory_unsupported_provider():
    config = {"provider": "gemini"}
    with pytest.raises(ValueError) as exc:
        ProviderFactory.create(config)
    assert "Unsupported LLM provider: gemini" in str(exc.value)


def test_factory_passes_budget_fields():
    config = {
        "api_key": "k",
        "output_token_mode": "split_budget",
        "reasoning_reserve": 256,
        "tokenizer_fudge": 1.2,
        "chat_template_overhead": 64,
        "domain_context_max_tokens": 128,
    }
    provider = ProviderFactory.create(config)
    assert isinstance(provider, OpenAIProvider)
    assert provider.output_token_mode.value == "split_budget"
    assert provider.reasoning_reserve == 256
    assert provider.tokenizer_fudge == 1.2
    assert provider.chat_template_overhead == 64
    assert provider.domain_context_max_tokens == 128


def test_factory_router_stages_distinct_context_limits():
    config = {
        "model_context_limit": 8192,
        "max_tokens": 1024,
        "stages": {
            "draft": {"model_context_limit": 4096, "model": "local-a"},
            "critique": {"model_context_limit": 16384, "model": "local-b"},
            "refine": {"model_context_limit": 8192, "model": "local-c"},
        },
    }
    provider = ProviderFactory.create(config)
    assert isinstance(provider, RouterLLMProvider)
    draft = cast(OpenAIProvider, provider.draft_provider)
    critique = cast(OpenAIProvider, provider.critique_provider)
    assert draft.model_context_limit == 4096
    assert critique.model_context_limit == 16384
    plan_d = draft.plan_budget(stage="draft", source_text="hello")
    plan_c = critique.plan_budget(
        stage="critique", source_text="hello", draft_text="hola"
    )
    assert plan_d.context_limit != plan_c.context_limit
