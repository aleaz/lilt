"""Select reflection strategy from translation mode."""

from lilt.core.translation.base_strategy import ReflectionStrategy
from lilt.core.translation.sequential_strategy import SequentialReflectionStrategy
from lilt.core.translation.workflow_strategy import WorkflowReflectionStrategy
from lilt.llm.provider import LLMProvider
from lilt.models.translation_mode import TranslationMode
from lilt.telemetry.service import TelemetryService
from lilt.tm.repository import TMRepository


def create_reflection_strategy(
    mode: TranslationMode,
    tm: TMRepository,
    llm: LLMProvider,
    context_window: int | dict[str, int],
    telemetry: TelemetryService,
    draft_empty_retries: int = 1,
) -> ReflectionStrategy:
    """Build the reflection strategy for a product translation mode."""
    if mode == TranslationMode.WORKFLOW:
        return WorkflowReflectionStrategy(
            tm,
            llm,
            context_window,
            telemetry=telemetry,
            draft_empty_retries=draft_empty_retries,
        )
    return SequentialReflectionStrategy(tm, llm, context_window, telemetry=telemetry)
