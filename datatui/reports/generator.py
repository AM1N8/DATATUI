from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import json

from jinja2 import Environment, FileSystemLoader
import plotly.graph_objects as go
import plotly.utils

from datatui.core.analyzer import AnalysisResult
from datatui.core.loader import DatasetInfo

__all__ = ["generate_html_report"]

TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_html_report(
    result: AnalysisResult,
    quality: Dict[str, Any],
    dataset_info: Optional[DatasetInfo] = None,
) -> str:
    # Ensure template directory exists
    if not TEMPLATE_DIR.exists():
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        # Create default template if missing
        if not (TEMPLATE_DIR / "report.html").exists():
            _create_default_template()

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report.html")

    # Generate charts
    charts = {}
    charts["missing"] = _generate_missing_chart(result.missing)
    charts["correlations"] = _generate_correlation_heatmap(result.correlations)
    charts["types"] = _generate_type_chart(result.schema)

    schema_rows = _build_schema_rows(result.schema)
    missing_rows = _build_missing_rows(result.missing)
    outlier_rows = _build_outlier_rows(result.outliers)
    correlation_rows = _build_correlation_rows(result.correlations)
    distribution_rows = _build_distribution_rows(result.distributions)

    memory_mb = round(result.memory_mb, 2)
    missing_pct = round(result.missing.get("overall_missing_percentage", 0), 2)

    context = {
        "dataset_name": result.dataset_name,
        "total_rows": f"{result.total_rows:,}",
        "total_columns": result.total_columns,
        "memory_mb": memory_mb,
        "quality_score": round(quality.get("overall_score", 0), 1),
        "quality_rating": quality.get("quality_rating", "unknown"),
        "missing_pct": missing_pct,
        "schema_rows": schema_rows,
        "missing_rows": missing_rows,
        "outlier_rows": outlier_rows,
        "correlation_rows": correlation_rows,
        "distribution_rows": distribution_rows,
        "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "charts": charts,
        "dataset_info": dataset_info,
    }

    return template.render(**context)


def _generate_missing_chart(missing: Dict[str, Any]) -> str:
    columns = missing.get("columns", {})
    sorted_cols = sorted(
        columns.items(),
        key=lambda x: x[1].missing_percentage,
        reverse=True,
    )
    # Top 20 columns with missing values
    top_cols = [c for c in sorted_cols if c[1].missing_count > 0][:20]
    
    if not top_cols:
        return ""

    x = [c[0] for c in top_cols]
    y = [c[1].missing_percentage for c in top_cols]

    fig = go.Figure(data=[
        go.Bar(name='Missing %', x=x, y=y, marker_color='rgb(255, 87, 87)')
    ])
    fig.update_layout(
        title="Missing Values by Column (Top 20)",
        yaxis_title="Percent Missing (%)",
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
    )
    return json.dumps(fig.to_dict(), cls=plotly.utils.PlotlyJSONEncoder)


def _generate_correlation_heatmap(correlations: Dict[str, Any]) -> str:
    matrix_data = correlations.get("matrix", [])
    columns = correlations.get("columns", [])
    
    if not matrix_data or not columns:
        return ""

    fig = go.Figure(data=go.Heatmap(
        z=matrix_data,
        x=columns,
        y=columns,
        colorscale='RdBu',
        zmin=-1,
        zmax=1,
    ))
    fig.update_layout(
        title="Correlation Matrix",
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=500,
    )
    return json.dumps(fig.to_dict(), cls=plotly.utils.PlotlyJSONEncoder)


def _generate_type_chart(schema: Dict[str, Any]) -> str:
    type_dist = schema.get("type_distribution", {})
    if not type_dist:
        return ""
        
    labels = list(type_dist.keys())
    values = list(type_dist.values())
    
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    fig.update_layout(
        title="Column Types",
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
    )
    return json.dumps(fig.to_dict(), cls=plotly.utils.PlotlyJSONEncoder)


def _build_schema_rows(schema: Dict[str, Any]):
    rows = []
    columns = schema.get("columns", {})
    for col_name, col_schema in columns.items():
        rows.append({
            "name": col_schema.column_name if hasattr(col_schema, "column_name") else col_name,
            "dtype": col_schema.dtype if hasattr(col_schema, "dtype") else str(col_schema.get("dtype", "")),
            "data_type": col_schema.data_type.value if hasattr(col_schema, "data_type") else str(col_schema.get("data_type", "")),
            "semantic_type": col_schema.semantic_type.value if hasattr(col_schema, "semantic_type") else str(col_schema.get("semantic_type", "")),
            "unique_count": f"{col_schema.unique_count:,}" if hasattr(col_schema, "unique_count") else str(col_schema.get("unique_count", 0)),
            "null_count": f"{col_schema.null_count:,}" if hasattr(col_schema, "null_count") else str(col_schema.get("null_count", 0)),
            "null_pct": round(col_schema.null_percentage, 2) if hasattr(col_schema, "null_percentage") else round(col_schema.get("null_percentage", 0), 2),
            "memory": f"{col_schema.memory_mb:.2f} MB" if hasattr(col_schema, "memory_mb") else "",
        })
    return rows


def _build_missing_rows(missing: Dict[str, Any]):
    rows = []
    columns = missing.get("columns", {})
    for col_name, col_info in columns.items():
        rows.append({
            "name": col_name,
            "missing": f"{col_info.missing_count:,}" if hasattr(col_info, "missing_count") else str(col_info.get("missing_count", 0)),
            "present": f"{col_info.present_count:,}" if hasattr(col_info, "present_count") else str(col_info.get("present_count", 0)),
            "pct": round(col_info.missing_percentage, 2) if hasattr(col_info, "missing_percentage") else round(col_info.get("missing_percentage", 0), 2),
        })
    return sorted(rows, key=lambda x: x["pct"], reverse=True)


def _build_outlier_rows(outliers: Dict[str, Any]):
    rows = []
    summary = outliers.get("summary", {})
    by_column = summary.get("outliers_by_column", {})
    for col_name, info in by_column.items():
        rows.append({
            "name": col_name,
            "iqr": f"{info.iqr_outlier_count:,}" if hasattr(info, "iqr_outlier_count") else str(info.get("iqr_outlier_count", 0)),
            "zscore": f"{info.zscore_outlier_count:,}" if hasattr(info, "zscore_outlier_count") else str(info.get("zscore_outlier_count", 0)),
            "mad": f"{info.mad_outlier_count:,}" if hasattr(info, "mad_outlier_count") else str(info.get("mad_outlier_count", 0)),
            "pct": round(info.outlier_percentage, 2) if hasattr(info, "outlier_percentage") else round(info.get("outlier_percentage", 0), 2),
        })
    return rows


def _build_correlation_rows(correlations: Dict[str, Any]):
    rows = []
    top = correlations.get("top_correlations", [])
    for pair in top[:20]:
        corr_val = pair.get("correlation", 0)
        rows.append({
            "col1": pair.get("column1", ""),
            "col2": pair.get("column2", ""),
            "corr": round(corr_val, 4),
            "abs_corr": round(abs(corr_val), 4),
            "method": pair.get("method", ""),
        })
    return rows


def _build_distribution_rows(distributions: Dict[str, Any]):
    rows = []
    dist_data = distributions.get("distributions", {})
    for col_name, info in dist_data.items():
        rows.append({
            "name": col_name,
            "dist_type": info.get("distribution_type", "unknown"),
            "is_normal": "Yes" if info.get("is_normal", False) else "No",
            "skewness": round(info.get("skewness", 0), 4),
            "kurtosis": round(info.get("kurtosis", 0), 4),
        })
    return rows

def _create_default_template():
    # Simplest fallback
    path = TEMPLATE_DIR / "report.html"
    path.write_text("<html><body><h1>Data Report</h1><p>Please reinstall datatui properly.</p></body></html>")

