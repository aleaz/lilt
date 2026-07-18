import os
import tempfile

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner()


def test_show_segment():
    with tempfile.TemporaryDirectory() as tmpdir:
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
        ]
        repo.save_namespace("mock", segments)

        # Run the show command by changing dir
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Test precise ID match
            result = runner.invoke(app, ["tm", "list", "mock", "--id", "abcd1234efgh"])
            assert result.exit_code == 0
            assert "abcd1234efgh" in result.output
            assert "This is a test source text." in result.output
            assert "generated" in result.output

            # Test short ID prefix match (unique)
            result = runner.invoke(app, ["tm", "list", "mock", "--id", "abcd5"])
            assert result.exit_code == 0
            assert "abcd5678ijkl" in result.output
            assert "Another source text." in result.output
            assert "Otra traducción." in result.output
            assert "reviewed" in result.output

            # Test ambiguous prefix match
            result = runner.invoke(app, ["tm", "list", "mock", "--id", "abcd"])
            assert result.exit_code == 1
            assert "Multiple segments match prefix" in str(result.exception)

            # Test no match
            result = runner.invoke(app, ["tm", "list", "mock", "--id", "nonexistent"])
            assert result.exit_code == 1
            assert "No segment found matching 'nonexistent' in namespace 'mock'" in str(
                result.exception
            )

        finally:
            os.chdir(original_cwd)
