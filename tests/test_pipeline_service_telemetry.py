from unittest.mock import MagicMock, patch

from lilt.core.translation import create_reflection_strategy
from lilt.core.translation.base_strategy import BaseReflectionStrategy
from lilt.models.config import LiltConfig
from lilt.models.translation_mode import TranslationMode
from lilt.services.pipeline_service import PipelineService
from lilt.services.workspace_context import WorkspaceContext


def test_create_reflection_strategy_uses_workspace_telemetry():
    ctx = WorkspaceContext.from_workspace("/tmp/ws")
    service = PipelineService("/tmp/ws", workspace_ctx=ctx)
    config = LiltConfig.model_validate(
        {
            "project": {"source_lang": "en", "target_lang": "es"},
            "llm": {"provider": "openai", "model": "gpt-4o"},
        }
    )

    with patch("lilt.services.pipeline_service.ProviderFactory") as factory:
        factory.create.return_value = MagicMock()
        llm_config = config.to_llm_factory_dict(workspace_dir=ctx.workspace_dir)
        llm = factory.create(llm_config)
        strategy = create_reflection_strategy(
            TranslationMode.from_llm_config(llm_config),
            ctx.repo,
            llm,
            config.llm.context_window,
            ctx.telemetry,
            draft_empty_retries=config.llm.draft_empty_retries,
        )

    assert isinstance(strategy, BaseReflectionStrategy)
    assert strategy.telemetry is ctx.telemetry
    assert service.ctx.telemetry is ctx.telemetry
