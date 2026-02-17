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
    format_number,
    format_percentage,
    get_outlier_style,
)
from datatui.cli.output.tables import build_outliers_table
from datatui.cli.utils.validators import validate_file_path, load_dataframe, validate_column_name
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_outliers"]

VALID_METHODS = ("iqr", "zscore", "mad", "all")


def run_outliers(
    file: Path,
    method: str = "all",
    column: Optional[str] = None,
    json_output: bool = False,
    quiet: bool = False,
) -> None:
    if method not in VALID_METHODS:
        print_error_panel("Error", f"Invalid method: {method}. Choose from: {', '.join(VALID_METHODS)}")
        raise typer.Exit(1)

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

    if column:
        try:
            validate_column_name(df, column)
        except typer.BadParameter as e:
            print_error_panel("Column Error", str(e))
            raise typer.Exit(1)

    from datatui.core.outliers import OutlierDetector

    detector = OutlierDetector(df)

    with create_spinner("Detecting outliers"):
        outliers = detector.detect_all()

    if column:
        if column not in outliers:
            print_error_panel("Error", f"Column '{column}' is not numeric or has no outlier data")
            raise typer.Exit(1)

        info = outliers[column]
        info_dict = asdict(info)

        if json_output:
            print_json_output({column: info_dict})
            raise typer.Exit(0)

        if quiet:
            console.print(f"{column}: outliers={format_percentage(info.outlier_percentage)}")
            raise typer.Exit(0)

        print_section(f"Outlier Detail: {column}")

        from rich.table import Table
        from rich import box as rich_box

        detail = Table(box=rich_box.ROUNDED, border_style="cyan", show_lines=True)
        detail.add_column("Method", style="bold cyan", min_width=15)
        detail.add_column("Count", justify="right", min_width=10)
        detail.add_column("Details", style="white", min_width=30)

        detail.add_row(
            "IQR",
            f"{info.iqr_outlier_count:,}",
            f"Bounds: [{format_number(info.iqr_lower_bound)}, {format_number(info.iqr_upper_bound)}]",
        )
        detail.add_row(
            "Z-Score",
            f"{info.zscore_outlier_count:,}",
            f"Threshold: {info.zscore_threshold}",
        )
        detail.add_row(
            "MAD",
            f"{info.mad_outlier_count:,}",
            f"Threshold: {info.mad_threshold}",
        )
        pct_style = get_outlier_style(info.outlier_percentage)
        detail.add_row(
            "Combined",
            f"[{pct_style}]{format_percentage(info.outlier_percentage)}[/]",
            f"Total unique outlier indices (union of all methods)",
        )
        console.print(detail)

        if info.outlier_values:
            print_info(f"Sample outlier values: {', '.join(format_number(v) for v in info.outlier_values[:10])}")
    else:
        if json_output:
            out = {col: asdict(info) for col, info in outliers.items()}
            print_json_output(out)
            raise typer.Exit(0)

        if quiet:
            for col, info in outliers.items():
                console.print(f"{col}: {format_percentage(info.outlier_percentage)} outliers")
            raise typer.Exit(0)

        console.print(build_outliers_table(outliers))

    print_success("Outlier detection complete")
