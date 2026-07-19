"""Merge deterministic AccuracyGate with LLM critique parse/degrade policy."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lilt.llm.critique_parser import CritiqueParser
from lilt.llm.provider import LLMResponse
from lilt.models.critique import CritiqueResult
from lilt.validation.accuracy_gate import AccuracyGateResult

logger = logging.getLogger(__name__)

CRITIQUE_JSON_RETRY_HINT = (
    "\n\n[critique_json_retry] Previous critique was not valid JSON. "
    "Return ONLY strict JSON with boolean requires_refine. "
    "Refer placeholders as type#id (e.g. macro#1); never paste raw tags "
    "with double quotes inside JSON strings."
)

BYPASS_CRITIQUE_PAYLOAD = '{"requires_refine": false, "issues": []}'


@dataclass
class CritiqueGateDecision:
    """Final critique text/flags after AccuracyGate merge and degrade policy."""

    text: str
    response: LLMResponse
    parsed: CritiqueResult | None
    requires_refine: bool
    parse_ok: bool
    parse_repaired: bool = False
    degraded: bool = False
    accuracy_forced: bool = False


def merge_critique_with_accuracy(
    accuracy: AccuracyGateResult,
    *,
    critique_text: str,
    response: LLMResponse,
    parsed: CritiqueResult | None,
    parse_ok: bool,
    parse_repaired: bool = False,
) -> CritiqueGateDecision:
    """Combine AccuracyGate with editorial critique into a final gate decision."""
    if not parse_ok:
        if not accuracy.ok:
            synthetic = accuracy.to_critique_json()
            if response.retry_reason is None:
                response.retry_reason = "critique_parse_degraded"
            logger.warning(
                "Critique JSON unusable; degrading to AccuracyGate force-refine "
                "(retry_reason=critique_parse_degraded)"
            )
            return CritiqueGateDecision(
                text=synthetic,
                response=response,
                parsed=CritiqueParser.try_parse(synthetic),
                requires_refine=True,
                parse_ok=True,
                parse_repaired=parse_repaired,
                degraded=True,
                accuracy_forced=True,
            )
        response.bypass = True
        if response.retry_reason is None:
            response.retry_reason = "critique_parse_degraded"
        logger.warning(
            "Critique JSON unusable; AccuracyGate ok — accepting draft "
            "(retry_reason=critique_parse_degraded)"
        )
        return CritiqueGateDecision(
            text=BYPASS_CRITIQUE_PAYLOAD,
            response=response,
            parsed=CritiqueResult(requires_refine=False, issues=[]),
            requires_refine=False,
            parse_ok=True,
            parse_repaired=parse_repaired,
            degraded=True,
            accuracy_forced=False,
        )

    assert parsed is not None
    requires = parsed.requires_refine
    text = critique_text
    accuracy_forced = False
    if not accuracy.ok and not requires:
        requires = True
        accuracy_forced = True
        text = accuracy.to_critique_json()
        parsed = CritiqueParser.try_parse(text) or CritiqueResult(
            requires_refine=True, issues=list(accuracy.issues)
        )
        if response.retry_reason is None:
            response.retry_reason = "accuracy_gate_forced_refine"
        logger.info(
            "AccuracyGate forced refine despite editorial accept "
            "(retry_reason=accuracy_gate_forced_refine)"
        )
    elif not accuracy.ok and requires:
        if CritiqueParser.try_parse(text) is None:
            text = accuracy.to_critique_json()
            parsed = CritiqueParser.try_parse(text)
        accuracy_forced = True

    if parse_repaired and response.retry_reason is None:
        response.retry_reason = "critique_parse_repaired"

    return CritiqueGateDecision(
        text=text,
        response=response,
        parsed=parsed,
        requires_refine=requires,
        parse_ok=True,
        parse_repaired=parse_repaired,
        degraded=False,
        accuracy_forced=accuracy_forced,
    )
