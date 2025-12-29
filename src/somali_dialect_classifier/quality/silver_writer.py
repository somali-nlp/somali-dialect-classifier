"""
Silver dataset writer with domain, embedding, and register fields.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from ..infra.config import get_config

logger = logging.getLogger(__name__)


class SilverDatasetWriter:
    """
    Writes records to silver dataset in Parquet format.

    Handles partitioning, schema validation, and file I/O.
    """

    # Current schema version: 1.0 (hard-coded, no backward compatibility)
    SCHEMA = pa.schema(
        [
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
            ("source_metadata", pa.string()),
            ("domain", pa.string()),
            ("embedding", pa.string()),
            ("register", pa.string()),
            ("run_id", pa.string()),  # Provenance: links record to metrics/logs
            ("schema_version", pa.string()),  # Always "1.0" (hard-coded)
        ]
    )

    VALID_REGISTERS = {"formal", "informal", "colloquial"}

    DOMAINS = {
        "news",
        "encyclopedia",
        "literature",
        "science",
        "health",
        "children",
        "radio",
        "social_media",
        "web",
        "academic",
        "translation",
        "qa",
        "historical",
        "general",
        "news_regional",
        "literature_translation",
    }

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

    def _get_next_partition_num(self, silver_dir: Path, run_id: str) -> int:
        """
        Get the next available partition number by scanning existing files for this run_id.

        Args:
            silver_dir: Directory to scan for existing partitions
            run_id: Run ID to filter files

        Returns:
            Next partition number (0 if no existing partitions for this run_id)
        """
        if not silver_dir.exists():
            return 0

        # Find all existing partition files for this run_id
        # Pattern: *_{run_id}_silver_part-*.parquet
        existing_parts = list(silver_dir.glob(f"*_{run_id}_silver_part-*.parquet"))

        if not existing_parts:
            return 0

        # Extract partition numbers and find max
        partition_nums = []
        for part_file in existing_parts:
            # Extract number from "{source}_{run_id}_silver_part-0000.parquet" -> 0
            try:
                # Split by '-' and get the last number before '.parquet'
                num_str = part_file.stem.split("-")[-1]
                partition_nums.append(int(num_str))
            except (IndexError, ValueError):
                continue

        return max(partition_nums) + 1 if partition_nums else 0

    def _validate_and_enrich_records(self, records: list[dict]) -> list[dict]:
        """
        Validate records and enrich with computed fields.

        STRICT VALIDATION: Fails fast on missing required fields.
        NO backward compatibility: All required fields must be present.

        Args:
            records: List of record dictionaries

        Returns:
            Validated and enriched records

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Define required fields from IngestionOutputV1 contract
        required_fields = {
            "id", "text", "title", "source", "source_type", "url",
            "date_accessed", "language", "license", "tokens", "text_hash",
            "pipeline_version", "source_metadata", "domain", "register", "run_id"
        }

        enriched_records = []

        for idx, record in enumerate(records):
            # STRICT VALIDATION: Check for missing required fields
            missing_fields = required_fields - set(record.keys())
            if missing_fields:
                raise ValueError(
                    f"Record {idx} (id={record.get('id', 'unknown')}) missing required fields: "
                    f"{sorted(missing_fields)}. All fields must be provided by pipeline."
                )

            # Validate domain value (fail on invalid, don't patch)
            if record["domain"] not in self.DOMAINS:
                raise ValueError(
                    f"Record {idx} (id={record['id']}) has invalid domain '{record['domain']}'. "
                    f"Valid domains: {sorted(self.DOMAINS)}"
                )

            # Validate register value (fail on invalid, don't patch)
            if record["register"] not in self.VALID_REGISTERS:
                raise ValueError(
                    f"Record {idx} (id={record['id']}) has invalid register '{record['register']}'. "
                    f"Valid registers: {sorted(self.VALID_REGISTERS)}"
                )

            # Handle embedding field - ensure it's a string or None
            if record.get("embedding") is not None and not isinstance(record["embedding"], str):
                # Convert embeddings to JSON string if provided as list/dict
                try:
                    record["embedding"] = json.dumps(record["embedding"])
                except (TypeError, ValueError) as e:
                    raise ValueError(
                        f"Record {idx} (id={record['id']}) has invalid embedding format: {e}"
                    )

            # HARD-CODE schema_version to "1.0" (no version detection)
            record["schema_version"] = "1.0"

            enriched_records.append(record)

        return enriched_records


    def write(
        self,
        records: list[dict],
        source: str,
        date_accessed: str,
        run_id: str,
        partition_num: Optional[int] = None,
    ) -> Optional[Path]:
        """
        Write records to partitioned Parquet file with enhanced schema and metadata.

        Args:
            records: List of record dictionaries
            source: Source name (e.g., "Wikipedia-Somali")
            date_accessed: ISO date for partitioning
            run_id: Run ID for file naming and traceability
            partition_num: Partition number (None = auto-increment to avoid overwrites)

        Returns:
            Path to written Parquet file, or None if no records

        Example:
            >>> writer = SilverDatasetWriter()
            >>> path = writer.write(
            ...     records=[{"id": "1", "text": "...", "domain": "news", ...}],
            ...     source="BBC-Somali",
            ...     date_accessed="2025-01-01",
            ...     run_id="20251020_143045"
            ... )
        """
        if not records:
            logger.warning("No records to write to silver dataset.")
            return None

        # Validate records and enrich (strict validation, no backward compatibility)
        records = self._validate_and_enrich_records(records)

        # Create partitioned directory structure
        silver_dir = self.base_dir / f"source={source}" / f"date_accessed={date_accessed}"
        silver_dir.mkdir(parents=True, exist_ok=True)

        # Auto-increment partition number if not specified
        if partition_num is None:
            partition_num = self._get_next_partition_num(silver_dir, run_id)

        # Generate source slug for filename (lowercase, hyphenated)
        source_slug = source.lower().replace("_", "-")

        # Generate partition filename with run_id
        # Pattern: {source_slug}_{run_id}_silver_part-{num}.parquet
        parquet_path = (
            silver_dir / f"{source_slug}_{run_id}_silver_part-{partition_num:04d}.parquet"
        )

        # Convert to PyArrow table and enforce schema to prevent drift
        table = pa.Table.from_pylist(records, schema=self.SCHEMA)

        # Write to Parquet
        pq.write_table(table, parquet_path)

        # Generate metadata JSON sidecar
        self._write_metadata_sidecar(
            silver_dir=silver_dir,
            source=source,
            source_slug=source_slug,
            run_id=run_id,
            date_accessed=date_accessed,
            partition_num=partition_num,
            records=records,
            parquet_path=parquet_path,
        )

        # Log domain distribution
        domain_counts = {}
        for record in records:
            domain = record.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        logger.info(
            f"Silver dataset written: {parquet_path} "
            f"({len(records)} rows, {self._format_size(parquet_path)})"
        )

        if len(domain_counts) > 1:
            logger.info(f"Domain distribution: {domain_counts}")

        return parquet_path

    def _format_size(self, path: Path) -> str:
        """Format file size for logging."""
        size_bytes = path.stat().st_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    def _compute_checksum(self, file_path: Path) -> str:
        """
        Compute SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal SHA256 checksum
        """
        import hashlib

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _write_metadata_sidecar(
        self,
        silver_dir: Path,
        source: str,
        source_slug: str,
        run_id: str,
        date_accessed: str,
        partition_num: int,
        records: list[dict],
        parquet_path: Path,
    ) -> None:
        """
        Write metadata JSON sidecar for silver dataset.

        Creates a metadata file with checksums, statistics, and lineage information.

        Args:
            silver_dir: Silver dataset directory
            source: Source name
            source_slug: Source slug for filename
            run_id: Run ID
            date_accessed: Date accessed
            partition_num: Partition number
            records: List of records written
            parquet_path: Path to Parquet file
        """
        from datetime import datetime, timezone

        # Check if metadata file already exists (create once per run)
        metadata_path = silver_dir / f"{source_slug}_{run_id}_silver_metadata.json"

        # Compute checksum for this partition
        checksum = self._compute_checksum(parquet_path)

        # Collect partition info
        partition_info = {
            f"part-{partition_num:04d}": {
                "sha256": checksum,
                "size_bytes": parquet_path.stat().st_size,
                "record_count": len(records),
            }
        }

        # Load existing metadata if present (for multi-batch writes)
        if metadata_path.exists():
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            # Update existing metadata
            metadata["total_records"] += len(records)
            metadata["total_partitions"] += 1
            metadata["checksums"].update(partition_info)
            metadata["statistics"]["total_size_bytes"] += parquet_path.stat().st_size
            metadata["statistics"]["avg_record_size_bytes"] = (
                metadata["statistics"]["total_size_bytes"] / metadata["total_records"]
            )
            metadata["date_processed"] = datetime.now(timezone.utc).isoformat()

        else:
            # Create new metadata
            total_size = parquet_path.stat().st_size
            metadata = {
                "run_id": run_id,
                "source": source,
                "pipeline_version": "2.1.0",
                "date_accessed": date_accessed,
                "date_processed": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "total_partitions": 1,
                "sidecar_format_version": "2.1",  # Renamed from schema_version to avoid collision with record field
                "checksums": partition_info,
                "statistics": {
                    "total_size_bytes": total_size,
                    "avg_record_size_bytes": total_size / len(records) if records else 0,
                },
            }

        # Write metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.debug(f"Metadata sidecar written: {metadata_path}")

    def read(self, source: str, date_accessed: str) -> pa.Table:
        """
        Read silver dataset for a given source and date.

        STRICT MODE: No backward compatibility. All files must have current schema.

        Args:
            source: Source name
            date_accessed: ISO date

        Returns:
            PyArrow table with all records

        Raises:
            FileNotFoundError: If dataset not found
            ValueError: If dataset schema doesn't match current schema
        """
        silver_dir = self.base_dir / f"source={source}" / f"date_accessed={date_accessed}"

        if not silver_dir.exists():
            raise FileNotFoundError(f"Silver dataset not found: {silver_dir}")

        # Read all parquet files in partition
        table = pq.read_table(silver_dir)

        # STRICT VALIDATION: All required fields must be present
        required_fields = {field.name for field in self.SCHEMA}
        actual_fields = set(table.column_names)
        missing_fields = required_fields - actual_fields

        if missing_fields:
            raise ValueError(
                f"Dataset at {silver_dir} has missing required fields: {sorted(missing_fields)}. "
                f"This indicates legacy data that is not supported. All data must be regenerated "
                f"with the current schema version (1.0)."
            )

        return table

    def get_domain_statistics(self, source: Optional[str] = None) -> dict[str, int]:
        """
        Get domain distribution statistics across silver datasets.

        Args:
            source: Optional source filter (None = all sources)

        Returns:
            Dictionary mapping domain to document count
        """
        stats = {}

        # Iterate through all source directories
        if source:
            source_dirs = [self.base_dir / f"source={source}"]
        else:
            source_dirs = [d for d in self.base_dir.glob("source=*") if d.is_dir()]

        for source_dir in source_dirs:
            # Iterate through all date partitions
            for date_dir in source_dir.glob("date_accessed=*"):
                try:
                    # Read partition
                    table = pq.read_table(date_dir)

                    # Count domains if field exists
                    if "domain" in table.column_names:
                        domains = table.column("domain").to_pylist()
                        for domain in domains:
                            if domain:
                                stats[domain] = stats.get(domain, 0) + 1

                except Exception as e:
                    logger.warning(f"Error reading {date_dir}: {e}")

        return stats
