#!/usr/bin/env python3
"""
Generate consolidated all_metrics.json from individual metric files.

This script consolidates all metrics/*.json files into a single file for
improved dashboard performance and reduced HTTP requests.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def load_metrics(metrics_dir: Path) -> List[Dict[str, Any]]:
    """Load all metrics from individual JSON files."""
    all_metrics = []

    if not metrics_dir.exists():
        print(f"Warning: Metrics directory not found: {metrics_dir}", file=sys.stderr)
        return all_metrics

    for metrics_file in sorted(metrics_dir.glob("*_processing.json")):
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            snapshot = data.get("snapshot", {})
            stats = data.get("statistics", {})

            # Extract key metrics
            metric = {
                "run_id": snapshot.get("run_id"),
                "source": snapshot.get("source"),
                "timestamp": snapshot.get("timestamp"),
                "duration_seconds": snapshot.get("duration_seconds", 0),
                "urls_discovered": snapshot.get("urls_discovered", 0),
                "urls_fetched": snapshot.get("urls_fetched", 0),
                "urls_processed": snapshot.get("urls_processed", 0),
                "records_written": snapshot.get("records_written", 0),
                "bytes_downloaded": snapshot.get("bytes_downloaded", 0),
                "success_rate": stats.get("fetch_success_rate", 0),
                "deduplication_rate": stats.get("deduplication_rate", 0),
                "performance": stats.get("throughput", {}),
                "quality": stats.get("text_length_stats", {})
            }

            all_metrics.append(metric)

        except json.JSONDecodeError as e:
            print(f"Error parsing {metrics_file.name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {metrics_file.name}: {e}", file=sys.stderr)

    return all_metrics


def generate_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics from metrics."""
    if not metrics:
        return {
            "total_records": 0,
            "avg_success_rate": 0,
            "sources": [],
            "total_runs": 0,
            "last_update": datetime.utcnow().isoformat() + "Z"
        }

    total_records = sum(m["records_written"] for m in metrics)
    success_rates = [m["success_rate"] for m in metrics if m["success_rate"] > 0]
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
    sources = list(set(m["source"] for m in metrics if m["source"]))

    return {
        "total_records": total_records,
        "avg_success_rate": avg_success_rate,
        "sources": sorted(sources),
        "total_runs": len(metrics),
        "last_update": datetime.utcnow().isoformat() + "Z"
    }


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
        print("No metrics found. Creating empty consolidated file.")
    else:
        print(f"Loaded {len(metrics)} metric records")

    # Generate summary
    summary = generate_summary(metrics)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write consolidated metrics
    all_metrics_file = output_dir / "all_metrics.json"
    with open(all_metrics_file, 'w', encoding='utf-8') as f:
        json.dump({
            "count": len(metrics),
            "records": summary["total_records"],
            "sources": summary["sources"],
            "metrics": metrics
        }, f, indent=2)

    print(f"✓ Wrote consolidated metrics to: {all_metrics_file}")

    # Write summary (update existing)
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Wrote summary to: {summary_file}")
    print(f"\nSummary:")
    print(f"  Total Records: {summary['total_records']:,}")
    print(f"  Avg Success Rate: {summary['avg_success_rate']:.1%}")
    print(f"  Sources: {', '.join(summary['sources'])}")
    print(f"  Total Runs: {summary['total_runs']}")


if __name__ == "__main__":
    main()
