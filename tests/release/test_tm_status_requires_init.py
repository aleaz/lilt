"""tm status requires initialized workspace (R-01-F1)."""

from __future__ import annotations

import os
import tempfile

from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.exceptions import ProjectNotInitializedError

runner = CliRunner(env={"COLUMNS": "200"})


def test_tm_status_without_init_fails() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        original = os.getcwd()
        try:
            os.chdir(tmpdir)
            # CliRunner invokes Typer ``app``, not ``run_app()``, so domain
            # errors surface as ``result.exception`` rather than stdout.
            result = runner.invoke(app, ["tm", "status"])
            assert result.exit_code != 0
            assert isinstance(result.exception, ProjectNotInitializedError)
            assert "Not initialized" in str(result.exception)
            assert "init" in str(result.exception).lower()
        finally:
            os.chdir(original)
