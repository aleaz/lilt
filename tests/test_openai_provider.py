import httpx
import pytest
from openai import APIConnectionError, AuthenticationError

from lilt.llm.openai_provider import (
    ContextLengthExceededError,
    OpenAIProvider,
    _is_retryable,
)
from lilt.llm.output_gate import EmptyLLMOutputError


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
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=1000,  # Small limit to force truncation
    )

    # max_total_tokens = 1000
    # system_tokens = 600
    # safety = 100
    # Base available budget = 300 tokens for target + output + context

    # Target text is 1 token ("word"). Expected output is 1 token.
    # Budget for context = 300 - 1 - 1 = 298 tokens.

    target_text = "word"

    # Create 3 context segments of ~102 tokens each.
    # Total context = 306 tokens. This exceeds the 298 tokens budget.
    # It should only include the most recent 2 segments (204 tokens).

    context = [
        "oldest " * 100,  # Oldest
        "middle " * 100,  # Middle
        "newest " * 100,  # Newest
    ]

    block = provider._build_context_block(context, target_text)

    # Should contain middle and newest, but not oldest
    assert "middle " * 100 in block
    assert "newest " * 100 in block
    assert "oldest " * 100 not in block


def test_openai_provider_dynamic_token_accounting_zero_budget():
    provider = OpenAIProvider(
        api_key="test", base_url="http://test", model_context_limit=1000
    )

    # max_total_tokens = 1000
    # system = 600, safety = 100 -> base available = 300 tokens.
    # Target text is 150 tokens. Expected output = 225 tokens.
    # Required for target + output = 375 tokens.
    # Budget is exceeded (-75 tokens). Context should be empty.
    target_text = "huge " * 150

    context = ["context " * 100]

    block = provider._build_context_block(context, target_text)

    # Budget is exceeded, block should be empty
    assert block == ""


def test_openai_provider_pre_flight_token_limit_exceeded(mocker):
    # Set context limit low enough that even a single short request exceeds it
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=10,  # extremely low limit
    )

    mock_create = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        return_value=MockResponse("Should not be called"),
    )

    with pytest.raises(ContextLengthExceededError) as exc_info:
        list(
            provider.translate_segment_iter(
                "This is a test segment that will exceed limit"
            )
        )

    assert "Segment exceeds token limit" in str(exc_info.value)

    # Ensure no API calls were made
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
