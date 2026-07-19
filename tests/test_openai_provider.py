import httpx
import pytest
from openai import APIConnectionError, AuthenticationError

from lilt.exceptions import ContextLengthExceededError, OutputTokenStarvationError
from lilt.llm.openai_provider import (
    OpenAIProvider,
    _is_retryable,
)
from lilt.llm.output_gate import EmptyLLMOutputError
from lilt.models.cost_plane import build_reflection_cost_plane


# Mock classes for OpenAI responses
class MockDelta:
    def __init__(self, content):
        self.content = content


class MockChunkChoice:
    def __init__(self, delta):
        self.delta = delta


class MockChunk:
    def __init__(self, content):
        self.choices = [MockChunkChoice(MockDelta(content))]


class MockResponse:
    def __init__(self, content):
        self.content = content

    def __iter__(self):
        yield MockChunk(self.content)


def test_openai_provider_initialization():
    provider = OpenAIProvider(
        api_key="test_key",
        base_url="http://test",
        model="test-model",
        temperature=0.5,
        reflection_temperature=0.1,
    )
    assert provider.api_key == "test_key"
    assert provider.base_url == "http://test"
    assert provider.model == "test-model"
    assert provider.temperature == 0.5
    assert provider.reflection_temperature == 0.1
    assert provider.client.api_key == "test_key"
    assert str(provider.client.base_url) == "http://test"


def test_openai_provider_dynamic_config():
    provider = OpenAIProvider(
        api_key="test_key",
        base_url="http://test",
        retry_config={"max_attempts": 2, "min_wait_seconds": 1, "max_wait_seconds": 2},
    )
    assert provider.retry_config["max_attempts"] == 2


def test_openai_provider_translate_segment(mocker):
    provider = OpenAIProvider(api_key="test", base_url="http://test")
    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        return_value=MockResponse("Translated text"),
    )

    result = list(provider.translate_segment_iter("Source text"))[-1]["text"]
    assert result == "Translated text"

    mock_create.assert_called_once()
    args, kwargs = mock_create.call_args
    assert kwargs["model"] == provider.model
    assert len(kwargs["messages"]) == 2
    assert (
        kwargs["messages"][1]["content"]
        == "<text_to_translate>\nSource text\n</text_to_translate>"
    )


def test_openai_provider_translate_segment_with_context(mocker):
    provider = OpenAIProvider(api_key="test", base_url="http://test")
    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        return_value=MockResponse("Translated text"),
    )

    context = ["Previous sentence.", "Another previous sentence."]
    result = list(provider.translate_segment_iter("Source text", context=context))[-1][
        "text"
    ]
    assert result == "Translated text"

    args, kwargs = mock_create.call_args
    system_prompt = kwargs["messages"][0]["content"]
    user_prompt = kwargs["messages"][1]["content"]
    assert "Previous sentence." in system_prompt
    assert "<text_to_translate>" in user_prompt
    assert "Source text" in user_prompt


def test_openai_provider_reflection_three_calls(mocker):
    """
    With reflection_enabled=True, the pipeline makes exactly 3 LLM calls:
    Draft → Critique (with changes) → Refine.
    """
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        reflection_enabled=True,
        reflection_temperature=0.0,
    )

    critique_with_changes = '{"requires_refine": true, "issues": [{"category": "fluency", "description": "The phrasing is slightly robotic"}]}'

    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[
            MockResponse("Draft text"),
            MockResponse(critique_with_changes),
            MockResponse("Refined text"),
        ],
    )

    result = list(provider.translate_segment_iter("Source text"))[-1]["text"]
    assert result == "Refined text"
    assert mock_create.call_count == 3

    # Verify Draft call uses translation temperature
    _, draft_kwargs = mock_create.call_args_list[0]
    assert draft_kwargs["temperature"] == provider.temperature  # 0.3 default

    # Verify Critique call uses reflection_temperature
    _, critique_kwargs = mock_create.call_args_list[1]
    assert critique_kwargs["temperature"] == provider.reflection_temperature  # 0.0

    # Verify Refine call uses reflection_temperature
    _, refine_kwargs = mock_create.call_args_list[2]
    assert refine_kwargs["temperature"] == provider.reflection_temperature  # 0.0

    # Verify critique prompt contains the draft
    critique_prompt = critique_kwargs["messages"][1]["content"]
    assert "Draft text" in critique_prompt
    assert "requires_refine" in critique_prompt

    # Verify refine prompt contains both draft and critique
    refine_prompt = refine_kwargs["messages"][1]["content"]
    assert "Draft text" in refine_prompt
    assert "requires_refine" in refine_prompt


def test_openai_provider_reflection_short_circuit(mocker):
    """
    Short-circuit: if the Critique returns ``requires_refine: false`` JSON,
    the Refine call is skipped — only 2 LLM calls are made.
    """
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        reflection_enabled=True,
    )

    critique_no_changes = '{"requires_refine": false, "issues": []}'

    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[
            MockResponse("Draft text"),
            MockResponse(critique_no_changes),
        ],
    )

    result = list(provider.translate_segment_iter("Source text"))[-1]["text"]
    # Short-circuit: returns draft without a 3rd call
    assert result == "Draft text"
    assert mock_create.call_count == 2


def test_openai_provider_reflection_context_passed_to_all_phases(mocker):
    """
    Context is passed to all 3 phases (Draft, Critique, Refine) so that
    the editor can evaluate narrative coherence and terminological consistency.
    """
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        reflection_enabled=True,
    )

    critique_with_changes = '{"requires_refine": true, "issues": [{"category": "other", "description": "Fix phrasing"}]}'

    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[
            MockResponse("Draft text"),
            MockResponse(critique_with_changes),
            MockResponse("Refined text"),
        ],
    )

    context = ["Previous paragraph in target language."]
    list(provider.translate_segment_iter("Source text", context=context))

    assert mock_create.call_count == 3
    for i, (_, kwargs) in enumerate(mock_create.call_args_list):
        system_prompt = kwargs["messages"][0]["content"]
        assert "Previous paragraph in target language." in system_prompt, (
            f"Context missing from system prompt in call #{i + 1} (Draft=0, Critique=1, Refine=2)"
        )


def test_openai_provider_reflection(mocker):
    """Backwards-compatibility test: reflection with changes produces refined output."""
    provider = OpenAIProvider(
        api_key="test", base_url="http://test", reflection_enabled=True
    )

    critique_with_changes = '{"requires_refine": true, "issues": [{"category": "fluency", "description": "Improve fluency."}]}'

    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[
            MockResponse("Draft text"),
            MockResponse(critique_with_changes),
            MockResponse("Refined text"),
        ],
    )

    result = list(provider.translate_segment_iter("Source text"))[-1]["text"]
    assert result == "Refined text"
    assert mock_create.call_count == 3

    # Critique prompt contains the draft
    _, critique_kwargs = mock_create.call_args_list[1]
    critique_prompt = critique_kwargs["messages"][1]["content"]
    assert "Draft text" in critique_prompt


def test_openai_provider_tenacity_retry(mocker):
    provider = OpenAIProvider(api_key="test", base_url="http://test")

    # Fail first, succeed second
    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[
            APIConnectionError(
                message="Connection failed",
                request=httpx.Request("POST", "http://test"),
            ),
            MockResponse("Success after retry"),
        ],
    )

    # Note: Because of wait_exponential, this might take a bit of time in tests
    # But since it's the first retry, wait is minimal (2 seconds).
    result = list(provider.translate_segment_iter("Source text"))[-1]["text"]
    assert result == "Success after retry"
    assert mock_create.call_count == 2


def test_openai_provider_dynamic_token_accounting():
    # Tight neighbor budget: only the most recent backward segment fits.
    # Pin output reservation near the ceiling so packing matches historical budget.
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=1540,
        max_tokens=900,
        tokenizer_fudge=1.0,
        chat_template_overhead=0,
        stage_policies={
            "draft": {
                "output_multiplier": 50.0,
                "output_floor": 900,
                "output_margin": 0,
            }
        },
    )

    target_text = "word"
    context = [
        "oldest " * 100,
        "middle " * 100,
        "newest " * 100,
    ]

    block, _pack_ms = provider._build_context_block(
        context, target_text, stage="draft"
    )

    # Budget fits two most-recent backward neighbors; oldest is dropped.
    assert "newest " * 100 in block
    assert "middle " * 100 in block
    assert "oldest " * 100 not in block


def test_openai_provider_dynamic_token_accounting_zero_budget():
    # Reserved output + measured fixed prompt leave no neighbor budget.
    # Use ceiling-aligned adaptive budget via high floor / multiplier so packing
    # still sees a large reserved_output (matches shared_budget ceiling).
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=1200,
        max_tokens=1000,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
        stage_policies={
            "draft": {
                "output_multiplier": 50.0,
                "output_floor": 1000,
                "output_margin": 0,
            }
        },
    )

    target_text = "huge " * 150
    context = ["context " * 100]

    block, _pack_ms = provider._build_context_block(
        context, target_text, stage="draft"
    )
    assert block == ""


def test_openai_provider_pre_flight_token_limit_exceeded(mocker):
    # Context limit below reserved output + fudged prompt → never call the API.
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=200,
        max_tokens=150,
        tokenizer_fudge=1.0,
        chat_template_overhead=48,
    )

    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        return_value=MockResponse("Should not be called"),
    )

    with pytest.raises(ContextLengthExceededError) as exc_info:
        list(
            provider.translate_segment_iter(
                "This is a test segment that will exceed limit " * 20
            )
        )

    assert "reserved_output" in str(exc_info.value)
    mock_create.assert_not_called()


def test_is_retryable_rejects_authentication_error():
    req = httpx.Request("POST", "http://test/v1/chat/completions")
    resp = httpx.Response(401, request=req)
    exc = AuthenticationError("Invalid API key", response=resp, body=None)
    assert _is_retryable(exc) is False
    assert _is_retryable(ContextLengthExceededError("too long")) is False


def test_is_retryable_rejects_empty_output_error():
    # EmptyLLMOutputError must not trigger tenacity retries: it is raised outside
    # the Retrying block, and empty-output handling lives in the workflow strategy.
    assert _is_retryable(EmptyLLMOutputError("empty")) is False


def test_openai_provider_does_not_retry_authentication_error(mocker):
    provider = OpenAIProvider(
        api_key="bad",
        base_url="http://test",
        retry_config={"max_attempts": 3, "min_wait_seconds": 0, "max_wait_seconds": 0},
    )
    req = httpx.Request("POST", "http://test/v1/chat/completions")
    resp = httpx.Response(401, request=req)
    auth_error = AuthenticationError("Invalid API key", response=resp, body=None)
    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=auth_error,
    )

    with pytest.raises(AuthenticationError):
        provider.generate_draft("Hello")

    assert mock_create.call_count == 1


def test_domain_context_truncated_to_cap():
    long_domain = "domain " * 500
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        domain_context=long_domain,
        domain_context_max_tokens=32,
    )
    assert provider.domain_truncated is True
    assert provider.domain_context is not None
    assert len(provider.domain_context) < len(long_domain)


def test_output_token_starvation_raises(mocker):
    class Usage:
        prompt_tokens = 10
        completion_tokens = 128
        prompt_tokens_details = None
        completion_tokens_details = None

    class StarvingChunk:
        def __init__(self):
            self.choices = [MockChunkChoice(MockDelta(None))]
            self.usage = Usage()

    class StarvingResponse:
        def __iter__(self):
            yield StarvingChunk()

    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=256,
    )
    mocker.patch.object(
        provider.client.chat.completions,
        "create",
        return_value=StarvingResponse(),
    )

    with pytest.raises(OutputTokenStarvationError, match="completion token"):
        provider.generate_draft("Hello world")


def test_output_token_starvation_retries_with_reasoning_budget(mocker):
    class Usage:
        prompt_tokens = 10
        completion_tokens = 128
        prompt_tokens_details = None
        completion_tokens_details = None

    class StarvingChunk:
        def __init__(self):
            self.choices = [MockChunkChoice(MockDelta(None))]
            self.usage = Usage()

    class OkChunk:
        def __init__(self):
            self.choices = [MockChunkChoice(MockDelta("Hola"))]
            self.usage = Usage()

    class StarvingResponse:
        def __iter__(self):
            yield StarvingChunk()

    class OkResponse:
        def __iter__(self):
            yield OkChunk()

    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=2048,
        cost_plane=build_reflection_cost_plane(
            cost_profile="balanced",
            stage_overrides={"draft": {"output_floor": 256}},
        ),
    )
    create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[StarvingResponse(), OkResponse()],
    )

    res = provider.generate_draft("Hello world")
    assert res.text == "Hola"
    assert res.retry_reason == "reasoning_budget"
    assert create.call_count == 2
    first_max = create.call_args_list[0].kwargs.get("max_tokens")
    second_max = create.call_args_list[1].kwargs.get("max_tokens")
    assert first_max is not None and second_max is not None
    assert second_max > first_max


def test_output_token_starvation_retries_with_thinking_disabled(mocker):
    class Usage:
        prompt_tokens = 10
        completion_tokens = 128
        prompt_tokens_details = None
        completion_tokens_details = None

    class StarvingChunk:
        def __init__(self):
            self.choices = [MockChunkChoice(MockDelta(None))]
            self.usage = Usage()

    class OkChunk:
        def __init__(self):
            self.choices = [MockChunkChoice(MockDelta("Hola"))]
            self.usage = Usage()

    class StarvingResponse:
        def __iter__(self):
            yield StarvingChunk()

    class OkResponse:
        def __iter__(self):
            yield OkChunk()

    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=256,
        cost_plane=build_reflection_cost_plane(
            cost_profile="balanced",
            stage_overrides={
                "draft": {"thinking": "on", "output_floor": 256},
            },
        ),
    )
    create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        side_effect=[StarvingResponse(), OkResponse()],
    )

    res = provider.generate_draft("Hello world")
    assert res.text == "Hola"
    assert res.retry_reason == "thinking_disabled"
    assert create.call_count == 2
    assert "reasoning_effort" not in create.call_args_list[0].kwargs
    assert create.call_args_list[1].kwargs.get("reasoning_effort") == "none"
