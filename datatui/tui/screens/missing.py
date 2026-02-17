from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

__all__ = ["MissingScreen"]


class MissingScreen(Screen):

    CSS_PATH = ["../styles/main.tcss"]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Missing Values Analysis", classes="screen-title"),
            Static(id="missing-dashboard"),
            Vertical(
                DataTable(id="missing-table", cursor_type="row"),
                Static("Missing Patterns", classes="section-header"),
                DataTable(id="missing-patterns-table", cursor_type="row"),
                id="missing-details"
            ),
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
        total_missing = missing.get("total_missing_values", 0)
        
        dashboard = self.query_one("#missing-dashboard", Static)
        
        if total_missing == 0:
            # Success Panel
            success_content = Align.center(
                Text("\n\n✔ No Missing Values Found\n\n", style="bold green", justify="center"),
                vertical="middle"
            )
            dashboard.update(Panel(success_content, title="Analysis Result", border_style="green"))
            self.query_one("#missing-details").display = False
            return
        
        self.query_one("#missing-details").display = True
        dashboard.update(Panel(
            Align.center(f"[bold red]{total_missing:,}[/] missing values ([bold red]{overall_pct:.2f}%[/] of data)"),
            title="Analysis Checks", border_style="red"
        ))

        table = self.query_one("#missing-table", DataTable)
        table.clear(columns=True)
        table.add_column("Column", key="column")
        table.add_column("Missing Count", key="missing")
        table.add_column("Missing %", key="pct")
        table.add_column("Visual", key="bar")

        columns = missing.get("columns", {})
        sorted_cols = sorted(
            columns.items(),
            key=lambda x: x[1].missing_percentage,
            reverse=True,
        )

        for col_name, col_info in sorted_cols:
            if col_info.missing_count == 0:
                continue
                
            pct = col_info.missing_percentage
            bar_len = int(pct / 2.5) # Max 40 chars
            bar_len = min(bar_len, 40)
            
            if pct < 5: color = "yellow"
            elif pct < 20: color = "dark_orange"
            else: color = "red"
            
            bar = Text("█" * bar_len, style=color)
            
            table.add_row(
                col_name,
                f"{col_info.missing_count:,}",
                Text(f"{pct:.2f}%", style=color),
                bar,
            )

        # Patterns Table
        p_table = self.query_one("#missing-patterns-table", DataTable)
        p_table.clear(columns=True)
        p_table.add_column("Pattern (Columns Missing Together)", key="pattern")
        p_table.add_column("Rows", key="rows")
        p_table.add_column("%", key="pct")
        
        patterns = missing.get("patterns", [])
        for pattern in patterns:
             # pattern is MissingPattern object, not dict
             cols_str = ", ".join(pattern.columns)
             count = pattern.count
             pct = pattern.percentage
             
             p_table.add_row(
                 cols_str,
                 f"{count:,}",
                 f"{pct:.2f}%"
             )

    def _render_error(self, message):
        loading = self.query_one("#missing-loading", LoadingIndicator)
        content = self.query_one("#missing-content")
        loading.display = False
        content.display = True
        dash = self.query_one("#missing-dashboard", Static)
        dash.update(f"[red]Error: {message}[/]")
