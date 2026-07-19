"""CLI commands for Translation Memory namespace and segment management."""

import typer
from rich.markup import escape

from lilt.cli.ui import (
    console,
    create_panel,
    create_standard_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from lilt.exceptions import TMCorruptionError
from lilt.llm.context_recommend import format_capacity_warnings
from lilt.models.segment import SegmentStatus
from lilt.services.tm_service import TMService
from lilt.utils.token_utils import count_tokens

app = typer.Typer(
    help="Manage Translation Memory (TM) namespaces and segments.",
    rich_markup_mode="rich",
)

admin_app = typer.Typer(
    help="Administrative and destructive TM commands.",
    rich_markup_mode="rich",
)
app.add_typer(admin_app, name="admin")


def _tm_service(ctx: typer.Context) -> TMService:
    return TMService(
        ctx.obj.get("workspace_dir", "."),
        workspace_ctx=ctx.obj.get("workspace_ctx"),
    )


@app.command(name="list")
def list_segments(
    ctx: typer.Context,
    namespace: str | None = typer.Argument(
        None,
        help="The TM namespace to list. If omitted and --all is not set, lists all namespaces.",
    ),
    status: str | None = typer.Option(
        None, "--status", help="Filter by status (e.g. reviewed, generated, deprecated)"
    ),
    search_query: str | None = typer.Option(
        None, "--search", help="Search string in source or translation"
    ),
    all_namespaces: bool = typer.Option(
        False, "--all", "-a", help="List segments from all namespaces"
    ),
    segment_id: str | None = typer.Option(
        None, "--id", help="Inspect a specific segment ID in detail"
    ),
) -> None:
    """List segments in the TM with optional filtering, or inspect a specific segment."""
    ctx.obj.get("workspace_dir", ".")
    service = _tm_service(ctx)

    if segment_id:
        if not namespace:
            print_warning(
                "You must provide a namespace to inspect a specific segment ID."
            )
            raise typer.Exit(code=1)
        _inspect_segment(service, namespace, segment_id)
        return

    if namespace and all_namespaces:
        print_warning(
            "Namespace argument provided alongside --all flag. Ignoring --all flag."
        )

    if namespace:
        # List segments for single namespace
        segments = service.list_segments(namespace, status, search_query)

        table = create_standard_table()
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Tokens", justify="right", style="bright_black")
        table.add_column("Source Text", style="blue")
        table.add_column("Translation", style="green")

        for seg in segments:
            src_preview = (
                seg.source_text[:50] + "..."
                if len(seg.source_text) > 50
                else seg.source_text
            )
            trans_preview = (
                seg.translation[:50] + "..."
                if seg.translation and len(seg.translation) > 50
                else (seg.translation or "")
            )
            table.add_row(
                seg.id[:8],
                seg.status.value,
                str(count_tokens(seg.source_text)),
                escape(src_preview),
                escape(trans_preview),
            )

        console.print(create_panel(table, title=f"Translation Memory: {namespace}"))
        print_info(f"Total matching segments: {len(segments)}")

    elif all_namespaces:
        # List segments across all namespaces
        results, corrupt_namespaces = service.list_all_segments(status, search_query)

        table = create_standard_table()
        table.add_column("Namespace", style="cyan")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Tokens", justify="right", style="bright_black")
        table.add_column("Source Text", style="blue")
        table.add_column("Translation", style="green")

        for ns, seg in results:
            src_preview = (
                seg.source_text[:40] + "..."
                if len(seg.source_text) > 40
                else seg.source_text
            )
            trans_preview = (
                seg.translation[:40] + "..."
                if seg.translation and len(seg.translation) > 40
                else (seg.translation or "")
            )
            table.add_row(
                ns,
                seg.id[:8],
                seg.status.value,
                str(count_tokens(seg.source_text)),
                escape(src_preview),
                escape(trans_preview),
            )

        console.print(create_panel(table, title="Translation Memory: All Namespaces"))
        print_info(f"Total matching segments: {len(results)}")
        for ns in corrupt_namespaces:
            print_warning(
                f"Skipped corrupt namespace '{ns}'. Run 'lilt tm admin repair {ns}'."
            )
    else:
        # List namespaces and their segment count/states (fallback to status view)
        _show_status(service, None, True)


def _inspect_segment(service: TMService, namespace: str, segment_id: str) -> None:
    seg = service.show_segment(namespace, segment_id)

    table = create_standard_table(show_header=False)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")
    table.add_row("Segment ID", seg.id)
    table.add_row("Status", seg.status.value)
    table.add_row("Source Hash", seg.source_hash)
    table.add_row("Source Text", f"[yellow]{escape(seg.source_text)}[/yellow]")

    if seg.translation:
        table.add_row("Translation", f"[green]{escape(seg.translation)}[/green]")
    else:
        table.add_row("Translation", "[dim red][No translation yet][/dim red]")

    # Show reflection stage artifacts if available
    if seg.draft:
        table.add_row(
            "Draft Content",
            f"[cyan]{escape(seg.draft.content)}[/cyan]\n[dim bright_black](Model: {seg.draft.model})[/dim bright_black]",
        )
    if seg.critique:
        table.add_row(
            "Critique Feedback",
            f"[magenta]{escape(seg.critique.content)}[/magenta]\n[dim bright_black](Model: {seg.critique.model})[/dim bright_black]",
        )
    if seg.refined:
        table.add_row(
            "Refined Content",
            f"[bold green]{escape(seg.refined.content)}[/bold green]\n[dim bright_black](Model: {seg.refined.model})[/dim bright_black]",
        )
    if seg.error_meta:
        table.add_row(
            "Infrastructure Error",
            f"[bold red]{escape(seg.error_meta.error_type)}[/bold red]: {escape(seg.error_meta.message)}",
        )

    panel = create_panel(table, title=f"Segment Preview [{seg.id[:8]}]")
    console.print(panel)


@app.command()
def status(
    ctx: typer.Context,
    namespace: str | None = typer.Argument(
        None, help="The namespace to show stats for"
    ),
    all_namespaces: bool = typer.Option(
        False, "--all", "-a", help="Show consolidated stats for all namespaces"
    ),
) -> None:
    """Show translation progress and statistics (dashboard)."""
    service = _tm_service(ctx)
    _show_status(service, namespace, all_namespaces)


@app.command()
def budget(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="TM namespace to size context for"),
) -> None:
    """Recommend model_context_limit from post-sync TM + StagePolicy windows."""
    service = _tm_service(ctx)
    try:
        report = service.context_budget(namespace)
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from None

    table = create_standard_table()
    table.add_column("Stage", style="cyan")
    table.add_column("min_bare", justify="right")
    table.add_column("min_full_neighbors", justify="right")
    table.add_column("max_useful", justify="right")
    table.add_column("worst_segment", style="dim")
    for stage_name in ("draft", "critique", "refine"):
        stage = report.stages.get(stage_name)
        if stage is None:
            continue
        table.add_row(
            stage.stage,
            str(stage.min_bare),
            str(stage.min_full_neighbors),
            str(stage.max_useful),
            (stage.worst_segment_id[:8] + "…")
            if len(stage.worst_segment_id) > 8
            else stage.worst_segment_id,
        )
    console.print(create_panel(table, title=f"Context capacity [{namespace}]"))
    print_info(
        f"configured={report.configured_limit}  "
        f"recommend_min={report.recommend_min}  "
        f"recommend_max_useful={report.recommend_max_useful}  "
        f"verdict={report.verdict}"
    )
    for msg in format_capacity_warnings(report):
        print_warning(msg)


def _show_status(
    service: TMService, namespace: str | None, all_namespaces: bool
) -> None:
    if namespace is None and not all_namespaces:
        all_namespaces = True

    if namespace and all_namespaces:
        print_warning(
            "Namespace argument provided alongside --all flag. Ignoring namespace argument."
        )

    if all_namespaces:
        s, corrupt_namespaces = service.get_all_stats()
        title_name = "ALL NAMESPACES"
    else:
        assert namespace is not None, "Namespace must be provided if --all is not set"
        s = service.get_stats(namespace)
        corrupt_namespaces = []
        title_name = namespace

    table = create_standard_table()
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")
    table.add_column("Tokens", justify="right", style="bright_black")

    total = s.pop("total", 0)
    reflection_used = s.pop("reflection_used", 0)
    draft_accepted = s.pop("draft_accepted", 0)
    refined = s.pop("refined", 0)
    tokens_total = s.pop("tokens_total", 0)
    tokens_pending = s.pop("tokens_pending", 0)
    tokens_reflection = s.pop("tokens_reflection_estimate", 0)

    for status_obj in SegmentStatus:
        status_val = status_obj.value
        count = s.get(status_val, 0)
        tokens = s.get(f"tokens_{status_val}", 0)

        pct = count / total * 100 if total > 0 else 0.0
        table.add_row(status_val, str(count), f"{pct:.1f}%", f"{tokens:,}")

    table.add_section()
    table.add_row("Total Segments", str(total), "100%", f"{tokens_total:,}")

    if reflection_used > 0:
        table.add_section()
        table.add_row("[bold cyan]Reflection Stats[/bold cyan]", "", "", "")

        pct_accepted = (
            (draft_accepted / reflection_used) * 100 if reflection_used > 0 else 0
        )
        pct_refined = (refined / reflection_used) * 100 if reflection_used > 0 else 0

        table.add_row(
            "Drafts Accepted", str(draft_accepted), f"{pct_accepted:.1f}%", ""
        )
        table.add_row("Segments Refined", str(refined), f"{pct_refined:.1f}%", "")
        table.add_row("Total Reflected", str(reflection_used), "100%", "")

    if tokens_total > 0:
        table.add_section()
        table.add_row("[bold magenta]Cost Estimation[/bold magenta]", "", "", "")

        est_cost_total, est_cost_pending, est_cost_reflection = (
            service.estimate_token_costs(
                tokens_total=tokens_total,
                tokens_pending=tokens_pending,
                tokens_reflection=tokens_reflection,
            )
        )

        table.add_row("Total Estimated Cost", "--", "--", f"${est_cost_total:.3f}")
        table.add_row(
            "Reflection Cost Estimate", "--", "--", f"${est_cost_reflection:.3f}"
        )
        table.add_row("Pending Cost", "--", "--", f"${est_cost_pending:.3f}")

    console.print(create_panel(table, title=f"Translation Progress: {title_name}"))

    for ns in corrupt_namespaces:
        print_warning(
            f"Skipped corrupt namespace '{ns}'. Run 'lilt tm admin repair {ns}'."
        )

    # Also list namespaces horizontally if all_namespaces
    if all_namespaces:
        namespaces = service.list_namespaces()
        if namespaces:
            ns_table = create_standard_table()
            ns_table.add_column("Namespace", style="cyan")
            ns_table.add_column("Total Segments", justify="right", style="magenta")
            ns_table.add_column("Approved", justify="right", style="green")
            ns_table.add_column("Generated", justify="right", style="dim yellow")
            for ns in namespaces:
                if ns in corrupt_namespaces:
                    continue
                try:
                    ns_stats = service.get_stats(ns)
                    ns_table.add_row(
                        ns,
                        str(ns_stats.get("total", 0)),
                        str(ns_stats.get("approved", 0)),
                        str(ns_stats.get("generated", 0)),
                    )
                except TMCorruptionError:
                    print_warning(
                        f"Skipped corrupt namespace '{ns}'. "
                        f"Run 'lilt tm admin repair {ns}'."
                    )
            console.print(create_panel(ns_table, title="Namespaces Overview"))


@app.command()
def set_status(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace"),
    segment_id: str = typer.Argument(..., help="The segment ID or prefix"),
    status: str = typer.Argument(..., help="New status (e.g. GENERATED, CONFLICT)"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow forced reset transitions (e.g. APPROVED -> GENERATED)",
    ),
) -> None:
    """Explicitly change the lifecycle state of a segment."""
    ctx.obj.get("workspace_dir", ".")
    service = _tm_service(ctx)

    seg, old_status = service.update_segment_status(
        namespace, segment_id, status, force=force
    )
    print_success(
        f"Updated segment [bold cyan]{seg.id[:8]}[/bold cyan] "
        f"from [yellow]{old_status}[/yellow] "
        f"to [bold yellow]{seg.status.value}[/bold yellow]"
    )


@app.command("export")
def export_tm(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace"),
    output_file: str = typer.Argument(
        ..., help="Output filepath (e.g., tm.csv or tm.json)"
    ),
    format: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Format to export (csv or json). Derived from extension if omitted.",
    ),
) -> None:
    """Export the translation memory to CSV or JSON."""
    ctx.obj.get("workspace_dir", ".")
    service = _tm_service(ctx)

    count = service.export_tm(namespace, output_file, format)
    print_success(f"Exported {count} segments to {output_file}")


@app.command("import")
def import_tm(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace"),
    input_file: str = typer.Argument(
        ..., help="Input filepath (e.g., tm.csv or tm.json)"
    ),
    format: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Format to import (csv or json). Derived from extension if omitted.",
    ),
) -> None:
    """Import translations from a CSV or JSON file back into the TM."""
    ctx.obj.get("workspace_dir", ".")
    service = _tm_service(ctx)

    total, updated = service.import_tm(namespace, input_file, format)
    print_success(f"Imported data. Processed {total} segments, updated {updated}.")


@admin_app.command()
def prune(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace to prune"),
) -> None:
    """Remove deprecated (orphaned-from-source) segments from the Translation Memory."""
    ctx.obj.get("workspace_dir", ".")
    service = _tm_service(ctx)

    removed = service.prune(namespace)
    print_success(
        f"Pruned {removed} deprecated segment(s) (orphaned from source) from {namespace}."
    )


@admin_app.command()
def repair(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace to repair"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report corrupt lines without rewriting the namespace file",
    ),
) -> None:
    """Repair a namespace by skipping corrupt JSONL lines and compacting."""
    service = _tm_service(ctx)

    corrupt_lines = service.repair(namespace, dry_run=dry_run)
    if not corrupt_lines:
        print_success(f"No corrupt lines found in namespace '{namespace}'.")
        return

    if dry_run:
        print_warning(
            f"Found {len(corrupt_lines)} corrupt line(s) in '{namespace}' (dry run)."
        )
    else:
        print_success(
            f"Repaired namespace '{namespace}': skipped {len(corrupt_lines)} "
            "corrupt line(s) and compacted the TM."
        )
    for report in corrupt_lines:
        print_info(f"  Line {report.line_number}: {report.detail}")


@admin_app.command()
def reset(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace to reset"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Also reset human-reviewed segments (REVIEWED, APPROVED)",
    ),
) -> None:
    """Reset machine-translated segments in a namespace back to GENERATED."""
    service = _tm_service(ctx)

    count = service.reset(namespace, force=force)
    print_info(f"Reset {count} segments back to GENERATED state in {namespace}.")
