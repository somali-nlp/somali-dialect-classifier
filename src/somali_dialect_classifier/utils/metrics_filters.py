"""
Backend filtering functions for metrics data.

Provides server-side filtering capabilities for dashboard data:
- Filter by source
- Filter by quality threshold
- Filter by date range
- Filter by status
- Combined filters

All functions work with consolidated metrics format and maintain
backward compatibility with existing schema.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


# ============================================================================
# FILTER FUNCTIONS
# ============================================================================

def filter_by_source(
    metrics: List[Dict[str, Any]],
    sources: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter metrics by data source.

    Args:
        metrics: List of consolidated metrics
        sources: List of source names to include (case-insensitive)

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = filter_by_source(metrics, ["BBC-Somali", "Wikipedia-Somali"])
    """
    if not sources:
        return metrics

    sources_lower = [s.lower() for s in sources]

    return [
        m for m in metrics
        if m.get("source", "").lower() in sources_lower
    ]


def filter_by_quality(
    metrics: List[Dict[str, Any]],
    threshold: float = 0.8,
    metric_name: str = "quality_pass_rate"
) -> List[Dict[str, Any]]:
    """
    Filter metrics by quality threshold.

    Args:
        metrics: List of consolidated metrics
        threshold: Minimum quality threshold (0-1)
        metric_name: Name of quality metric to filter on

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = filter_by_quality(metrics, threshold=0.85)
    """
    if not 0 <= threshold <= 1:
        logger.warning(f"Invalid threshold: {threshold}. Must be between 0 and 1.")
        return metrics

    return [
        m for m in metrics
        if m.get(metric_name, 0) >= threshold
    ]


def filter_by_date_range(
    metrics: List[Dict[str, Any]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter metrics by date range.

    Args:
        metrics: List of consolidated metrics
        start_date: Start date (ISO format: YYYY-MM-DD or ISO 8601)
        end_date: End date (ISO format: YYYY-MM-DD or ISO 8601)

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = filter_by_date_range(
        ...     metrics,
        ...     start_date="2025-10-01",
        ...     end_date="2025-10-31"
        ... )
    """
    if not start_date and not end_date:
        return metrics

    filtered = []

    try:
        # Parse dates and ensure timezone awareness
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                from datetime import timezone as tz
                start_dt = start_dt.replace(tzinfo=tz.utc)
        else:
            start_dt = None

        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                from datetime import timezone as tz
                end_dt = end_dt.replace(tzinfo=tz.utc)
        else:
            end_dt = None

        for m in metrics:
            timestamp_str = m.get("timestamp", "")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Ensure timestamp is timezone-aware
                if timestamp.tzinfo is None:
                    from datetime import timezone as tz
                    timestamp = timestamp.replace(tzinfo=tz.utc)

                if start_dt and timestamp < start_dt:
                    continue
                if end_dt and timestamp > end_dt:
                    continue

                filtered.append(m)

            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse timestamp: {timestamp_str}: {e}")
                continue

    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid date format: {e}")
        return metrics

    return filtered


def filter_by_status(
    metrics: List[Dict[str, Any]],
    status: str = "healthy"
) -> List[Dict[str, Any]]:
    """
    Filter metrics by pipeline status.

    Status classification:
    - healthy: success_rate >= 0.9
    - degraded: 0.7 <= success_rate < 0.9
    - unhealthy: success_rate < 0.7

    Args:
        metrics: List of consolidated metrics
        status: Status to filter ('healthy', 'degraded', 'unhealthy')

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = filter_by_status(metrics, status="healthy")
    """
    status_thresholds = {
        "healthy": (0.9, 1.0),
        "degraded": (0.7, 0.9),
        "unhealthy": (0.0, 0.7)
    }

    if status not in status_thresholds:
        logger.warning(f"Unknown status: {status}. Use 'healthy', 'degraded', or 'unhealthy'.")
        return metrics

    min_threshold, max_threshold = status_thresholds[status]

    filtered = []

    for m in metrics:
        # Get primary success rate based on pipeline type
        pipeline_type = m.get("pipeline_type", "web_scraping")

        if pipeline_type == "web_scraping":
            success_rate = m.get("http_request_success_rate", 0)
        elif pipeline_type == "file_processing":
            success_rate = m.get("file_extraction_success_rate", 0)
        elif pipeline_type == "stream_processing":
            success_rate = m.get("stream_connection_success_rate", 0)
        else:
            # Fallback to generic success rate
            success_rate = m.get("http_request_success_rate", 0)

        if min_threshold <= success_rate < max_threshold:
            filtered.append(m)

    return filtered


def filter_by_records_threshold(
    metrics: List[Dict[str, Any]],
    min_records: int = 0,
    max_records: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Filter metrics by record count range.

    Args:
        metrics: List of consolidated metrics
        min_records: Minimum number of records written
        max_records: Maximum number of records written (None = no limit)

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = filter_by_records_threshold(metrics, min_records=1000)
    """
    filtered = []

    for m in metrics:
        records = m.get("records_written", 0)

        if records < min_records:
            continue
        if max_records is not None and records > max_records:
            continue

        filtered.append(m)

    return filtered


def filter_by_pipeline_type(
    metrics: List[Dict[str, Any]],
    pipeline_types: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter metrics by pipeline type.

    Args:
        metrics: List of consolidated metrics
        pipeline_types: List of pipeline types ('web_scraping', 'file_processing', 'stream_processing')

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = filter_by_pipeline_type(metrics, ["web_scraping", "file_processing"])
    """
    if not pipeline_types:
        return metrics

    pipeline_types_lower = [pt.lower() for pt in pipeline_types]

    return [
        m for m in metrics
        if m.get("pipeline_type", "").lower() in pipeline_types_lower
    ]


# ============================================================================
# COMBINED FILTER
# ============================================================================

def apply_filters(
    metrics: List[Dict[str, Any]],
    sources: Optional[List[str]] = None,
    quality_threshold: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    min_records: Optional[int] = None,
    max_records: Optional[int] = None,
    pipeline_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Apply multiple filters to metrics data.

    All filters are applied in sequence (AND logic).

    Args:
        metrics: List of consolidated metrics
        sources: Filter by sources (OR logic within sources)
        quality_threshold: Minimum quality pass rate
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        status: Filter by status ('healthy', 'degraded', 'unhealthy')
        min_records: Minimum record count
        max_records: Maximum record count
        pipeline_types: Filter by pipeline types

    Returns:
        Filtered list of metrics

    Example:
        >>> filtered = apply_filters(
        ...     metrics,
        ...     sources=["BBC-Somali"],
        ...     quality_threshold=0.8,
        ...     start_date="2025-10-01",
        ...     status="healthy"
        ... )
    """
    result = metrics

    # Apply each filter if specified
    if sources:
        result = filter_by_source(result, sources)
        logger.info(f"After source filter: {len(result)} metrics")

    if quality_threshold is not None:
        result = filter_by_quality(result, quality_threshold)
        logger.info(f"After quality filter: {len(result)} metrics")

    if start_date or end_date:
        result = filter_by_date_range(result, start_date, end_date)
        logger.info(f"After date range filter: {len(result)} metrics")

    if status:
        result = filter_by_status(result, status)
        logger.info(f"After status filter: {len(result)} metrics")

    if min_records is not None or max_records is not None:
        result = filter_by_records_threshold(result, min_records or 0, max_records)
        logger.info(f"After records threshold filter: {len(result)} metrics")

    if pipeline_types:
        result = filter_by_pipeline_type(result, pipeline_types)
        logger.info(f"After pipeline type filter: {len(result)} metrics")

    return result


# ============================================================================
# EXPORT FILTERED DATA
# ============================================================================

def export_filtered_metrics(
    metrics: List[Dict[str, Any]],
    output_file: str,
    **filter_kwargs
) -> Dict[str, Any]:
    """
    Apply filters and export to JSON file.

    Args:
        metrics: List of consolidated metrics
        output_file: Path to output JSON file
        **filter_kwargs: Filter parameters (see apply_filters)

    Returns:
        Dictionary with filtered metrics and metadata

    Example:
        >>> export_filtered_metrics(
        ...     metrics,
        ...     "filtered_metrics.json",
        ...     sources=["BBC-Somali"],
        ...     quality_threshold=0.8
        ... )
    """
    import json
    from pathlib import Path

    filtered = apply_filters(metrics, **filter_kwargs)

    output = {
        "count": len(filtered),
        "filters_applied": {k: v for k, v in filter_kwargs.items() if v is not None},
        "metrics": filtered
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    logger.info(f"✓ Exported {len(filtered)} filtered metrics to: {output_path}")

    return output


# ============================================================================
# SEARCH AND QUERY FUNCTIONS
# ============================================================================

def search_metrics(
    metrics: List[Dict[str, Any]],
    query: str,
    fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search metrics by text query.

    Searches in specified fields for case-insensitive matches.

    Args:
        metrics: List of consolidated metrics
        query: Search query string
        fields: List of fields to search (default: ['source', 'run_id'])

    Returns:
        Filtered list of metrics matching query

    Example:
        >>> results = search_metrics(metrics, query="bbc", fields=["source"])
    """
    if not query:
        return metrics

    if fields is None:
        fields = ['source', 'run_id']

    query_lower = query.lower()
    results = []

    for m in metrics:
        for field in fields:
            value = str(m.get(field, "")).lower()
            if query_lower in value:
                results.append(m)
                break  # Found match, move to next metric

    return results


def get_top_performers(
    metrics: List[Dict[str, Any]],
    metric_name: str = "quality_pass_rate",
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top N performing metrics by specified metric.

    Args:
        metrics: List of consolidated metrics
        metric_name: Metric to sort by
        top_n: Number of top results to return

    Returns:
        Top N metrics sorted by metric_name (descending)

    Example:
        >>> top = get_top_performers(metrics, metric_name="quality_pass_rate", top_n=5)
    """
    sorted_metrics = sorted(
        metrics,
        key=lambda m: m.get(metric_name, 0),
        reverse=True
    )

    return sorted_metrics[:top_n]


def get_recent_metrics(
    metrics: List[Dict[str, Any]],
    num_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get metrics from recent N days.

    Args:
        metrics: List of consolidated metrics
        num_days: Number of days to look back

    Returns:
        Metrics from last N days

    Example:
        >>> recent = get_recent_metrics(metrics, num_days=7)
    """
    cutoff_date = datetime.now() - timedelta(days=num_days)

    recent = []

    for m in metrics:
        timestamp_str = m.get("timestamp", "")
        if not timestamp_str:
            continue

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if timestamp >= cutoff_date:
                recent.append(m)
        except (ValueError, AttributeError):
            continue

    return recent
