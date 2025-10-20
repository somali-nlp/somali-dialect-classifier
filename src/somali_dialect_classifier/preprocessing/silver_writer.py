"""
Silver dataset writer - handles Parquet serialization.

Separates data I/O from processing logic.
"""

import logging
from pathlib import Path
from typing import List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from ..config import get_config


logger = logging.getLogger(__name__)


class SilverDatasetWriter:
    """
    Writes records to silver dataset in Parquet format.

    Handles partitioning, schema validation, and file I/O.
    """

    # Standardized schema for all silver datasets
    SCHEMA = pa.schema([
        ("id", pa.string()),
        ("text", pa.string()),
        ("title", pa.string()),
        ("source", pa.string()),
        ("source_type", pa.string()),
        ("url", pa.string()),
        ("source_id", pa.string()),
        ("date_published", pa.string()),
        ("date_accessed", pa.string()),
        ("language", pa.string()),
        ("license", pa.string()),
        ("topic", pa.string()),
        ("tokens", pa.int64()),
        ("text_hash", pa.string()),
        ("pipeline_version", pa.string()),
        ("source_metadata", pa.string()),  # JSON string
    ])

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize silver dataset writer.

        Args:
            base_dir: Base directory for silver datasets (None = use config default)
        """
        if base_dir is None:
            config = get_config()
            base_dir = config.data.silver_dir
        self.base_dir = base_dir

    def _get_next_partition_num(self, silver_dir: Path) -> int:
        """
        Get the next available partition number by scanning existing files.

        Args:
            silver_dir: Directory to scan for existing partitions

        Returns:
            Next partition number (0 if no existing partitions)
        """
        if not silver_dir.exists():
            return 0

        # Find all existing partition files
        existing_parts = list(silver_dir.glob("part-*.parquet"))

        if not existing_parts:
            return 0

        # Extract partition numbers and find max
        partition_nums = []
        for part_file in existing_parts:
            # Extract number from "part-0000.parquet" -> 0
            try:
                num_str = part_file.stem.split('-')[1]
                partition_nums.append(int(num_str))
            except (IndexError, ValueError):
                continue

        return max(partition_nums) + 1 if partition_nums else 0

    def write(
        self,
        records: List[dict],
        source: str,
        date_accessed: str,
        partition_num: Optional[int] = None,
    ) -> Optional[Path]:
        """
        Write records to partitioned Parquet file.

        Args:
            records: List of record dictionaries
            source: Source name (e.g., "Wikipedia-Somali")
            date_accessed: ISO date for partitioning
            partition_num: Partition number (None = auto-increment to avoid overwrites)

        Returns:
            Path to written Parquet file, or None if no records

        Example:
            >>> writer = SilverDatasetWriter()
            >>> path = writer.write(
            ...     records=[{"id": "1", "text": "...", ...}],
            ...     source="Wikipedia-Somali",
            ...     date_accessed="2025-01-01"
            ... )
        """
        if not records:
            logger.warning("No records to write to silver dataset.")
            return None

        # Create partitioned directory structure
        silver_dir = self.base_dir / f"source={source}" / f"date_accessed={date_accessed}"
        silver_dir.mkdir(parents=True, exist_ok=True)

        # Auto-increment partition number if not specified
        if partition_num is None:
            partition_num = self._get_next_partition_num(silver_dir)

        # Generate partition filename
        parquet_path = silver_dir / f"part-{partition_num:04d}.parquet"

        # Convert to PyArrow table and enforce schema to prevent drift
        table = pa.Table.from_pylist(records, schema=self.SCHEMA)

        # Write to Parquet
        pq.write_table(table, parquet_path)

        logger.info(
            f"Silver dataset written: {parquet_path} "
            f"({len(records)} rows, {self._format_size(parquet_path)})"
        )

        return parquet_path

    def _format_size(self, path: Path) -> str:
        """Format file size for logging."""
        size_bytes = path.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    def read(self, source: str, date_accessed: str) -> pa.Table:
        """
        Read silver dataset for a given source and date.

        Args:
            source: Source name
            date_accessed: ISO date

        Returns:
            PyArrow table with all records
        """
        silver_dir = self.base_dir / f"source={source}" / f"date_accessed={date_accessed}"

        if not silver_dir.exists():
            raise FileNotFoundError(f"Silver dataset not found: {silver_dir}")

        # Read all parquet files in partition
        return pq.read_table(silver_dir)
