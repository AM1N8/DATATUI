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
    format_percentage,
    format_memory,
)
from datatui.cli.output.tables import build_schema_table
from datatui.cli.utils.validators import validate_file_path, load_dataframe, validate_column_name
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_schema"]


def run_schema(
    file: Path,
    column: Optional[str] = None,
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

    with create_spinner("Detecting schema"):
        schema = analyzer.analyze_schema()

    if column:
        try:
            validate_column_name(df, column)
        except typer.BadParameter as e:
            print_error_panel("Column Error", str(e))
            raise typer.Exit(1)

        col_schema = schema.get("columns", {}).get(column)
        if col_schema is None:
            print_error_panel("Error", f"Column '{column}' not found in schema")
            raise typer.Exit(1)

        col_dict = asdict(col_schema)

        if json_output:
            print_json_output(col_dict)
            raise typer.Exit(0)

        if quiet:
            console.print(
                f"{column}: {col_schema.data_type.value} | "
                f"{col_schema.semantic_type.value} | "
                f"nulls={format_percentage(col_schema.null_percentage)}"
            )
            raise typer.Exit(0)

        print_section(f"Column Detail: {column}")

        from rich.table import Table
        from rich import box as rich_box

        detail = Table(box=rich_box.ROUNDED, border_style="cyan", show_lines=True)
        detail.add_column("Property", style="bold cyan", min_width=20)
        detail.add_column("Value", style="white", min_width=30)

        detail.add_row("Name", col_schema.column_name)
        detail.add_row("Polars DType", col_schema.dtype)
        detail.add_row("Data Type", col_schema.data_type.value)
        detail.add_row("Semantic Type", col_schema.semantic_type.value)
        detail.add_row("Unique Values", f"{col_schema.unique_count:,}")
        detail.add_row("Cardinality", col_schema.cardinality.value)
        detail.add_row("Null Count", f"{col_schema.null_count:,}")
        detail.add_row("Null Percentage", format_percentage(col_schema.null_percentage))
        detail.add_row("Memory", format_memory(col_schema.memory_mb))
        detail.add_row(
            "Sample Values",
            ", ".join(str(v) for v in col_schema.sample_values[:5]),
        )
        console.print(detail)
    else:
        if json_output:
            schema_dict = {}
            for col_name, col_s in schema.get("columns", {}).items():
                schema_dict[col_name] = asdict(col_s)
            print_json_output(schema_dict)
            raise typer.Exit(0)

        if quiet:
            for col_name, col_s in schema.get("columns", {}).items():
                console.print(
                    f"{col_name}: {col_s.data_type.value} "
                    f"({col_s.dtype}) nulls={format_percentage(col_s.null_percentage)}"
                )
            raise typer.Exit(0)

        console.print(build_schema_table(schema))

    print_success("Schema analysis complete")
