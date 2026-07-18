import os
import tempfile
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from lilt.cli.main import app

runner = CliRunner()


def test_cli_translate(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            # Create a mock tex file and sync it
            tex_path = os.path.join(tmpdir, "test.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("Hello World\n")
            runner.invoke(app, ["pipeline", "sync", tex_path])

            # Mock the translator pipeline to avoid LLM calls
            mock_pipeline = MagicMock()
            mock_pipeline.run_translation_iter.return_value = [
                {"type": "start", "total": 1},
                {
                    "type": "progress",
                    "segment_id": "123",
                    "status": "PASS",
                    "elapsed": 1.0,
                },
                {"type": "done"},
            ]

            with patch(
                "lilt.services.pipeline_service.TranslatorPipeline",
                return_value=mock_pipeline,
            ):
                result = runner.invoke(app, ["pipeline", "translate", "test"])

                assert result.exit_code == 0
                assert "Translation completed successfully!" in result.output

                mock_pipeline.run_translation_iter.assert_called_once_with(
                    "test", False, None, None, None
                )

        finally:
            os.chdir(original_cwd)
