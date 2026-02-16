import polars as pl
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import Counter


@dataclass
class ColumnMissingInfo:
    column_name: str
    missing_count: int
    present_count: int
    missing_percentage: float
    total_count: int


@dataclass
class MissingPattern:
    columns: List[str]
    count: int
    percentage: float


class MissingAnalyzer:
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_rows = len(df)
    
    def analyze_missing(self) -> Dict[str, Any]:
        column_info = self._analyze_columns()
        patterns = self._detect_patterns()
        matrix = self._create_missing_matrix()
        
        total_missing = sum(info.missing_count for info in column_info.values())
        columns_with_missing = [
            col for col, info in column_info.items() 
            if info.missing_count > 0
        ]
        
        total_cells = self.total_rows * len(self.df.columns)
        overall_missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0.0
        
        complete_rows = self._count_complete_rows()
        complete_rows_pct = (complete_rows / self.total_rows * 100) if self.total_rows > 0 else 0.0
        
        return {
            'columns': column_info,
            'total_missing_values': total_missing,
            'total_cells': total_cells,
            'overall_missing_percentage': overall_missing_pct,
            'columns_with_missing': columns_with_missing,
            'columns_count': len(self.df.columns),
            'complete_rows': complete_rows,
            'complete_rows_percentage': complete_rows_pct,
            'incomplete_rows': self.total_rows - complete_rows,
            'patterns': patterns,
            'missing_matrix': matrix
        }
    
    def _analyze_columns(self) -> Dict[str, ColumnMissingInfo]:
        column_info = {}
        
        for col in self.df.columns:
            missing_count = self.df[col].null_count()
            present_count = self.total_rows - missing_count
            missing_pct = (missing_count / self.total_rows * 100) if self.total_rows > 0 else 0.0
            
            column_info[col] = ColumnMissingInfo(
                column_name=col,
                missing_count=missing_count,
                present_count=present_count,
                missing_percentage=missing_pct,
                total_count=self.total_rows
            )
        
        return column_info
    
    def _detect_patterns(self, max_patterns: int = 20) -> List[MissingPattern]:
        if self.total_rows == 0:
            return []
        
        null_df = self.df.select([
            pl.col(col).is_null().alias(col) 
            for col in self.df.columns
        ])
        
        pattern_rows = []
        for row in null_df.iter_rows():
            missing_cols = tuple(
                col for col, is_null in zip(self.df.columns, row) 
                if is_null
            )
            if missing_cols:
                pattern_rows.append(missing_cols)
        
        pattern_counts = Counter(pattern_rows)
        
        patterns = []
        for pattern_tuple, count in pattern_counts.most_common(max_patterns):
            percentage = (count / self.total_rows * 100)
            patterns.append(MissingPattern(
                columns=list(pattern_tuple),
                count=count,
                percentage=percentage
            ))
        
        return patterns
    
    def _create_missing_matrix(self) -> List[List[bool]]:
        if self.total_rows == 0 or len(self.df.columns) == 0:
            return []
        
        sample_size = min(1000, self.total_rows)
        
        sampled_df = self.df.head(sample_size)
        
        null_df = sampled_df.select([
            pl.col(col).is_null().alias(col) 
            for col in sampled_df.columns
        ])
        
        matrix = []
        for row in null_df.iter_rows():
            matrix.append(list(row))
        
        return matrix
    
    def _count_complete_rows(self) -> int:
        if len(self.df.columns) == 0:
            return self.total_rows
        
        complete_mask = pl.lit(True)
        for col in self.df.columns:
            complete_mask = complete_mask & pl.col(col).is_not_null()
        
        complete_count = self.df.select(complete_mask.alias('complete')).sum().item()
        
        return int(complete_count)
    
    def get_missing_summary(self) -> Dict[str, Any]:
        analysis = self.analyze_missing()
        
        sorted_columns = sorted(
            analysis['columns'].items(),
            key=lambda x: x[1].missing_percentage,
            reverse=True
        )
        
        high_missing = [
            (col, info.missing_percentage) 
            for col, info in sorted_columns 
            if info.missing_percentage > 50
        ]
        
        medium_missing = [
            (col, info.missing_percentage) 
            for col, info in sorted_columns 
            if 10 < info.missing_percentage <= 50
        ]
        
        low_missing = [
            (col, info.missing_percentage) 
            for col, info in sorted_columns 
            if 0 < info.missing_percentage <= 10
        ]
        
        return {
            'overall_missing_percentage': analysis['overall_missing_percentage'],
            'complete_rows_percentage': analysis['complete_rows_percentage'],
            'columns_with_missing_count': len(analysis['columns_with_missing']),
            'high_missing_columns': high_missing,
            'medium_missing_columns': medium_missing,
            'low_missing_columns': low_missing,
            'top_patterns': analysis['patterns'][:5]
        }
    
    def get_correlation_with_missing(self, target_column: str) -> Dict[str, float]:
        if target_column not in self.df.columns:
            return {}
        
        target_is_null = self.df.select(
            pl.col(target_column).is_null().cast(pl.Float64).alias('target_null')
        )['target_null']
        
        correlations = {}
        
        for col in self.df.columns:
            if col == target_column:
                continue
            
            col_is_null = self.df.select(
                pl.col(col).is_null().cast(pl.Float64).alias('col_null')
            )['col_null']
            
            try:
                corr_df = pl.DataFrame({
                    'target': target_is_null,
                    'col': col_is_null
                })
                
                corr = corr_df.select(
                    pl.corr('target', 'col').alias('correlation')
                )['correlation'][0]
                
                if corr is not None and not (isinstance(corr, float) and (corr != corr)):
                    correlations[col] = float(corr)
            except:
                continue
        
        return correlations


def analyze_missing(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = MissingAnalyzer(df)
    return analyzer.analyze_missing()


def get_missing_summary(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = MissingAnalyzer(df)
    return analyzer.get_missing_summary()


def get_missing_heatmap_data(df: pl.DataFrame, sample_size: int = 1000) -> Dict[str, Any]:
    analyzer = MissingAnalyzer(df)
    analysis = analyzer.analyze_missing()
    
    sample = min(sample_size, len(df))
    
    return {
        'columns': df.columns,
        'matrix': analysis['missing_matrix'][:sample],
        'column_missing_pct': {
            col: info.missing_percentage 
            for col, info in analysis['columns'].items()
        }
    }


def detect_missing_type(df: pl.DataFrame, column: str) -> str:
    analyzer = MissingAnalyzer(df)
    
    if column not in df.columns:
        return "unknown"
    
    col_info = analyzer._analyze_columns()[column]
    
    if col_info.missing_count == 0:
        return "no_missing"
    
    if col_info.missing_percentage == 100:
        return "all_missing"
    
    correlations = analyzer.get_correlation_with_missing(column)
    
    if not correlations:
        return "mcar"
    
    high_corr = [col for col, corr in correlations.items() if abs(corr) > 0.5]
    
    if len(high_corr) > 0:
        return "mar"
    
    return "mcar"