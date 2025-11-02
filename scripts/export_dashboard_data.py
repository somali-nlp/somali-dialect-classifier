#!/usr/bin/env python3
"""
Export Dashboard Data

Aggregates metrics from data/metrics/*.json and prepares dashboard-ready data.
This script can be run manually or via GitHub Actions. It includes schema
validation to ensure data integrity.

Schema Contract:
    - Input: data/metrics/*_processing.json (Phase 3 schema)
    - Output: _site/data/all_metrics.json (validated)
    - Output: _site/data/summary.json (validated)
    - Output: _site/data/reports.json (optional)

Usage:
    python scripts/export_dashboard_data.py [--github-pages|--local]
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sys

try:
    from somali_dialect_classifier.utils.metrics_schema import (
        validate_processing_json,
        validate_consolidated_metrics,
        validate_dashboard_summary,
        ConsolidatedMetric,
    )
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    print("Warning: Schema validation not available. Install with: pip install -e '.[config]'", file=sys.stderr)
    SCHEMA_VALIDATION_AVAILABLE = False


def load_all_metrics() -> List[Dict[str, Any]]:
    """
    Load all metrics JSON files with Phase 3 schema support.

    Returns:
        List of consolidated metric dictionaries
    """
    metrics_dir = Path("data/metrics")

    if not metrics_dir.exists():
        print(f"Warning: {metrics_dir} does not exist")
        return []

    all_metrics = []
    seen_runs = set()

    for metrics_file in sorted(metrics_dir.glob("*_processing.json")):
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)

            # Validate input schema if available
            if SCHEMA_VALIDATION_AVAILABLE:
                try:
                    validated = validate_processing_json(data)
                    # Convert Pydantic models to dicts for uniform access
                    layered = validated.layered_metrics.model_dump() if hasattr(validated.layered_metrics, 'model_dump') else validated.layered_metrics.dict()
                    legacy = validated.legacy_metrics.model_dump() if hasattr(validated.legacy_metrics, 'model_dump') else validated.legacy_metrics.dict()
                    snapshot = legacy.get("snapshot", {})
                    stats = legacy.get("statistics", {})
                except Exception as e:
                    print(f"Schema validation failed for {metrics_file.name}: {e}", file=sys.stderr)
                    continue
            else:
                # Fallback to dict access
                layered = data.get("layered_metrics", {})
                legacy = data.get("legacy_metrics", {})
                snapshot = legacy.get("snapshot", {})
                stats = legacy.get("statistics", {})

            # Extract consolidated metric
            run_id = data.get("_run_id") or snapshot.get("run_id", "")
            source = data.get("_source") or snapshot.get("source", "")

            # Guard against null sources
            if not source or not run_id:
                print(f"Warning: Missing source or run_id in {metrics_file.name}", file=sys.stderr)
                continue

            # Skip duplicates
            if run_id in seen_runs:
                continue
            seen_runs.add(run_id)

            # Extract from layered metrics (Phase 3)
            volume = layered.get("volume", {})
            quality = layered.get("quality", {})

            # CRITICAL FIX: Calculate quality_pass_rate from filter_breakdown
            # Bug: Pre-calculated quality_pass_rate in stats was wrong for TikTok/HuggingFace
            # Correct formula: passed / (passed + sum(filter_breakdown))
            filter_breakdown = quality.get("filter_breakdown", {})
            records_passed = quality.get("records_passed_filters", 0)

            if filter_breakdown and sum(filter_breakdown.values()) > 0:
                # Calculate from actual filter data (most accurate)
                total_filtered = sum(filter_breakdown.values())
                total_input = records_passed + total_filtered
                quality_pass_rate = records_passed / total_input if total_input > 0 else 0
            else:
                # Fallback to pre-calculated value
                quality_pass_rate = stats.get("quality_pass_rate") or 0

            metric_entry = {
                "run_id": run_id,
                "source": source,
                "timestamp": data.get("_timestamp") or snapshot.get("timestamp", ""),
                "pipeline_type": data.get("_pipeline_type", "unknown"),
                "duration_seconds": snapshot.get("duration_seconds", 0),

                # Discovery metrics
                "urls_discovered": snapshot.get("urls_discovered", 0),
                "urls_fetched": snapshot.get("urls_fetched", 0),
                "urls_processed": snapshot.get("urls_processed", 0),

                # Volume metrics (from layered_metrics.volume)
                "records_written": volume.get("records_written", 0),
                "bytes_downloaded": volume.get("bytes_downloaded", 0),
                "total_chars": volume.get("total_chars", 0),

                # Quality metrics (from statistics) - handle None for non-web pipelines
                "http_request_success_rate": stats.get("http_request_success_rate") or 0,
                "content_extraction_success_rate": stats.get("content_extraction_success_rate") or 0,
                "quality_pass_rate": quality_pass_rate,  # Now correctly calculated
                "deduplication_rate": stats.get("deduplication_rate") or 0,

                # Throughput metrics
                "urls_per_second": stats.get("throughput", {}).get("urls_per_second", 0),
                "bytes_per_second": stats.get("throughput", {}).get("bytes_per_second", 0),
                "records_per_minute": stats.get("throughput", {}).get("records_per_minute", 0),
            }

            # Optional detailed stats
            if "text_length_stats" in stats and stats["text_length_stats"]:
                metric_entry["text_length_stats"] = stats["text_length_stats"]

            if "fetch_duration_stats" in stats and stats["fetch_duration_stats"]:
                metric_entry["fetch_duration_stats"] = stats["fetch_duration_stats"]

            # Filter breakdown
            filter_breakdown = quality.get("filter_breakdown", {})
            if filter_breakdown:
                metric_entry["filter_breakdown"] = filter_breakdown

            # Validate consolidated metric
            if SCHEMA_VALIDATION_AVAILABLE:
                try:
                    ConsolidatedMetric.model_validate(metric_entry)
                except Exception as e:
                    print(f"Warning: Consolidated metric validation failed for {metrics_file.name}: {e}", file=sys.stderr)

            all_metrics.append(metric_entry)

        except json.JSONDecodeError as e:
            print(f"Error loading {metrics_file.name}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Error processing {metrics_file.name}: {e}", file=sys.stderr)
            continue

    return all_metrics


def generate_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for dashboard.

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
            "last_update": datetime.now().isoformat(),
            "total_runs": 0,
            "date_range": {
                "start": None,
                "end": None
            },
            "source_breakdown": {}
        }

    # Sort by timestamp
    sorted_metrics = sorted(metrics, key=lambda x: x["timestamp"])

    total_records = sum(m["records_written"] for m in metrics)
    total_urls = sum(m["urls_processed"] for m in metrics)
    total_bytes = sum(m["bytes_downloaded"] for m in metrics)

    # Use http_request_success_rate as primary metric (handle None values)
    success_rates = [m["http_request_success_rate"] for m in metrics if m.get("http_request_success_rate") and m["http_request_success_rate"] > 0]
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0

    sources = sorted(list(set(m["source"] for m in metrics)))

    summary = {
        "total_records": total_records,
        "total_urls_processed": total_urls,
        "avg_success_rate": avg_success_rate,
        "total_data_downloaded_bytes": total_bytes,
        "sources": sources,
        "last_update": sorted_metrics[-1]["timestamp"] if sorted_metrics else datetime.now().isoformat(),
        "total_runs": len(metrics),
        "date_range": {
            "start": sorted_metrics[0]["timestamp"] if sorted_metrics else None,
            "end": sorted_metrics[-1]["timestamp"] if sorted_metrics else None
        }
    }

    # Per-source breakdown
    source_stats = {}
    for source in sources:
        source_metrics = [m for m in metrics if m["source"] == source]
        # Handle None values in success rates
        http_rates = [m["http_request_success_rate"] for m in source_metrics if m.get("http_request_success_rate") is not None]
        quality_rates = [m["quality_pass_rate"] for m in source_metrics if m.get("quality_pass_rate") is not None]

        source_stats[source] = {
            "records": sum(m["records_written"] for m in source_metrics),
            "runs": len(source_metrics),
            "avg_success_rate": sum(http_rates) / len(http_rates) if http_rates else 0,
            "avg_quality_pass_rate": sum(quality_rates) / len(quality_rates) if quality_rates else 0,
            "total_chars": sum(m["total_chars"] for m in source_metrics),
            "last_run": max(m["timestamp"] for m in source_metrics)
        }

    summary["source_breakdown"] = source_stats

    # Validate summary schema
    if SCHEMA_VALIDATION_AVAILABLE:
        try:
            validate_dashboard_summary(summary)
        except Exception as e:
            print(f"Warning: Summary schema validation failed: {e}", file=sys.stderr)

    return summary


def export_for_github_pages(output_dir: Path = Path("_site/data")):
    """
    Export data for GitHub Pages deployment.

    This creates JSON files that the static dashboard can consume.
    Includes schema validation to ensure data integrity.

    Args:
        output_dir: Output directory for exported files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load metrics
    metrics = load_all_metrics()
    summary = generate_summary(metrics)

    # Export summary
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"[SUCCESS] Exported summary to {summary_file}")
    print(f"   - Total records: {summary['total_records']:,}")
    print(f"   - Total runs: {summary['total_runs']}")
    print(f"   - Sources: {', '.join(summary['sources'])}")

    # Export all metrics (for advanced usage)
    all_metrics_output = {
        "count": len(metrics),
        "records": summary["total_records"],
        "sources": summary["sources"],
        "metrics": metrics
    }

    # Validate consolidated output
    if SCHEMA_VALIDATION_AVAILABLE:
        try:
            validate_consolidated_metrics(all_metrics_output)
            print("[SUCCESS] Schema validation passed for all_metrics.json")
        except Exception as e:
            print(f"[ERROR] Schema validation failed: {e}", file=sys.stderr)
            sys.exit(1)

    all_metrics_file = output_dir / "all_metrics.json"
    with open(all_metrics_file, 'w') as f:
        json.dump(all_metrics_output, f, indent=2)

    print(f"[SUCCESS] Exported all metrics to {all_metrics_file}")

    # Export reports list
    reports_dir = Path("data/reports")
    if reports_dir.exists():
        reports_list = []
        for report_file in reports_dir.glob("*_final_quality_report.md"):
            reports_list.append({
                "name": report_file.stem.replace("_final_quality_report", ""),
                "filename": report_file.name,
                "path": str(report_file)
            })

        reports_file = output_dir / "reports.json"
        with open(reports_file, 'w') as f:
            json.dump(sorted(reports_list, key=lambda x: x["name"], reverse=True), f, indent=2)

        print(f"[SUCCESS] Exported {len(reports_list)} reports to {reports_file}")

    return summary


def export_for_local_dashboard(output_dir: Path = Path("dashboard/data")):
    """
    Export data for local Streamlit dashboard (optional).

    This is useful if you want to pre-aggregate data for faster loading.

    Args:
        output_dir: Output directory for local cache
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = load_all_metrics()
    summary = generate_summary(metrics)

    # Export
    with open(output_dir / "cache_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"[SUCCESS] Exported local dashboard cache to {output_dir}")


def main():
    """Main entry point."""
    print("[INFO] Exporting dashboard data...\n")

    # Export for GitHub Pages (used by CI/CD)
    if len(sys.argv) > 1 and sys.argv[1] == "--github-pages":
        export_for_github_pages()
    # Export for local development
    elif len(sys.argv) > 1 and sys.argv[1] == "--local":
        export_for_local_dashboard()
    # Export both
    else:
        print("[INFO] GitHub Pages Export:")
        export_for_github_pages()
        print("\n[INFO] Local Dashboard Cache:")
        export_for_local_dashboard()

    if SCHEMA_VALIDATION_AVAILABLE:
        print("\n[SUCCESS] Dashboard data export complete with schema validation!")
    else:
        print("\n[SUCCESS] Dashboard data export complete (schema validation skipped)")


if __name__ == "__main__":
    main()
