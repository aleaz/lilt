"""Text helpers for detecting translatable linguistic content using heuristics."""

import re
from dataclasses import dataclass
from typing import Protocol

_PLACEHOLDER_RE = re.compile(r"<[a-z_]+ id=\"\d+\"/>")
_WORD_RE = re.compile(r"[a-zA-Z\u00C0-\u024F\u0400-\u04FF]{3,}")
_LATEX_CMD_PREFIX_RE = re.compile(r"\\[a-z]+(?=[A-Za-z])")
_CJK_OR_ARABIC_RE = re.compile(
    r"[\u4e00-\u9fff\u3040-\u30ff\uAC00-\uD7AF\u0600-\u06FF]{2,}"
)
_TEX_PARAM_RE = re.compile(r"#\d")
_TEX_INTERNAL_AT_RE = re.compile(r"@\w+")
_DIMENSION_TOKEN_RE = re.compile(
    r"(?:\d*\.\d+|\d+)\s*(?:in|pt|em|ex|true|false)\b", re.IGNORECASE
)
_PROSE_HINT_RE = re.compile(
    r"\b(?:the|and|or|for|with|from|that|this|are|was|were|have|has|been|will|see|fig|figure|hello|hola)\b",
    re.IGNORECASE,
)
_SENTENCE_PUNCT_RE = re.compile(r"\w[.!?](?:\s|$)")


@dataclass
class TextContext:
    """Features extracted from a segment for linguistic heuristics."""

    text: str
    linguistic_text: str
    placeholder_ratio: float
    word_count: int
    alpha_chars: int
    tex_params: int
    dimension_tokens: int
    at_token_count: int
    has_prose_hint: bool


class HeuristicRule(Protocol):
    """Protocol for ordered linguistic-content heuristic rules."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Return True to accept, False to reject, None to continue to next rule."""
        pass


class EmptyTextRule:
    """Reject empty or non-alphabetic text."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the empty-text rule."""
        if not ctx.text or not ctx.text.strip() or ctx.alpha_chars == 0:
            return False
        return None


class NonLatinScriptRule:
    """Accept CJK or Arabic script as linguistic content."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the non-Latin script rule."""
        if _CJK_OR_ARABIC_RE.search(ctx.linguistic_text):
            return True
        return None


class NoWordsRule:
    """Reject text with no word-like tokens."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the no-words rule."""
        if ctx.word_count == 0:
            return False
        return None


class MultiTexParamRule:
    """Reject TeX macro-parameter-heavy fragments."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the multi TeX-param rule."""
        if ctx.tex_params >= 2:
            return False
        return None


class ShortProseRule:
    """Accept short single-word prose without TeX params."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the short-prose rule."""
        if (
            ctx.tex_params == 0
            and ctx.placeholder_ratio < 0.85
            and ctx.word_count == 1
            and ctx.alpha_chars >= 3
            and not _DIMENSION_TOKEN_RE.search(ctx.linguistic_text)
            and not _TEX_INTERNAL_AT_RE.search(ctx.linguistic_text)
        ):
            return True
        return None


class StrongProseHintRule:
    """Accept text with strong prose lexical hints."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the strong prose-hint rule."""
        if (
            ctx.has_prose_hint
            and ctx.tex_params == 0
            and ctx.alpha_chars >= 5
            and ctx.placeholder_ratio < 0.85
        ):
            return True
        return None


class TexParamRatioRule:
    """Reject TeX-param text with high placeholder ratio."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the TeX-param ratio rule."""
        if ctx.tex_params >= 1 and ctx.placeholder_ratio > 0.15:
            return False
        if ctx.tex_params >= 1 and ctx.alpha_chars < 25:
            return False
        return None


class SentencePunctuationRule:
    """Accept multi-word text with sentence punctuation or prose hints."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the sentence-punctuation rule."""
        if ctx.word_count >= 3 and ctx.has_prose_hint:
            return True
        if (
            ctx.word_count >= 2
            and ctx.alpha_chars >= 8
            and ctx.tex_params == 0
            and (ctx.has_prose_hint or _SENTENCE_PUNCT_RE.search(ctx.linguistic_text))
        ):
            return True
        return None


class InfrastructureCodeRule:
    """Reject dimension-heavy or internal TeX infrastructure text."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the infrastructure-code rule."""
        if ctx.dimension_tokens >= 2 and ctx.placeholder_ratio > 0.3:
            return False
        if ctx.at_token_count >= 2 and ctx.alpha_chars < 30:
            return False
        return None


class HighPlaceholderRatioRule:
    """Reject mostly-placeholder segments with little prose."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the high placeholder-ratio rule."""
        if ctx.placeholder_ratio > 0.7 and ctx.alpha_chars < 40:
            return False
        if ctx.placeholder_ratio > 0.5 and ctx.word_count < 2:
            return False
        return None


class IsolatedWordRule:
    """Reject very short isolated single words."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the isolated-word rule."""
        if ctx.word_count == 1 and ctx.alpha_chars < 12:
            return False
        return None


class FallbackRule:
    """Default accept when enough alphabetic content remains."""

    def evaluate(self, ctx: TextContext) -> bool | None:
        """Apply the fallback alphabetic-length rule."""
        return ctx.alpha_chars >= 8


_HEURISTIC_RULES: list[HeuristicRule] = [
    EmptyTextRule(),
    NonLatinScriptRule(),
    NoWordsRule(),
    MultiTexParamRule(),
    ShortProseRule(),
    StrongProseHintRule(),
    TexParamRatioRule(),
    SentencePunctuationRule(),
    InfrastructureCodeRule(),
    HighPlaceholderRatioRule(),
    IsolatedWordRule(),
    FallbackRule(),
]


def _count_words(clean_text: str) -> int:
    return len(_WORD_RE.findall(clean_text))


def _strip_latex_command_prefixes(clean_text: str) -> str:
    r"""Remove residual \\macro names left when placeholders mask macro arguments."""
    return _LATEX_CMD_PREFIX_RE.sub("", clean_text)


def has_linguistic_content(text: str) -> bool:
    """Determine if a segment contains linguistic text that requires translation.

    Uses a chain of heuristic rules to evaluate the text content.
    """
    if not text or not text.strip():
        return False

    placeholder_matches = _PLACEHOLDER_RE.findall(text)
    placeholder_chars = sum(len(match) for match in placeholder_matches)
    clean_text = _PLACEHOLDER_RE.sub("", text)
    linguistic_text = _strip_latex_command_prefixes(clean_text).strip()

    total_len = len(text)
    placeholder_ratio = placeholder_chars / total_len if total_len else 0.0

    ctx = TextContext(
        text=text,
        linguistic_text=linguistic_text,
        placeholder_ratio=placeholder_ratio,
        word_count=_count_words(linguistic_text),
        alpha_chars=sum(1 for char in linguistic_text if char.isalpha()),
        tex_params=len(_TEX_PARAM_RE.findall(linguistic_text)),
        dimension_tokens=len(_DIMENSION_TOKEN_RE.findall(linguistic_text)),
        at_token_count=len(_TEX_INTERNAL_AT_RE.findall(linguistic_text)),
        has_prose_hint=bool(_PROSE_HINT_RE.search(linguistic_text)),
    )

    for rule in _HEURISTIC_RULES:
        result = rule.evaluate(ctx)
        if result is not None:
            return result

    return False
