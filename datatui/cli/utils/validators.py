from pathlib import Path
from typing import Optional

import typer

from datatui.core.loader import DataLoader

__all__ = [
    "validate_file_path",
    "validate_column_name",
    "validate_threshold",
    "load_dataframe",
]

SUPPORTED_EXTENSIONS = {
    ".csv", ".tsv", ".txt", ".json", ".jsonl", ".ndjson",
    ".parquet", ".pq", ".xlsx", ".xls", ".arrow", ".feather",
}


def validate_file_path(file_path: Path) -> Path:
    if not file_path.exists():
        raise typer.BadParameter(f"File not found: {file_path}")
    if not file_path.is_file():
        raise typer.BadParameter(f"Not a file: {file_path}")
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise typer.BadParameter(
            f"Unsupported format: {file_path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return file_path


def validate_column_name(df, column: str) -> bool:
    if column not in df.columns:
        raise typer.BadParameter(
            f"Column '{column}' not found. "
            f"Available: {', '.join(df.columns)}"
        )
    return True


def validate_threshold(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    if value < min_val or value > max_val:
        raise typer.BadParameter(
            f"Threshold must be between {min_val} and {max_val}"
        )
    return value


def load_dataframe(file_path: Path):
    import polars as pl

    loader = DataLoader(lazy=False)
    df = loader.load(file_path)
    if isinstance(df, pl.LazyFrame):
        df = df.collect()
    return df, loader.info
