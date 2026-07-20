"""CLI commands for sync, translate, build, and review workflows."""

import click
import typer
from rich.markup import escape

from lilt.cli.ui import (
    TransientProgressLayout,
    console,
    create_panel,
    create_standard_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from lilt.exceptions import BuildError, TranslationValidationError
from lilt.models.segment import SegmentStatus
from lilt.models.status_resolver import StatusResolver
from lilt.models.translation_mode import TranslationMode
from lilt.models.translation_stage import TranslationStage
from lilt.services.pipeline_service import PipelineService


def _pipeline_service(ctx: typer.Context) -> PipelineService:
    workspace_ctx = ctx.obj.get("workspace_ctx")
    workspace_dir = ctx.obj.get("workspace_dir", ".")
    return PipelineService(workspace_dir, workspace_ctx=workspace_ctx)


app = typer.Typer(
    help="Manage the core LILT pipeline (sync, translate, build, review).",
    rich_markup_mode="rich",
)


@app.command()
def sync(
    ctx: typer.Context,
    input_file: str = typer.Argument(..., help="Path to the LaTeX file to parse"),
) -> None:
    """Parse a LaTeX document and populate the Translation Memory."""
    ctx.obj.get("workspace_dir", ".")
    service = _pipeline_service(ctx)

    try:
        results = service.sync_file(input_file)
        table = create_standard_table()
        table.add_column("Namespace", style="cyan")
        table.add_column("Active", justify="right")
        table.add_column("New", justify="right")
        table.add_column("Updated", justify="right")
        table.add_column("Conflicts", justify="right")
        table.add_column("Deprecated", justify="right", style="dim")
        for result in results:
            table.add_row(
                result.namespace,
                str(result.total_active),
                str(result.new_segments),
                str(result.updated_segments),
                str(result.new_conflicts),
                str(result.deprecated_marked),
            )
        console.print(table)
        seen_warn: set[str] = set()
        for result in results:
            for msg in result.capacity_warnings:
                if msg not in seen_warn:
                    seen_warn.add(msg)
                    print_warning(msg)
        if len(results) > 1:
            print_info(f"Auto-discovered and synced {len(results)} dependency files.")
    except (FileNotFoundError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(code=1) from None


@app.command()
def translate(
    ctx: typer.Context,
    namespace: str | None = typer.Argument(None, help="The TM namespace to translate"),
    all_namespaces: bool = typer.Option(
        False, "--all", "-a", help="Translate all namespaces in the TM"
    ),
    status_filter: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help=f"Translate only segments with this status ({StatusResolver.help_text()})",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help=(
            "In workflow mode, expands draft eligibility only (not critique/refine). "
            "In sequential mode, re-runs full D→C→R on non-immutable segments."
        ),
    ),
    segment_id: str | None = typer.Option(
        None, "--id", help="Translate only a specific segment ID"
    ),
    stage: TranslationStage | None = typer.Option(
        None,
        "--stage",
        help=(
            "Workflow only: draft, critique, or refine. "
            "Critique needs drafted segments; refine needs critiqued "
            "(--force does not invent those artifacts)."
        ),
    ),
    mode: TranslationMode | None = typer.Option(
        None,
        "--mode",
        help="Override translation mode: workflow (batched stages) or sequential (depth-first per segment)",
    ),
) -> None:
    """Translate pending segments in a namespace or globally.

    Interrupted runs: re-invoke translate (no separate resume command).
    Finished segments stay in the TM.
    """
    ctx.obj.get("workspace_dir", ".")
    service = _pipeline_service(ctx)

    if not namespace and not all_namespaces:
        print_error("You must provide a namespace argument or use the --all flag.")
        raise typer.Exit(code=1) from None
    if namespace and all_namespaces:
        print_warning(
            "Namespace argument provided alongside --all flag. Ignoring namespace argument."
        )

    service.ctx.preconditions.require_initialized()

    if all_namespaces:
        target_namespaces = service.ctx.repo.list_namespaces()
    else:
        assert namespace is not None, "Namespace must be provided if --all is not set"
        target_namespaces = [namespace]

    if not target_namespaces:
        print_info("No namespaces found in the Translation Memory.")
        return

    try:
        with TransientProgressLayout(console) as layout:
            failures = 0
            for ns in target_namespaces:
                generator = service.run_translation(
                    ns, force, segment_id, status_filter, stage, translation_mode=mode
                )
                task = layout.progress.add_task(
                    f"Translating {ns}...", total=None, seg_info=""
                )
                first = True
                for _current, total, seg_id, status_msg, advance_bar in generator:
                    if advance_bar and "FAIL" in status_msg:
                        failures += 1
                        layout.add_error(
                            f"[red]✖ Failed segment {seg_id[:8]}: {status_msg}[/red]"
                        )

                    if first:
                        layout.progress.update(task, total=total)
                        first = False

                    desc = f"Translating {ns}..."
                    if failures > 0:
                        desc += f" [red]({failures} failed)[/red]"

                    if seg_id == "done" or seg_id == "start":
                        if seg_id == "start":
                            layout.progress.update(
                                task,
                                completed=0,
                                total=total,
                                description=desc,
                                seg_info=f"[yellow]{status_msg}[/yellow]",
                            )
                        else:
                            layout.progress.update(
                                task,
                                description=desc,
                                seg_info=f"[yellow]{status_msg}[/yellow]",
                            )
                    else:
                        color = "red" if "FAIL" in status_msg else "yellow"
                        layout.progress.update(
                            task,
                            advance=1 if advance_bar else 0,
                            description=desc,
                            seg_info=f"[bright_black](ID: {seg_id[:8]})[/bright_black] - [{color}]{status_msg}[/{color}]",
                        )
    except KeyboardInterrupt:
        print_warning("\nTranslation interrupted by user. Progress has been saved.")
        raise typer.Exit(code=130) from None

    remaining_blocked = 0
    for ns in target_namespaces:
        segments = service.ctx.repo.load_namespace(ns)
        remaining_blocked += sum(
            1
            for s in segments.values()
            if s.status in (SegmentStatus.CONFLICT, SegmentStatus.ERROR)
        )

    if failures > 0:
        print_warning(
            f"Translation completed, but {failures} segment(s) encountered errors or conflicts."
        )
        print_info(
            "Next: `lilt tm status`; `lilt tm list NS --status conflict`; "
            "or `lilt pipeline build ... --allow-partial` for a first look."
        )
        raise typer.Exit(code=1) from None
    if remaining_blocked > 0:
        print_warning(
            f"No new work ran, but {remaining_blocked} conflict/error segment(s) remain."
        )
        print_info(
            "Next: `lilt tm list NS --status conflict`; "
            "re-translate with `--force`, or build with `--allow-partial`."
        )
        raise typer.Exit(code=1) from None
    print_success("Translation completed successfully!")


@app.command()
def build(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace to use"),
    input_file: str = typer.Argument(..., help="Path to original LaTeX file"),
    output_file: str = typer.Argument(
        ..., help="Path to save the translated LaTeX file"
    ),
    allow_partial: bool = typer.Option(
        False,
        "--allow-partial",
        help="Emit source text for untranslated segments instead of failing the build",
    ),
) -> None:
    """Reconstruct the translated document and output to a new LaTeX file."""
    ctx.obj.get("workspace_dir", ".")
    service = _pipeline_service(ctx)

    try:
        result = service.run_build(
            namespace, input_file, output_file, allow_partial=allow_partial
        )
        message = f"[green]Successfully built document at:[/green]\n{output_file}"
        if result.skipped:
            skipped_ids = ", ".join(item.segment_id[:8] for item in result.skipped)
            message += (
                f"\n[yellow]Warning: {len(result.skipped)} segment(s) used source "
                f"fallback: {skipped_ids}[/yellow]"
            )
        console.print(
            create_panel(
                message,
                title="Build Complete",
                border_style="green",
            )
        )
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from None
    except Exception as e:
        # Catch BuildError or any other unexpected error
        if isinstance(e, BuildError):
            print_error(str(e))
        else:
            print_error(f"Unexpected error during build: {e}")
        raise typer.Exit(code=1) from None


def _edit_segment(service: PipelineService, namespace: str, seg_id: str) -> bool:
    seg = service.get_segment(namespace, seg_id)

    marker = "\n# --- DO NOT EDIT BELOW THIS LINE ---\n"
    content = f"{seg.translation or ''}{marker}Source Text:\n{seg.source_text}"

    edited = click.edit(content, extension=".txt", require_save=True)
    if edited is not None:
        new_trans = edited.split(marker)[0].strip()
        try:
            service.submit_human_translation(
                namespace, seg.id, new_trans, SegmentStatus.APPROVED
            )
        except TranslationValidationError as exc:
            print_error(f"Validation failed: {exc}")
            return False
        return True
    return False


@app.command()
def review(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace to review"),
) -> None:
    """Interactively review and approve translated segments."""
    ctx.obj.get("workspace_dir", ".")
    service = _pipeline_service(ctx)

    to_review = service.get_segments_to_review(namespace)

    if not to_review:
        print_success(f"No segments pending review in namespace '{namespace}'.")
        raise typer.Exit()

    print_info(f"Found {len(to_review)} segments to review.\n")

    for i, seg in enumerate(to_review, 1):
        table = create_standard_table(show_header=False)
        table.add_column("Property", style="bold yellow")
        table.add_column("Value")
        table.add_row("Source", f"[yellow]{escape(seg.source_text)}[/yellow]")
        table.add_row(
            "Translation",
            f"[green]{escape(seg.translation or '[No translation yet]')}[/green]",
        )

        panel = create_panel(
            table, title=f"Segment {i}/{len(to_review)} [ID: {seg.id[:8]}]"
        )
        console.print(panel)

        while True:
            choice = typer.prompt(
                "Action [a]pprove, [e]dit, [r]eject, [s]kip, [q]uit", default="a"
            ).lower()
            if choice == "a":
                try:
                    service.submit_human_translation(
                        namespace, seg.id, seg.translation, SegmentStatus.APPROVED
                    )
                except TranslationValidationError as exc:
                    print_error(f"Validation failed: {exc}")
                    continue
                print_success("Approved.")
                console.print()
                break
            elif choice == "e":
                if _edit_segment(service, namespace, seg.id):
                    print_success("Saved and approved.")
                    console.print()
                else:
                    print_warning("Edit cancelled. Segment skipped.")
                    console.print()
                break
            elif choice == "r":
                service.update_segment_translation(
                    namespace, seg.id, seg.translation, SegmentStatus.CONFLICT
                )
                print_warning("Rejected (marked as conflict).")
                console.print()
                break
            elif choice == "s":
                print_info("Skipped.")
                console.print()
                break
            elif choice == "q":
                print_info("Exiting review.")
                raise typer.Exit()
            else:
                print_warning("Invalid choice.")


@app.command()
def edit(
    ctx: typer.Context,
    namespace: str = typer.Argument(..., help="The TM namespace"),
    segment_id: str = typer.Argument(..., help="The segment ID or prefix"),
) -> None:
    """Directly edit a specific segment's translation in your $EDITOR."""
    ctx.obj.get("workspace_dir", ".")
    service = _pipeline_service(ctx)

    if _edit_segment(service, namespace, segment_id):
        print_success("Successfully updated and approved segment.")
    else:
        print_warning("No changes made.")
