from unittest.mock import MagicMock, patch

from lilt.models.config import LiltConfig
from lilt.services.pipeline_service import PipelineService
from lilt.services.workspace_context import WorkspaceContext


def test_build_translator_pipeline_uses_workspace_telemetry():
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
        pipeline = service._build_translator_pipeline(config)

    assert pipeline.strategy.telemetry is ctx.telemetry
