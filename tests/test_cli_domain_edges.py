"""CLI / service edge tests for sandbox and budget domain errors."""

import os
import tempfile
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app, run_app
from lilt.exceptions import BudgetPreflightError, WorkspacePathError
from lilt.services.pipeline_service import PipelineService

runner = CliRunner()


def _init_workspace(tmpdir: str) -> None:
    config_dir = os.path.join(tmpdir, ".lilt")
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "lilt.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "project": {"source_lang": "en", "target_lang": "es"},
                "llm": {"provider": "openai", "model": "gpt-4o"},
            },
            f,
        )


def test_sync_rejects_sibling_prefix_workspace_path():
    with tempfile.TemporaryDirectory() as parent:
        workspace = os.path.join(parent, "proj")
        sibling = os.path.join(parent, "proj_evil")
        os.makedirs(workspace)
        os.makedirs(sibling)
        _init_workspace(workspace)
        evil_tex = os.path.join(sibling, "x.tex")
        with open(evil_tex, "w", encoding="utf-8") as f:
            f.write("Hello\n")

        service = PipelineService(workspace)
        try:
            service.sync_file(evil_tex)
            raise AssertionError("Expected WorkspacePathError")
        except WorkspacePathError:
            pass


def test_cli_sync_sibling_path_exits_via_domain_error():
    with tempfile.TemporaryDirectory() as parent:
        workspace = os.path.join(parent, "proj")
        sibling = os.path.join(parent, "proj_evil")
        os.makedirs(workspace)
        os.makedirs(sibling)
        evil_tex = os.path.join(sibling, "x.tex")
        with open(evil_tex, "w", encoding="utf-8") as f:
            f.write("Hello\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(workspace)
            runner.invoke(app, ["project", "init"])
            result = runner.invoke(app, ["pipeline", "sync", evil_tex])
            assert result.exit_code == 1
            combined = (result.output + str(result.exception)).lower()
            assert (
                "workspace" in combined or "path" in combined or "sandbox" in combined
            )
        finally:
            os.chdir(original_cwd)


def test_cli_translate_budget_preflight_surfaces_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])
            tex_path = os.path.join(tmpdir, "test.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("Hello World\n")
            runner.invoke(app, ["pipeline", "sync", tex_path])

            with patch(
                "lilt.services.pipeline_service.TranslationOrchestrator.run_translation",
                side_effect=BudgetPreflightError(
                    "budget preflight infeasible for stage=draft"
                ),
            ):
                result = runner.invoke(app, ["pipeline", "translate", "test"])
            assert result.exit_code != 0
            combined = (result.output + str(result.exception)).lower()
            assert "infeasible" in combined
        finally:
            os.chdir(original_cwd)


def test_run_app_maps_budget_preflight_to_clean_exit(capsys, monkeypatch):
    def boom() -> None:
        raise BudgetPreflightError("budget preflight infeasible for stage=draft")

    monkeypatch.setattr("lilt.cli.main.app", boom)
    try:
        run_app()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected SystemExit(1)")
    captured = capsys.readouterr()
    assert "infeasible" in (captured.out + captured.err).lower()
