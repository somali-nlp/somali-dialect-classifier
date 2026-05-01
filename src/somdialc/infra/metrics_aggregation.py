"""
Centralized metrics aggregation utilities.

This module provides single source of truth for extracting and transforming
metrics from processing JSON files. Eliminates code duplication across
scripts and reduces maintenance risk.

Supports Phase 3 (layered) structure with schema validation.

Usage:
    >>> from somdialc.infra.metrics_aggregation import (
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
    from somdialc.infra.metrics_schema import (
        ConsolidatedMetric,
        validate_processing_json,
    )

    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False
    logger.warning("Schema validation not available. Install with: pip install -e '.[config]'")


def extract_consolidated_metric(data: dict[str, Any], source_file: str) -> Optional[dict[str, Any]]:
    """
    Extract consolidated metric from a Phase-3 *_processing.json.

    Reads from `layered_metrics` (the current schema). If the older
    `legacy_metrics.snapshot/statistics` block is also present (test
    fixtures and pre-Phase-3 files), its richer fields — `duration_seconds`,
    `throughput`, `text_length_stats`, `fetch_duration_stats` — are used
    to enrich the output. Files without a `legacy_metrics` block return
    derived counts from `layered_metrics` only and zeros for the
    duration/throughput fields.

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
        # Best-effort schema validation. Validation only catches malformed
        # files; extraction below uses dict access so the function works for
        # both validated and non-validated payloads.
        if SCHEMA_VALIDATION_AVAILABLE:
            try:
                validate_processing_json(data)
            except Exception as validation_error:
                logger.debug(
                    f"Schema validation failed for {source_file}, "
                    f"continuing with raw extraction: {validation_error}"
                )

        # Top-level identity fields (Phase-3 underscore-prefixed names).
        layered = data.get("layered_metrics", {}) or {}
        legacy = data.get("legacy_metrics", {}) or {}
        snapshot = legacy.get("snapshot", {}) or {}
        stats = legacy.get("statistics", {}) or {}

        source = data.get("_source") or snapshot.get("source")
        if not source:
            logger.warning(f"No source found in {source_file}, skipping")
            return None
        run_id = data.get("_run_id") or snapshot.get("run_id")
        if not run_id:
            logger.warning(f"No run_id found in {source_file}, skipping")
            return None

        # Layered-metrics sublayers.
        connectivity = layered.get("connectivity", {}) or {}
        extraction = layered.get("extraction", {}) or {}
        quality = layered.get("quality", {}) or {}
        volume = layered.get("volume", {}) or {}

        # Helpers to derive counts from the new schema, with legacy fallback.
        def _first_present(*candidates: Any) -> Any:
            for value in candidates:
                if value is not None:
                    return value
            return None

        def _safe_ratio(num: Any, denom: Any) -> float:
            try:
                if denom in (None, 0, 0.0):
                    return 0.0
                return float(num or 0) / float(denom)
            except (TypeError, ValueError):
                return 0.0

        # Discovery / fetch counts. Different pipeline types populate
        # different fields under `extraction`; pick the first that applies,
        # falling back to the legacy snapshot for older files.
        urls_discovered = _first_present(
            extraction.get("http_requests_attempted"),
            extraction.get("files_discovered"),
            extraction.get("records_fetched"),
            snapshot.get("urls_discovered"),
            0,
        )
        urls_fetched = _first_present(
            extraction.get("http_requests_successful"),
            extraction.get("files_processed"),
            extraction.get("records_fetched"),
            snapshot.get("urls_fetched"),
            0,
        )
        urls_processed = _first_present(
            quality.get("records_received"),
            snapshot.get("urls_processed"),
            0,
        )
        records_extracted = _first_present(
            extraction.get("records_extracted"),
            snapshot.get("records_extracted"),
            urls_processed,
        )

        # Derived success rates. Prefer the legacy stats block when it is
        # present (operators may rely on the precomputed values), otherwise
        # compute from raw counts.
        http_success_rate = _first_present(
            stats.get("http_request_success_rate"),
            (
                _safe_ratio(
                    extraction.get("http_requests_successful"),
                    extraction.get("http_requests_attempted"),
                )
                if extraction.get("http_requests_attempted") is not None
                else None
            ),
            0,
        )
        content_extraction_rate = _first_present(
            stats.get("content_extraction_success_rate"),
            (
                _safe_ratio(extraction.get("content_extracted"), extraction.get("pages_parsed"))
                if extraction.get("pages_parsed") is not None
                else None
            ),
            (
                _safe_ratio(extraction.get("files_processed"), extraction.get("files_discovered"))
                if extraction.get("files_discovered") is not None
                else None
            ),
            1.0 if connectivity.get("connection_successful") else 0.0,
        )
        quality_pass_rate = _first_present(
            stats.get("quality_pass_rate"),
            _safe_ratio(quality.get("records_passed_filters"), quality.get("records_received")),
        )

        # Throughput requires a duration. Phase-3 payloads do not carry one;
        # fall back to the legacy statistics block when available, else 0.
        throughput = stats.get("throughput", {}) or {}

        metric: dict[str, Any] = {
            "run_id": run_id,
            "source": source,
            "timestamp": data.get("_timestamp") or snapshot.get("timestamp", ""),
            "duration_seconds": snapshot.get("duration_seconds", 0),
            "pipeline_type": data.get("_pipeline_type")
            or snapshot.get("pipeline_type", "unknown"),
            # Discovery / fetch counts (from layered_metrics, legacy fallback)
            "urls_discovered": urls_discovered or 0,
            "urls_fetched": urls_fetched or 0,
            "urls_processed": urls_processed or 0,
            "records_extracted": records_extracted or 0,
            # Volume (from layered_metrics.volume)
            "records_written": volume.get("records_written", 0),
            "bytes_downloaded": volume.get("bytes_downloaded", 0),
            "total_chars": volume.get("total_chars", 0),
            # Quality / success rates (computed from raw counts when the
            # legacy stats block is absent)
            "http_request_success_rate": http_success_rate or 0,
            "content_extraction_success_rate": content_extraction_rate or 0,
            "quality_pass_rate": quality_pass_rate or 0,
            "deduplication_rate": stats.get("deduplication_rate", 0),
            # Throughput (only in legacy schema; defaults to 0 for Phase-3)
            "urls_per_second": throughput.get("urls_per_second", 0),
            "bytes_per_second": throughput.get("bytes_per_second", 0),
            "records_per_minute": throughput.get("records_per_minute", 0),
        }

        # Optional richer stats from the legacy block.
        if stats.get("text_length_stats"):
            metric["text_length_stats"] = stats["text_length_stats"]
        if stats.get("fetch_duration_stats"):
            metric["fetch_duration_stats"] = stats["fetch_duration_stats"]

        # Filter breakdown — surface from layered_metrics.quality (Phase-3)
        # OR legacy filter_reasons (older snapshots).
        filter_breakdown = quality.get("filter_breakdown") or snapshot.get("filter_reasons")
        if filter_breakdown:
            metric["filter_breakdown"] = filter_breakdown

        # Best-effort consolidated-shape validation. Failures are logged but
        # don't suppress the metric — schema drift here should not silently
        # blank the dashboard.
        if SCHEMA_VALIDATION_AVAILABLE:
            try:
                ConsolidatedMetric.model_validate(metric)
            except Exception as e:
                logger.debug(f"Consolidated metric validation failed for {source_file}: {e}")

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
