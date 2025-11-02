"""
Metrics collection and quality reporting utilities.

Provides:
- MetricsCollector for tracking pipeline metrics
- QualityReporter for generating markdown reports
- JSON export for metrics (Prometheus migration path)
- Statistical analysis of pipeline performance
- Layered metrics architecture for clear separation of concerns
- Type-safe metric validation and factory functions

PHASE 1 REFACTORING (2025-10-26):
- Renamed metrics to be semantically accurate per pipeline type:
  * Web scraping: http_request_success_rate, content_extraction_success_rate
  * File processing: file_extraction_success_rate, record_parsing_success_rate
  * Stream processing: stream_connection_success_rate, record_retrieval_success_rate
- Fixed BBC test limit bug (only count attempted URLs, not discovered)
- Added metric semantics metadata for clarity
- Deprecated old 'fetch_success_rate' (backward compatible for 1 version)

PHASE 2 REFACTORING (2025-10-26):
- Implemented layered metrics architecture:
  * Layer 1: Connectivity (can we reach the source?)
  * Layer 2: Extraction (can we retrieve data? - pipeline-specific)
  * Layer 3: Quality (does data meet standards?)
  * Layer 4: Volume (how much data?)
- Added pipeline-specific extraction metric classes (WebScraping, FileProcessing, Streaming)
- Each layer has clear purpose and separation of concerns

PHASE 3 REFACTORING (2025-10-26):
- Added type safety with validation methods for each metric class
- Created factory functions to prevent mixing metric types
- Implemented Prometheus export format for observability
- Added schema versioning for backward compatibility tracking
- Validation catches logical inconsistencies before export
"""

import json
import time
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import statistics


class PipelineType(Enum):
    """
    Defines the type of pipeline for appropriate metrics tracking.

    - WEB_SCRAPING: URL-based web scrapers (BBC)
    - FILE_PROCESSING: File/dump processors (Wikipedia, Språkbanken)
    - STREAM_PROCESSING: API streamers (HuggingFace)
    """
    WEB_SCRAPING = "web_scraping"
    FILE_PROCESSING = "file_processing"
    STREAM_PROCESSING = "stream_processing"


# ============================================================================
# PHASE 2: LAYERED METRICS ARCHITECTURE
# ============================================================================
# Layer 1: Connectivity - Can we reach the source?
# Layer 2: Extraction - Can we retrieve data? (pipeline-specific)
# Layer 3: Quality - Does data meet standards?
# Layer 4: Volume - How much data?
# ============================================================================


@dataclass
class ConnectivityMetrics:
    """
    Layer 1: Source connectivity metrics.

    Tracks whether we can establish a connection to the data source.
    This is the first layer - without connectivity, nothing else matters.
    """
    connection_attempted: bool = False
    connection_successful: bool = False
    connection_duration_ms: float = 0.0
    connection_error: Optional[str] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency of connectivity metrics."""
        if self.connection_successful and not self.connection_attempted:
            return False, "Connection marked successful but not attempted"

        if self.connection_duration_ms < 0:
            return False, f"Connection duration cannot be negative: {self.connection_duration_ms}"

        if self.connection_successful and self.connection_error:
            return False, "Connection successful but error message present"

        if not self.connection_successful and self.connection_attempted and not self.connection_error:
            # Warning, not error - error message might not always be captured
            pass

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class ExtractionMetrics:
    """
    Layer 2: Data extraction metrics (base class).

    This is an abstract base class. Use pipeline-specific subclasses:
    - WebScrapingExtractionMetrics for HTTP-based scraping
    - FileProcessingExtractionMetrics for file I/O
    - StreamProcessingExtractionMetrics for API streaming
    """

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency. Subclasses should override."""
        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class WebScrapingExtractionMetrics(ExtractionMetrics):
    """
    Extraction metrics for web scraping pipelines (BBC).

    Tracks HTTP requests, response codes, and content extraction.
    """
    http_requests_attempted: int = 0
    http_requests_successful: int = 0
    http_status_distribution: Dict[int, int] = field(default_factory=dict)
    pages_parsed: int = 0
    content_extracted: int = 0

    @property
    def http_success_rate(self) -> float:
        """Calculate HTTP request success rate."""
        if self.http_requests_attempted == 0:
            return 0.0
        return self.http_requests_successful / self.http_requests_attempted

    @property
    def content_extraction_rate(self) -> float:
        """Calculate content extraction success rate."""
        if self.pages_parsed == 0:
            return 0.0
        return self.content_extracted / self.pages_parsed

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency of web scraping metrics."""
        if self.http_requests_successful > self.http_requests_attempted:
            return False, f"Successful requests ({self.http_requests_successful}) exceed attempted ({self.http_requests_attempted})"

        if self.content_extracted > self.pages_parsed:
            return False, f"Extracted content ({self.content_extracted}) exceeds parsed pages ({self.pages_parsed})"

        if self.pages_parsed > self.http_requests_successful:
            return False, f"Parsed pages ({self.pages_parsed}) exceed successful requests ({self.http_requests_successful})"

        if self.http_success_rate < 0 or self.http_success_rate > 1:
            return False, f"HTTP success rate out of bounds: {self.http_success_rate}"

        # Validate status distribution
        if self.http_status_distribution:
            total_statuses = sum(self.http_status_distribution.values())
            if total_statuses > self.http_requests_attempted:
                return False, f"Status distribution total ({total_statuses}) exceeds attempted requests"

        return True, None


@dataclass
class FileProcessingExtractionMetrics(ExtractionMetrics):
    """
    Extraction metrics for file processing pipelines (Wikipedia, Språkbanken).

    Tracks file discovery, processing, and record extraction.
    """
    files_discovered: int = 0
    files_processed: int = 0
    files_failed: int = 0
    records_extracted: int = 0
    extraction_errors: Dict[str, int] = field(default_factory=dict)

    @property
    def file_extraction_rate(self) -> float:
        """Calculate file extraction success rate."""
        if self.files_discovered == 0:
            return 0.0
        return self.files_processed / self.files_discovered

    @property
    def extraction_efficiency(self) -> float:
        """Calculate average records per file processed."""
        if self.files_processed == 0:
            return 0.0
        return self.records_extracted / self.files_processed

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency of file processing metrics."""
        if self.files_processed > self.files_discovered:
            return False, f"Processed files ({self.files_processed}) exceed discovered ({self.files_discovered})"

        if self.files_processed + self.files_failed > self.files_discovered:
            return False, f"Processed + failed ({self.files_processed + self.files_failed}) exceed discovered ({self.files_discovered})"

        if self.file_extraction_rate < 0 or self.file_extraction_rate > 1:
            return False, f"File extraction rate out of bounds: {self.file_extraction_rate}"

        if self.extraction_efficiency < 0:
            return False, f"Extraction efficiency cannot be negative: {self.extraction_efficiency}"

        return True, None


@dataclass
class StreamProcessingExtractionMetrics(ExtractionMetrics):
    """
    Extraction metrics for streaming pipelines (HuggingFace).

    Tracks stream connection, batching, and record retrieval.
    """
    stream_opened: bool = False
    total_records_available: Optional[int] = None
    batches_attempted: int = 0
    batches_completed: int = 0
    batches_failed: int = 0
    records_fetched: int = 0

    @property
    def stream_reliability(self) -> float:
        """Calculate stream batch completion reliability."""
        total = self.batches_completed + self.batches_failed
        if total == 0:
            return 0.0
        return self.batches_completed / total

    @property
    def dataset_coverage_rate(self) -> Optional[float]:
        """Calculate dataset coverage (if total size known)."""
        if self.total_records_available is None or self.total_records_available == 0:
            return None
        return self.records_fetched / self.total_records_available

    @property
    def stream_completion_rate(self) -> float:
        """Calculate batch completion rate."""
        if self.batches_attempted == 0:
            return 0.0
        return self.batches_completed / self.batches_attempted

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency of stream processing metrics."""
        if not self.stream_opened and self.records_fetched > 0:
            return False, "Stream not opened but records were fetched"

        if self.batches_completed > self.batches_attempted:
            return False, f"Completed batches ({self.batches_completed}) exceed attempted ({self.batches_attempted})"

        if self.batches_completed + self.batches_failed > self.batches_attempted:
            return False, f"Completed + failed batches exceed attempted"

        if self.stream_reliability < 0 or self.stream_reliability > 1:
            return False, f"Stream reliability out of bounds: {self.stream_reliability}"

        coverage = self.dataset_coverage_rate
        if coverage is not None and (coverage < 0 or coverage > 1):
            return False, f"Dataset coverage rate out of bounds: {coverage}"

        return True, None


@dataclass
class QualityMetrics:
    """
    Layer 3: Data quality metrics (consistent across all pipelines).

    Tracks quality filtering, validation, and filter reasons.
    """
    records_received: int = 0
    records_passed_filters: int = 0
    filter_breakdown: Dict[str, int] = field(default_factory=dict)

    @property
    def quality_pass_rate(self) -> float:
        """Calculate quality filter pass rate."""
        if self.records_received == 0:
            return 0.0
        return self.records_passed_filters / self.records_received

    @property
    def total_filtered(self) -> int:
        """Calculate total records filtered out."""
        return self.records_received - self.records_passed_filters

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency of quality metrics."""
        if self.records_passed_filters > self.records_received:
            return False, f"Passed records ({self.records_passed_filters}) exceed received ({self.records_received})"

        if self.quality_pass_rate < 0 or self.quality_pass_rate > 1:
            return False, f"Quality pass rate out of bounds: {self.quality_pass_rate}"

        # Validate filter breakdown sums correctly
        if self.filter_breakdown:
            filter_sum = sum(self.filter_breakdown.values())
            if filter_sum > self.total_filtered:
                return False, f"Filter breakdown sum ({filter_sum}) exceeds total filtered ({self.total_filtered})"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class VolumeMetrics:
    """
    Layer 4: Data volume metrics.

    Tracks the amount of data processed, downloaded, and written.
    """
    records_written: int = 0
    bytes_downloaded: int = 0
    total_chars: int = 0

    @property
    def avg_record_size_bytes(self) -> float:
        """Calculate average record size in bytes."""
        if self.records_written == 0:
            return 0.0
        return self.bytes_downloaded / self.records_written

    @property
    def avg_record_length_chars(self) -> float:
        """Calculate average record length in characters."""
        if self.records_written == 0:
            return 0.0
        return self.total_chars / self.records_written

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency of volume metrics."""
        if self.records_written < 0:
            return False, f"Records written cannot be negative: {self.records_written}"

        if self.bytes_downloaded < 0:
            return False, f"Bytes downloaded cannot be negative: {self.bytes_downloaded}"

        if self.total_chars < 0:
            return False, f"Total chars cannot be negative: {self.total_chars}"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


# ============================================================================
# PHASE 3: TYPE SAFETY & FACTORY FUNCTIONS
# ============================================================================


def create_extraction_metrics(
    pipeline_type: Union[str, PipelineType],
    **kwargs
) -> ExtractionMetrics:
    """
    Factory function to create appropriate extraction metrics for pipeline type.

    Ensures type safety by preventing mixing of metric types across pipelines.

    Args:
        pipeline_type: Pipeline type (enum or string)
        **kwargs: Metric-specific fields

    Returns:
        Appropriate ExtractionMetrics subclass instance

    Raises:
        ValueError: If pipeline type is unknown

    Example:
        >>> metrics = create_extraction_metrics(
        ...     PipelineType.WEB_SCRAPING,
        ...     http_requests_attempted=100,
        ...     http_requests_successful=95
        ... )
        >>> assert isinstance(metrics, WebScrapingExtractionMetrics)
    """
    # Convert enum to string if needed
    if isinstance(pipeline_type, PipelineType):
        pipeline_type = pipeline_type.value

    if pipeline_type == PipelineType.WEB_SCRAPING.value:
        return WebScrapingExtractionMetrics(**kwargs)
    elif pipeline_type == PipelineType.FILE_PROCESSING.value:
        return FileProcessingExtractionMetrics(**kwargs)
    elif pipeline_type == PipelineType.STREAM_PROCESSING.value:
        return StreamProcessingExtractionMetrics(**kwargs)
    else:
        raise ValueError(f"Unknown pipeline type: {pipeline_type}. Must be one of: {[t.value for t in PipelineType]}")


def validate_layered_metrics(
    connectivity: ConnectivityMetrics,
    extraction: ExtractionMetrics,
    quality: QualityMetrics,
    volume: VolumeMetrics
) -> Tuple[bool, List[str]]:
    """
    Validate all layered metrics for consistency.

    Args:
        connectivity: Layer 1 metrics
        extraction: Layer 2 metrics
        quality: Layer 3 metrics
        volume: Layer 4 metrics

    Returns:
        Tuple of (all_valid, list_of_errors)

    Example:
        >>> valid, errors = validate_layered_metrics(conn, extr, qual, vol)
        >>> if not valid:
        ...     print(f"Validation failed: {errors}")
    """
    errors = []

    # Validate each layer
    for layer_name, layer_metrics in [
        ("Connectivity", connectivity),
        ("Extraction", extraction),
        ("Quality", quality),
        ("Volume", volume)
    ]:
        is_valid, error = layer_metrics.validate()
        if not is_valid:
            errors.append(f"{layer_name}: {error}")

    # Cross-layer validation
    # Volume records written should not exceed quality records passed
    if volume.records_written > quality.records_passed_filters:
        errors.append(
            f"Volume: Records written ({volume.records_written}) exceeds "
            f"quality-passed records ({quality.records_passed_filters})"
        )

    # If no connection, extraction metrics should be zero
    if not connectivity.connection_successful:
        if isinstance(extraction, WebScrapingExtractionMetrics):
            if extraction.http_requests_successful > 0:
                errors.append("Connectivity failed but HTTP requests succeeded")
        elif isinstance(extraction, FileProcessingExtractionMetrics):
            if extraction.files_processed > 0:
                errors.append("Connectivity failed but files were processed")
        elif isinstance(extraction, StreamProcessingExtractionMetrics):
            if extraction.stream_opened:
                errors.append("Connectivity failed but stream was opened")

    return len(errors) == 0, errors


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: str
    run_id: str
    source: str
    duration_seconds: float
    pipeline_type: str = "web_scraping"  # Default for backward compatibility

    # Web scraping counters (BBC)
    urls_discovered: int = 0
    urls_fetched: int = 0
    urls_processed: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    urls_deduplicated: int = 0

    # File processing counters (Wikipedia, Språkbanken)
    files_discovered: int = 0
    files_processed: int = 0
    records_extracted: int = 0

    # Stream processing counters (HuggingFace)
    datasets_opened: int = 0
    records_fetched: int = 0
    records_processed: int = 0
    batches_completed: int = 0

    # Common counters
    bytes_downloaded: int = 0
    records_written: int = 0

    # NEW: Quality filtering counters (separate from fetch success)
    records_filtered: int = 0  # Total records filtered out by quality checks

    # Distributions
    http_status_codes: Dict[int, int] = field(default_factory=dict)
    filter_reasons: Dict[str, int] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)

    # Timing statistics (milliseconds)
    fetch_durations_ms: List[float] = field(default_factory=list)
    process_durations_ms: List[float] = field(default_factory=list)

    # Text length statistics
    text_lengths: List[int] = field(default_factory=list)

    # Quality metrics
    unique_hashes: int = 0
    duplicate_hashes: int = 0
    near_duplicates: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate derived statistics based on pipeline type.

        Returns pipeline-specific metrics with semantically accurate names:
        - Web scraping: http_request_success_rate, content_extraction_success_rate
        - File processing: file_extraction_success_rate, record_parsing_success_rate
        - Stream processing: stream_connection_success_rate, record_retrieval_success_rate

        All pipelines include: quality_pass_rate, deduplication_rate
        """
        stats = {}

        # Calculate success rate based on pipeline type
        if self.pipeline_type == PipelineType.WEB_SCRAPING.value:
            # ============================================================
            # WEB SCRAPING METRICS (BBC)
            # ============================================================
            # FIXED: Only count actually attempted URLs, not discovered URLs
            # This fixes the bug where test limits made success rates look artificially low
            total_attempted = self.urls_fetched + self.urls_failed

            if total_attempted > 0:
                # NEW METRIC: http_request_success_rate
                # Network-level HTTP success (2xx responses)
                http_success_count = self.http_status_codes.get(200, 0)
                if http_success_count > 0:
                    stats["http_request_success_rate"] = http_success_count / total_attempted
                else:
                    # Fallback: use urls_fetched if HTTP status not tracked
                    stats["http_request_success_rate"] = self.urls_fetched / total_attempted

                # NEW METRIC: content_extraction_success_rate
                # Content successfully extracted from HTTP responses
                # This is separate from HTTP success (you can get 200 OK but fail to extract content)
                if self.urls_fetched > 0:
                    stats["content_extraction_success_rate"] = self.urls_fetched / self.urls_fetched  # Always 1.0 for now
                else:
                    stats["content_extraction_success_rate"] = 0.0

                stats["http_request_failure_rate"] = self.urls_failed / total_attempted if total_attempted > 0 else 0

                # Quality pass rate: records that passed quality filters
                # Percentage of non-duplicate records that passed quality filters
                # Formula: records_written / (records_written + records_filtered)
                # BACKWARD COMPATIBILITY: For web scraping, if records_written is not set,
                # fall back to urls_processed (they're equivalent for web scraping)
                records_written = self.records_written if self.records_written > 0 else self.urls_processed
                total_non_dup_records = records_written + self.records_filtered
                if total_non_dup_records > 0:
                    stats["quality_pass_rate"] = records_written / total_non_dup_records
                else:
                    stats["quality_pass_rate"] = 0

                stats["deduplication_rate"] = (self.urls_deduplicated / total_attempted) if total_attempted > 0 else 0

                # DEPRECATED: Keep for backward compatibility (1 version)
                stats["fetch_success_rate"] = stats["http_request_success_rate"]
                stats["fetch_failure_rate"] = stats["http_request_failure_rate"]
            else:
                stats["http_request_success_rate"] = 0
                stats["content_extraction_success_rate"] = 0
                stats["http_request_failure_rate"] = 0
                stats["quality_pass_rate"] = 0
                stats["deduplication_rate"] = 0
                # DEPRECATED
                stats["fetch_success_rate"] = 0
                stats["fetch_failure_rate"] = 0

        elif self.pipeline_type == PipelineType.FILE_PROCESSING.value:
            # ============================================================
            # FILE PROCESSING METRICS (Wikipedia, Språkbanken)
            # ============================================================
            # NEW METRIC: file_extraction_success_rate
            # File-level extraction success (local file I/O, not HTTP)
            if self.files_discovered > 0:
                stats["file_extraction_success_rate"] = (self.files_processed / self.files_discovered)
                stats["file_extraction_failure_rate"] = 1 - stats["file_extraction_success_rate"]
            elif self.records_extracted > 0:
                # If no files tracked but records extracted, assume 100% success
                stats["file_extraction_success_rate"] = 1.0
                stats["file_extraction_failure_rate"] = 0
            else:
                stats["file_extraction_success_rate"] = 0
                stats["file_extraction_failure_rate"] = 0

            # NEW METRIC: record_parsing_success_rate
            # Record-level parsing success from extracted files
            total_extracted = self.records_extracted if self.records_extracted > 0 else 0
            if total_extracted > 0:
                # Assume all extracted records were parseable (can be refined later)
                stats["record_parsing_success_rate"] = 1.0
            else:
                stats["record_parsing_success_rate"] = 0.0

            # Quality pass rate for file processing
            # Percentage of non-duplicate records that passed quality filters
            # Formula: records_written / (records_written + records_filtered)
            total_non_dup_records = self.records_written + self.records_filtered
            if total_non_dup_records > 0:
                stats["quality_pass_rate"] = self.records_written / total_non_dup_records
            else:
                stats["quality_pass_rate"] = 0

            # Add deduplication rate for file processing
            total_records = self.records_extracted if self.records_extracted > 0 else self.records_written
            if total_records > 0:
                stats["deduplication_rate"] = (self.duplicate_hashes + self.near_duplicates) / total_records
            else:
                stats["deduplication_rate"] = 0

            # DEPRECATED: Keep for backward compatibility (1 version)
            stats["fetch_success_rate"] = stats["file_extraction_success_rate"]
            stats["fetch_failure_rate"] = stats["file_extraction_failure_rate"]

        elif self.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            # ============================================================
            # STREAM PROCESSING METRICS (HuggingFace)
            # ============================================================
            # NEW METRIC: stream_connection_success_rate
            # Boolean: stream opened successfully (1.0) or failed (0.0)
            if self.records_fetched > 0:
                stats["stream_connection_success_rate"] = 1.0
            else:
                stats["stream_connection_success_rate"] = 0.0

            # NEW METRIC: record_retrieval_success_rate
            # Actual records received vs what we attempted to fetch
            # For now, if we got records, assume 100% of attempted fetches succeeded
            if self.records_fetched > 0:
                stats["record_retrieval_success_rate"] = 1.0
            else:
                stats["record_retrieval_success_rate"] = 0.0

            # NEW METRIC: dataset_coverage_rate
            # Records received / total dataset size (if known)
            # For now, set to None (unknown) - can be enhanced when dataset size is tracked
            stats["dataset_coverage_rate"] = None  # Unknown - needs dataset metadata

            # Quality pass rate: records that passed quality filters
            # Percentage of non-duplicate records that passed quality filters
            # Formula: records_written / (records_written + records_filtered)
            # BACKWARD COMPATIBILITY: For streaming, if records_written is not set,
            # fall back to records_processed (they're equivalent for streaming)
            records_written = self.records_written if self.records_written > 0 else self.records_processed
            total_non_dup_records = records_written + self.records_filtered
            if total_non_dup_records > 0:
                stats["quality_pass_rate"] = records_written / total_non_dup_records
            else:
                stats["quality_pass_rate"] = 0

            # Add deduplication rate for streaming
            if self.records_fetched > 0:
                stats["deduplication_rate"] = (self.duplicate_hashes + self.near_duplicates) / self.records_fetched
            else:
                stats["deduplication_rate"] = 0

            # DEPRECATED: Keep for backward compatibility (1 version)
            stats["fetch_success_rate"] = stats["stream_connection_success_rate"]
            stats["fetch_failure_rate"] = 1.0 - stats["stream_connection_success_rate"]
        else:
            # Backward compatibility: default to web scraping logic
            total_attempts = self.urls_fetched
            if total_attempts > 0:
                stats["fetch_success_rate"] = (self.urls_processed / total_attempts)
                stats["fetch_failure_rate"] = (self.urls_failed / total_attempts)
                stats["deduplication_rate"] = (self.urls_deduplicated / total_attempts)
            else:
                stats["fetch_success_rate"] = 0
                stats["fetch_failure_rate"] = 0
                stats["deduplication_rate"] = 0

            # Quality pass rate: consistent formula across all pipeline types
            total_non_dup_records = self.records_written + self.records_filtered
            if total_non_dup_records > 0:
                stats["quality_pass_rate"] = self.records_written / total_non_dup_records
            else:
                stats["quality_pass_rate"] = 0

        # Timing statistics
        if self.fetch_durations_ms:
            stats["fetch_duration_stats"] = {
                "min": min(self.fetch_durations_ms),
                "max": max(self.fetch_durations_ms),
                "mean": statistics.mean(self.fetch_durations_ms),
                "median": statistics.median(self.fetch_durations_ms),
                "p95": self._percentile(self.fetch_durations_ms, 95),
                "p99": self._percentile(self.fetch_durations_ms, 99)
            }

        if self.process_durations_ms:
            stats["process_duration_stats"] = {
                "min": min(self.process_durations_ms),
                "max": max(self.process_durations_ms),
                "mean": statistics.mean(self.process_durations_ms),
                "median": statistics.median(self.process_durations_ms),
                "p95": self._percentile(self.process_durations_ms, 95),
                "p99": self._percentile(self.process_durations_ms, 99)
            }

        # Text length statistics
        if self.text_lengths:
            stats["text_length_stats"] = {
                "min": min(self.text_lengths),
                "max": max(self.text_lengths),
                "mean": statistics.mean(self.text_lengths),
                "median": statistics.median(self.text_lengths),
                "total_chars": sum(self.text_lengths)
            }

        # Throughput
        if self.duration_seconds > 0:
            stats["throughput"] = {
                "urls_per_second": self.urls_processed / self.duration_seconds,
                "bytes_per_second": self.bytes_downloaded / self.duration_seconds,
                "records_per_minute": (self.records_written / self.duration_seconds) * 60
            }

        # Add metric semantics metadata for clarity
        stats["_metric_semantics"] = self._get_metric_semantics()
        stats["_deprecation_warnings"] = self._get_deprecation_warnings()

        # Validate quality_pass_rate is between 0 and 1
        if "quality_pass_rate" in stats:
            qpr = stats["quality_pass_rate"]
            if qpr < 0 or qpr > 1:
                self.logger.error(
                    f"VALIDATION ERROR: quality_pass_rate out of range: {qpr} "
                    f"(should be 0-1). This indicates a bug in metric calculation. "
                    f"Pipeline: {self.pipeline_type}, "
                    f"records_written={self.records_written}, "
                    f"records_filtered={self.records_filtered}"
                )
                # Clamp to valid range to prevent downstream errors
                stats["quality_pass_rate"] = max(0.0, min(1.0, qpr))
                stats["_validation_warnings"] = stats.get("_validation_warnings", [])
                stats["_validation_warnings"].append(
                    f"quality_pass_rate clamped from {qpr} to {stats['quality_pass_rate']}"
                )

        return stats

    def _get_metric_semantics(self) -> Dict[str, str]:
        """
        Return semantic descriptions for metrics based on pipeline type.

        This clarifies what each metric actually measures to prevent confusion.
        """
        if self.pipeline_type == PipelineType.WEB_SCRAPING.value:
            return {
                "http_request_success_rate": "Network-level HTTP success (2xx responses / attempted requests)",
                "content_extraction_success_rate": "Content successfully extracted from HTTP responses",
                "quality_pass_rate": "Records passing quality filters (after deduplication)",
                "deduplication_rate": "Records filtered as duplicates",
                "fetch_success_rate": "DEPRECATED: Use http_request_success_rate instead"
            }
        elif self.pipeline_type == PipelineType.FILE_PROCESSING.value:
            return {
                "file_extraction_success_rate": "File-level extraction success (local file I/O, not HTTP)",
                "record_parsing_success_rate": "Record-level parsing success from extracted files",
                "quality_pass_rate": "Records passing quality filters (after deduplication)",
                "deduplication_rate": "Records filtered as duplicates",
                "fetch_success_rate": "DEPRECATED: Use file_extraction_success_rate instead"
            }
        elif self.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            return {
                "stream_connection_success_rate": "Stream connection established (boolean: 1.0 or 0.0)",
                "record_retrieval_success_rate": "Records successfully retrieved from stream",
                "dataset_coverage_rate": "Fraction of total dataset consumed (if known)",
                "quality_pass_rate": "Records passing quality filters (after deduplication)",
                "deduplication_rate": "Records filtered as duplicates",
                "fetch_success_rate": "DEPRECATED: Use stream_connection_success_rate instead"
            }
        else:
            return {
                "fetch_success_rate": "Generic success rate (pipeline type unknown)"
            }

    def _get_deprecation_warnings(self) -> List[str]:
        """
        Return deprecation warnings for old metric names.

        These metrics will be removed in the next major version.
        """
        warnings = []
        if self.pipeline_type == PipelineType.WEB_SCRAPING.value:
            warnings.append(
                "fetch_success_rate is deprecated for web scraping. "
                "Use http_request_success_rate for HTTP success and "
                "content_extraction_success_rate for content extraction success."
            )
        elif self.pipeline_type == PipelineType.FILE_PROCESSING.value:
            warnings.append(
                "fetch_success_rate is deprecated for file processing. "
                "Use file_extraction_success_rate instead."
            )
        elif self.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            warnings.append(
                "fetch_success_rate is deprecated for stream processing. "
                "Use stream_connection_success_rate and record_retrieval_success_rate instead."
            )
        return warnings

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]


class MetricsCollector:
    """
    Collects and tracks metrics during pipeline execution.
    """

    def __init__(self, run_id: str, source: str, pipeline_type: Optional[PipelineType] = None):
        """
        Initialize metrics collector.

        Args:
            run_id: Unique run identifier
            source: Data source name
            pipeline_type: Type of pipeline (WEB_SCRAPING, FILE_PROCESSING, STREAM_PROCESSING)
        """
        self.run_id = run_id
        self.source = source
        self.pipeline_type = pipeline_type or PipelineType.WEB_SCRAPING
        self.start_time = time.time()

        # Initialize counters
        self.counters = defaultdict(int)

        # Initialize distributions
        self.distributions = {
            "http_status_codes": Counter(),
            "filter_reasons": Counter(),
            "error_types": Counter()
        }

        # Initialize timing lists
        self.timings = {
            "fetch_durations_ms": [],
            "process_durations_ms": []
        }

        # Initialize text statistics
        self.text_lengths = []

        # Unique hash tracking for deduplication
        self.unique_hashes = set()
        self.duplicate_count = 0
        self.near_duplicate_count = 0

    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric."""
        self.counters[metric] += value

    def record_http_status(self, status_code: int):
        """Record HTTP status code."""
        self.distributions["http_status_codes"][status_code] += 1

    def record_filter_reason(self, reason: str):
        """Record why a record was filtered."""
        self.distributions["filter_reasons"][reason] += 1

    def record_error(self, error_type: str):
        """Record error type."""
        self.distributions["error_types"][error_type] += 1

    def record_fetch_duration(self, duration_ms: float):
        """Record fetch duration in milliseconds."""
        self.timings["fetch_durations_ms"].append(duration_ms)

    def record_process_duration(self, duration_ms: float):
        """Record processing duration in milliseconds."""
        self.timings["process_durations_ms"].append(duration_ms)

    def record_text_length(self, length: int):
        """Record text length in characters."""
        self.text_lengths.append(length)

    def record_hash(self, text_hash: str) -> bool:
        """
        Record text hash for deduplication tracking.

        Returns:
            True if unique, False if duplicate
        """
        if text_hash in self.unique_hashes:
            self.duplicate_count += 1
            self.increment("duplicate_hashes")
            self.increment("urls_deduplicated")  # Backward compatibility
            return False
        else:
            self.unique_hashes.add(text_hash)
            self.increment("unique_hashes")
            return True

    def record_near_duplicate(self):
        """Record near-duplicate found."""
        self.near_duplicate_count += 1
        self.increment("near_duplicates")

    def get_snapshot(self) -> MetricSnapshot:
        """Get current metrics snapshot."""
        duration = time.time() - self.start_time

        return MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            source=self.source,
            duration_seconds=duration,
            pipeline_type=self.pipeline_type.value,
            # Web scraping counters
            urls_discovered=self.counters["urls_discovered"],
            urls_fetched=self.counters["urls_fetched"],
            urls_processed=self.counters["urls_processed"],
            urls_failed=self.counters["urls_failed"],
            urls_skipped=self.counters["urls_skipped"],
            urls_deduplicated=self.counters["urls_deduplicated"],
            # File processing counters
            files_discovered=self.counters["files_discovered"],
            files_processed=self.counters["files_processed"],
            records_extracted=self.counters["records_extracted"],
            # Stream processing counters
            datasets_opened=self.counters["datasets_opened"],
            records_fetched=self.counters["records_fetched"],
            records_processed=self.counters["records_processed"],
            batches_completed=self.counters["batches_completed"],
            # Common counters
            bytes_downloaded=self.counters["bytes_downloaded"],
            records_written=self.counters["records_written"],
            records_filtered=self.counters["records_filtered"],
            http_status_codes=dict(self.distributions["http_status_codes"]),
            filter_reasons=dict(self.distributions["filter_reasons"]),
            error_types=dict(self.distributions["error_types"]),
            fetch_durations_ms=self.timings["fetch_durations_ms"][-1000:],  # Last 1000
            process_durations_ms=self.timings["process_durations_ms"][-1000:],
            text_lengths=self.text_lengths[-1000:],  # Last 1000
            unique_hashes=len(self.unique_hashes),
            duplicate_hashes=self.duplicate_count,
            near_duplicates=self.near_duplicate_count
        )

    def get_layered_metrics(self) -> Dict[str, Any]:
        """
        Export metrics in layered structure (Phase 2).

        Returns a dictionary with four layers:
        1. Connectivity: Can we reach the source?
        2. Extraction: Can we retrieve data? (pipeline-specific)
        3. Quality: Does data meet standards?
        4. Volume: How much data?

        Returns:
            Dictionary with layered metrics that can be serialized to JSON

        Example:
            >>> collector = MetricsCollector("test", "BBC", PipelineType.WEB_SCRAPING)
            >>> layered = collector.get_layered_metrics()
            >>> assert "connectivity" in layered
            >>> assert "extraction" in layered
            >>> assert isinstance(layered["extraction"], WebScrapingExtractionMetrics)
        """
        snapshot = self.get_snapshot()
        pipeline_type = snapshot.pipeline_type

        # Layer 1: Connectivity
        # Calculate connection duration from fetch durations if available
        conn_duration_ms = 0.0
        if self.timings["fetch_durations_ms"]:
            conn_duration_ms = self.timings["fetch_durations_ms"][0] if len(self.timings["fetch_durations_ms"]) > 0 else 0.0

        connectivity = ConnectivityMetrics(
            connection_attempted=True,  # If we have any data, connection was attempted
            connection_successful=True,  # Assume success if we have any successful operations
            connection_duration_ms=conn_duration_ms,
            connection_error=None
        )

        # Determine if connection was actually successful based on pipeline type
        if pipeline_type == PipelineType.WEB_SCRAPING.value:
            connectivity.connection_successful = snapshot.urls_fetched > 0 or snapshot.urls_processed > 0
            if not connectivity.connection_successful and snapshot.error_types:
                connectivity.connection_error = list(snapshot.error_types.keys())[0] if snapshot.error_types else None
        elif pipeline_type == PipelineType.FILE_PROCESSING.value:
            connectivity.connection_successful = snapshot.files_processed > 0 or snapshot.records_extracted > 0
        elif pipeline_type == PipelineType.STREAM_PROCESSING.value:
            connectivity.connection_successful = snapshot.datasets_opened > 0 or snapshot.records_fetched > 0

        # Layer 2: Extraction (pipeline-specific)
        extraction: ExtractionMetrics
        if pipeline_type == PipelineType.WEB_SCRAPING.value:
            total_attempted = snapshot.urls_fetched + snapshot.urls_failed
            http_success_count = snapshot.http_status_codes.get(200, 0)
            if http_success_count == 0:
                # Fallback: assume all fetched URLs were successful
                http_success_count = snapshot.urls_fetched

            extraction = WebScrapingExtractionMetrics(
                http_requests_attempted=total_attempted,
                http_requests_successful=http_success_count,
                http_status_distribution=snapshot.http_status_codes,
                pages_parsed=snapshot.urls_fetched,
                content_extracted=snapshot.urls_processed
            )

        elif pipeline_type == PipelineType.FILE_PROCESSING.value:
            extraction = FileProcessingExtractionMetrics(
                files_discovered=snapshot.files_discovered,
                files_processed=snapshot.files_processed,
                files_failed=snapshot.files_discovered - snapshot.files_processed if snapshot.files_discovered > 0 else 0,
                records_extracted=snapshot.records_extracted,
                extraction_errors=snapshot.error_types
            )

        elif pipeline_type == PipelineType.STREAM_PROCESSING.value:
            extraction = StreamProcessingExtractionMetrics(
                stream_opened=snapshot.datasets_opened > 0,
                total_records_available=None,  # Unknown unless tracked
                batches_attempted=snapshot.batches_completed,  # We only track completed for now
                batches_completed=snapshot.batches_completed,
                batches_failed=0,  # Not currently tracked
                records_fetched=snapshot.records_fetched
            )

        else:
            # Fallback for unknown pipeline types
            extraction = ExtractionMetrics()

        # Layer 3: Quality
        # Calculate records received based on pipeline type
        if pipeline_type == PipelineType.WEB_SCRAPING.value:
            records_received = snapshot.urls_fetched - snapshot.urls_deduplicated
        elif pipeline_type == PipelineType.FILE_PROCESSING.value:
            records_received = snapshot.records_extracted - (snapshot.duplicate_hashes + snapshot.near_duplicates)
        elif pipeline_type == PipelineType.STREAM_PROCESSING.value:
            # Handle hybrid streams (Apify-based TikTok vs traditional dataset streams)
            if snapshot.urls_fetched > 0:
                # Apify-style stream - uses urls_fetched like web scraping
                records_received = snapshot.urls_fetched - snapshot.urls_deduplicated
            else:
                # Traditional dataset stream - uses records_fetched
                records_received = snapshot.records_fetched - (snapshot.duplicate_hashes + snapshot.near_duplicates)
        else:
            records_received = snapshot.records_written

        # Sanity check: records_received should be at least records_written
        records_received = max(records_received, snapshot.records_written)

        quality = QualityMetrics(
            records_received=max(records_received, 0),  # Ensure non-negative
            records_passed_filters=snapshot.records_written,
            filter_breakdown=snapshot.filter_reasons
        )

        # Layer 4: Volume
        total_chars = sum(snapshot.text_lengths) if snapshot.text_lengths else 0

        volume = VolumeMetrics(
            records_written=snapshot.records_written,
            bytes_downloaded=snapshot.bytes_downloaded,
            total_chars=total_chars
        )

        return {
            "connectivity": connectivity.to_dict(),
            "extraction": extraction.to_dict(),
            "quality": quality.to_dict(),
            "volume": volume.to_dict()
        }

    def export_json(self, output_path: Path, include_layered: bool = True):
        """
        Export metrics to JSON file with schema versioning (Phase 3).

        Args:
            output_path: Path to save JSON file
            include_layered: Whether to include Phase 2 layered metrics (default: True)

        The exported JSON includes:
        - Schema version for backward compatibility tracking
        - Pipeline type metadata
        - Layered metrics (Phase 2) - optional
        - Legacy flat metrics (Phase 1) - for backward compatibility
        - Validation warnings if metrics are inconsistent
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        snapshot = self.get_snapshot()
        stats = snapshot.calculate_statistics()

        # Build export data with schema versioning
        metrics_data = {
            "_schema_version": "3.0",  # Phase 2/3 schema
            "_pipeline_type": snapshot.pipeline_type,
            "_timestamp": snapshot.timestamp,
            "_run_id": snapshot.run_id,
            "_source": snapshot.source,
        }

        # Add layered metrics if requested
        if include_layered:
            layered = self.get_layered_metrics()
            metrics_data["layered_metrics"] = layered

            # Validate layered metrics
            try:
                # Reconstruct metric objects for validation
                connectivity = ConnectivityMetrics(**layered["connectivity"])
                extraction_dict = layered["extraction"]
                extraction = create_extraction_metrics(snapshot.pipeline_type, **extraction_dict)
                quality = QualityMetrics(**layered["quality"])
                volume = VolumeMetrics(**layered["volume"])

                is_valid, errors = validate_layered_metrics(connectivity, extraction, quality, volume)
                if not is_valid:
                    metrics_data["_validation_warnings"] = errors
                    # Log warnings
                    logger = logging.getLogger(__name__)
                    for error in errors:
                        logger.warning(f"Metric validation warning: {error}")
            except Exception as e:
                metrics_data["_validation_error"] = str(e)

        # Add legacy metrics for backward compatibility
        metrics_data["legacy_metrics"] = {
            "snapshot": snapshot.to_dict(),
            "statistics": stats
        }

        # Write to file
        with open(output_path, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)

    def export_prometheus(self, output_path: Path):
        """
        Export metrics in Prometheus text format (Phase 3).

        Exports metrics in the standard Prometheus exposition format:
        https://prometheus.io/docs/instrumenting/exposition_formats/

        The format includes:
        - HELP text describing each metric
        - TYPE declarations (counter, gauge, histogram)
        - Metric values with labels

        Labels include:
        - source: Data source name
        - pipeline_type: Type of pipeline (web_scraping, file_processing, stream_processing)
        - run_id: Unique run identifier

        Example Prometheus scrape configuration:
            scrape_configs:
              - job_name: 'somali-nlp-pipeline'
                static_configs:
                  - targets: ['localhost:9090']
                file_sd_configs:
                  - files:
                    - '/path/to/metrics/*.prom'
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        snapshot = self.get_snapshot()
        stats = snapshot.calculate_statistics()
        layered = self.get_layered_metrics()
        lines = []

        # Common labels for all metrics
        labels = f'source="{self.source}",pipeline_type="{snapshot.pipeline_type}",run_id="{self.run_id}"'

        # ===================================================================
        # CONNECTIVITY METRICS (Layer 1)
        # ===================================================================
        connectivity = layered["connectivity"]

        lines.extend([
            "# HELP pipeline_connection_attempted Whether connection to data source was attempted",
            "# TYPE pipeline_connection_attempted gauge",
            f'pipeline_connection_attempted{{{labels}}} {1 if connectivity["connection_attempted"] else 0}',
            "",
            "# HELP pipeline_connection_successful Whether connection to data source succeeded",
            "# TYPE pipeline_connection_successful gauge",
            f'pipeline_connection_successful{{{labels}}} {1 if connectivity["connection_successful"] else 0}',
            "",
            "# HELP pipeline_connection_duration_ms Connection establishment duration in milliseconds",
            "# TYPE pipeline_connection_duration_ms gauge",
            f'pipeline_connection_duration_ms{{{labels}}} {connectivity["connection_duration_ms"]}',
            ""
        ])

        # ===================================================================
        # EXTRACTION METRICS (Layer 2 - Pipeline-specific)
        # ===================================================================
        extraction = layered["extraction"]

        if snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value:
            # Web scraping extraction metrics
            lines.extend([
                "# HELP pipeline_http_requests_attempted Total HTTP requests attempted",
                "# TYPE pipeline_http_requests_attempted counter",
                f'pipeline_http_requests_attempted{{{labels}}} {extraction["http_requests_attempted"]}',
                "",
                "# HELP pipeline_http_requests_successful Total successful HTTP requests (2xx)",
                "# TYPE pipeline_http_requests_successful counter",
                f'pipeline_http_requests_successful{{{labels}}} {extraction["http_requests_successful"]}',
                "",
                "# HELP pipeline_http_success_rate HTTP request success rate (0-1)",
                "# TYPE pipeline_http_success_rate gauge",
                f'pipeline_http_success_rate{{{labels}}} {stats.get("http_request_success_rate", 0)}',
                "",
                "# HELP pipeline_pages_parsed Total pages parsed",
                "# TYPE pipeline_pages_parsed counter",
                f'pipeline_pages_parsed{{{labels}}} {extraction["pages_parsed"]}',
                "",
                "# HELP pipeline_content_extracted Total content items extracted",
                "# TYPE pipeline_content_extracted counter",
                f'pipeline_content_extracted{{{labels}}} {extraction["content_extracted"]}',
                ""
            ])

            # HTTP status distribution
            for status_code, count in extraction.get("http_status_distribution", {}).items():
                lines.extend([
                    f'pipeline_http_status_total{{status_code="{status_code}",{labels}}} {count}'
                ])
            if extraction.get("http_status_distribution"):
                lines.append("")

        elif snapshot.pipeline_type == PipelineType.FILE_PROCESSING.value:
            # File processing extraction metrics
            lines.extend([
                "# HELP pipeline_files_discovered Total files discovered",
                "# TYPE pipeline_files_discovered counter",
                f'pipeline_files_discovered{{{labels}}} {extraction["files_discovered"]}',
                "",
                "# HELP pipeline_files_processed Total files successfully processed",
                "# TYPE pipeline_files_processed counter",
                f'pipeline_files_processed{{{labels}}} {extraction["files_processed"]}',
                "",
                "# HELP pipeline_files_failed Total files that failed processing",
                "# TYPE pipeline_files_failed counter",
                f'pipeline_files_failed{{{labels}}} {extraction["files_failed"]}',
                "",
                "# HELP pipeline_file_extraction_rate File extraction success rate (0-1)",
                "# TYPE pipeline_file_extraction_rate gauge",
                f'pipeline_file_extraction_rate{{{labels}}} {stats.get("file_extraction_success_rate", 0)}',
                "",
                "# HELP pipeline_records_extracted Total records extracted from files",
                "# TYPE pipeline_records_extracted counter",
                f'pipeline_records_extracted{{{labels}}} {extraction["records_extracted"]}',
                "",
                "# HELP pipeline_extraction_efficiency Average records per file",
                "# TYPE pipeline_extraction_efficiency gauge",
                f'pipeline_extraction_efficiency{{{labels}}} {extraction["records_extracted"] / max(extraction["files_processed"], 1)}',
                ""
            ])

        elif snapshot.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            # Stream processing extraction metrics
            lines.extend([
                "# HELP pipeline_stream_opened Whether stream was successfully opened",
                "# TYPE pipeline_stream_opened gauge",
                f'pipeline_stream_opened{{{labels}}} {1 if extraction["stream_opened"] else 0}',
                "",
                "# HELP pipeline_batches_attempted Total stream batches attempted",
                "# TYPE pipeline_batches_attempted counter",
                f'pipeline_batches_attempted{{{labels}}} {extraction["batches_attempted"]}',
                "",
                "# HELP pipeline_batches_completed Total stream batches completed",
                "# TYPE pipeline_batches_completed counter",
                f'pipeline_batches_completed{{{labels}}} {extraction["batches_completed"]}',
                "",
                "# HELP pipeline_batches_failed Total stream batches failed",
                "# TYPE pipeline_batches_failed counter",
                f'pipeline_batches_failed{{{labels}}} {extraction["batches_failed"]}',
                "",
                "# HELP pipeline_stream_reliability Batch completion reliability (0-1)",
                "# TYPE pipeline_stream_reliability gauge",
                f'pipeline_stream_reliability{{{labels}}} {stats.get("stream_connection_success_rate", 0)}',
                "",
                "# HELP pipeline_records_fetched Total records fetched from stream",
                "# TYPE pipeline_records_fetched counter",
                f'pipeline_records_fetched{{{labels}}} {extraction["records_fetched"]}',
                ""
            ])

            # Dataset coverage if available
            if extraction.get("total_records_available"):
                coverage = extraction["records_fetched"] / extraction["total_records_available"]
                lines.extend([
                    "# HELP pipeline_dataset_coverage_rate Dataset coverage rate (0-1)",
                    "# TYPE pipeline_dataset_coverage_rate gauge",
                    f'pipeline_dataset_coverage_rate{{{labels}}} {coverage}',
                    ""
                ])

        # ===================================================================
        # QUALITY METRICS (Layer 3 - Common to all pipelines)
        # ===================================================================
        quality = layered["quality"]

        lines.extend([
            "# HELP pipeline_records_received Total records received for quality filtering",
            "# TYPE pipeline_records_received counter",
            f'pipeline_records_received{{{labels}}} {quality["records_received"]}',
            "",
            "# HELP pipeline_records_passed_filters Total records that passed quality filters",
            "# TYPE pipeline_records_passed_filters counter",
            f'pipeline_records_passed_filters{{{labels}}} {quality["records_passed_filters"]}',
            "",
            "# HELP pipeline_quality_pass_rate Quality filter pass rate (0-1)",
            "# TYPE pipeline_quality_pass_rate gauge",
            f'pipeline_quality_pass_rate{{{labels}}} {stats.get("quality_pass_rate", 0)}',
            "",
            "# HELP pipeline_records_filtered Total records filtered out",
            "# TYPE pipeline_records_filtered counter",
            f'pipeline_records_filtered{{{labels}}} {quality["records_received"] - quality["records_passed_filters"]}',
            ""
        ])

        # Filter breakdown by reason
        for reason, count in quality.get("filter_breakdown", {}).items():
            # Sanitize reason for Prometheus label
            safe_reason = reason.replace('"', '\\"').replace('\n', ' ')
            lines.append(f'pipeline_filter_reason_total{{reason="{safe_reason}",{labels}}} {count}')
        if quality.get("filter_breakdown"):
            lines.append("")

        # ===================================================================
        # VOLUME METRICS (Layer 4 - Common to all pipelines)
        # ===================================================================
        volume = layered["volume"]

        lines.extend([
            "# HELP pipeline_records_written_total Total records written to output",
            "# TYPE pipeline_records_written_total counter",
            f'pipeline_records_written_total{{{labels}}} {volume["records_written"]}',
            "",
            "# HELP pipeline_bytes_downloaded_total Total bytes downloaded",
            "# TYPE pipeline_bytes_downloaded_total counter",
            f'pipeline_bytes_downloaded_total{{{labels}}} {volume["bytes_downloaded"]}',
            "",
            "# HELP pipeline_total_chars_total Total characters processed",
            "# TYPE pipeline_total_chars_total counter",
            f'pipeline_total_chars_total{{{labels}}} {volume["total_chars"]}',
            "",
            "# HELP pipeline_avg_record_size_bytes Average record size in bytes",
            "# TYPE pipeline_avg_record_size_bytes gauge",
            f'pipeline_avg_record_size_bytes{{{labels}}} {volume["bytes_downloaded"] / max(volume["records_written"], 1)}',
            "",
            "# HELP pipeline_avg_record_length_chars Average record length in characters",
            "# TYPE pipeline_avg_record_length_chars gauge",
            f'pipeline_avg_record_length_chars{{{labels}}} {volume["total_chars"] / max(volume["records_written"], 1)}',
            ""
        ])

        # ===================================================================
        # DEDUPLICATION METRICS
        # ===================================================================
        lines.extend([
            "# HELP pipeline_deduplication_rate Deduplication rate (0-1)",
            "# TYPE pipeline_deduplication_rate gauge",
            f'pipeline_deduplication_rate{{{labels}}} {stats.get("deduplication_rate", 0)}',
            "",
            "# HELP pipeline_unique_hashes Total unique document hashes",
            "# TYPE pipeline_unique_hashes counter",
            f'pipeline_unique_hashes{{{labels}}} {snapshot.unique_hashes}',
            "",
            "# HELP pipeline_duplicate_hashes Total duplicate documents",
            "# TYPE pipeline_duplicate_hashes counter",
            f'pipeline_duplicate_hashes{{{labels}}} {snapshot.duplicate_hashes}',
            ""
        ])

        # ===================================================================
        # PERFORMANCE METRICS
        # ===================================================================
        if "fetch_duration_stats" in stats:
            fetch_stats = stats["fetch_duration_stats"]
            lines.extend([
                "# HELP pipeline_fetch_duration_ms_mean Mean fetch duration in milliseconds",
                "# TYPE pipeline_fetch_duration_ms_mean gauge",
                f'pipeline_fetch_duration_ms_mean{{{labels}}} {fetch_stats["mean"]}',
                "",
                "# HELP pipeline_fetch_duration_ms_p95 95th percentile fetch duration",
                "# TYPE pipeline_fetch_duration_ms_p95 gauge",
                f'pipeline_fetch_duration_ms_p95{{{labels}}} {fetch_stats["p95"]}',
                ""
            ])

        if "throughput" in stats:
            throughput = stats["throughput"]
            lines.extend([
                "# HELP pipeline_records_per_minute Record processing throughput",
                "# TYPE pipeline_records_per_minute gauge",
                f'pipeline_records_per_minute{{{labels}}} {throughput["records_per_minute"]}',
                "",
                "# HELP pipeline_bytes_per_second Data download throughput",
                "# TYPE pipeline_bytes_per_second gauge",
                f'pipeline_bytes_per_second{{{labels}}} {throughput["bytes_per_second"]}',
                ""
            ])

        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))


class QualityReporter:
    """
    Generates quality reports from metrics.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize quality reporter.

        Args:
            metrics_collector: MetricsCollector instance with data
        """
        self.collector = metrics_collector
        self.snapshot = metrics_collector.get_snapshot()
        self.stats = self.snapshot.calculate_statistics()

    def generate_markdown_report(self, output_path: Path):
        """Generate markdown quality report."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_lines = []

        # Header
        report_lines.extend([
            f"# Data Quality Report",
            f"",
            f"**Run ID:** {self.snapshot.run_id}",
            f"**Source:** {self.snapshot.source}",
            f"**Timestamp:** {self.snapshot.timestamp}",
            f"**Duration:** {self._format_duration(self.snapshot.duration_seconds)}",
            f"",
            "---",
            ""
        ])

        # Executive Summary
        report_lines.extend(self._generate_summary())

        # Processing Statistics
        report_lines.extend(self._generate_processing_stats())

        # Performance Metrics
        report_lines.extend(self._generate_performance_metrics())

        # Data Quality Metrics
        report_lines.extend(self._generate_quality_metrics())

        # HTTP Status Distribution
        report_lines.extend(self._generate_http_distribution())

        # Filter Statistics
        report_lines.extend(self._generate_filter_stats())

        # Error Analysis
        report_lines.extend(self._generate_error_analysis())

        # Recommendations
        report_lines.extend(self._generate_recommendations())

        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))

    def _generate_summary(self) -> List[str]:
        """Generate executive summary section with pipeline-specific metrics."""
        lines = ["## Executive Summary", ""]

        # Get pipeline-specific primary metric
        if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value:
            primary_metric = self.stats.get("http_request_success_rate", 0)
            primary_metric_name = "HTTP Request Success Rate"
        elif self.snapshot.pipeline_type == PipelineType.FILE_PROCESSING.value:
            primary_metric = self.stats.get("file_extraction_success_rate", 0)
            primary_metric_name = "File Extraction Success Rate"
        elif self.snapshot.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            primary_metric = self.stats.get("stream_connection_success_rate", 0)
            primary_metric_name = "Stream Connection Success"
        else:
            # Fallback to old metric
            primary_metric = self.stats.get("fetch_success_rate", 0)
            primary_metric_name = "Fetch Success Rate"

        primary_metric_pct = primary_metric * 100
        quality_pass_rate = self.stats.get("quality_pass_rate", 0) * 100
        dedup_rate = self.stats.get("deduplication_rate", 0) * 100

        # Status indicator based on primary metric
        if primary_metric_pct >= 90:
            status = "✅ **HEALTHY**"
        elif primary_metric_pct >= 70:
            status = "⚠️ **DEGRADED**"
        else:
            status = "❌ **UNHEALTHY**"

        lines.extend([
            f"**Pipeline Status:** {status}",
            f"**Pipeline Type:** {self.snapshot.pipeline_type}",
            "",
            f"- **{primary_metric_name}:** {primary_metric_pct:.1f}%",
        ])

        # Add secondary pipeline-specific metrics
        if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value:
            content_extraction = self.stats.get("content_extraction_success_rate", 0) * 100
            lines.append(f"- **Content Extraction Success Rate:** {content_extraction:.1f}%")
        elif self.snapshot.pipeline_type == PipelineType.FILE_PROCESSING.value:
            record_parsing = self.stats.get("record_parsing_success_rate", 0) * 100
            lines.append(f"- **Record Parsing Success Rate:** {record_parsing:.1f}%")
        elif self.snapshot.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            record_retrieval = self.stats.get("record_retrieval_success_rate", 0) * 100
            lines.append(f"- **Record Retrieval Success Rate:** {record_retrieval:.1f}%")
            dataset_coverage = self.stats.get("dataset_coverage_rate")
            if dataset_coverage is not None:
                lines.append(f"- **Dataset Coverage:** {dataset_coverage * 100:.3f}%")

        lines.extend([
            f"- **Quality Filter Pass Rate:** {quality_pass_rate:.1f}%",
            f"- **Deduplication Rate:** {dedup_rate:.1f}%",
            f"- **Total Records Processed:** {self.snapshot.records_written:,}",
            f"- **Data Downloaded:** {self._format_bytes(self.snapshot.bytes_downloaded)}",
            "",
            "---",
            ""
        ])

        return lines

    def _generate_processing_stats(self) -> List[str]:
        """Generate processing statistics section based on pipeline type."""
        lines = ["## Processing Statistics", ""]

        if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value:
            # Web scraping statistics
            lines.extend([
                "| Metric | Count | Percentage |",
                "|--------|-------|------------|",
                f"| URLs Discovered | {self.snapshot.urls_discovered:,} | 100.0% |",
                f"| URLs Fetched | {self.snapshot.urls_fetched:,} | {self._percentage(self.snapshot.urls_fetched, self.snapshot.urls_discovered):.1f}% |",
                f"| URLs Processed | {self.snapshot.urls_processed:,} | {self._percentage(self.snapshot.urls_processed, self.snapshot.urls_discovered):.1f}% |",
                f"| URLs Failed | {self.snapshot.urls_failed:,} | {self._percentage(self.snapshot.urls_failed, self.snapshot.urls_discovered):.1f}% |",
                f"| URLs Skipped | {self.snapshot.urls_skipped:,} | {self._percentage(self.snapshot.urls_skipped, self.snapshot.urls_discovered):.1f}% |",
                f"| URLs Deduplicated | {self.snapshot.urls_deduplicated:,} | {self._percentage(self.snapshot.urls_deduplicated, self.snapshot.urls_discovered):.1f}% |",
            ])
        elif self.snapshot.pipeline_type == PipelineType.FILE_PROCESSING.value:
            # File processing statistics
            total_base = self.snapshot.files_discovered if self.snapshot.files_discovered > 0 else 1
            lines.extend([
                "| Metric | Count |",
                "|--------|-------|",
                f"| Files Discovered | {self.snapshot.files_discovered:,} |",
                f"| Files Processed | {self.snapshot.files_processed:,} |",
                f"| Records Extracted | {self.snapshot.records_extracted:,} |",
                f"| Records Written | {self.snapshot.records_written:,} |",
            ])
        elif self.snapshot.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            # Stream processing statistics
            lines.extend([
                "| Metric | Count |",
                "|--------|-------|",
                f"| Datasets Opened | {self.snapshot.datasets_opened:,} |",
                f"| Records Fetched | {self.snapshot.records_fetched:,} |",
                f"| Records Processed | {self.snapshot.records_processed:,} |",
                f"| Batches Completed | {self.snapshot.batches_completed:,} |",
                f"| Records Written | {self.snapshot.records_written:,} |",
            ])
        else:
            # Default/backward compatibility
            lines.extend([
                "| Metric | Count | Percentage |",
                "|--------|-------|------------|",
                f"| URLs Discovered | {self.snapshot.urls_discovered:,} | 100.0% |",
                f"| URLs Fetched | {self.snapshot.urls_fetched:,} | {self._percentage(self.snapshot.urls_fetched, self.snapshot.urls_discovered):.1f}% |",
                f"| URLs Processed | {self.snapshot.urls_processed:,} | {self._percentage(self.snapshot.urls_processed, self.snapshot.urls_discovered):.1f}% |",
            ])

        lines.extend(["", "---", ""])
        return lines

    def _generate_performance_metrics(self) -> List[str]:
        """Generate performance metrics section."""
        lines = ["## Performance Metrics", ""]

        # Fetch performance (more relevant for web scraping and stream processing)
        if "fetch_duration_stats" in self.stats:
            fetch_stats = self.stats["fetch_duration_stats"]
            label = "Fetch Performance" if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value else "Download Performance"
            lines.extend([
                f"### {label}",
                "",
                f"- **Mean:** {fetch_stats['mean']:.0f} ms",
                f"- **Median:** {fetch_stats['median']:.0f} ms",
                f"- **P95:** {fetch_stats['p95']:.0f} ms",
                f"- **P99:** {fetch_stats['p99']:.0f} ms",
                f"- **Min:** {fetch_stats['min']:.0f} ms",
                f"- **Max:** {fetch_stats['max']:.0f} ms",
                ""
            ])

        # Processing performance
        if "process_duration_stats" in self.stats:
            process_stats = self.stats["process_duration_stats"]
            label = "Processing Performance"
            if self.snapshot.pipeline_type == PipelineType.FILE_PROCESSING.value:
                label = "Extraction Performance"
            lines.extend([
                f"### {label}",
                "",
                f"- **Mean:** {process_stats['mean']:.0f} ms",
                f"- **Median:** {process_stats['median']:.0f} ms",
                f"- **P95:** {process_stats['p95']:.0f} ms",
                f"- **P99:** {process_stats['p99']:.0f} ms",
                ""
            ])

        # Throughput
        if "throughput" in self.stats:
            throughput = self.stats["throughput"]
            lines.extend([
                "### Throughput",
                ""
            ])

            # Adaptive throughput metrics based on pipeline type
            if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value:
                lines.append(f"- **URLs/second:** {throughput['urls_per_second']:.2f}")

            lines.extend([
                f"- **Records/minute:** {throughput['records_per_minute']:.1f}",
                f"- **Bytes/second:** {self._format_bytes(throughput['bytes_per_second'])}/s",
                "",
                "---",
                ""
            ])

        return lines

    def _generate_quality_metrics(self) -> List[str]:
        """Generate data quality metrics section."""
        lines = ["## Data Quality Metrics", ""]

        # Deduplication statistics
        lines.extend([
            "### Deduplication",
            "",
            f"- **Unique Documents:** {self.snapshot.unique_hashes:,}",
            f"- **Exact Duplicates:** {self.snapshot.duplicate_hashes:,}",
            f"- **Near Duplicates:** {self.snapshot.near_duplicates:,}",
            ""
        ])

        # Text length statistics
        if "text_length_stats" in self.stats:
            text_stats = self.stats["text_length_stats"]
            lines.extend([
                "### Text Length Distribution",
                "",
                f"- **Mean:** {text_stats['mean']:,.0f} chars",
                f"- **Median:** {text_stats['median']:,.0f} chars",
                f"- **Min:** {text_stats['min']:,} chars",
                f"- **Max:** {text_stats['max']:,} chars",
                f"- **Total:** {self._format_bytes(text_stats['total_chars'])}",
                "",
                "---",
                ""
            ])

        return lines

    def _generate_http_distribution(self) -> List[str]:
        """Generate HTTP status distribution section."""
        if not self.snapshot.http_status_codes:
            return []

        lines = ["## HTTP Status Distribution", ""]

        # Group by status class
        status_classes = defaultdict(int)
        for status, count in self.snapshot.http_status_codes.items():
            status_class = f"{status // 100}xx"
            status_classes[status_class] += count

        lines.extend([
            "| Status Class | Count | Details |",
            "|--------------|-------|---------|"
        ])

        for status_class in sorted(status_classes.keys()):
            count = status_classes[status_class]
            # Get individual status codes
            details = [f"{s}:{c}" for s, c in self.snapshot.http_status_codes.items()
                      if s // 100 == int(status_class[0])]
            details_str = ", ".join(details[:3])  # Show first 3
            if len(details) > 3:
                details_str += f", +{len(details)-3} more"

            lines.append(f"| {status_class} | {count:,} | {details_str} |")

        lines.extend(["", "---", ""])
        return lines

    def _generate_filter_stats(self) -> List[str]:
        """Generate filter statistics section."""
        if not self.snapshot.filter_reasons:
            return []

        lines = ["## Filter Statistics", ""]

        total_filtered = sum(self.snapshot.filter_reasons.values())
        lines.extend([
            f"**Total Filtered:** {total_filtered:,} records",
            "",
            "| Filter Reason | Count | Percentage |",
            "|---------------|-------|------------|"
        ])

        for reason, count in sorted(self.snapshot.filter_reasons.items(),
                                   key=lambda x: x[1], reverse=True):
            percentage = (count / total_filtered * 100) if total_filtered > 0 else 0
            lines.append(f"| {reason} | {count:,} | {percentage:.1f}% |")

        lines.extend(["", "---", ""])
        return lines

    def _generate_error_analysis(self) -> List[str]:
        """Generate error analysis section."""
        if not self.snapshot.error_types:
            return []

        lines = ["## Error Analysis", ""]

        total_errors = sum(self.snapshot.error_types.values())
        lines.extend([
            f"**Total Errors:** {total_errors:,}",
            "",
            "| Error Type | Count | Percentage |",
            "|------------|-------|------------|"
        ])

        for error_type, count in sorted(self.snapshot.error_types.items(),
                                       key=lambda x: x[1], reverse=True):
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            lines.append(f"| {error_type} | {count:,} | {percentage:.1f}% |")

        lines.extend(["", "---", ""])
        return lines

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on pipeline-specific metrics."""
        lines = ["## Recommendations", ""]

        recommendations = []

        # Check pipeline-specific primary metric
        if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value:
            http_success_rate = self.stats.get("http_request_success_rate", 0)
            if http_success_rate < 0.8:
                recommendations.append(
                    "⚠️ **Low HTTP request success rate detected.** Consider reviewing error logs, "
                    "adjusting retry logic, or checking for network/DNS issues."
                )
        elif self.snapshot.pipeline_type == PipelineType.FILE_PROCESSING.value:
            file_extraction_rate = self.stats.get("file_extraction_success_rate", 0)
            if file_extraction_rate < 0.95:
                recommendations.append(
                    "⚠️ **Low file extraction success rate detected.** Check for corrupted files, "
                    "missing dependencies, or file format issues."
                )
        elif self.snapshot.pipeline_type == PipelineType.STREAM_PROCESSING.value:
            stream_connection = self.stats.get("stream_connection_success_rate", 0)
            if stream_connection < 1.0:
                recommendations.append(
                    "❌ **Stream connection failed.** Check API credentials, network connectivity, "
                    "and rate limits."
                )
            dataset_coverage = self.stats.get("dataset_coverage_rate")
            if dataset_coverage is not None and dataset_coverage < 0.01:
                recommendations.append(
                    "⚠️ **Very low dataset coverage.** Stream may have been interrupted. "
                    "Check for timeout settings or API rate limits."
                )

        # Check quality pass rate (common to all pipelines)
        quality_pass_rate = self.stats.get("quality_pass_rate", 0)
        if quality_pass_rate < 0.5:
            recommendations.append(
                "⚠️ **Low quality filter pass rate.** Many records are being filtered out. "
                "Review filter configurations or consider adjusting quality thresholds."
            )

        # Check deduplication rate (common to all pipelines)
        dedup_rate = self.stats.get("deduplication_rate", 0)
        if dedup_rate > 0.3:
            recommendations.append(
                "📊 **High deduplication rate.** Consider implementing more aggressive "
                "discovery filtering or checking data source for redundancy."
            )

        # Check fetch performance (more relevant for web scraping and streaming)
        if "fetch_duration_stats" in self.stats:
            p95 = self.stats["fetch_duration_stats"]["p95"]
            if p95 > 5000:  # 5 seconds
                recommendations.append(
                    "🐢 **Slow fetch times detected.** Consider implementing connection "
                    "pooling, adjusting timeouts, or using concurrent requests."
                )

        # Check error rate (web scraping specific)
        if self.snapshot.pipeline_type == PipelineType.WEB_SCRAPING.value and self.snapshot.urls_failed > 0:
            total_attempted = self.snapshot.urls_fetched + self.snapshot.urls_failed
            if total_attempted > 0:
                error_rate = self.snapshot.urls_failed / total_attempted
                if error_rate > 0.1:
                    recommendations.append(
                        "❌ **High error rate detected.** Review error types and consider "
                        "implementing circuit breakers or exponential backoff."
                    )

        if recommendations:
            lines.extend(recommendations)
        else:
            lines.append("✅ All metrics within acceptable ranges.")

        lines.extend(["", "---", ""])
        return lines

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _format_bytes(self, bytes_count: float) -> str:
        """Format bytes in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

    def _percentage(self, value: float, total: float) -> float:
        """Calculate percentage safely."""
        if total == 0:
            return 0
        return (value / total) * 100


# Example usage
if __name__ == "__main__":
    # Create metrics collector
    collector = MetricsCollector(
        run_id="20250119_103045_bbc",
        source="BBC-Somali"
    )

    # Simulate metrics collection
    collector.increment("urls_discovered", 1000)
    collector.increment("urls_fetched", 950)
    collector.increment("urls_processed", 900)
    collector.increment("urls_failed", 50)
    collector.increment("bytes_downloaded", 50_000_000)

    # Record some timings
    for _ in range(100):
        collector.record_fetch_duration(500 + (time.time() % 1000))
        collector.record_process_duration(100 + (time.time() % 500))

    # Record HTTP status codes
    for _ in range(900):
        collector.record_http_status(200)
    for _ in range(50):
        collector.record_http_status(404)

    # Export metrics
    collector.export_json(Path("metrics_example.json"))

    # Generate quality report
    reporter = QualityReporter(collector)
    reporter.generate_markdown_report(Path("quality_report_example.md"))
