"""
Metrics command implementations for somali-tools CLI.

This module contains testable library code for metrics operations.
Separated from CLI to enable unit testing without Click framework.

Functions are extracted from scripts:
- generate_consolidated_metrics.py
- generate_enhanced_metrics.py
- check_metrics_anomalies.py
- validate_metrics_schema.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import schema validation and utilities
try:
    from somali_dialect_classifier.infra.metrics_aggregation import (
        extract_consolidated_metric,
        load_all_processing_metrics,
        load_metrics_from_file,
    )
    from somali_dialect_classifier.infra.metrics_schema import (
        ConsolidatedMetric,
        ConsolidatedMetricsOutput,
        DashboardSummary,
        validate_processing_json,
    )
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Schema validation not available: {e}")
    SCHEMA_VALIDATION_AVAILABLE = False


# ============================================================================
# METRICS CONSOLIDATION
# ============================================================================


def consolidate_metrics(
    metrics_dir: Path,
    output_path: Path,
    source_filter: list[str] | None = None
) -> Path:
    """
    Consolidate metrics from multiple processing files.

    Args:
        metrics_dir: Directory containing *_processing.json files
        output_path: Output path for consolidated metrics
        source_filter: Optional list of sources to include

    Returns:
        Path to written consolidated metrics file

    Raises:
        FileNotFoundError: If metrics_dir doesn't exist
        ValueError: If no metrics found
    """
    if not metrics_dir.exists():
        raise FileNotFoundError(f"Metrics directory not found: {metrics_dir}")

    # Load all metrics
    logger.info(f"Loading metrics from: {metrics_dir}")
    metrics = load_all_processing_metrics(metrics_dir)

    # Filter by source if specified
    if source_filter:
        metrics = [m for m in metrics if m.get("source") in source_filter]
        logger.info(f"Filtered to {len(metrics)} metrics matching sources: {source_filter}")

    if not metrics:
        logger.warning("No metrics found matching criteria")

    logger.info(f"Successfully loaded {len(metrics)} metric records")

    # Generate summary
    summary = generate_summary(metrics)

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write consolidated metrics
    consolidated_output = {
        "count": len(metrics),
        "records": summary["total_records"],
        "sources": summary["sources"],
        "metrics": metrics
    }

    # Validate if schema available
    if SCHEMA_VALIDATION_AVAILABLE:
        try:
            ConsolidatedMetricsOutput.model_validate(consolidated_output)
            logger.info("Schema validation passed for consolidated metrics")
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            raise ValueError(f"Schema validation failed: {e}")

    # Write consolidated file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated_output, f, indent=2)

    logger.info(f"Wrote consolidated metrics to: {output_path}")

    # Write summary file alongside
    summary_path = output_path.parent / "summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Wrote summary to: {summary_path}")

    return output_path


def generate_summary(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate summary statistics from consolidated metrics.

    Args:
        metrics: List of consolidated metrics

    Returns:
        Dashboard summary dict with aggregate statistics
    """
    if not metrics:
        return {
            "total_records": 0,
            "total_urls_processed": 0,
            "avg_success_rate": 0,
            "total_data_downloaded_bytes": 0,
            "sources": [],
            "total_runs": 0,
            "last_update": datetime.utcnow().isoformat() + "Z",
            "source_breakdown": {}
        }

    total_records = sum(m.get("records_written", 0) for m in metrics)
    total_urls = sum(m.get("urls_processed", 0) for m in metrics)
    total_bytes = sum(m.get("bytes_downloaded", 0) for m in metrics)

    # Use http_request_success_rate as primary success metric (skip None values)
    success_rates = [
        m["http_request_success_rate"]
        for m in metrics
        if m.get("http_request_success_rate") is not None
        and m["http_request_success_rate"] > 0
    ]
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0

    sources = sorted({m["source"] for m in metrics if m.get("source")})

    # Per-source breakdown
    source_stats = {}
    for source in sources:
        source_metrics = [m for m in metrics if m.get("source") == source]

        # Calculate avg_success_rate, handling None values
        source_success_rates = [
            m["http_request_success_rate"]
            for m in source_metrics
            if m.get("http_request_success_rate") is not None
        ]
        avg_success = (
            sum(source_success_rates) / len(source_success_rates)
            if source_success_rates else 0.0
        )

        source_stats[source] = {
            "records": sum(m.get("records_written", 0) for m in source_metrics),
            "runs": len(source_metrics),
            "avg_success_rate": avg_success,
            "avg_quality_pass_rate": (
                sum(m.get("quality_pass_rate", 0) for m in source_metrics) /
                len(source_metrics)
            ),
            "total_chars": sum(m.get("total_chars", 0) for m in source_metrics),
            "last_run": max(m.get("timestamp", "") for m in source_metrics)
        }

    summary = {
        "total_records": total_records,
        "total_urls_processed": total_urls,
        "avg_success_rate": avg_success_rate,
        "total_data_downloaded_bytes": total_bytes,
        "sources": sources,
        "total_runs": len(metrics),
        "last_update": datetime.utcnow().isoformat() + "Z",
        "source_breakdown": source_stats
    }

    # Validate summary if schema available
    if SCHEMA_VALIDATION_AVAILABLE:
        try:
            DashboardSummary.model_validate(summary)
        except Exception as e:
            logger.warning(f"Summary validation failed: {e}")

    return summary


# ============================================================================
# METRICS VALIDATION
# ============================================================================


def validate_metrics(
    metrics_dir: Path,
    strict: bool = False
) -> dict[str, Any]:
    """
    Validate metrics files against Phase 3 schema.

    Args:
        metrics_dir: Directory containing *_processing.json files
        strict: If True, treat warnings as errors

    Returns:
        Validation report with counts and details

    Raises:
        FileNotFoundError: If metrics_dir doesn't exist
    """
    if not metrics_dir.exists():
        raise FileNotFoundError(f"Metrics directory not found: {metrics_dir}")

    if not SCHEMA_VALIDATION_AVAILABLE:
        raise ImportError(
            "Schema validation not available. Install with: pip install -e '.[config]'"
        )

    # Find all processing files
    processing_files = sorted(metrics_dir.glob("*_processing.json"))

    if not processing_files:
        logger.warning(f"No *_processing.json files found in {metrics_dir}")
        return {
            "total_files": 0,
            "valid": 0,
            "errors": 0,
            "warnings": 0,
            "files": []
        }

    results = []
    valid_count = 0
    error_count = 0
    warning_count = 0

    for file_path in processing_files:
        try:
            data = load_metrics_from_file(file_path)

            # Validate against schema
            validated = validate_processing_json(data)

            # Success
            results.append({
                "file": file_path.name,
                "status": "valid",
                "message": "Schema validation passed"
            })
            valid_count += 1

        except json.JSONDecodeError as e:
            results.append({
                "file": file_path.name,
                "status": "error",
                "message": f"Invalid JSON: {e}"
            })
            error_count += 1

        except Exception as e:
            # Check if it's a warning-level issue
            if strict or "required" in str(e).lower():
                results.append({
                    "file": file_path.name,
                    "status": "error",
                    "message": str(e)
                })
                error_count += 1
            else:
                results.append({
                    "file": file_path.name,
                    "status": "warning",
                    "message": str(e)
                })
                warning_count += 1

    return {
        "total_files": len(processing_files),
        "valid": valid_count,
        "errors": error_count,
        "warnings": warning_count,
        "files": results
    }


# ============================================================================
# ANOMALY DETECTION
# ============================================================================


class AnomalyLevel:
    """Anomaly severity levels."""
    WARNING = "warning"
    ERROR = "error"


def check_anomalies(
    metrics_dir: Path,
    threshold: int = 3
) -> dict[str, Any]:
    """
    Check for metric anomalies and outliers.

    Args:
        metrics_dir: Directory containing *_processing.json files
        threshold: Number of warnings before flagging as issue

    Returns:
        Anomaly report with findings

    Raises:
        FileNotFoundError: If metrics_dir doesn't exist
    """
    if not metrics_dir.exists():
        raise FileNotFoundError(f"Metrics directory not found: {metrics_dir}")

    # Find all processing files
    processing_files = sorted(metrics_dir.glob("*_processing.json"))

    if not processing_files:
        logger.warning(f"No *_processing.json files found in {metrics_dir}")
        return {
            "total_files": 0,
            "total_anomalies": 0,
            "error_anomalies": 0,
            "warning_anomalies": 0,
            "anomalies": []
        }

    all_anomalies = []

    for file_path in processing_files:
        try:
            file_anomalies = check_file_for_anomalies(file_path)
            all_anomalies.extend(file_anomalies)
        except Exception as e:
            logger.error(f"Error checking {file_path.name}: {e}")
            all_anomalies.append({
                "file": file_path.name,
                "source": "unknown",
                "level": AnomalyLevel.ERROR,
                "message": f"Failed to check file: {e}",
                "timestamp": "",
                "details": {}
            })

    # Count by severity
    error_count = sum(1 for a in all_anomalies if a["level"] == AnomalyLevel.ERROR)
    warning_count = sum(1 for a in all_anomalies if a["level"] == AnomalyLevel.WARNING)

    return {
        "total_files": len(processing_files),
        "total_anomalies": len(all_anomalies),
        "error_anomalies": error_count,
        "warning_anomalies": warning_count,
        "threshold": threshold,
        "anomalies": all_anomalies,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def check_file_for_anomalies(metrics_file: Path) -> list[dict[str, Any]]:
    """
    Check a single metrics file for anomalies.

    Args:
        metrics_file: Path to *_processing.json file

    Returns:
        List of anomaly dictionaries
    """
    anomalies = []

    try:
        with metrics_file.open() as f:
            metrics = json.load(f)

        source = metrics.get("source", "unknown")
        timestamp = metrics.get("timestamp", "")

        # Check layered_metrics structure
        layered = metrics.get("layered_metrics", {})
        quality = layered.get("quality", {})

        records_received = quality.get("records_received", 0)
        records_passed_filters = quality.get("records_passed_filters", 0)
        records_filtered = quality.get("records_filtered", 0)
        records_written = quality.get("records_written", 0)
        quality_pass_rate = quality.get("quality_pass_rate", 0.0)

        # Anomaly Check 1: records_passed_filters > records_received
        if records_passed_filters > records_received:
            anomalies.append({
                "file": metrics_file.name,
                "source": source,
                "level": AnomalyLevel.ERROR,
                "message": (
                    f"METRICS_ANOMALY: records_passed_filters ({records_passed_filters}) "
                    f"> records_received ({records_received})"
                ),
                "timestamp": timestamp,
                "details": {
                    "records_received": records_received,
                    "records_passed_filters": records_passed_filters,
                    "records_filtered": records_filtered
                }
            })

        # Anomaly Check 2: quality_pass_rate > 1.0
        if quality_pass_rate > 1.0:
            anomalies.append({
                "file": metrics_file.name,
                "source": source,
                "level": AnomalyLevel.ERROR,
                "message": (
                    f"METRICS_ANOMALY: quality_pass_rate ({quality_pass_rate}) "
                    f"> 1.0 (impossible percentage)"
                ),
                "timestamp": timestamp,
                "details": {
                    "quality_pass_rate": quality_pass_rate
                }
            })

        # Anomaly Check 3: records_written < 0
        if records_written < 0:
            anomalies.append({
                "file": metrics_file.name,
                "source": source,
                "level": AnomalyLevel.ERROR,
                "message": (
                    f"METRICS_ANOMALY: records_written ({records_written}) "
                    f"< 0 (negative record count)"
                ),
                "timestamp": timestamp,
                "details": {
                    "records_written": records_written
                }
            })

        # Anomaly Check 4: Zero records with non-zero URLs (warning level)
        urls_processed = layered.get("volume", {}).get("urls_processed", 0)
        if urls_processed > 0 and records_written == 0:
            anomalies.append({
                "file": metrics_file.name,
                "source": source,
                "level": AnomalyLevel.WARNING,
                "message": (
                    f"METRICS_WARNING: {urls_processed} URLs processed "
                    f"but 0 records written (possible quality issue)"
                ),
                "timestamp": timestamp,
                "details": {
                    "urls_processed": urls_processed,
                    "records_written": records_written,
                    "quality_pass_rate": quality_pass_rate
                }
            })

    except json.JSONDecodeError as e:
        anomalies.append({
            "file": metrics_file.name,
            "source": "unknown",
            "level": AnomalyLevel.ERROR,
            "message": f"JSON_ERROR: Invalid JSON in metrics file: {e}",
            "timestamp": "",
            "details": {}
        })
    except Exception as e:
        anomalies.append({
            "file": metrics_file.name,
            "source": "unknown",
            "level": AnomalyLevel.ERROR,
            "message": f"CHECK_ERROR: Failed to check file: {e}",
            "timestamp": "",
            "details": {}
        })

    return anomalies


# ============================================================================
# METRICS EXPORT
# ============================================================================


def export_metrics(
    metrics_dir: Path,
    output_path: Path,
    format: str = "json"
) -> Path:
    """
    Export metrics to various formats.

    Args:
        metrics_dir: Directory containing *_processing.json files
        output_path: Output file path
        format: Export format (json, csv, parquet)

    Returns:
        Path to written export file

    Raises:
        FileNotFoundError: If metrics_dir doesn't exist
        ValueError: If format not supported
    """
    if not metrics_dir.exists():
        raise FileNotFoundError(f"Metrics directory not found: {metrics_dir}")

    supported_formats = ["json", "csv", "parquet"]
    if format not in supported_formats:
        raise ValueError(
            f"Unsupported format: {format}. "
            f"Supported: {', '.join(supported_formats)}"
        )

    # Load all metrics
    metrics = load_all_processing_metrics(metrics_dir)

    if not metrics:
        raise ValueError("No metrics found to export")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

    elif format == "csv":
        # Flatten metrics for CSV
        import csv

        if not metrics:
            raise ValueError("No metrics to export")

        # Get all unique keys from first metric
        fieldnames = sorted(metrics[0].keys())

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for metric in metrics:
                # Convert nested dicts to JSON strings
                row = {}
                for key, value in metric.items():
                    if isinstance(value, (dict, list)):
                        row[key] = json.dumps(value)
                    else:
                        row[key] = value
                writer.writerow(row)

    elif format == "parquet":
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Parquet export requires pandas. "
                "Install with: pip install pandas pyarrow"
            )

        # Convert to DataFrame
        df = pd.DataFrame(metrics)
        df.to_parquet(output_path, index=False)

    logger.info(f"Exported {len(metrics)} metrics to {output_path} ({format})")
    return output_path
