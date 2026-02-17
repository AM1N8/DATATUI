from typing import Optional

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from datatui.cli.output.console import console

__all__ = [
    "create_progress",
    "create_spinner",
]


def create_progress(description: str = "Processing") -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def create_spinner(message: str = "Analyzing"):
    return console.status(f"[bold cyan]{message}...", spinner="dots")
