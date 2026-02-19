import matplotlib.pyplot as plt
import seaborn as sns

SEABORN_DARK_THEME = {
    'style': 'darkgrid',
    'palette': ['#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff'],
    'figure.facecolor': '#0d1117',
    'axes.facecolor': '#161b22',
    'text.color': '#c9d1d9',
    'axes.labelcolor': '#c9d1d9',
    'xtick.color': '#c9d1d9',
    'ytick.color': '#c9d1d9',
    'grid.color': '#30363d',
    'font.family': 'sans-serif',  # Changed from monospace to be more professional if monospace is not available
    'figure.dpi': 100
}

def apply_theme() -> None:
    """Apply the DataTUI dark theme to matplotlib and seaborn."""
    plt.style.use('dark_background')
    sns.set_theme(
        style="darkgrid",
        rc={
            "figure.facecolor": "#0d1117",
            "axes.facecolor": "#161b22",
            "grid.color": "#30363d",
            "text.color": "#c9d1d9",
            "axes.labelcolor": "#c9d1d9",
            "xtick.color": "#c9d1d9",
            "ytick.color": "#c9d1d9",
            "axes.edgecolor": "#30363d",
        }
    )
    sns.set_palette(SEABORN_DARK_THEME['palette'])
