import polars as pl
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import time

from .schema import SchemaDetector
from .statistics import StatisticsAnalyzer
from .missing import MissingAnalyzer
from .outliers import OutlierDetector
from .correlations import CorrelationAnalyzer
from .distributions import DistributionAnalyzer


@dataclass
class AnalysisResult:
    dataset_name: str
    total_rows: int
    total_columns: int
    memory_mb: float
    analysis_time_seconds: float
    schema: Dict[str, Any]
    statistics: Dict[str, Any]
    missing: Dict[str, Any]
    outliers: Dict[str, Any]
    correlations: Dict[str, Any]
    distributions: Dict[str, Any]


class DataAnalyzer:
    
    def __init__(self, df: pl.DataFrame, dataset_name: str = "Dataset"):
        self.df = df
        self.dataset_name = dataset_name
        self.total_rows = len(df)
        self.total_columns = len(df.columns)
        self._cache = {}
    
    def analyze_all(self, skip_multivariate_outliers: bool = False) -> AnalysisResult:
        start_time = time.time()
        
        schema_results = self.analyze_schema()
        statistics_results = self.analyze_statistics()
        missing_results = self.analyze_missing()
        outliers_results = self.analyze_outliers(skip_multivariate=skip_multivariate_outliers)
        correlations_results = self.analyze_correlations()
        distributions_results = self.analyze_distributions()
        
        memory_mb = self._estimate_memory()
        
        analysis_time = time.time() - start_time
        
        return AnalysisResult(
            dataset_name=self.dataset_name,
            total_rows=self.total_rows,
            total_columns=self.total_columns,
            memory_mb=memory_mb,
            analysis_time_seconds=analysis_time,
            schema=schema_results,
            statistics=statistics_results,
            missing=missing_results,
            outliers=outliers_results,
            correlations=correlations_results,
            distributions=distributions_results
        )
    
    def analyze_schema(self) -> Dict[str, Any]:
        if 'schema' in self._cache:
            return self._cache['schema']
        
        detector = SchemaDetector(self.df)
        result = detector.get_schema_summary()
        
        self._cache['schema'] = result
        return result
    
    def analyze_statistics(self) -> Dict[str, Any]:
        if 'statistics' in self._cache:
            return self._cache['statistics']
        
        analyzer = StatisticsAnalyzer(self.df)
        result = analyzer.get_summary()
        
        self._cache['statistics'] = result
        return result
    
    def analyze_missing(self) -> Dict[str, Any]:
        if 'missing' in self._cache:
            return self._cache['missing']
        
        analyzer = MissingAnalyzer(self.df)
        result = analyzer.analyze_missing()
        
        self._cache['missing'] = result
        return result
    
    def analyze_outliers(self, skip_multivariate: bool = False) -> Dict[str, Any]:
        if 'outliers' in self._cache:
            return self._cache['outliers']
        
        detector = OutlierDetector(self.df)
        
        univariate_outliers = detector.detect_all()
        
        multivariate_outliers = None
        if not skip_multivariate:
            numeric_cols = detector._get_numeric_columns()
            if len(numeric_cols) > 1 and self.total_rows < 100000:
                try:
                    multivariate_outliers = detector.detect_multivariate_outliers(
                        columns=numeric_cols,
                        contamination=0.1
                    )
                except Exception:
                    multivariate_outliers = None
        
        result = {
            'univariate': {col: asdict(info) for col, info in univariate_outliers.items()},
            'multivariate': asdict(multivariate_outliers) if multivariate_outliers else None,
            'summary': detector.get_outlier_summary()
        }
        
        self._cache['outliers'] = result
        return result
    
    def analyze_correlations(self) -> Dict[str, Any]:
        if 'correlations' in self._cache:
            return self._cache['correlations']
        
        analyzer = CorrelationAnalyzer(self.df)
        
        all_correlations = analyzer.analyze_all()
        
        pearson_pairs = [
            asdict(pair) for pair in all_correlations['pearson'].values()
        ]
        spearman_pairs = [
            asdict(pair) for pair in all_correlations['spearman'].values()
        ]
        cramers_pairs = [
            asdict(pair) for pair in all_correlations['cramers_v'].values()
        ]
        mixed_pairs = [
            asdict(pair) for pair in all_correlations['mixed'].values()
        ]
        
        top_correlations = [
            asdict(pair) for pair in analyzer.get_top_correlations(n=20, min_correlation=0.3)
        ]
        
        correlation_matrix = analyzer.get_correlation_matrix(method='pearson')
        
        result = {
            'pearson': pearson_pairs,
            'spearman': spearman_pairs,
            'cramers_v': cramers_pairs,
            'mixed': mixed_pairs,
            'top_correlations': top_correlations,
            'correlation_matrix': correlation_matrix,
            'numeric_columns': all_correlations['numeric_columns'],
            'categorical_columns': all_correlations['categorical_columns']
        }
        
        self._cache['correlations'] = result
        return result
    
    def analyze_distributions(self, bins: int = 30) -> Dict[str, Any]:
        if 'distributions' in self._cache:
            return self._cache['distributions']
        
        analyzer = DistributionAnalyzer(self.df)
        
        all_distributions = analyzer.analyze_all(bins=bins)
        
        distributions_dict = {
            col: asdict(info) for col, info in all_distributions.items()
        }
        
        summary = analyzer.get_distribution_summary()
        
        result = {
            'distributions': distributions_dict,
            'summary': {
                'total_numeric_columns': summary['total_numeric_columns'],
                'normal_columns': summary['normal_columns'],
                'skewed_columns': summary['skewed_columns'],
                'heavy_tailed_columns': summary['heavy_tailed_columns'],
                'distribution_type_counts': summary['distribution_type_counts']
            }
        }
        
        self._cache['distributions'] = result
        return result
    
    def _estimate_memory(self) -> float:
        try:
            total_bytes = sum(
                self.df[col].estimated_size() 
                for col in self.df.columns
            )
            return total_bytes / (1024 * 1024)
        except Exception:
            return 0.0
    
    def get_quick_summary(self) -> Dict[str, Any]:
        schema = self.analyze_schema()
        missing = self.analyze_missing()
        
        return {
            'dataset_name': self.dataset_name,
            'rows': self.total_rows,
            'columns': self.total_columns,
            'memory_mb': self._estimate_memory(),
            'column_types': schema.get('type_distribution', {}),
            'missing_percentage': missing.get('overall_missing_percentage', 0.0),
            'complete_rows_percentage': missing.get('complete_rows_percentage', 100.0)
        }
    
    def clear_cache(self):
        self._cache = {}
    
    def get_column_analysis(self, column: str) -> Dict[str, Any]:
        if column not in self.df.columns:
            return {'error': f'Column {column} not found'}
        
        schema = self.analyze_schema()
        statistics = self.analyze_statistics()
        missing = self.analyze_missing()
        outliers = self.analyze_outliers()
        distributions = self.analyze_distributions()
        
        result = {
            'column_name': column,
            'exists': True
        }
        
        if column in schema.get('columns', {}):
            col_schema = schema['columns'][column]
            result['schema'] = asdict(col_schema)
        
        if column in statistics.get('statistics', {}):
            col_stats = statistics['statistics'][column]
            result['statistics'] = asdict(col_stats)
        
        if column in missing.get('columns', {}):
            col_missing = missing['columns'][column]
            result['missing'] = asdict(col_missing)
        
        if column in outliers.get('univariate', {}):
            col_outliers = outliers['univariate'][column]
            result['outliers'] = col_outliers
        
        if column in distributions.get('distributions', {}):
            col_dist = distributions['distributions'][column]
            result['distribution'] = col_dist
        
        return result
    
    def get_data_quality_score(self) -> Dict[str, Any]:
        missing = self.analyze_missing()
        outliers = self.analyze_outliers(skip_multivariate=True)
        schema = self.analyze_schema()
        
        completeness_score = missing.get('complete_rows_percentage', 100.0)
        
        outlier_summary = outliers.get('summary', {})
        total_outlier_pct = 0.0
        if outlier_summary.get('total_numeric_columns', 0) > 0:
            outliers_by_col = outlier_summary.get('outliers_by_column', {})
            for col_name, col_info in outliers_by_col.items():
                # col_info is an OutlierInfo object, access as attribute
                total_outlier_pct += col_info.outlier_percentage
            avg_outlier_pct = total_outlier_pct / outlier_summary['total_numeric_columns']
        else:
            avg_outlier_pct = 0.0
        
        outlier_score = max(0, 100 - avg_outlier_pct)
        
        duplicate_cols = 0
        unnamed_cols = 0
        columns_info = schema.get('columns', {})
        for col_name, col_schema in columns_info.items():
            # col_schema is a ColumnSchema object
            if hasattr(col_schema, 'column_name'):
                # Check column name patterns
                if 'column_' in col_schema.column_name:
                    unnamed_cols += 1
        
        # Check for duplicate column names
        all_col_names = [col for col in self.df.columns]
        if len(all_col_names) != len(set(all_col_names)):
            duplicate_cols = len(all_col_names) - len(set(all_col_names))
        
        schema_score = max(0, 100 - (duplicate_cols + unnamed_cols) * 10)
        
        overall_score = (completeness_score * 0.4 + outlier_score * 0.4 + schema_score * 0.2)
        
        quality_rating = 'excellent' if overall_score >= 90 else \
                        'good' if overall_score >= 75 else \
                        'fair' if overall_score >= 60 else \
                        'poor'
        
        return {
            'overall_score': round(overall_score, 2),
            'quality_rating': quality_rating,
            'completeness_score': round(completeness_score, 2),
            'outlier_score': round(outlier_score, 2),
            'schema_score': round(schema_score, 2),
            'issues': {
                'missing_percentage': missing.get('overall_missing_percentage', 0.0),
                'average_outlier_percentage': round(avg_outlier_pct, 2),
                'duplicate_columns': duplicate_cols,
                'unnamed_columns': unnamed_cols
            }
        }


def analyze_dataset(
    df: pl.DataFrame, 
    dataset_name: str = "Dataset",
    skip_multivariate_outliers: bool = False
) -> AnalysisResult:
    analyzer = DataAnalyzer(df, dataset_name=dataset_name)
    return analyzer.analyze_all(skip_multivariate_outliers=skip_multivariate_outliers)


def quick_analyze(df: pl.DataFrame, dataset_name: str = "Dataset") -> Dict[str, Any]:
    analyzer = DataAnalyzer(df, dataset_name=dataset_name)
    return analyzer.get_quick_summary()


def get_data_quality_score(df: pl.DataFrame) -> Dict[str, Any]:
    analyzer = DataAnalyzer(df)
    return analyzer.get_data_quality_score()