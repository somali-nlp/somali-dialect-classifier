"""
DataManager: Handles all file I/O operations for pipeline.

Responsibilities:
- Read/write files (raw, staging, silver layers)
- Path management (construct output paths)
- File validation (existence, size, format)
- Checksum calculation (SHA256)

This service extracts file I/O logic from BasePipeline to promote:
- Single Responsibility Principle
- Reusability across processors
- Easier testing (mockable service)
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None


class DataPaths:
    """Data path configuration for medallion architecture."""

    def __init__(self, base_dir: Path = Path("data")):
        """
        Initialize data paths.

        Args:
            base_dir: Base directory for all data (default: "data")
        """
        self.base = base_dir
        self.raw = base_dir / "raw"
        self.staging = base_dir / "staging"
        self.silver = base_dir / "processed" / "silver"
        self.metrics = base_dir / "metrics"
        self.reports = base_dir / "reports"

    def ensure_directories(self):
        """Create all directories if they don't exist."""
        for path in [self.raw, self.staging, self.silver, self.metrics, self.reports]:
            path.mkdir(parents=True, exist_ok=True)


class DataManager:
    """
    Manages all file I/O operations for data pipeline.

    Features:
    - Medallion layer file operations (raw/staging/silver)
    - Path construction with naming conventions
    - File validation
    - Checksum calculation

    Example:
        >>> manager = DataManager(source="BBC-Somali", run_id="20231115_120000")
        >>> data = {"title": "Example", "text": "Content"}
        >>> path = manager.write_to_raw(data, "example.json", format="json")
        >>> checksum = manager.compute_file_checksum(path)
    """

    def __init__(self, source: str, run_id: str, base_dir: Path = Path("data")):
        """
        Initialize data manager.

        Args:
            source: Source identifier (e.g., "BBC-Somali", "Wikipedia-Somali")
            run_id: Unique run identifier for this pipeline execution
            base_dir: Base directory for data (default: "data")
        """
        self.source = source
        self.run_id = run_id
        self.paths = DataPaths(base_dir)
        self.paths.ensure_directories()
        self.logger = logging.getLogger(__name__)

    def compute_file_checksum(self, filepath: Path, algorithm: str = "sha256") -> str:
        """
        Compute cryptographic checksum of a file.

        Used for file-level deduplication to detect if a dump has already been processed.
        Reads file in chunks for memory efficiency with large files.

        Args:
            filepath: Path to file to checksum
            algorithm: Hash algorithm ('sha256', 'md5', etc.). Default: 'sha256'

        Returns:
            Hex digest of file checksum

        Raises:
            ValueError: If unsupported hash algorithm
            FileNotFoundError: If file does not exist

        Example:
            >>> checksum = manager.compute_file_checksum(Path("dump.xml.bz2"))
            >>> # Returns: "a3f5b8c9d2e1f0..."
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Create hasher instance based on algorithm
        try:
            hasher = hashlib.new(algorithm)
        except ValueError:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        # Read file in 4KB chunks for memory efficiency
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def write_to_raw(
        self, data: Any, filename: str, format: str = "json", partition_by_source: bool = True
    ) -> Path:
        """
        Write data to raw layer.

        Args:
            data: Data to write
            filename: Output filename
            format: File format (json, jsonl, txt, parquet)
            partition_by_source: If True, partition by source=<source> directory

        Returns:
            Path to written file

        Raises:
            ValueError: If unknown format or invalid data type

        Example:
            >>> data = [{"text": "Example"}]
            >>> path = manager.write_to_raw(data, "articles.jsonl", format="jsonl")
        """
        if partition_by_source:
            output_path = self.paths.raw / f"source={self.source}" / filename
        else:
            output_path = self.paths.raw / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

        elif format == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(data))

        elif format == "parquet":
            if not PANDAS_AVAILABLE:
                raise ImportError("pandas is required for parquet format")
            if isinstance(data, pd.DataFrame):
                data.to_parquet(output_path, index=False)
            else:
                raise ValueError("Parquet format requires pandas DataFrame")

        else:
            raise ValueError(f"Unknown format: {format}")

        self.logger.info(f"Wrote {format} to raw layer: {output_path}")
        return output_path

    def write_to_staging(
        self, data: Any, filename: str, format: str = "jsonl", partition_by_source: bool = True
    ) -> Path:
        """
        Write data to staging layer.

        Args:
            data: Data to write
            filename: Output filename
            format: File format (json, jsonl, txt)
            partition_by_source: If True, partition by source=<source> directory

        Returns:
            Path to written file

        Example:
            >>> records = [{"title": "A", "text": "Content A"}]
            >>> path = manager.write_to_staging(records, "extracted.jsonl")
        """
        if partition_by_source:
            output_path = self.paths.staging / f"source={self.source}" / filename
        else:
            output_path = self.paths.staging / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

        elif format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(data))

        else:
            raise ValueError(f"Unknown format: {format}")

        self.logger.info(f"Wrote {format} to staging layer: {output_path}")
        return output_path

    def write_to_silver(
        self, df: "pd.DataFrame", filename: str, partition_by_source: bool = True
    ) -> Path:
        """
        Write DataFrame to silver layer as Parquet.

        Args:
            df: DataFrame to write
            filename: Output filename (without extension)
            partition_by_source: If True, partition by source=<source> directory

        Returns:
            Path to written file

        Raises:
            ImportError: If pandas not available
            ValueError: If df is not a DataFrame

        Example:
            >>> df = pd.DataFrame([{"text": "Example", "source": "BBC"}])
            >>> path = manager.write_to_silver(df, "bbc_final")
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for silver layer writes")

        if not isinstance(df, pd.DataFrame):
            raise ValueError("Silver layer requires pandas DataFrame")

        if partition_by_source:
            output_path = self.paths.silver / f"source={self.source}" / f"{filename}.parquet"
        else:
            output_path = self.paths.silver / f"{filename}.parquet"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_parquet(output_path, index=False, compression="snappy")

        self.logger.info(f"Wrote {len(df)} records to silver layer: {output_path}")
        return output_path

    def read_from_raw(
        self, filename: str, format: str = "json", partition_by_source: bool = True
    ) -> Any:
        """
        Read data from raw layer.

        Args:
            filename: Input filename
            format: File format (json, jsonl, txt)
            partition_by_source: If True, read from source=<source> directory

        Returns:
            Loaded data

        Raises:
            FileNotFoundError: If file does not exist
        """
        if partition_by_source:
            input_path = self.paths.raw / f"source={self.source}" / filename
        else:
            input_path = self.paths.raw / filename

        if not input_path.exists():
            raise FileNotFoundError(f"Raw file not found: {input_path}")

        if format == "json":
            with open(input_path, "r", encoding="utf-8") as f:
                return json.load(f)

        elif format == "jsonl":
            data = []
            with open(input_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            return data

        elif format == "txt":
            with open(input_path, "r", encoding="utf-8") as f:
                return f.read()

        else:
            raise ValueError(f"Unknown format: {format}")

    def read_from_staging(
        self, filename: str, format: str = "jsonl", partition_by_source: bool = True
    ) -> Any:
        """
        Read data from staging layer.

        Args:
            filename: Input filename
            format: File format (json, jsonl, txt)
            partition_by_source: If True, read from source=<source> directory

        Returns:
            Loaded data

        Raises:
            FileNotFoundError: If file does not exist
        """
        if partition_by_source:
            input_path = self.paths.staging / f"source={self.source}" / filename
        else:
            input_path = self.paths.staging / filename

        if not input_path.exists():
            raise FileNotFoundError(f"Staging file not found: {input_path}")

        if format == "jsonl":
            data = []
            with open(input_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            return data

        elif format == "json":
            with open(input_path, "r", encoding="utf-8") as f:
                return json.load(f)

        elif format == "txt":
            with open(input_path, "r", encoding="utf-8") as f:
                return f.read()

        else:
            raise ValueError(f"Unknown format: {format}")

    def read_from_silver(
        self, filename: str, partition_by_source: bool = True
    ) -> "pd.DataFrame":
        """
        Read DataFrame from silver layer.

        Args:
            filename: Input filename (without extension)
            partition_by_source: If True, read from source=<source> directory

        Returns:
            Loaded DataFrame

        Raises:
            ImportError: If pandas not available
            FileNotFoundError: If file does not exist
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for silver layer reads")

        if partition_by_source:
            input_path = self.paths.silver / f"source={self.source}" / f"{filename}.parquet"
        else:
            input_path = self.paths.silver / f"{filename}.parquet"

        if not input_path.exists():
            raise FileNotFoundError(f"Silver file not found: {input_path}")

        return pd.read_parquet(input_path)

    def validate_file(self, filepath: Path, min_size: int = 0) -> bool:
        """
        Validate file exists and meets criteria.

        Args:
            filepath: Path to validate
            min_size: Minimum file size in bytes

        Returns:
            True if valid, False otherwise
        """
        if not filepath.exists():
            return False

        if filepath.stat().st_size < min_size:
            return False

        return True

    def get_source_dir(self, layer: str) -> Path:
        """
        Get source-partitioned directory for a layer.

        Args:
            layer: Layer name (raw, staging, silver)

        Returns:
            Path to source directory

        Example:
            >>> manager.get_source_dir("raw")
            PosixPath('data/raw/source=BBC-Somali')
        """
        layer_path = getattr(self.paths, layer, None)
        if layer_path is None:
            raise ValueError(f"Unknown layer: {layer}")

        return layer_path / f"source={self.source}"

    def list_files(self, layer: str, pattern: str = "*") -> List[Path]:
        """
        List files in a layer directory.

        Args:
            layer: Layer name (raw, staging, silver)
            pattern: Glob pattern for file matching (default: "*")

        Returns:
            List of matching file paths

        Example:
            >>> files = manager.list_files("raw", pattern="*.json")
        """
        source_dir = self.get_source_dir(layer)

        if not source_dir.exists():
            return []

        return sorted(source_dir.glob(pattern))
