"""Tests for critique response parsing."""

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


def test_parse_critique_malformed_defaults_to_refine():
    result = CritiqueParser.parse("No JSON here, just prose.")
    assert result.requires_refine is True
    assert result.issues == []


def test_parse_critique_empty_string():
    result = CritiqueParser.parse("")
    assert result.requires_refine is True


def test_parse_critique_json_fence_with_nested_braces():
    text = """```json
{"requires_refine": false, "issues": []}
```"""
    result = CritiqueParser.parse(text)
    assert result.requires_refine is False
