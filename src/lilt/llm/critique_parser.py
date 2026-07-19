"""Parse structured critique responses from LLM output."""

import json
import re
from dataclasses import dataclass

from lilt.models.critique import CritiqueResult

_JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
# LLMs often paste LILT placeholders with double-quoted id attrs inside JSON
# strings, which breaks json.loads. Rewrite to single-quoted attrs for parse.
_PLACEHOLDER_DQUOTE_RE = re.compile(
    r"<([a-z_]+)\s+id=\"(\d+)\"\s*/>",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CritiqueParseAttempt:
    """Parse outcome including whether a known repair was applied."""

    result: CritiqueResult | None
    repaired: bool = False


class CritiqueParser:
    """Extracts structured critique results from free-form LLM output."""

    @staticmethod
    def repair_placeholder_quotes(raw: str) -> tuple[str, bool]:
        """Rewrite ``<tag id="N"/>`` to single-quoted attrs inside candidate JSON."""
        if not raw:
            return raw, False
        repaired, count = _PLACEHOLDER_DQUOTE_RE.subn(
            r"<\1 id='\2'/>",
            raw,
        )
        return repaired, count > 0

    @staticmethod
    def try_parse_detailed(text: str) -> CritiqueParseAttempt:
        """Return parse attempt with repair metadata."""
        if not text or not text.strip():
            return CritiqueParseAttempt(result=None, repaired=False)

        fence_matches = list(_JSON_FENCE_RE.finditer(text))
        if fence_matches:
            candidate = fence_matches[-1].group(1)
            attempt = CritiqueParser._try_parse_candidate(candidate)
            if attempt.result is not None:
                return attempt

        brace_positions = [i for i, ch in enumerate(text) if ch == "{"]
        for start in reversed(brace_positions):
            depth = 0
            for end in range(start, len(text)):
                char = text[end]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        attempt = CritiqueParser._try_parse_candidate(
                            text[start : end + 1]
                        )
                        if attempt.result is not None:
                            return attempt
                        break

        return CritiqueParseAttempt(result=None, repaired=False)

    @staticmethod
    def try_parse(text: str) -> CritiqueResult | None:
        """Return CritiqueResult when JSON with ``requires_refine`` is found.

        Tries fenced ```json blocks first, then scans for the last valid JSON object.
        Returns ``None`` when the text is empty or no valid critique payload exists.
        """
        return CritiqueParser.try_parse_detailed(text).result

    @staticmethod
    def parse(text: str) -> CritiqueResult:
        """Extract a CritiqueResult or raise ValueError when structure is missing.

        Prefer :meth:`try_parse` when callers need soft failure.
        """
        parsed = CritiqueParser.try_parse(text)
        if parsed is None:
            raise ValueError(
                "Critique output is not valid JSON with a boolean requires_refine field"
            )
        return parsed

    @staticmethod
    def _try_parse_candidate(raw: str) -> CritiqueParseAttempt:
        parsed = CritiqueParser._try_parse(raw)
        if parsed is not None:
            return CritiqueParseAttempt(result=parsed, repaired=False)
        repaired_raw, did_repair = CritiqueParser.repair_placeholder_quotes(raw)
        if not did_repair:
            return CritiqueParseAttempt(result=None, repaired=False)
        parsed = CritiqueParser._try_parse(repaired_raw)
        return CritiqueParseAttempt(result=parsed, repaired=parsed is not None)

    @staticmethod
    def _try_parse(raw: str) -> CritiqueResult | None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        if "requires_refine" not in data:
            return None
        try:
            return CritiqueResult.model_validate(data)
        except Exception:
            requires_refine = data.get("requires_refine", True)
            if isinstance(requires_refine, bool):
                return CritiqueResult(requires_refine=requires_refine, issues=[])
            return None
