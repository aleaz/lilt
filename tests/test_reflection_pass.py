from unittest.mock import MagicMock, patch

import pytest

from lilt.llm.provider import LLMResponse
from lilt.llm.reflection_pass import (
    DENSE_SEGMENT_VALIDATION_RETRIES,
    REFINE_MAX_VALIDATION_RETRIES,
    run_critique,
    run_draft,
    run_refine,
    run_reflection_pass,
    validation_retries_for_source,
)
from lilt.validation.validators import ValidationError


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.reflection_enabled = True
    llm.generate_draft.return_value = LLMResponse(text="Hola draft")
    llm.generate_critique.return_value = LLMResponse(
        text='{"requires_refine": false, "issues": []}'
    )
    llm.generate_refine.return_value = LLMResponse(text="Hola refined")
    return llm


def test_run_reflection_pass_bypasses_non_linguistic_content(mock_llm):
    result = run_reflection_pass(mock_llm, '<macro id="1"/>')

    assert result.bypass is True
    assert result.text == '<macro id="1"/>'
    assert result.meta["bypass"] is True
    mock_llm.generate_draft.assert_not_called()


def test_run_reflection_pass_short_circuits_when_critique_accepts_draft(mock_llm):
    result = run_reflection_pass(mock_llm, "Hello")

    assert result.text == "Hola draft"
    assert result.meta["draft_accepted"] is True
    assert result.critique is not None
    assert result.refine is None
    mock_llm.generate_refine.assert_not_called()


def test_run_reflection_pass_runs_refine_when_critique_requires_changes(mock_llm):
    mock_llm.generate_critique.return_value = LLMResponse(
        text='{"requires_refine": true, "issues": [{"category": "other", "description": "fix"}]}'
    )

    result = run_reflection_pass(mock_llm, "Hello", max_validation_retries=0)

    assert result.text == "Hola refined"
    assert result.meta["draft_accepted"] is False
    mock_llm.generate_refine.assert_called_once()


def test_run_reflection_pass_skips_reflection_when_disabled(mock_llm):
    mock_llm.reflection_enabled = False

    result = run_reflection_pass(mock_llm, "Hello")

    assert result.text == "Hola draft"
    assert result.meta["used"] is False
    mock_llm.generate_critique.assert_not_called()


@patch("lilt.llm.reflection_pass.SegmentTranslationValidator.normalize_translation")
def test_run_refine_retries_on_validation_error(mock_normalize, mock_llm):
    mock_llm.generate_critique.return_value = LLMResponse(
        text='{"requires_refine": true, "issues": [{"category": "other", "description": "fix"}]}'
    )
    mock_llm.generate_refine.side_effect = [
        LLMResponse(text="bad"),
        LLMResponse(text="Hola refined"),
    ]

    def normalize(source, translated):
        if translated == "bad":
            raise ValidationError("Missing placeholder")
        return translated

    mock_normalize.side_effect = normalize
    result = run_refine(
        mock_llm,
        "Hola draft",
        '{"requires_refine": true, "issues": []}',
        "Hello",
        max_validation_retries=REFINE_MAX_VALIDATION_RETRIES,
    )

    assert result.text == "Hola refined"
    assert mock_llm.generate_refine.call_count == 2


def test_run_draft_and_critique_delegate_to_provider(mock_llm):
    draft = run_draft(mock_llm, "Hello")
    critique = run_critique(mock_llm, draft.text, "Hello")

    assert draft.text == "Hola draft"
    assert critique.requires_refine is False


def test_validation_retries_for_source_scales_with_density() -> None:
    sparse = "Hello world"
    dense = " ".join(f'<block id="{index}"/>' for index in range(20))
    assert validation_retries_for_source(sparse) == REFINE_MAX_VALIDATION_RETRIES
    assert validation_retries_for_source(dense) == DENSE_SEGMENT_VALIDATION_RETRIES
