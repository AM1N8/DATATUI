import polars as pl
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest


@dataclass
class OutlierInfo:
    column_name: str
    total_count: int
    iqr_outliers: List[int]
    iqr_outlier_count: int
    iqr_lower_bound: float
    iqr_upper_bound: float
    zscore_outliers: List[int]
    zscore_outlier_count: int
    zscore_threshold: float
    mad_outliers: List[int]
    mad_outlier_count: int
    mad_threshold: float
    outlier_percentage: float
    outlier_values: List[float]


@dataclass
class MultivariatOutlierInfo:
    total_count: int
    outlier_indices: List[int]
    outlier_count: int
    outlier_percentage: float
    contamination: float


class OutlierDetector:
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_rows = len(df)
    
    def detect_all(self, zscore_threshold: float = 3.0, mad_threshold: float = 3.5) -> Dict[str, OutlierInfo]:
        outliers = {}
        
        numeric_cols = self._get_numeric_columns()
        
        for col in numeric_cols:
            outliers[col] = self._detect_column_outliers(
                col, 
                zscore_threshold=zscore_threshold,
                mad_threshold=mad_threshold
            )
        
        return outliers
    
    def _get_numeric_columns(self) -> List[str]:
        numeric_cols = []
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if any(t in dtype for t in ['Int', 'UInt', 'Float']):
                numeric_cols.append(col)
        return numeric_cols
    
    def _detect_column_outliers(
        self, 
        column: str, 
        zscore_threshold: float = 3.0,
        mad_threshold: float = 3.5
    ) -> OutlierInfo:
        series = self.df[column].drop_nulls()
        
        if len(series) == 0:
            return OutlierInfo(
                column_name=column,
                total_count=0,
                iqr_outliers=[],
                iqr_outlier_count=0,
                iqr_lower_bound=0.0,
                iqr_upper_bound=0.0,
                zscore_outliers=[],
                zscore_outlier_count=0,
                zscore_threshold=zscore_threshold,
                mad_outliers=[],
                mad_outlier_count=0,
                mad_threshold=mad_threshold,
                outlier_percentage=0.0,
                outlier_values=[]
            )
        
        iqr_outliers, iqr_lower, iqr_upper = self._detect_iqr_outliers(series)
        zscore_outliers = self._detect_zscore_outliers(series, threshold=zscore_threshold)
        mad_outliers = self._detect_mad_outliers(series, threshold=mad_threshold)
        
        all_outlier_indices = set(iqr_outliers + zscore_outliers + mad_outliers)
        outlier_percentage = (len(all_outlier_indices) / len(series) * 100) if len(series) > 0 else 0.0
        
        outlier_values = []
        if all_outlier_indices:
            for idx in sorted(list(all_outlier_indices))[:100]:
                if idx < len(series):
                    outlier_values.append(float(series[idx]))
        
        return OutlierInfo(
            column_name=column,
            total_count=len(series),
            iqr_outliers=iqr_outliers[:1000],
            iqr_outlier_count=len(iqr_outliers),
            iqr_lower_bound=iqr_lower,
            iqr_upper_bound=iqr_upper,
            zscore_outliers=zscore_outliers[:1000],
            zscore_outlier_count=len(zscore_outliers),
            zscore_threshold=zscore_threshold,
            mad_outliers=mad_outliers[:1000],
            mad_outlier_count=len(mad_outliers),
            mad_threshold=mad_threshold,
            outlier_percentage=outlier_percentage,
            outlier_values=outlier_values[:100]
        )
    
    def _detect_iqr_outliers(self, series: pl.Series) -> tuple[List[int], float, float]:
        q1 = float(series.quantile(0.25, interpolation='linear'))
        q3 = float(series.quantile(0.75, interpolation='linear'))
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outlier_mask = (series < lower_bound) | (series > upper_bound)
        outlier_indices = [i for i, is_outlier in enumerate(outlier_mask.to_list()) if is_outlier]
        
        return outlier_indices, lower_bound, upper_bound
    
    def _detect_zscore_outliers(self, series: pl.Series, threshold: float = 3.0) -> List[int]:
        mean = float(series.mean())
        std = float(series.std())
        
        if std == 0:
            return []
        
        zscores = ((series - mean) / std).abs()
        outlier_mask = zscores > threshold
        outlier_indices = [i for i, is_outlier in enumerate(outlier_mask.to_list()) if is_outlier]
        
        return outlier_indices
    
    def _detect_mad_outliers(self, series: pl.Series, threshold: float = 3.5) -> List[int]:
        median = float(series.median())
        
        deviations = (series - median).abs()
        mad = float(deviations.median())
        
        if mad == 0:
            return []
        
        modified_zscores = (0.6745 * deviations / mad)
        outlier_mask = modified_zscores > threshold
        outlier_indices = [i for i, is_outlier in enumerate(outlier_mask.to_list()) if is_outlier]
        
        return outlier_indices
    
    def detect_multivariate_outliers(
        self, 
        columns: Optional[List[str]] = None,
        contamination: float = 0.1,
        random_state: int = 42
    ) -> MultivariatOutlierInfo:
        if columns is None:
            columns = self._get_numeric_columns()
        
        if not columns:
            return MultivariatOutlierInfo(
                total_count=self.total_rows,
                outlier_indices=[],
                outlier_count=0,
                outlier_percentage=0.0,
                contamination=contamination
            )
        
        df_subset = self.df.select(columns).drop_nulls()
        
        if len(df_subset) == 0:
            return MultivariatOutlierInfo(
                total_count=0,
                outlier_indices=[],
                outlier_count=0,
                outlier_percentage=0.0,
                contamination=contamination
            )
        
        X = df_subset.to_numpy()
        
        if X.shape[0] < 2:
            return MultivariatOutlierInfo(
                total_count=len(df_subset),
                outlier_indices=[],
                outlier_count=0,
                outlier_percentage=0.0,
                contamination=contamination
            )
        
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1
        )
        
        predictions = iso_forest.fit_predict(X)
        
        outlier_indices = [i for i, pred in enumerate(predictions) if pred == -1]
        outlier_count = len(outlier_indices)
        outlier_percentage = (outlier_count / len(df_subset) * 100) if len(df_subset) > 0 else 0.0
        
        return MultivariatOutlierInfo(
            total_count=len(df_subset),
            outlier_indices=outlier_indices[:1000],
            outlier_count=outlier_count,
            outlier_percentage=outlier_percentage,
            contamination=contamination
        )
    
    def get_outlier_summary(self) -> Dict[str, Any]:
        outliers = self.detect_all()
        
        columns_with_outliers = [
            col for col, info in outliers.items() 
            if info.iqr_outlier_count > 0 or info.zscore_outlier_count > 0
        ]
        
        total_outliers = sum(
            len(set(info.iqr_outliers + info.zscore_outliers + info.mad_outliers))
            for info in outliers.values()
        )
        
        high_outlier_cols = [
            (col, info.outlier_percentage)
            for col, info in outliers.items()
            if info.outlier_percentage > 5
        ]
        
        return {
            'total_numeric_columns': len(outliers),
            'columns_with_outliers': columns_with_outliers,
            'columns_with_outliers_count': len(columns_with_outliers),
            'total_outlier_detections': total_outliers,
            'high_outlier_columns': sorted(high_outlier_cols, key=lambda x: x[1], reverse=True),
            'outliers_by_column': outliers
        }


def detect_outliers(df: pl.DataFrame) -> Dict[str, OutlierInfo]:
    detector = OutlierDetector(df)
    return detector.detect_all()


def detect_multivariate_outliers(
    df: pl.DataFrame, 
    columns: Optional[List[str]] = None,
    contamination: float = 0.1
) -> MultivariatOutlierInfo:
    detector = OutlierDetector(df)
    return detector.detect_multivariate_outliers(columns=columns, contamination=contamination)


def get_outlier_summary(df: pl.DataFrame) -> Dict[str, Any]:
    detector = OutlierDetector(df)
    return detector.get_outlier_summary()


def get_outliers_for_column(df: pl.DataFrame, column: str) -> Dict[str, Any]:
    detector = OutlierDetector(df)
    
    if column not in df.columns:
        return {'error': f'Column {column} not found'}
    
    dtype = str(df[column].dtype)
    if not any(t in dtype for t in ['Int', 'UInt', 'Float']):
        return {'error': f'Column {column} is not numeric'}
    
    info = detector._detect_column_outliers(column)
    
    return {
        'column': column,
        'total_count': info.total_count,
        'iqr': {
            'count': info.iqr_outlier_count,
            'percentage': (info.iqr_outlier_count / info.total_count * 100) if info.total_count > 0 else 0,
            'lower_bound': info.iqr_lower_bound,
            'upper_bound': info.iqr_upper_bound,
            'indices': info.iqr_outliers[:100]
        },
        'zscore': {
            'count': info.zscore_outlier_count,
            'percentage': (info.zscore_outlier_count / info.total_count * 100) if info.total_count > 0 else 0,
            'threshold': info.zscore_threshold,
            'indices': info.zscore_outliers[:100]
        },
        'mad': {
            'count': info.mad_outlier_count,
            'percentage': (info.mad_outlier_count / info.total_count * 100) if info.total_count > 0 else 0,
            'threshold': info.mad_threshold,
            'indices': info.mad_outliers[:100]
        },
        'outlier_values': info.outlier_values
    }