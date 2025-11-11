"""
Base pipeline orchestrator for all data sources.

Eliminates duplication by providing shared orchestration logic:
- Logging setup and progress tracking
- Record batching and processing flow
- Silver dataset writing
- Error handling

Refactored (P2.2) to use dependency injection:
- DataManager for file I/O operations
- MetricsCollector for metrics tracking (already injected by processors)
- DedupEngine for deduplication (already injected by processors)

Subclasses only implement source-specific logic:
- download() - How to fetch raw data
- extract() - How to parse into staging format
- _extract_records() - How to yield RawRecords for processing
- _create_cleaner() - Which text cleaner to use
"""

from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from ..config import get_config
from ..data import DataManager
from .data_processor import DataProcessor
from .record_utils import build_silver_record
from .silver_writer import SilverDatasetWriter
from .text_cleaners import TextCleaningPipeline


class RawRecord:
    """
    Intermediate representation between extraction and processing.

    Decouples source-specific extraction from shared processing logic.
    """

    def __init__(
        self,
        title: str,
        text: str,
        url: str,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize a raw record.

        Args:
            title: Document title
            text: Raw text content (will be cleaned)
            url: Source URL or identifier
            metadata: Additional source-specific metadata (date_published, category, etc.)
        """
        self.title = title
        self.text = text
        self.url = url
        self.metadata = metadata or {}


class BasePipeline(DataProcessor, ABC):
    """
    Base class for all data pipeline processors.

    Provides:
    - Common directory structure (raw/, staging/, processed/)
    - Shared orchestration logic in process()
    - Logging and progress tracking
    - Filter execution framework

    Subclasses implement:
    - download() - Fetch raw data
    - extract() - Parse into staging format
    - _extract_records() - Yield RawRecords for processing
    - _register_filters() - Add quality filters
    - _create_cleaner() - Create text cleaner instance
    - _get_source_metadata() - Return source-specific metadata
    - _get_source_type() - Return source type (news, web, etc.)
    - _get_license() - Return license information
    - _get_language() - Return language code (default: "so")
    - _get_domain() - Return content domain
    - _get_register() - Return linguistic register
    """

    def __init__(
        self,
        source: str,
        log_frequency: int = 100,
        batch_size: Optional[int] = None,
        force: bool = False,
        data_manager: Optional[DataManager] = None,
    ):
        """
        Initialize base pipeline.

        Args:
            source: Source identifier (e.g., "BBC-Somali", "Wikipedia-Somali")
            log_frequency: Log progress every N records (default: 100)
            batch_size: Optional batch size for incremental silver writes
            force: Force reprocessing even if output exists (default: False)
            data_manager: Optional DataManager instance for dependency injection
        """
        # SECURITY FIX: Sanitize source name to prevent path traversal attacks
        from ..utils.security import sanitize_source_name

        try:
            safe_source = sanitize_source_name(source)
        except ValueError as e:
            raise ValueError(f"Invalid source name: {e}")

        self.source = safe_source  # Use sanitized source
        self.log_frequency = log_frequency
        self.batch_size = batch_size
        self.force = force

        # Generate unique run_id for this pipeline execution
        from ..utils.logging_utils import StructuredLogger, generate_run_id

        self.run_id = generate_run_id(safe_source)

        # Initialize structured logger with file output
        log_file = Path("logs") / f"{self.run_id}.log"
        structured_logger = StructuredLogger(name=safe_source, log_file=log_file, json_format=True)
        self.logger = structured_logger.get_logger()  # Get actual logger instance

        # Timestamp for partitioning
        self.date_accessed = datetime.now(timezone.utc).date().isoformat()

        # Load config for directory paths
        config = get_config()

        # Inject or create DataManager for file I/O operations
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            # Create default DataManager using config paths
            base_dir = config.data.raw_dir.parent  # Get data/ directory
            self.data_manager = DataManager(
                source=safe_source, run_id=self.run_id, base_dir=base_dir
            )

        # Consistent directory structure using config paths (with sanitized source)
        # Keep these for backward compatibility with existing processors
        self.raw_dir = (
            config.data.raw_dir / f"source={safe_source}" / f"date_accessed={self.date_accessed}"
        )
        self.staging_dir = (
            config.data.staging_dir / f"source={safe_source}" / f"date_accessed={self.date_accessed}"
        )
        self.processed_dir = (
            config.data.processed_dir / f"source={safe_source}" / f"date_processed={self.date_accessed}"
        )

        # Initialize shared utilities
        self.text_cleaner = self._create_cleaner()
        self.silver_writer = SilverDatasetWriter()

        # Record filters for quality control
        # List of (filter_func, kwargs) tuples
        # Each filter_func signature: (cleaned_text: str, **kwargs) -> (bool, Dict[str, Any])
        self.record_filters: list[tuple[Callable, dict[str, Any]]] = []
        self._register_filters()  # Subclasses override to add filters

        # Subclasses set these paths
        self.staging_file: Optional[Path] = None
        self.processed_file: Optional[Path] = None
        self.silver_path: Optional[Path] = None  # Parquet file from silver_writer.write()

    def _register_filters(self) -> None:
        """
        Register record filters for quality control.

        Subclasses override this method to append filters to self.record_filters.
        Base implementation provides empty list (no filtering by default).

        Each filter is a tuple of (filter_func, kwargs) where:
        - filter_func(cleaned_text: str, **kwargs) -> (bool, Dict[str, Any])
        - Returns (passes, metadata_updates)

        Example:
            def _register_filters(self):
                from .filters import min_length_filter, langid_filter
                self.record_filters.append((min_length_filter, {"threshold": 50}))
                self.record_filters.append((langid_filter, {"allowed_langs": {"so"}}))
        """
        # Base implementation: no filters
        # Subclasses can override to add specific filters
        pass

    @abstractmethod
    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging format.

        Subclasses implement this to yield RawRecord objects from staging data.
        Called by process() to get records for cleaning and filtering.

        Yields:
            RawRecord objects with title, text, url, metadata

        Example:
            def _extract_records(self):
                with open(self.staging_file, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        yield RawRecord(
                            title=data['title'],
                            text=data['text'],
                            url=data['url'],
                            metadata={'date': data.get('date')}
                        )
        """
        pass

    @abstractmethod
    def _create_cleaner(self) -> TextCleaningPipeline:
        """
        Create text cleaner instance.

        Subclasses implement this to return appropriate cleaner.
        Common options: create_html_cleaner(), create_wiki_cleaner()

        Returns:
            TextCleaningPipeline instance

        Example:
            def _create_cleaner(self):
                from .text_cleaners import create_html_cleaner
                return create_html_cleaner()
        """
        pass

    @abstractmethod
    def _get_source_type(self) -> str:
        """
        Return source type for silver records.

        Returns:
            Source type string (e.g., "news", "web", "social", "encyclopedia")
        """
        pass

    @abstractmethod
    def _get_license(self) -> str:
        """
        Return license information for silver records.

        Returns:
            License string (e.g., "CC-BY-SA-3.0", "ODC-BY-1.0")
        """
        pass

    @abstractmethod
    def _get_language(self) -> str:
        """
        Return ISO 639-1 language code.

        Returns:
            Language code (default: "so" for Somali)
        """
        return "so"

    @abstractmethod
    def _get_source_metadata(self) -> dict[str, Any]:
        """
        Return source-specific metadata for silver records.

        Returns:
            Dictionary with source-specific metadata (URLs, configs, etc.)
        """
        pass

    @abstractmethod
    def _get_domain(self) -> str:
        """
        Return content domain for silver records.

        Returns:
            Domain string (e.g., "news", "encyclopedia", "web", "social_media")
        """
        pass

    @abstractmethod
    def _get_register(self) -> str:
        """
        Return linguistic register for silver records.

        Returns:
            Register string (e.g., "formal", "informal", "colloquial")
        """
        pass

    def process(self) -> Path:
        """
        Shared processing logic for all pipelines.

        Orchestrates:
        1. Reads from staging (via _extract_records)
        2. Applies text cleaning
        3. Executes filters
        4. Enriches with metadata
        5. Writes to silver dataset

        Subclasses don't override this - they implement _extract_records() instead.

        Returns:
            Path to processed file
        """
        if not self.staging_file or not self.staging_file.exists():
            raise FileNotFoundError(f"Staging file not found: {self.staging_file}")

        self.processed_dir.mkdir(parents=True, exist_ok=True)

        if self.processed_file.exists() and not self.force:
            self.logger.info(f"Processed file already exists: {self.processed_file}")
            self.logger.info("Use force=True to reprocess")
            return self.processed_file

        if self.processed_file.exists() and self.force:
            self.logger.info(f"Force reprocessing: removing existing file {self.processed_file}")
            self.processed_file.unlink()

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PHASE 3: Text Processing & Silver Dataset Creation")
        self.logger.info("=" * 60)

        records_processed = 0
        records_filtered = 0
        filter_stats = Counter()  # Track filter drop counts
        records = []

        with open(self.processed_file, "w", encoding="utf-8") as fout:
            for raw_record in self._extract_records():
                # Shared text cleaning
                cleaned = self.text_cleaner.clean(raw_record.text)

                if not cleaned:
                    records_filtered += 1
                    filter_stats["empty_after_cleaning"] += 1

                    # Record filter reason in metrics if available
                    if hasattr(self, "metrics") and self.metrics is not None:
                        self.metrics.record_filter_reason("empty_after_cleaning")
                    continue

                # Execute record filters
                filter_metadata = {}
                passed_all_filters = True

                for filter_func, filter_kwargs in self.record_filters:
                    try:
                        passes, metadata_updates = filter_func(cleaned, **filter_kwargs)

                        if not passes:
                            # Record failed this filter
                            filter_name = filter_func.__name__
                            filter_stats[f"filtered_by_{filter_name}"] += 1
                            records_filtered += 1
                            passed_all_filters = False

                            # Record filter reason in metrics if available
                            if hasattr(self, "metrics") and self.metrics is not None:
                                self.metrics.record_filter_reason(filter_name)

                            # Debug log for filter rejections
                            self.logger.debug(
                                f"Record '{raw_record.title[:50]}...' filtered by {filter_name}"
                            )
                            break

                        # Merge metadata updates from filter
                        filter_metadata.update(metadata_updates)

                    except Exception as e:
                        # Log filter errors but don't fail pipeline
                        self.logger.warning(
                            f"Filter {filter_func.__name__} raised error on '{raw_record.title}': {e}"
                        )
                        # Treat as pass to avoid data loss from buggy filters
                        continue

                if not passed_all_filters:
                    continue  # Skip this record

                # Write to text file
                fout.write(f"=== {raw_record.title} ===\n{cleaned}\n\n")

                # Merge source-wide metadata with per-record metadata
                source_meta = self._get_source_metadata()
                # Add per-record metadata (category, scraped_at, etc.)
                # Include filter-enriched metadata
                merged_metadata = {**source_meta, **raw_record.metadata, **filter_metadata}

                # Extract source_id from metadata if available
                # This allows sources to populate source_id field (e.g., corpus_id for Språkbanken)
                source_id = raw_record.metadata.get("corpus_id") or raw_record.metadata.get(
                    "source_id"
                )

                # Build silver record using shared utility
                record = build_silver_record(
                    text=cleaned,
                    title=raw_record.title,
                    source=self.source,
                    url=raw_record.url,
                    date_accessed=self.date_accessed,
                    source_type=self._get_source_type(),
                    language=self._get_language(),
                    license_str=self._get_license(),
                    pipeline_version="2.1.0",  # Updated for schema v2.1
                    source_metadata=merged_metadata,
                    date_published=raw_record.metadata.get("date_published"),
                    topic=raw_record.metadata.get("topic"),
                    domain=self._get_domain(),
                    embedding=None,  # Placeholder for future embeddings
                    register=self._get_register(),  # v2.1: Linguistic register
                    source_id=source_id,  # Source-specific identifier
                )

                # Add schema versioning fields (NEW in schema v1.0)
                from ..schema import CURRENT_SCHEMA_VERSION
                record["schema_version"] = CURRENT_SCHEMA_VERSION
                record["run_id"] = self.run_id

                # Validate record against schema before adding
                from ..schema import SchemaValidator
                validator = SchemaValidator()
                is_valid, errors = validator.validate_record(record)

                if not is_valid:
                    # Log validation errors
                    self.logger.warning(
                        f"Record validation failed for '{raw_record.title[:50]}...': {errors}"
                    )
                    records_filtered += 1
                    filter_stats["schema_validation_failed"] += 1

                    # Record filter reason in metrics if available
                    if hasattr(self, "metrics") and self.metrics is not None:
                        self.metrics.record_filter_reason("schema_validation_failed")

                    # Skip invalid record
                    continue

                records.append(record)
                records_processed += 1

                # Mark URL as processed in ledger (if ledger exists)
                if hasattr(self, "ledger") and self.ledger is not None:
                    # Get minhash_signature from metadata if available
                    minhash_sig = raw_record.metadata.get("minhash_signature")
                    self.ledger.mark_processed(
                        url=raw_record.url,
                        text_hash=record["text_hash"],
                        silver_id=record["id"],
                        minhash_signature=minhash_sig,
                        source=self.source,
                    )

                # Consistent progress logging
                if records_processed % self.log_frequency == 0:
                    self.logger.info(f"Progress: {records_processed} records processed...")

                # Optional: batch writing for large datasets
                if self.batch_size and len(records) >= self.batch_size:
                    self._write_batch(records)
                    records = []

        # Shared completion logging
        self.logger.info("=" * 60)
        self.logger.info(f"Processing complete: {records_processed} records")
        if records_filtered > 0:
            self.logger.info(f"Filtered: {records_filtered} records")

            # Log per-filter statistics
            if filter_stats:
                self.logger.info("Filter statistics:")
                for filter_reason, count in filter_stats.most_common():
                    self.logger.info(f"  {filter_reason}: {count} records")

        self.logger.info("=" * 60)

        # Write final batch to silver dataset
        if records:
            silver_path = self.silver_writer.write(
                records=records,
                source=self.source,
                date_accessed=self.date_accessed,
                run_id=self.run_id,
            )
            if silver_path:
                self.silver_path = silver_path

        # Export processing metrics and generate final quality report
        # Only do this if metrics collector is available (passed from subclass)
        if hasattr(self, "metrics") and self.metrics is not None:
            # Update metrics with processing stats
            self.metrics.increment("urls_processed", records_processed)
            self.metrics.increment("records_written", records_processed)
            self.metrics.increment("records_filtered", records_filtered)

            # Export final metrics after processing
            from pathlib import Path

            metrics_path = Path("data/metrics") / f"{self.run_id}_processing.json"
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            self.metrics.export_json(metrics_path)
            self.logger.info(f"Processing metrics exported: {metrics_path}")

            # Generate final quality report with complete stats
            from ..utils.metrics import QualityReporter

            report_path = Path("data/reports") / f"{self.run_id}_final_quality_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            QualityReporter(self.metrics).generate_markdown_report(report_path)
            self.logger.info(f"Final quality report: {report_path}")

        # Return Parquet path if available, otherwise fall back to debug .txt file
        return self.silver_path if self.silver_path else self.processed_file

    def _write_batch(self, records: list) -> None:
        """Write a batch of records to silver dataset."""
        if records:
            self.logger.info(f"Writing batch of {len(records)} records...")
            silver_path = self.silver_writer.write(
                records=records,
                source=self.source,
                date_accessed=self.date_accessed,
                run_id=self.run_id,
            )
            if silver_path:
                self.silver_path = silver_path

    def save(self, processed_data: str) -> None:
        """
        Save processed data (required by DataProcessor abstract class).

        In this architecture, saving is handled by the process() method
        through the SilverDatasetWriter, so this method is a no-op placeholder.

        Args:
            processed_data: Path to processed data (not used)
        """
        # Saving is already handled by process() method via silver_writer
        pass

    def run(self) -> Path:
        """
        Template method - orchestrates full pipeline.

        Returns:
            Path to silver Parquet file (or debug .txt file as fallback)
        """
        self.download()
        self.extract()
        processed_file = self.process()

        # process() now returns Parquet path (self.silver_path) if available
        return processed_file

    def _cleanup_old_raw_files(self):
        """
        Clean up old raw files to save disk space.

        Keeps only the most recent N files (configurable via config).
        """
        config = get_config()
        keep_n = getattr(config.preprocessing, "raw_files_to_keep", 3)

        if not self.raw_dir.exists():
            return

        # Find all raw files sorted by modification time
        raw_files = sorted(
            [f for f in self.raw_dir.iterdir() if f.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Remove files beyond keep_n threshold
        for old_file in raw_files[keep_n:]:
            try:
                old_file.unlink()
                self.logger.debug(f"Cleaned up old raw file: {old_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete {old_file.name}: {e}")

    def _compute_file_checksum(self, filepath: Path, algorithm: str = 'sha256') -> str:
        """
        Compute cryptographic checksum of a file.

        REFACTORED (P2.2): Delegates to DataManager for file operations.

        Used for file-level deduplication to detect if a dump has already been processed.
        Reads file in chunks for memory efficiency with large files.

        Args:
            filepath: Path to file to checksum
            algorithm: Hash algorithm ('sha256', 'md5', etc.). Default: 'sha256'

        Returns:
            Hex digest of file checksum

        Example:
            checksum = processor._compute_file_checksum(Path("dump.xml.bz2"))
            # Returns: "a3f5b8c9d2e1f0..."
        """
        # Delegate to DataManager (service extraction pattern)
        return self.data_manager.compute_file_checksum(filepath, algorithm)
