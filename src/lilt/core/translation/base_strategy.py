"""Base infrastructure for reflection-based translation strategies."""

import logging
from collections.abc import Iterable
from typing import Any, Literal, Protocol

from lilt.core.translation.context_resolver import ContextResolver
from lilt.llm.provider import LLMProvider, LLMResponse
from lilt.telemetry.service import TelemetryService
from lilt.tm.checkpoint import TranslationCheckpoint
from lilt.tm.repository import TMRepository

logger = logging.getLogger(__name__)


class ReflectionStrategy(Protocol):
    """Protocol for translation execution strategies."""

    def run_iter(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: str | None = None,
    ) -> Iterable[dict[str, Any]]:
        """Execute the translation pipeline iteratively."""
        ...


class BaseReflectionStrategy:
    """Shared infrastructure for reflection-based translation strategies."""

    def __init__(
        self,
        tm: TMRepository,
        llm: LLMProvider,
        context_window: int | dict[str, int] = 3,
        telemetry: TelemetryService | None = None,
        draft_empty_retries: int = 1,
    ):
        self.tm = tm
        self.llm = llm
        self.resolver = ContextResolver(context_window)
        self.telemetry = telemetry
        self.checkpoint = TranslationCheckpoint(tm)
        # Number of draft generations attempted before giving up on empty output.
        # Defaults to 1 (fast-fail): a local model that returns empty output for a
        # segment tends to do so deterministically, so extra attempts only multiply
        # latency without improving the result. Configurable via llm.draft_empty_retries.
        self._draft_empty_retries = max(1, draft_empty_retries)
        self._pending_telemetry: list[
            tuple[
                str,
                str,
                Literal["draft", "critique", "refine", "sequential"],
                LLMResponse,
                str,
                str,
            ]
        ] = []

    def _queue_telemetry(
        self,
        namespace: str,
        segment_id: str,
        stage: Literal["draft", "critique", "refine", "sequential"],
        res: LLMResponse,
        model_name: str,
        finish_reason: str = "stop",
    ) -> None:
        """Defer telemetry until after checkpoint so ``checkpoint_ms`` is known."""
        self._pending_telemetry.append(
            (namespace, segment_id, stage, res, model_name, finish_reason)
        )

    def _flush_telemetry(self, checkpoint_ms: int | None = None) -> None:
        for namespace, segment_id, stage, res, model_name, finish_reason in (
            self._pending_telemetry
        ):
            if checkpoint_ms is not None:
                res.checkpoint_ms = checkpoint_ms
            self._record_telemetry(
                namespace, segment_id, stage, res, model_name, finish_reason
            )
        self._pending_telemetry.clear()

    def _record_telemetry(
        self,
        namespace: str,
        segment_id: str,
        stage: Literal["draft", "critique", "refine", "sequential"],
        res: LLMResponse,
        model_name: str,
        finish_reason: str = "stop",
    ) -> None:
        if not self.telemetry:
            return
        try:
            result = self.telemetry.record_inference_from_llm(
                self.llm,
                namespace,
                segment_id,
                stage,
                res,
                model_name,
                finish_reason,
            )
            if not result.success:
                logger.warning("Telemetry write failed: %s", result.error)
        except Exception as exc:
            logger.warning("Telemetry recording raised unexpectedly: %s", exc)

    def _stage_model(self, stage: str) -> str:
        return self.llm.stage_model_name(stage)
