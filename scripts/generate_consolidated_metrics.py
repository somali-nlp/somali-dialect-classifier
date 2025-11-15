#!/usr/bin/env python3
"""
Generate consolidated all_metrics.json from individual metric files.

This script consolidates all metrics/*.json files into a single file for
improved dashboard performance and reduced HTTP requests. It properly handles
Phase 3 schema by surfacing layered_metrics and computing derived statistics.

Schema Contract:
    - Input: data/metrics/*_processing.json (Phase 3 schema)
    - Output: _site/data/all_metrics.json (ConsolidatedMetricsOutput)
    - Output: _site/data/summary.json (DashboardSummary)

Usage:
    python scripts/generate_consolidated_metrics.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from somali_dialect_classifier.utils.metrics_aggregation import (
        extract_consolidated_metric,
        load_all_processing_metrics,
        load_metrics_from_file,
    )
    from somali_dialect_classifier.utils.metrics_schema import (
        ConsolidatedMetric,
        ConsolidatedMetricsOutput,
        DashboardSummary,
        validate_processing_json,
    )
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import utilities: {e}", file=sys.stderr)
    print("Install with: pip install -e '.[config]'", file=sys.stderr)
    SCHEMA_VALIDATION_AVAILABLE = False
    # Module cannot function without utilities
    sys.exit(1)


def load_metrics(metrics_dir: Path) -> list[dict[str, Any]]:
    """
    Load all metrics from individual JSON files.

    This is a thin wrapper around load_all_processing_metrics from the
    centralized utilities module.

    Args:
        metrics_dir: Path to data/metrics directory

    Returns:
        List of consolidated metrics
    """
    return load_all_processing_metrics(metrics_dir)


def generate_summary(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate summary statistics from consolidated metrics.

    Args:
        metrics: List of consolidated metrics

    Returns:
        Dashboard summary dict
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

    total_records = sum(m["records_written"] for m in metrics)
    total_urls = sum(m["urls_processed"] for m in metrics)
    total_bytes = sum(m["bytes_downloaded"] for m in metrics)

    # Use http_request_success_rate as primary success metric (skip None values)
    success_rates = [m["http_request_success_rate"] for m in metrics
                     if m["http_request_success_rate"] is not None and m["http_request_success_rate"] > 0]
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0

    sources = sorted({m["source"] for m in metrics if m["source"]})

    # Per-source breakdown
    source_stats = {}
    for source in sources:
        source_metrics = [m for m in metrics if m["source"] == source]
        # Calculate avg_success_rate, handling None values
        source_success_rates = [m["http_request_success_rate"] for m in source_metrics
                                if m["http_request_success_rate"] is not None]
        avg_success = sum(source_success_rates) / len(source_success_rates) if source_success_rates else 0.0

        source_stats[source] = {
            "records": sum(m["records_written"] for m in source_metrics),
            "runs": len(source_metrics),
            "avg_success_rate": avg_success,
            "avg_quality_pass_rate": sum(m["quality_pass_rate"] for m in source_metrics) / len(source_metrics),
            "total_chars": sum(m["total_chars"] for m in source_metrics),
            "last_run": max(m["timestamp"] for m in source_metrics)
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
            print(f"Warning: Summary validation failed: {e}", file=sys.stderr)

    return summary


def main():
    """Main execution function."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    metrics_dir = project_root / "data" / "metrics"
    output_dir = project_root / "_site" / "data"

    # Load metrics
    print(f"Loading metrics from: {metrics_dir}")
    metrics = load_metrics(metrics_dir)

    if not metrics:
        print("No valid metrics found. Creating empty consolidated file.")
    else:
        print(f"Successfully loaded {len(metrics)} metric records")

    # Generate summary
    summary = generate_summary(metrics)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write consolidated metrics
    all_metrics_file = output_dir / "all_metrics.json"
    consolidated_output = {
        "count": len(metrics),
        "records": summary["total_records"],
        "sources": summary["sources"],
        "metrics": metrics
    }

    # Validate consolidated output if schema available
    if SCHEMA_VALIDATION_AVAILABLE:
        try:
            ConsolidatedMetricsOutput.model_validate(consolidated_output)
            print("✓ Schema validation passed for all_metrics.json")
        except Exception as e:
            print(f"✗ Schema validation failed for all_metrics.json: {e}", file=sys.stderr)
            sys.exit(1)

    with open(all_metrics_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_output, f, indent=2)

    print(f"✓ Wrote consolidated metrics to: {all_metrics_file}")

    # Write summary
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Wrote summary to: {summary_file}")
    print("\nSummary:")
    print(f"  Total Records: {summary['total_records']:,}")
    print(f"  Total URLs Processed: {summary['total_urls_processed']:,}")
    print(f"  Avg HTTP Success Rate: {summary['avg_success_rate']:.1%}")
    print(f"  Total Data Downloaded: {summary['total_data_downloaded_bytes']:,} bytes")
    print(f"  Sources: {', '.join(summary['sources'])}")
    print(f"  Total Runs: {summary['total_runs']}")

    if SCHEMA_VALIDATION_AVAILABLE:
        print("\n✓ All schema validations passed")
    else:
        print("\n⚠ Schema validation skipped (pydantic not installed)")


if __name__ == "__main__":
    main()
