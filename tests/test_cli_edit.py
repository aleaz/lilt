import os
import tempfile
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner()


def setup_mock_env(tmpdir):
    # 1. Create a basic lilt.yaml config
    config_file = os.path.join(tmpdir, ".lilt", "lilt.yaml")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    initial_config = {
        "project": {"source_lang": "en", "target_lang": "es"},
        "llm": {"provider": "openai", "model": "test"},
    }
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(initial_config, f)

    # 2. Setup mock TM segments
    tm_dir = os.path.join(tmpdir, ".lilt", "tm")
    repo = TMRepository(base_dir=tm_dir)
    segments = [
        StoredSegment(
            id="abcd1234efgh",
            source_hash="abcd1234efgh",
            source_text="This is a test source text.",
            status=SegmentStatus.GENERATED,
            translation="",
        ),
        StoredSegment(
            id="abcd5678ijkl",
            source_hash="abcd5678ijkl",
            source_text="Another source text.",
            status=SegmentStatus.REVIEWED,
            translation="Otra traducción.",
        ),
        StoredSegment(
            id="zyxw0987lkji",
            source_hash="zyxw0987lkji",
            source_text="Final source text.",
            status=SegmentStatus.REVIEWED,
            translation="Traducción final.",
        ),
    ]
    repo.save_namespace("mock", segments)
    return repo


@patch("lilt.cli.commands.pipeline.click.edit", return_value="Nueva traducción manual.")
def test_edit_segment_interactive(mock_editor):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["pipeline", "edit", "mock", "abcd5678"])
            assert result.exit_code == 0
            assert "Successfully updated and approved segment." in result.output

            segments = repo.load_namespace("mock")
            assert segments["abcd5678ijkl"].translation == "Nueva traducción manual."
            assert segments["abcd5678ijkl"].status == SegmentStatus.APPROVED
            mock_editor.assert_called_once()

        finally:
            os.chdir(original_cwd)


@patch(
    "lilt.cli.commands.pipeline.click.edit",
    return_value="Traduccion { sin cerrar.",
)
def test_edit_segment_validation_failure(mock_editor):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["pipeline", "edit", "mock", "abcd5678"])
            assert result.exit_code == 0
            assert "Validation failed" in result.output

            segments = repo.load_namespace("mock")
            assert segments["abcd5678ijkl"].translation == "Otra traducción."
            assert segments["abcd5678ijkl"].status == SegmentStatus.REVIEWED

        finally:
            os.chdir(original_cwd)


def test_edit_segment_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Ambiguous ID
            result = runner.invoke(app, ["pipeline", "edit", "mock", "abcd"])
            assert result.exit_code == 1
            assert "Error:" in str(
                result.exception
            ) or "Multiple segments match prefix" in str(result.exception)
            assert "Multiple segments" in str(result.exception)

            # Missing ID
            result = runner.invoke(app, ["pipeline", "edit", "mock", "missing123"])
            assert result.exit_code == 1
            assert "Error:" in str(
                result.exception
            ) or "No segment found matching" in str(result.exception)
            assert "No segment found matching" in str(result.exception)

        finally:
            os.chdir(original_cwd)


def test_review_all():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # 2 segments have status REVIEWED
            result = runner.invoke(app, ["pipeline", "review", "mock"], input="a\nr\n")
            assert result.exit_code == 0

            # First one approved
            segments = repo.load_namespace("mock")
            assert segments["abcd5678ijkl"].status == SegmentStatus.APPROVED
            # Second one rejected
            assert segments["zyxw0987lkji"].status == SegmentStatus.CONFLICT

        finally:
            os.chdir(original_cwd)
