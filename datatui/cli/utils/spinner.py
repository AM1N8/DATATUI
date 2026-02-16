from typing import Callable, TypeVar
from rich.console import Console
from rich.spinner import Spinner

console = Console()
T = TypeVar('T')


def with_spinner(func: Callable[[], T], text: str = "Loading...") -> T:
    """Execute function with loading spinner."""
    with console.status(f"[bold cyan]{text}[/bold cyan]", spinner="dots"):
        return func()