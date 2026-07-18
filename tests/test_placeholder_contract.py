"""Tests for canonical placeholder contract and block compression."""

from __future__ import annotations

import pytest

from lilt.parser.placeholder_contract import (
    PLACEHOLDER_RE,
    extract,
    normalize_llm_placeholders,
    reject_zero_length_ranges,
    validate_counts,
)
from lilt.parser.placeholder_engine import PlaceholderEngine


def test_extract_normalizes_case() -> None:
    text = '<MACRO id="1"/> plain <math id="2"/>'
    assert extract(text) == ['<macro id="1"/>', '<math id="2"/>']


def test_validate_counts_detects_missing_and_added() -> None:
    source = 'Hello <macro id="1"/> world'
    with pytest.raises(ValueError, match="Missing"):
        validate_counts(source, "Hello world")
    with pytest.raises(ValueError, match="hallucinated"):
        validate_counts(source, source + ' <macro id="2"/>')


def test_normalize_llm_placeholders_repairs_malformed_id_close() -> None:
    broken = '<group_start id="8/>scikit-learn<group_end id="8/>'
    fixed = normalize_llm_placeholders(broken)
    assert '<group_start id="8"/>' in fixed
    assert '<group_end id="8"/>' in fixed


def test_normalize_llm_placeholders_repairs_emph_group_start() -> None:
    source = r'\emph<group_start id="2"/>Scikit-learn<group_end id="2"/>'
    broken = '<emph group_start id="2"/>Scikit-learn<group_end id="2"/>'
    fixed = normalize_llm_placeholders(broken, source)
    assert r'\emph<group_start id="2"/>' in fixed


def test_normalize_llm_placeholders_strips_html_closers() -> None:
    broken = r'\emph<group_start id="8"/>text</emph><block id="3"/>'
    fixed = normalize_llm_placeholders(broken)
    assert "</emph>" not in fixed


def test_normalize_llm_placeholders_preserves_text_between_valid_tokens() -> None:
    source = r'\emph<group_start id="2"/>Scikit-learn<group_end id="2"/> text'
    broken = (
        '<macro id="1"/>'
        r'\emph<group_start id="2"/>Scikit-learn<group_end id="2"/> traducido'
    )
    fixed = normalize_llm_placeholders(broken, source)
    assert "Scikit-learn" in fixed
    assert "traducido" in fixed
    assert '<macro id="1"/>' not in fixed


def test_normalize_llm_placeholders_strips_hallucinated_macro() -> None:
    source = r'\emph<group_start id="2"/>Scikit-learn<group_end id="2"/>'
    broken = '<macro id="1"/><emph group_start id="2"/>Scikit-learn<group_end id="2"/>'
    fixed = normalize_llm_placeholders(broken, source)
    validate_counts(source, fixed)


def test_restore_dropped_comment_placeholders() -> None:
    source = (
        'Paragraph one <cite id="1"/>.\n'
        '<comment id="2"/>Paragraph two.\n'
        '<comment id="1"/>Paragraph three.'
    )
    broken = 'Párrafo uno <cite id="1"/>.\n\nPárrafo dos.\n\nPárrafo tres.'
    fixed = normalize_llm_placeholders(broken, source)
    validate_counts(source, fixed)


def test_reject_zero_length_ranges() -> None:
    with pytest.raises(ValueError, match="Zero-length"):
        reject_zero_length_ranges([(0, 0, "MACRO", "")])


def test_compress_blocks_merges_adjacent_placeholders() -> None:
    engine = PlaceholderEngine()
    text = '<macro id="1"/> <macro id="2"/> text <math id="3"/>'
    compressed = engine.compress_blocks(text)
    assert PLACEHOLDER_RE.findall(compressed)
    assert compressed.count("<block id=") >= 1
    assert '<macro id="1"/>' not in compressed


def test_compress_blocks_preserves_separated_placeholders() -> None:
    engine = PlaceholderEngine()
    text = '<macro id="1"/>word<macro id="2"/>'
    assert engine.compress_blocks(text) == text
