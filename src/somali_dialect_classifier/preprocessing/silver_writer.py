"""
Silver dataset writer - enhanced with domain, embedding, and register fields.

Version 2.1: Adds register field for linguistic formality classification.
Version 2.0: Added domain classification and embedding placeholder.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from ..config import get_config

logger = logging.getLogger(__name__)


class SilverDatasetWriter:
    """
    Writes records to silver dataset in Parquet format.

    Handles partitioning, schema validation, and file I/O.
    Version 2.1 adds register field for linguistic formality.
    Version 2.0 added domain and embedding fields.
    """

    # Enhanced schema with domain, embedding, and register fields
    SCHEMA = pa.schema(
        [
            # Original fields
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
            # Fields added in v2.0
            ("domain", pa.string()),  # Content domain (news, literature, science, etc.)
            ("embedding", pa.string()),  # Placeholder for future embeddings (JSON string)
            # Fields added in v2.1
            ("register", pa.string()),  # Linguistic register: "formal", "informal", "colloquial"
        ]
    )

    # Schema for reading v2.0 files (without register field)
    SCHEMA_V2_0 = pa.schema(
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
        ]
    )

    # Schema for reading v1.0 files (original schema)
    SCHEMA_V1_0 = pa.schema(
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
        ]
    )

    # Valid register values
    VALID_REGISTERS = {"formal", "informal", "colloquial"}

    # Standard domain taxonomy
    DOMAINS = {
        "news",  # News articles
        "encyclopedia",  # Encyclopedia/reference (Wikipedia)
        "literature",  # Fiction, poetry, stories
        "science",  # Scientific texts
        "health",  # Health-related content
        "children",  # Children's content
        "radio",  # Radio transcripts
        "social_media",  # Social media posts
        "web",  # General web content
        "academic",  # Academic papers
        "translation",  # Translated content
        "qa",  # Question-answer format
        "historical",  # Historical documents
        "general",  # Unclassified/mixed
        "news_regional",  # Regional news (e.g., Ogaden)
        "literature_translation",  # Translated literature
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

    def _ensure_schema_compatibility(self, records: list[dict]) -> list[dict]:
        """
        Ensure records have all required fields for the current schema.

        Adds default values for new fields if missing.

        Args:
            records: List of record dictionaries

        Returns:
            Records with all required fields
        """
        enhanced_records = []

        for record in records:
            # Add domain field if missing
            if "domain" not in record:
                # Try to infer domain from source or source_type
                record["domain"] = self._infer_domain(record)

            # Validate domain value
            if record["domain"] not in self.DOMAINS:
                logger.warning(
                    f"Unknown domain '{record['domain']}' for record {record.get('id')}, "
                    f"using 'general'"
                )
                record["domain"] = "general"

            # Add embedding field if missing (placeholder for now)
            if "embedding" not in record:
                record["embedding"] = None  # Will be converted to null in Parquet

            # Handle embedding field - ensure it's a string or None
            if record["embedding"] is not None and not isinstance(record["embedding"], str):
                # Convert embeddings to JSON string if provided as list/dict
                try:
                    record["embedding"] = json.dumps(record["embedding"])
                except (TypeError, ValueError):
                    record["embedding"] = None

            # Add register field if missing (v2.1)
            if "register" not in record:
                # Default to formal for all current sources
                record["register"] = self._infer_register(record)

            # Validate register value
            if record["register"] not in self.VALID_REGISTERS:
                logger.warning(
                    f"Invalid register '{record['register']}' for record {record.get('id')}, "
                    f"using 'formal'"
                )
                record["register"] = "formal"

            enhanced_records.append(record)

        return enhanced_records

    def _infer_domain(self, record: dict) -> str:
        """
        Infer domain from record metadata when not explicitly provided.

        Args:
            record: Record dictionary

        Returns:
            Inferred domain string
        """
        source = record.get("source", "").lower()
        source_type = record.get("source_type", "").lower()

        # Source-based inference
        if "bbc" in source or "news" in source_type:
            return "news"
        elif "wikipedia" in source or "wiki" in source_type:
            return "encyclopedia"
        elif "huggingface" in source or "mc4" in source:
            return "web"
        elif "sprakbanken" in source or "språkbanken" in source:
            # Try to get more specific domain from source_metadata
            try:
                metadata = json.loads(record.get("source_metadata", "{}"))
                corpus_id = metadata.get("corpus_id", "")
                return self._infer_sprakbanken_domain(corpus_id)
            except (json.JSONDecodeError, TypeError):
                return "general"
        else:
            return "general"

    def _infer_sprakbanken_domain(self, corpus_id: str) -> str:
        """
        Infer domain for Språkbanken corpus based on corpus ID.

        Args:
            corpus_id: Språkbanken corpus identifier

        Returns:
            Domain string
        """
        corpus_id = corpus_id.lower()

        if "news" in corpus_id or "as-" in corpus_id or "ah-" in corpus_id or "cb" in corpus_id:
            return "news"
        elif "ogaden" in corpus_id:
            return "news_regional"
        elif "sheekooyin-carruureed" in corpus_id:
            return "children"
        elif "sheekooyin" in corpus_id or "suugaan" in corpus_id:
            return "literature"
        elif "turjuman" in corpus_id:
            if "suugaan" in corpus_id:
                return "literature_translation"
            else:
                return "translation"
        elif "cilmi" in corpus_id or "saynis" in corpus_id:
            return "science"
        elif "caafimaad" in corpus_id:
            return "health"
        elif "radio" in corpus_id:
            return "radio"
        elif "kqa" in corpus_id:
            return "qa"
        else:
            return "general"

    def _infer_register(self, record: dict) -> str:
        """
        Infer linguistic register from record metadata.

        Maps source types to register values:
        - "formal": Wikipedia, BBC, HuggingFace MC4, Språkbanken (all current sources)
        - "informal": TikTok, social media (future sources)
        - "colloquial": Informal conversational content (future sources)

        Args:
            record: Record dictionary

        Returns:
            Inferred register string ("formal", "informal", or "colloquial")
        """
        record.get("source", "").lower()
        source_type = record.get("source_type", "").lower()

        # Map source types to register
        # All current sources are formal
        if source_type in {"wiki", "news", "corpus", "web"}:
            return "formal"
        elif source_type == "social":
            # Future TikTok integration
            return "informal"
        else:
            # Default to formal for unknown types
            return "formal"

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

        # Ensure schema compatibility
        records = self._ensure_schema_compatibility(records)

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
                "schema_version": "2.1",
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

        Handles v1.0, v2.0, and v2.1 schema formats.

        Args:
            source: Source name
            date_accessed: ISO date

        Returns:
            PyArrow table with all records (enhanced with default values if older version)
        """
        silver_dir = self.base_dir / f"source={source}" / f"date_accessed={date_accessed}"

        if not silver_dir.exists():
            raise FileNotFoundError(f"Silver dataset not found: {silver_dir}")

        # Read all parquet files in partition
        table = pq.read_table(silver_dir)

        # Check for missing fields and add defaults
        missing_fields = []

        if "domain" not in table.column_names:
            missing_fields.append("domain (v1.0 detected)")
        if "embedding" not in table.column_names:
            missing_fields.append("embedding (v1.0 detected)")
        if "register" not in table.column_names:
            missing_fields.append("register (v2.0 detected)")

        if missing_fields:
            logger.info(
                f"Reading older silver dataset from {silver_dir}, adding: {', '.join(missing_fields)}"
            )

            # Convert to pandas for easier manipulation
            df = table.to_pandas()

            # Add missing fields with defaults
            if "domain" not in df.columns:
                df["domain"] = "general"
            if "embedding" not in df.columns:
                df["embedding"] = None
            if "register" not in df.columns:
                df["register"] = "formal"

            # Convert back to PyArrow table with current schema
            table = pa.Table.from_pandas(df, schema=self.SCHEMA)

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
