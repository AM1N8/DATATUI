from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable, Input
from textual import work
from rich.text import Text

__all__ = ["SchemaScreen"]


class SchemaScreen(Screen):

    CSS_PATH = ["../styles/main.tcss"]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Schema Analysis", classes="screen-title"),
            Input(placeholder="Search columns...", id="schema-search", classes="search-input"),
            Horizontal(
                DataTable(id="schema-table", cursor_type="row"),
                Vertical(
                    Static("Select a column to see details", id="schema-detail"),
                    classes="detail-panel"
                ),
            ),
            id="schema-content",
        )
        yield LoadingIndicator(id="schema-loading")

    def on_mount(self) -> None:
        self.load_data()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "schema-search":
            self._filter_table(event.value)

    def load_data(self) -> None:
        loading = self.query_one("#schema-loading", LoadingIndicator)
        content = self.query_one("#schema-content")
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
            self.app.call_from_thread(self._render_schema, schema)
        except Exception as e:
            self.app.call_from_thread(self._render_error, str(e))

    def _render_schema(self, schema):
        loading = self.query_one("#schema-loading", LoadingIndicator)
        content = self.query_one("#schema-content")
        loading.display = False
        content.display = True

        table = self.query_one("#schema-table", DataTable)
        table.clear(columns=True)
        
        # Define columns with styled headers
        table.add_column(Text("Column", style="green bold"), key="column")
        table.add_column(Text("Type", style="cyan bold"), key="type")
        table.add_column(Text("Nulls", style="red bold"), key="nulls")
        table.add_column(Text("Null %", style="red bold"), key="null_pct")
        table.add_column(Text("Unique", style="blue bold"), key="unique")
        table.add_column(Text("Memory", style="magenta bold"), key="memory")

        columns = schema.get("columns", {})
        self._schema_data = columns # Store for details
        self._all_rows = [] # Store for filtering

        for col_name, col_schema in columns.items():
            # Style Type column
            dtype_val = col_schema.data_type.value
            if dtype_val == "Numeric": type_color = "cyan"
            elif dtype_val == "Categorical": type_color = "green"
            elif dtype_val == "Datetime": type_color = "magenta"
            else: type_color = "yellow"
            
            type_cell = Text(dtype_val, style=type_color)

            # Style Null % column
            null_pct = col_schema.null_percentage
            if null_pct == 0:
                null_style = "green"
                bar = ""
            elif null_pct < 10:
                null_style = "yellow"
                bar = "▂"
            else:
                null_style = "red"
                bar = "▃" if null_pct < 50 else "▄"
            
            null_pct_cell = Text(f"{null_pct:.1f}% {bar}", style=null_style)

            memory = col_schema.memory_mb
            mem_str = f"{memory:.2f} MB" if memory >= 1 else f"{memory * 1024:.1f} KB"

            row = [
                col_name,
                col_schema.dtype, # Raw dtype
                type_cell, # Visual Type
                f"{col_schema.null_count:,}",
                null_pct_cell,
                f"{col_schema.unique_count:,}",
                mem_str,
            ]
            
            # Simplified columns for table (merged some)
            visual_row = [
                Text(col_name, style="bold"),
                type_cell,
                str(col_schema.null_count),
                null_pct_cell,
                str(col_schema.unique_count),
                Text(mem_str, style="dim magenta")
            ]
            
            self._all_rows.append((col_name, visual_row))
            table.add_row(*visual_row, key=col_name)

    def _filter_table(self, query: str) -> None:
        table = self.query_one("#schema-table", DataTable)
        table.clear()
        
        query = query.lower()
        for col_name, row_data in self._all_rows:
            if query in col_name.lower():
                table.add_row(*row_data, key=col_name)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_schema_data"):
            return

        # Get key (col name) from selection
        try:
            row_key = event.row_key.value
        except:
            # Fallback if row key usage is tricky, use cursor row index mapped to filtered list? No, key is safer.
            # But wait, DataTable row keys are maintained even after filtering? Yes if added with key.
            return

        col_schema = self._schema_data.get(row_key)
        if col_schema:
            detail = self.query_one("#schema-detail", Static)
            
            samples = ", ".join(str(v) for v in col_schema.sample_values[:8])
            
            # Format nicely
            content = f"""
[bold gold1]{col_schema.column_name}[/]
[dim]--------------------------------[/]
[bold]Data Type:[/][cyan] {col_schema.dtype}[/]
[bold]Semantic Type:[/][{col_schema.data_type.value == 'Numeric' and 'cyan' or 'green'}] {col_schema.semantic_type.value}[/]

[bold]Statistics:[/][dim]
- Unique values: {col_schema.unique_count:,}
- Null values: {col_schema.null_count:,} ({col_schema.null_percentage:.2f}%)
- Cardinality: {col_schema.cardinality.value}
- Memory Usage: {col_schema.memory_mb:.2f} MB
[/]

[bold]Sample Values:[/][italic]
{samples}
[/]
"""
            detail.update(content)

    def _render_error(self, message):
        loading = self.query_one("#schema-loading", LoadingIndicator)
        content = self.query_one("#schema-content")
        loading.display = False
        content.display = True
        detail = self.query_one("#schema-detail", Static)
        detail.update(f"[red]Error loading schema: {message}[/]")
