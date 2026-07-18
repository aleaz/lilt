"""Validators for placeholder integrity, LaTeX syntax, and build output."""

import re

from lilt.exceptions import TranslationValidationError
from lilt.parser.placeholder_contract import normalize_llm_placeholders, validate_counts


class ValidationError(TranslationValidationError):
    """Internal structural/lexical validation failure (domain error)."""

    def __init__(self, message: str, *, attempt_text: str | None = None) -> None:
        super().__init__(message)
        self.attempt_text = attempt_text


class PlaceholderValidator:
    """Ensures that all placeholders present in the source segment are preserved in the translation."""

    @staticmethod
    def normalize(source_text: str, translated_text: str) -> str:
        """Return placeholder-normalized translation text."""
        try:
            cleaned = normalize_llm_placeholders(translated_text, source_text)
            validate_counts(source_text, cleaned)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return cleaned

    @staticmethod
    def validate(source_text: str, translated_text: str) -> None:
        """Validates that all placeholders in the source text are present in the translation."""
        PlaceholderValidator.normalize(source_text, translated_text)


class SyntaxValidator:
    """Ensures structural integrity of the LaTeX strings returned by the LLM, including balanced braces and rejection of hallucinated math symbols like unescaped ^ or _."""

    @staticmethod
    def validate(source_text: str, translated_text: str) -> None:
        """Validates the structural integrity of the translated text.

        Ensures balanced braces, inline math, display math, and rejects hallucinated
        unescaped carets and underscores.

        Args:
            source_text: The original segment text.
            translated_text: The translated segment text.

        Raises:
            ValidationError: If structural syntax checks fail.
        """
        # 1. Check balanced braces { }
        # Ignoring escaped braces \{ and \}
        source_open_braces = len(re.findall(r"(?<!\\)(?:\\\\)*\{", source_text))
        source_close_braces = len(re.findall(r"(?<!\\)(?:\\\\)*\}", source_text))
        source_delta = source_open_braces - source_close_braces

        trans_open_braces = len(re.findall(r"(?<!\\)(?:\\\\)*\{", translated_text))
        trans_close_braces = len(re.findall(r"(?<!\\)(?:\\\\)*\}", translated_text))
        trans_delta = trans_open_braces - trans_close_braces

        if source_delta != trans_delta:
            raise ValidationError(
                f"Unbalanced braces: expected delta {source_delta}, got {trans_delta}."
            )

        # 2. Check balanced inline math $ $
        # Ignoring escaped dollar signs \$
        dollars = len(re.findall(r"(?<!\\)(?:\\\\)*\$", translated_text))
        if dollars % 2 != 0:
            raise ValidationError(
                f"Unbalanced inline math ($): found {dollars} unescaped dollar signs."
            )

        # 3. Check balanced display math \[ \]
        open_brackets = len(re.findall(r"\\\[", translated_text))
        close_brackets = len(re.findall(r"\\\]", translated_text))
        if open_brackets != close_brackets:
            raise ValidationError(
                f"Unbalanced display math: {open_brackets} open (\\[), {close_brackets} close (\\])."
            )

        # 4. Check for hallucinated math characters (^ and _)
        source_carets = len(re.findall(r"(?<!\\)(?:\\\\)*\^", source_text))
        trans_carets = len(re.findall(r"(?<!\\)(?:\\\\)*\^", translated_text))
        if trans_carets > source_carets:
            raise ValidationError(
                f"Hallucinated unescaped caret (^): source had {source_carets}, translation has {trans_carets}."
            )

        source_underscores = len(re.findall(r"(?<!\\)(?:\\\\)*_", source_text))
        trans_underscores = len(re.findall(r"(?<!\\)(?:\\\\)*_", translated_text))
        if trans_underscores > source_underscores:
            raise ValidationError(
                f"Hallucinated unescaped underscore (_): source had {source_underscores}, translation has {trans_underscores}."
            )


class BuildValidator:
    """Validates TM placeholder contracts during document reconstruction."""

    @staticmethod
    def validate_placeholder_mapping(
        segment_id: str,
        persisted: dict[str, str],
        fresh: dict[str, str],
    ) -> None:
        """Ensure persisted TM placeholders match the current parse mapping.

        Build uses the persisted mapping as the reproducibility contract. Drift
        between sync-time and build-time parser output indicates re-sync is required.
        """
        if persisted == fresh:
            return
        if not persisted and fresh:
            raise ValidationError(
                f"Segment '{segment_id}' has no persisted placeholders but the "
                "re-parsed source produced a mapping. Run 'lilt pipeline sync'."
            )
        if persisted and not fresh:
            raise ValidationError(
                f"Segment '{segment_id}' has persisted placeholders but the "
                "re-parsed source produced none. Run 'lilt pipeline sync'."
            )
        persisted_keys = set(persisted.keys())
        fresh_keys = set(fresh.keys())
        if persisted_keys != fresh_keys:
            missing = fresh_keys - persisted_keys
            extra = persisted_keys - fresh_keys
            details: list[str] = []
            if missing:
                details.append(f"missing in TM: {sorted(missing)}")
            if extra:
                details.append(f"stale in TM: {sorted(extra)}")
            raise ValidationError(
                f"Placeholder mapping drift for segment '{segment_id}' "
                f"({'; '.join(details)}). Run 'lilt pipeline sync' before build."
            )
        for key in persisted_keys:
            if persisted[key] != fresh[key]:
                raise ValidationError(
                    f"Placeholder content drift for '{key}' in segment '{segment_id}'. "
                    "Run 'lilt pipeline sync' before build."
                )


class SegmentTranslationValidator:
    """Unified validation gate for machine and human translation submissions."""

    @staticmethod
    def normalize_translation(source_text: str, translated_text: str) -> str:
        """Validate and return the persisted-safe translation text."""
        cleaned = PlaceholderValidator.normalize(source_text, translated_text)
        SyntaxValidator.validate(source_text, cleaned)
        return cleaned

    @staticmethod
    def validate(source_text: str, translated_text: str) -> None:
        """Run placeholder and syntax validators on a translation candidate."""
        SegmentTranslationValidator.normalize_translation(source_text, translated_text)

    @staticmethod
    def try_normalize_draft(source_text: str, draft_text: str) -> str | None:
        """Return normalized draft text when it passes validation, else None."""
        if not draft_text:
            return None
        try:
            return SegmentTranslationValidator.normalize_translation(
                source_text, draft_text
            )
        except ValidationError:
            return None
