"""
Pydantic schema models for Phase 3 metrics validation.

This module defines the contract for metrics files to ensure data integrity
and facilitate reliable dashboard aggregation. All *_processing.json files
must conform to this schema.

Schema Version: 3.0
"""

from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class ConnectivityMetrics(BaseModel):
    """Phase 3 connectivity layer metrics."""

    connection_attempted: bool
    connection_successful: bool
    connection_duration_ms: float = Field(ge=0)
    connection_error: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ExtractionMetrics(BaseModel):
    """Phase 3 extraction layer metrics."""

    http_requests_attempted: int = Field(ge=0)
    http_requests_successful: int = Field(ge=0)
    http_status_distribution: Dict[str, int] = Field(default_factory=dict)
    pages_parsed: int = Field(ge=0)
    content_extracted: int = Field(ge=0)

    model_config = ConfigDict(extra="allow")

    @field_validator("http_requests_successful")
    @classmethod
    def validate_success_count(cls, v, info):
        if "http_requests_attempted" in info.data and v > info.data["http_requests_attempted"]:
            raise ValueError("http_requests_successful cannot exceed http_requests_attempted")
        return v


class QualityMetrics(BaseModel):
    """Phase 3 quality layer metrics."""

    records_received: int = Field(ge=0)
    records_passed_filters: int = Field(ge=0)
    filter_breakdown: Dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("records_passed_filters")
    @classmethod
    def validate_passed_count(cls, v, info):
        if "records_received" in info.data and v > info.data["records_received"]:
            raise ValueError("records_passed_filters cannot exceed records_received")
        return v


class VolumeMetrics(BaseModel):
    """Phase 3 volume layer metrics."""

    records_written: int = Field(ge=0)
    bytes_downloaded: int = Field(ge=0)
    total_chars: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class LayeredMetrics(BaseModel):
    """Phase 3 layered metrics structure."""

    connectivity: ConnectivityMetrics
    extraction: ExtractionMetrics
    quality: QualityMetrics
    volume: VolumeMetrics

    model_config = ConfigDict(extra="forbid")


class FetchDurationStats(BaseModel):
    """Statistical metrics for fetch durations."""

    min: float = Field(ge=0)
    max: float = Field(ge=0)
    mean: float = Field(ge=0)
    median: float = Field(ge=0)
    p95: float = Field(ge=0)
    p99: float = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class TextLengthStats(BaseModel):
    """Statistical metrics for text lengths."""

    min: int = Field(ge=0)
    max: int = Field(ge=0)
    mean: float = Field(ge=0)
    median: float = Field(ge=0)
    total_chars: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ThroughputMetrics(BaseModel):
    """Throughput performance metrics."""

    urls_per_second: float = Field(ge=0)
    bytes_per_second: float = Field(ge=0)
    records_per_minute: float = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class Statistics(BaseModel):
    """Phase 3 statistics section."""

    # Pipeline-specific success rates (at least one must be present)
    http_request_success_rate: Optional[float] = Field(default=None, ge=0, le=1)
    content_extraction_success_rate: Optional[float] = Field(default=None, ge=0, le=1)
    http_request_failure_rate: Optional[float] = Field(default=None, ge=0, le=1)

    # Alternative success rates for different pipeline types
    file_extraction_success_rate: Optional[float] = Field(default=None, ge=0, le=1)
    stream_connection_success_rate: Optional[float] = Field(default=None, ge=0, le=1)

    # Common quality metrics
    quality_pass_rate: float = Field(ge=0, le=1)
    deduplication_rate: float = Field(ge=0, le=1)
    fetch_duration_stats: Optional[FetchDurationStats] = None
    text_length_stats: Optional[TextLengthStats] = None
    throughput: ThroughputMetrics

    # Legacy field for backward compatibility (deprecated)
    fetch_success_rate: Optional[float] = Field(default=None, ge=0, le=1)
    fetch_failure_rate: Optional[float] = Field(default=None, ge=0, le=1)

    # Metadata fields (optional, informational) - use aliases for underscore-prefixed
    metric_semantics: Optional[Dict[str, str]] = Field(default=None, alias="_metric_semantics")
    deprecation_warnings: Optional[List[str]] = Field(default=None, alias="_deprecation_warnings")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Snapshot(BaseModel):
    """Legacy snapshot section for backward compatibility."""

    timestamp: str
    run_id: str
    source: str
    duration_seconds: float = Field(ge=0)
    pipeline_type: str

    # URL-based metrics
    urls_discovered: int = Field(ge=0)
    urls_fetched: int = Field(ge=0)
    urls_processed: int = Field(ge=0)
    urls_failed: int = Field(ge=0, default=0)
    urls_skipped: int = Field(ge=0, default=0)
    urls_deduplicated: int = Field(ge=0, default=0)

    # File-based metrics (for dataset sources)
    files_discovered: int = Field(ge=0, default=0)
    files_processed: int = Field(ge=0, default=0)
    records_extracted: int = Field(ge=0, default=0)
    datasets_opened: int = Field(ge=0, default=0)
    records_fetched: int = Field(ge=0, default=0)
    records_processed: int = Field(ge=0, default=0)
    batches_completed: int = Field(ge=0, default=0)

    # Volume metrics
    bytes_downloaded: int = Field(ge=0)
    records_written: int = Field(ge=0)
    records_filtered: int = Field(ge=0, default=0)

    # Status codes and errors
    http_status_codes: Dict[str, int] = Field(default_factory=dict)
    filter_reasons: Dict[str, int] = Field(default_factory=dict)
    error_types: Dict[str, int] = Field(default_factory=dict)

    # Raw timing data
    fetch_durations_ms: List[float] = Field(default_factory=list)
    process_durations_ms: List[float] = Field(default_factory=list)
    text_lengths: List[int] = Field(default_factory=list)

    # Deduplication
    unique_hashes: int = Field(ge=0, default=0)
    duplicate_hashes: int = Field(ge=0, default=0)
    near_duplicates: int = Field(ge=0, default=0)

    model_config = ConfigDict(extra="allow")


class LegacyMetrics(BaseModel):
    """Legacy metrics wrapper for backward compatibility."""

    snapshot: Snapshot
    statistics: Statistics

    model_config = ConfigDict(extra="forbid")


class Phase3MetricsSchema(BaseModel):
    """
    Complete Phase 3 metrics schema for *_processing.json files.

    This is the root schema that all metrics files must conform to.
    """

    schema_version: str = Field(alias="_schema_version", pattern=r"^3\.\d+$")
    pipeline_type: str = Field(alias="_pipeline_type")
    timestamp: str = Field(alias="_timestamp")
    run_id: str = Field(alias="_run_id")
    source: str = Field(alias="_source")

    layered_metrics: LayeredMetrics
    legacy_metrics: LegacyMetrics

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        """Ensure timestamp is valid ISO format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")
        return v


class ConsolidatedMetric(BaseModel):
    """
    Consolidated metric entry for dashboard consumption.

    This is the schema for entries in all_metrics.json after consolidation.
    """

    run_id: str
    source: str
    timestamp: str
    duration_seconds: float = Field(ge=0)

    # Discovery metrics
    urls_discovered: int = Field(ge=0)
    urls_fetched: int = Field(ge=0)
    urls_processed: int = Field(ge=0)

    # Volume metrics
    records_written: int = Field(ge=0)
    bytes_downloaded: int = Field(ge=0)
    total_chars: int = Field(ge=0)

    # Quality metrics
    http_request_success_rate: float = Field(ge=0, le=1)
    content_extraction_success_rate: float = Field(ge=0, le=1)
    quality_pass_rate: float = Field(ge=0, le=1)
    deduplication_rate: float = Field(ge=0, le=1)

    # Throughput metrics
    urls_per_second: float = Field(ge=0)
    bytes_per_second: float = Field(ge=0)
    records_per_minute: float = Field(ge=0)

    # Statistical metrics (optional)
    text_length_stats: Optional[Dict[str, Any]] = None
    fetch_duration_stats: Optional[Dict[str, Any]] = None
    filter_breakdown: Optional[Dict[str, int]] = None

    model_config = ConfigDict(extra="allow")


class ConsolidatedMetricsOutput(BaseModel):
    """Schema for the consolidated all_metrics.json file."""

    count: int = Field(ge=0)
    records: int = Field(ge=0)
    sources: List[str]
    metrics: List[ConsolidatedMetric]

    model_config = ConfigDict(extra="forbid")


class DashboardSummary(BaseModel):
    """Schema for the dashboard summary.json file."""

    total_records: int = Field(ge=0)
    total_urls_processed: int = Field(ge=0)
    avg_success_rate: float = Field(ge=0, le=1)
    total_data_downloaded_bytes: int = Field(ge=0)
    sources: List[str]
    last_update: str
    total_runs: int = Field(ge=0)
    source_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class AdvancedVisualizationData(BaseModel):
    """Schema for advanced visualization data (Sankey, Ridge, Time-series)."""

    # Sankey flow data
    sankey_available: bool = False
    sankey_last_updated: Optional[str] = None

    # Ridge plot data
    ridge_available: bool = False
    ridge_last_updated: Optional[str] = None

    # Time-series data
    timeseries_available: bool = False
    timeseries_last_updated: Optional[str] = None

    # Comparison data
    comparison_available: bool = False
    comparison_last_updated: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class EnhancedDashboardMetadata(BaseModel):
    """Enhanced metadata for dashboard with visualization flags."""

    generated_at: str
    schema_version: str = "4.0"
    metrics_count: int = Field(ge=0)
    sources_count: int = Field(ge=0)
    visualizations: AdvancedVisualizationData

    # Cache information
    cache_key: Optional[str] = None
    cache_ttl_seconds: Optional[int] = 3600  # 1 hour default

    model_config = ConfigDict(extra="allow")


def validate_processing_json(data: Dict[str, Any]) -> Phase3MetricsSchema:
    """
    Validate a *_processing.json file against Phase 3 schema.

    Args:
        data: Loaded JSON data from processing file

    Returns:
        Validated Phase3MetricsSchema instance

    Raises:
        ValidationError: If data doesn't conform to schema

    Example:
        >>> with open("data/metrics/..._processing.json") as f:
        ...     data = json.load(f)
        >>> validated = validate_processing_json(data)
        >>> print(validated.layered_metrics.volume.records_written)
    """
    return Phase3MetricsSchema.model_validate(data)


def validate_consolidated_metrics(data: Dict[str, Any]) -> ConsolidatedMetricsOutput:
    """
    Validate consolidated all_metrics.json against schema.

    Args:
        data: Loaded JSON data from all_metrics.json

    Returns:
        Validated ConsolidatedMetricsOutput instance

    Raises:
        ValidationError: If data doesn't conform to schema
    """
    return ConsolidatedMetricsOutput.model_validate(data)


def validate_dashboard_summary(data: Dict[str, Any]) -> DashboardSummary:
    """
    Validate summary.json against schema.

    Args:
        data: Loaded JSON data from summary.json

    Returns:
        Validated DashboardSummary instance

    Raises:
        ValidationError: If data doesn't conform to schema
    """
    return DashboardSummary.model_validate(data)
