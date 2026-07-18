import pytest

from lilt.validation.validators import (
    PlaceholderValidator,
    SegmentTranslationValidator,
    SyntaxValidator,
    ValidationError,
)


def test_placeholder_validator_exact_match():
    # Identical placeholders
    source = 'Hello <macro id="1"/>, test <macro id="2"/>.'
    trans = 'Hola <macro id="1"/>, prueba <macro id="2"/>.'
    # Should not raise any error
    PlaceholderValidator.validate(source, trans)


def test_placeholder_validator_reordered():
    # Order doesn't matter
    source = 'Hello <macro id="1"/>, test <macro id="2"/>.'
    trans = 'Prueba <macro id="2"/>, hola <macro id="1"/>.'
    PlaceholderValidator.validate(source, trans)


def test_placeholder_validator_missing():
    source = 'Hello <macro id="1"/>, test <macro id="2"/>.'
    trans = 'Hola, prueba <macro id="2"/>.'
    with pytest.raises(ValidationError) as exc:
        PlaceholderValidator.validate(source, trans)
    assert "Missing: {'<macro id=\"1\"/>'}" in str(exc.value)


def test_placeholder_validator_hallucinated():
    source = 'Hello <macro id="1"/>.'
    trans = 'Hola <macro id="1"/>, prueba <macro id="2"/>.'
    cleaned = PlaceholderValidator.normalize(source, trans)
    assert '<macro id="1"/>' in cleaned
    assert '<macro id="2"/>' not in cleaned


def test_syntax_validator_balanced_braces():
    source = "Math {a} and {b}."
    trans = "Matemáticas {a} y {b}."
    SyntaxValidator.validate(source, trans)

    # Missing a brace
    trans_missing = "Matemáticas {a y {b}."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_missing)
    assert "Unbalanced braces" in str(exc.value)


def test_syntax_validator_escaped_braces():
    source = r"Escaped \{ and \} should not count."
    trans = r"Escapado \{ y \} no deben contar."
    SyntaxValidator.validate(source, trans)

    # An extra unescaped brace in translation
    trans_extra = r"Escapado \{ y \} no {deben contar."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_extra)
    assert "Unbalanced braces" in str(exc.value)


def test_syntax_validator_inline_math():
    source = "Math $a + b$."
    trans = "Matemáticas $a + b$."
    SyntaxValidator.validate(source, trans)

    # Odd number of dollar signs in translation
    trans_odd = "Matemáticas $a + b."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_odd)
    assert "Unbalanced inline math" in str(exc.value)


def test_syntax_validator_display_math():
    source = r"Equation \[ a = b \]."
    trans = r"Ecuación \[ a = b \]."
    SyntaxValidator.validate(source, trans)

    trans_unbalanced = r"Ecuación \[ a = b."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_unbalanced)
    assert "Unbalanced display math" in str(exc.value)


def test_syntax_validator_hallucinated_carets_and_underscores():
    source = "No math symbols here."
    trans_caret = "No math symbols ^ here."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_caret)
    assert "Hallucinated unescaped caret" in str(exc.value)

    trans_underscore = "No math symbols _ here."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_underscore)
    assert "Hallucinated unescaped underscore" in str(exc.value)

    # Valid if they are in the source
    source_math = "Math $a^2_b$."
    trans_math = "Matemáticas $a^2_b$."
    SyntaxValidator.validate(source_math, trans_math)

    # Valid if they are escaped
    source_no_math = "No math."
    trans_escaped = r"Sin matemáticas \_ y \^."
    SyntaxValidator.validate(source_no_math, trans_escaped)


def test_segment_translation_validator_delegates():
    source = 'Hello <macro id="1"/>.'
    SegmentTranslationValidator.validate(source, 'Hola <macro id="1"/>.')
    with pytest.raises(ValidationError):
        SegmentTranslationValidator.validate(source, "Hola sin placeholder.")


def test_syntax_validator_even_escaped_braces():
    # \\{ is an escaped backslash followed by an unescaped brace
    source = r"Escaped backslash \\{ should count as unescaped brace. }"
    trans = r"Escaped backslash \\{ should count as unescaped brace. }"
    SyntaxValidator.validate(source, trans)

    # If it is unbalanced because one \\{ has no close brace
    trans_unbalanced = r"Escaped backslash \\{ missing close brace."
    with pytest.raises(ValidationError) as exc:
        SyntaxValidator.validate(source, trans_unbalanced)
    assert "Unbalanced braces" in str(exc.value)
