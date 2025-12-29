"""
Centralized metrics aggregation utilities.

This module provides single source of truth for extracting and transforming
metrics from processing JSON files. Eliminates code duplication across
scripts and reduces maintenance risk.

Supports Phase 3 (layered) structure with schema validation.

Usage:
    >>> from somali_dialect_classifier.utils.metrics_aggregation import (
    ...     extract_consolidated_metric,
    ...     load_metrics_from_file
    ... )
    >>> data = load_metrics_from_file(Path("data/metrics/wikipedia_20251115_processing.json"))
    >>> metric = extract_consolidated_metric(data, "wikipedia_20251115_processing.json")
"""

import json
import logging
import statistics
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import schema validation
try:
    from somali_dialect_classifier.utils.metrics_schema import (
        ConsolidatedMetric,
        validate_processing_json,
    )

    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False
    logger.warning("Schema validation not available. Install with: pip install -e '.[config]'")


def extract_consolidated_metric(data: dict[str, Any], source_file: str) -> Optional[dict[str, Any]]:
    """
    Extract consolidated metric from Phase 3 *_processing.json.

    This function transforms Phase 3 processing JSON into a consolidated
    metric dictionary suitable for dashboard consumption. It properly
    surfaces layered_metrics and computes derived statistics.

    Args:
        data: Loaded JSON from *_processing.json
        source_file: Filename for error reporting

    Returns:
        Consolidated metric dict, or None if extraction fails

    Example:
        >>> data = load_metrics_from_file(Path("wikipedia_20251115_processing.json"))
        >>> metric = extract_consolidated_metric(data, "wikipedia_20251115_processing.json")
        >>> print(metric['records_written'])  # 9960
    """
    try:
        # Try schema validation if available
        use_validation = False
        validated = None

        if SCHEMA_VALIDATION_AVAILABLE:
            try:
                validated = validate_processing_json(data)
                use_validation = True
            except Exception as validation_error:
                logger.debug(
                    f"Schema validation failed for {source_file}, using fallback: {validation_error}"
                )
                use_validation = False

        if use_validation and validated:
            # Guard against null sources (stale data)
            source = validated.source
            run_id = validated.run_id

            # Access Pydantic model attributes directly
            layered = validated.layered_metrics
            legacy = validated.legacy_metrics
            snapshot = legacy.snapshot
            stats = legacy.statistics

            quality = layered.quality
            volume = layered.volume
        else:
            # Fallback to dict access
            layered = data.get("layered_metrics", {})
            legacy = data.get("legacy_metrics", {})
            snapshot = legacy.get("snapshot", {})
            stats = legacy.get("statistics", {})

            # Guard against null sources (stale data)
            source = data.get("_source") or snapshot.get("source")
            if not source:
                logger.warning(f"No source found in {source_file}, skipping")
                return None

            run_id = data.get("_run_id") or snapshot.get("run_id")
            if not run_id:
                logger.warning(f"No run_id found in {source_file}, skipping")
                return None

            quality = layered.get("quality", {})
            volume = layered.get("volume", {})

        # Build consolidated metric (handle both Pydantic and dict access)
        if use_validation and validated:
            metric = {
                "run_id": run_id,
                "source": source,
                "timestamp": validated.timestamp,
                "duration_seconds": snapshot.duration_seconds,
                "pipeline_type": snapshot.pipeline_type,
                # Discovery metrics (from legacy for backward compatibility)
                "urls_discovered": snapshot.urls_discovered,
                "urls_fetched": snapshot.urls_fetched,
                "urls_processed": snapshot.urls_processed,
                "records_extracted": snapshot.records_extracted,
                # Volume metrics (from layered_metrics.volume)
                "records_written": volume.records_written,
                "bytes_downloaded": volume.bytes_downloaded,
                "total_chars": volume.total_chars,
                # Quality metrics (from statistics)
                "http_request_success_rate": stats.http_request_success_rate,
                "content_extraction_success_rate": stats.content_extraction_success_rate,
                "quality_pass_rate": stats.quality_pass_rate,
                "deduplication_rate": stats.deduplication_rate,
                # Throughput metrics (from statistics.throughput)
                "urls_per_second": stats.throughput.urls_per_second,
                "bytes_per_second": stats.throughput.bytes_per_second,
                "records_per_minute": stats.throughput.records_per_minute,
            }

            # Optional: Include detailed stats
            if stats.text_length_stats:
                metric["text_length_stats"] = stats.text_length_stats.model_dump()

            if stats.fetch_duration_stats:
                metric["fetch_duration_stats"] = stats.fetch_duration_stats.model_dump()

            # Include filter breakdown from quality layer
            if quality.filter_breakdown:
                metric["filter_breakdown"] = quality.filter_breakdown
        else:
            metric = {
                "run_id": run_id,
                "source": source,
                "timestamp": data.get("_timestamp") or snapshot.get("timestamp", ""),
                "duration_seconds": snapshot.get("duration_seconds", 0),
                "pipeline_type": data.get("_pipeline_type")
                or snapshot.get("pipeline_type", "unknown"),
                # Discovery metrics (from legacy for backward compatibility)
                "urls_discovered": snapshot.get("urls_discovered", 0),
                "urls_fetched": snapshot.get("urls_fetched", 0),
                "urls_processed": snapshot.get("urls_processed", 0),
                "records_extracted": snapshot.get("records_extracted", 0),
                # Volume metrics (from layered_metrics.volume)
                "records_written": volume.get("records_written", 0),
                "bytes_downloaded": volume.get("bytes_downloaded", 0),
                "total_chars": volume.get("total_chars", 0),
                # Quality metrics (from statistics)
                "http_request_success_rate": stats.get("http_request_success_rate", 0),
                "content_extraction_success_rate": stats.get("content_extraction_success_rate", 0),
                "quality_pass_rate": stats.get("quality_pass_rate", 0),
                "deduplication_rate": stats.get("deduplication_rate", 0),
                # Throughput metrics (from statistics.throughput)
                "urls_per_second": stats.get("throughput", {}).get("urls_per_second", 0),
                "bytes_per_second": stats.get("throughput", {}).get("bytes_per_second", 0),
                "records_per_minute": stats.get("throughput", {}).get("records_per_minute", 0),
            }

            # Optional: Include detailed stats
            if "text_length_stats" in stats and stats["text_length_stats"]:
                metric["text_length_stats"] = stats["text_length_stats"]

            if "fetch_duration_stats" in stats and stats["fetch_duration_stats"]:
                metric["fetch_duration_stats"] = stats["fetch_duration_stats"]

            # Include filter breakdown from quality layer
            filter_breakdown = quality.get("filter_breakdown", {})
            if filter_breakdown:
                metric["filter_breakdown"] = filter_breakdown

        # Validate consolidated metric if validation was used
        if use_validation and SCHEMA_VALIDATION_AVAILABLE:
            try:
                ConsolidatedMetric.model_validate(metric)
            except Exception as e:
                logger.debug(f"Consolidated metric validation failed for {source_file}: {e}")
                # Continue anyway, metric is still usable

        return metric

    except KeyError as e:
        logger.error(f"Missing required field in {source_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing {source_file}: {e}")
        return None


def load_metrics_from_file(file_path: Path) -> dict[str, Any]:
    """
    Load and parse metrics JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON dict

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON

    Example:
        >>> data = load_metrics_from_file(Path("data/metrics/wikipedia_20251115_processing.json"))
        >>> print(data.keys())  # dict_keys(['_source', 'layered_metrics', ...])
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def load_all_processing_metrics(metrics_dir: Path) -> list[dict[str, Any]]:
    """
    Load all *_processing.json files from metrics directory.

    This is a convenience function that loads and consolidates all processing
    metrics, properly handling errors and logging warnings for malformed files.

    Args:
        metrics_dir: Path to data/metrics directory

    Returns:
        List of consolidated metrics dictionaries

    Example:
        >>> metrics = load_all_processing_metrics(Path("data/metrics"))
        >>> print(f"Loaded {len(metrics)} metric records")
    """
    all_metrics = []

    if not metrics_dir.exists():
        logger.warning(f"Metrics directory not found: {metrics_dir}")
        return all_metrics

    processing_files = sorted(metrics_dir.glob("*_processing.json"))

    if not processing_files:
        logger.warning(f"No *_processing.json files found in {metrics_dir}")
        return all_metrics

    for metrics_file in processing_files:
        try:
            data = load_metrics_from_file(metrics_file)
            metric = extract_consolidated_metric(data, metrics_file.name)

            if metric:
                all_metrics.append(metric)
            else:
                logger.warning(f"Skipped {metrics_file.name} (failed extraction)")

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing {metrics_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error processing {metrics_file.name}: {e}")

    return all_metrics


def aggregate_metrics_across_sources(
    metrics_dir: Path, sources: list[str], metric_field: str
) -> dict[str, Optional[float]]:
    """
    Aggregate a specific metric field across multiple sources.

    Finds the most recent metrics file for each source and extracts
    the specified field from the consolidated metric.

    Args:
        metrics_dir: Directory containing metrics files
        sources: List of source names
        metric_field: Field name to extract from consolidated metric (e.g., 'records_written')

    Returns:
        Dict mapping source name to metric value

    Example:
        >>> sources = ['wikipedia', 'bbc-somali', 'huggingface-somali']
        >>> metrics = aggregate_metrics_across_sources(
        ...     Path('data/metrics'),
        ...     sources,
        ...     'records_written'
        ... )
        >>> print(metrics)  # {'wikipedia': 9960, 'bbc-somali': 350, ...}
    """
    result = {}

    for source in sources:
        # Find most recent metrics file for this source
        pattern = f"{source}_*_processing.json"
        files = sorted(metrics_dir.glob(pattern), reverse=True)

        if not files:
            logger.warning(f"No metrics files found for {source}")
            result[source] = None
            continue

        # Use most recent file
        try:
            latest_file = files[0]
            data = load_metrics_from_file(latest_file)
            metric = extract_consolidated_metric(data, latest_file.name)

            if metric and metric_field in metric:
                result[source] = metric[metric_field]
            else:
                result[source] = None
        except Exception as e:
            logger.error(f"Error extracting {metric_field} from {source}: {e}")
            result[source] = None

    return result


def calculate_metric_statistics(values: list[Optional[float]]) -> dict[str, float]:
    """
    Calculate statistics for a list of metric values.

    Args:
        values: List of numeric values (None values filtered out)

    Returns:
        Dict with mean, median, min, max, sum, count

    Example:
        >>> values = [100, 200, 150, 300]
        >>> stats = calculate_metric_statistics(values)
        >>> print(stats)  # {'mean': 187.5, 'median': 175.0, 'sum': 750, ...}
    """
    # Filter out None values
    valid_values = [v for v in values if v is not None]

    if not valid_values:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "sum": 0.0, "count": 0}

    return {
        "mean": statistics.mean(valid_values),
        "median": statistics.median(valid_values),
        "min": min(valid_values),
        "max": max(valid_values),
        "sum": sum(valid_values),
        "count": len(valid_values),
    }
