"""Tests for translation progress event handling in PipelineService."""

from unittest.mock import MagicMock, patch

from lilt.models.config import LiltConfig
from lilt.services.pipeline_service import PipelineService


def test_run_translation_propagates_error_detail_in_status_message():
    """Failure progress events must surface the underlying error to the CLI."""
    ctx = MagicMock()
    ctx.workspace_dir = "/tmp/ws"
    ctx.preconditions.load_config.return_value = LiltConfig.model_validate(
        {
            "project": {"source_lang": "en", "target_lang": "es"},
            "llm": {"provider": "openai", "model": "gpt-4o"},
        }
    )
    ctx.preconditions.require_namespace.return_value = None
    ctx.repo.namespace_session.return_value.__enter__ = MagicMock(return_value=None)
    ctx.repo.namespace_session.return_value.__exit__ = MagicMock(return_value=False)
    ctx.telemetry = MagicMock()

    service = PipelineService("/tmp/ws", workspace_ctx=ctx)
    mock_strategy = MagicMock()
    mock_strategy.run_iter.return_value = [
        {"type": "start", "total": 1, "stage": "draft"},
        {
            "type": "progress",
            "segment_id": "seg-1",
            "status": "FAIL (LLM Error)",
            "elapsed": 1.25,
            "error": "LLM returned empty output during 'draft' for translatable content.",
        },
        {"type": "done"},
    ]

    with (
        patch(
            "lilt.services.pipeline_service.ProviderFactory.create",
            return_value=MagicMock(),
        ),
        patch(
            "lilt.services.pipeline_service.create_reflection_strategy",
            return_value=mock_strategy,
        ),
    ):
        events = list(service.run_translation("test_ns"))

    progress = next(e for e in events if e[2] == "seg-1" and e[4] is True)
    assert progress[3].startswith("FAIL (LLM Error) (1.25s):")
    assert "empty output during 'draft'" in progress[3]
