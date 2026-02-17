import json
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
    build_schema_table,
    build_numeric_stats_table,
    build_categorical_stats_table,
    build_missing_table,
    build_outliers_table,
    build_top_correlations_table,
    build_distributions_table,
    build_quality_table,
)
from datatui.cli.utils.validators import validate_file_path, load_dataframe
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_analyze"]


def run_analyze(
    file: Path,
    output: Optional[Path] = None,
    skip_multivariate: bool = False,
    columns: Optional[str] = None,
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

    if columns:
        selected = [c.strip() for c in columns.split(",")]
        valid_cols = [c for c in selected if c in df.columns]
        if valid_cols:
            df = df.select(valid_cols)

    from datatui.core.analyzer import DataAnalyzer

    analyzer = DataAnalyzer(df, dataset_name=file.stem)

    with create_spinner("Running full analysis"):
        result = analyzer.analyze_all(skip_multivariate_outliers=skip_multivariate)

    result_dict = asdict(result)

    if output:
        with open(output, "w") as f:
            json.dump(result_dict, f, indent=2, default=str)
        print_success(f"Results saved to {output}")
        if quiet:
            raise typer.Exit(0)

    if json_output:
        print_json_output(result_dict)
        raise typer.Exit(0)

    if quiet:
        console.print(
            f"Analysis complete: {result.total_rows:,} rows x {result.total_columns} cols"
        )
        raise typer.Exit(0)

    quality = analyzer.get_data_quality_score()
    console.print(build_quality_table(quality))

    print_section("Schema")
    schema = analyzer.analyze_schema()
    console.print(build_schema_table(schema))

    print_section("Statistics")
    statistics = analyzer.analyze_statistics()
    console.print(build_numeric_stats_table(statistics))
    console.print(build_categorical_stats_table(statistics))

    print_section("Missing Values")
    missing = analyzer.analyze_missing()
    console.print(build_missing_table(missing))

    print_section("Outliers")
    outlier_data = analyzer.analyze_outliers(skip_multivariate=skip_multivariate)
    summary = outlier_data.get("summary", {})
    outliers_by_col = summary.get("outliers_by_column", {})
    console.print(build_outliers_table(outliers_by_col))

    print_section("Top Correlations")
    corr_data = analyzer.analyze_correlations()
    top_corrs = corr_data.get("top_correlations", [])
    console.print(build_top_correlations_table(top_corrs))

    print_section("Distributions")
    dist_data = analyzer.analyze_distributions()
    console.print(build_distributions_table(dist_data))

    print_success(f"Full analysis complete in {result.analysis_time_seconds:.3f}s")
