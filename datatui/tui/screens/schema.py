from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, LoadingIndicator, DataTable
from textual import work

__all__ = ["SchemaScreen"]


class SchemaScreen(Screen):

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Schema", classes="screen-title"),
            DataTable(id="schema-table"),
            Static("", id="schema-detail"),
            id="schema-content",
        )
        yield LoadingIndicator(id="schema-loading")

    def on_mount(self) -> None:
        self.load_data()

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

        table.add_column("Column", key="column")
        table.add_column("DType", key="dtype")
        table.add_column("Type", key="type")
        table.add_column("Semantic", key="semantic")
        table.add_column("Unique", key="unique")
        table.add_column("Cardinality", key="cardinality")
        table.add_column("Nulls", key="nulls")
        table.add_column("Null %", key="null_pct")
        table.add_column("Memory", key="memory")

        columns = schema.get("columns", {})
        self._schema_data = columns

        for col_name, col_schema in columns.items():
            null_pct = col_schema.null_percentage
            memory = col_schema.memory_mb
            mem_str = f"{memory:.2f} MB" if memory >= 1 else f"{memory * 1024:.1f} KB"

            table.add_row(
                col_schema.column_name,
                col_schema.dtype,
                col_schema.data_type.value,
                col_schema.semantic_type.value,
                f"{col_schema.unique_count:,}",
                col_schema.cardinality.value,
                f"{col_schema.null_count:,}",
                f"{null_pct:.2f}%",
                mem_str,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not hasattr(self, "_schema_data"):
            return

        row_index = event.cursor_row
        columns = list(self._schema_data.values())
        if 0 <= row_index < len(columns):
            col_schema = columns[row_index]
            detail = self.query_one("#schema-detail", Static)
            samples = ", ".join(str(v) for v in col_schema.sample_values[:5])
            detail.update(
                f"\n  Selected: {col_schema.column_name}\n"
                f"  Type: {col_schema.data_type.value} | Semantic: {col_schema.semantic_type.value}\n"
                f"  Samples: {samples}\n"
            )

    def _render_error(self, message):
        loading = self.query_one("#schema-loading", LoadingIndicator)
        content = self.query_one("#schema-content")
        loading.display = False
        content.display = True
        detail = self.query_one("#schema-detail", Static)
        detail.update(f"  Error: {message}")
