from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work

from datatui.tui.widgets.stat_card import StatCard

__all__ = ["MissingScreen"]


class MissingScreen(Screen):

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Missing Values", classes="screen-title"),
            Static("", id="missing-summary"),
            DataTable(id="missing-table"),
            Static("", id="missing-patterns"),
            id="missing-content",
        )
        yield LoadingIndicator(id="missing-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#missing-loading", LoadingIndicator)
        content = self.query_one("#missing-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
            return

        try:
            missing = analyzer.analyze_missing()
            self.app.call_from_thread(self._render_missing, missing)
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_missing(self, missing):
        loading = self.query_one("#missing-loading", LoadingIndicator)
        content = self.query_one("#missing-content")
        loading.display = False
        content.display = True

        overall_pct = missing.get("overall_missing_percentage", 0)
        complete_rows = missing.get("complete_rows", 0)
        complete_pct = missing.get("complete_rows_percentage", 0)
        total_cells = missing.get("total_cells", 0)
        total_missing = missing.get("total_missing_values", 0)

        summary = self.query_one("#missing-summary", Static)
        summary.update(
            f"  Overall Missing: {overall_pct:.2f}%  |  "
            f"Complete Rows: {complete_rows:,} ({complete_pct:.1f}%)  |  "
            f"Total Cells: {total_cells:,}  |  "
            f"Missing Cells: {total_missing:,}"
        )

        table = self.query_one("#missing-table", DataTable)
        table.clear(columns=True)
        table.add_column("Column", key="column")
        table.add_column("Missing", key="missing")
        table.add_column("Present", key="present")
        table.add_column("Missing %", key="pct")
        table.add_column("Bar", key="bar")

        columns = missing.get("columns", {})
        sorted_cols = sorted(
            columns.items(),
            key=lambda x: x[1].missing_percentage,
            reverse=True,
        )

        for col_name, col_info in sorted_cols:
            pct = col_info.missing_percentage
            bar_len = int(pct / 2.5)
            bar = "\u2588" * bar_len
            table.add_row(
                col_name,
                f"{col_info.missing_count:,}",
                f"{col_info.present_count:,}",
                f"{pct:.2f}%",
                bar,
            )

        patterns = missing.get("patterns", [])
        if patterns:
            patterns_widget = self.query_one("#missing-patterns", Static)
            lines = ["", "  Missing Patterns:"]
            for i, pattern in enumerate(patterns[:10], 1):
                cols_str = ", ".join(pattern.columns[:5])
                if len(pattern.columns) > 5:
                    cols_str += f" (+{len(pattern.columns) - 5} more)"
                lines.append(
                    f"    {i}. [{cols_str}] - "
                    f"{pattern.count:,} rows ({pattern.percentage:.2f}%)"
                )
            patterns_widget.update("\n".join(lines))

    def _render_error(self, message):
        loading = self.query_one("#missing-loading", LoadingIndicator)
        content = self.query_one("#missing-content")
        loading.display = False
        content.display = True
        summary = self.query_one("#missing-summary", Static)
        summary.update(f"  Error: {message}")
