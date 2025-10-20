#!/usr/bin/env python3
"""
Export Dashboard Data

Aggregates metrics from data/metrics/*.json and prepares dashboard-ready data.
This script can be run manually or via GitHub Actions.

Usage:
    python scripts/export_dashboard_data.py
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sys


def load_all_metrics() -> List[Dict[str, Any]]:
    """Load all metrics JSON files."""
    metrics_dir = Path("data/metrics")

    if not metrics_dir.exists():
        print(f"Warning: {metrics_dir} does not exist")
        return []

    all_metrics = []
    seen_runs = set()  # Track unique run_ids to avoid duplicates

    # Support both naming patterns: *_metrics.json and phase-specific files
    for metrics_file in metrics_dir.glob("*.json"):
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)

            snapshot = data.get("snapshot", {})
            stats = data.get("statistics", {})

            metric_entry = {
                "run_id": snapshot.get("run_id", ""),
                "source": snapshot.get("source", ""),
                "timestamp": snapshot.get("timestamp", ""),
                "duration_seconds": snapshot.get("duration_seconds", 0),
                "records_written": snapshot.get("records_written", 0),
                "urls_discovered": snapshot.get("urls_discovered", 0),
                "urls_processed": snapshot.get("urls_processed", 0),
                "urls_failed": snapshot.get("urls_failed", 0),
                "bytes_downloaded": snapshot.get("bytes_downloaded", 0),
                "success_rate": stats.get("fetch_success_rate", 0),
                "dedup_rate": stats.get("deduplication_rate", 0),
            }

            # Add throughput if available
            if "throughput" in stats:
                metric_entry["urls_per_second"] = stats["throughput"].get("urls_per_second", 0)
                metric_entry["records_per_minute"] = stats["throughput"].get("records_per_minute", 0)

            # Only include unique runs (avoid duplicates from phase-specific files)
            run_id = metric_entry["run_id"]
            if run_id and run_id not in seen_runs:
                seen_runs.add(run_id)
                all_metrics.append(metric_entry)

        except Exception as e:
            print(f"Error loading {metrics_file.name}: {e}")
            continue

    return all_metrics


def generate_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics for dashboard."""
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
            }
        }

    # Sort by timestamp
    sorted_metrics = sorted(metrics, key=lambda x: x["timestamp"])

    summary = {
        "total_records": sum(m["records_written"] for m in metrics),
        "total_urls_processed": sum(m["urls_processed"] for m in metrics),
        "avg_success_rate": sum(m["success_rate"] for m in metrics) / len(metrics),
        "total_data_downloaded_bytes": sum(m["bytes_downloaded"] for m in metrics),
        "sources": sorted(list(set(m["source"] for m in metrics))),
        "last_update": sorted_metrics[-1]["timestamp"],
        "total_runs": len(metrics),
        "date_range": {
            "start": sorted_metrics[0]["timestamp"],
            "end": sorted_metrics[-1]["timestamp"]
        }
    }

    # Per-source breakdown
    source_stats = {}
    for source in summary["sources"]:
        source_metrics = [m for m in metrics if m["source"] == source]
        source_stats[source] = {
            "records": sum(m["records_written"] for m in source_metrics),
            "runs": len(source_metrics),
            "avg_success_rate": sum(m["success_rate"] for m in source_metrics) / len(source_metrics),
            "last_run": max(m["timestamp"] for m in source_metrics)
        }

    summary["source_breakdown"] = source_stats

    return summary


def export_for_github_pages(output_dir: Path = Path("_site/data")):
    """
    Export data for GitHub Pages deployment.

    This creates JSON files that the static dashboard can consume.
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
    all_metrics_file = output_dir / "all_metrics.json"
    with open(all_metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

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

    print("\n[SUCCESS] Dashboard data export complete!")


if __name__ == "__main__":
    main()
