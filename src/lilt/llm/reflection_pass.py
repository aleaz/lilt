"""Pure reflection-stage execution: draft, critique, and refine."""

from dataclasses import dataclass
from typing import Any

from lilt.llm.critique_gate import (
    CRITIQUE_JSON_RETRY_HINT,
    CritiqueGateDecision,
    merge_critique_with_accuracy,
)
from lilt.llm.critique_parser import CritiqueParser
from lilt.llm.provider import ContextData, LLMProvider, LLMResponse
from lilt.models.critique import CritiqueResult
from lilt.parser.linguistic import has_linguistic_content
from lilt.parser.placeholder_contract import extract
from lilt.validation.accuracy_gate import AccuracyGate
from lilt.validation.validators import SegmentTranslationValidator, ValidationError

REFINE_MAX_VALIDATION_RETRIES = 3
DENSE_PLACEHOLDER_THRESHOLD = 15
DENSE_SEGMENT_VALIDATION_RETRIES = 5


def validation_retries_for_source(source: str) -> int:
    """Return refine validation retries scaled to placeholder density."""
    if len(extract(source)) > DENSE_PLACEHOLDER_THRESHOLD:
        return DENSE_SEGMENT_VALIDATION_RETRIES
    return REFINE_MAX_VALIDATION_RETRIES


@dataclass
class DraftResult:
    """Outcome of a draft generation call."""

    text: str
    response: LLMResponse


@dataclass
class CritiquePassResult:
    """Outcome of a critique generation call."""

    text: str
    response: LLMResponse
    parsed: CritiqueResult | None
    requires_refine: bool
    parse_ok: bool
    parse_repaired: bool = False
    degraded: bool = False
    accuracy_forced: bool = False


@dataclass
class RefineResult:
    """Outcome of a refine generation call."""

    text: str
    response: LLMResponse | None
    bypassed: bool


@dataclass
class ReflectionPassResult:
    """Outcome of a full draft-to-refine pass for one segment."""

    text: str
    meta: dict[str, Any]
    draft: DraftResult | None = None
    critique: CritiquePassResult | None = None
    refine: RefineResult | None = None
    bypass: bool = False


def _decision_to_pass(decision: CritiqueGateDecision) -> CritiquePassResult:
    return CritiquePassResult(
        text=decision.text,
        response=decision.response,
        parsed=decision.parsed,
        requires_refine=decision.requires_refine,
        parse_ok=decision.parse_ok,
        parse_repaired=decision.parse_repaired,
        degraded=decision.degraded,
        accuracy_forced=decision.accuracy_forced,
    )


def run_draft(
    llm: LLMProvider,
    source: str,
    context: ContextData | None = None,
) -> DraftResult:
    """Generate an initial translation draft."""
    response = llm.generate_draft(source, context)
    return DraftResult(text=response.text, response=response)


def run_critique(
    llm: LLMProvider,
    draft: str,
    source: str,
    context: ContextData | None = None,
) -> CritiquePassResult:
    """Evaluate a draft with AccuracyGate merge and JSON degrade policy."""
    accuracy = AccuracyGate.evaluate(source, draft)
    response = llm.generate_critique(draft, source, context)
    attempt = CritiqueParser.try_parse_detailed(response.text)

    if attempt.result is None and response.text.strip():
        retry = llm.generate_critique(draft + CRITIQUE_JSON_RETRY_HINT, source, context)
        retry.attempt = max(response.attempt or 1, 1) + 1
        retry.retry_reason = "critique_json"
        retry_attempt = CritiqueParser.try_parse_detailed(retry.text)
        response = retry
        attempt = retry_attempt

    if not response.text.strip():
        return _decision_to_pass(
            merge_critique_with_accuracy(
                accuracy,
                critique_text="",
                response=response,
                parsed=None,
                parse_ok=False,
                parse_repaired=False,
            )
        )

    return _decision_to_pass(
        merge_critique_with_accuracy(
            accuracy,
            critique_text=response.text,
            response=response,
            parsed=attempt.result,
            parse_ok=attempt.result is not None,
            parse_repaired=attempt.repaired,
        )
    )


def run_refine(
    llm: LLMProvider,
    draft: str,
    critique: str,
    source: str,
    context: ContextData | None = None,
    *,
    max_validation_retries: int = REFINE_MAX_VALIDATION_RETRIES,
) -> RefineResult:
    """Produce a refined translation, optionally retrying on validation failure."""
    parsed_critique = CritiqueParser.try_parse(critique)
    if parsed_critique is None:
        accuracy = AccuracyGate.evaluate(source, draft)
        if not accuracy.ok:
            critique = accuracy.to_critique_json()
            parsed_critique = CritiqueParser.try_parse(critique)
        if parsed_critique is None:
            raise ValidationError(
                "Critique output is not valid JSON with a boolean requires_refine field; "
                "refine aborted"
            )
    if not parsed_critique.requires_refine:
        normalized_draft = SegmentTranslationValidator.normalize_translation(
            source, draft
        )
        return RefineResult(text=normalized_draft, response=None, bypassed=True)

    if max_validation_retries <= 0:
        max_validation_retries = 1

    retries = 0
    refined_text = draft
    last_error: str | None = None
    working_critique = critique
    last_response: LLMResponse | None = None

    while retries < max_validation_retries:
        response = llm.generate_refine(refined_text, working_critique, source, context)
        response.attempt = retries + 1
        if retries > 0:
            response.retry_reason = "validation"
        candidate = response.text
        try:
            refined_text = SegmentTranslationValidator.normalize_translation(
                source, candidate
            )
            last_response = response
            last_error = None
            break
        except ValidationError as exc:
            refined_text = candidate
            last_error = str(exc)
            working_critique += (
                f"\n\nValidation Error on previous attempt: {last_error}. Please fix."
            )
            retries += 1

    if last_error:
        raise ValidationError(
            "Failed to fix validation errors after "
            f"{max_validation_retries} retries: {last_error}",
            attempt_text=refined_text,
        )

    return RefineResult(text=refined_text, response=last_response, bypassed=False)


def run_reflection_pass(
    llm: LLMProvider,
    source: str,
    context: ContextData | None = None,
    *,
    max_validation_retries: int = 0,
) -> ReflectionPassResult:
    """Run draft, critique, and refine for one segment."""
    if not has_linguistic_content(source):
        return ReflectionPassResult(
            text=source,
            meta={"used": True, "draft_accepted": True, "bypass": True},
            bypass=True,
        )

    draft_result = run_draft(llm, source, context)
    draft_text = draft_result.text

    if not llm.reflection_enabled or not draft_text:
        return ReflectionPassResult(
            text=draft_text,
            meta={"used": False, "draft_accepted": True},
            draft=draft_result,
        )

    critique_result = run_critique(llm, draft_text, source, context)
    if not critique_result.requires_refine:
        normalized_draft = SegmentTranslationValidator.normalize_translation(
            source, draft_text
        )
        return ReflectionPassResult(
            text=normalized_draft,
            meta={
                "used": True,
                "draft_accepted": True,
                "critique_feedback": critique_result.text,
                "critique_degraded": critique_result.degraded,
                "accuracy_forced": critique_result.accuracy_forced,
            },
            draft=draft_result,
            critique=critique_result,
        )

    try:
        refine_result = run_refine(
            llm,
            draft_text,
            critique_result.text,
            source,
            context,
            max_validation_retries=max_validation_retries
            if max_validation_retries > 0
            else validation_retries_for_source(source),
        )
        final_text = SegmentTranslationValidator.normalize_translation(
            source, refine_result.text if refine_result.text else draft_text
        )
    except ValidationError:
        recovered_draft = SegmentTranslationValidator.try_normalize_draft(
            source, draft_text
        )
        if recovered_draft is None:
            raise
        final_text = recovered_draft
        return ReflectionPassResult(
            text=final_text,
            meta={
                "used": True,
                "draft_accepted": True,
                "critique_feedback": critique_result.text,
            },
            draft=draft_result,
            critique=critique_result,
        )

    return ReflectionPassResult(
        text=final_text,
        meta={
            "used": True,
            "draft_accepted": False,
            "critique_feedback": critique_result.text,
            "critique_degraded": critique_result.degraded,
            "accuracy_forced": critique_result.accuracy_forced,
        },
        draft=draft_result,
        critique=critique_result,
        refine=refine_result,
    )
