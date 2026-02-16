import polars as pl
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from scipy import stats
from scipy.stats import shapiro, anderson, kstest, normaltest


@dataclass
class DistributionInfo:
    column_name: str
    histogram: Dict[str, Any]
    kde_available: bool
    normality_tests: Dict[str, Any]
    distribution_type: str
    skewness: float
    kurtosis: float
    is_normal: bool
    quartiles: Dict[str, float]


class DistributionAnalyzer:
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_rows = len(df)
    
    def analyze_all(self, bins: int = 30) -> Dict[str, DistributionInfo]:
        distributions = {}
        
        numeric_cols = self._get_numeric_columns()
        
        for col in numeric_cols:
            distributions[col] = self._analyze_column(col, bins=bins)
        
        return distributions
    
    def _get_numeric_columns(self) -> List[str]:
        numeric_cols = []
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if any(t in dtype for t in ['Int', 'UInt', 'Float']):
                numeric_cols.append(col)
        return numeric_cols
    
    def _analyze_column(self, column: str, bins: int = 30) -> DistributionInfo:
        series = self.df[column].drop_nulls()
        
        if len(series) == 0:
            return self._empty_distribution(column)
        
        histogram = self._calculate_histogram(series, bins=bins)
        normality_tests = self._test_normality(series)
        distribution_type = self._detect_distribution_type(series, normality_tests)
        
        skewness = self._calculate_skewness(series)
        kurtosis = self._calculate_kurtosis(series)
        
        is_normal = normality_tests.get('is_normal', False)
        
        quartiles = self._calculate_quartiles(series)
        
        kde_available = len(series) > 10
        
        return DistributionInfo(
            column_name=column,
            histogram=histogram,
            kde_available=kde_available,
            normality_tests=normality_tests,
            distribution_type=distribution_type,
            skewness=skewness,
            kurtosis=kurtosis,
            is_normal=is_normal,
            quartiles=quartiles
        )
    
    def _empty_distribution(self, column: str) -> DistributionInfo:
        return DistributionInfo(
            column_name=column,
            histogram={'bins': [], 'counts': [], 'edges': []},
            kde_available=False,
            normality_tests={},
            distribution_type='unknown',
            skewness=0.0,
            kurtosis=0.0,
            is_normal=False,
            quartiles={}
        )
    
    def _calculate_histogram(self, series: pl.Series, bins: int = 30) -> Dict[str, Any]:
        data = series.to_numpy().astype(float)
        
        counts, edges = np.histogram(data, bins=bins)
        
        bin_centers = (edges[:-1] + edges[1:]) / 2
        
        return {
            'counts': counts.tolist(),
            'edges': edges.tolist(),
            'bin_centers': bin_centers.tolist(),
            'bin_width': float(edges[1] - edges[0]) if len(edges) > 1 else 0.0,
            'total_count': int(counts.sum())
        }
    
    def _test_normality(self, series: pl.Series) -> Dict[str, Any]:
        data = series.to_numpy().astype(float)
        
        if len(data) < 3:
            return {'is_normal': False, 'reason': 'insufficient_data'}
        
        results = {}
        
        try:
            if len(data) <= 5000:
                stat, p_value = shapiro(data)
                results['shapiro_wilk'] = {
                    'statistic': float(stat),
                    'p_value': float(p_value),
                    'is_normal': p_value > 0.05
                }
        except Exception:
            results['shapiro_wilk'] = None
        
        try:
            result = anderson(data, dist='norm', method='interpolate')
            critical_value = result.critical_values[2]
            results['anderson_darling'] = {
                'statistic': float(result.statistic),
                'critical_value': float(critical_value),
                'is_normal': result.statistic < critical_value
            }
        except Exception:
            results['anderson_darling'] = None
        
        try:
            if len(data) >= 8:
                stat, p_value = normaltest(data)
                results['dagostino_pearson'] = {
                    'statistic': float(stat),
                    'p_value': float(p_value),
                    'is_normal': p_value > 0.05
                }
        except Exception:
            results['dagostino_pearson'] = None
        
        try:
            stat, p_value = kstest(data, 'norm', args=(np.mean(data), np.std(data)))
            results['kolmogorov_smirnov'] = {
                'statistic': float(stat),
                'p_value': float(p_value),
                'is_normal': p_value > 0.05
            }
        except Exception:
            results['kolmogorov_smirnov'] = None
        
        normal_votes = sum([
            test.get('is_normal', False) 
            for test in results.values() 
            if test is not None and isinstance(test, dict)
        ])
        total_tests = sum([1 for test in results.values() if test is not None])
        
        results['is_normal'] = (normal_votes / total_tests) >= 0.5 if total_tests > 0 else False
        results['normal_test_count'] = total_tests
        results['normal_votes'] = normal_votes
        
        return results
    
    def _detect_distribution_type(self, series: pl.Series, normality_tests: Dict[str, Any]) -> str:
        data = series.to_numpy().astype(float)
        
        if len(data) < 10:
            return 'unknown'
        
        if normality_tests.get('is_normal', False):
            return 'normal'
        
        skew = float(stats.skew(data))
        kurt = float(stats.kurtosis(data))
        
        if abs(skew) < 0.5 and abs(kurt) < 0.5:
            return 'approximately_normal'
        
        if skew > 1.0:
            return 'right_skewed'
        elif skew < -1.0:
            return 'left_skewed'
        
        if kurt > 3:
            return 'heavy_tailed'
        elif kurt < -1:
            return 'light_tailed'
        
        unique_count = len(np.unique(data))
        if unique_count < 10:
            return 'discrete'
        
        range_val = np.max(data) - np.min(data)
        std_val = np.std(data)
        cv = std_val / np.mean(data) if np.mean(data) != 0 else 0
        
        if cv < 0.1:
            return 'uniform'
        
        if len(data[data < 0]) == 0 and skew > 0.5:
            return 'exponential'
        
        return 'unknown'
    
    def _calculate_skewness(self, series: pl.Series) -> float:
        data = series.to_numpy().astype(float)
        
        if len(data) < 3:
            return 0.0
        
        try:
            return float(stats.skew(data))
        except Exception:
            return 0.0
    
    def _calculate_kurtosis(self, series: pl.Series) -> float:
        data = series.to_numpy().astype(float)
        
        if len(data) < 4:
            return 0.0
        
        try:
            return float(stats.kurtosis(data))
        except Exception:
            return 0.0
    
    def _calculate_quartiles(self, series: pl.Series) -> Dict[str, float]:
        try:
            q0 = float(series.min())
            q25 = float(series.quantile(0.25, interpolation='linear'))
            q50 = float(series.quantile(0.50, interpolation='linear'))
            q75 = float(series.quantile(0.75, interpolation='linear'))
            q100 = float(series.max())
            
            return {
                'min': q0,
                'q25': q25,
                'median': q50,
                'q75': q75,
                'max': q100,
                'iqr': q75 - q25
            }
        except Exception:
            return {}
    
    def calculate_kde(self, column: str, num_points: int = 100) -> Optional[Dict[str, List[float]]]:
        if column not in self.df.columns:
            return None
        
        series = self.df[column].drop_nulls()
        
        if len(series) < 10:
            return None
        
        data = series.to_numpy().astype(float)
        
        try:
            kde = stats.gaussian_kde(data)
            
            x_min, x_max = data.min(), data.max()
            padding = (x_max - x_min) * 0.1
            x_range = np.linspace(x_min - padding, x_max + padding, num_points)
            
            y_values = kde(x_range)
            
            return {
                'x': x_range.tolist(),
                'y': y_values.tolist()
            }
        except Exception:
            return None
    
    def fit_distribution(self, column: str, dist_name: str = 'norm') -> Optional[Dict[str, Any]]:
        if column not in self.df.columns:
            return None
        
        series = self.df[column].drop_nulls()
        
        if len(series) < 10:
            return None
        
        data = series.to_numpy().astype(float)
        
        try:
            if dist_name == 'norm':
                params = stats.norm.fit(data)
                dist = stats.norm(*params)
            elif dist_name == 'expon':
                params = stats.expon.fit(data)
                dist = stats.expon(*params)
            elif dist_name == 'uniform':
                params = stats.uniform.fit(data)
                dist = stats.uniform(*params)
            elif dist_name == 'gamma':
                params = stats.gamma.fit(data)
                dist = stats.gamma(*params)
            else:
                return None
            
            ks_stat, ks_pvalue = stats.kstest(data, dist.cdf)
            
            return {
                'distribution': dist_name,
                'parameters': params,
                'ks_statistic': float(ks_stat),
                'ks_pvalue': float(ks_pvalue),
                'goodness_of_fit': 'good' if ks_pvalue > 0.05 else 'poor'
            }
        except Exception:
            return None
    
    def get_distribution_summary(self) -> Dict[str, Any]:
        distributions = self.analyze_all()
        
        normal_cols = [col for col, info in distributions.items() if info.is_normal]
        skewed_cols = [col for col, info in distributions.items() if abs(info.skewness) > 1.0]
        heavy_tailed_cols = [col for col, info in distributions.items() if info.kurtosis > 3]
        
        distribution_types = {}
        for col, info in distributions.items():
            dist_type = info.distribution_type
            distribution_types[dist_type] = distribution_types.get(dist_type, 0) + 1
        
        return {
            'total_numeric_columns': len(distributions),
            'normal_columns': normal_cols,
            'skewed_columns': skewed_cols,
            'heavy_tailed_columns': heavy_tailed_cols,
            'distribution_type_counts': distribution_types,
            'distributions': distributions
        }


def analyze_distributions(df: pl.DataFrame, bins: int = 30) -> Dict[str, DistributionInfo]:
    analyzer = DistributionAnalyzer(df)
    return analyzer.analyze_all(bins=bins)


def get_distribution_summary(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = DistributionAnalyzer(df)
    return analyzer.get_distribution_summary()


def get_histogram(df: pl.DataFrame, column: str, bins: int = 30) -> Optional[Dict[str, Any]]:
    analyzer = DistributionAnalyzer(df)
    
    if column not in df.columns:
        return None
    
    dtype = str(df[column].dtype)
    if not any(t in dtype for t in ['Int', 'UInt', 'Float']):
        return None
    
    info = analyzer._analyze_column(column, bins=bins)
    return info.histogram


def get_kde(df: pl.DataFrame, column: str, num_points: int = 100) -> Optional[Dict[str, List[float]]]:
    analyzer = DistributionAnalyzer(df)
    return analyzer.calculate_kde(column, num_points=num_points)


def test_normality(df: pl.DataFrame, column: str) -> Optional[Dict[str, Any]]:
    analyzer = DistributionAnalyzer(df)
    
    if column not in df.columns:
        return None
    
    dtype = str(df[column].dtype)
    if not any(t in dtype for t in ['Int', 'UInt', 'Float']):
        return None
    
    series = df[column].drop_nulls()
    return analyzer._test_normality(series)