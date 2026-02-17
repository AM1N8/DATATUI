from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from datatui.tui.widgets.mini_chart import MiniChart
from datatui.tui.widgets.stat_card import StatCard

__all__ = ["OutliersScreen"]


class OutliersScreen(Screen):

    CSS_PATH = ["../styles/main.tcss"]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Outlier Analysis", classes="screen-title"),
            Static(id="outliers-dashboard"),
            Vertical(
                DataTable(id="outliers-table", cursor_type="row"),
                Static("Detailed Analysis", classes="section-header"),
                Static(id="outliers-detail", classes="detail-panel"),
                id="outliers-panel"
            ),
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
            # We assume OutlierDetector is available and working
            # If strict "do not modify/create" applies to core, then I trust it works.
            # But I should check imports if I was not sure.
            
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
        
        dashboard = self.query_one("#outliers-dashboard", Static)
        if cols_with_outliers == 0:
            success_content = Align.center(
                Text("\n\n✔ No Outliers Detected\n\n", style="bold green", justify="center"),
                vertical="middle"
            )
            dashboard.update(Panel(success_content, title="Analysis Result", border_style="green"))
            self.query_one("#outliers-panel").display = False
            return
            
        self.query_one("#outliers-panel").display = True
        dashboard.update(Panel(
            Align.center(f"[bold yellow]{cols_with_outliers}[/] columns have outliers"),
            title="Analysis Summary", border_style="yellow"
        ))

        table = self.query_one("#outliers-table", DataTable)
        table.clear(columns=True)
        table.add_column("Column", key="column")
        table.add_column("Total Outliers", key="total")
        table.add_column("Outlier %", key="pct")
        table.add_column("Method Comparison (IQR vs Z vs MAD)", key="comparison", width=30)
        table.add_column("Bounds (IQR)", key="bounds")

        self._outlier_data = outliers

        sorted_outliers = sorted(
            outliers.items(),
            key=lambda x: x[1].outlier_percentage,
            reverse=True,
        )
        
        if sorted_outliers:
            max_outliers_any_col = max(info.total_count for _, info in sorted_outliers)
        else:
            max_outliers_any_col = 1

        for col_name, info in sorted_outliers:
             if info.total_count == 0:
                 continue
                 
             # Color for pct
             pct = info.outlier_percentage
             if pct < 5: pct_color = "green"
             elif pct < 10: pct_color = "yellow"
             else: pct_color = "red"
             
             # Comparison Bars
             # Simple approach: show stacked or side-by-side mini bars?
             # Textual DataTable supports Rich. 
             # Let's show: IQR[bar] Z[bar] MAD[bar]
             # Normalized against max of THIS column across methods to show relative sensitivity?
             # Or against total rows?
             # Comparison means checking which method flags more.
             methods = [("I", info.iqr_outlier_count), ("Z", info.zscore_outlier_count), ("M", info.mad_outlier_count)]
             max_m = max(m[1] for m in methods) if methods else 1
             
             # Construct Text object manually
             comp_visual = Text()
             for i, (label, count) in enumerate(methods):
                 bar = MiniChart.render_bar(count, max_m, width=5, color="blue" if label=="I" else "cyan" if label=="Z" else "magenta")
                 if i > 0:
                     comp_visual.append(" ")
                 comp_visual.append(f"{label}:{bar}")
             
             # Bounds visual
             bounds_str = f"[{info.iqr_lower_bound:.2f} ... {info.iqr_upper_bound:.2f}]"
             
             table.add_row(
                 col_name,
                 f"{info.total_count:,}",
                 Text(f"{pct:.2f}%", style=pct_color),
                 comp_visual,
                 Text(bounds_str, style="dim white"),
                 key=col_name
             )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_outlier_data"):
            return

        # Use row key
        try:
            row_key = event.row_key.value
        except:
             return
        
        info = self._outlier_data.get(row_key)
        if info:
            detail = self.query_one("#outliers-detail", Static)

            sample_vals = ""
            if info.outlier_values:
                # Top 10 outliers
                vals = sorted(info.outlier_values, reverse=True)[:10]
                sample_vals = ", ".join(f"{v:.4f}" for v in vals)

            content = f"""
[bold]{row_key}[/]:
[dim]--------------------------------[/]
[bold]IQR Outliers:[/][yellow] {info.iqr_outlier_count:,}[/]  [dim](Robust to extremes)[/]
[bold]Z-Score Outliers:[/][cyan] {info.zscore_outlier_count:,}[/]  [dim](Assumes normality)[/]
[bold]MAD Outliers:[/][magenta] {info.mad_outlier_count:,}[/]  [dim](Strict)[/]

[bold]Statistical Bounds (IQR):[/]
Lower: [red]{info.iqr_lower_bound:.4f}[/]
Upper: [red]{info.iqr_upper_bound:.4f}[/]

[bold]Extreme Values Found:[/][italic]
{sample_vals}
[/]
"""
            detail.update(content)

    def _render_error(self, message):
        loading = self.query_one("#outliers-loading", LoadingIndicator)
        content = self.query_one("#outliers-content")
        loading.display = False
        content.display = True
        
        dash = self.query_one("#outliers-dashboard", Static)
        dash.update(f"[red]Error: {message}[/]")
