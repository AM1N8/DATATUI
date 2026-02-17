from textual.widget import Widget
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

__all__ = ["StatCard"]


class StatCard(Widget):

    DEFAULT_CSS = """
    StatCard {
        height: auto;
        min-height: 5;
        padding: 1 2;
        background: #161b22;
        border: solid #30363d;
        margin: 0 1 1 0;
    }
    """

    label = reactive("")
    value = reactive("")
    variant = reactive("default")

    def __init__(
        self,
        label: str = "",
        value: str = "",
        variant: str = "default",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.variant = variant

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.label, classes="card-label"),
            Static(self.value, classes="card-value"),
        )

    def watch_value(self, new_value: str) -> None:
        try:
            value_widget = self.query_one(".card-value", Static)
            value_widget.update(new_value)
        except Exception:
            pass

    def watch_label(self, new_label: str) -> None:
        try:
            label_widget = self.query_one(".card-label", Static)
            label_widget.update(new_label)
        except Exception:
            pass

    def watch_variant(self, new_variant: str) -> None:
        self.remove_class("success", "warning", "error", "info")
        if new_variant in ("success", "warning", "error", "info"):
            self.add_class(new_variant)
