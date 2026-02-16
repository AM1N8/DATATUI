import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()

app = typer.Typer(
    name="datatui",
    help="🦇 Datatui - Explore the castle of your data",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True
)


@app.command()
def version():
    """Show version information."""
    console.print(f"[bold cyan]Datatui[/bold cyan] version [green]0.1.0[/green]")


@app.command()
def inspect(
    file_path: Path = typer.Argument(..., help="Path to dataset file")
):
    """Quick dataset inspection."""
    from datatui.core.loader import load_dataset
    from datatui.core.analyzer import quick_analyze, get_data_quality_score
    from rich.table import Table
    from rich.panel import Panel
    
    console.print(f"[bold cyan]Inspecting:[/bold cyan] {file_path.name}\n")
    
    try:
        with console.status("[bold cyan]Loading dataset...", spinner="dots"):
            df = load_dataset(file_path)
        
        summary = quick_analyze(df, dataset_name=file_path.stem)
        
        table = Table(title="Dataset Overview", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Dataset", summary['dataset_name'])
        table.add_row("Rows", f"{summary['rows']:,}")
        table.add_row("Columns", f"{summary['columns']}")
        table.add_row("Memory", f"{summary['memory_mb']:.2f} MB")
        table.add_row("Missing", f"{summary['missing_percentage']:.2f}%")
        
        for dtype, count in summary['column_types'].items():
            table.add_row(f"  {dtype}", f"{count} columns")
        
        console.print(table)
        
        with console.status("[bold cyan]Calculating quality score...", spinner="dots"):
            quality = get_data_quality_score(df)
        
        quality_color = "green" if quality['quality_rating'] == 'excellent' else \
                      "yellow" if quality['quality_rating'] == 'good' else "red"
        
        console.print(Panel(
            f"[bold {quality_color}]{quality['overall_score']:.1f}/100[/bold {quality_color}] - {quality['quality_rating'].upper()}",
            title="🏆 Data Quality Score"
        ))
        
        console.print("\n[bold green]✓[/bold green] Inspection complete!")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def analyze(
    file_path: Path = typer.Argument(..., help="Path to dataset file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to JSON")
):
    """Run full analysis on dataset."""
    from datatui.core.loader import load_dataset
    from datatui.core.analyzer import DataAnalyzer
    
    console.print(f"[bold cyan]Analyzing:[/bold cyan] {file_path.name}\n")
    
    try:
        df = load_dataset(file_path)
        analyzer = DataAnalyzer(df, dataset_name=file_path.stem)
        
        with console.status("[bold cyan]Running complete analysis...", spinner="dots"):
            results = analyzer.analyze_all()
        
        console.print(f"\n[bold green]✓[/bold green] Analysis complete in {results.analysis_time_seconds:.2f}s")
        console.print(f"  • {results.total_rows:,} rows × {results.total_columns} columns")
        console.print(f"  • {results.memory_mb:.2f} MB in memory")
        
        if output:
            import json
            from dataclasses import asdict
            
            with open(output, 'w') as f:
                json.dump(asdict(results), f, indent=2, default=str)
            
            console.print(f"\n[bold green]✓[/bold green] Results saved to {output}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.callback()
def callback():
    """
    🦇 Datatui - A powerful dataset analysis tool.
    
    Explore, analyze, and understand your data through the terminal.
    """
    pass


def main():
    app()


if __name__ == "__main__":
    main()