"""CLI entry point for the LILT application.

This module orchestrates Typer CLI commands, loads configuration/environment
variables, and configures the global logging hierarchy.
"""

import logging
import os
import sys

import typer
from dotenv import load_dotenv

from lilt.cli.commands import pipeline, project, telemetry, tm
from lilt.cli.ui import print_error
from lilt.exceptions import LiltDomainError
from lilt.services.workspace_context import WorkspaceContext

app = typer.Typer(
    help="LILT: LaTeX Intelligent Localization Tool",
    context_settings={"help_option_names": ["-h", "--help"]},
    rich_markup_mode="rich",
)

app.add_typer(
    project.app, name="project", help="Manage project initialization and configuration"
)
app.add_typer(
    tm.app, name="tm", help="Manage Translation Memory (search, status, export, import)"
)
app.add_typer(
    pipeline.app,
    name="pipeline",
    help="Run the translation lifecycle (sync, translate, build, review)",
)
app.add_typer(
    telemetry.app,
    name="telemetry",
    help="View LLM telemetry and cost consumption metrics",
)


@app.callback()
def main(
    ctx: typer.Context,
    work_dir: str = typer.Option(
        ".", "--work-dir", "-C", help="Target project directory"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
) -> None:
    """LILT is an advanced AST-based localization engine for LaTeX.

    Args:
        ctx: Typer context object injected automatically.
        work_dir: Target project directory where configuration and TM exist.
        debug: Flag to enable verbose debug logging and standard output handler.
    """
    ctx.ensure_object(dict)
    workspace_dir = os.path.abspath(work_dir)
    ctx.obj["workspace_dir"] = workspace_dir
    ctx.obj["workspace_ctx"] = WorkspaceContext.from_workspace(workspace_dir)
    ctx.obj["debug"] = debug

    # Load environment variables
    load_dotenv(os.path.join(workspace_dir, ".env"))
    load_dotenv(os.path.join(workspace_dir, ".lilt", ".env"))

    # Setup global logging
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers: list[logging.Handler] = []

    lilt_dir = os.path.join(workspace_dir, ".lilt")
    if os.path.exists(lilt_dir):
        log_file = os.path.join(lilt_dir, "lilt.log")
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    if debug:
        handlers.append(logging.StreamHandler(sys.stdout))

    if handlers:
        logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
    else:
        logging.basicConfig(level=log_level, format=log_format)


def run_app() -> None:
    """Entry point for the CLI application.

    Catches custom domain LiltDomainError exceptions and prints them cleanly
    to the terminal before exiting with exit code 1.
    """
    try:
        app()
    except LiltDomainError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print_error("Operation interrupted. Completed progress has been saved.")
        sys.exit(130)


if __name__ == "__main__":
    run_app()
