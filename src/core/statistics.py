import polars as pl
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import math


@dataclass
class NumericStats:
    count: int
    null_count: int
    mean: float
    median: float
    mode: Optional[float]
    std: float
    variance: float
    min: float
    max: float
    range: float
    q25: float
    q50: float
    q75: float
    iqr: float
    skewness: float
    kurtosis: float
    cv: float
    sum: float
    zero_count: int
    negative_count: int
    positive_count: int


@dataclass
class CategoricalStats:
    count: int
    null_count: int
    unique_count: int
    mode: Optional[str]
    mode_frequency: int
    mode_percentage: float
    top_values: List[tuple]
    entropy: float
    is_unique: bool


@dataclass
class DatetimeStats:
    count: int
    null_count: int
    min: Any
    max: Any
    range_days: Optional[float]
    mode: Optional[Any]
    unique_count: int


@dataclass
class TextStats:
    count: int
    null_count: int
    unique_count: int
    mode: Optional[str]
    avg_length: float
    min_length: int
    max_length: int
    empty_count: int
    top_values: List[tuple]


class StatisticsAnalyzer:
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_rows = len(df)
    
    def analyze_all(self) -> Dict[str, Any]:
        stats = {}
        for col in self.df.columns:
            stats[col] = self.analyze_column(col)
        return stats
    
    def analyze_column(self, column: str) -> Dict[str, Any]:
        series = self.df[column]
        dtype = str(series.dtype)
        
        if self._is_numeric(dtype):
            return self._analyze_numeric(series)
        elif self._is_datetime(dtype):
            return self._analyze_datetime(series)
        elif self._is_categorical(series):
            return self._analyze_categorical(series)
        else:
            return self._analyze_text(series)
    
    def _is_numeric(self, dtype: str) -> bool:
        return any(t in dtype for t in ['Int', 'UInt', 'Float'])
    
    def _is_datetime(self, dtype: str) -> bool:
        return any(t in dtype for t in ['Date', 'Datetime', 'Time'])
    
    def _is_categorical(self, series: pl.Series) -> bool:
        if 'Categorical' in str(series.dtype):
            return True
        
        non_null = series.drop_nulls()
        if len(non_null) == 0:
            return False
        
        unique_ratio = non_null.n_unique() / len(non_null)
        return unique_ratio <= 0.05
    
    def _analyze_numeric(self, series: pl.Series) -> NumericStats:
        non_null = series.drop_nulls()
        count = len(non_null)
        null_count = series.null_count()
        
        if count == 0:
            return NumericStats(
                count=0,
                null_count=null_count,
                mean=0.0,
                median=0.0,
                mode=None,
                std=0.0,
                variance=0.0,
                min=0.0,
                max=0.0,
                range=0.0,
                q25=0.0,
                q50=0.0,
                q75=0.0,
                iqr=0.0,
                skewness=0.0,
                kurtosis=0.0,
                cv=0.0,
                sum=0.0,
                zero_count=0,
                negative_count=0,
                positive_count=0
            )
        
        mean = float(non_null.mean())
        median = float(non_null.median())
        std = float(non_null.std())
        variance = float(non_null.var())
        min_val = float(non_null.min())
        max_val = float(non_null.max())
        range_val = max_val - min_val
        total_sum = float(non_null.sum())
        
        quantiles = non_null.quantile([0.25, 0.5, 0.75], interpolation='linear')
        q25 = float(quantiles[0])
        q50 = float(quantiles[1])
        q75 = float(quantiles[2])
        iqr = q75 - q25
        
        mode_val = self._calculate_mode(non_null)
        
        skewness = self._calculate_skewness(non_null, mean, std, count)
        kurtosis = self._calculate_kurtosis(non_null, mean, std, count)
        
        cv = (std / mean) if mean != 0 else 0.0
        
        zero_count = int((non_null == 0).sum())
        negative_count = int((non_null < 0).sum())
        positive_count = int((non_null > 0).sum())
        
        return NumericStats(
            count=count,
            null_count=null_count,
            mean=mean,
            median=median,
            mode=mode_val,
            std=std,
            variance=variance,
            min=min_val,
            max=max_val,
            range=range_val,
            q25=q25,
            q50=q50,
            q75=q75,
            iqr=iqr,
            skewness=skewness,
            kurtosis=kurtosis,
            cv=cv,
            sum=total_sum,
            zero_count=zero_count,
            negative_count=negative_count,
            positive_count=positive_count
        )
    
    def _analyze_categorical(self, series: pl.Series) -> CategoricalStats:
        non_null = series.drop_nulls()
        count = len(non_null)
        null_count = series.null_count()
        unique_count = non_null.n_unique()
        
        if count == 0:
            return CategoricalStats(
                count=0,
                null_count=null_count,
                unique_count=0,
                mode=None,
                mode_frequency=0,
                mode_percentage=0.0,
                top_values=[],
                entropy=0.0,
                is_unique=False
            )
        
        value_counts = non_null.value_counts().sort('count', descending=True)
        
        mode = None
        mode_frequency = 0
        mode_percentage = 0.0
        
        if len(value_counts) > 0:
            mode_row = value_counts.row(0)
            mode = str(mode_row[0])
            mode_frequency = int(mode_row[1])
            mode_percentage = (mode_frequency / count) * 100
        
        top_values = []
        for i in range(min(10, len(value_counts))):
            row = value_counts.row(i)
            value = str(row[0])
            freq = int(row[1])
            pct = (freq / count) * 100
            top_values.append((value, freq, pct))
        
        entropy = self._calculate_entropy(value_counts['count'].to_list(), count)
        
        is_unique = (unique_count == count)
        
        return CategoricalStats(
            count=count,
            null_count=null_count,
            unique_count=unique_count,
            mode=mode,
            mode_frequency=mode_frequency,
            mode_percentage=mode_percentage,
            top_values=top_values,
            entropy=entropy,
            is_unique=is_unique
        )
    
    def _analyze_datetime(self, series: pl.Series) -> DatetimeStats:
        non_null = series.drop_nulls()
        count = len(non_null)
        null_count = series.null_count()
        
        if count == 0:
            return DatetimeStats(
                count=0,
                null_count=null_count,
                min=None,
                max=None,
                range_days=None,
                mode=None,
                unique_count=0
            )
        
        min_val = non_null.min()
        max_val = non_null.max()
        unique_count = non_null.n_unique()
        
        range_days = None
        try:
            if min_val and max_val:
                delta = max_val - min_val
                if hasattr(delta, 'days'):
                    range_days = float(delta.days)
                elif hasattr(delta, 'total_seconds'):
                    range_days = delta.total_seconds() / 86400
        except:
            pass
        
        mode_val = self._calculate_mode(non_null)
        
        return DatetimeStats(
            count=count,
            null_count=null_count,
            min=min_val,
            max=max_val,
            range_days=range_days,
            mode=mode_val,
            unique_count=unique_count
        )
    
    def _analyze_text(self, series: pl.Series) -> TextStats:
        non_null = series.drop_nulls()
        count = len(non_null)
        null_count = series.null_count()
        unique_count = non_null.n_unique()
        
        if count == 0:
            return TextStats(
                count=0,
                null_count=null_count,
                unique_count=0,
                mode=None,
                avg_length=0.0,
                min_length=0,
                max_length=0,
                empty_count=0,
                top_values=[]
            )
        
        lengths = non_null.str.len_chars()
        avg_length = float(lengths.mean())
        min_length = int(lengths.min())
        max_length = int(lengths.max())
        
        empty_count = int((lengths == 0).sum())
        
        value_counts = non_null.value_counts().sort('count', descending=True)
        
        mode = None
        if len(value_counts) > 0:
            mode = str(value_counts.row(0)[0])
        
        top_values = []
        for i in range(min(10, len(value_counts))):
            row = value_counts.row(i)
            value = str(row[0])
            freq = int(row[1])
            pct = (freq / count) * 100
            top_values.append((value, freq, pct))
        
        return TextStats(
            count=count,
            null_count=null_count,
            unique_count=unique_count,
            mode=mode,
            avg_length=avg_length,
            min_length=min_length,
            max_length=max_length,
            empty_count=empty_count,
            top_values=top_values
        )
    
    def _calculate_mode(self, series: pl.Series) -> Optional[Any]:
        if len(series) == 0:
            return None
        
        value_counts = series.value_counts()
        if len(value_counts) == 0:
            return None
        
        value_counts = value_counts.sort('count', descending=True)
        mode_val = value_counts.row(0)[0]
        
        return mode_val
    
    def _calculate_skewness(self, series: pl.Series, mean: float, std: float, n: int) -> float:
        if n < 3 or std == 0:
            return 0.0
        
        try:
            m3 = ((series - mean) ** 3).mean()
            skew = float(m3 / (std ** 3))
            return skew
        except:
            return 0.0
    
    def _calculate_kurtosis(self, series: pl.Series, mean: float, std: float, n: int) -> float:
        if n < 4 or std == 0:
            return 0.0
        
        try:
            m4 = ((series - mean) ** 4).mean()
            kurt = float(m4 / (std ** 4)) - 3.0
            return kurt
        except:
            return 0.0
    
    def _calculate_entropy(self, counts: List[int], total: int) -> float:
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in counts:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        return entropy
    
    def get_summary(self) -> Dict[str, Any]:
        all_stats = self.analyze_all()
        
        numeric_cols = []
        categorical_cols = []
        datetime_cols = []
        text_cols = []
        
        for col, stats in all_stats.items():
            if isinstance(stats, NumericStats):
                numeric_cols.append(col)
            elif isinstance(stats, CategoricalStats):
                categorical_cols.append(col)
            elif isinstance(stats, DatetimeStats):
                datetime_cols.append(col)
            elif isinstance(stats, TextStats):
                text_cols.append(col)
        
        return {
            'total_columns': len(all_stats),
            'numeric_columns': numeric_cols,
            'categorical_columns': categorical_cols,
            'datetime_columns': datetime_cols,
            'text_columns': text_cols,
            'statistics': all_stats
        }


def analyze_statistics(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = StatisticsAnalyzer(df)
    return analyzer.analyze_all()


def get_statistics_summary(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = StatisticsAnalyzer(df)
    return analyzer.get_summary()