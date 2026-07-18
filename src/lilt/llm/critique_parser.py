"""Parse structured critique responses from LLM output."""

import json
import re

from lilt.models.critique import CritiqueResult

_JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


class CritiqueParser:
    """Extracts structured critique results from free-form LLM output."""

    @staticmethod
    def parse(text: str) -> CritiqueResult:
        """Extract a CritiqueResult from free-form critique LLM output.

        Tries fenced ```json blocks first, then scans for the last valid JSON object.
        Defaults to requires_refine=True when parsing fails.
        """
        if not text or not text.strip():
            return CritiqueResult(requires_refine=True, issues=[])

        fence_matches = list(_JSON_FENCE_RE.finditer(text))
        if fence_matches:
            candidate = fence_matches[-1].group(1)
            parsed = CritiqueParser._try_parse(candidate)
            if parsed is not None:
                return parsed

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
                        parsed = CritiqueParser._try_parse(text[start : end + 1])
                        if parsed is not None:
                            return parsed
                        break

        return CritiqueResult(requires_refine=True, issues=[])

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
