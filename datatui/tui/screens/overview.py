from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, LoadingIndicator, Label, ProgressBar
from textual import work

from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich import box

from datatui.tui.widgets.quality_bar import QualityBar

__all__ = ["OverviewScreen"]


class OverviewScreen(Screen):
    CSS_PATH = ["../styles/main.tcss", "../styles/overview.tcss"]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Analyzing...", id="overview-banner"),
            
            # Metrics Grid (using Horizontal which becomes grid via CSS)
            Horizontal(id="metrics-grid", classes="metrics-grid"),

            # Quality Section
            Vertical(
                Label("Data Quality Score", classes="section-header"),
                QualityBar(id="quality-bar"),
                classes="quality-section"
            ),

            # Bottom Split (Charts & Alerts)
            Horizontal(
                Static(id="type-chart", classes="chart-panel"),
                Static(id="alerts-panel", classes="alerts-panel"),
                id="bottom-split",
                classes="bottom-split"
            ),
            
            id="overview-content",
        )
        yield LoadingIndicator(id="overview-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#overview-loading", LoadingIndicator)
        content = self.query_one("#overview-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
            return

        try:
            schema = analyzer.analyze_schema()
            quality = analyzer.get_data_quality_score()
            missing = analyzer.analyze_missing()
            
            self.app.call_from_thread(
                self._render_overview, schema, quality, missing
            )
        except Exception as e:
            self.app.call_from_thread(
                self._render_error, str(e)
            )

    def _create_stat_card(self, label: str, value: str, variant: str = "info") -> Static:
        return Static(
            f"\n[{variant} bold]{value}[/]\n[dim]{label}[/]",
            classes="big-stat"
        )

    def _render_overview(self, schema, quality, missing):
        loading = self.query_one("#overview-loading", LoadingIndicator)
        content = self.query_one("#overview-content")
        loading.display = False
        content.display = True

        analyzer = self.app.analyzer
        df = analyzer.df
        dataset_name = self.app.file_path.name

        # 1. Banner
        banner = self.query_one("#overview-banner", Static)
        banner_content = Align.center(
            Text(dataset_name, style="bold magenta", justify="center"), 
            vertical="middle"
        )
        banner.update(Panel(banner_content, title="[b]DATATUI[/]", subtitle=f"{len(df):,} rows", border_style="magenta"))

        # 2. Metrics Grid
        grid = self.query_one("#metrics-grid", Horizontal)
        grid.remove_children()
        
        # Calculate stats
        mem_bytes = sum(col.memory_mb for col in schema.get("columns", {}).values()) * 1024 * 1024
        mem_str = f"{mem_bytes / 1024 / 1024:.1f} MB"
        
        missing_pct = missing.get("overall_missing_percentage", 0)
        missing_color = "green" if missing_pct < 5 else "yellow" if missing_pct < 20 else "red"
        
        dup_count = df.is_duplicated().sum() if hasattr(df, "is_duplicated") else 0 # Polars check
        # Notes: Polars DataFrame doesn't have is_duplicated() directly in all versions, 
        # usually `df.is_duplicated().sum()` works or `len(df) - len(df.unique())`.
        # Let's use generic approach:
        try:
            # Polars
            import polars as pl
            if isinstance(df, pl.DataFrame):
                dup_count = len(df) - len(df.unique())
            else:
                # Pandas fallback if ever used
                dup_count = df.duplicated().sum()
        except:
            dup_count = 0
            
        dup_pct = (dup_count / len(df)) * 100 if len(df) > 0 else 0
        
        grid.mount(self._create_stat_card("Rows", f"{len(df):,}", "cyan"))
        grid.mount(self._create_stat_card("Columns", f"{len(df.columns)}", "cyan"))
        grid.mount(self._create_stat_card("Memory", mem_str, "magenta"))
        grid.mount(self._create_stat_card("Missing", f"{missing_pct:.1f}%", missing_color))

        # 3. Quality Score
        q_score = quality.get("overall_score", 0)
        q_bar = self.query_one("#quality-bar", QualityBar)
        q_bar.score = q_score
        q_bar.rating = quality.get("quality_rating", "Unknown")

        # 4. Type Distribution Chart (Bottom Left)
        type_chart = self.query_one("#type-chart", Static)
        type_dist = schema.get("type_distribution", {})
        
        chart_table = Table(box=None, expand=True, show_header=False)
        chart_table.add_column("Type", width=15)
        chart_table.add_column("Chart")
        chart_table.add_column("Count", justify="right")
        
        max_count = max(type_dist.values()) if type_dist else 1
        
        for dtype, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            bar_len = int((count / max_count) * 20)
            bar = "█" * bar_len
            chart_table.add_row(
                dtype,
                Text(bar, style="blue"),
                str(count)
            )
            
        type_chart.update(Panel(chart_table, title="Column Types", border_style="blue"))

        # 5. Alerts (Bottom Right)
        alerts_panel = self.query_one("#alerts-panel", Static)
        alerts_table = Table(box=None, expand=True, show_header=False)
        
        has_alerts = False
        
        if missing_pct > 0:
            level = "[red]" if missing_pct > 20 else "[yellow]" if missing_pct > 5 else "[blue]"
            alerts_table.add_row(f"{level}⚠[/] {missing_pct:.1f}% data missing")
            has_alerts = True
            
        if dup_pct > 0:
             alerts_table.add_row(f"[yellow]⚠[/] {dup_count:,} duplicates ({dup_pct:.1f}%)")
             has_alerts = True
             
        if q_score < 60:
            alerts_table.add_row(f"[red]⚠[/] Low Quality Score: {q_score:.1f}")
            has_alerts = True
            
        cols_with_missing = [
            col for col, info in missing.get("columns", {}).items()
            if info.missing_percentage > 50
        ]
        if cols_with_missing:
            alerts_table.add_row(f"[red]![/] {len(cols_with_missing)} cols > 50% missing")
            has_alerts = True

        if not has_alerts:
            alerts_table.add_row("[green]✔[/] No critical issues found")

        alerts_panel.update(Panel(alerts_table, title="System Alerts", border_style="yellow"))

    def _render_error(self, message):
        loading = self.query_one("#overview-loading", LoadingIndicator)
        content = self.query_one("#overview-content")
        loading.display = False
        content.display = True
        
        # Display error in banner or alerts
        banner = self.query_one("#overview-banner", Static)
        banner.update(Panel(f"[red bold]Error: {message}[/]", title="Error", border_style="red"))
