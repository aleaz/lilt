import os
import tempfile

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner(env={"COLUMNS": "150"})


def setup_mock_env(tmpdir):
    # 1. Create a basic config
    config_file = os.path.join(tmpdir, ".lilt", "lilt.yaml")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump({"project": {"source_lang": "en"}}, f)

    # 2. Setup mock TM segments in two namespaces
    tm_dir = os.path.join(tmpdir, ".lilt", "tm")
    repo = TMRepository(base_dir=tm_dir)

    seg1 = StoredSegment(
        id="abcd1234efgh",
        source_hash="abcd1234efgh",
        source_text="The quick brown fox",
        status=SegmentStatus.REVIEWED,
        translation="El zorro rápido y marrón",
    )
    repo.save_namespace("chapter1", [seg1])

    seg2 = StoredSegment(
        id="zyxw0987lkji",
        source_hash="zyxw0987lkji",
        source_text="Jumps over the lazy dog",
        status=SegmentStatus.APPROVED,
        translation="Salta sobre el perro perezoso",
    )
    repo.save_namespace("chapter2", [seg2])

    return repo


def test_status_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Test valid status update
            result = runner.invoke(
                app, ["tm", "set-status", "chapter1", "abcd1234", "CONFLICT"]
            )
            assert result.exit_code == 0
            assert "Updated segment" in result.output

            segments = repo.load_namespace("chapter1")
            assert segments["abcd1234efgh"].status == SegmentStatus.CONFLICT

            # Test invalid status
            result = runner.invoke(
                app, ["tm", "set-status", "chapter1", "abcd1234", "INVALID"]
            )
            assert result.exit_code == 1
            assert "Invalid status 'INVALID'" in str(result.exception)

            # Test invalid segment ID
            result = runner.invoke(
                app, ["tm", "set-status", "chapter1", "missing", "GENERATED"]
            )
            assert result.exit_code == 1
            assert "No segment found matching" in str(result.exception)

            # Test forced reset from APPROVED to GENERATED
            result = runner.invoke(
                app,
                [
                    "tm",
                    "set-status",
                    "chapter2",
                    "zyxw0987",
                    "GENERATED",
                    "--force",
                ],
            )
            assert result.exit_code == 0
            segments = repo.load_namespace("chapter2")
            seg = segments["zyxw0987lkji"]
            assert seg.status == SegmentStatus.GENERATED
            assert seg.translation == ""
            assert len(seg.history) == 1
            assert seg.history[0].translation == "Salta sobre el perro perezoso"

        finally:
            os.chdir(original_cwd)


def test_search_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Search translation
            result = runner.invoke(app, ["tm", "list", "--all", "--search", "zorro"])
            assert result.exit_code == 0
            assert "Total matching segments: 1" in result.output
            assert "chapter1" in result.output
            assert "abcd1234" in result.output

            # Search source
            result = runner.invoke(app, ["tm", "list", "--all", "--search", "lazy dog"])
            assert result.exit_code == 0
            assert "Total matching segments: 1" in result.output
            assert "chapter2" in result.output

            # Search not found
            result = runner.invoke(app, ["tm", "list", "--all", "--search", "elefante"])
            assert result.exit_code == 0
            assert "Total matching segments: 0" in result.output

            # Restrict by namespace
            result = runner.invoke(app, ["tm", "list", "chapter2", "--search", "zorro"])
            assert result.exit_code == 0
            assert "Total matching segments: 0" in result.output

        finally:
            os.chdir(original_cwd)


def test_list_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_mock_env(tmpdir)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Test basic list
            result = runner.invoke(app, ["tm", "list", "chapter1"])
            assert result.exit_code == 0
            assert "Translation Memory: chapter1" in result.output
            assert "quick" in result.output
            assert "brown" in result.output
            assert "fox" in result.output
            assert "Total matching segments: 1" in result.output

            # Test list with status filter (matching)
            result = runner.invoke(
                app, ["tm", "list", "chapter1", "--status", "reviewed"]
            )
            assert result.exit_code == 0
            assert "Total matching segments: 1" in result.output

            # Test list with status filter (non-matching)
            result = runner.invoke(
                app, ["tm", "list", "chapter1", "--status", "approved"]
            )
            assert result.exit_code == 0
            assert "Total matching segments: 0" in result.output

            # Test list with search query filter (matching)
            result = runner.invoke(app, ["tm", "list", "chapter1", "--search", "brown"])
            assert result.exit_code == 0
            assert "Total matching segments: 1" in result.output

            # Test list with search query filter (non-matching)
            result = runner.invoke(app, ["tm", "list", "chapter1", "--search", "blue"])
            assert result.exit_code == 0
            assert "Total matching segments: 0" in result.output

            # Test list without namespace argument (should list namespaces)
            result = runner.invoke(app, ["tm", "list"])
            assert result.exit_code == 0
            assert "Namespaces Overview" in result.output
            assert "chap" in result.output

            # Test list with --all flag
            result = runner.invoke(app, ["tm", "list", "--all"])
            assert result.exit_code == 0
            assert "Translation Memory: All Namespaces" in result.output
            assert "chap" in result.output
            assert "quick" in result.output
            assert "brown" in result.output
            assert "lazy" in result.output
            assert "dog" in result.output
            assert "Total matching segments: 2" in result.output

        finally:
            os.chdir(original_cwd)
