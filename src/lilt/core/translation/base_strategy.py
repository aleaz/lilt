"""Base infrastructure for reflection-based translation strategies."""

import logging
from typing import Literal

from lilt.core.translation.context_resolver import ContextResolver
from lilt.llm.provider import LLMProvider, LLMResponse
from lilt.telemetry.service import TelemetryService
from lilt.tm.checkpoint import TranslationCheckpoint
from lilt.tm.repository import TMRepository

logger = logging.getLogger(__name__)


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
