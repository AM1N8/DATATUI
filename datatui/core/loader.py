from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import polars as pl
from dataclasses import dataclass
import logging
import tempfile

logger = logging.getLogger(__name__)

@dataclass
class DatasetInfo:
    file_path: Path
    file_size_mb: float
    format: str
    rows: int
    columns: int
    column_names: list[str]
    load_time_seconds: float
    encoding: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class LoaderError(Exception):
    pass

class DataLoader:
    FORMAT_EXTENSIONS = {
        '.csv': "csv",
        ".pq": "parquet",
        ".xlsx": "excel",
        ".tsv": "tsv",
        ".txt": "csv",
        ".json": "json",
        ".parquet": "parquet",
        ".xls": "excel",
        ".arrow": "arrow",
        ".feather": "feather",
        ".jsonl": "jsonl",
        ".ndjson": "jsonl"
    }

    def __init__(self, lazy: bool = False, low_memory: bool = False):
        self.lazy = lazy
        self.low_memory = low_memory
        self.info: Optional[DatasetInfo] = None

    def load(
        self, 
        file_path: str | Path, 
        format: Optional[str] = None, 
        **kwargs
    ) -> pl.DataFrame | pl.LazyFrame:
        import time 
        start_time = time.time()
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise LoaderError(f"File {file_path} does not exist.")
        
        if not file_path.is_file():
            raise LoaderError(f"Path {file_path} is not a file.")
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        if format is None:
            format = self._detect_format(file_path)

        logger.info(f"Loading {format.upper()} file: {file_path} ({file_size_mb:.2f} MB)")

        try:
            if format == 'csv' or format == 'tsv':
                df, encoding = self._load_csv(file_path, format, **kwargs)
            elif format == 'parquet':
                df = self._load_parquet(file_path, **kwargs)
                encoding = None
            elif format == 'excel':
                df = self._load_excel(file_path, **kwargs)
                encoding = None
            elif format == 'json' or format == 'jsonl':
                df = self._load_json(file_path, format, **kwargs)
                encoding = None
            elif format == 'arrow' or format == 'feather':
                df = self._load_arrow(file_path, **kwargs)
                encoding = None
            else:
                raise LoaderError(f"Unsupported format: {format}")
        except Exception as e:
            raise LoaderError(f"Failed to load file: {str(e)}") from e

        if isinstance(df, pl.LazyFrame) and not self.lazy:
            df = df.collect()

        if isinstance(df, pl.LazyFrame):
            schema = df.collect_schema()
            rows = -1
            columns = len(schema)
            column_names = schema.names()
        else:
            rows, columns = df.shape
            column_names = df.columns
        
        load_time = time.time() - start_time

        self.info = DatasetInfo(
            file_path=file_path,
            file_size_mb=file_size_mb,
            format=format,
            rows=rows,
            columns=columns,
            column_names=column_names,
            load_time_seconds=load_time,
            encoding=encoding,
        )

        self._validate_dataframe(df)
        
        logger.info(f"Loaded {rows} rows × {columns} columns in {load_time:.2f}s")
        
        return df
    
    def _detect_format(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in self.FORMAT_EXTENSIONS:
            return self.FORMAT_EXTENSIONS[suffix]
        logger.warning(f"Unknown file extension '{suffix}' for file {file_path}. Defaulting to CSV.")
        return "csv"
    
    def _detect_encoding(self, file_path: Path, sample_size: int = 100000) -> str:
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(sample_size)
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                
                logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")
                
                if encoding:
                    encoding = encoding.lower()
                    encoding_map = {
                        'ascii': 'utf-8',
                        'windows-1252': 'cp1252',
                        'iso-8859-1': 'latin-1',
                    }
                    encoding = encoding_map.get(encoding, encoding)
                
                return encoding or 'utf-8'
        except ImportError:
            logger.warning("chardet not installed, defaulting to utf-8")
            return 'utf-8'
        except Exception as e:
            logger.warning(f"Encoding detection failed: {e}, defaulting to utf-8")
            return 'utf-8'
    
    def _convert_to_utf8(self, file_path: Path, source_encoding: str) -> Path:
        temp_fd, temp_path_str = tempfile.mkstemp(suffix='.csv', prefix='dataloader_')
        temp_path = Path(temp_path_str)
        
        try:
            with open(file_path, 'r', encoding=source_encoding, errors='replace') as f_in:
                with open(temp_path, 'w', encoding='utf-8') as f_out:
                    chunk_size = 1024 * 1024
                    while True:
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
            
            logger.info(f"Converted {source_encoding} to UTF-8: {temp_path}")
            return temp_path
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            raise LoaderError(f"Failed to convert encoding: {e}") from e
    
    def _load_csv(
        self, 
        file_path: Path, 
        format: str, 
        **kwargs
    ) -> Tuple[pl.DataFrame | pl.LazyFrame, str]:
        separator = '\t' if format == 'tsv' else ','
        
        default_options = {
            'separator': separator,
            'infer_schema_length': 10000,
            'try_parse_dates': True,
            'null_values': ['NA', 'N/A', 'null', 'NULL', ''],
            'ignore_errors': False,
        }
        
        options = {**default_options, **kwargs}
        options.pop('encoding', None)
        
        temp_file = None
        try:
            if self.lazy:
                df = pl.scan_csv(file_path, encoding='utf8', **options)
            else:
                df = pl.read_csv(file_path, encoding='utf8', **options)
            
            logger.info("Successfully loaded with UTF-8 encoding")
            return df, 'utf-8'
        except Exception as utf8_error:
            logger.debug(f"UTF-8 failed: {utf8_error}")
            
            try:
                if self.lazy:
                    df = pl.scan_csv(file_path, encoding='utf8-lossy', **options)
                else:
                    df = pl.read_csv(file_path, encoding='utf8-lossy', **options)
                
                logger.info("Successfully loaded with UTF-8 (lossy) encoding")
                if self.info:
                    self.info.warnings.append("File contained invalid UTF-8 bytes")
                return df, 'utf-8-lossy'
            except Exception as lossy_error:
                logger.debug(f"UTF-8 lossy failed: {lossy_error}")
                
                try:
                    detected_encoding = self._detect_encoding(file_path)
                    logger.info(f"Converting from {detected_encoding} to UTF-8")
                    
                    temp_file = self._convert_to_utf8(file_path, detected_encoding)
                    
                    if self.lazy:
                        df = pl.scan_csv(temp_file, encoding='utf8', **options)
                    else:
                        df = pl.read_csv(temp_file, encoding='utf8', **options)
                    
                    logger.info(f"Successfully loaded after converting from {detected_encoding}")
                    return df, detected_encoding
                except Exception as final_error:
                    raise LoaderError(
                        f"Could not load CSV with any encoding method. Last error: {final_error}"
                    ) from final_error
                finally:
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
    
    def _load_parquet(self, file_path: Path, **kwargs) -> pl.DataFrame | pl.LazyFrame:
        if self.lazy:
            return pl.scan_parquet(file_path, **kwargs)
        else:
            return pl.read_parquet(file_path, **kwargs)

    def _load_excel(self, file_path: Path, **kwargs) -> pl.DataFrame:
        default_options = {
            'sheet_id': 0,
            'infer_schema_length': 1000,
        }
        options = {**default_options, **kwargs}
        
        try:
            df = pl.read_excel(file_path, **options)
        except Exception as e:
            try:
                df = pl.read_excel(file_path, engine='openpyxl', **options)
            except Exception:
                raise LoaderError(f"Failed to load Excel file: {e}") from e
        return df
    
    def _load_json(
        self, 
        file_path: Path, 
        format: str, 
        **kwargs
    ) -> pl.DataFrame | pl.LazyFrame:
        if format == 'jsonl':
            if self.lazy:
                return pl.scan_ndjson(file_path, **kwargs)
            else:
                return pl.read_ndjson(file_path, **kwargs)
        else:
            return pl.read_json(file_path, **kwargs)
    
    def _load_arrow(self, file_path: Path, **kwargs) -> pl.DataFrame | pl.LazyFrame:
        if self.lazy:
            return pl.scan_ipc(file_path, **kwargs)
        else:
            return pl.read_ipc(file_path, **kwargs)
        
    def _validate_dataframe(self, df: pl.DataFrame | pl.LazyFrame) -> None:
        if self.info is None:
            return
        
        if isinstance(df, pl.DataFrame):
            if df.shape[0] == 0:
                self.info.warnings.append("Dataset is empty (0 rows)")
            
            if df.shape[1] == 0:
                self.info.warnings.append("Dataset has no columns")
        
        if isinstance(df, pl.LazyFrame):
            column_names = df.collect_schema().names()
        else:
            column_names = df.columns
            
        if len(column_names) != len(set(column_names)):
            duplicates = [name for name in column_names if column_names.count(name) > 1]
            self.info.warnings.append(f"Duplicate column names found: {set(duplicates)}")
        
        unnamed = [name for name in column_names if name.startswith('column_')]
        if unnamed:
            self.info.warnings.append(f"Found {len(unnamed)} unnamed columns")
    
    def get_info(self) -> Optional[DatasetInfo]:
        return self.info


def load_dataset(
    file_path: str | Path,
    format: Optional[str] = None,
    lazy: bool = False,
    **kwargs
) -> pl.DataFrame:
    loader = DataLoader(lazy=lazy)
    df = loader.load(file_path, format=format, **kwargs)
    
    if loader.info and loader.info.warnings:
        for warning in loader.info.warnings:
            logger.warning(warning)
    
    return df


def preview_dataset(file_path: str | Path, n_rows: int = 5) -> Dict[str, Any]:
    file_path = Path(file_path)
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    
    loader = DataLoader()
    format = loader._detect_format(file_path)
    
    try:
        if format in ['csv', 'tsv']:
            df_preview = pl.read_csv(file_path, n_rows=n_rows, encoding='utf8-lossy')
        elif format == 'parquet':
            df_preview = pl.read_parquet(file_path, n_rows=n_rows)
        elif format == 'excel':
            df_preview = pl.read_excel(file_path, sheet_id=0)
            df_preview = df_preview.head(n_rows)
        else:
            df_preview = load_dataset(file_path).head(n_rows)
        
        return {
            'file_path': str(file_path),
            'file_size_mb': file_size_mb,
            'format': format,
            'columns': len(df_preview.columns),
            'column_names': df_preview.columns,
            'dtypes': {col: str(dtype) for col, dtype in zip(df_preview.columns, df_preview.dtypes)},
            'preview': df_preview,
        }
    except Exception as e:
        raise LoaderError(f"Failed to preview file: {e}") from e