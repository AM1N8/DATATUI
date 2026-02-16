import polars as pl
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import re


class DataType(Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class SemanticType(Enum):
    NONE = "none"
    ID = "id"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    CURRENCY = "currency"
    ZIPCODE = "zipcode"
    IP_ADDRESS = "ip_address"
    COORDINATE = "coordinate"
    PERCENTAGE = "percentage"


class Cardinality(Enum):
    UNIQUE = "unique"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONSTANT = "constant"


@dataclass
class ColumnSchema:
    column_name: str
    dtype: str
    data_type: DataType
    semantic_type: SemanticType
    unique_count: int
    cardinality: Cardinality
    null_count: int
    null_percentage: float
    memory_mb: float
    sample_values: List[Any]


class SchemaDetector:
    
    CATEGORICAL_THRESHOLD = 0.05
    HIGH_CARDINALITY_THRESHOLD = 0.5
    MEDIUM_CARDINALITY_THRESHOLD = 0.1
    
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s]+$')
    PHONE_PATTERN = re.compile(r'^[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$')
    IP_PATTERN = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
    ZIPCODE_PATTERN = re.compile(r'^\d{5}(-\d{4})?$')
    COORDINATE_PATTERN = re.compile(r'^-?\d+\.\d+$')
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_rows = len(df)
    
    def detect_schema(self) -> Dict[str, ColumnSchema]:
        schema = {}
        for col in self.df.columns:
            schema[col] = self._analyze_column(col)
        return schema
    
    def _analyze_column(self, column: str) -> ColumnSchema:
        series = self.df[column]
        
        dtype = str(series.dtype)
        null_count = series.null_count()
        null_percentage = (null_count / self.total_rows * 100) if self.total_rows > 0 else 0
        
        non_null_series = series.drop_nulls()
        unique_count = non_null_series.n_unique()
        
        data_type = self._detect_data_type(series, dtype)
        semantic_type = self._detect_semantic_type(non_null_series, column, data_type)
        cardinality = self._detect_cardinality(unique_count, len(non_null_series))
        
        memory_mb = series.estimated_size() / (1024 * 1024)
        
        sample_values = self._get_sample_values(non_null_series, n=5)
        
        return ColumnSchema(
            column_name=column,
            dtype=dtype,
            data_type=data_type,
            semantic_type=semantic_type,
            unique_count=unique_count,
            cardinality=cardinality,
            null_count=null_count,
            null_percentage=null_percentage,
            memory_mb=memory_mb,
            sample_values=sample_values
        )
    
    def _detect_data_type(self, series: pl.Series, dtype: str) -> DataType:
        if 'Int' in dtype or 'UInt' in dtype or 'Float' in dtype:
            return DataType.NUMERIC
        elif 'Boolean' in dtype or 'Bool' in dtype:
            return DataType.BOOLEAN
        elif 'Date' in dtype or 'Datetime' in dtype or 'Time' in dtype:
            return DataType.DATETIME
        elif 'String' in dtype or 'Utf8' in dtype or 'Categorical' in dtype:
            non_null = series.drop_nulls()
            if len(non_null) == 0:
                return DataType.TEXT
            
            unique_ratio = non_null.n_unique() / len(non_null)
            
            if unique_ratio <= self.CATEGORICAL_THRESHOLD:
                return DataType.CATEGORICAL
            else:
                return DataType.TEXT
        else:
            return DataType.UNKNOWN
    
    def _detect_semantic_type(
        self, 
        series: pl.Series, 
        column_name: str, 
        data_type: DataType
    ) -> SemanticType:
        if len(series) == 0:
            return SemanticType.NONE
        
        column_lower = column_name.lower()
        
        if data_type == DataType.NUMERIC:
            if 'id' in column_lower or column_lower.endswith('_id'):
                return SemanticType.ID
            
            if 'price' in column_lower or 'cost' in column_lower or 'amount' in column_lower:
                return SemanticType.CURRENCY
            
            if 'percent' in column_lower or 'pct' in column_lower or 'rate' in column_lower:
                return SemanticType.PERCENTAGE
            
            if 'lat' in column_lower or 'lon' in column_lower or 'lng' in column_lower:
                return SemanticType.COORDINATE
        
        if data_type == DataType.TEXT or data_type == DataType.CATEGORICAL:
            sample = series.head(min(100, len(series)))
            sample_str = [str(x) for x in sample.to_list() if x is not None]
            
            if not sample_str:
                return SemanticType.NONE
            
            if 'email' in column_lower:
                return SemanticType.EMAIL
            
            if 'url' in column_lower or 'link' in column_lower or 'website' in column_lower:
                return SemanticType.URL
            
            if 'phone' in column_lower or 'tel' in column_lower or 'mobile' in column_lower:
                return SemanticType.PHONE
            
            if 'zip' in column_lower or 'postal' in column_lower:
                return SemanticType.ZIPCODE
            
            if 'ip' in column_lower:
                return SemanticType.IP_ADDRESS
            
            email_matches = sum(1 for x in sample_str if self.EMAIL_PATTERN.match(x))
            if email_matches / len(sample_str) > 0.8:
                return SemanticType.EMAIL
            
            url_matches = sum(1 for x in sample_str if self.URL_PATTERN.match(x))
            if url_matches / len(sample_str) > 0.8:
                return SemanticType.URL
            
            phone_matches = sum(1 for x in sample_str if self.PHONE_PATTERN.match(x))
            if phone_matches / len(sample_str) > 0.8:
                return SemanticType.PHONE
            
            ip_matches = sum(1 for x in sample_str if self.IP_PATTERN.match(x))
            if ip_matches / len(sample_str) > 0.8:
                return SemanticType.IP_ADDRESS
            
            zip_matches = sum(1 for x in sample_str if self.ZIPCODE_PATTERN.match(x))
            if zip_matches / len(sample_str) > 0.8:
                return SemanticType.ZIPCODE
        
        return SemanticType.NONE
    
    def _detect_cardinality(self, unique_count: int, total_count: int) -> Cardinality:
        if total_count == 0:
            return Cardinality.CONSTANT
        
        if unique_count == 1:
            return Cardinality.CONSTANT
        
        if unique_count == total_count:
            return Cardinality.UNIQUE
        
        unique_ratio = unique_count / total_count
        
        if unique_ratio > self.HIGH_CARDINALITY_THRESHOLD:
            return Cardinality.HIGH
        elif unique_ratio > self.MEDIUM_CARDINALITY_THRESHOLD:
            return Cardinality.MEDIUM
        else:
            return Cardinality.LOW
    
    def _get_sample_values(self, series: pl.Series, n: int = 5) -> List[Any]:
        if len(series) == 0:
            return []
        
        sample_size = min(n, len(series))
        return series.head(sample_size).to_list()
    
    def get_schema_summary(self) -> Dict[str, Any]:
        schema = self.detect_schema()
        
        type_counts = {}
        for col_schema in schema.values():
            dt = col_schema.data_type.value
            type_counts[dt] = type_counts.get(dt, 0) + 1
        
        total_memory = sum(col.memory_mb for col in schema.values())
        
        columns_with_nulls = sum(1 for col in schema.values() if col.null_count > 0)
        
        high_cardinality_cols = [
            col.column_name for col in schema.values() 
            if col.cardinality == Cardinality.HIGH or col.cardinality == Cardinality.UNIQUE
        ]
        
        return {
            'total_columns': len(schema),
            'total_rows': self.total_rows,
            'total_memory_mb': total_memory,
            'type_distribution': type_counts,
            'columns_with_nulls': columns_with_nulls,
            'high_cardinality_columns': high_cardinality_cols,
            'columns': schema
        }


def detect_schema(df: pl.DataFrame) -> Dict[str, ColumnSchema]:
    detector = SchemaDetector(df)
    return detector.detect_schema()


def get_schema_summary(df: pl.DataFrame) -> Dict[str, Any]:
    detector = SchemaDetector(df)
    return detector.get_schema_summary()