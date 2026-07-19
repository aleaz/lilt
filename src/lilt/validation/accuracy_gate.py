"""Deterministic placeholder/syntax accuracy gate for draft translations.

Separates structural integrity from LLM editorial critique so free-text JSON
descriptions never own the accuracy decision.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from lilt.models.critique import CritiqueResult, TranslationIssue
from lilt.parser.placeholder_contract import (
    PLACEHOLDER_RE,
    extract,
    normalize_llm_placeholders,
)
from lilt.validation.validators import SegmentTranslationValidator, ValidationError

_PLACEHOLDER_REF_RE = re.compile(r'<([a-z_]+) id="(\d+)"/>', re.IGNORECASE)


def placeholder_ref(token: str) -> str:
    """Return a JSON-safe citation like ``macro#1`` for a placeholder token."""
    match = _PLACEHOLDER_REF_RE.fullmatch(token.strip())
    if match:
        return f"{match.group(1).lower()}#{match.group(2)}"
    return token.strip()


@dataclass
class AccuracyGateResult:
    """Outcome of a deterministic accuracy check on a draft."""

    ok: bool
    issues: list[TranslationIssue] = field(default_factory=list)

    def to_critique_json(self) -> str:
        """Serialize as critique JSON (safe: descriptions use type#id refs)."""
        result = CritiqueResult(requires_refine=not self.ok, issues=list(self.issues))
        return json.dumps(result.model_dump(), ensure_ascii=False)


class AccuracyGate:
    """Machine accuracy gate over :class:`SegmentTranslationValidator`."""

    @staticmethod
    def evaluate(source_text: str, draft_text: str) -> AccuracyGateResult:
        """Return whether draft preserves placeholders/syntax vs source."""
        if not draft_text:
            return AccuracyGateResult(
                ok=False,
                issues=[
                    TranslationIssue(
                        category="accuracy",
                        description="Draft is empty",
                    )
                ],
            )
        try:
            SegmentTranslationValidator.validate(source_text, draft_text)
            return AccuracyGateResult(ok=True, issues=[])
        except ValidationError as exc:
            issues = AccuracyGate._issues_from_mismatch(source_text, draft_text)
            if not issues:
                issues = [
                    TranslationIssue(
                        category="accuracy",
                        description=str(exc).replace('"', "'"),
                    )
                ]
            return AccuracyGateResult(ok=False, issues=issues)

    @staticmethod
    def _issues_from_mismatch(
        source_text: str, draft_text: str
    ) -> list[TranslationIssue]:
        cleaned = normalize_llm_placeholders(draft_text, source_text)
        source_tokens = extract(source_text)
        draft_tokens = extract(cleaned)
        source_counts = Counter(source_tokens)
        draft_counts = Counter(draft_tokens)
        issues: list[TranslationIssue] = []
        for token in sorted(set(source_counts) | set(draft_counts)):
            expected = source_counts[token]
            got = draft_counts[token]
            if expected == got:
                continue
            ref = placeholder_ref(token)
            if got < expected:
                issues.append(
                    TranslationIssue(
                        category="accuracy",
                        description=(
                            f"Missing or under-counted placeholder {ref} "
                            f"(expected {expected}, got {got})"
                        ),
                    )
                )
            else:
                issues.append(
                    TranslationIssue(
                        category="accuracy",
                        description=(
                            f"Extra or over-counted placeholder {ref} "
                            f"(expected {expected}, got {got})"
                        ),
                    )
                )
        if issues:
            return issues
        # Syntax-only failure: no placeholder multiset diff.
        source_ph = len(PLACEHOLDER_RE.findall(source_text))
        draft_ph = len(PLACEHOLDER_RE.findall(cleaned))
        if source_ph != draft_ph:
            issues.append(
                TranslationIssue(
                    category="accuracy",
                    description=(
                        f"Placeholder count mismatch "
                        f"(source {source_ph}, draft {draft_ph})"
                    ),
                )
            )
        return issues
