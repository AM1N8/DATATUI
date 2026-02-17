<p align="center">
  <img src="assets/logo.png" alt="DataTUI Logo" width="500">
</p>

# DataTUI

DataTUI is a professional terminal-based toolkit designed for efficient exploratory data analysis (EDA). It provides a suite of tools to inspect, analyze, and visualize datasets directly from the command line or through an interactive text-based user interface (TUI).

## Current Status

This project is currently under active development. Features are being refined and expanded to improve data processing capabilities and visual representation.

## Core Capabilities

### Command Line Interface

The CLI provides granular commands for rapid data inspection:

- Schema and metadata extraction.
- Statistical summary generation for numeric and categorical data.
- Missing value analysis and pattern detection.
- Outlier identification across multiple statistical methods.
- Correlation analysis and distribution testing.

### Interactive TUI

An interactive terminal interface for navigating dataset characteristics:

- Real-time navigation of statistics and schema.
- Embedded visualizations including histograms and heatmaps.
- Dynamic filtering and detail panels.

### Reporting

Generate comprehensive HTML reports containing:

- Interactive Plotly visualizations.
- Detailed data quality assessments.
- Summarized analysis of distributions and correlations.

## Getting Started

DataTUI is built with Python and utilizes Polars for high-performance data processing.

### Installation

Ensure you have the latest version of `uv` or `pip` installed.

```bash
uv run datatui --help
```

### Usage

Analyze a dataset via the CLI:

```bash
datatui stats data/your_dataset.csv
```

Launch the interactive interface:

```bash
datatui tui data/your_dataset.csv
```

Generate a full analysis report:

```bash
datatui report data/your_dataset.csv --output report.html
```

## Future Roadmap

Development is focused on enhancing multivariate analysis support, increasing visualization fidelity in the TUI, and streamlining the integration of external data connectors.


