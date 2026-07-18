"""Shared Rich-based console helpers, tables, and progress layout for the CLI."""

from types import TracebackType
from typing import Any, Self

from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

console = Console()


class TransientProgressLayout:
    """A layout that wraps a Progress bar and shows a transient panel of recent errors."""

    def __init__(self, console: Console, max_errors: int = 3):
        self.console = console
        self.max_errors = max_errors
        self.recent_errors: list[str] = []
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            BarColumn(
                bar_width=30,
                style="bright_black",
                complete_style="cyan",
                finished_style="green",
            ),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TextColumn("[bright_black]{task.fields[seg_info]}"),
            console=self.console,
        )
        self.live = Live(
            self._get_renderable(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )

    def _get_renderable(self) -> RenderableType:
        if not self.recent_errors:
            return self.progress
        else:
            error_text = "\n".join(self.recent_errors)
            error_panel = Panel(
                error_text,
                title="[bold red]Recent Errors[/bold red]",
                border_style="red",
                expand=True,
            )
            return Group(self.progress, error_panel)

    def add_error(self, error_msg: str) -> None:
        """Adds an error to the panel and updates the layout."""
        self.recent_errors.append(error_msg)
        if len(self.recent_errors) > self.max_errors:
            self.recent_errors.pop(0)
        self.live.update(self._get_renderable())

    def __enter__(self) -> Self:
        """Starts the live display block."""
        self.live.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stops the live display block."""
        self.live.__exit__(exc_type, exc_val, exc_tb)


def create_standard_table(expand: bool = True, **kwargs: Any) -> Table:
    """Creates a standardized Rich Table with clean borders and consistent styling."""
    return Table(
        box=box.SIMPLE,
        expand=expand,
        border_style="bright_black",
        header_style="bold cyan",
        **kwargs,
    )


def create_panel(
    renderable: Any, title: str | None = None, border_style: str = "bright_black"
) -> Panel:
    """Creates a standardized Rich Panel for structured output blocks."""
    return Panel(
        renderable,
        title=f"[bold white]{title}[/bold white]" if title else None,
        border_style=border_style,
        expand=True,
        title_align="left",
    )


def print_success(msg: str) -> None:
    """Print a standardized success message."""
    console.print(f"[bold green]✓[/bold green] [green]{msg}[/green]")


def print_warning(msg: str) -> None:
    """Print a standardized warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] [yellow]{msg}[/yellow]")


def print_error(msg: str) -> None:
    """Print a standardized error panel."""
    console.print(
        create_panel(
            f"[red]{msg}[/red]",
            title="[bold red]✗ Error[/bold red]",
            border_style="red",
        )
    )


def print_info(msg: str) -> None:
    """Print a standardized info message."""
    console.print(f"[bold cyan]i[/bold cyan] [cyan]{msg}[/cyan]")
