import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

import typer

from datatui.cli.output.console import (
    console,
    print_banner,
    print_success,
    print_error_panel,
)
from datatui.cli.utils.validators import validate_file_path, load_dataframe
from datatui.cli.utils.progress import create_spinner

__all__ = ["run_report"]


def run_report(
    file: Path,
    output: Optional[Path] = None,
    open_report: bool = False,
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

    with create_spinner("Running full analysis"):
        result = analyzer.analyze_all(skip_multivariate_outliers=True)

    quality = analyzer.get_data_quality_score()

    if json_output:
        from datatui.cli.output.console import print_json_output
        print_json_output(asdict(result))
        raise typer.Exit(0)

    if output is None:
        output = Path(f"{file.stem}_report.html")

    from datatui.reports.generator import generate_html_report

    with create_spinner("Generating HTML report"):
        html_content = generate_html_report(result, quality, dataset_info)

    output.write_text(html_content, encoding="utf-8")

    if quiet:
        console.print(str(output))
    else:
        print_success(f"Report saved to {output}")

    if open_report:
        import webbrowser
        webbrowser.open(str(output.resolve()))
        print_success("Report opened in browser")
