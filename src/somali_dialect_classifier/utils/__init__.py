"""
Utility modules for Somali Dialect Classifier.
"""

from .aggregation import (
    AggregationMethod,
    aggregate_compatible_metrics,
    calculate_aggregate_summary,
    calculate_volume_weighted_quality,
    calculate_weighted_harmonic_mean,
    validate_metric_compatibility,
)
from .logging_utils import (
    LogEvent,
    StructuredLogger,
    Timer,
    clear_context,
    generate_run_id,
    get_context,
    log_context,
    log_event,
    set_context,
    setup_logging,
)
from .metrics import (
    # Phase 2/3: Layered metrics
    ConnectivityMetrics,
    ExtractionMetrics,
    FileProcessingExtractionMetrics,
    MetricsCollector,
    MetricSnapshot,
    PipelineType,
    QualityMetrics,
    QualityReporter,
    StreamProcessingExtractionMetrics,
    VolumeMetrics,
    WebScrapingExtractionMetrics,
    create_extraction_metrics,
    validate_layered_metrics,
)

__all__ = [
    # Logging
    "StructuredLogger",
    "set_context",
    "get_context",
    "clear_context",
    "log_context",
    "generate_run_id",
    "LogEvent",
    "log_event",
    "Timer",
    "setup_logging",
    # Metrics (Phase 1)
    "MetricsCollector",
    "QualityReporter",
    "MetricSnapshot",
    "PipelineType",
    # Metrics (Phase 2/3: Layered architecture)
    "ConnectivityMetrics",
    "ExtractionMetrics",
    "WebScrapingExtractionMetrics",
    "FileProcessingExtractionMetrics",
    "StreamProcessingExtractionMetrics",
    "QualityMetrics",
    "VolumeMetrics",
    "create_extraction_metrics",
    "validate_layered_metrics",
    # Aggregation
    "calculate_volume_weighted_quality",
    "calculate_weighted_harmonic_mean",
    "aggregate_compatible_metrics",
    "validate_metric_compatibility",
    "calculate_aggregate_summary",
    "AggregationMethod",
]
