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
    build_correlation_matrix_table,
    build_top_correlations_table,
)
from datatui.cli.utils.validators import validate_file_path, load_dataframe
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_correlations"]

VALID_METHODS = ("pearson", "spearman", "all")


def run_correlations(
    file: Path,
    method: str = "pearson",
    min_corr: float = 0.3,
    top: int = 20,
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

    from datatui.core.correlations import CorrelationAnalyzer

    analyzer = CorrelationAnalyzer(df)

    with create_spinner("Computing correlations"):
        if method == "all":
            matrix_pearson = analyzer.get_correlation_matrix(method="pearson")
            matrix_spearman = analyzer.get_correlation_matrix(method="spearman")
        else:
            matrix = analyzer.get_correlation_matrix(method=method)

        top_corrs = analyzer.get_top_correlations(n=top, min_correlation=min_corr)

    top_corrs_dicts = [asdict(pair) for pair in top_corrs]

    if json_output:
        output = {"top_correlations": top_corrs_dicts}
        if method == "all":
            output["pearson_matrix"] = matrix_pearson
            output["spearman_matrix"] = matrix_spearman
        else:
            output["matrix"] = matrix
        print_json_output(output)
        raise typer.Exit(0)

    if quiet:
        for pair in top_corrs[:10]:
            console.print(f"{pair.column1} <-> {pair.column2}: {pair.correlation:.4f} ({pair.method})")
        raise typer.Exit(0)

    if method == "all":
        print_section("Pearson Correlation Matrix")
        console.print(build_correlation_matrix_table(matrix_pearson))
        print_section("Spearman Correlation Matrix")
        console.print(build_correlation_matrix_table(matrix_spearman))
    else:
        print_section(f"{method.title()} Correlation Matrix")
        console.print(build_correlation_matrix_table(matrix))

    if top_corrs_dicts:
        print_section(f"Top {len(top_corrs_dicts)} Correlations (|r| >= {min_corr})")
        console.print(build_top_correlations_table(top_corrs_dicts))

    print_success("Correlation analysis complete")
