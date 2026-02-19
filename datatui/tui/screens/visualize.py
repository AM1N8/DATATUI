from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, Horizontal, Container
from textual.widgets import Static, LoadingIndicator, DataTable, RadioSet, RadioButton, Select, Button, Input, Checkbox, Label
from textual import work, on
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from pathlib import Path
from typing import List, Dict, Any, Optional
import polars as pl

from datatui.visualizers.terminal import (
    preview_histogram, preview_box_plot, preview_scatter, preview_correlation_heatmap
)
from datatui.visualizers.plots import (
    generate_histogram, generate_box_plot, generate_correlation_heatmap,
    generate_scatter_plot, generate_pair_plot, generate_violin_plot,
    generate_distribution_comparison, generate_categorical_bar,
    generate_missing_pattern, generate_time_series
)

__all__ = ["VisualizeScreen"]

class VisualizeScreen(Screen):
    CSS_PATH = ["../styles/main.tcss"]
    BINDINGS = [
        ("p", "preview", "Preview"),
        ("g", "generate", "Generate"),
        ("b", "batch", "Batch Generate"),
    ]

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Visualization Laboratory", classes="screen-title"),
            
            Horizontal(
                # Left Panel: Configuration
                Vertical(
                    Static("Plot Type", classes="section-header"),
                    RadioSet(
                        RadioButton("Histogram", id="radio-histogram", value=True),
                        RadioButton("Box Plot", id="radio-box"),
                        RadioButton("Correlation Heatmap", id="radio-heatmap"),
                        RadioButton("Scatter Plot", id="radio-scatter"),
                        RadioButton("Pair Plot", id="radio-pair"),
                        RadioButton("Violin Plot", id="radio-violin"),
                        RadioButton("Distribution Comparison", id="radio-dist"),
                        RadioButton("Categorical Bar", id="radio-categorical"),
                        RadioButton("Missing Pattern", id="radio-missing"),
                        id="plot-type-selector"
                    ),
                    
                    Horizontal(
                        Button("Preview", variant="primary", id="btn-preview"),
                        Button("Generate", variant="success", id="btn-generate"),
                        id="action-buttons"
                    ),
                    Button("Batch Generate All", variant="default", id="btn-batch", classes="full-width"),
                    
                    Static("Column Selection", classes="section-header"),
                    Container(
                        # Mode 1: Single Numeric
                        Vertical(
                            Label("Select Column"),
                            Select([], id="select-col-numeric", prompt="Choose numeric..."),
                            id="group-numeric",
                            classes="config-group"
                        ),
                        # Mode 2: Multi Numeric
                        Vertical(
                            Label("Select Columns (Max 10)"),
                            ScrollableContainer(id="multi-col-list"),
                            id="group-multi",
                            classes="config-group hidden"
                        ),
                        # Mode 3: Scatter
                        Vertical(
                            Label("X Axis (Numeric)"),
                            Select([], id="select-scatter-x", prompt="X Variable"),
                            Label("Y Axis (Numeric)"),
                            Select([], id="select-scatter-y", prompt="Y Variable"),
                            Label("Color By (Optional)"),
                            Select([], id="select-scatter-hue", prompt="None"),
                            id="group-scatter",
                            classes="config-group hidden"
                        ),
                        # Mode 4: Categorical
                        Vertical(
                            Label("Select Category"),
                            Select([], id="select-col-cat", prompt="Choose categorical..."),
                            id="group-cat",
                            classes="config-group hidden"
                        ),
                        id="column-selectors"
                    ),
                    
                    Static("Configuration", classes="section-header"),
                    Horizontal(
                        Vertical(
                            Label("Format"),
                            RadioSet(
                                RadioButton("PNG", value=True, id="f-png"),
                                RadioButton("SVG", id="f-svg"),
                                RadioButton("PDF", id="f-pdf"),
                                id="format-selector"
                            ),
                        ),
                        Vertical(
                            Label("DPI"),
                            Input("300", id="input-dpi"),
                        ),
                        classes="config-row"
                    ),
                    Vertical(
                        Label("Filename"),
                        Input("", id="input-filename"),
                    ),
                    
                    Static(classes="spacer"),
                    classes="viz-left-panel"
                ),
                
                # Right Panel: Preview
                Vertical(
                    Static("Terminal Preview", classes="section-header"),
                    Container(
                        Static(id="viz-preview-content"),
                        LoadingIndicator(id="viz-preview-loading", classes="hidden"),
                        id="viz-preview-container", 
                        classes="chart-panel"
                    ),
                    Static(id="viz-status-log", classes="status-log"),
                    classes="viz-right-panel"
                ),
                id="viz-split-view"
            ),
            id="visualize-content",
        )
        yield LoadingIndicator(id="visualize-loading")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        loading = self.query_one("#visualize-loading", LoadingIndicator)
        content = self.query_one("#visualize-content")
        loading.display = True
        content.display = False
        self._load_data_worker()

    @work(exclusive=True, thread=True)
    def _load_data_worker(self) -> None:
        analyzer = self.app.analyzer
        if analyzer is None:
             return
             
        numeric_cols = [c for c, t in zip(analyzer.df.columns, analyzer.df.dtypes) if t in pl.NUMERIC_DTYPES]
        cat_cols = [c for c, t in zip(analyzer.df.columns, analyzer.df.dtypes) if t in [pl.String, pl.Categorical, pl.Boolean]]
        all_cols = analyzer.df.columns
        
        self.app.call_from_thread(self._setup_ui, numeric_cols, cat_cols, all_cols)

    def _setup_ui(self, numeric_cols, cat_cols, all_cols):
        self._numeric_cols = numeric_cols
        self._cat_cols = cat_cols
        self._all_cols = all_cols
        
        loading = self.query_one("#visualize-loading", LoadingIndicator)
        content = self.query_one("#visualize-content")
        loading.display = False
        content.display = True
        
        # Populate Selects
        num_opts = [(c, c) for c in numeric_cols]
        cat_opts = [(c, c) for c in cat_cols]
        all_opts = [("None", None)] + [(c, c) for c in all_cols]
        
        self.query_one("#select-col-numeric", Select).set_options(num_opts)
        self.query_one("#select-col-cat", Select).set_options(cat_opts)
        self.query_one("#select-scatter-x", Select).set_options(num_opts)
        self.query_one("#select-scatter-y", Select).set_options(num_opts)
        self.query_one("#select-scatter-hue", Select).set_options(all_opts)
        
        # Populate Multi-col list
        multi_list = self.query_one("#multi-col-list", ScrollableContainer)
        multi_list.remove_children()
        for col in numeric_cols:
            multi_list.mount(Checkbox(col, id=f"cb-{col}"))
            
        self._update_selectors("histogram")

    def _update_selectors(self, plot_type: str):
        groups = {
            "numeric": self.query_one("#group-numeric"),
            "multi": self.query_one("#group-multi"),
            "scatter": self.query_one("#group-scatter"),
            "cat": self.query_one("#group-cat")
        }
        
        for g in groups.values(): 
            g.display = False
        
        low_label = plot_type.lower()
        if "histogram" in low_label or "distribution" in low_label:
            groups["numeric"].display = True
        elif any(t in low_label for t in ["box", "violin", "pair"]):
            groups["multi"].display = True
        elif "scatter" in low_label:
            groups["scatter"].display = True
        elif "categorical" in low_label:
            groups["cat"].display = True
            
    def _get_current_plot_type(self) -> str:
        active = self.query_one("#plot-type-selector").pressed_button
        return str(active.label).lower()

    @on(RadioSet.Changed, "#plot-type-selector")
    def on_plot_type_changed(self, event: RadioSet.Changed):
        label = str(event.pressed.label).lower()
        self._update_selectors(label)
        dataset_name = self.app.analyzer.dataset_name if self.app.analyzer else "plot"
        self.query_one("#input-filename").value = f"{label.replace(' ', '_')}_{dataset_name}.png"

    def _log(self, message: str, style: str = "white"):
        self.query_one("#viz-status-log", Static).update(Text(message, style=style))

    @on(Button.Pressed, "#btn-preview")
    def on_preview_pressed(self):
        ptype = self._get_current_plot_type()
        self._log(f"Generating preview for {ptype}...")
        self.query_one("#viz-preview-content").display = False
        self.query_one("#viz-preview-loading").display = True
        self._preview_worker(ptype)

    @work(exclusive=True, thread=True)
    def _preview_worker(self, ptype: str):
        analyzer = self.app.analyzer
        df = analyzer.df
        preview_str = ""
        
        try:
            label = ptype.lower()
            if "histogram" in label or "distribution" in label:
                col = self.query_one("#select-col-numeric", Select).value
                if col == Select.BLANK or col is None: raise ValueError("Select a column first")
                data = df[col].drop_nulls().to_list()
                if not data: raise ValueError(f"Column '{col}' has no data")
                preview_str = preview_histogram(data, f"{ptype.title()}: {col}")
            
            elif "scatter" in label:
                x_col = self.query_one("#select-scatter-x", Select).value
                y_col = self.query_one("#select-scatter-y", Select).value
                if x_col == Select.BLANK or y_col == Select.BLANK: raise ValueError("Select X and Y")
                x_data = df[x_col].drop_nulls().to_list()
                y_data = df[y_col].drop_nulls().to_list()
                if len(x_data) > 1000:
                    x_data = x_data[:1000]
                    y_data = y_data[:1000]
                preview_str = preview_scatter(x_data, y_data, x_col, y_col)
            
            elif "box" in label:
                selected = [cb.label.plain for cb in self.query_one("#multi-col-list").query(Checkbox) if cb.value]
                if not selected: raise ValueError("Check at least one column")
                data_dict = {col: df[col].drop_nulls().to_list()[:500] for col in selected[:5]}
                preview_str = preview_box_plot(data_dict)
                
            elif "correlation" in label:
                numeric_df = df.select(pl.col(pl.NUMERIC_DTYPES))
                if numeric_df.width < 2: raise ValueError("Need 2+ numeric columns")
                corr_matrix = numeric_df.to_pandas().corr().values.tolist()
                preview_str = preview_correlation_heatmap(corr_matrix, numeric_df.columns)

            elif "categorical" in label:
                col = self.query_one("#select-col-cat", Select).value
                if col == Select.BLANK or col is None: raise ValueError("Select a categorical column")
                import plotext as plt
                counts = df[col].value_counts().sort('count', descending=True).head(10)
                plt.clf()
                plt.theme("dark")
                plt.plotsize(100, 25)
                plt.bar(counts[col].to_list(), counts['count'].to_list(), color="magenta")
                plt.title(f"Top 10: {col}")
                preview_str = plt.build()
            
            else:
                preview_str = f"Preview for '{ptype}' is not available in terminal yet.\nUse 'Generate' for full Seaborn export."

            self.app.call_from_thread(self._update_preview, preview_str)
        except Exception as e:
            self.app.call_from_thread(self._log, f"Error: {e}", "red")

    def _update_preview(self, content: str):
        self.query_one("#viz-preview-loading").display = False
        content_static = self.query_one("#viz-preview-content", Static)
        content_static.display = True
        
        if content.startswith("\x1b"):
            content_static.update(Text.from_ansi(content))
        else:
            content_static.update(Align(Text(content, justify="center"), align="center", vertical="middle"))
        self._log("Ready", "green")

    @on(Button.Pressed, "#btn-generate")
    def on_generate_pressed(self):
        ptype = self._get_current_plot_type()
        filename = self.query_one("#input-filename").value or f"{ptype.replace(' ', '_').replace('(', '').replace(')', '')}.png"
        self._log(f"Generating high-res {ptype} -> {filename}...")
        self._generate_worker(ptype, filename)

    @work(exclusive=True, thread=True)
    def _generate_worker(self, ptype: str, filename: str):
        analyzer = self.app.analyzer
        df = analyzer.df
        output_path = Path(filename)
        
        try:
            # Common params
            fmt = str(self.query_one("#format-selector").pressed_button.label).lower()
            dpi_str = self.query_one("#input-dpi").value
            dpi = int(dpi_str) if dpi_str.isdigit() else 300
            
            if ptype == "histogram":
                col = self.query_one("#select-col-numeric", Select).value
                generate_histogram(df, col, output_path, format=fmt, dpi=dpi)
            
            elif ptype == "box plot":
                cols = [cb.label.plain for cb in self.query_one("#multi-col-list").query(Checkbox) if cb.value]
                generate_box_plot(df, cols, output_path, format=fmt, dpi=dpi)
            
            elif ptype == "correlation heatmap":
                numeric_df = df.select(pl.col(pl.NUMERIC_DTYPES))
                corr_matrix = numeric_df.to_pandas().corr().values.tolist()
                generate_correlation_heatmap(corr_matrix, numeric_df.columns, output_path, format=fmt, dpi=dpi)
            
            elif ptype == "scatter plot":
                x_col = self.query_one("#select-scatter-x", Select).value
                y_col = self.query_one("#select-scatter-y", Select).value
                hue_col = self.query_one("#select-scatter-hue", Select).value
                if hue_col == "None": hue_col = None
                generate_scatter_plot(df, x_col, y_col, output_path, hue_col=hue_col, format=fmt, dpi=dpi)
            
            elif ptype == "pair plot":
                cols = [cb.label.plain for cb in self.query_one("#multi-col-list").query(Checkbox) if cb.value]
                generate_pair_plot(df, cols, output_path, format=fmt, dpi=dpi)
            
            elif ptype == "violin plot":
                cols = [cb.label.plain for cb in self.query_one("#multi-col-list").query(Checkbox) if cb.value]
                generate_violin_plot(df, cols, output_path, format=fmt, dpi=dpi)
            
            elif ptype == "distribution comparison":
                col = self.query_one("#select-col-numeric", Select).value
                generate_distribution_comparison(df, col, output_path, format=fmt, dpi=dpi)
            
            elif ptype == "categorical bar":
                col = self.query_one("#select-col-cat", Select).value
                generate_categorical_bar(df, col, output_path, format=fmt, dpi=dpi)
                
            elif ptype == "missing pattern":
                generate_missing_pattern(df, output_path, format=fmt, dpi=dpi)
            
            self.app.call_from_thread(self._log, f"Saved to {output_path.absolute()}", "green")
        except Exception as e:
            self.app.call_from_thread(self._log, f"Error: {e}", "red")

    @on(Button.Pressed, "#btn-batch")
    def on_batch_pressed(self):
        self._log("Starting batch generation in 'plots/' directory...")
        output_dir = Path("plots")
        output_dir.mkdir(exist_ok=True)
        self._batch_worker(output_dir)

    @work(exclusive=True, thread=True)
    def _batch_worker(self, output_dir: Path):
        from datatui.cli.commands.visualize import run_batch_mode
        try:
            run_batch_mode(self.app.analyzer.df, output_dir, "png", 150)
            self.app.call_from_thread(self._log, f"Batch complete: {output_dir.absolute()}", "bold green")
        except Exception as e:
            self.app.call_from_thread(self._log, f"Batch Error: {e}", "red")
    def action_preview(self):
        self.on_preview_pressed()

    def action_generate(self):
        self.on_generate_pressed()

    def action_batch(self):
        self.on_batch_pressed()
