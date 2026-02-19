from pathlib import Path
from typing import Optional

import polars as pl
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, LoadingIndicator
from textual import work

from datatui.core.loader import DataLoader, load_dataset
from datatui.core.analyzer import DataAnalyzer

from datatui.tui.screens.overview import OverviewScreen
from datatui.tui.screens.schema import SchemaScreen
from datatui.tui.screens.statistics import StatisticsScreen
from datatui.tui.screens.missing import MissingScreen
from datatui.tui.screens.outliers import OutliersScreen
from datatui.tui.screens.correlations import CorrelationsScreen
from datatui.tui.screens.distributions import DistributionsScreen
from datatui.tui.screens.visualize import VisualizeScreen

__all__ = ["DatatuiApp"]

SCREENS = {
    "overview": OverviewScreen,
    "schema": SchemaScreen,
    "statistics": StatisticsScreen,
    "missing": MissingScreen,
    "outliers": OutliersScreen,
    "correlations": CorrelationsScreen,
    "distributions": DistributionsScreen,
    "visualize": VisualizeScreen,
}

SCREEN_LABELS = [
    ("1  Overview", "overview"),
    ("2  Schema", "schema"),
    ("3  Statistics", "statistics"),
    ("4  Missing", "missing"),
    ("5  Outliers", "outliers"),
    ("6  Correlations", "correlations"),
    ("7  Distributions", "distributions"),
    ("8  Visualize", "visualize"),
]


class DatatuiApp(App):

    CSS_PATH = "styles/main.tcss"

    TITLE = "DataTUI"

    BINDINGS = [
        Binding("1", "switch_screen('overview')", "Overview", show=True),
        Binding("2", "switch_screen('schema')", "Schema", show=True),
        Binding("3", "switch_screen('statistics')", "Statistics", show=True),
        Binding("4", "switch_screen('missing')", "Missing", show=True),
        Binding("5", "switch_screen('outliers')", "Outliers", show=True),
        Binding("6", "switch_screen('correlations')", "Correlations", show=True),
        Binding("7", "switch_screen('distributions')", "Distributions", show=True),
        Binding("8", "switch_screen('visualize')", "Visualize", show=True),
        Binding("v", "switch_screen('visualize')", "Visualize", show=False),
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh_data", "Refresh", show=True),
    ]

    def __init__(self, file_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.file_path = file_path
        self.analyzer: Optional[DataAnalyzer] = None
        self._current_screen_name = "overview"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("  DataTUI", classes="screen-title"),
                ListView(
                    *[
                        ListItem(Label(label), id=f"nav-{name}")
                        for label, name in SCREEN_LABELS
                    ],
                    id="nav-list",
                ),
                id="sidebar",
            ),
            Vertical(
                Static("Loading dataset...", id="status-bar"),
                LoadingIndicator(id="main-loading"),
                id="main-content",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = str(self.file_path.name)
        self.load_dataset()

    def load_dataset(self) -> None:
        loading = self.query_one("#main-loading", LoadingIndicator)
        status = self.query_one("#status-bar", Static)
        loading.display = True
        status.update(f"  Loading {self.file_path.name}...")
        self._load_dataset_worker()

    @work(exclusive=True, thread=True)
    def _load_dataset_worker(self) -> None:
        try:
            df = load_dataset(self.file_path, lazy=False)
            if isinstance(df, pl.LazyFrame):
                df = df.collect()

            analyzer = DataAnalyzer(df, dataset_name=self.file_path.stem)
            self.analyzer = analyzer

            self.call_from_thread(
                self._on_data_loaded,
                f"  {self.file_path.name} | {len(df):,} rows x {len(df.columns)} cols",
            )
        except Exception as e:
            self.call_from_thread(
                self._on_load_error, str(e)
            )

    def _on_data_loaded(self, status_text: str) -> None:
        loading = self.query_one("#main-loading", LoadingIndicator)
        loading.display = False

        status = self.query_one("#status-bar", Static)
        status.update(status_text)

        for name, screen_class in SCREENS.items():
            self.install_screen(screen_class, name=name)

        self.push_screen("overview")
        self._current_screen_name = "overview"

    def _on_load_error(self, message: str) -> None:
        loading = self.query_one("#main-loading", LoadingIndicator)
        loading.display = False
        status = self.query_one("#status-bar", Static)
        status.update(f"  Error: {message}")

    def action_switch_screen(self, screen_name: str) -> None:
        if self.analyzer is None:
            return
        if screen_name == self._current_screen_name:
            return
        if screen_name not in SCREENS:
            return

        try:
            self.pop_screen()
        except Exception:
            pass

        self.push_screen(screen_name)
        self._current_screen_name = screen_name

    def action_refresh_data(self) -> None:
        if self.analyzer is None:
            return

        current = self._current_screen_name
        try:
            self.pop_screen()
        except Exception:
            pass

        self.push_screen(current)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id and item_id.startswith("nav-"):
            screen_name = item_id[4:]
            self.action_switch_screen(screen_name)
