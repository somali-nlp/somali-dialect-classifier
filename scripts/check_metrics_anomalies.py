#!/usr/bin/env python3
"""
Check metrics files for anomalies and generate anomaly report.

This script scans all processing metrics files for validation warnings
and anomalies (e.g., records_passed_filters > records_received).

Usage:
    python scripts/check_metrics_anomalies.py
    python scripts/check_metrics_anomalies.py --metrics-dir data/metrics
    python scripts/check_metrics_anomalies.py --output test-results/anomalies.json

Exit Codes:
    0: No anomalies found
    1: Warnings found (3+ warning-level anomalies)
    2: Errors found (any error-level anomalies)
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any


class AnomalyLevel:
    """Anomaly severity levels."""
    WARNING = "warning"
    ERROR = "error"


def check_file_for_anomalies(metrics_file: Path) -> List[Dict[str, Any]]:
    """
    Check a single metrics file for anomalies.

    Returns:
        List of anomaly dictionaries with keys:
        - file: filename
        - source: data source name
        - level: "warning" or "error"
        - message: description of anomaly
        - timestamp: when metrics were generated
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
                "message": f"METRICS_ANOMALY: records_passed_filters ({records_passed_filters}) > records_received ({records_received})",
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
                "message": f"METRICS_ANOMALY: quality_pass_rate ({quality_pass_rate}) > 1.0 (impossible percentage)",
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
                "message": f"METRICS_ANOMALY: records_written ({records_written}) < 0 (negative record count)",
                "timestamp": timestamp,
                "details": {
                    "records_written": records_written
                }
            })

        # Anomaly Check 4: filter_breakdown sum mismatch
        filter_breakdown = quality.get("filter_breakdown", {})
        if filter_breakdown and records_filtered > 0:
            filter_sum = sum(filter_breakdown.values())
            # Allow 5% tolerance
            tolerance = max(1, int(records_filtered * 0.05))

            if abs(filter_sum - records_filtered) > tolerance:
                anomalies.append({
                    "file": metrics_file.name,
                    "source": source,
                    "level": AnomalyLevel.WARNING,
                    "message": f"METRICS_ANOMALY: filter_breakdown sum ({filter_sum}) != records_filtered ({records_filtered}), diff={abs(filter_sum - records_filtered)}",
                    "timestamp": timestamp,
                    "details": {
                        "filter_sum": filter_sum,
                        "records_filtered": records_filtered,
                        "difference": abs(filter_sum - records_filtered),
                        "tolerance": tolerance
                    }
                })

        # Anomaly Check 5: records_received = 0 but has records_written
        if records_received == 0 and records_written > 0:
            anomalies.append({
                "file": metrics_file.name,
                "source": source,
                "level": AnomalyLevel.WARNING,
                "message": f"METRICS_ANOMALY: records_received=0 but records_written={records_written} (possible missing instrumentation)",
                "timestamp": timestamp,
                "details": {
                    "records_received": records_received,
                    "records_written": records_written
                }
            })

    except json.JSONDecodeError as e:
        anomalies.append({
            "file": metrics_file.name,
            "source": "unknown",
            "level": AnomalyLevel.ERROR,
            "message": f"Failed to parse metrics JSON: {e}",
            "timestamp": "",
            "details": {"error": str(e)}
        })
    except Exception as e:
        anomalies.append({
            "file": metrics_file.name,
            "source": "unknown",
            "level": AnomalyLevel.ERROR,
            "message": f"Unexpected error processing metrics: {e}",
            "timestamp": "",
            "details": {"error": str(e)}
        })

    return anomalies


def scan_metrics_directory(metrics_dir: Path) -> Dict[str, Any]:
    """
    Scan all metrics files in directory for anomalies.

    Returns:
        Dictionary with keys:
        - total_files: number of files scanned
        - total_anomalies: total anomaly count
        - error_count: number of error-level anomalies
        - warning_count: number of warning-level anomalies
        - anomalies: list of all anomalies
        - sources_affected: unique sources with anomalies
        - generated_at: timestamp
    """
    if not metrics_dir.exists():
        return {
            "total_files": 0,
            "total_anomalies": 0,
            "error_count": 0,
            "warning_count": 0,
            "anomalies": [],
            "sources_affected": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": f"Metrics directory not found: {metrics_dir}"
        }

    # Find all processing.json files
    metrics_files = sorted(metrics_dir.glob("*_processing.json"))

    all_anomalies = []
    for metrics_file in metrics_files:
        file_anomalies = check_file_for_anomalies(metrics_file)
        all_anomalies.extend(file_anomalies)

    # Count by severity
    error_count = sum(1 for a in all_anomalies if a["level"] == AnomalyLevel.ERROR)
    warning_count = sum(1 for a in all_anomalies if a["level"] == AnomalyLevel.WARNING)

    # Get unique sources affected
    sources_affected = sorted(list(set(a["source"] for a in all_anomalies)))

    return {
        "total_files": len(metrics_files),
        "total_anomalies": len(all_anomalies),
        "error_count": error_count,
        "warning_count": warning_count,
        "anomalies": all_anomalies,
        "sources_affected": sources_affected,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check metrics files for calculation anomalies"
    )
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=Path("data/metrics"),
        help="Directory containing metrics JSON files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test-results/anomalies.json"),
        help="Output file for anomaly report"
    )
    parser.add_argument(
        "--warning-threshold",
        type=int,
        default=3,
        help="Number of warnings to trigger CI warning (default: 3)"
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with code 2 if any error-level anomalies found"
    )

    args = parser.parse_args()

    # Scan metrics directory
    print(f"Scanning metrics directory: {args.metrics_dir}")
    report = scan_metrics_directory(args.metrics_dir)

    # Write report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Metrics Anomaly Report")
    print(f"{'='*60}")
    print(f"Files scanned:       {report['total_files']}")
    print(f"Total anomalies:     {report['total_anomalies']}")
    print(f"  - Errors:          {report['error_count']}")
    print(f"  - Warnings:        {report['warning_count']}")
    print(f"Sources affected:    {', '.join(report['sources_affected']) if report['sources_affected'] else 'None'}")
    print(f"Report written to:   {args.output}")
    print(f"{'='*60}")

    # Print anomalies if found
    if report['total_anomalies'] > 0:
        print("\nAnomalies detected:")
        for anomaly in report['anomalies']:
            level_icon = "🚨" if anomaly['level'] == AnomalyLevel.ERROR else "⚠️"
            print(f"  {level_icon} [{anomaly['level'].upper()}] {anomaly['source']}: {anomaly['message']}")

    # Determine exit code
    exit_code = 0

    if report['error_count'] > 0 and args.fail_on_error:
        print(f"\n❌ FAILED: {report['error_count']} error-level anomalies detected")
        exit_code = 2
    elif report['warning_count'] >= args.warning_threshold:
        print(f"\n⚠️  WARNING: {report['warning_count']} warning-level anomalies detected (threshold: {args.warning_threshold})")
        exit_code = 1
    elif report['total_anomalies'] == 0:
        print("\n✅ PASSED: No anomalies detected")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
