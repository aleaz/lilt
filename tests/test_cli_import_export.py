import os
import tempfile

from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner()


def test_cli_export_import():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            # Setup mock TM
            tm_dir = os.path.join(tmpdir, ".lilt", "tm")
            repo = TMRepository(base_dir=tm_dir)
            segments = [
                StoredSegment(
                    id="abcd",
                    source_hash="abcd",
                    source_text="Test source.",
                    status=SegmentStatus.REVIEWED,
                    translation="Prueba fuente.",
                )
            ]
            repo.save_namespace("test", segments)

            # Export CSV
            out_csv = os.path.join(tmpdir, "export.csv")
            result = runner.invoke(app, ["tm", "export", "test", out_csv])
            assert result.exit_code == 0
            assert "Exported" in result.output
            assert os.path.exists(out_csv)

            # Change translation in CSV
            with open(out_csv, encoding="utf-8") as f:
                content = f.read()
            content = content.replace("Prueba fuente.", "Nueva prueba.")
            with open(out_csv, "w", encoding="utf-8") as f:
                f.write(content)

            # Import CSV
            result = runner.invoke(app, ["tm", "import", "test", out_csv])
            assert result.exit_code == 0
            assert "Imported data." in result.output

            # Verify update
            updated_segments = repo.load_namespace("test")
            assert updated_segments["abcd"].translation == "Nueva prueba."

        finally:
            os.chdir(original_cwd)
