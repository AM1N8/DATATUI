from typing import Any, Dict, List, Optional

from rich.table import Table
from rich import box

from datatui.cli.output.themes import (
    PRIMARY,
    SUCCESS,
    WARNING,
    ERROR,
    DIM,
    HEADER,
)
from datatui.cli.output.console import (
    format_number,
    format_percentage,
    format_memory,
    get_quality_style,
    get_missing_style,
    get_outlier_style,
    get_correlation_style,
)

__all__ = [
    "build_inspect_table",
    "build_schema_table",
    "build_numeric_stats_table",
    "build_categorical_stats_table",
    "build_datetime_stats_table",
    "build_text_stats_table",
    "build_missing_table",
    "build_missing_patterns_table",
    "build_outliers_table",
    "build_correlation_matrix_table",
    "build_top_correlations_table",
    "build_distributions_table",
    "build_quality_table",
    "build_type_distribution_table",
]


def build_inspect_table(info: Dict[str, Any]) -> Table:
    table = Table(
        title="Dataset Overview",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Property", style=PRIMARY, min_width=20)
    table.add_column("Value", style="white", min_width=30)

    table.add_row("Rows", f"{info.get('rows', 0):,}")
    table.add_row("Columns", f"{info.get('columns', 0):,}")
    table.add_row("Memory", format_memory(info.get("memory_mb", 0)))
    table.add_row("Format", info.get("format", "unknown").upper())
    if info.get("file_path"):
        table.add_row("File", str(info["file_path"]))
    if info.get("load_time"):
        table.add_row("Load Time", f"{info['load_time']:.3f}s")
    return table


def build_schema_table(schema: Dict[str, Any]) -> Table:
    table = Table(
        title="Schema",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=20)
    table.add_column("DType", style=DIM, min_width=12)
    table.add_column("Type", style="white", min_width=12)
    table.add_column("Semantic", style="white", min_width=12)
    table.add_column("Unique", justify="right", min_width=8)
    table.add_column("Cardinality", style=DIM, min_width=10)
    table.add_column("Nulls", justify="right", min_width=10)
    table.add_column("Null %", justify="right", min_width=8)
    table.add_column("Memory", justify="right", min_width=8)

    columns = schema.get("columns", {})
    for col_name, col_schema in columns.items():
        null_pct = col_schema.null_percentage
        null_style = get_missing_style(null_pct)
        table.add_row(
            col_schema.column_name,
            col_schema.dtype,
            col_schema.data_type.value,
            col_schema.semantic_type.value,
            f"{col_schema.unique_count:,}",
            col_schema.cardinality.value,
            f"{col_schema.null_count:,}",
            f"[{null_style}]{format_percentage(null_pct)}[/]",
            format_memory(col_schema.memory_mb),
        )
    return table


def build_numeric_stats_table(statistics: Dict[str, Any]) -> Table:
    table = Table(
        title="Numeric Statistics",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=16)
    table.add_column("Count", justify="right")
    table.add_column("Mean", justify="right")
    table.add_column("Std", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Q25", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("Q75", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Skew", justify="right")
    table.add_column("Kurt", justify="right")

    stats_data = statistics.get("statistics", {})
    from datatui.core.statistics import NumericStats

    for col_name, col_stats in stats_data.items():
        if not isinstance(col_stats, NumericStats):
            continue
        table.add_row(
            col_name,
            f"{col_stats.count:,}",
            format_number(col_stats.mean),
            format_number(col_stats.std),
            format_number(col_stats.min),
            format_number(col_stats.q25),
            format_number(col_stats.median),
            format_number(col_stats.q75),
            format_number(col_stats.max),
            format_number(col_stats.skewness, 3),
            format_number(col_stats.kurtosis, 3),
        )
    return table


def build_categorical_stats_table(statistics: Dict[str, Any]) -> Table:
    table = Table(
        title="Categorical Statistics",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=16)
    table.add_column("Count", justify="right")
    table.add_column("Unique", justify="right")
    table.add_column("Mode", style="white")
    table.add_column("Mode Freq", justify="right")
    table.add_column("Mode %", justify="right")
    table.add_column("Entropy", justify="right")

    stats_data = statistics.get("statistics", {})
    from datatui.core.statistics import CategoricalStats

    for col_name, col_stats in stats_data.items():
        if not isinstance(col_stats, CategoricalStats):
            continue
        table.add_row(
            col_name,
            f"{col_stats.count:,}",
            f"{col_stats.unique_count:,}",
            str(col_stats.mode) if col_stats.mode else "-",
            f"{col_stats.mode_frequency:,}",
            format_percentage(col_stats.mode_percentage),
            format_number(col_stats.entropy, 3),
        )
    return table


def build_datetime_stats_table(statistics: Dict[str, Any]) -> Table:
    table = Table(
        title="Datetime Statistics",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=16)
    table.add_column("Count", justify="right")
    table.add_column("Min", style="white")
    table.add_column("Max", style="white")
    table.add_column("Range (days)", justify="right")
    table.add_column("Unique", justify="right")

    stats_data = statistics.get("statistics", {})
    from datatui.core.statistics import DatetimeStats

    for col_name, col_stats in stats_data.items():
        if not isinstance(col_stats, DatetimeStats):
            continue
        range_days = (
            f"{col_stats.range_days:.1f}" if col_stats.range_days is not None else "-"
        )
        table.add_row(
            col_name,
            f"{col_stats.count:,}",
            str(col_stats.min) if col_stats.min else "-",
            str(col_stats.max) if col_stats.max else "-",
            range_days,
            f"{col_stats.unique_count:,}",
        )
    return table


def build_text_stats_table(statistics: Dict[str, Any]) -> Table:
    table = Table(
        title="Text Statistics",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=16)
    table.add_column("Count", justify="right")
    table.add_column("Unique", justify="right")
    table.add_column("Mode", style="white")
    table.add_column("Avg Len", justify="right")
    table.add_column("Min Len", justify="right")
    table.add_column("Max Len", justify="right")
    table.add_column("Empty", justify="right")

    stats_data = statistics.get("statistics", {})
    from datatui.core.statistics import TextStats

    for col_name, col_stats in stats_data.items():
        if not isinstance(col_stats, TextStats):
            continue
        mode_val = str(col_stats.mode)[:30] if col_stats.mode else "-"
        table.add_row(
            col_name,
            f"{col_stats.count:,}",
            f"{col_stats.unique_count:,}",
            mode_val,
            format_number(col_stats.avg_length, 1),
            f"{col_stats.min_length}",
            f"{col_stats.max_length}",
            f"{col_stats.empty_count:,}",
        )
    return table


def build_missing_table(missing: Dict[str, Any]) -> Table:
    table = Table(
        title="Missing Values",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=20)
    table.add_column("Missing", justify="right")
    table.add_column("Present", justify="right")
    table.add_column("Missing %", justify="right")
    table.add_column("Bar", min_width=20)

    columns = missing.get("columns", {})
    sorted_cols = sorted(
        columns.items(),
        key=lambda x: x[1].missing_percentage,
        reverse=True,
    )

    for col_name, col_info in sorted_cols:
        pct = col_info.missing_percentage
        style = get_missing_style(pct)
        bar_len = int(pct / 5)
        bar = "[red]" + ">" * bar_len + "[/]" + " " * (20 - bar_len)
        table.add_row(
            col_name,
            f"{col_info.missing_count:,}",
            f"{col_info.present_count:,}",
            f"[{style}]{format_percentage(pct)}[/]",
            bar,
        )
    return table


def build_missing_patterns_table(patterns: List[Any]) -> Table:
    table = Table(
        title="Missing Patterns",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("#", style=DIM, justify="right")
    table.add_column("Columns", style=PRIMARY, min_width=30)
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    for i, pattern in enumerate(patterns[:15], 1):
        cols_str = ", ".join(pattern.columns[:5])
        if len(pattern.columns) > 5:
            cols_str += f" (+{len(pattern.columns) - 5} more)"
        table.add_row(
            str(i),
            cols_str,
            f"{pattern.count:,}",
            format_percentage(pattern.percentage),
        )
    return table


def build_outliers_table(outliers: Dict[str, Any]) -> Table:
    table = Table(
        title="Outlier Detection",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=16)
    table.add_column("Total", justify="right")
    table.add_column("IQR", justify="right")
    table.add_column("Z-Score", justify="right")
    table.add_column("MAD", justify="right")
    table.add_column("Outlier %", justify="right")
    table.add_column("IQR Lower", justify="right")
    table.add_column("IQR Upper", justify="right")

    for col_name, info in outliers.items():
        pct = info.outlier_percentage
        style = get_outlier_style(pct)
        table.add_row(
            col_name,
            f"{info.total_count:,}",
            f"{info.iqr_outlier_count:,}",
            f"{info.zscore_outlier_count:,}",
            f"{info.mad_outlier_count:,}",
            f"[{style}]{format_percentage(pct)}[/]",
            format_number(info.iqr_lower_bound),
            format_number(info.iqr_upper_bound),
        )
    return table


def build_correlation_matrix_table(
    matrix_data: Dict[str, Any],
) -> Table:
    columns = matrix_data.get("columns", [])
    matrix = matrix_data.get("matrix", [])

    table = Table(
        title="Correlation Matrix",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("", style=PRIMARY, min_width=12)
    for col in columns:
        table.add_column(col[:10], justify="center", min_width=8)

    for i, row_col in enumerate(columns):
        cells = [row_col[:12]]
        for j in range(len(columns)):
            if i < len(matrix) and j < len(matrix[i]):
                val = matrix[i][j]
                style = get_correlation_style(val)
                cells.append(f"[{style}]{val:.2f}[/]")
            else:
                cells.append("-")
        table.add_row(*cells)
    return table


def build_top_correlations_table(
    correlations: List[Dict[str, Any]],
) -> Table:
    table = Table(
        title="Top Correlations",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("#", style=DIM, justify="right")
    table.add_column("Column 1", style=PRIMARY)
    table.add_column("Column 2", style=PRIMARY)
    table.add_column("Correlation", justify="right")
    table.add_column("Method", style=DIM)
    table.add_column("Strength", min_width=15)

    for i, pair in enumerate(correlations, 1):
        val = pair.get("correlation", 0)
        style = get_correlation_style(val)
        abs_val = abs(val)
        bar_len = int(abs_val * 15)
        bar_char = ">" if val >= 0 else "<"
        bar = f"[{style}]" + bar_char * bar_len + "[/]"
        table.add_row(
            str(i),
            pair.get("column1", ""),
            pair.get("column2", ""),
            f"[{style}]{val:.4f}[/]",
            pair.get("method", ""),
            bar,
        )
    return table


def build_distributions_table(distributions: Dict[str, Any]) -> Table:
    table = Table(
        title="Distributions",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Column", style=PRIMARY, min_width=16)
    table.add_column("Type", style="white")
    table.add_column("Normal?", justify="center")
    table.add_column("Skewness", justify="right")
    table.add_column("Kurtosis", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Q25", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("Q75", justify="right")
    table.add_column("Max", justify="right")

    dist_data = distributions.get("distributions", {})
    for col_name, info in dist_data.items():
        is_normal = info.get("is_normal", False)
        normal_str = f"[{SUCCESS}]Yes[/]" if is_normal else f"[{DIM}]No[/]"
        quartiles = info.get("quartiles", {})
        table.add_row(
            col_name,
            info.get("distribution_type", "unknown"),
            normal_str,
            format_number(info.get("skewness", 0), 3),
            format_number(info.get("kurtosis", 0), 3),
            format_number(quartiles.get("min", 0)),
            format_number(quartiles.get("q25", 0)),
            format_number(quartiles.get("median", 0)),
            format_number(quartiles.get("q75", 0)),
            format_number(quartiles.get("max", 0)),
        )
    return table


def build_quality_table(quality: Dict[str, Any]) -> Table:
    table = Table(
        title="Data Quality Score",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Metric", style=PRIMARY, min_width=25)
    table.add_column("Score", justify="right", min_width=10)
    table.add_column("Rating", min_width=12)

    overall = quality.get("overall_score", 0)
    overall_style = get_quality_style(overall)
    rating = quality.get("quality_rating", "unknown").upper()
    table.add_row(
        "Overall Quality",
        f"[{overall_style}]{overall:.1f}/100[/]",
        f"[{overall_style}]{rating}[/]",
    )

    completeness = quality.get("completeness_score", 0)
    comp_style = get_quality_style(completeness)
    table.add_row(
        "Completeness",
        f"[{comp_style}]{completeness:.1f}/100[/]",
        "",
    )

    outlier_score = quality.get("outlier_score", 0)
    out_style = get_quality_style(outlier_score)
    table.add_row(
        "Outlier Score",
        f"[{out_style}]{outlier_score:.1f}/100[/]",
        "",
    )

    schema_score = quality.get("schema_score", 0)
    sch_style = get_quality_style(schema_score)
    table.add_row(
        "Schema Score",
        f"[{sch_style}]{schema_score:.1f}/100[/]",
        "",
    )
    return table


def build_type_distribution_table(type_dist: Dict[str, int]) -> Table:
    table = Table(
        title="Column Type Distribution",
        box=box.ROUNDED,
        title_style=HEADER,
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Type", style=PRIMARY, min_width=15)
    table.add_column("Count", justify="right", min_width=8)
    table.add_column("Bar", min_width=25)

    total = sum(type_dist.values()) if type_dist else 1
    for dtype, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
        bar_len = int((count / total) * 25)
        bar = "[cyan]" + ">" * bar_len + "[/]"
        table.add_row(dtype, str(count), bar)
    return table
