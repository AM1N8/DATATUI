from typing import List, Optional

from textual.widget import Widget
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widgets import Static

__all__ = ["MiniChart"]

BLOCKS = [" ", "\u2581", "\u2582", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2588"]


class MiniChart(Widget):

    DEFAULT_CSS = """
    MiniChart {
        height: auto;
        min-height: 6;
        padding: 1;
        background: #161b22;
        border: solid #30363d;
    }
    """

    title = reactive("")

    def __init__(
        self,
        title: str = "",
        values: Optional[List[float]] = None,
        width: int = 50,
        color: str = "#58a6ff",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self._values = values or []
        self._width = width
        self._color = color

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="section-header")
        yield Static(id="chart-content")

    def on_mount(self) -> None:
        self._render_chart()

    def set_values(self, values: List[float], title: Optional[str] = None) -> None:
        self._values = values
        if title is not None:
            self.title = title
        self._render_chart()

    def _render_chart(self) -> None:
        try:
            content = self.query_one("#chart-content", Static)
        except Exception:
            return

        if not self._values:
            content.update("No data")
            return

        chart_str = self._build_bar_chart(self._values)
        content.update(chart_str)

    def _build_bar_chart(self, values: List[float]) -> str:
        if not values:
            return "No data"

        max_val = max(values) if values else 1
        min_val = min(values) if values else 0

        if max_val == min_val:
            normalized = [4 for _ in values]
        else:
            normalized = [
                int(((v - min_val) / (max_val - min_val)) * (len(BLOCKS) - 1))
                for v in values
            ]

        display_width = min(self._width, len(values))
        if len(values) > display_width:
            chunk_size = len(values) / display_width
            resampled = []
            for i in range(display_width):
                start = int(i * chunk_size)
                end = int((i + 1) * chunk_size)
                chunk = normalized[start:end]
                resampled.append(int(sum(chunk) / len(chunk)) if chunk else 0)
            normalized = resampled

        bar_line = "".join(BLOCKS[min(n, len(BLOCKS) - 1)] for n in normalized)

        lines = [
            f"  min: {min_val:.2f}  max: {max_val:.2f}  count: {len(values)}",
            f"  {bar_line}",
        ]

        return "\n".join(lines)
