from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable, TabbedContent, TabPane
from textual import work

from datatui.core.statistics import NumericStats, CategoricalStats, DatetimeStats, TextStats

__all__ = ["StatisticsScreen"]


class StatisticsScreen(Screen):

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="statistics-content"):
            yield Static("Statistics", classes="screen-title")
            with TabbedContent(id="stats-tabs"):
                with TabPane("Numeric", id="tab-numeric"):
                    yield DataTable(id="numeric-stats-table")
                with TabPane("Categorical", id="tab-categorical"):
                    yield DataTable(id="categorical-stats-table")
                with TabPane("Datetime", id="tab-datetime"):
                    yield DataTable(id="datetime-stats-table")
                with TabPane("Text", id="tab-text"):
                    yield DataTable(id="text-stats-table")
        yield LoadingIndicator(id="statistics-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#statistics-loading", LoadingIndicator)
        content = self.query_one("#statistics-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
            return

        try:
            statistics = analyzer.analyze_statistics()
            self.app.call_from_thread(self._render_statistics, statistics)
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_statistics(self, statistics):
        loading = self.query_one("#statistics-loading", LoadingIndicator)
        content = self.query_one("#statistics-content")
        loading.display = False
        content.display = True

        stats_data = statistics.get("statistics", {})

        numeric_table = self.query_one("#numeric-stats-table", DataTable)
        numeric_table.clear(columns=True)
        numeric_table.add_column("Column", key="column")
        numeric_table.add_column("Count", key="count")
        numeric_table.add_column("Mean", key="mean")
        numeric_table.add_column("Std", key="std")
        numeric_table.add_column("Min", key="min")
        numeric_table.add_column("Q25", key="q25")
        numeric_table.add_column("Median", key="median")
        numeric_table.add_column("Q75", key="q75")
        numeric_table.add_column("Max", key="max")
        numeric_table.add_column("Skew", key="skew")
        numeric_table.add_column("Kurt", key="kurt")

        for col_name, col_stats in stats_data.items():
            if isinstance(col_stats, NumericStats):
                numeric_table.add_row(
                    col_name,
                    f"{col_stats.count:,}",
                    f"{col_stats.mean:.4f}",
                    f"{col_stats.std:.4f}",
                    f"{col_stats.min:.4f}",
                    f"{col_stats.q25:.4f}",
                    f"{col_stats.median:.4f}",
                    f"{col_stats.q75:.4f}",
                    f"{col_stats.max:.4f}",
                    f"{col_stats.skewness:.3f}",
                    f"{col_stats.kurtosis:.3f}",
                )

        cat_table = self.query_one("#categorical-stats-table", DataTable)
        cat_table.clear(columns=True)
        cat_table.add_column("Column", key="column")
        cat_table.add_column("Count", key="count")
        cat_table.add_column("Unique", key="unique")
        cat_table.add_column("Mode", key="mode")
        cat_table.add_column("Mode Freq", key="mode_freq")
        cat_table.add_column("Mode %", key="mode_pct")
        cat_table.add_column("Entropy", key="entropy")

        for col_name, col_stats in stats_data.items():
            if isinstance(col_stats, CategoricalStats):
                cat_table.add_row(
                    col_name,
                    f"{col_stats.count:,}",
                    f"{col_stats.unique_count:,}",
                    str(col_stats.mode) if col_stats.mode else "-",
                    f"{col_stats.mode_frequency:,}",
                    f"{col_stats.mode_percentage:.2f}%",
                    f"{col_stats.entropy:.3f}",
                )

        dt_table = self.query_one("#datetime-stats-table", DataTable)
        dt_table.clear(columns=True)
        dt_table.add_column("Column", key="column")
        dt_table.add_column("Count", key="count")
        dt_table.add_column("Min", key="min")
        dt_table.add_column("Max", key="max")
        dt_table.add_column("Range (days)", key="range")
        dt_table.add_column("Unique", key="unique")

        for col_name, col_stats in stats_data.items():
            if isinstance(col_stats, DatetimeStats):
                range_str = f"{col_stats.range_days:.1f}" if col_stats.range_days is not None else "-"
                dt_table.add_row(
                    col_name,
                    f"{col_stats.count:,}",
                    str(col_stats.min) if col_stats.min else "-",
                    str(col_stats.max) if col_stats.max else "-",
                    range_str,
                    f"{col_stats.unique_count:,}",
                )

        text_table = self.query_one("#text-stats-table", DataTable)
        text_table.clear(columns=True)
        text_table.add_column("Column", key="column")
        text_table.add_column("Count", key="count")
        text_table.add_column("Unique", key="unique")
        text_table.add_column("Mode", key="mode")
        text_table.add_column("Avg Len", key="avg_len")
        text_table.add_column("Min Len", key="min_len")
        text_table.add_column("Max Len", key="max_len")
        text_table.add_column("Empty", key="empty")

        for col_name, col_stats in stats_data.items():
            if isinstance(col_stats, TextStats):
                mode_val = str(col_stats.mode)[:30] if col_stats.mode else "-"
                text_table.add_row(
                    col_name,
                    f"{col_stats.count:,}",
                    f"{col_stats.unique_count:,}",
                    mode_val,
                    f"{col_stats.avg_length:.1f}",
                    str(col_stats.min_length),
                    str(col_stats.max_length),
                    f"{col_stats.empty_count:,}",
                )

    def _render_error(self, message):
        loading = self.query_one("#statistics-loading", LoadingIndicator)
        content = self.query_one("#statistics-content")
        loading.display = False
        content.display = True
