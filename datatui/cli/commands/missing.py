from pathlib import Path
from typing import Optional
from dataclasses import asdict

import typer

from datatui.cli.output.console import (
    console,
    print_banner,
    print_section,
    print_success,
    print_info,
    print_json_output,
    print_error_panel,
    format_percentage,
    get_missing_style,
)
from datatui.cli.output.tables import (
    build_missing_table,
    build_missing_patterns_table,
)
from datatui.cli.utils.validators import validate_file_path, load_dataframe
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_missing"]


def run_missing(
    file: Path,
    threshold: float = 0.0,
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

    with create_spinner("Analyzing missing values"):
        missing = analyzer.analyze_missing()

    if threshold > 0:
        filtered_cols = {}
        for col_name, col_info in missing.get("columns", {}).items():
            if col_info.missing_percentage >= threshold:
                filtered_cols[col_name] = col_info
        missing["columns"] = filtered_cols

    if json_output:
        serializable = {
            "overall_missing_percentage": missing.get("overall_missing_percentage", 0),
            "complete_rows": missing.get("complete_rows", 0),
            "complete_rows_percentage": missing.get("complete_rows_percentage", 0),
            "total_missing_values": missing.get("total_missing_values", 0),
            "total_cells": missing.get("total_cells", 0),
            "columns": {
                col: asdict(info) for col, info in missing.get("columns", {}).items()
            },
            "patterns": [asdict(p) for p in missing.get("patterns", [])],
        }
        print_json_output(serializable)
        raise typer.Exit(0)

    if quiet:
        overall = missing.get("overall_missing_percentage", 0)
        cols_missing = len(missing.get("columns_with_missing", []))
        console.print(f"Missing: {format_percentage(overall)} | Columns with missing: {cols_missing}")
        raise typer.Exit(0)

    print_section("Summary")
    overall_pct = missing.get("overall_missing_percentage", 0)
    overall_style = get_missing_style(overall_pct)
    console.print(f"  Overall Missing: [{overall_style}]{format_percentage(overall_pct)}[/]")
    console.print(f"  Complete Rows:   {missing.get('complete_rows', 0):,} ({format_percentage(missing.get('complete_rows_percentage', 0))})")
    console.print(f"  Incomplete Rows: {missing.get('incomplete_rows', 0):,}")
    console.print(f"  Total Cells:     {missing.get('total_cells', 0):,}")

    print_section("Per-Column Missing Values")
    console.print(build_missing_table(missing))

    patterns = missing.get("patterns", [])
    if patterns:
        print_section("Missing Patterns")
        console.print(build_missing_patterns_table(patterns))

    print_success("Missing value analysis complete")
