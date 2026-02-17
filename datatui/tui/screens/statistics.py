from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.widgets import Static, LoadingIndicator, DataTable, TabbedContent, TabPane
from textual import work
from rich.text import Text

from datatui.core.statistics import NumericStats, CategoricalStats, DatetimeStats, TextStats
from datatui.tui.widgets.mini_chart import MiniChart

__all__ = ["StatisticsScreen"]


class StatisticsScreen(Screen):

    CSS_PATH = ["../styles/main.tcss"]

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="statistics-content"):
            yield Static("Statistics Analysis", classes="screen-title")
            with TabbedContent(id="stats-tabs"):
                with TabPane("Numeric", id="tab-numeric"):
                    yield DataTable(id="numeric-stats-table", cursor_type="row")
                with TabPane("Categorical", id="tab-categorical"):
                    yield DataTable(id="categorical-stats-table", cursor_type="row")
                with TabPane("Datetime", id="tab-datetime"):
                    yield DataTable(id="datetime-stats-table", cursor_type="row")
                with TabPane("Text", id="tab-text"):
                    yield DataTable(id="text-stats-table", cursor_type="row")
            
            # Detail Panel
            yield Vertical(
                Static("Select a row to see distribution", id="stats-detail-text"),
                Static(id="stats-detail-chart"),
                id="stats-detail-panel",
                classes="detail-panel"
            )
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
            # We also need histogram data for numeric columns for the detail view
            # The analyzer might not compute histograms by default in analyze_statistics
            # We can fetch them on demand or pre-compute.
            # For now let's assume we can get distribution data or compute it on selection?
            # Computing on selection in UI thread is bad if heavy.
            # Best to compute basic histograms now or use existing data.
            # analyze_statistics might not have histograms. analyze_distributions does.
            # Let's try to get distributions too if cheap, or just raw data access on selection (since it is worker thread? No selection is main thread).
            # Actually, `NumericStats` in `datatui.core.statistics` likely has `histogram` if we added it, or we can compute it from df.
            # Safe bet: access df in selection handler (main thread) but keep it light (sample?).
            # Or run a worker on selection.
            
            self.app.call_from_thread(self._render_statistics, statistics)
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_statistics(self, statistics):
        loading = self.query_one("#statistics-loading", LoadingIndicator)
        content = self.query_one("#statistics-content")
        loading.display = False
        content.display = True

        self._stats_data = statistics.get("statistics", {})

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

        for col_name, col_stats in self._stats_data.items():
            if isinstance(col_stats, NumericStats):
                skew_val = col_stats.skewness
                if abs(skew_val) < 0.5: skew_color = "green"
                elif abs(skew_val) < 1.0: skew_color = "yellow"
                else: skew_color = "red"
                
                skew_cell = Text(f"{skew_val:.3f}", style=skew_color)
                
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
                    skew_cell,
                    f"{col_stats.kurtosis:.3f}",
                    key=col_name
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

        for col_name, col_stats in self._stats_data.items():
            if isinstance(col_stats, CategoricalStats):
                cat_table.add_row(
                    col_name,
                    f"{col_stats.count:,}",
                    f"{col_stats.unique_count:,}",
                    str(col_stats.mode) if col_stats.mode else "-",
                    f"{col_stats.mode_frequency:,}",
                    f"{col_stats.mode_percentage:.2f}%",
                    f"{col_stats.entropy:.3f}",
                    key=col_name
                )
                
        # Datetime and Text tables (simpler)
        dt_table = self.query_one("#datetime-stats-table", DataTable)
        dt_table.clear(columns=True)
        dt_table.add_column("Column", key="column")
        dt_table.add_column("Count", key="count")
        dt_table.add_column("Min", key="min")
        dt_table.add_column("Max", key="max")
        dt_table.add_column("Range (days)", key="range")
        dt_table.add_column("Unique", key="unique")

        for col_name, col_stats in self._stats_data.items():
             if isinstance(col_stats, DatetimeStats):
                range_str = f"{col_stats.range_days:.1f}" if col_stats.range_days is not None else "-"
                dt_table.add_row(
                    col_name,
                    f"{col_stats.count:,}",
                    str(col_stats.min),
                    str(col_stats.max),
                    range_str,
                    f"{col_stats.unique_count:,}",
                    key=col_name
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
        
        for col_name, col_stats in self._stats_data.items():
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
                    key=col_name
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_stats_data"):
            return
            
        try:
            row_key = event.row_key.value
        except:
            return
            
        col_stats = self._stats_data.get(row_key)
        if not col_stats:
            return
            
        detail_text = self.query_one("#stats-detail-text", Static)
        detail_chart = self.query_one("#stats-detail-chart", Static)
        
        detail_text.update(f"[bold]{row_key}[/]")
        
        if isinstance(col_stats, NumericStats):
            # Compute histogram on the fly from DF (fast for small data, potentially slow for big)
            # Better to use a worker, but for visual snapiness on main thread with 'flights-1m.json' might be heavy.
            # But wait, we need 'analyzer.df'.
            analyzer = self.app.analyzer
            if analyzer and analyzer.df is not None:
                # Use numpy/polars to get histogram
                try:
                    import numpy as np
                    col_data = analyzer.df[row_key].drop_nulls()
                    if len(col_data) > 0:
                        hist, bin_edges = np.histogram(col_data.to_numpy(), bins=20)
                        chart = MiniChart.render_histogram(hist, bin_edges, width=60)
                        detail_chart.update(chart)
                    else:
                        detail_chart.update("No data for histogram")
                except Exception as e:
                    detail_chart.update(f"Could not compute histogram: {e}")
                    
        elif isinstance(col_stats, CategoricalStats):
            # Show top values
            if col_stats.top_values:
                # Render bar chart
                lines = []
                # top_values is list of (val, count, pct)
                max_count = max(item[1] for item in col_stats.top_values) if col_stats.top_values else 1
                for val, count, _ in col_stats.top_values:
                    bar = MiniChart.render_bar(count, max_count, width=40, color="blue")
                    lines.append(f"{str(val)[:20]:<20} {bar} {count}")
                detail_chart.update(Text("\n".join(lines)))
            else:
                detail_chart.update("No top values available")
        else:
            detail_chart.update("No visual distribution available for this type")

    def _render_error(self, message):
        loading = self.query_one("#statistics-loading", LoadingIndicator)
        content = self.query_one("#statistics-content")
        loading.display = False
        content.display = True
        detail = self.query_one("#stats-detail-text", Static)
        detail.update(f"[red]Error: {message}[/]")
