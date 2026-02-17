import json
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from datatui.cli.output.themes import (
    PRIMARY,
    SECONDARY,
    SUCCESS,
    WARNING,
    ERROR,
    DIM,
    HEADER,
    BANNER,
    QUALITY_THRESHOLDS,
    MISSING_THRESHOLDS,
    OUTLIER_THRESHOLDS,
)

__all__ = [
    "console",
    "print_banner",
    "print_section",
    "print_success",
    "print_warning",
    "print_error",
    "print_info",
    "print_json_output",
    "print_error_panel",
    "get_quality_style",
    "get_missing_style",
    "get_outlier_style",
    "get_correlation_style",
    "format_number",
    "format_percentage",
    "format_memory",
]

console = Console()


def print_banner() -> None:
    text = Text(BANNER, style=PRIMARY)
    console.print(text)
    console.print(
        "  Data Analysis Toolkit for your Terminal",
        style=DIM,
    )
    console.print()


def print_section(title: str) -> None:
    console.print()
    console.rule(f"[{HEADER}]{title}[/]", style="cyan")
    console.print()


def print_success(message: str) -> None:
    console.print(f"[{SUCCESS}][OK][/] {message}")


def print_warning(message: str) -> None:
    console.print(f"[{WARNING}][!][/] {message}")


def print_error(message: str) -> None:
    console.print(f"[{ERROR}][X][/] {message}")


def print_info(message: str) -> None:
    console.print(f"[{DIM}][i][/] {message}")


def print_json_output(data: Any) -> None:
    console.print_json(json.dumps(data, indent=2, default=str))


def print_error_panel(title: str, message: str) -> None:
    panel = Panel(
        f"[{ERROR}]{message}[/]",
        title=f"[{ERROR}]{title}[/]",
        border_style="red",
        box=box.ROUNDED,
    )
    console.print(panel)


def get_quality_style(score: float) -> str:
    if score >= QUALITY_THRESHOLDS["excellent"]:
        return SUCCESS
    if score >= QUALITY_THRESHOLDS["good"]:
        return "green"
    if score >= QUALITY_THRESHOLDS["fair"]:
        return WARNING
    return ERROR


def get_missing_style(percentage: float) -> str:
    if percentage >= MISSING_THRESHOLDS["critical"]:
        return ERROR
    if percentage >= MISSING_THRESHOLDS["high"]:
        return WARNING
    if percentage >= MISSING_THRESHOLDS["medium"]:
        return "yellow"
    return SUCCESS


def get_outlier_style(percentage: float) -> str:
    if percentage >= OUTLIER_THRESHOLDS["critical"]:
        return ERROR
    if percentage >= OUTLIER_THRESHOLDS["high"]:
        return WARNING
    if percentage >= OUTLIER_THRESHOLDS["medium"]:
        return "yellow"
    return SUCCESS


def get_correlation_style(value: float) -> str:
    abs_val = abs(value)
    if abs_val >= 0.8:
        return ERROR
    if abs_val >= 0.6:
        return WARNING
    if abs_val >= 0.4:
        return "yellow"
    return DIM


def format_number(value: float, precision: int = 4) -> str:
    if abs(value) >= 1e6:
        return f"{value:.2e}"
    if abs(value) < 0.001 and value != 0:
        return f"{value:.2e}"
    return f"{value:.{precision}f}"


def format_percentage(value: float, precision: int = 2) -> str:
    return f"{value:.{precision}f}%"


def format_memory(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    if mb >= 1:
        return f"{mb:.2f} MB"
    return f"{mb * 1024:.2f} KB"
