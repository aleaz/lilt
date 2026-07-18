"""CLI commands for viewing LLM inference telemetry and metrics."""

import typer

from lilt.cli.ui import (
    console,
    create_panel,
    create_standard_table,
    print_error,
    print_info,
)
from lilt.services.workspace_context import WorkspaceContext

app = typer.Typer(
    help="View and manage LLM telemetry and observability metrics.",
    rich_markup_mode="rich",
)


@app.command()
def show(
    ctx: typer.Context,
    namespace: str = typer.Option(
        None, "--namespace", "-n", help="Filter by namespace"
    ),
) -> None:
    """Show a dashboard of LLM consumption and telemetry metrics."""
    workspace_dir = ctx.obj.get("workspace_dir", ".")
    workspace_ctx = ctx.obj.get("workspace_ctx") or WorkspaceContext.from_workspace(
        workspace_dir
    )

    if not workspace_ctx.telemetry_db_path.exists():
        print_error("Telemetry database not found. Run translation first.")
        raise typer.Exit(code=1)

    try:
        service = workspace_ctx.telemetry

        summary = service.get_global_summary(namespace)
        if not summary or summary.get("total_requests", 0) == 0:
            print_info("No telemetry records found.")
            raise typer.Exit()

        table = create_standard_table()
        table.add_column("Metric", style="bold yellow")
        table.add_column("Value")
        table.add_row("Total LLM Requests", str(summary["total_requests"]))
        table.add_row("Prompt Tokens", f"{summary['total_prompt_tokens']:,}")
        table.add_row("Completion Tokens", f"{summary['total_completion_tokens']:,}")

        total_tokens = (summary["total_prompt_tokens"] or 0) + (
            summary["total_completion_tokens"] or 0
        )
        table.add_row("Total Tokens", f"[bold cyan]{total_tokens:,}[/bold cyan]")

        duration_s = (summary["total_duration_ms"] or 0) / 1000.0
        table.add_row("Total Time", f"{duration_s:.2f} s")

        panel = create_panel(table, title="Global Telemetry Summary")
        console.print(panel)

        breakdown = service.get_stage_breakdown(namespace)
        if breakdown:
            btable = create_standard_table()
            btable.add_column("Stage", style="bold yellow")
            btable.add_column("Requests")
            btable.add_column("Prompt")
            btable.add_column("Completion")
            btable.add_column("Avg Time (ms)")
            for row in breakdown:
                btable.add_row(
                    str(row["stage"]).capitalize(),
                    str(row["reqs"]),
                    f"{row['pt']:,}" if row["pt"] else "0",
                    f"{row['ct']:,}" if row["ct"] else "0",
                    f"{row['avg_ms']:.1f}" if row["avg_ms"] else "0.0",
                )
            console.print(create_panel(btable, title="Stage Breakdown"))

        workflow = service.get_workflow_summary(namespace)
        if workflow:
            wtable = create_standard_table()
            wtable.add_column("Segment", style="bold yellow")
            wtable.add_column("Namespace")
            wtable.add_column("Critique")
            wtable.add_column("Refine")
            wtable.add_column("Tokens")
            wtable.add_column("Duration (ms)")
            for row in workflow:
                wtable.add_row(
                    str(row["segment_id"]),
                    str(row["namespace"]),
                    "yes" if row["critique_executed"] else "no",
                    "yes" if row["refine_executed"] else "no",
                    f"{row['total_tokens_consumed']:,}"
                    if row["total_tokens_consumed"]
                    else "0",
                    f"{row['total_duration_ms']:,}"
                    if row["total_duration_ms"]
                    else "0",
                )
            console.print(create_panel(wtable, title="Workflow Summary"))

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to read telemetry data: {e}")
        raise typer.Exit(code=1) from e
