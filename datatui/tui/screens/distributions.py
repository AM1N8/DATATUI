from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from datatui.tui.widgets.mini_chart import MiniChart

__all__ = ["DistributionsScreen"]


class DistributionsScreen(Screen):

    CSS_PATH = ["../styles/main.tcss"]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Distribution Analysis", classes="screen-title"),
            Static(id="dist-summary"),
            
            Horizontal(
                Vertical(
                    Static("Distributions Table", classes="section-header"),
                    DataTable(id="dist-table", cursor_type="row"),
                    classes="dist-left-panel"
                ),
                Vertical(
                    Static("Selected Column Distribution", classes="section-header"),
                    Static(id="dist-plot-container", classes="chart-panel"),
                    Static("Normality Tests", classes="section-header"),
                    DataTable(id="dist-normality-table", cursor_type="row"),
                    classes="dist-right-panel"
                ),
                id="dist-split-view"
            ),
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
        summary.update(Panel(
            Align.center(
                f"Columns Analyzed: [bold]{len(distributions)}[/]  |  "
                f"Normal: [bold green]{len(normal_cols)}[/]  |  "
                f"Skewed: [bold red]{len(skewed_cols)}[/]"
            ),
            title="Overview", border_style="blue"
        ))

        table = self.query_one("#dist-table", DataTable)
        table.clear(columns=True)
        table.add_column("Column", key="column")
        table.add_column("Type", key="type")
        table.add_column("Normal?", key="normal")
        table.add_column("Skewness", key="skew")
        #table.add_column("Kurtosis", key="kurt")

        self._dist_data = distributions

        for col_name, info in distributions.items():
            is_normal = info.get("is_normal", False)
            skew = info.get('skewness', 0)
            
            # Badges
            normal_badge = Text("YES", style="bold green") if is_normal else Text("NO", style="bold red")
            
            skew_style = "green"
            if abs(skew) > 1: skew_style = "red"
            elif abs(skew) > 0.5: skew_style = "yellow"
            
            skew_text = Text(f"{skew:.3f}", style=skew_style)
            if skew > 0: skew_text.append(" (R)", style="dim")
            elif skew < 0: skew_text.append(" (L)", style="dim")
            
            dist_type = info.get("distribution_type", "unknown")
            type_badge = Text(dist_type, style="cyan")

            table.add_row(
                col_name,
                type_badge,
                normal_badge,
                skew_text,
                #f"{info.get('kurtosis', 0):.3f}",
                key=col_name
            )

        if distributions:
            # Select first row
            first_col = next(iter(distributions))
            self._show_histogram(first_col)
            # We can programmatically select row 0 if we want
            # table.move_cursor(row=0) # Need to check API

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_dist_data"):
            return

        try:
             col_name = event.row_key.value
             self._show_histogram(col_name)
        except:
             pass

    def _show_histogram(self, col_name):
        if col_name not in self._dist_data:
            return

        info = self._dist_data[col_name]
        histogram = info.get("histogram", {})
        counts = histogram.get("counts", [])
        bins = histogram.get("edges", [])

        chart_container = self.query_one("#dist-plot-container", Static)
        
        # Try using plotext if available, else MiniChart
        try:
            import plotext as plt
            # Ensure safe data types (list) and check for empty
            if hasattr(counts, "__len__") and len(counts) > 0:
                plt.clf()
                plt.plotsize(60, 20) # Width, Height
                plt.theme("dark")
                
                # Convert to lists to be safe with plotext
                x = list(bins[:-1])
                y = list(counts)
                
                plt.bar(x, y, label=col_name, color="blue")
                plt.title(f"Distribution of {col_name}")
                plt.xlabel("Value")
                plt.ylabel("Frequency")
                plot_str = plt.build()
                chart_container.update(Text.from_ansi(plot_str))
            else:
                 chart_container.update("No data for histogram")
        except ImportError:
             # Fallback to MiniChart
            if hasattr(counts, "__len__") and len(counts) > 0:
                # Basic bar chart from counts
                # Ensure lists
                c_list = list(counts) if hasattr(counts, "tolist") else list(counts)
                b_list = list(bins) if hasattr(bins, "tolist") else list(bins)
                
                chart_text = MiniChart.render_histogram(c_list, b_list, width=60)
                # Manually add title since render_histogram doesn't support it
                title = Text(f"Histogram: {col_name}\n", style="bold")
                chart_container.update(title + chart_text)
            else:
                chart_container.update(f"No histogram data for {col_name}")
        except Exception as e:
             chart_container.update(f"Error rendering plot: {e}")

        # Normality Table
        norm_table = self.query_one("#dist-normality-table", DataTable)
        norm_table.clear(columns=True)
        norm_table.add_column("Test", key="test")
        norm_table.add_column("Statistic", key="stat")
        norm_table.add_column("p-value", key="p")
        norm_table.add_column("Result", key="result")
        
        normality = info.get("normality_tests", {})
        if normality:
            for test_name in ("shapiro_wilk", "anderson_darling", "dagostino_pearson", "kolmogorov_smirnov"):
                test = normality.get(test_name)
                if test and isinstance(test, dict):
                    stat = test.get("statistic", 0)
                    p_val = test.get("p_value", test.get("critical_value", 0))
                    is_n = test.get("is_normal", False)
                    
                    result_badge = Text("Normal", style="bold green") if is_n else Text("Not Normal", style="bold red")
                    
                    norm_table.add_row(
                        test_name.replace('_', ' ').title(),
                        f"{stat:.4f}",
                        f"{p_val:.4f}",
                        result_badge
                    )
        else:
            norm_table.add_row("No normality tests run", "-", "-", "-")

    def _render_error(self, message):
        loading = self.query_one("#distributions-loading", LoadingIndicator)
        content = self.query_one("#distributions-content")
        loading.display = False
        content.display = True
        summary = self.query_one("#dist-summary", Static)
        summary.update(f"[red]Error: {message}[/]")
