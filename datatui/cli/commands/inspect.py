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
    format_memory,
    format_percentage,
)
from datatui.cli.output.tables import (
    build_inspect_table,
    build_quality_table,
    build_type_distribution_table,
)
from datatui.cli.utils.validators import validate_file_path, load_dataframe
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_inspect"]


def run_inspect(
    file: Path,
    no_quality: bool = False,
    sample: int = 5,
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

    info = {
        "rows": dataset_info.rows,
        "columns": dataset_info.columns,
        "memory_mb": dataset_info.file_size_mb,
        "format": dataset_info.format,
        "file_path": str(dataset_info.file_path),
        "load_time": dataset_info.load_time_seconds,
        "column_names": dataset_info.column_names,
    }

    quality = None
    if not no_quality:
        with create_spinner("Computing quality score"):
            quality = analyzer.get_data_quality_score()

    schema = analyzer.analyze_schema()

    if json_output:
        output = {"dataset": info, "quality": quality, "schema_summary": schema.get("type_distribution", {})}
        print_json_output(output)
        raise typer.Exit(0)

    if quiet:
        console.print(f"{info['rows']:,} rows x {info['columns']} cols | {format_memory(info['memory_mb'])}")
        raise typer.Exit(0)

    console.print(build_inspect_table(info))

    type_dist = schema.get("type_distribution", {})
    if type_dist:
        console.print(build_type_distribution_table(type_dist))

    if quality:
        console.print(build_quality_table(quality))

    if sample > 0:
        print_section("Data Sample")
        from rich.table import Table
        from rich import box as rich_box

        sample_df = df.head(sample)
        sample_table = Table(
            title=f"First {sample} Rows",
            box=rich_box.SIMPLE,
            border_style="cyan",
            show_lines=False,
        )
        for col in sample_df.columns:
            sample_table.add_column(col[:20], style="white", max_width=25)
        for row in sample_df.iter_rows():
            sample_table.add_row(*[str(v)[:25] for v in row])
        console.print(sample_table)

    if dataset_info.warnings:
        print_section("Warnings")
        for warning in dataset_info.warnings:
            from datatui.cli.output.console import print_warning
            print_warning(warning)

    print_success(f"Inspection complete in {dataset_info.load_time_seconds:.3f}s")
