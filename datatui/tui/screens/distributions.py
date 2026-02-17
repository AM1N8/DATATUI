from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work

from datatui.tui.widgets.mini_chart import MiniChart

__all__ = ["DistributionsScreen"]


class DistributionsScreen(Screen):

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Distributions", classes="screen-title"),
            Static("", id="dist-summary"),
            DataTable(id="dist-table"),
            MiniChart(title="Histogram", id="dist-chart"),
            Static("", id="dist-normality"),
            id="distributions-content",
        )
        yield LoadingIndicator(id="distributions-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#distributions-loading", LoadingIndicator)
        content = self.query_one("#distributions-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
            return

        try:
            dist_data = analyzer.analyze_distributions()
            self.app.call_from_thread(self._render_distributions, dist_data)
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_distributions(self, dist_data):
        loading = self.query_one("#distributions-loading", LoadingIndicator)
        content = self.query_one("#distributions-content")
        loading.display = False
        content.display = True

        distributions = dist_data.get("distributions", {})
        summary_data = dist_data.get("summary", {})

        normal_cols = summary_data.get("normal_columns", [])
        skewed_cols = summary_data.get("skewed_columns", [])

        summary = self.query_one("#dist-summary", Static)
        summary.update(
            f"  Columns: {len(distributions)}  |  "
            f"Normal: {len(normal_cols)}  |  "
            f"Skewed: {len(skewed_cols)}"
        )

        table = self.query_one("#dist-table", DataTable)
        table.clear(columns=True)
        table.add_column("Column", key="column")
        table.add_column("Type", key="type")
        table.add_column("Normal?", key="normal")
        table.add_column("Skewness", key="skew")
        table.add_column("Kurtosis", key="kurt")
        table.add_column("Min", key="min")
        table.add_column("Median", key="median")
        table.add_column("Max", key="max")
        table.add_column("IQR", key="iqr")

        self._dist_data = distributions

        for col_name, info in distributions.items():
            is_normal = info.get("is_normal", False)
            quartiles = info.get("quartiles", {})
            table.add_row(
                col_name,
                info.get("distribution_type", "unknown"),
                "Yes" if is_normal else "No",
                f"{info.get('skewness', 0):.3f}",
                f"{info.get('kurtosis', 0):.3f}",
                f"{quartiles.get('min', 0):.4f}",
                f"{quartiles.get('median', 0):.4f}",
                f"{quartiles.get('max', 0):.4f}",
                f"{quartiles.get('iqr', 0):.4f}",
            )

        if distributions:
            first_col = next(iter(distributions))
            self._show_histogram(first_col)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_dist_data"):
            return

        col_names = list(self._dist_data.keys())
        row_index = event.cursor_row
        if 0 <= row_index < len(col_names):
            self._show_histogram(col_names[row_index])

    def _show_histogram(self, col_name):
        if col_name not in self._dist_data:
            return

        info = self._dist_data[col_name]
        histogram = info.get("histogram", {})
        counts = histogram.get("counts", [])

        chart = self.query_one("#dist-chart", MiniChart)
        if counts:
            chart.set_values(
                [float(c) for c in counts],
                title=f"Histogram: {col_name}",
            )
        else:
            chart.set_values([], title=f"No histogram data for {col_name}")

        normality = info.get("normality_tests", {})
        normality_widget = self.query_one("#dist-normality", Static)
        if normality:
            lines = [f"\n  Normality Tests for {col_name}:"]
            for test_name in ("shapiro_wilk", "anderson_darling", "dagostino_pearson", "kolmogorov_smirnov"):
                test = normality.get(test_name)
                if test and isinstance(test, dict):
                    stat = test.get("statistic", 0)
                    p_val = test.get("p_value", test.get("critical_value", 0))
                    is_n = test.get("is_normal", False)
                    result = "Normal" if is_n else "Non-normal"
                    lines.append(
                        f"    {test_name.replace('_', ' ').title()}: "
                        f"stat={stat:.6f}  p={p_val:.6f}  -> {result}"
                    )
            normality_widget.update("\n".join(lines))
        else:
            normality_widget.update("")

    def _render_error(self, message):
        loading = self.query_one("#distributions-loading", LoadingIndicator)
        content = self.query_one("#distributions-content")
        loading.display = False
        content.display = True
        summary = self.query_one("#dist-summary", Static)
        summary.update(f"  Error: {message}")
