"""Sequential reflection strategy (depth-first execution mode)."""

import logging
import time
from collections.abc import Iterable

from lilt.core.translation.base_strategy import BaseReflectionStrategy
from lilt.core.translation.progress_events import (
    progress_error,
    progress_pass,
    progress_validation_fail,
)
from lilt.core.translation.segment_uow import process_segment
from lilt.exceptions import MultipleSegmentsFoundError
from lilt.llm.output_gate import EmptyLLMOutputError
from lilt.llm.provider import LLMResponse
from lilt.models.segment import ReflectionMeta
from lilt.models.segment_policy import SegmentPolicy
from lilt.tm.segment_lookup import resolve_unique_segment
from lilt.validation.validators import SegmentTranslationValidator, ValidationError

logger = logging.getLogger(__name__)


class SequentialReflectionStrategy(BaseReflectionStrategy):
    """Depth-first reflection: Draft -> Critique -> Refine per segment before the next."""

    def run_iter(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: str | None = None,
    ) -> Iterable[dict]:
        """Execute reflection pass-by-pass for each eligible segment (sequential mode)."""
        if stage:
            logger.warning(
                "The --stage flag is ignored in sequential execution mode "
                "(translation_mode=sequential). "
                "Running the full Draft->Critique->Refine pipeline per segment."
            )
        segments = self.tm.load_namespace(namespace)
        if not segments:
            logger.info(f"No segments found for {namespace}.")
            return

        active_segments = list(segments.values())
        if segment_id:
            resolved = resolve_unique_segment(segments, segment_id, namespace)
            segment_id = resolved.id

        to_translate = [
            s
            for s in active_segments
            if SegmentPolicy.is_eligible_for_sequential(
                s, force, status_filter, segment_id
            )
        ]

        yield {"type": "start", "total": len(to_translate)}

        if not to_translate:
            return

        segment_to_idx = {s.id: idx for idx, s in enumerate(active_segments)}

        for i, seg in enumerate(to_translate):
            start_time = time.time()
            translated_text = ""
            result_meta: dict | None = None
            result_event = None
            with process_segment(
                self.checkpoint,
                namespace,
                seg,
                active_segments,
                is_last=(i == len(to_translate) - 1),
            ):
                try:
                    context = self.resolver.resolve_for_refine(
                        seg, active_segments, segment_to_idx
                    )
                    saw_result = False
                    for event in self.llm.translate_segment_iter(
                        seg.source_text, context=context
                    ):
                        if event["type"] == "status":
                            yield {
                                "type": "sub_status",
                                "segment_id": seg.id,
                                "status_msg": event["message"],
                            }
                        elif event["type"] == "result":
                            saw_result = True
                            translated_text = event["text"]
                            result_meta = event.get("meta")

                            if self.telemetry:
                                meta = event.get("meta", {})
                                simulated_res = LLMResponse(
                                    text=translated_text,
                                    duration_ms=int((time.time() - start_time) * 1000),
                                    bypass=meta.get("bypass", False),
                                )
                                self._record_telemetry(
                                    namespace=namespace,
                                    segment_id=seg.id,
                                    stage="sequential",
                                    res=simulated_res,
                                    model_name=self._stage_model("sequential"),
                                )

                    if not saw_result:
                        raise EmptyLLMOutputError("sequential")

                    translated_text = SegmentTranslationValidator.normalize_translation(
                        seg.source_text, translated_text
                    )
                    if result_meta:
                        seg.reflection_meta = ReflectionMeta(**result_meta)
                    seg.apply_successful_translation(translated_text)
                    result_event = progress_pass(seg.id, time.time() - start_time)
                except ValidationError as exc:
                    logger.error(f"Validation failed for {seg.id}: {exc}")
                    normalized_draft = SegmentTranslationValidator.try_normalize_draft(
                        seg.source_text,
                        translated_text or (seg.draft.content if seg.draft else ""),
                    )
                    if normalized_draft is not None:
                        if result_meta:
                            seg.reflection_meta = ReflectionMeta(
                                used=True,
                                draft_accepted=True,
                                critique_feedback=seg.reflection_meta.critique_feedback
                                if seg.reflection_meta
                                else "",
                            )
                        seg.apply_successful_translation(normalized_draft)
                        result_event = progress_pass(seg.id, time.time() - start_time)
                        if result_event is not None:
                            yield result_event
                        continue
                    conflict_text = (
                        translated_text or getattr(exc, "attempt_text", None) or ""
                    )
                    seg.mark_validation_conflict(conflict_text)
                    result_event = progress_validation_fail(
                        seg.id, time.time() - start_time, str(exc)
                    )
                except (MultipleSegmentsFoundError, EmptyLLMOutputError):
                    raise
                except Exception as exc:
                    logger.error(f"LLM failure for {seg.id}: {exc}")
                    seg.mark_infrastructure_error(exc)
                    result_event = progress_error(
                        seg.id, time.time() - start_time, str(exc), kind="llm"
                    )

            if result_event is not None:
                yield result_event

        yield {"type": "done"}
