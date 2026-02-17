from pathlib import Path
from typing import Optional

import typer
from rich.text import Text

from datatui.cli.output.console import (
    console,
    print_banner,
    print_section,
    print_success,
    print_info,
    print_json_output,
    print_error_panel,
    format_number,
)
from datatui.cli.output.tables import build_distributions_table
from datatui.cli.utils.validators import validate_file_path, load_dataframe, validate_column_name
from datatui.cli.utils.progress import create_spinner
from datatui.cli.output.themes import SUCCESS, DIM

__all__ = ["run_distributions"]


def run_distributions(
    file: Path,
    column: Optional[str] = None,
    bins: int = 30,
    json_output: bool = False,
    quiet: bool = False,
) -> None:
    try:
        file = validate_file_path(file)
    except typer.BadParameter as e:
        print_error_panel("File Error", str(e))
        raise typer.Exit(1)

    if not quiet and not json_output:
        print_banner()

    try:
        with create_spinner("Loading dataset"):
            df, dataset_info = load_dataframe(file)
    except Exception as e:
        print_error_panel("Load Error", str(e))
        raise typer.Exit(1)

    from datatui.core.analyzer import DataAnalyzer

    analyzer = DataAnalyzer(df, dataset_name=file.stem)

    with create_spinner("Analyzing distributions"):
        dist_data = analyzer.analyze_distributions(bins=bins)

    if column:
        try:
            validate_column_name(df, column)
        except typer.BadParameter as e:
            print_error_panel("Column Error", str(e))
            raise typer.Exit(1)

        col_dist = dist_data.get("distributions", {}).get(column)
        if col_dist is None:
            print_error_panel("Error", f"No distribution data for column '{column}' (may not be numeric)")
            raise typer.Exit(1)

        if json_output:
            print_json_output({column: col_dist})
            raise typer.Exit(0)

        if quiet:
            console.print(
                f"{column}: {col_dist.get('distribution_type', 'unknown')} | "
                f"skew={format_number(col_dist.get('skewness', 0), 3)}"
            )
            raise typer.Exit(0)

        print_section(f"Distribution: {column}")

        from rich.table import Table
        from rich import box as rich_box

        detail = Table(box=rich_box.ROUNDED, border_style="blue", show_lines=True)
        detail.add_column("Property", style="bold cyan", min_width=20)
        detail.add_column("Value", style="white", min_width=30)

        detail.add_row("Distribution Type", col_dist.get("distribution_type", "unknown"))
        is_normal = col_dist.get("is_normal", False)
        normal_str = f"[{SUCCESS}]Yes[/]" if is_normal else f"[{DIM}]No[/]"
        detail.add_row("Normal?", normal_str)
        detail.add_row("Skewness", format_number(col_dist.get("skewness", 0), 4))
        detail.add_row("Kurtosis", format_number(col_dist.get("kurtosis", 0), 4))

        quartiles = col_dist.get("quartiles", {})
        if quartiles:
            detail.add_row("Min", format_number(quartiles.get("min", 0)))
            detail.add_row("Q25", format_number(quartiles.get("q25", 0)))
            detail.add_row("Median", format_number(quartiles.get("median", 0)))
            detail.add_row("Q75", format_number(quartiles.get("q75", 0)))
            detail.add_row("Max", format_number(quartiles.get("max", 0)))
            detail.add_row("IQR", format_number(quartiles.get("iqr", 0)))
        console.print(detail)

        normality = col_dist.get("normality_tests", {})
        if normality:
            print_section("Normality Tests")
            norm_table = Table(box=rich_box.ROUNDED, border_style="blue", show_lines=False)
            norm_table.add_column("Test", style="bold cyan", min_width=22)
            norm_table.add_column("Statistic", justify="right")
            norm_table.add_column("P-Value", justify="right")
            norm_table.add_column("Normal?", justify="center")

            for test_name in ("shapiro_wilk", "anderson_darling", "dagostino_pearson", "kolmogorov_smirnov"):
                test_data = normality.get(test_name)
                if test_data and isinstance(test_data, dict):
                    stat = test_data.get("statistic", 0)
                    p_val = test_data.get("p_value", test_data.get("critical_value", 0))
                    is_n = test_data.get("is_normal", False)
                    n_str = f"[{SUCCESS}]Yes[/]" if is_n else f"[{DIM}]No[/]"
                    norm_table.add_row(
                        test_name.replace("_", " ").title(),
                        format_number(stat, 6),
                        format_number(p_val, 6),
                        n_str,
                    )
            console.print(norm_table)

        histogram = col_dist.get("histogram", {})
        counts = histogram.get("counts", [])
        edges = histogram.get("edges", [])
        
        if counts and len(counts) > 0:
            print_section("Histogram")
            try:
                import plotext as plt
                
                plt.clf()
                plt.plotsize(80, 20)
                plt.theme("dark")
                plt.title(f"Histogram: {column}")
                
                # plotext.bar takes x and y
                # We have bins edges. We need centers or just use range.
                # counts length is N, edges length is N+1
                bar_labels = [f"{e:.2f}" for e in edges[:-1]]
                
                plt.bar(bar_labels, counts, color="blue", label=column)
                plt.xlabel("Value")
                plt.ylabel("Frequency")
                
                plot_str = plt.build()
                console.print(Text.from_ansi(plot_str))
                
            except ImportError:
                # Fallback to simple rich bars
                max_count = max(counts) if counts else 1
                bar_width = 40
                for i, count in enumerate(counts):
                    bar_len = int((count / max_count) * bar_width)
                    bar = "█" * bar_len
                    if i < len(edges) - 1:
                        label = f"{edges[i]:.2f}"
                    else:
                        label = ""
                    console.print(f"  {label:>10} | [cyan]{bar}[/] {count}")
    else:
        if json_output:
            print_json_output(dist_data)
            raise typer.Exit(0)

        if quiet:
            for col_name, d in dist_data.get("distributions", {}).items():
                console.print(f"{col_name}: {d.get('distribution_type', 'unknown')}")
            raise typer.Exit(0)

        console.print(build_distributions_table(dist_data))

        summary = dist_data.get("summary", {})
        if summary:
            print_section("Distribution Summary")
            print_info(f"Normal columns: {', '.join(summary.get('normal_columns', [])) or 'None'}")
            print_info(f"Skewed columns: {', '.join(summary.get('skewed_columns', [])) or 'None'}")
            print_info(f"Heavy-tailed columns: {', '.join(summary.get('heavy_tailed_columns', [])) or 'None'}")

    print_success("Distribution analysis complete")
