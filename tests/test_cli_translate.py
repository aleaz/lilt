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

            mock_strategy = MagicMock()
            mock_strategy.run_iter.return_value = [
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
                "lilt.services.pipeline_service.create_reflection_strategy",
                return_value=mock_strategy,
            ):
                result = runner.invoke(app, ["pipeline", "translate", "test"])

                assert result.exit_code == 0
                assert "Translation completed successfully!" in result.output

                mock_strategy.run_iter.assert_called_once_with(
                    "test", False, None, None, None
                )

        finally:
            os.chdir(original_cwd)


def test_cli_translate_workflow_stage_done_lines():
    """Workflow D→C→R prints per-stage durable lines with non-cumulative counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            tex_path = os.path.join(tmpdir, "trap.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("Hello World\n")
            runner.invoke(app, ["pipeline", "sync", tex_path])

            def _stage_batch(stage: str, seg_ids: list[str]) -> list[dict]:
                events: list[dict] = [
                    {"type": "start", "total": len(seg_ids), "stage": stage}
                ]
                for seg_id in seg_ids:
                    events.append(
                        {
                            "type": "progress",
                            "segment_id": seg_id,
                            "status": f"PASS ({stage.upper()})",
                            "elapsed": 0.1,
                        }
                    )
                events.append({"type": "done", "stage": stage})
                return events

            seg_ids = ["aaaa1111", "bbbb2222"]
            mock_strategy = MagicMock()
            mock_strategy.run_iter.return_value = (
                _stage_batch("draft", seg_ids)
                + _stage_batch("critique", seg_ids)
                + _stage_batch("refine", seg_ids)
            )

            with patch(
                "lilt.services.pipeline_service.create_reflection_strategy",
                return_value=mock_strategy,
            ):
                result = runner.invoke(app, ["pipeline", "translate", "trap"])

            assert result.exit_code == 0
            out = result.output
            assert "trap — draft done (2 segments)" in out
            assert "trap — critique done (2 segments)" in out
            assert "trap — refine done (2 segments)" in out
            # Must not show cumulative 4 / 6 across stages.
            assert "done (4 segments)" not in out
            assert "done (6 segments)" not in out
            assert "Translation completed successfully!" in out

        finally:
            os.chdir(original_cwd)


def test_cli_translate_sequential_done_line():
    """Sequential batch keeps generic Done and does not print Initializing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            tex_path = os.path.join(tmpdir, "sched.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("Hello World\n")
            runner.invoke(app, ["pipeline", "sync", tex_path])

            mock_strategy = MagicMock()
            mock_strategy.run_iter.return_value = [
                {"type": "start", "total": 1, "stage": "sequential"},
                {
                    "type": "progress",
                    "segment_id": "cccc3333",
                    "status": "PASS",
                    "elapsed": 0.5,
                },
                {"type": "done", "stage": "sequential"},
            ]

            with patch(
                "lilt.services.pipeline_service.create_reflection_strategy",
                return_value=mock_strategy,
            ):
                result = runner.invoke(
                    app, ["pipeline", "translate", "sched", "--mode", "sequential"]
                )

            assert result.exit_code == 0
            assert "sched — Done (1 segments)" in result.output
            assert "Initializing" not in result.output
            assert "draft done" not in result.output

        finally:
            os.chdir(original_cwd)
