import os
import tempfile
from datetime import UTC, datetime

from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.services.workspace_context import WorkspaceContext
from lilt.telemetry.models import InferenceRecord, TokenUsage

runner = CliRunner(env={"COLUMNS": "150"})


def test_telemetry_show_empty_db_exits_cleanly():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            _ = WorkspaceContext.from_workspace(tmpdir).telemetry

            result = runner.invoke(app, ["telemetry", "show"])
            assert result.exit_code == 0
            assert "No telemetry records found" in result.output
        finally:
            os.chdir(original_cwd)


def test_telemetry_show_with_records():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            ctx = WorkspaceContext.from_workspace(tmpdir)
            started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
            finished = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)
            ctx.telemetry.record_inference(
                InferenceRecord(
                    id="rec-1",
                    segment_id="seg1",
                    namespace="chapter1",
                    provider="MockProvider",
                    model="mock",
                    stage="draft",
                    prompt_version="draft:abc",
                    started_at=started,
                    finished_at=finished,
                    duration_ms=100,
                    ttft_ms=10,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
                    usage_source="api",
                    finish_reason="stop",
                )
            )

            result = runner.invoke(app, ["telemetry", "show"])
            assert result.exit_code == 0
            assert "Global Telemetry Summary" in result.output
            assert "Total LLM Requests" in result.output
            assert "Stage Breakdown" in result.output
        finally:
            os.chdir(original_cwd)


def test_telemetry_show_missing_db_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["telemetry", "show"])
            assert result.exit_code == 1
            assert "Telemetry database not found" in result.output
        finally:
            os.chdir(original_cwd)
