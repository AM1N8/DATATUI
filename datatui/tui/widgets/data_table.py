from typing import Any, Dict, List, Optional

from textual.widget import Widget
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable as TextualDataTable, Input, Static
from textual.reactive import reactive

__all__ = ["FilterableDataTable"]


class FilterableDataTable(Widget):

    DEFAULT_CSS = """
    FilterableDataTable {
        height: 1fr;
        background: #161b22;
    }
    FilterableDataTable Input {
        margin: 0 0 1 0;
        height: 3;
    }
    """

    filter_text = reactive("")

    def __init__(
        self,
        columns: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._columns = columns or []
        self._rows: List[List[str]] = []
        self._all_rows: List[List[str]] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter rows...", id="filter-input")
        yield TextualDataTable(id="inner-table")

    def on_mount(self) -> None:
        table = self.query_one("#inner-table", TextualDataTable)
        for col in self._columns:
            table.add_column(col, key=col)

    def set_data(self, columns: List[str], rows: List[List[str]]) -> None:
        self._columns = columns
        self._all_rows = rows
        self._rows = rows

        table = self.query_one("#inner-table", TextualDataTable)
        table.clear(columns=True)
        for col in columns:
            table.add_column(col, key=col)
        for row in rows:
            table.add_row(*row)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self.filter_text = event.value

    def watch_filter_text(self, value: str) -> None:
        self._apply_filter(value)

    def _apply_filter(self, text: str) -> None:
        table = self.query_one("#inner-table", TextualDataTable)
        table.clear()

        if not text:
            filtered = self._all_rows
        else:
            lower_text = text.lower()
            filtered = [
                row for row in self._all_rows
                if any(lower_text in str(cell).lower() for cell in row)
            ]

        for row in filtered:
            table.add_row(*row)
