from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.widgets import Static, LoadingIndicator, DataTable, Input
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from datatui.tui.widgets.mini_chart import MiniChart

__all__ = ["CorrelationsScreen"]


class CorrelationsScreen(Screen):

    CSS_PATH = ["../styles/main.tcss"]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Correlation Analysis", classes="screen-title"),
            Static(id="corr-summary"),
            
            # Filter
            Static("Top Correlations", classes="section-header"),
            Input(placeholder="Minimum Correlation (0.0 - 1.0)", id="corr-filter", classes="search-input"),
            DataTable(id="corr-top-table", cursor_type="row"),
            
            Static("Correlation Matrix (Heatmap)", classes="section-header"),
            Static(id="corr-heatmap-panel", classes="chart-panel"),
            
            id="correlations-content",
        )
        yield LoadingIndicator(id="correlations-loading")

    def on_mount(self) -> None:
        self.load_data()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "corr-filter":
            try:
                min_val = float(event.value) if event.value else 0.0
                self._filter_top_corrs(min_val)
            except ValueError:
                pass

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
            # Assuming we can instantiate this
            corr_analyzer = CorrelationAnalyzer(analyzer.df)
            matrix = corr_analyzer.get_correlation_matrix(method="pearson")
            top_corrs = corr_analyzer.get_top_correlations(n=50, min_correlation=0.1) # Get more to filter locally

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
        high_corr_count = sum(1 for c in top_corrs if abs(c.correlation) > 0.6)
        
        summary.update(Panel(
            Align.center(
                f"Numeric Columns: [bold]{len(columns)}[/]  |  "
                f"Strong Correlations (|r|>0.6): [bold {'red' if high_corr_count > 0 else 'green'}]{high_corr_count}[/]"
            ),
            title="Analysis Summary", border_style="blue"
        ))

        # Render Heatmap using MiniChart
        heatmap_panel = self.query_one("#corr-heatmap-panel", Static)
        if matrix_data and columns:
            # We assume matrix val is float
            # MiniChart.render_heatmap handles rendering
            heatmap = MiniChart.render_heatmap(matrix_data, labels=columns)
            heatmap_panel.update(heatmap)
        else:
            heatmap_panel.update("No numeric data for correlations.")

        # Top Correlations Table
        self._top_corrs_data = top_corrs
        self._filter_top_corrs(0.3) # Default filter

    def _filter_top_corrs(self, min_val: float):
        if not hasattr(self, "_top_corrs_data"):
            return
            
        top_table = self.query_one("#corr-top-table", DataTable)
        top_table.clear(columns=True)
        top_table.add_column("Rank", key="rank")
        top_table.add_column("Column 1", key="col1")
        top_table.add_column("Column 2", key="col2")
        top_table.add_column("Correlation", key="corr")
        top_table.add_column("Strength", key="strength")

        filtered = [c for c in self._top_corrs_data if abs(c.correlation) >= min_val]
        
        for i, pair in enumerate(filtered, 1):
            corr = pair.correlation
            abs_corr = abs(corr)
            
            if abs_corr > 0.8: strength = "Very Strong"
            elif abs_corr > 0.6: strength = "Strong"
            elif abs_corr > 0.4: strength = "Moderate"
            else: strength = "Weak"
            
            color = "red" if corr < 0 else "green"
            if abs_corr < 0.3: color = "dim white"
            
            # Badge style for strength
            badge_style = "bold red" if abs_corr > 0.8 else "yellow" if abs_corr > 0.6 else "blue"
            
            top_table.add_row(
                str(i),
                pair.column1,
                pair.column2,
                Text(f"{corr:.4f}", style=color),
                Text(strength, style=badge_style)
            )

    def _render_error(self, message):
        loading = self.query_one("#correlations-loading", LoadingIndicator)
        content = self.query_one("#correlations-content")
        loading.display = False
        content.display = True
        summary = self.query_one("#corr-summary", Static)
        summary.update(f"[red]Error: {message}[/]")
