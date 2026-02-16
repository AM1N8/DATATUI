from rich.console import Console
from rich.panel import Panel

console = Console()


def print_header(text: str):
    """Print section header."""
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold cyan]{text}[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")


def print_success(text: str):
    """Print success message."""
    console.print(f"[bold green]✓[/bold green] {text}")


def print_error(text: str):
    """Print error message."""
    console.print(f"[bold red]✗[/bold red] {text}")


def print_warning(text: str):
    """Print warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] {text}")


def print_info(text: str):
    """Print info message."""
    console.print(f"[bold blue]ℹ[/bold blue] {text}")