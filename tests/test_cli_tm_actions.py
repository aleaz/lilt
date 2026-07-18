import os
import tempfile

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner()


def setup_mock_env(tmpdir):
    # 1. Create a basic config
    config_file = os.path.join(tmpdir, ".lilt", "lilt.yaml")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump({"project": {"source_lang": "en"}}, f)

    # 2. Setup mock TM segments
    tm_dir = os.path.join(tmpdir, ".lilt", "tm")
    repo = TMRepository(base_dir=tm_dir)

    seg1 = StoredSegment(
        id="seg1",
        source_hash="seg1",
        source_text="Source 1",
        status=SegmentStatus.REVIEWED,
        translation="Traduccion 1",
    )
    seg2 = StoredSegment(
        id="seg2",
        source_hash="seg2",
        source_text="Source 2",
        status=SegmentStatus.DEPRECATED,
        translation="Traduccion vieja",
    )
    repo.save_namespace("chapter1", [seg1, seg2])
    return repo


def test_cli_tm_reset():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Reset requires --force for human-reviewed segments
            result = runner.invoke(app, ["tm", "admin", "reset", "chapter1", "--force"])
            assert result.exit_code == 0
            assert "Reset 1 segments back to GENERATED" in result.output

            # Check that seg1 translation was cleared and status is generated
            segments = repo.load_namespace("chapter1")
            assert segments["seg1"].status == SegmentStatus.GENERATED
            assert segments["seg1"].translation == ""
            # seg2 (deprecated) should not be affected
            assert segments["seg2"].status == SegmentStatus.DEPRECATED

        finally:
            os.chdir(original_cwd)


def test_cli_tm_prune():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Prune the namespace
            result = runner.invoke(app, ["tm", "admin", "prune", "chapter1"])
            assert result.exit_code == 0
            assert "Pruned 1 deprecated segment(s)" in result.output

            # Check that seg2 is gone, seg1 remains
            segments = repo.load_namespace("chapter1")
            assert "seg2" not in segments
            assert "seg1" in segments

        finally:
            os.chdir(original_cwd)
