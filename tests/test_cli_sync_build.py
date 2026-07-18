import os
import tempfile

from typer.testing import CliRunner

from lilt.cli.main import app

runner = CliRunner()


def setup_mock_env(tmpdir):
    runner.invoke(app, ["project", "init"])
    # Create a mock tex file
    tex_path = os.path.join(tmpdir, "test.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("\\section{Introduction}\nHello World\n")
    return tex_path


def test_cli_sync_build():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            tex_path = setup_mock_env(tmpdir)

            # Sync
            result = runner.invoke(app, ["pipeline", "sync", tex_path])
            assert result.exit_code == 0
            assert "Namespace" in result.output

            # Build without translations is blocked by default
            out_path = os.path.join(tmpdir, "out.tex")
            result = runner.invoke(
                app, ["pipeline", "build", "test", tex_path, out_path]
            )
            assert result.exit_code == 1
            assert "Build blocked" in result.output

            # Opt-in partial build still emits source text for untranslated segments
            result = runner.invoke(
                app,
                [
                    "pipeline",
                    "build",
                    "test",
                    tex_path,
                    out_path,
                    "--allow-partial",
                ],
            )
            assert result.exit_code == 0
            assert "Successfully built document at:" in result.output

            with open(out_path, encoding="utf-8") as f:
                content = f.read()
            assert "Hello World" in content

        finally:
            os.chdir(original_cwd)


def test_cli_sync_uninitialized():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # No init
            result = runner.invoke(app, ["pipeline", "sync", "fake.tex"])
            assert result.exit_code == 1
            assert "fake.tex" in result.output
        finally:
            os.chdir(original_cwd)


def test_cli_sync_rejects_non_tex_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])
            readme = os.path.join(tmpdir, "README")
            with open(readme, "w", encoding="utf-8") as handle:
                handle.write("plain text\n")
            result = runner.invoke(app, ["pipeline", "sync", readme])
            assert result.exit_code == 1
            assert ".tex" in result.output
        finally:
            os.chdir(original_cwd)
