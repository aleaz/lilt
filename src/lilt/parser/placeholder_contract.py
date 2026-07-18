"""Canonical placeholder token format shared by engine, validation, and build."""

import re
from collections import Counter

PLACEHOLDER_RE = re.compile(r"<[a-z_]+ id=\"\d+\"/>", re.IGNORECASE)
_MALFORMED_ID_CLOSE_RE = re.compile(
    r'(<[a-z_]+ id=")(\d+)/?(?=[^"]*/>)',
    re.IGNORECASE,
)
_EMPH_GROUP_START_RE = re.compile(
    r"<emph\s+group_start\s+id=\"(\d+)\"/>",
    re.IGNORECASE,
)
_HTML_CLOSER_RE = re.compile(
    r"</(?:emph|block|group_start|group_end|macro)[^>]*>",
    re.IGNORECASE,
)
_COMMENT_RE = re.compile(r'<comment id="\d+"/>', re.IGNORECASE)
_MALFORMED_PLACEHOLDER_TAIL_RE = re.compile(
    r'(<[a-z_]+ id="\d+/)[^<]*(?=<[a-z_]+ id=)',
    re.IGNORECASE,
)


def _strip_hallucinated_placeholders(text: str, source_text: str) -> str:
    """Remove placeholder tokens that do not appear in the source multiset."""
    if not source_text:
        return text
    allowed = set(extract(source_text))

    def _keep(match: re.Match[str]) -> str:
        token = match.group(0).lower()
        return match.group(0) if token in allowed else ""

    return PLACEHOLDER_RE.sub(_keep, text)


def restore_dropped_comment_placeholders(text: str, source_text: str) -> str:
    """Reinsert comment placeholders dropped across paragraph boundaries."""
    source_comments = _COMMENT_RE.findall(source_text)
    if not source_comments or _COMMENT_RE.search(text):
        return text
    paragraphs = [
        part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()
    ]
    if len(paragraphs) != len(source_comments) + 1:
        return text
    rebuilt: list[str] = []
    for index, paragraph in enumerate(paragraphs):
        if index > 0:
            paragraph = f"{source_comments[index - 1]}{paragraph}"
        rebuilt.append(paragraph)
    return "\n\n".join(rebuilt)


def normalize_llm_placeholders(text: str, source_text: str = "") -> str:
    r"""Repair common LLM placeholder typos before validation.

    Fixes unclosed quote in ``id="N/>``, HTML-style closers, and fused
    ``<emph group_start .../>`` tokens when the source uses ``\\emph<group_start``.
    """
    if not text:
        return text
    normalized = _HTML_CLOSER_RE.sub("", text)
    normalized = _MALFORMED_ID_CLOSE_RE.sub(r'\1\2"/>', normalized)
    if r"\emph<group_start" in source_text:
        normalized = _EMPH_GROUP_START_RE.sub(
            r'\\emph<group_start id="\1"/>',
            normalized,
        )
    # Drop text accidentally merged into a still-malformed placeholder tail.
    normalized = _MALFORMED_PLACEHOLDER_TAIL_RE.sub(r"\1", normalized)
    normalized = _strip_hallucinated_placeholders(normalized, source_text)
    normalized = restore_dropped_comment_placeholders(normalized, source_text)
    return normalized


def extract(text: str) -> list[str]:
    """Return placeholder tokens normalized to lowercase."""
    return [match.lower() for match in PLACEHOLDER_RE.findall(text)]


def validate_counts(source_text: str, translated_text: str) -> None:
    """Raise ValueError when placeholder multiset differs."""
    source_sorted = sorted(extract(source_text))
    translated_sorted = sorted(extract(translated_text))
    if source_sorted == translated_sorted:
        return
    missing = set(source_sorted) - set(translated_sorted)
    added = set(translated_sorted) - set(source_sorted)
    error_msg = "Placeholder mismatch."
    if missing:
        error_msg += f" Missing: {missing}."
    if added:
        error_msg += f" Added (hallucinated): {added}."
    if not missing and not added:
        src_counts = Counter(source_sorted)
        tr_counts = Counter(translated_sorted)
        diffs = [
            f"{tok}: expected {src_counts[tok]}, got {tr_counts[tok]}"
            for tok in sorted(src_counts.keys() | tr_counts.keys())
            if src_counts[tok] != tr_counts[tok]
        ]
        error_msg += f" Count mismatch ({'; '.join(diffs)})."
    raise ValueError(error_msg)


def reject_zero_length_ranges(ranges: list[tuple[int, int, str, str]]) -> None:
    """Reject opaque ranges with zero length."""
    for _start, length, _, _ in ranges:
        if length <= 0:
            raise ValueError("Zero-length opaque range is not allowed.")
