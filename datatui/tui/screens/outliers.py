from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work

__all__ = ["OutliersScreen"]


class OutliersScreen(Screen):

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Outliers", classes="screen-title"),
            Static("", id="outliers-summary"),
            DataTable(id="outliers-table"),
            Static("", id="outliers-detail"),
            id="outliers-content",
        )
        yield LoadingIndicator(id="outliers-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#outliers-loading", LoadingIndicator)
        content = self.query_one("#outliers-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
            return

        try:
            from datatui.core.outliers import OutlierDetector

            detector = OutlierDetector(analyzer.df)
            outliers = detector.detect_all()
            self.app.call_from_thread(self._render_outliers, outliers)
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_outliers(self, outliers):
        loading = self.query_one("#outliers-loading", LoadingIndicator)
        content = self.query_one("#outliers-content")
        loading.display = False
        content.display = True

        total_cols = len(outliers)
        cols_with_outliers = sum(
            1 for info in outliers.values() if info.outlier_percentage > 0
        )
        summary = self.query_one("#outliers-summary", Static)
        summary.update(
            f"  Columns analyzed: {total_cols}  |  "
            f"Columns with outliers: {cols_with_outliers}"
        )

        table = self.query_one("#outliers-table", DataTable)
        table.clear(columns=True)
        table.add_column("Column", key="column")
        table.add_column("Total", key="total")
        table.add_column("IQR", key="iqr")
        table.add_column("Z-Score", key="zscore")
        table.add_column("MAD", key="mad")
        table.add_column("Outlier %", key="pct")
        table.add_column("IQR Lower", key="lower")
        table.add_column("IQR Upper", key="upper")

        self._outlier_data = outliers

        sorted_outliers = sorted(
            outliers.items(),
            key=lambda x: x[1].outlier_percentage,
            reverse=True,
        )

        for col_name, info in sorted_outliers:
            table.add_row(
                col_name,
                f"{info.total_count:,}",
                f"{info.iqr_outlier_count:,}",
                f"{info.zscore_outlier_count:,}",
                f"{info.mad_outlier_count:,}",
                f"{info.outlier_percentage:.2f}%",
                f"{info.iqr_lower_bound:.4f}",
                f"{info.iqr_upper_bound:.4f}",
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_outlier_data"):
            return

        sorted_items = sorted(
            self._outlier_data.items(),
            key=lambda x: x[1].outlier_percentage,
            reverse=True,
        )

        row_index = event.cursor_row
        if 0 <= row_index < len(sorted_items):
            col_name, info = sorted_items[row_index]
            detail = self.query_one("#outliers-detail", Static)

            sample_vals = ""
            if info.outlier_values:
                sample_vals = ", ".join(f"{v:.4f}" for v in info.outlier_values[:8])

            detail.update(
                f"\n  Column: {col_name}\n"
                f"  IQR Outliers: {info.iqr_outlier_count:,}  |  "
                f"Z-Score: {info.zscore_outlier_count:,}  |  "
                f"MAD: {info.mad_outlier_count:,}\n"
                f"  IQR Bounds: [{info.iqr_lower_bound:.4f}, {info.iqr_upper_bound:.4f}]\n"
                f"  Sample outlier values: {sample_vals}\n"
            )

    def _render_error(self, message):
        loading = self.query_one("#outliers-loading", LoadingIndicator)
        content = self.query_one("#outliers-content")
        loading.display = False
        content.display = True
        summary = self.query_one("#outliers-summary", Static)
        summary.update(f"  Error: {message}")
