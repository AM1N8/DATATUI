from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work

__all__ = ["CorrelationsScreen"]


class CorrelationsScreen(Screen):

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Correlations", classes="screen-title"),
            Static("", id="corr-summary"),
            Static("Correlation Matrix", classes="section-header"),
            DataTable(id="corr-matrix-table"),
            Static("Top Correlations", classes="section-header"),
            DataTable(id="corr-top-table"),
            id="correlations-content",
        )
        yield LoadingIndicator(id="correlations-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#correlations-loading", LoadingIndicator)
        content = self.query_one("#correlations-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
            return

        try:
            from datatui.core.correlations import CorrelationAnalyzer

            corr_analyzer = CorrelationAnalyzer(analyzer.df)
            matrix = corr_analyzer.get_correlation_matrix(method="pearson")
            top_corrs = corr_analyzer.get_top_correlations(n=20, min_correlation=0.3)

            self.app.call_from_thread(
                self._render_correlations, matrix, top_corrs
            )
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_correlations(self, matrix, top_corrs):
        loading = self.query_one("#correlations-loading", LoadingIndicator)
        content = self.query_one("#correlations-content")
        loading.display = False
        content.display = True

        columns = matrix.get("columns", [])
        matrix_data = matrix.get("matrix", [])

        summary = self.query_one("#corr-summary", Static)
        summary.update(
            f"  Numeric columns: {len(columns)}  |  "
            f"Strong correlations (|r| > 0.6): "
            f"{sum(1 for c in top_corrs if abs(c.correlation) > 0.6)}"
        )

        matrix_table = self.query_one("#corr-matrix-table", DataTable)
        matrix_table.clear(columns=True)

        if columns:
            matrix_table.add_column("", key="row_header")
            for col in columns:
                display_name = col[:12] if len(col) > 12 else col
                matrix_table.add_column(display_name, key=col)

            for i, row_col in enumerate(columns):
                cells = [row_col[:12]]
                for j in range(len(columns)):
                    if i < len(matrix_data) and j < len(matrix_data[i]):
                        val = matrix_data[i][j]
                        cells.append(f"{val:.2f}")
                    else:
                        cells.append("-")
                matrix_table.add_row(*cells)

        top_table = self.query_one("#corr-top-table", DataTable)
        top_table.clear(columns=True)
        top_table.add_column("#", key="rank")
        top_table.add_column("Column 1", key="col1")
        top_table.add_column("Column 2", key="col2")
        top_table.add_column("Correlation", key="corr")
        top_table.add_column("Method", key="method")
        top_table.add_column("Strength", key="strength")

        for i, pair in enumerate(top_corrs, 1):
            abs_val = abs(pair.correlation)
            bar_len = int(abs_val * 15)
            bar_char = "+" if pair.correlation >= 0 else "-"
            bar = bar_char * bar_len

            top_table.add_row(
                str(i),
                pair.column1,
                pair.column2,
                f"{pair.correlation:.4f}",
                pair.method,
                bar,
            )

    def _render_error(self, message):
        loading = self.query_one("#correlations-loading", LoadingIndicator)
        content = self.query_one("#correlations-content")
        loading.display = False
        content.display = True
        summary = self.query_one("#corr-summary", Static)
        summary.update(f"  Error: {message}")
