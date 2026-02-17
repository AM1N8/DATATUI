from textual.widget import Widget
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

__all__ = ["StatCard"]


class StatCard(Widget):

    DEFAULT_CSS = """
    StatCard {
        height: 3;
        min-height: 3;
        padding: 0 1;
        background: #161b22;
        border: solid #30363d;
        content-align: center middle;
    }
    .card-content {
        text-align: center;
        width: 100%;
    }
    """

    label = reactive("")
    value = reactive("")
    variant = reactive("default")
    color = reactive("")
    trend = reactive("")

    def __init__(
        self,
        label: str = "",
        value: str = "",
        variant: str = "default",
        color: str = "",
        trend: str = "", # "up", "down", or ""
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.variant = variant
        self.color = color
        self.trend = trend

    def compose(self) -> ComposeResult:
        trend_icon = " \u2191" if self.trend == "up" else " \u2193" if self.trend == "down" else ""
        yield Static(f"{self.label}: {self.value}{trend_icon}", classes="card-content")

    def on_mount(self) -> None:
        if self.color:
             self.styles.border = ("solid", self.color)
             # self.query_one(".card-content").styles.color = self.color # Optional text color

    def watch_value(self, new_value: str) -> None:
        self._update_display()
            
    def watch_trend(self, new_trend: str) -> None:
        self._update_display()
        
    def _update_display(self) -> None:
        try:
            trend_icon = " \u2191" if self.trend == "up" else " \u2193" if self.trend == "down" else ""
            content = self.query_one(".card-content", Static)
            content.update(f"{self.label}: {self.value}{trend_icon}")
        except Exception:
            pass

    def watch_label(self, new_label: str) -> None:
        self._update_display()

    def watch_variant(self, new_variant: str) -> None:
        self.remove_class("success", "warning", "error", "info")
        if new_variant in ("success", "warning", "error", "info"):
            self.add_class(new_variant)
            
    def watch_color(self, new_color: str) -> None:
        if new_color:
             self.styles.border = ("solid", new_color)
