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
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from somali_dialect_classifier.utils.metrics_schema import (
        validate_processing_json,
        ConsolidatedMetric,
        ConsolidatedMetricsOutput,
        DashboardSummary,
    )
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    print("Warning: Schema validation not available. Install with: pip install -e '.[config]'", file=sys.stderr)
    SCHEMA_VALIDATION_AVAILABLE = False


def extract_consolidated_metric(data: Dict[str, Any], source_file: str) -> Optional[Dict[str, Any]]:
    """
    Extract consolidated metric from Phase 3 *_processing.json.

    This function properly surfaces layered_metrics and computes
    derived statistics for dashboard consumption.

    Args:
        data: Loaded JSON from *_processing.json
        source_file: Filename for error reporting

    Returns:
        Consolidated metric dict, or None if extraction fails
    """
    try:
        # Validate schema if available
        if SCHEMA_VALIDATION_AVAILABLE:
            validated = validate_processing_json(data)

            # Guard against null sources (stale data)
            source = validated.source
            run_id = validated.run_id

            # Access Pydantic model attributes directly
            layered = validated.layered_metrics
            legacy = validated.legacy_metrics
            snapshot = legacy.snapshot
            stats = legacy.statistics

            connectivity = layered.connectivity
            extraction = layered.extraction
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
                print(f"Warning: No source found in {source_file}, skipping", file=sys.stderr)
                return None

            run_id = data.get("_run_id") or snapshot.get("run_id")
            if not run_id:
                print(f"Warning: No run_id found in {source_file}, skipping", file=sys.stderr)
                return None

            connectivity = layered.get("connectivity", {})
            extraction = layered.get("extraction", {})
            quality = layered.get("quality", {})
            volume = layered.get("volume", {})

        # Build consolidated metric (handle both Pydantic and dict access)
        if SCHEMA_VALIDATION_AVAILABLE:
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
                "pipeline_type": data.get("_pipeline_type") or snapshot.get("pipeline_type", "unknown"),

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

        # Validate consolidated metric if schema available
        if SCHEMA_VALIDATION_AVAILABLE:
            try:
                ConsolidatedMetric.model_validate(metric)
            except Exception as e:
                print(f"Warning: Consolidated metric validation failed for {source_file}: {e}", file=sys.stderr)
                # Continue anyway, but log the issue

        return metric

    except KeyError as e:
        print(f"Error: Missing required field in {source_file}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing {source_file}: {e}", file=sys.stderr)
        return None


def load_metrics(metrics_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all metrics from individual JSON files.

    Args:
        metrics_dir: Path to data/metrics directory

    Returns:
        List of consolidated metrics
    """
    all_metrics = []

    if not metrics_dir.exists():
        print(f"Warning: Metrics directory not found: {metrics_dir}", file=sys.stderr)
        return all_metrics

    processing_files = sorted(metrics_dir.glob("*_processing.json"))

    if not processing_files:
        print(f"Warning: No *_processing.json files found in {metrics_dir}", file=sys.stderr)

    for metrics_file in processing_files:
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            metric = extract_consolidated_metric(data, metrics_file.name)

            if metric:
                all_metrics.append(metric)
            else:
                print(f"Skipped {metrics_file.name} (failed extraction)", file=sys.stderr)

        except json.JSONDecodeError as e:
            print(f"Error parsing {metrics_file.name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {metrics_file.name}: {e}", file=sys.stderr)

    return all_metrics


def generate_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    sources = sorted(set(m["source"] for m in metrics if m["source"]))

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
    print(f"\nSummary:")
    print(f"  Total Records: {summary['total_records']:,}")
    print(f"  Total URLs Processed: {summary['total_urls_processed']:,}")
    print(f"  Avg HTTP Success Rate: {summary['avg_success_rate']:.1%}")
    print(f"  Total Data Downloaded: {summary['total_data_downloaded_bytes']:,} bytes")
    print(f"  Sources: {', '.join(summary['sources'])}")
    print(f"  Total Runs: {summary['total_runs']}")

    if SCHEMA_VALIDATION_AVAILABLE:
        print(f"\n✓ All schema validations passed")
    else:
        print(f"\n⚠ Schema validation skipped (pydantic not installed)")


if __name__ == "__main__":
    main()
