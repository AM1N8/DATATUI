import typer
from pathlib import Path
from rich.console import Console

from ...core.loader import load_dataset
from ...core.analyzer import DataAnalyzer
from ..output.console import print_header, print_success, print_error
from ..utils.spinner import with_spinner

app = typer.Typer()
console = Console()


@app.command()
def html(
    file_path: Path = typer.Argument(..., help="Path to dataset file"),
    output: Path = typer.Option("report.html", "--output", "-o", help="Output HTML file"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open in browser")
):
    """Generate HTML report."""
    
    print_header(f"Generating report for: {file_path.name}")
    
    try:
        df = with_spinner(
            lambda: load_dataset(file_path),
            text="Loading dataset..."
        )
        
        analyzer = DataAnalyzer(df, dataset_name=file_path.stem)
        
        results = with_spinner(
            lambda: analyzer.analyze_all(),
            text="Analyzing dataset..."
        )
        
        console.print("[yellow]HTML report generation not yet implemented.[/yellow]")
        console.print("[dim]Coming soon: Interactive HTML reports with charts![/dim]")
        
        print_success(f"Report would be saved to: {output}")
        
    except Exception as e:
        print_error(f"Report generation failed: {e}")
        raise typer.Exit(1)