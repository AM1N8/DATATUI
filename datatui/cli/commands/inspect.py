import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from datatui.core.loader import load_dataset, LoaderError
from datatui.core.analyzer import quick_analyze, get_data_quality_score
from datatui.cli.output.console import print_header, print_success, print_error
from datatui.cli.utils.spinner import with_spinner

app = typer.Typer()
console = Console()


@app.command()
def quick(
    file_path: Path = typer.Argument(..., help="Path to dataset file"),
    show_quality: bool = typer.Option(True, "--quality/--no-quality", help="Show data quality score")
):
    """Quick dataset overview."""
    
    print_header(f"Inspecting: {file_path.name}")
    
    try:
        df = with_spinner(
            lambda: load_dataset(file_path),
            text="Loading dataset..."
        )
        
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
        
        if show_quality:
            quality = with_spinner(
                lambda: get_data_quality_score(df),
                text="Calculating quality score..."
            )
            
            quality_color = "green" if quality['quality_rating'] == 'excellent' else \
                          "yellow" if quality['quality_rating'] == 'good' else \
                          "red"
            
            console.print(Panel(
                f"[bold {quality_color}]{quality['overall_score']:.1f}/100[/bold {quality_color}] - {quality['quality_rating'].upper()}",
                title="🏆 Data Quality Score"
            ))
        
        print_success("Inspection complete!")
        
    except LoaderError as e:
        print_error(f"Failed to load dataset: {e}")
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command()
def columns(
    file_path: Path = typer.Argument(..., help="Path to dataset file"),
    limit: int = typer.Option(None, "--limit", "-n", help="Limit number of columns to show")
):
    """List all columns with basic info."""
    
    try:
        df = with_spinner(
            lambda: load_dataset(file_path),
            text="Loading dataset..."
        )
        
        from ...core.schema import detect_schema
        
        schema = with_spinner(
            lambda: detect_schema(df),
            text="Detecting schema..."
        )
        
        table = Table(title="Columns")
        table.add_column("Column", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Semantic", style="yellow")
        table.add_column("Nulls", style="red")
        table.add_column("Unique", style="magenta")
        
        columns_to_show = list(schema.items())[:limit] if limit else list(schema.items())
        
        for col_name, col_info in columns_to_show:
            table.add_row(
                col_name,
                col_info.data_type.value,
                col_info.semantic_type.value,
                f"{col_info.null_percentage:.1f}%",
                f"{col_info.unique_count:,}"
            )
        
        console.print(table)
        
        if limit and len(schema) > limit:
            console.print(f"\n[dim]Showing {limit} of {len(schema)} columns[/dim]")
        
    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(1)