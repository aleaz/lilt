"""Translation pipeline orchestration."""

from collections.abc import Iterable
from pathlib import Path

from lilt.core.translation.protocols import ReflectionStrategy
from lilt.core.translation.sequential_strategy import SequentialReflectionStrategy
from lilt.core.translation.workflow_strategy import WorkflowReflectionStrategy
from lilt.llm.provider import LLMProvider
from lilt.models.translation_mode import TranslationMode
from lilt.telemetry.service import TelemetryService
from lilt.tm.repository import TMRepository


class TranslatorPipeline:
    """Orchestrates the translation of segments through the LLM."""

    def __init__(
        self,
        tm: TMRepository,
        llm: LLMProvider,
        context_window: int | dict[str, int] = 3,
        translation_mode: TranslationMode = TranslationMode.WORKFLOW,
        telemetry: TelemetryService | None = None,
        draft_empty_retries: int = 1,
    ):
        if telemetry is not None:
            self.telemetry = telemetry
        else:
            telemetry_db_path = Path("telemetry.db")
            if hasattr(tm, "base_dir") and isinstance(tm.base_dir, (str, Path)):
                telemetry_db_path = Path(tm.base_dir).parent / "telemetry.db"
            self.telemetry = TelemetryService(telemetry_db_path)
        self.strategy = TranslatorPipeline._create_strategy(
            translation_mode,
            tm,
            llm,
            context_window,
            self.telemetry,
            draft_empty_retries,
        )

    @staticmethod
    def _create_strategy(
        mode: TranslationMode,
        tm: TMRepository,
        llm: LLMProvider,
        context_window: int | dict[str, int],
        telemetry: TelemetryService,
        draft_empty_retries: int = 1,
    ) -> ReflectionStrategy:
        if mode == TranslationMode.WORKFLOW:
            return WorkflowReflectionStrategy(
                tm,
                llm,
                context_window,
                telemetry=telemetry,
                draft_empty_retries=draft_empty_retries,
            )
        return SequentialReflectionStrategy(
            tm, llm, context_window, telemetry=telemetry
        )

    def run_translation_iter(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: str | None = None,
    ) -> Iterable[dict]:
        """Yields progress events while translating segments using the selected Strategy."""
        yield from self.strategy.run_iter(
            namespace, force, segment_id, status_filter, stage
        )
