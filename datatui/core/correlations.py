import polars as pl
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from scipy.stats import pearsonr, spearmanr, pointbiserialr
import math


@dataclass
class CorrelationPair:
    column1: str
    column2: str
    correlation: float
    method: str
    p_value: Optional[float] = None


class CorrelationAnalyzer:
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_rows = len(df)
    
    def analyze_all(self) -> Dict[str, Any]:
        numeric_cols = self._get_numeric_columns()
        categorical_cols = self._get_categorical_columns()
        
        pearson_corr = self._calculate_pearson(numeric_cols)
        spearman_corr = self._calculate_spearman(numeric_cols)
        cramers_v = self._calculate_cramers_v(categorical_cols)
        
        mixed_corr = self._calculate_mixed_correlations(numeric_cols, categorical_cols)
        
        return {
            'pearson': pearson_corr,
            'spearman': spearman_corr,
            'cramers_v': cramers_v,
            'mixed': mixed_corr,
            'numeric_columns': numeric_cols,
            'categorical_columns': categorical_cols
        }
    
    def _get_numeric_columns(self) -> List[str]:
        numeric_cols = []
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if any(t in dtype for t in ['Int', 'UInt', 'Float']):
                numeric_cols.append(col)
        return numeric_cols
    
    def _get_categorical_columns(self) -> List[str]:
        categorical_cols = []
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            series = self.df[col].drop_nulls()
            
            if 'Categorical' in dtype or 'Utf8' in dtype or 'String' in dtype:
                if len(series) > 0:
                    unique_ratio = series.n_unique() / len(series)
                    if unique_ratio <= 0.1:
                        categorical_cols.append(col)
        return categorical_cols
    
    def _calculate_pearson(self, columns: List[str]) -> Dict[Tuple[str, str], CorrelationPair]:
        correlations = {}
        
        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                corr_value, p_value = self._pearson_correlation(col1, col2)
                
                if corr_value is not None:
                    correlations[(col1, col2)] = CorrelationPair(
                        column1=col1,
                        column2=col2,
                        correlation=corr_value,
                        method='pearson',
                        p_value=p_value
                    )
        
        return correlations
    
    def _calculate_spearman(self, columns: List[str]) -> Dict[Tuple[str, str], CorrelationPair]:
        correlations = {}
        
        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                corr_value, p_value = self._spearman_correlation(col1, col2)
                
                if corr_value is not None:
                    correlations[(col1, col2)] = CorrelationPair(
                        column1=col1,
                        column2=col2,
                        correlation=corr_value,
                        method='spearman',
                        p_value=p_value
                    )
        
        return correlations
    
    def _calculate_cramers_v(self, columns: List[str]) -> Dict[Tuple[str, str], CorrelationPair]:
        correlations = {}
        
        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                corr_value = self._cramers_v(col1, col2)
                
                if corr_value is not None:
                    correlations[(col1, col2)] = CorrelationPair(
                        column1=col1,
                        column2=col2,
                        correlation=corr_value,
                        method='cramers_v',
                        p_value=None
                    )
        
        return correlations
    
    def _calculate_mixed_correlations(
        self, 
        numeric_cols: List[str], 
        categorical_cols: List[str]
    ) -> Dict[Tuple[str, str], CorrelationPair]:
        correlations = {}
        
        for num_col in numeric_cols:
            for cat_col in categorical_cols:
                if self._is_binary(cat_col):
                    corr_value, p_value = self._point_biserial(num_col, cat_col)
                    
                    if corr_value is not None:
                        correlations[(num_col, cat_col)] = CorrelationPair(
                            column1=num_col,
                            column2=cat_col,
                            correlation=corr_value,
                            method='point_biserial',
                            p_value=p_value
                        )
        
        return correlations
    
    def _pearson_correlation(self, col1: str, col2: str) -> Tuple[Optional[float], Optional[float]]:
        try:
            df_clean = self.df.select([col1, col2]).drop_nulls()
            
            if len(df_clean) < 2:
                return None, None
            
            x = df_clean[col1].to_numpy().astype(float)
            y = df_clean[col2].to_numpy().astype(float)
            
            if np.std(x) == 0 or np.std(y) == 0:
                return None, None
            
            corr, p_value = pearsonr(x, y)
            
            if np.isnan(corr):
                return None, None
            
            return float(corr), float(p_value)
        except Exception:
            return None, None
    
    def _spearman_correlation(self, col1: str, col2: str) -> Tuple[Optional[float], Optional[float]]:
        try:
            df_clean = self.df.select([col1, col2]).drop_nulls()
            
            if len(df_clean) < 2:
                return None, None
            
            x = df_clean[col1].to_numpy().astype(float)
            y = df_clean[col2].to_numpy().astype(float)
            
            if len(np.unique(x)) == 1 or len(np.unique(y)) == 1:
                return None, None
            
            corr, p_value = spearmanr(x, y)
            
            if np.isnan(corr):
                return None, None
            
            return float(corr), float(p_value)
        except Exception:
            return None, None
    
    def _cramers_v(self, col1: str, col2: str) -> Optional[float]:
        try:
            df_clean = self.df.select([col1, col2]).drop_nulls()
            
            if len(df_clean) < 2:
                return None
            
            contingency_table = df_clean.group_by([col1, col2]).agg(pl.len().alias('count'))
            
            pivot = contingency_table.pivot(
                values='count',
                index=col1,
                columns=col2,
                aggregate_function='sum'
            ).fill_null(0)
            
            observed = pivot.select(pl.all().exclude(col1)).to_numpy()
            
            if observed.size == 0:
                return None
            
            chi2 = self._calculate_chi_square(observed)
            n = observed.sum()
            min_dim = min(observed.shape[0], observed.shape[1]) - 1
            
            if min_dim == 0 or n == 0:
                return None
            
            cramers = math.sqrt(chi2 / (n * min_dim))
            
            return float(cramers)
        except Exception:
            return None
    
    def _calculate_chi_square(self, observed: np.ndarray) -> float:
        row_sums = observed.sum(axis=1, keepdims=True)
        col_sums = observed.sum(axis=0, keepdims=True)
        total = observed.sum()
        
        if total == 0:
            return 0.0
        
        expected = (row_sums @ col_sums) / total
        
        expected = np.where(expected == 0, 1e-10, expected)
        
        chi2 = np.sum((observed - expected) ** 2 / expected)
        
        return float(chi2)
    
    def _is_binary(self, column: str) -> bool:
        unique_count = self.df[column].drop_nulls().n_unique()
        return unique_count == 2
    
    def _point_biserial(self, numeric_col: str, binary_col: str) -> Tuple[Optional[float], Optional[float]]:
        try:
            df_clean = self.df.select([numeric_col, binary_col]).drop_nulls()
            
            if len(df_clean) < 2:
                return None, None
            
            x = df_clean[numeric_col].to_numpy().astype(float)
            
            y_series = df_clean[binary_col]
            unique_vals = y_series.unique().to_list()
            
            if len(unique_vals) != 2:
                return None, None
            
            y = (y_series == unique_vals[1]).to_numpy().astype(int)
            
            if np.std(x) == 0:
                return None, None
            
            corr, p_value = pointbiserialr(y, x)
            
            if np.isnan(corr):
                return None, None
            
            return float(corr), float(p_value)
        except Exception:
            return None, None
    
    def get_correlation_matrix(self, method: str = 'pearson') -> Dict[str, Any]:
        numeric_cols = self._get_numeric_columns()
        
        if not numeric_cols:
            return {'columns': [], 'matrix': []}
        
        n = len(numeric_cols)
        matrix = np.eye(n)
        
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                if i < j:
                    if method == 'pearson':
                        corr, _ = self._pearson_correlation(col1, col2)
                    elif method == 'spearman':
                        corr, _ = self._spearman_correlation(col1, col2)
                    else:
                        corr = None
                    
                    if corr is not None:
                        matrix[i, j] = corr
                        matrix[j, i] = corr
        
        return {
            'columns': numeric_cols,
            'matrix': matrix.tolist()
        }
    
    def get_top_correlations(self, n: int = 10, min_correlation: float = 0.0) -> List[CorrelationPair]:
        all_correlations = self.analyze_all()
        
        all_pairs = []
        for corr_dict in [all_correlations['pearson'], all_correlations['spearman'], all_correlations['cramers_v'], all_correlations['mixed']]:
            all_pairs.extend(corr_dict.values())
        
        filtered = [pair for pair in all_pairs if abs(pair.correlation) >= min_correlation]
        
        sorted_pairs = sorted(filtered, key=lambda x: abs(x.correlation), reverse=True)
        
        return sorted_pairs[:n]


def analyze_correlations(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = CorrelationAnalyzer(df)
    return analyzer.analyze_all()


def get_correlation_matrix(df: pl.DataFrame, method: str = 'pearson') -> Dict[str, Any]:
    analyzer = CorrelationAnalyzer(df)
    return analyzer.get_correlation_matrix(method=method)


def get_top_correlations(df: pl.DataFrame, n: int = 10, min_correlation: float = 0.5) -> List[CorrelationPair]:
    analyzer = CorrelationAnalyzer(df)
    return analyzer.get_top_correlations(n=n, min_correlation=min_correlation)


def get_correlation_for_columns(df: pl.DataFrame, col1: str, col2: str) -> Dict[str, Any]:
    analyzer = CorrelationAnalyzer(df)
    
    if col1 not in df.columns or col2 not in df.columns:
        return {'error': 'One or both columns not found'}
    
    dtype1 = str(df[col1].dtype)
    dtype2 = str(df[col2].dtype)
    
    is_numeric1 = any(t in dtype1 for t in ['Int', 'UInt', 'Float'])
    is_numeric2 = any(t in dtype2 for t in ['Int', 'UInt', 'Float'])
    
    result = {}
    
    if is_numeric1 and is_numeric2:
        pearson, p_pearson = analyzer._pearson_correlation(col1, col2)
        spearman, p_spearman = analyzer._spearman_correlation(col1, col2)
        
        result['pearson'] = {
            'correlation': pearson,
            'p_value': p_pearson
        }
        result['spearman'] = {
            'correlation': spearman,
            'p_value': p_spearman
        }
    elif not is_numeric1 and not is_numeric2:
        cramers = analyzer._cramers_v(col1, col2)
        result['cramers_v'] = {
            'correlation': cramers
        }
    elif is_numeric1 and analyzer._is_binary(col2):
        pb_corr, pb_p = analyzer._point_biserial(col1, col2)
        result['point_biserial'] = {
            'correlation': pb_corr,
            'p_value': pb_p
        }
    elif is_numeric2 and analyzer._is_binary(col1):
        pb_corr, pb_p = analyzer._point_biserial(col2, col1)
        result['point_biserial'] = {
            'correlation': pb_corr,
            'p_value': pb_p
        }
    else:
        result['error'] = 'No appropriate correlation method for these column types'
    
    return result