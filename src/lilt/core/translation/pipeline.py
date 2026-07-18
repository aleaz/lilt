"""Compatibility wrapper around reflection strategy selection.

Prefer :func:`create_reflection_strategy` from application services.
"""

from collections.abc import Iterable

from lilt.core.translation.strategy_factory import create_reflection_strategy
from lilt.llm.provider import LLMProvider
from lilt.models.translation_mode import TranslationMode
from lilt.telemetry.service import TelemetryService
from lilt.tm.repository import TMRepository


class TranslatorPipeline:
    """Runs reflection via a mode-selected strategy (test / legacy entry)."""

    def __init__(
        self,
        tm: TMRepository,
        llm: LLMProvider,
        context_window: int | dict[str, int] = 3,
        translation_mode: TranslationMode = TranslationMode.WORKFLOW,
        telemetry: TelemetryService | None = None,
        draft_empty_retries: int = 1,
    ):
        if telemetry is None:
            raise TypeError(
                "TranslatorPipeline requires an explicit TelemetryService "
                "(inject WorkspaceContext.telemetry)."
            )
        self.strategy = create_reflection_strategy(
            translation_mode,
            tm,
            llm,
            context_window,
            telemetry,
            draft_empty_retries,
        )

    def run_translation_iter(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: str | None = None,
    ) -> Iterable[dict]:
        """Yield progress events while translating segments."""
        yield from self.strategy.run_iter(
            namespace, force, segment_id, status_filter, stage
        )
