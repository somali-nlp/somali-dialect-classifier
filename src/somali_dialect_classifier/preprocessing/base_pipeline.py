"""
Base pipeline orchestrator for all data sources.

Eliminates duplication by providing shared orchestration logic:
- Logging setup and progress tracking
- Record batching and processing flow
- Silver dataset writing
- Error handling

Subclasses only implement source-specific logic:
- download() - How to fetch raw data
- extract() - How to parse into staging format
- _extract_records() - How to yield RawRecords for processing
- _create_cleaner() - Which text cleaner to use
"""

from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Optional, List, Tuple, Callable
from pathlib import Path
from datetime import datetime, timezone
import logging
from collections import Counter

from .data_processor import DataProcessor
from .text_cleaners import TextCleaningPipeline
from .record_utils import build_silver_record
from .silver_writer import SilverDatasetWriter
from ..config import get_config


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
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a raw record.

        Args:
            title: Document title
            text: Raw text content (will be cleaned)
            url: Source URL
            metadata: Additional source-specific metadata
        """
        self.title = title
        self.text = text
        self.url = url
        self.metadata = metadata or {}


class BasePipeline(DataProcessor, ABC):
    """
    Reusable orchestration layer for all data sources.

    Provides:
    - Consistent directory structure
    - Shared processing flow (no duplication!)
    - Standardized logging
    - Silver dataset writing

    Subclasses implement:
    - download() - Source-specific data acquisition
    - extract() - Source-specific parsing to staging
    - _extract_records() - Yield RawRecords from staging
    - _create_cleaner() - Which text cleaner to use
    - _get_source_type() - Source type (wiki, news, social, etc.)
    - _get_license() - License information
    - _get_language() - Language code
    - _get_source_metadata() - Source-specific metadata for silver records
    """

    def __init__(
        self,
        source: str,
        log_frequency: int = 1000,
        batch_size: Optional[int] = None,
        force: bool = False,
    ):
        """
        Initialize base pipeline.

        Args:
            source: Source name (e.g., "Wikipedia-Somali", "BBC-Somali")
            log_frequency: Log progress every N records (default: 1000)
            batch_size: Write silver dataset in batches of N records (None = all at once)
            force: Force reprocessing even if output files exist (default: False)
        """
        self.source = source
        self.log_frequency = log_frequency
        self.batch_size = batch_size
        self.force = force
        self.logger = logging.getLogger(__name__)

        # Timestamp for partitioning
        self.date_accessed = datetime.now(timezone.utc).date().isoformat()

        # Load config for directory paths
        config = get_config()

        # Consistent directory structure using config paths
        self.raw_dir = config.data.raw_dir / f"source={source}" / f"date_accessed={self.date_accessed}"
        self.staging_dir = config.data.staging_dir / f"source={source}" / f"date_accessed={self.date_accessed}"
        self.processed_dir = config.data.processed_dir / f"source={source}" / f"date_processed={self.date_accessed}"

        # Initialize shared utilities
        self.text_cleaner = self._create_cleaner()
        self.silver_writer = SilverDatasetWriter()

        # Record filters for quality control
        # List of (filter_func, kwargs) tuples
        # Each filter_func signature: (cleaned_text: str, **kwargs) -> (bool, Dict[str, Any])
        self.record_filters: List[Tuple[Callable, Dict[str, Any]]] = []
        self._register_filters()  # Subclasses override to add filters

        # Subclasses set these paths
        self.staging_file = None
        self.processed_file = None

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
    def _create_cleaner(self) -> TextCleaningPipeline:
        """
        Create source-specific text cleaner.

        Returns:
            TextCleaningPipeline configured for this source

        Example:
            return create_wikipedia_cleaner()  # or create_html_cleaner()
        """
        pass

    @abstractmethod
    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file (source-specific).

        This is the key method where source-specific logic lives.
        The base class handles everything else.

        Yields:
            RawRecord objects with title, text, url, and metadata

        Example (Wikipedia):
            for page in self._parse_xml():
                yield RawRecord(
                    title=page.title,
                    text=page.text,
                    url=self._title_to_url(page.title),
                    metadata={}
                )
        """
        pass

    @abstractmethod
    def _get_source_type(self) -> str:
        """
        Get source type for silver records.

        Returns:
            Source type (e.g., "wiki", "news", "social")
        """
        pass

    @abstractmethod
    def _get_license(self) -> str:
        """
        Get license information for silver records.

        Returns:
            License string (e.g., "CC-BY-SA-3.0", "BBC Terms of Use")
        """
        pass

    @abstractmethod
    def _get_language(self) -> str:
        """
        Get language code for silver records.

        Returns:
            ISO 639-1 language code (e.g., "so" for Somali)
        """
        pass

    @abstractmethod
    def _get_source_metadata(self) -> Dict[str, Any]:
        """
        Get source-specific metadata for silver records.

        Returns:
            Dictionary with source-specific metadata

        Example (Wikipedia):
            return {"wiki_code": "sowiki", "dump_url": self.dump_url}
        """
        pass

    def process(self) -> Path:
        """
        Shared processing orchestration (NO MORE DUPLICATION!).

        This method:
        1. Iterates through records from _extract_records()
        2. Cleans text using self.text_cleaner
        3. Builds silver records
        4. Logs progress consistently
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

        with open(self.processed_file, 'w', encoding='utf-8') as fout:
            for raw_record in self._extract_records():
                # Shared text cleaning
                cleaned = self.text_cleaner.clean(raw_record.text)

                if not cleaned:
                    records_filtered += 1
                    filter_stats["empty_after_cleaning"] += 1
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
                    pipeline_version="1.0.0",
                    source_metadata=merged_metadata,
                    date_published=raw_record.metadata.get('date_published'),
                    topic=raw_record.metadata.get('topic'),
                )
                records.append(record)
                records_processed += 1

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
            self.silver_writer.write(
                records=records,
                source=self.source,
                date_accessed=self.date_accessed,
            )

        return self.processed_file

    def _write_batch(self, records: list) -> None:
        """Write a batch of records to silver dataset."""
        if records:
            self.logger.info(f"Writing batch of {len(records)} records...")
            self.silver_writer.write(
                records=records,
                source=self.source,
                date_accessed=self.date_accessed,
            )

    def run(self) -> Path:
        """
        Template method - orchestrates full pipeline.

        Returns:
            Path to processed file
        """
        self.download()
        self.extract()
        return self.process()

    def save(self, processed_data: str) -> None:
        """
        Save processed data (legacy method from DataProcessor).

        Note: In the new architecture, saving is handled by process().
        This method is kept for backward compatibility but is not used.
        """
        with open(self.processed_file, 'w', encoding='utf-8') as f:
            f.write(processed_data)
