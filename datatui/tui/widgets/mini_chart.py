from typing import List, Optional, Union
import math

from textual.widget import Widget
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widgets import Static
from rich.text import Text
from rich.style import Style
from rich.table import Table

__all__ = ["MiniChart"]

BLOCKS = [" ", "\u2581", "\u2582", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2588"]
SPARK_BLOCKS = [" ", "\u2581", "\u2582", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2588"]

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

        if self._values is None or len(self._values) == 0:
            content.update("No data")
            return

        chart_str = self._build_bar_chart(self._values)
        content.update(chart_str)

    def _build_bar_chart(self, values: List[float]) -> str:
        if values is None or len(values) == 0:
            return "No data"

        max_val = max(values) if len(values) > 0 else 1
        min_val = min(values) if len(values) > 0 else 0

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

        bar_line = "".join(BLOCKS[min(max(0, n), len(BLOCKS) - 1)] for n in normalized)

        lines = [
            f"  min: {min_val:.2f}  max: {max_val:.2f}  count: {len(values)}",
            f"  {bar_line}",
        ]

        return "\n".join(lines)
        
    @staticmethod
    def render_histogram(counts: List[int], edges: List[float], width: int = 50) -> Text:
        """Render a unicode histogram."""
        # Handle numpy arrays safely
        if hasattr(counts, "__len__") and len(counts) == 0:
            return Text("")
        if not hasattr(counts, "__len__") and not counts:
             return Text("")
             
        try:
            max_count = max(counts)
        except ValueError:
            max_count = 1
            
        if max_count == 0: max_count = 1
        
        lines = []
        for i, count in enumerate(counts):
            bar_len = int((count / max_count) * width)
            bar = "\u2588" * bar_len
            if i < len(edges) - 1:
                label = f"{edges[i]:.1f}-{edges[i+1]:.1f}"
            else:
                label = ""
            lines.append(f"{label:>15} {bar} {count}")
            
        return Text("\n".join(lines), style="#58a6ff")

    @staticmethod
    def render_bar(value: float, max_value: float, width: int = 20, color: str = "green") -> Text:
        """Render a single progress bar."""
        if max_value == 0:
            pct = 0
        else:
            pct = min(1.0, max(0.0, value / max_value))
            
        bar_len = int(pct * width)
        bar = "\u2588" * bar_len
        remainder = width - bar_len
        empty = "\u2591" * remainder
        
        return Text(f"{bar}{empty}", style=color)

    @staticmethod
    def render_sparkline(values: List[float], width: int = 20) -> str:
        """Render a sparkline using unicode blocks."""
        if not values:
            return ""
            
        # Resample if needed
        if len(values) > width:
            chunk_size = len(values) / width
            resampled = []
            for i in range(width):
                 start = int(i * chunk_size)
                 end = int((i + 1) * chunk_size)
                 chunk = values[start:end]
                 resampled.append(sum(chunk) / len(chunk) if chunk else 0)
            values = resampled

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val
        
        if range_val == 0:
            return "\u2584" * len(values)
            
        chars = []
        for v in values:
            norm = (v - min_val) / range_val
            idx = int(norm * (len(SPARK_BLOCKS) - 1))
            chars.append(SPARK_BLOCKS[idx])
            
        return "".join(chars)

    @staticmethod
    def render_heatmap(matrix: List[List[float]], labels: List[str] = None) -> Table:
        """Render a correlation heatmap using Rich Table."""
        
        table = Table(box=None, show_header=True, show_edge=False, pad_edge=False)
        table.add_column("") # Row labels
        
        if labels:
            for label in labels:
                table.add_column(label[:3], justify="center", width=3)
        else:
            for i in range(len(matrix[0])):
                table.add_column(str(i), justify="center", width=3)
                
        for i, row in enumerate(matrix):
            cells = [labels[i][:10] if labels else str(i)]
            for val in row:
                # Color mapping: -1 (red) -> 0 (white) -> 1 (green)
                # We use background colors
                if val is None:
                    color = "#30363d" # gray
                    symbol = " "
                elif val >= 0:
                    intensity = int(val * 255)
                    # Green scale
                    color = f"rgb(0,{intensity},0)" if intensity > 50 else "#0d1117"
                    symbol = "\u2588"
                else:
                    intensity = int(abs(val) * 255)
                    # Red scale
                    color = f"rgb({intensity},0,0)" if intensity > 50 else "#0d1117"
                    symbol = "\u2588"
                
                # Using rich styling for block
                # Simplified: use text color for block
                if val > 0.7: style = "bright_green"
                elif val > 0.3: style = "green"
                elif val > -0.3: style = "dim white"
                elif val > -0.7: style = "red"
                else: style = "bright_red"
                
                cells.append(Text("\u2588\u2588", style=style))
            table.add_row(*cells)
            
        return table
