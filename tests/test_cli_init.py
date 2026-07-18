import os
import tempfile

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app

runner = CliRunner()


def test_cli_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["project", "init"])
            assert result.exit_code == 0
            assert "LILT initialized successfully" in result.output
            assert os.path.exists(".lilt/lilt.yaml")

            # Check valid YAML
            with open(".lilt/lilt.yaml", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                assert "project" in data
                assert "llm" in data
                assert "parser" in data
                assert data["project"]["source_lang"] == "English"
        finally:
            os.chdir(original_cwd)


def test_cli_init_twice():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            # Run again
            result = runner.invoke(app, ["project", "init"])
            assert result.exit_code == 0
            assert "LILT initialized successfully" in result.output
        finally:
            os.chdir(original_cwd)
