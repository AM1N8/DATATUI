import matplotlib.pyplot as plt
import seaborn as sns
import polars as pl
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from .themes import apply_theme

def _to_pandas(df: Union[pl.DataFrame, pd.DataFrame]) -> pd.DataFrame:
    """Convert polars to pandas for seaborn compatibility."""
    if isinstance(df, pl.DataFrame):
        return df.to_pandas()
    return df

def _sample_df(df: pd.DataFrame, max_rows: int = 100000) -> pd.DataFrame:
    """Sample dataframe if it exceeds max_rows."""
    if len(df) > max_rows:
        return df.sample(n=max_rows, random_state=42)
    return df

def generate_histogram(df: pl.DataFrame, column: str, output_path: Path, 
                       format: str = 'png', dpi: int = 300) -> Path:
    """Generate a high-quality histogram with KDE."""
    apply_theme()
    pdf = _to_pandas(df)
    pdf = _sample_df(pdf)
    
    plt.figure(figsize=(10, 6))
    sns.histplot(data=pdf, x=column, kde=True, color='#58a6ff')
    
    # Add mean/median lines
    mean_val = pdf[column].mean()
    median_val = pdf[column].median()
    plt.axvline(mean_val, color='#f85149', linestyle='--', label=f'Mean: {mean_val:.2f}')
    plt.axvline(median_val, color='#3fb950', linestyle='-', label=f'Median: {median_val:.2f}')
    
    plt.title(f"Distribution of {column}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_box_plot(df: pl.DataFrame, columns: List[str], output_path: Path,
                      format: str = 'png', dpi: int = 300) -> Path:
    """Generate side-by-side box plots."""
    apply_theme()
    pdf = _to_pandas(df)
    pdf = _sample_df(pdf)
    
    plt.figure(figsize=(12, 6))
    # Melt for side-by-side comparison if multiple columns
    if len(columns) > 1:
        melted = pdf.melt(value_vars=columns)
        sns.boxplot(data=melted, x='variable', y='value', showmeans=True,
                    meanprops={"marker":"D","markerfacecolor":"white", "markeredgecolor":"white"})
    else:
        sns.boxplot(data=pdf, y=columns[0], showmeans=True,
                    meanprops={"marker":"D","markerfacecolor":"white", "markeredgecolor":"white"})
        plt.xlabel(columns[0])
    
    plt.title("Box Plot Comparison")
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_correlation_heatmap(correlation_matrix: List[List[float]], 
                                 labels: List[str], output_path: Path,
                                 format: str = 'png', dpi: int = 300) -> Path:
    """Generate a Seaborn heatmap from a correlation matrix."""
    apply_theme()
    
    plt.figure(figsize=(12, 10))
    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    
    sns.heatmap(correlation_matrix, xticklabels=labels, yticklabels=labels,
                annot=True, fmt=".2f", cmap='RdYlGn', center=0,
                square=True, linewidths=.5, cbar_kws={"shrink": .5}, mask=mask)
    
    plt.title("Correlation Matrix Heatmap")
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_scatter_plot(df: pl.DataFrame, x_col: str, y_col: str, 
                         output_path: Path, hue_col: str = None,
                         format: str = 'png', dpi: int = 300) -> Path:
    """Generate a scatter plot with optional hue and trend line."""
    apply_theme()
    pdf = _to_pandas(df)
    pdf = _sample_df(pdf)
    
    plt.figure(figsize=(10, 6))
    if hue_col:
        sns.scatterplot(data=pdf, x=x_col, y=y_col, hue=hue_col)
    else:
        sns.scatterplot(data=pdf, x=x_col, y=y_col)
        # Add regression line only for single color
        try:
            sns.regplot(data=pdf, x=x_col, y=y_col, scatter=False, color='#f85149')
            # Calculate R2
            from scipy import stats
            mask = ~pdf[x_col].isna() & ~pdf[y_col].isna()
            slope, intercept, r_value, p_value, std_err = stats.linregress(pdf[x_col][mask], pdf[y_col][mask])
            plt.annotate(f'R² = {r_value**2:.3f}', xy=(0.05, 0.95), xycoords='axes fraction')
        except:
            pass
            
    plt.title(f"{x_col} vs {y_col}")
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_pair_plot(df: pl.DataFrame, columns: List[str], 
                      output_path: Path, hue_col: str = None,
                      format: str = 'png', dpi: int = 300) -> Path:
    """Generate a Seaborn pairplot."""
    apply_theme()
    pdf = _to_pandas(df)
    # Pairplots are very heavy, sample more aggressively
    pdf = _sample_df(pdf, max_rows=5000)
    
    cols_to_plot = columns + ([hue_col] if hue_col else [])
    
    g = sns.pairplot(data=pdf[cols_to_plot], hue=hue_col, corner=True)
    g.fig.suptitle("Pair Plot Analysis", y=1.02)
    
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_violin_plot(df: pl.DataFrame, columns: List[str], 
                        output_path: Path, format: str = 'png', dpi: int = 300) -> Path:
    """Generate distribution shape visualization via violin plot."""
    apply_theme()
    pdf = _to_pandas(df)
    pdf = _sample_df(pdf)
    
    plt.figure(figsize=(12, 6))
    if len(columns) > 1:
        melted = pdf.melt(value_vars=columns)
        sns.violinplot(data=melted, x='variable', y='value', split=True, inner="quart")
    else:
        sns.violinplot(data=pdf, y=columns[0], inner="quart")
        plt.xlabel(columns[0])
        
    plt.title("Violin Plot Distribution")
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_distribution_comparison(df: pl.DataFrame, column: str, 
                                   output_path: Path, format: str = 'png', dpi: int = 300) -> Path:
    """Generate a 4-panel distribution analysis plot."""
    apply_theme()
    pdf = _to_pandas(df)
    pdf = _sample_df(pdf)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Histogram
    sns.histplot(pdf[column], kde=True, ax=axes[0, 0], color='#58a6ff')
    axes[0, 0].set_title('Histogram & KDE')
    
    # 2. Box Plot
    sns.boxplot(y=pdf[column], ax=axes[0, 1], color='#3fb950')
    axes[0, 1].set_title('Box Plot')
    
    # 3. Violin Plot
    sns.violinplot(y=pdf[column], ax=axes[1, 0], color='#bc8cff')
    axes[1, 0].set_title('Violin Plot')
    
    # 4. QQ Plot
    from scipy import stats
    stats.probplot(pdf[column].dropna(), plot=axes[1, 1])
    axes[1, 1].set_title('QQ Plot')
    
    plt.suptitle(f"Comprehensive Distribution Analysis: {column}", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_categorical_bar(df: pl.DataFrame, column: str, 
                           output_path: Path, top_n: int = 20, 
                           format: str = 'png', dpi: int = 300) -> Path:
    """Generate a bar chart of value counts."""
    apply_theme()
    counts = df[column].value_counts().sort('counts', descending=True).head(top_n)
    pdf = counts.to_pandas()
    
    plt.figure(figsize=(10, 8))
    sns.barplot(data=pdf, y=column, x='counts', palette='viridis')
    
    # Add percentages
    total = df[column].count()
    for i, p in enumerate(plt.gca().patches):
        width = p.get_width()
        plt.gca().text(width + total*0.01, p.get_y() + p.get_height()/2,
                f'{width/total*100:.1f}%', va='center')
                
    plt.title(f"Value Counts: {column} (Top {top_n})")
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_missing_pattern(df: pl.DataFrame, output_path: Path,
                            format: str = 'png', dpi: int = 300) -> Path:
    """Generate a heatmap showing missing data patterns."""
    apply_theme()
    # Sample if too large
    if len(df) > 500:
        pdf_missing = df.sample(n=500).to_pandas().isna()
    else:
        pdf_missing = df.to_pandas().isna()
        
    plt.figure(figsize=(12, 8))
    sns.heatmap(pdf_missing, cbar=False, yticklabels=False, cmap='binary_r')
    
    plt.title("Missing Data Pattern (White=Present, Black=Missing)")
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path

def generate_time_series(df: pl.DataFrame, date_col: str, value_col: str,
                        output_path: Path, format: str = 'png', dpi: int = 300) -> Path:
    """Generate a time series line plot with rolling average."""
    apply_theme()
    pdf = df.select([date_col, value_col]).to_pandas()
    pdf[date_col] = pd.to_datetime(pdf[date_col])
    pdf = pdf.sort_values(date_col)
    
    plt.figure(figsize=(12, 6))
    plt.plot(pdf[date_col], pdf[value_col], alpha=0.3, label='Actual', color='#58a6ff')
    
    # Rolling average
    pdf['rolling'] = pdf[value_col].rolling(window=min(len(pdf)//10, 30)).mean()
    plt.plot(pdf[date_col], pdf['rolling'], color='#f85149', linewidth=2, label='Rolling Avg')
    
    plt.title(f"Time Series: {value_col} over {date_col}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, format=format, dpi=dpi)
    plt.close()
    return output_path
