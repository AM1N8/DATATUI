from textual.widget import Widget
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, ProgressBar

__all__ = ["QualityBar"]

QUALITY_COLORS = {
    "excellent": "success",
    "good": "success",
    "fair": "warning",
    "poor": "error",
}


class QualityBar(Widget):

    DEFAULT_CSS = """
    QualityBar {
        height: 5;
        padding: 1 2;
        background: #161b22;
        border: solid #30363d;
    }
    """

    score = reactive(0.0)
    rating = reactive("unknown")

    def __init__(
        self,
        score: float = 0.0,
        rating: str = "unknown",
        label: str = "Quality Score",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.score = score
        self.rating = rating
        self._label = label

    def compose(self) -> ComposeResult:
        yield Static(f"{self._label}: {self.score:.1f}/100 ({self.rating.upper()})", id="quality-label")
        yield ProgressBar(total=100, show_eta=False, show_percentage=True, id="quality-progress")

    def on_mount(self) -> None:
        self._update_bar()

    def watch_score(self, new_score: float) -> None:
        self._update_bar()

    def _update_bar(self) -> None:
        try:
            bar = self.query_one("#quality-progress", ProgressBar)
            bar.update(progress=self.score)
            
            # Update color based on score
            bar.ctx.classes.difference_update({"success", "warning", "error"})
            if self.score >= 75:
                bar.add_class("success")
            elif self.score >= 60:
                bar.add_class("warning")
            else:
                bar.add_class("error")
                
            label = self.query_one("#quality-label", Static)
            label.update(f"{self._label}: {self.score:.1f}/100 ({self.rating.upper()})")
        except Exception:
            pass
