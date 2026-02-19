import typer
import polars as pl
from pathlib import Path
from typing import List, Optional, Dict
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from datatui.visualizers import (
    generate_histogram, generate_box_plot, generate_correlation_heatmap,
    generate_scatter_plot, generate_pair_plot, generate_violin_plot,
    generate_distribution_comparison, generate_categorical_bar,
    generate_missing_pattern, generate_time_series
)

console = Console()

def run_visualize(
    file: Path,
    type: str = "batch",
    column: Optional[str] = None,
    columns: Optional[str] = None,
    x: Optional[str] = None,
    y: Optional[str] = None,
    hue: Optional[str] = None,
    output: Optional[Path] = None,
    format: str = "png",
    dpi: int = 300,
    top_n: int = 20,
    batch: bool = False,
    output_dir: Optional[Path] = None
) -> None:
    """Entry point for the visualization command."""
    # Load dataset
    try:
        from datatui.cli.utils.validators import validate_file_path, load_dataframe
        file = validate_file_path(file)
        df, _ = load_dataframe(file)
    except Exception as e:
        console.print(f"[red]Error loading file: {e}[/]")
        raise typer.Exit(1)

    if batch or type == "batch":
        if not output_dir:
            output_dir = Path("plots")
        run_batch_mode(df, output_dir, format, dpi)
        return

    if not output:
        output = Path(f"{type}_{column or 'plot'}.{format}")

    try:
        if type == "histogram":
            if not column: raise ValueError("Histogram requires --column")
            generate_histogram(df, column, output, format, dpi)
        elif type == "box":
            cols = columns.split(',') if columns else [column] if column else []
            if not cols: raise ValueError("Box plot requires --column or --columns")
            generate_box_plot(df, cols, output, format, dpi)
        elif type == "heatmap":
            numeric_df = df.select(pl.col(pl.NUMERIC_DTYPES))
            if numeric_df.width < 2: raise ValueError("Heatmap requires at least 2 numeric columns")
            corr_matrix = numeric_df.to_pandas().corr().values.tolist()
            labels = numeric_df.columns
            generate_correlation_heatmap(corr_matrix, labels, output, format, dpi)
        elif type == "scatter":
            if not x or not y: raise ValueError("Scatter plot requires --x and --y")
            generate_scatter_plot(df, x, y, output, hue, format, dpi)
        elif type == "pair":
            cols = columns.split(',') if columns else []
            if not cols: raise ValueError("Pair plot requires --columns")
            generate_pair_plot(df, cols, output, hue, format, dpi)
        elif type == "violin":
            cols = columns.split(',') if columns else [column] if column else []
            if not cols: raise ValueError("Violin plot requires --column or --columns")
            generate_violin_plot(df, cols, output, format, dpi)
        elif type == "dist":
            if not column: raise ValueError("Dist comparison requires --column")
            generate_distribution_comparison(df, column, output, format, dpi)
        elif type == "categorical":
            if not column: raise ValueError("Categorical bar requires --column")
            generate_categorical_bar(df, column, output, top_n, format, dpi)
        elif type == "missing":
            generate_missing_pattern(df, output, format, dpi)
        elif type == "timeseries":
            if not x or not y: raise ValueError("Time series requires --x (date) and --y (value)")
            generate_time_series(df, x, y, output, format, dpi)
        else:
            console.print(f"[red]Unknown plot type: {type}[/]")
            raise typer.Exit(1)
            
        console.print(f"[green]Successfully generated {type} plot: {output}[/]")
    except Exception as e:
        console.print(f"[red]Error generating plot: {e}[/]")
        raise typer.Exit(1)

    if batch:
        if not output_dir:
            output_dir = Path("plots")
        run_batch_mode(df, output_dir, format, dpi)
        return

    if not output:
        output = Path(f"{type}_{column or 'plot'}.{format}")

    try:
        if type == "histogram":
            if not column: raise ValueError("Histogram requires --column")
            generate_histogram(df, column, output, format, dpi)
        elif type == "box":
            cols = columns.split(',') if columns else [column] if column else []
            if not cols: raise ValueError("Box plot requires --column or --columns")
            generate_box_plot(df, cols, output, format, dpi)
        elif type == "heatmap":
            # Compute correlation matrix first
            numeric_df = df.select(pl.col(pl.NUMERIC_DTYPES))
            if numeric_df.width < 2: raise ValueError("Heatmap requires at least 2 numeric columns")
            corr_matrix = numeric_df.to_pandas().corr().values.tolist()
            labels = numeric_df.columns
            generate_correlation_heatmap(corr_matrix, labels, output, format, dpi)
        elif type == "scatter":
            if not x or not y: raise ValueError("Scatter plot requires --x and --y")
            generate_scatter_plot(df, x, y, output, hue, format, dpi)
        elif type == "pair":
            cols = columns.split(',') if columns else []
            if not cols: raise ValueError("Pair plot requires --columns")
            generate_pair_plot(df, cols, output, hue, format, dpi)
        elif type == "violin":
            cols = columns.split(',') if columns else [column] if column else []
            if not cols: raise ValueError("Violin plot requires --column or --columns")
            generate_violin_plot(df, cols, output, format, dpi)
        elif type == "dist":
            if not column: raise ValueError("Dist comparison requires --column")
            generate_distribution_comparison(df, column, output, format, dpi)
        elif type == "categorical":
            if not column: raise ValueError("Categorical bar requires --column")
            generate_categorical_bar(df, column, output, top_n, format, dpi)
        elif type == "missing":
            generate_missing_pattern(df, output, format, dpi)
        elif type == "timeseries":
            if not x or not y: raise ValueError("Time series requires --x (date) and --y (value)")
            generate_time_series(df, x, y, output, format, dpi)
        else:
            console.print(f"[red]Unknown plot type: {type}[/]")
            raise typer.Exit(1)
            
        console.print(f"[green]Successfully generated {type} plot: {output}[/]")
    except Exception as e:
        console.print(f"[red]Error generating plot: {e}[/]")
        raise typer.Exit(1)

def run_batch_mode(df: pl.DataFrame, output_dir: Path, format: str, dpi: int):
    """Generate a batch of recommended plots."""
    os.makedirs(output_dir, exist_ok=True)
    
    numeric_cols = [c for c, t in zip(df.columns, df.dtypes) if t in pl.NUMERIC_DTYPES]
    cat_cols = [c for c, t in zip(df.columns, df.dtypes) if t in [pl.String, pl.Categorical]]
    
    plots_to_generate = []
    
    # 1. Histograms for numeric columns (top 5 by default)
    for col in numeric_cols[:5]:
        plots_to_generate.append(("histogram", col, output_dir / f"hist_{col}.{format}"))
        
    # 2. Box plot for all numeric
    if numeric_cols:
        plots_to_generate.append(("box", numeric_cols[:10], output_dir / f"box_comparison.{format}"))
        
    # 3. Heatmap
    if len(numeric_cols) >= 2:
         plots_to_generate.append(("heatmap", numeric_cols, output_dir / f"correlation_heatmap.{format}"))
         
    # 4. Categorical bars
    for col in cat_cols[:3]:
        plots_to_generate.append(("categorical", col, output_dir / f"cat_{col}.{format}"))
        
    # 5. Missing pattern
    plots_to_generate.append(("missing", None, output_dir / f"missing_pattern.{format}"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Generating batch plots...", total=len(plots_to_generate))
        
        generated_files = []
        for ptype, pinfo, ppath in plots_to_generate:
            progress.update(task, description=f"Generating {ptype} for {pinfo if pinfo else 'dataset'}...")
            try:
                if ptype == "histogram":
                    generate_histogram(df, pinfo, ppath, format, dpi)
                elif ptype == "box":
                    generate_box_plot(df, pinfo, ppath, format, dpi)
                elif ptype == "heatmap":
                    numeric_df = df.select(pl.col(pl.NUMERIC_DTYPES))
                    corr_matrix = numeric_df.to_pandas().corr().values.tolist()
                    generate_correlation_heatmap(corr_matrix, numeric_df.columns, ppath, format, dpi)
                elif ptype == "categorical":
                    generate_categorical_bar(df, pinfo, ppath, 20, format, dpi)
                elif ptype == "missing":
                    generate_missing_pattern(df, ppath, format, dpi)
                
                generated_files.append({"type": ptype, "info": str(pinfo), "path": ppath.name})
            except Exception as e:
                console.print(f"[yellow]Skipped {ptype}: {e}[/]")
            
            progress.advance(task)

    # Create index.html
    create_batch_index(output_dir, generated_files)
    console.print(f"[bold green]Batch generation complete![/] View results in [blue]{output_dir}/index.html[/]")

def create_batch_index(output_dir: Path, files: List[Dict[str, str]]):
    """Create a simple gallery index.html."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DataTUI Visualization Gallery</title>
        <style>
            body {{ font-family: sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
            .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }}
            .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px; }}
            .card img {{ width: 100%; border-radius: 4px; }}
            .card h3 {{ margin: 10px 0 5px 0; color: #58a6ff; }}
            .card p {{ margin: 0; font-size: 0.9em; color: #8b949e; }}
        </style>
    </head>
    <body>
        <h1>DataTUI Visualization Gallery</h1>
        <div class="gallery">
    """
    for f in files:
        html += f"""
            <div class="card">
                <img src="{f['path']}" alt="{f['type']}">
                <h3>{f['type'].capitalize()}</h3>
                <p>{f['info']}</p>
            </div>
        """
    html += """
        </div>
    </body>
    </html>
    """
    with open(output_dir / "index.html", "w") as f:
        f.write(html)
