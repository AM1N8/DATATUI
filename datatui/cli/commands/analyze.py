import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from datatui.core.loader import load_dataset
from datatui.core.analyzer import DataAnalyzer
from datatui.cli.output.console import print_header, print_success, print_error

app = typer.Typer()
console = Console()


@app.command()
def full(
    file_path: Path = typer.Argument(..., help="Path to dataset file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to JSON"),
    skip_multivariate: bool = typer.Option(False, "--skip-multivariate", help="Skip multivariate outlier detection")
):
    """Run complete analysis on dataset."""
    
    print_header(f"Analyzing: {file_path.name}")
    
    try:
        df = load_dataset(file_path)
        analyzer = DataAnalyzer(df, dataset_name=file_path.stem)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Running analysis...", total=7)
            
            progress.update(task, description="[cyan]Analyzing schema...")
            analyzer.analyze_schema()
            progress.advance(task)
            
            progress.update(task, description="[cyan]Computing statistics...")
            analyzer.analyze_statistics()
            progress.advance(task)
            
            progress.update(task, description="[cyan]Checking missing values...")
            analyzer.analyze_missing()
            progress.advance(task)
            
            progress.update(task, description="[cyan]Detecting outliers...")
            analyzer.analyze_outliers(skip_multivariate=skip_multivariate)
            progress.advance(task)
            
            progress.update(task, description="[cyan]Calculating correlations...")
            analyzer.analyze_correlations()
            progress.advance(task)
            
            progress.update(task, description="[cyan]Analyzing distributions...")
            analyzer.analyze_distributions()
            progress.advance(task)
            
            progress.update(task, description="[cyan]Finalizing...")
            results = analyzer.analyze_all(skip_multivariate_outliers=skip_multivariate)
            progress.advance(task)
        
        console.print(f"\n[bold green]✓[/bold green] Analysis complete in {results.analysis_time_seconds:.2f}s")
        console.print(f"  • {results.total_rows:,} rows × {results.total_columns} columns")
        console.print(f"  • {results.memory_mb:.2f} MB in memory")
        
        if output:
            import json
            from dataclasses import asdict
            
            with open(output, 'w') as f:
                json.dump(asdict(results), f, indent=2, default=str)
            
            print_success(f"Results saved to {output}")
        
    except Exception as e:
        print_error(f"Analysis failed: {e}")
        raise typer.Exit(1)


@app.command()
def column(
    file_path: Path = typer.Argument(..., help="Path to dataset file"),
    column_name: str = typer.Argument(..., help="Column to analyze")
):
    """Analyze a specific column in detail."""
    
    try:
        df = load_dataset(file_path)
        analyzer = DataAnalyzer(df)
        
        col_analysis = analyzer.get_column_analysis(column_name)
        
        if 'error' in col_analysis:
            print_error(col_analysis['error'])
            raise typer.Exit(1)
        
        console.print(f"\n[bold cyan]Column:[/bold cyan] {column_name}\n")
        
        if 'schema' in col_analysis:
            schema = col_analysis['schema']
            console.print(f"[cyan]Type:[/cyan] {schema['data_type']}")
            console.print(f"[cyan]Semantic:[/cyan] {schema['semantic_type']}")
            console.print(f"[cyan]Unique values:[/cyan] {schema['unique_count']:,}")
            console.print(f"[cyan]Null percentage:[/cyan] {schema['null_percentage']:.2f}%")
        
        if 'statistics' in col_analysis:
            stats = col_analysis['statistics']
            console.print(f"\n[bold]Statistics:[/bold]")
            if 'mean' in stats:
                console.print(f"  Mean: {stats['mean']:.2f}")
                console.print(f"  Median: {stats['median']:.2f}")
                console.print(f"  Std: {stats['std']:.2f}")
                console.print(f"  Skewness: {stats['skewness']:.3f}")
        
        if 'outliers' in col_analysis:
            outliers = col_analysis['outliers']
            console.print(f"\n[bold]Outliers:[/bold]")
            console.print(f"  IQR method: {outliers['iqr_outlier_count']} ({outliers['iqr_outlier_count']/outliers['total_count']*100:.2f}%)")
            console.print(f"  Z-score method: {outliers['zscore_outlier_count']}")
        
    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(1)