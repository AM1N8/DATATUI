from pathlib import Path
from typing import Optional
from dataclasses import asdict

import typer

from datatui.cli.output.console import (
    console,
    print_banner,
    print_section,
    print_success,
    print_json_output,
    print_error_panel,
)
from datatui.cli.output.tables import (
    build_numeric_stats_table,
    build_categorical_stats_table,
    build_datetime_stats_table,
    build_text_stats_table,
)
from datatui.cli.utils.validators import validate_file_path, load_dataframe, validate_column_name
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_stats"]


def run_stats(
    file: Path,
    column: Optional[str] = None,
    numeric_only: bool = False,
    categorical_only: bool = False,
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

    with create_spinner("Computing statistics"):
        statistics = analyzer.analyze_statistics()

    if column:
        try:
            validate_column_name(df, column)
        except typer.BadParameter as e:
            print_error_panel("Column Error", str(e))
            raise typer.Exit(1)

        col_stats = statistics.get("statistics", {}).get(column)
        if col_stats is None:
            print_error_panel("Error", f"No statistics for column '{column}'")
            raise typer.Exit(1)

        col_dict = asdict(col_stats)

        if json_output:
            print_json_output({column: col_dict})
            raise typer.Exit(0)

        print_section(f"Statistics: {column}")

        from rich.table import Table
        from rich import box as rich_box

        detail = Table(box=rich_box.ROUNDED, border_style="cyan", show_lines=True)
        detail.add_column("Metric", style="bold cyan", min_width=20)
        detail.add_column("Value", style="white", min_width=20)

        for key, value in col_dict.items():
            if isinstance(value, list):
                display = ", ".join(str(v) for v in value[:5])
            elif isinstance(value, float):
                from datatui.cli.output.console import format_number
                display = format_number(value)
            else:
                display = str(value)
            detail.add_row(key.replace("_", " ").title(), display)
        console.print(detail)
    else:
        if json_output:
            all_stats = {}
            for col_name, col_stats in statistics.get("statistics", {}).items():
                all_stats[col_name] = asdict(col_stats)
            print_json_output(all_stats)
            raise typer.Exit(0)

        if quiet:
            for col_name in statistics.get("numeric_columns", []):
                col_stats = statistics["statistics"].get(col_name)
                if col_stats:
                    from datatui.cli.output.console import format_number
                    console.print(f"{col_name}: mean={format_number(col_stats.mean)} std={format_number(col_stats.std)}")
            raise typer.Exit(0)

        if not categorical_only:
            print_section("Numeric Statistics")
            console.print(build_numeric_stats_table(statistics))

        if not numeric_only:
            print_section("Categorical Statistics")
            console.print(build_categorical_stats_table(statistics))

            print_section("Datetime Statistics")
            console.print(build_datetime_stats_table(statistics))

            print_section("Text Statistics")
            console.print(build_text_stats_table(statistics))

    print_success("Statistics analysis complete")
