import plotext as plt
from typing import List, Dict, Any

def preview_histogram(data: List[float], title: str) -> str:
    """Render a plotext histogram as a string."""
    plt.clf()
    plt.theme("dark")
    plt.plotsize(100, 25)
    plt.title(title)
    plt.hist(data, bins=20, color="cyan")
    return plt.build()

def preview_correlation_heatmap(matrix: List[List[float]], labels: List[str]) -> str:
    """Render a plotext heatmap as a string."""
    # Plotext doesn't have a direct heatmap, but we can use matrix plotting if supported
    # or a grid of bars. For now, we'll try to use a simple matrix representation or 
    # warn that it's a simplified version.
    plt.clf()
    plt.theme("dark")
    plt.plotsize(100, 25)
    plt.title("Correlation Heatmap (Preview)")
    
    # Note: plotext's matrix/heatmap support is limited in some versions.
    # We'll use a scatter plot with blocks if needed, but standard bar/plot is safer.
    # Simplified: Show as a matrix-like scatter plot
    x = []
    y = []
    colors = []
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            x.append(j)
            y.append(i)
            # Map val to color or size?
            
    plt.scatter(x, y, marker="block")
    plt.xticks(range(len(labels)), labels)
    plt.yticks(range(len(labels)), labels)
    return plt.build()

def preview_box_plot(data: Dict[str, List[float]]) -> str:
    """Render a plotext box plot as a string."""
    plt.clf()
    plt.theme("dark")
    plt.plotsize(100, 25)
    plt.title("Box Plot (Preview)")
    
    labels = list(data.keys())
    values = list(data.values())
    
    plt.box(labels, values)
    return plt.build()

def preview_scatter(x: List[float], y: List[float], x_label: str = "X", y_label: str = "Y") -> str:
    """Render a plotext scatter plot as a string."""
    plt.clf()
    plt.theme("dark")
    plt.plotsize(100, 25)
    plt.title(f"Scatter: {x_label} vs {y_label}")
    plt.scatter(x, y, color="blue")
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    return plt.build()
