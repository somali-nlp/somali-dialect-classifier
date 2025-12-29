"""
Volume-weighted aggregation functions for Somali NLP metrics system.

PHASE 2 IMPLEMENTATION (2025-10-26):
This module provides safe, volume-weighted aggregation of COMPATIBLE metrics
across data sources. It prevents the mistakes from Phase 0 (simple averaging
of incompatible metrics) while enabling meaningful cross-source analysis.

KEY PRINCIPLES:
- Only aggregate COMPATIBLE metrics (same semantic meaning)
- Weight by data volume (records_written) for representative averages
- Provide breakdown showing each source's contribution
- Support multiple aggregation methods for different use cases
- Validate compatibility before aggregating to prevent errors

COMPATIBLE METRICS:
- quality_pass_rate: Compatible across ALL pipeline types
- deduplication_rate: Compatible across ALL pipeline types
- records_written: Compatible across ALL pipeline types (summable)
- bytes_downloaded: Compatible across ALL pipeline types (summable)

INCOMPATIBLE METRICS (require same pipeline type):
- http_request_success_rate: Only web_scraping
- content_extraction_success_rate: Only web_scraping
- file_extraction_success_rate: Only file_processing
- record_parsing_success_rate: Only file_processing
- stream_connection_success_rate: Only stream_processing
- record_retrieval_success_rate: Only stream_processing

USAGE EXAMPLES:
    # Calculate volume-weighted quality across sources
    >>> from somali_dialect_classifier.utils.aggregation import calculate_volume_weighted_quality
    >>> sources = [
    ...     {"name": "BBC", "records_written": 150, "layered_metrics": {"quality": {"quality_pass_rate": 0.847}}},
    ...     {"name": "Wikipedia", "records_written": 10000, "layered_metrics": {"quality": {"quality_pass_rate": 1.0}}}
    ... ]
    >>> result = calculate_volume_weighted_quality(sources)
    >>> print(f"Overall quality: {result['overall_quality_rate']:.3f}")
    Overall quality: 0.987

    # Validate metric compatibility
    >>> from somali_dialect_classifier.utils.aggregation import validate_metric_compatibility
    >>> is_compat, reason = validate_metric_compatibility(sources, "http_request_success_rate")
    >>> if not is_compat:
    ...     print(f"Cannot aggregate: {reason}")
"""

import json
from enum import Enum
from typing import Any, Optional


class AggregationMethod(Enum):
    """
    Supported aggregation methods.

    - VOLUME_WEIGHTED_MEAN: Weight by data volume (default for quality metrics)
    - HARMONIC_MEAN: Unweighted harmonic mean (penalizes outliers)
    - WEIGHTED_HARMONIC_MEAN: Volume-weighted harmonic mean
    - MIN: Minimum value across sources
    - MAX: Maximum value across sources
    - SUM: Sum across sources (for countable metrics like records_written)
    """

    VOLUME_WEIGHTED_MEAN = "volume_weighted_mean"
    HARMONIC_MEAN = "harmonic_mean"
    WEIGHTED_HARMONIC_MEAN = "weighted_harmonic_mean"
    MIN = "min"
    MAX = "max"
    SUM = "sum"


def calculate_volume_weighted_quality(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate volume-weighted quality metrics across sources.

    Only aggregates semantically compatible metrics (quality_pass_rate).
    Weights by data volume (records_written) to give more influence to
    sources that contributed more data.

    WHY VOLUME-WEIGHTED?
    Simple average would treat all sources equally:
        avg = (bbc_quality + wiki_quality) / 2 = (84.7% + 100%) / 2 = 92.35%

    But if BBC only contributed 150 records and Wikipedia contributed 10,000:
        weighted = (150*0.847 + 10000*1.0) / 10150 = 98.7%

    The weighted average better represents the overall dataset quality.

    Args:
        sources: List of source metrics with structure:
            {
                "name": str,
                "records_written": int,
                "layered_metrics": {
                    "quality": {"quality_pass_rate": float}
                }
            }


    Returns:
        {
            "overall_quality_rate": float,
            "total_records": int,
            "sources_count": int,
            "source_breakdown": List[Dict],
            "method": "volume_weighted_mean"
        }
    """
    if not sources:
        return {
            "overall_quality_rate": 0.0,
            "total_records": 0,
            "sources_count": 0,
            "source_breakdown": [],
            "method": "volume_weighted_mean",
        }

    total_weight = 0
    weighted_sum = 0.0
    breakdown = []

    for source in sources:
        # Extract volume and quality (handle both formats)
        volume, quality, source_name = _extract_metrics(source, "quality_pass_rate")

        if volume > 0:
            total_weight += volume
            weighted_sum += volume * quality

    # Calculate contribution percentages now that we know total
    for source in sources:
        volume, quality, source_name = _extract_metrics(source, "quality_pass_rate")

        if volume > 0:
            contribution = volume / total_weight if total_weight > 0 else 0.0
            breakdown.append(
                {
                    "source": source_name,
                    "volume": volume,
                    "quality_rate": quality,
                    "contribution": contribution,
                }
            )

    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    return {
        "overall_quality_rate": overall,
        "total_records": total_weight,
        "sources_count": len(breakdown),
        "source_breakdown": breakdown,
        "method": "volume_weighted_mean",
    }


def calculate_weighted_harmonic_mean(
    sources: list[dict[str, Any]],
    metric_path: str = "quality_pass_rate",
    weight_path: str = "records_written",
) -> float:
    """
    Calculate weighted harmonic mean.

    Harmonic mean penalizes outliers more heavily than arithmetic mean,
    useful when one poor-performing source should pull down the average.

    Formula: Σw_i / Σ(w_i / x_i)
    where w_i is weight, x_i is value

    WHEN TO USE:
    - Use harmonic mean when you want to penalize low performers
    - Example: If one source has 10% quality and others have 100%,
      harmonic mean will be closer to 10% than arithmetic mean

    Args:
        sources: List of source metrics
        metric_path: Name of metric to aggregate (e.g., "quality_pass_rate")
        weight_path: Name of weight field (e.g., "records_written")

    Returns:
        Weighted harmonic mean
    """
    total_weight = 0
    weighted_reciprocal_sum = 0.0

    for source in sources:
        weight, value, _ = _extract_metrics(source, metric_path, weight_path)

        if weight > 0 and value > 0:
            total_weight += weight
            weighted_reciprocal_sum += weight / value

    if total_weight == 0 or weighted_reciprocal_sum == 0:
        return 0.0

    return total_weight / weighted_reciprocal_sum


def aggregate_compatible_metrics(
    sources: list[dict[str, Any]],
    metric_name: str,
    method: AggregationMethod = AggregationMethod.VOLUME_WEIGHTED_MEAN,
) -> Optional[float]:
    """
    Aggregate a specific metric across sources using specified method.

    IMPORTANT: Only works with compatible metrics! Caller must ensure semantic
    compatibility using validate_metric_compatibility() first.

    Args:
        sources: List of source metrics
        metric_name: Name of metric to aggregate (e.g., "quality_pass_rate")
        method: Aggregation method to use

    Returns:
        Aggregated value or None if not applicable

    Raises:
        ValueError: If method is unknown
    """
    if method == AggregationMethod.VOLUME_WEIGHTED_MEAN:
        if metric_name == "quality_pass_rate":
            return calculate_volume_weighted_quality(sources)["overall_quality_rate"]
        else:
            # Generic volume-weighted mean for other metrics
            total_weight = 0
            weighted_sum = 0.0
            for source in sources:
                weight, value, _ = _extract_metrics(source, metric_name)
                if weight > 0:
                    total_weight += weight
                    weighted_sum += weight * value
            return weighted_sum / total_weight if total_weight > 0 else None

    elif method == AggregationMethod.HARMONIC_MEAN:
        # Simple harmonic mean (unweighted)
        values = []
        for source in sources:
            _, value, _ = _extract_metrics(source, metric_name)
            if value > 0:
                values.append(value)

        if not values:
            return None
        return len(values) / sum(1 / v for v in values)

    elif method == AggregationMethod.WEIGHTED_HARMONIC_MEAN:
        return calculate_weighted_harmonic_mean(sources, metric_name)

    elif method == AggregationMethod.MIN:
        values = []
        for source in sources:
            _, value, _ = _extract_metrics(source, metric_name)
            values.append(value)
        return min(values) if values else None

    elif method == AggregationMethod.MAX:
        values = []
        for source in sources:
            _, value, _ = _extract_metrics(source, metric_name)
            values.append(value)
        return max(values) if values else None

    elif method == AggregationMethod.SUM:
        # Sum values (for countable metrics like records_written, bytes_downloaded)
        total = 0
        for source in sources:
            _, value, _ = _extract_metrics(source, metric_name)
            total += value
        return total

    else:
        raise ValueError(f"Unknown aggregation method: {method}")


def validate_metric_compatibility(
    sources: list[dict[str, Any]], metric_name: str
) -> tuple[bool, Optional[str]]:
    """
    Check if a metric is safe to aggregate across sources.

    Returns:
        (is_compatible, reason_if_not)

    Examples:
        >>> sources = [
        ...     {"snapshot": {"pipeline_type": "web_scraping"}, "statistics": {}},
        ...     {"snapshot": {"pipeline_type": "file_processing"}, "statistics": {}}
        ... ]
        >>> validate_metric_compatibility(sources, "quality_pass_rate")
        (True, None)
        >>> validate_metric_compatibility(sources, "http_request_success_rate")
        (False, "Cannot aggregate http_request_success_rate across different pipeline types: {'web_scraping', 'file_processing'}")
    """
    # Quality metrics are compatible across all pipeline types
    compatible_metrics = {
        "quality_pass_rate",
        "deduplication_rate",
        "records_written",
        "bytes_downloaded",
        "records_filtered",
    }

    if metric_name in compatible_metrics:
        return True, None

    # Extract pipeline types from all sources
    pipeline_types = set()
    for source in sources:
        # Handle both formats
        if "pipeline_type" in source:
            pipeline_type = source["pipeline_type"]
        elif "layered_metrics" in source:
            # Try to infer from layered metrics if possible, or default to unknown
            # Usually pipeline_type is at root in Phase 3
            pipeline_type = source.get("_pipeline_type", "unknown")
        else:
            pipeline_type = "unknown"

        pipeline_types.add(pipeline_type)

    # Check if all sources have same pipeline type
    if len(pipeline_types) == 1:
        # Same pipeline type - extraction metrics are compatible
        return True, None

    # Mixing different pipeline types with pipeline-specific metrics
    return False, (
        f"Cannot aggregate {metric_name} across different pipeline types: {pipeline_types}. "
        f"This metric is pipeline-specific. Only these metrics can be aggregated across "
        f"different pipelines: {compatible_metrics}"
    )


def _extract_metrics(
    source: dict[str, Any], metric_name: str, weight_name: str = "records_written"
) -> tuple[int, float, str]:
    """
    Extract weight, value, and source name from a source dict.

    Handles two formats:
    1. Flat format: {"name": str, "records_written": int, "layered_metrics": {...}}
    2. Processing.json format: {"snapshot": {...}, "statistics": {...}}

    Args:
        source: Source metrics dict
        metric_name: Name of metric to extract
        weight_name: Name of weight field (default: "records_written")

    Returns:
        (weight, value, source_name)
    """
    # Determine format
    if "layered_metrics" in source:
        # Flat format with layered_metrics
        weight = source.get(weight_name, 0)

        # Navigate layered_metrics (e.g., layered_metrics.quality.quality_pass_rate)
        layered = source.get("layered_metrics", {})
        if metric_name == "quality_pass_rate":
            value = layered.get("quality", {}).get(metric_name, 0.0)
        else:
            # For other metrics, try to find in layered structure
            value = 0.0
            for category in layered.values():
                if isinstance(category, dict) and metric_name in category:
                    value = category[metric_name]
                    break
            # If not found in layered_metrics, check top level (for records_written, etc.)
            if value == 0.0:
                value = source.get(metric_name, 0.0)

        source_name = source.get("name", "unknown")

    else:
        # Simple flat format
        weight = source.get(weight_name, 0)
        value = source.get(metric_name, 0.0)
        source_name = source.get("name", source.get("source", "unknown"))

    # Convert percentage (0-100) to rate (0-1) if needed
    if metric_name.endswith("_rate") and value > 1.0:
        value = value / 100.0

    return weight, value, source_name


def calculate_aggregate_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate comprehensive aggregate summary across sources.

    This is a convenience function that aggregates all compatible metrics
    and returns a comprehensive summary.

    Args:
        sources: List of source metrics (from processing.json files)

    Returns:
        {
            "total_records": int,
            "total_bytes": int,
            "sources_count": int,
            "quality_metrics": {...},
            "pipeline_types": List[str],
            "source_contributions": List[Dict]
        }
    """
    if not sources:
        return {
            "total_records": 0,
            "total_bytes": 0,
            "sources_count": 0,
            "quality_metrics": {},
            "pipeline_types": [],
            "source_contributions": [],
        }

    # Aggregate summable metrics
    total_records = (
        aggregate_compatible_metrics(sources, "records_written", AggregationMethod.SUM) or 0
    )

    total_bytes = (
        aggregate_compatible_metrics(sources, "bytes_downloaded", AggregationMethod.SUM) or 0
    )

    # Aggregate quality metrics (volume-weighted)
    quality_result = calculate_volume_weighted_quality(sources)

    # Calculate deduplication rate (volume-weighted)
    dedup_rate = (
        aggregate_compatible_metrics(
            sources, "deduplication_rate", AggregationMethod.VOLUME_WEIGHTED_MEAN
        )
        or 0.0
    )

    # Extract pipeline types
    pipeline_types = []
    for source in sources:
        pt = source.get("pipeline_type", source.get("_pipeline_type", "unknown"))
        if pt not in pipeline_types:
            pipeline_types.append(pt)

    return {
        "total_records": int(total_records),
        "total_bytes": int(total_bytes),
        "sources_count": len(sources),
        "quality_metrics": {
            "overall_quality_rate": quality_result["overall_quality_rate"],
            "deduplication_rate": dedup_rate,
            "source_breakdown": quality_result["source_breakdown"],
        },
        "pipeline_types": pipeline_types,
        "source_contributions": quality_result["source_breakdown"],
    }


# Example usage
if __name__ == "__main__":
    # Example: Load real metrics and aggregate
    import json

    # Simulate loading metrics from processing.json files
    example_sources = [
        {
            "snapshot": {
                "source": "BBC-Somali",
                "pipeline_type": "web_scraping",
                "records_written": 20,
                "bytes_downloaded": 99176,
            },
            "statistics": {"quality_pass_rate": 1.0, "deduplication_rate": 0.0},
        },
        {
            "snapshot": {
                "source": "Wikipedia-Somali",
                "pipeline_type": "file_processing",
                "records_written": 9623,
                "bytes_downloaded": 14280506,
            },
            "statistics": {"quality_pass_rate": 0.7075735294117646, "deduplication_rate": 0.0},
        },
        {
            "snapshot": {
                "source": "HuggingFace-Somali_c4-so",
                "pipeline_type": "stream_processing",
                "records_written": 19,
                "bytes_downloaded": 0,
            },
            "statistics": {"quality_pass_rate": 0.95, "deduplication_rate": 0.0},
        },
    ]

    print("=" * 80)
    print("PHASE 2: Volume-Weighted Aggregation Example")
    print("=" * 80)
    print()

    # Calculate volume-weighted quality
    quality_result = calculate_volume_weighted_quality(example_sources)
    print(
        f"Overall Quality Rate: {quality_result['overall_quality_rate']:.3f} ({quality_result['overall_quality_rate'] * 100:.1f}%)"
    )
    print(f"Total Records: {quality_result['total_records']:,}")
    print(f"Sources: {quality_result['sources_count']}")
    print()
    print("Source Breakdown:")
    for item in quality_result["source_breakdown"]:
        print(
            f"  {item['source']:30s} - {item['volume']:6,} records ({item['contribution'] * 100:5.1f}%) - Quality: {item['quality_rate'] * 100:5.1f}%"
        )
    print()

    # Validate compatibility
    print("Metric Compatibility Check:")
    print("-" * 80)

    test_metrics = [
        "quality_pass_rate",
        "deduplication_rate",
        "http_request_success_rate",
        "file_extraction_success_rate",
    ]

    for metric in test_metrics:
        is_compat, reason = validate_metric_compatibility(example_sources, metric)
        status = "✅ Compatible" if is_compat else "❌ Incompatible"
        print(f"{metric:40s} {status}")
        if reason:
            print(f"  Reason: {reason}")
    print()

    # Calculate comprehensive summary
    summary = calculate_aggregate_summary(example_sources)
    print("Aggregate Summary:")
    print("-" * 80)
    print(json.dumps(summary, indent=2))
