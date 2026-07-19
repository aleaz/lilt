"""Tests for critique response parsing."""

import pytest

from lilt.llm.critique_parser import CritiqueParser


def test_parse_critique_with_reasoning_and_fenced_json():
    text = """<reasoning>
The draft looks good overall.
</reasoning>
```json
{"requires_refine": false, "issues": []}
```"""
    result = CritiqueParser.parse(text)
    assert result.requires_refine is False
    assert result.issues == []


def test_parse_critique_nested_json_in_reasoning():
    text = """<reasoning>
Example object {"nested": true} in reasoning.
</reasoning>
{"requires_refine": true, "issues": [{"category": "fluency", "description": "Awkward phrasing"}]}
"""
    result = CritiqueParser.parse(text)
    assert result.requires_refine is True
    assert len(result.issues) == 1
    assert result.issues[0].category == "fluency"


def test_parse_critique_with_unescaped_placeholder_quotes():
    """Gemma residual: placeholder tags with \" inside JSON strings."""
    text = (
        '{"requires_refine": true, "issues": [{"category": "accuracy", '
        '"description": "The placeholder <macro id="1"/> was incorrectly '
        "translated/replaced with '10%' and the original tag was lost.\"}]}"
    )
    attempt = CritiqueParser.try_parse_detailed(text)
    assert attempt.repaired is True
    assert attempt.result is not None
    assert attempt.result.requires_refine is True
    assert attempt.result.issues[0].description.startswith("The placeholder")


def test_try_parse_malformed_returns_none():
    assert CritiqueParser.try_parse("No JSON here, just prose.") is None
    with pytest.raises(ValueError, match="requires_refine"):
        CritiqueParser.parse("No JSON here, just prose.")


def test_try_parse_empty_returns_none():
    assert CritiqueParser.try_parse("") is None
    with pytest.raises(ValueError, match="requires_refine"):
        CritiqueParser.parse("")


def test_parse_critique_json_fence_with_nested_braces():
    text = """```json
{"requires_refine": false, "issues": []}
```"""
    result = CritiqueParser.parse(text)
    assert result.requires_refine is False
