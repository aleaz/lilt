"""Tests for persisted translation normalization."""

from lilt.validation.validators import SegmentTranslationValidator


def test_normalize_translation_persists_comment_placeholders() -> None:
    source = (
        'Paragraph one <cite id="1"/>.\n'
        '<comment id="2"/>Paragraph two.\n'
        '<comment id="1"/>Paragraph three.'
    )
    broken = 'Párrafo uno <cite id="1"/>.\n\nPárrafo dos.\n\nPárrafo tres.'
    normalized = SegmentTranslationValidator.normalize_translation(source, broken)
    assert '<comment id="2"/>' in normalized
    assert '<comment id="1"/>' in normalized


def test_try_normalize_draft_returns_none_on_invalid() -> None:
    source = 'Hello <macro id="1"/>'
    assert SegmentTranslationValidator.try_normalize_draft(source, "Hola") is None
