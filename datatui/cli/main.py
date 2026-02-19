from pathlib import Path
from typing import Optional

import typer

__all__ = ["app", "main"]

app = typer.Typer(
    name="datatui",
    help="DataTUI - Data Analysis Toolkit for your Terminal",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.command()
def inspect(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    no_quality: bool = typer.Option(False, "--no-quality", help="Skip quality score calculation"),
    sample: int = typer.Option(5, "--sample", "-s", help="Number of sample rows to display"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.inspect import run_inspect
    run_inspect(file, no_quality, sample, json_output, quiet)


@app.command()
def analyze(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to JSON file"),
    skip_multivariate: bool = typer.Option(False, "--skip-multivariate", help="Skip multivariate outlier detection"),
    columns: Optional[str] = typer.Option(None, "--columns", "-c", help="Comma-separated column names to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.analyze import run_analyze
    run_analyze(file, output, skip_multivariate, columns, json_output, quiet)


@app.command()
def schema(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    column: Optional[str] = typer.Option(None, "--column", "-c", help="Show details for a specific column"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.schema import run_schema
    run_schema(file, column, json_output, quiet)


@app.command()
def stats(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    column: Optional[str] = typer.Option(None, "--column", "-c", help="Analyze a specific column"),
    numeric_only: bool = typer.Option(False, "--numeric-only", help="Show only numeric columns"),
    categorical_only: bool = typer.Option(False, "--categorical-only", help="Show only categorical columns"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.stats import run_stats
    run_stats(file, column, numeric_only, categorical_only, json_output, quiet)


@app.command()
def missing(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    threshold: float = typer.Option(0.0, "--threshold", "-t", help="Only show columns above this missing percentage"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.missing import run_missing
    run_missing(file, threshold, json_output, quiet)


@app.command()
def outliers(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    method: str = typer.Option("all", "--method", "-m", help="Detection method: iqr, zscore, mad, all"),
    column: Optional[str] = typer.Option(None, "--column", "-c", help="Analyze a specific column"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.outliers import run_outliers
    run_outliers(file, method, column, json_output, quiet)


@app.command()
def correlations(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    method: str = typer.Option("pearson", "--method", "-m", help="Correlation method: pearson, spearman, all"),
    min_corr: float = typer.Option(0.3, "--min", help="Minimum correlation to display"),
    top: int = typer.Option(20, "--top", "-n", help="Number of top correlations to show"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.correlations import run_correlations
    run_correlations(file, method, min_corr, top, json_output, quiet)


@app.command()
def distributions(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    column: Optional[str] = typer.Option(None, "--column", "-c", help="Analyze a specific column"),
    bins: int = typer.Option(30, "--bins", "-b", help="Number of histogram bins"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.distributions import run_distributions
    run_distributions(file, column, bins, json_output, quiet)


@app.command()
def report(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    open_report: bool = typer.Option(False, "--open", help="Open report in browser after generation"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    from datatui.cli.commands.report import run_report
    run_report(file, output, open_report, json_output, quiet)


@app.command()
def visualize(
    file: Path = typer.Argument(..., help="Path to the dataset file"),
    type: str = typer.Option("batch", "--type", "-t", help="Type of plot: histogram, box, heatmap, scatter, pair, violin, dist, categorical, missing, timeseries"),
    column: Optional[str] = typer.Option(None, "--column", "-c", help="Column name for single-column plots"),
    columns: Optional[str] = typer.Option(None, "--columns", help="Comma-separated column names for multi-column plots"),
    x: Optional[str] = typer.Option(None, "--x", help="X column/Date column"),
    y: Optional[str] = typer.Option(None, "--y", help="Y column/Value column"),
    hue: Optional[str] = typer.Option(None, "--hue", help="Grouping column"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("png", "--format", help="Output format (png, svg, pdf)"),
    dpi: int = typer.Option(300, "--dpi", help="DPI (default: 300)"),
    top_n: int = typer.Option(20, "--top-n", help="Top N categories (default: 20)"),
    batch: bool = typer.Option(False, "--batch", help="Generate all recommended plots"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Output directory for batch mode"),
) -> None:
    from datatui.cli.commands.visualize import run_visualize
    run_visualize(file, type, column, columns, x, y, hue, output, format, dpi, top_n, batch, output_dir)


@app.command()
def tui(
    file_path: Path = typer.Argument(..., help="Path to the dataset file to explore"),
    theme: str = typer.Option("dark", "--theme", "-t", help="TUI theme: dark"),
) -> None:
    from datatui.tui.app import DatatuiApp

    tui_app = DatatuiApp(file_path=file_path)
    tui_app.run()


def main() -> None:
    app()
