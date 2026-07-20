"""Workflow (breadth-first) reflection strategy."""

import logging
import time
from collections.abc import Iterable

from lilt.core.translation.base_strategy import BaseReflectionStrategy
from lilt.core.translation.progress_events import (
    progress_error,
    progress_pass,
    progress_validation_fail,
)
from lilt.core.translation.reflection_runtime import (
    EmptyLLMOutputError,
    preflight_translation_budget,
    run_critique,
    run_draft,
    run_refine,
    validation_retries_for_source,
)
from lilt.core.translation.segment_uow import process_segment
from lilt.exceptions import MultipleSegmentsFoundError, PreconditionError
from lilt.llm.critique_gate import merge_critique_with_accuracy
from lilt.llm.provider import LLMResponse
from lilt.models.segment import (
    ReflectionMeta,
    SegmentStatus,
    StageArtifact,
    StoredSegment,
)
from lilt.models.segment_policy import SegmentPolicy
from lilt.models.status_resolver import StatusResolver
from lilt.tm.segment_lookup import resolve_unique_segment
from lilt.validation.accuracy_gate import AccuracyGate
from lilt.validation.validators import SegmentTranslationValidator, ValidationError

logger = logging.getLogger(__name__)

_CRITIQUE_BYPASS_PAYLOAD = '{"requires_refine": false, "issues": []}'
_STAGE_PROGRESS_LABEL = {
    "draft": "Drafting",
    "critique": "Critiquing",
    "refine": "Refining",
}


class WorkflowReflectionStrategy(BaseReflectionStrategy):
    """Persistent Workflow Engine executing batched passes across the namespace."""

    def run_iter(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: str | None = None,
    ) -> Iterable[dict]:
        """Execute the translation pipeline iteratively."""
        stages_to_run = ["draft", "critique", "refine"] if not stage else [stage]
        if not stage and not self.llm.reflection_enabled:
            stages_to_run = ["draft"]

        segments = self.tm.load_namespace(namespace)
        if segments:
            if segment_id:
                resolved = resolve_unique_segment(segments, segment_id, namespace)
                eligible = [resolved]
            else:
                eligible = [
                    s
                    for s in segments.values()
                    if any(
                        SegmentPolicy.is_eligible_for_workflow_stage(s, st, force)
                        for st in stages_to_run
                    )
                ]
            eligible_sources = [s.source_text for s in eligible]
            if eligible_sources:
                preflight_translation_budget(
                    self.llm,
                    source_texts=eligible_sources,
                    stages=stages_to_run,
                    segments=eligible,
                )

        for current_stage in stages_to_run:
            yield from self._run_stage(
                namespace, current_stage, force, segment_id, status_filter
            )

    def _run_stage(
        self,
        namespace: str,
        stage: str,
        force: bool,
        segment_id: str | None,
        status_filter: str | None,
    ) -> Iterable[dict]:
        segments = self.tm.load_namespace(namespace)
        if not segments:
            return

        active_segments = list(segments.values())
        if segment_id:
            resolved = resolve_unique_segment(segments, segment_id, namespace)
            segment_id = resolved.id

        segment_to_idx = {s.id: idx for idx, s in enumerate(active_segments)}

        if stage in ("critique", "refine") and not self.llm.reflection_enabled:
            yield {"type": "start", "total": 0, "stage": stage}
            return

        to_process: list[StoredSegment] = []
        for segment in active_segments:
            if segment_id and not segment.id.startswith(segment_id):
                continue
            if status_filter and not StatusResolver.matches(
                segment.status, status_filter
            ):
                continue
            if SegmentPolicy.is_eligible_for_workflow_stage(segment, stage, force):
                to_process.append(segment)

        yield {"type": "start", "total": len(to_process), "stage": stage}
        if not to_process:
            return

        for i, seg in enumerate(to_process):
            start_time = time.time()
            refined_text: str | None = None
            yield {
                "type": "sub_status",
                "segment_id": seg.id,
                "status_msg": f"{_STAGE_PROGRESS_LABEL.get(stage, f'{stage.capitalize()}ing')}...",
            }
            timing: dict[str, int] = {}
            try:
                with process_segment(
                    self.checkpoint,
                    namespace,
                    seg,
                    active_segments,
                    is_last=(i == len(to_process) - 1),
                    timing=timing,
                ):
                    try:
                        if stage == "draft":
                            self._execute_draft(
                                seg, namespace, active_segments, segment_to_idx
                            )
                        elif stage == "critique":
                            self._execute_critique(
                                seg, namespace, active_segments, segment_to_idx
                            )
                        elif stage == "refine":
                            self._execute_refine(
                                seg,
                                namespace,
                                active_segments,
                                segment_to_idx,
                                start_time,
                            )
                            if seg.refined:
                                refined_text = seg.refined.content

                        yield progress_pass(
                            seg.id, time.time() - start_time, stage=stage
                        )
                    except ValidationError as exc:
                        if stage == "refine" and self._try_accept_valid_draft(seg):
                            yield progress_pass(
                                seg.id, time.time() - start_time, stage=stage
                            )
                            continue
                        logger.error(f"Validation failed for {seg.id}: {exc}")
                        conflict_text = (
                            refined_text or getattr(exc, "attempt_text", None) or ""
                        )
                        if stage == "draft" and not conflict_text and seg.draft:
                            conflict_text = seg.draft.content
                        seg.mark_validation_conflict(
                            conflict_text,
                            stage=stage if stage == "refine" else None,
                            refine_model=self._stage_model("refine")
                            if stage == "refine"
                            else None,
                        )
                        yield progress_validation_fail(
                            seg.id, time.time() - start_time, str(exc)
                        )
                    except (PreconditionError, MultipleSegmentsFoundError):
                        raise
                    except Exception as exc:
                        logger.error(f"LLM/Pipeline failure for {seg.id}: {exc}")
                        seg.mark_infrastructure_error(exc)
                        if (
                            isinstance(exc, EmptyLLMOutputError)
                            and seg.error_meta is not None
                        ):
                            seg.error_meta = seg.error_meta.model_copy(
                                update={
                                    "message": (
                                        f"{seg.error_meta.message} "
                                        "Hint: retry with --force, use a larger model, "
                                        "or simplify complex macro blocks (e.g. \\author)."
                                    )
                                }
                            )
                        yield progress_error(
                            seg.id,
                            time.time() - start_time,
                            str(exc),
                            kind="llm"
                            if isinstance(exc, EmptyLLMOutputError)
                            else "pipeline",
                        )
            finally:
                self._flush_telemetry(timing.get("checkpoint_ms"))

        self.checkpoint.finalize_stage(namespace, active_segments)
        yield {"type": "done"}

    def _execute_draft(
        self,
        seg: StoredSegment,
        namespace: str,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
    ) -> None:
        """Execute the draft workflow stage for one segment."""
        context = self.resolver.resolve_for_draft(seg, active_segments, segment_to_idx)
        draft_result = None
        last_empty_error: EmptyLLMOutputError | None = None
        attempts = self._draft_empty_retries
        for attempt in range(attempts):
            try:
                draft_result = run_draft(self.llm, seg.source_text, context)
                draft_result.response.attempt = attempt + 1
                if attempt > 0:
                    draft_result.response.retry_reason = "draft_empty"
                break
            except EmptyLLMOutputError as exc:
                last_empty_error = exc
                if attempt + 1 >= attempts:
                    raise
                logger.warning(
                    "Empty draft for segment %s (attempt %s/%s); retrying.",
                    seg.id,
                    attempt + 1,
                    attempts,
                )
        if draft_result is None:
            raise last_empty_error or RuntimeError("Draft stage produced no result")
        draft_text = draft_result.text
        model_name = self._stage_model("draft")
        seg.archive_current_translation()
        seg.draft = StageArtifact(content=draft_text, model=model_name)
        seg.critique = None
        seg.refined = None

        if not self.llm.reflection_enabled:
            draft_text = SegmentTranslationValidator.normalize_translation(
                seg.source_text, draft_text
            )
            seg.translation = draft_text
            seg.status = SegmentStatus.REFINED
            seg.reflection_meta = ReflectionMeta(used=False, draft_accepted=True)
            seg.error_meta = None
        else:
            seg.translation = ""
            seg.status = SegmentStatus.DRAFTED
            seg.reflection_meta = ReflectionMeta(used=True, draft_accepted=False)

        self._queue_telemetry(
            namespace, seg.id, "draft", draft_result.response, model_name
        )

    def _execute_critique(
        self,
        seg: StoredSegment,
        namespace: str,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
    ) -> None:
        """Execute the critique workflow stage for one segment."""
        context = self.resolver.resolve_for_critique(
            seg, active_segments, segment_to_idx
        )
        draft_text = seg.draft.content if seg.draft else ""
        if not draft_text:
            raise PreconditionError(
                f"No draft available for critique on segment {seg.id}"
            )
        model_name = self._stage_model("critique")
        try:
            critique_result = run_critique(
                self.llm, draft_text, seg.source_text, context
            )
        except EmptyLLMOutputError:
            logger.warning(
                "Empty critique for segment %s; degrading via AccuracyGate.",
                seg.id,
            )
            empty = LLMResponse(text="", duration_ms=0)
            decision = merge_critique_with_accuracy(
                AccuracyGate.evaluate(seg.source_text, draft_text),
                critique_text="",
                response=empty,
                parsed=None,
                parse_ok=False,
            )
            seg.critique = StageArtifact(content=decision.text, model=model_name)
            seg.reflection_meta = ReflectionMeta(
                used=True,
                draft_accepted=not decision.requires_refine,
                critique_feedback=decision.text,
            )
            seg.status = SegmentStatus.CRITIQUED
            self._queue_telemetry(
                namespace, seg.id, "critique", decision.response, model_name
            )
            return

        # run_critique merges AccuracyGate and degrades bad JSON — never conflict here.
        critique_text = critique_result.text
        seg.critique = StageArtifact(content=critique_text, model=model_name)
        seg.reflection_meta = ReflectionMeta(
            used=True,
            draft_accepted=not critique_result.requires_refine,
            critique_feedback=critique_text,
        )
        seg.status = SegmentStatus.CRITIQUED
        self._queue_telemetry(
            namespace, seg.id, "critique", critique_result.response, model_name
        )

    def _execute_refine(
        self,
        seg: StoredSegment,
        namespace: str,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
        start_time: float,
    ) -> None:
        """Execute the refine workflow stage for one segment."""
        context = self.resolver.resolve_for_refine(seg, active_segments, segment_to_idx)
        draft_text = seg.draft.content if seg.draft else ""
        critique_text = seg.critique.content if seg.critique else ""
        if not draft_text:
            raise PreconditionError(f"Missing draft for refine on segment {seg.id}")
        if not critique_text.strip():
            critique_text = _CRITIQUE_BYPASS_PAYLOAD

        model_name = self._stage_model("refine")
        refine_result = run_refine(
            self.llm,
            draft_text,
            critique_text,
            seg.source_text,
            context,
            max_validation_retries=validation_retries_for_source(seg.source_text),
        )

        if refine_result.bypassed:
            refined_text = refine_result.text
            res = LLMResponse(
                text=refined_text,
                duration_ms=int((time.time() - start_time) * 1000),
            )
            res.bypass = True
            self._queue_telemetry(namespace, seg.id, "refine", res, model_name)
            refined_text = SegmentTranslationValidator.normalize_translation(
                seg.source_text, refined_text
            )
            seg.refined = StageArtifact(content=refined_text, model=model_name)
            seg.translation = refined_text
            seg.status = SegmentStatus.REFINED
            seg.error_meta = None
            if seg.reflection_meta:
                seg.reflection_meta.draft_accepted = True
            else:
                seg.reflection_meta = ReflectionMeta(
                    used=True,
                    draft_accepted=True,
                    critique_feedback=critique_text,
                )
            return

        if refine_result.response is None:
            raise ValidationError("Refine stage completed without an LLM response")

        refined_text = SegmentTranslationValidator.normalize_translation(
            seg.source_text, refine_result.text
        )
        self._queue_telemetry(
            namespace, seg.id, "refine", refine_result.response, model_name
        )
        seg.refined = StageArtifact(content=refined_text, model=model_name)
        seg.translation = refined_text
        seg.status = SegmentStatus.REFINED
        seg.error_meta = None
        if seg.reflection_meta:
            seg.reflection_meta.draft_accepted = False
        else:
            seg.reflection_meta = ReflectionMeta(
                used=True,
                draft_accepted=False,
                critique_feedback=critique_text,
            )

    def _try_accept_valid_draft(self, seg: StoredSegment) -> bool:
        """Accept a draft when refine validation fails but the draft is sound."""
        if not seg.draft or not seg.draft.content:
            return False
        draft_text = SegmentTranslationValidator.try_normalize_draft(
            seg.source_text, seg.draft.content
        )
        if draft_text is None:
            return False
        model_name = self._stage_model("refine")
        seg.refined = StageArtifact(content=draft_text, model=model_name)
        seg.translation = draft_text
        seg.status = SegmentStatus.REFINED
        seg.error_meta = None
        if seg.reflection_meta:
            seg.reflection_meta.draft_accepted = True
        else:
            seg.reflection_meta = ReflectionMeta(used=True, draft_accepted=True)
        logger.warning(
            "Refine validation failed for %s; accepting valid draft instead.",
            seg.id,
        )
        return True

    def _apply_critique_bypass(
        self,
        seg: StoredSegment,
        namespace: str,
        model_name: str,
    ) -> None:
        """Persist a synthetic no-refine critique when the LLM returns empty output."""
        seg.critique = StageArtifact(content=_CRITIQUE_BYPASS_PAYLOAD, model=model_name)
        seg.reflection_meta = ReflectionMeta(
            used=True,
            draft_accepted=True,
            critique_feedback="",
        )
        seg.status = SegmentStatus.CRITIQUED
        res = LLMResponse(text=_CRITIQUE_BYPASS_PAYLOAD, duration_ms=0)
        res.bypass = True
        self._queue_telemetry(namespace, seg.id, "critique", res, model_name)
