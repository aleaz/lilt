"""CLI commands for project initialization and configuration."""

import os

import typer
from rich.markup import escape

from lilt.cli.ui import (
    console,
    create_panel,
    create_standard_table,
    print_error,
    print_success,
    print_warning,
)
from lilt.exceptions import ProjectNotInitializedError
from lilt.services.pipeline_service import PipelineService
from lilt.services.project_service import ProjectService


def _pipeline_service(ctx: typer.Context) -> PipelineService:
    return PipelineService(
        ctx.obj.get("workspace_dir", "."),
        workspace_ctx=ctx.obj.get("workspace_ctx"),
    )


app = typer.Typer(
    help="Manage LILT project configuration and initialization.",
    rich_markup_mode="rich",
)


def _project_service(ctx: typer.Context) -> ProjectService:
    return ProjectService(
        ctx.obj.get("workspace_dir", "."),
        workspace_ctx=ctx.obj.get("workspace_ctx"),
    )


@app.command()
def init(ctx: typer.Context) -> None:
    """Initialize LILT in the current directory."""
    service = _project_service(ctx)

    config_path, has_git = service.initialize_workspace()
    print_success(
        f"LILT initialized successfully. Config file created at: {config_path}"
    )
    if not has_git:
        print_warning(
            "No Git repository detected. Version control is recommended for "
            "tracking Translation Memory changes (.lilt/tm/*.jsonl)."
        )


@app.command()
def configure(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="File or directory to scan for macros"),
    include_macros: bool = typer.Option(
        True, "--macros/--no-macros", help="Register unknown macros in lilt.yaml"
    ),
    include_aliases: bool = typer.Option(
        False,
        "--include-aliases",
        help="Register inferred environment aliases in lilt.yaml",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Analyze the project and report findings without modifying lilt.yaml",
    ),
    show_known: bool = typer.Option(
        False,
        "--known",
        help="Also show macros already known to pylatexenc (verbose) [Only with --dry-run]",
    ),
    show_gaps: bool = typer.Option(
        False,
        "--gaps",
        help="Show syntax gaps (invalid LaTeX fragments) detected in the source [Only with --dry-run]",
    ),
) -> None:
    """Scan LaTeX files to auto-discover parser configuration and update lilt.yaml.

    Use --dry-run to preview what will be discovered or analyze the project state
    without modifying the configuration file.
    """
    service = _project_service(ctx)
    workspace_dir = ctx.obj.get("workspace_dir", ".")

    scan_path = os.path.abspath(
        path if os.path.isabs(path) else os.path.join(workspace_dir, path)
    )

    if dry_run:
        _run_analysis(service, workspace_dir, scan_path, show_known, show_gaps)
        return

    try:
        new_macros, new_aliases = service.configure_project(
            scan_path, include_macros=include_macros, include_aliases=include_aliases
        )
    except ProjectNotInitializedError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from None

    if new_macros == 0 and new_aliases == 0:
        print_success("No new parser configuration discovered.")
    else:
        parts = []
        if new_macros:
            parts.append(f"{new_macros} macro(s)")
        if new_aliases:
            parts.append(f"{new_aliases} environment alias(es)")
        print_success(f"Registered {' and '.join(parts)} in lilt.yaml.")


def _run_analysis(
    service: ProjectService,
    workspace_dir: str,
    scan_path: str,
    show_known: bool,
    show_gaps: bool,
) -> None:
    if not os.path.exists(scan_path):
        print_error(f"Path '{scan_path}' does not exist.")
        raise typer.Exit(code=1) from None

    try:
        report = service.analyze(scan_path)
    except Exception as e:
        print_error(f"Error during analysis: {e}")
        raise typer.Exit(code=1) from None

    # ── Header summary ────────────────────────────────────────────────
    summary_table = create_standard_table(show_header=False)
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Files Scanned:", str(report.total_files))
    summary_table.add_row("Macros Seen:", str(sum(report.macros.values())))
    summary_table.add_row("Environments:", str(sum(report.environments.values())))
    console.print(create_panel(summary_table, title="LILT Project Analysis (Dry-Run)"))
    console.print()

    # ── Unknown macros ─────────────────────────────────────────────────
    if report.unknown_macros:
        table = create_standard_table()
        table.add_column("Macro", style="cyan")
        table.add_column("Inferred Args", justify="center")
        table.add_column("Occurrences", justify="right")
        for name in sorted(report.unknown_macros):
            args = report.unknown_macros_with_args.get(name, 0)
            count = report.macros.get(name, 0)
            table.add_row(escape(f"\\{name}"), str(args), str(count))
        console.print(
            create_panel(table, title=f"Unknown Macros ({len(report.unknown_macros)})")
        )
        console.print()
    else:
        table = create_standard_table(show_header=False)
        table.add_column("Status")
        table.add_row(
            "[green][OK][/green] No unknown macros found — all macros are configured."
        )
        console.print(create_panel(table, title="Unknown Macros"))
        console.print()

    # ── Verbatim usage ─────────────────────────────────────────────────
    if report.verbatim_usage:
        v_table = create_standard_table()
        v_table.add_column("Macro", style="cyan")
        v_table.add_column("Occurrences", justify="right")
        for name, count in sorted(report.verbatim_usage.items()):
            v_table.add_row(escape(f"\\{name}"), str(count))
        console.print(create_panel(v_table, title="Verbatim Macros (shielded)"))
        console.print()

    # ── Gaps (optional) ────────────────────────────────────────────────
    if show_gaps:
        if report.gaps:
            g_table = create_standard_table()
            g_table.add_column("File", style="cyan")
            g_table.add_column("Pos", justify="right")
            g_table.add_column("Length", justify="right")
            g_table.add_column("Preview")
            for filepath, start, end, text in report.gaps:
                preview = text.replace("\n", "↵")[:60]
                if len(text) > 60:
                    preview += "…"
                g_table.add_row(
                    os.path.relpath(filepath, workspace_dir),
                    str(start),
                    str(end - start),
                    escape(preview),
                )
            console.print(
                create_panel(
                    g_table, title=f"Syntax Gaps ({len(report.gaps)}) (invalid LaTeX)"
                )
            )
            console.print()
        else:
            table = create_standard_table(show_header=False)
            table.add_column("Status")
            table.add_row("[green][OK][/green] No syntax gaps found.")
            console.print(create_panel(table, title="Syntax Gaps"))
            console.print()

    # ── Semantic Environment Aliases ──────────────────────────────────
    if report.environment_aliases:
        alias_table = create_standard_table()
        alias_table.add_column("Alias Macro", style="cyan")
        alias_table.add_column("Type")
        alias_table.add_column("Target Environment")
        for alias, spec in report.environment_aliases.items():
            alias_table.add_row(
                escape(f"\\{alias}"),
                spec.get("type", "unknown"),
                escape(spec.get("env", "")),
            )
        console.print(
            create_panel(
                alias_table,
                title=f"Semantic Environment Aliases ({len(report.environment_aliases)})",
            )
        )
        console.print()

    # ── System Status & Action Required ────────────────────────────────
    is_initialized = os.path.exists(os.path.join(workspace_dir, ".lilt", "lilt.yaml"))
    warnings = []
    status_lines = []

    if is_initialized:
        status_lines.append("[green][OK][/green] Project is initialized.")
    else:
        warnings.append("Project is not initialized. Run `lilt project init`.")

    if report.unknown_macros:
        warnings.append(
            f"{len(report.unknown_macros)} unknown macros detected. Run `lilt project configure` without --dry-run."
        )
    else:
        if is_initialized:
            status_lines.append("[green][OK][/green] Configuration is up-to-date.")

    if status_lines:
        status_table = create_standard_table(show_header=False)
        status_table.add_column("Status")
        for line in status_lines:
            status_table.add_row(line)
        console.print(create_panel(status_table, title="System Status"))
        console.print()

    if warnings:
        action_lines = []
        for w in warnings:
            action_lines.append(f"[yellow][WARN][/yellow] {w}")

        action_table = create_standard_table(show_header=False)
        action_table.add_column("Action")
        for line in action_lines:
            action_table.add_row(line)
        console.print(create_panel(action_table, title="Action Required"))
        console.print()
