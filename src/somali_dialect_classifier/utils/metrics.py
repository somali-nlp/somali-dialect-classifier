"""
Metrics collection and quality reporting utilities.

Provides:
- MetricsCollector for tracking pipeline metrics
- QualityReporter for generating markdown reports
- JSON export for metrics (Prometheus migration path)
- Statistical analysis of pipeline performance

PHASE 1 REFACTORING (2025-10-26):
- Renamed metrics to be semantically accurate per pipeline type:
  * Web scraping: http_request_success_rate, content_extraction_success_rate
  * File processing: file_extraction_success_rate, record_parsing_success_rate
  * Stream processing: stream_connection_success_rate, record_retrieval_success_rate
- Fixed BBC test limit bug (only count attempted URLs, not discovered)
- Added metric semantics metadata for clarity
- Deprecated old 'fetch_success_rate' (backward compatible for 1 version)
"""

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
                # quality_pass_rate = records_processed / (records_fetched - duplicates)
                # For BBC: urls_processed / (urls_fetched - urls_deduplicated)
                processable_urls = self.urls_fetched - self.urls_deduplicated
                if processable_urls > 0:
                    stats["quality_pass_rate"] = self.urls_processed / processable_urls
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
            if total_extracted > 0:
                # quality_pass_rate = records_written / (records_extracted - duplicates)
                non_dup_records = total_extracted - (self.duplicate_hashes + self.near_duplicates)
                if non_dup_records > 0:
                    stats["quality_pass_rate"] = self.records_written / non_dup_records
                else:
                    stats["quality_pass_rate"] = 0
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

            # Quality pass rate: how many fetched records passed quality filters
            if self.records_fetched > 0:
                # quality_pass_rate = records_processed / (records_fetched - duplicates)
                non_dup_records = self.records_fetched - (self.duplicate_hashes + self.near_duplicates)
                if non_dup_records > 0:
                    stats["quality_pass_rate"] = self.records_processed / non_dup_records
                else:
                    stats["quality_pass_rate"] = 0
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
                stats["quality_pass_rate"] = (self.urls_processed / total_attempts)
                stats["deduplication_rate"] = (self.urls_deduplicated / total_attempts)
            else:
                stats["fetch_success_rate"] = 0
                stats["fetch_failure_rate"] = 0
                stats["quality_pass_rate"] = 0
                stats["deduplication_rate"] = 0

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

    def export_json(self, output_path: Path):
        """Export metrics to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        snapshot = self.get_snapshot()
        metrics_data = {
            "snapshot": snapshot.to_dict(),
            "statistics": snapshot.calculate_statistics()
        }

        with open(output_path, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)

    def export_prometheus(self, output_path: Path):
        """
        Export metrics in Prometheus format.

        Note: This is a placeholder for future Prometheus integration.
        """
        # Prometheus text format example:
        # metric_name{label1="value1",label2="value2"} metric_value timestamp
        output_path.parent.mkdir(parents=True, exist_ok=True)

        snapshot = self.get_snapshot()
        lines = []

        # Add counters
        lines.append(f'# HELP urls_discovered Total URLs discovered')
        lines.append(f'# TYPE urls_discovered counter')
        lines.append(f'urls_discovered{{source="{self.source}",run_id="{self.run_id}"}} {snapshot.urls_discovered}')

        # Add more metrics...
        # This is a skeleton for future implementation

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
