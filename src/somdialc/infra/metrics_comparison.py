"""
Metrics comparison and delta calculation utilities.

Provides functions to compare metrics across different runs:
- Calculate deltas between two metric runs
- Calculate percentage changes
- Identify significant changes
- Generate comparison reports
- Track trends over time

All functions work with consolidated metrics format and support
both single-run and time-series comparisons.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# COMPARISON FUNCTIONS
# ============================================================================


def calculate_delta(
    current: dict[str, Any], baseline: dict[str, Any], numeric_fields: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Calculate deltas between two metric runs.

    Args:
        current: Current metric run
        baseline: Baseline metric run to compare against
        numeric_fields: List of numeric fields to compare (auto-detect if None)

    Returns:
        Dictionary with deltas and percentage changes

    Example:
        {
            "run_id": "current_run_id",
            "baseline_run_id": "baseline_run_id",
            "deltas": {
                "records_written": 500,
                "quality_pass_rate": 0.05
            },
            "percent_changes": {
                "records_written": 5.0,
                "quality_pass_rate": 5.26
            },
            "significant_changes": ["quality_pass_rate"]
        }
    """
    if numeric_fields is None:
        # Auto-detect numeric fields
        numeric_fields = [
            "records_written",
            "urls_discovered",
            "urls_fetched",
            "urls_processed",
            "bytes_downloaded",
            "total_chars",
            "http_request_success_rate",
            "content_extraction_success_rate",
            "quality_pass_rate",
            "deduplication_rate",
            "file_extraction_success_rate",
            "stream_connection_success_rate",
            "urls_per_second",
            "bytes_per_second",
            "records_per_minute",
            "duration_seconds",
        ]

    deltas = {}
    percent_changes = {}
    significant_changes = []

    for field in numeric_fields:
        current_val = current.get(field, 0)
        baseline_val = baseline.get(field, 0)

        if not isinstance(current_val, (int, float)) or not isinstance(baseline_val, (int, float)):
            continue

        # Calculate absolute delta
        delta = current_val - baseline_val
        deltas[field] = delta

        # Calculate percentage change
        if baseline_val != 0:
            pct_change = (delta / baseline_val) * 100
            percent_changes[field] = pct_change

            # Flag significant changes (>10% or rates changed >0.05)
            if field.endswith("_rate"):
                # For rates (0-1), check if absolute change > 0.05
                if abs(delta) > 0.05:
                    significant_changes.append(field)
            else:
                # For counts, check if percentage change > 10%
                if abs(pct_change) > 10:
                    significant_changes.append(field)
        else:
            # Baseline was 0
            if current_val > 0:
                percent_changes[field] = float("inf")
                significant_changes.append(field)
            else:
                percent_changes[field] = 0

    return {
        "run_id": current.get("run_id", ""),
        "baseline_run_id": baseline.get("run_id", ""),
        "timestamp": current.get("timestamp", ""),
        "baseline_timestamp": baseline.get("timestamp", ""),
        "source": current.get("source", ""),
        "deltas": deltas,
        "percent_changes": percent_changes,
        "significant_changes": significant_changes,
    }


def compare_multiple_runs(
    metrics: list[dict[str, Any]], source: Optional[str] = None
) -> list[dict[str, Any]]:
    """
    Compare multiple runs for the same source.

    Calculates deltas between consecutive runs.

    Args:
        metrics: List of consolidated metrics (sorted by timestamp)
        source: Optional source filter (compare only this source)

    Returns:
        List of comparison results

    Example:
        >>> comparisons = compare_multiple_runs(metrics, source="BBC-Somali")
    """
    # Filter by source if specified
    if source:
        metrics = [m for m in metrics if m.get("source", "").lower() == source.lower()]

    if len(metrics) < 2:
        logger.warning(f"Need at least 2 metrics for comparison. Found: {len(metrics)}")
        return []

    # Sort by timestamp
    sorted_metrics = sorted(metrics, key=lambda m: m.get("timestamp", ""))

    comparisons = []

    # Compare consecutive runs
    for i in range(1, len(sorted_metrics)):
        baseline = sorted_metrics[i - 1]
        current = sorted_metrics[i]

        comparison = calculate_delta(current, baseline)
        comparisons.append(comparison)

    return comparisons


def identify_trends(
    comparisons: list[dict[str, Any]], metric_name: str = "quality_pass_rate"
) -> dict[str, Any]:
    """
    Identify trends from comparison data.

    Args:
        comparisons: List of comparison results from compare_multiple_runs
        metric_name: Metric to analyze for trends

    Returns:
        Dictionary with trend analysis

    Example:
        {
            "metric": "quality_pass_rate",
            "trend": "improving",  # or "declining", "stable"
            "average_change": 0.03,
            "num_increases": 5,
            "num_decreases": 2,
            "num_stable": 1
        }
    """
    if not comparisons:
        return {
            "metric": metric_name,
            "trend": "unknown",
            "average_change": 0,
            "num_increases": 0,
            "num_decreases": 0,
            "num_stable": 0,
        }

    changes = []
    increases = 0
    decreases = 0
    stable = 0

    for comp in comparisons:
        delta = comp.get("deltas", {}).get(metric_name, 0)

        if delta > 0:
            increases += 1
        elif delta < 0:
            decreases += 1
        else:
            stable += 1

        changes.append(delta)

    avg_change = sum(changes) / len(changes) if changes else 0

    # Determine overall trend
    if increases > decreases and avg_change > 0:
        trend = "improving"
    elif decreases > increases and avg_change < 0:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "metric": metric_name,
        "trend": trend,
        "average_change": avg_change,
        "num_increases": increases,
        "num_decreases": decreases,
        "num_stable": stable,
        "total_comparisons": len(comparisons),
    }


def generate_comparison_summary(
    current: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate human-readable comparison summary.

    Args:
        current: Current metric run
        baseline: Baseline metric run

    Returns:
        Dictionary with formatted comparison summary
    """
    delta_result = calculate_delta(current, baseline)

    summary = {
        "overview": {
            "current_run": current.get("run_id", ""),
            "baseline_run": baseline.get("run_id", ""),
            "source": current.get("source", ""),
            "time_between_runs": _calculate_time_diff(
                current.get("timestamp", ""), baseline.get("timestamp", "")
            ),
        },
        "key_metrics": [],
        "improvements": [],
        "regressions": [],
        "stable_metrics": [],
    }

    # Analyze key metrics
    key_metrics = [
        ("records_written", "Records Written"),
        ("quality_pass_rate", "Quality Pass Rate"),
        ("http_request_success_rate", "HTTP Success Rate"),
        ("file_extraction_success_rate", "File Extraction Rate"),
        ("deduplication_rate", "Deduplication Rate"),
    ]

    for field, label in key_metrics:
        if field not in delta_result["deltas"]:
            continue

        delta = delta_result["deltas"][field]
        pct_change = delta_result["percent_changes"].get(field, 0)
        current_val = current.get(field, 0)
        baseline_val = baseline.get(field, 0)

        metric_info = {
            "name": label,
            "current": current_val,
            "baseline": baseline_val,
            "delta": delta,
            "percent_change": pct_change,
        }

        summary["key_metrics"].append(metric_info)

        # Categorize as improvement/regression/stable
        if field in delta_result["significant_changes"]:
            if delta > 0 and not field.endswith("_rate"):
                # More records is improvement
                summary["improvements"].append(metric_info)
            elif delta > 0 and field.endswith("_rate"):
                # Higher rate is improvement (except deduplication)
                if field == "deduplication_rate":
                    summary["regressions"].append(metric_info)
                else:
                    summary["improvements"].append(metric_info)
            elif delta < 0 and field.endswith("_rate"):
                # Lower rate is regression (except deduplication)
                if field == "deduplication_rate":
                    summary["improvements"].append(metric_info)
                else:
                    summary["regressions"].append(metric_info)
            elif delta < 0:
                # Fewer records might be regression or intentional
                summary["regressions"].append(metric_info)
        else:
            summary["stable_metrics"].append(metric_info)

    return summary


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _calculate_time_diff(timestamp1: str, timestamp2: str) -> str:
    """
    Calculate human-readable time difference between two timestamps.

    Args:
        timestamp1: ISO format timestamp
        timestamp2: ISO format timestamp

    Returns:
        Human-readable time difference (e.g., "2 days, 3 hours")
    """
    try:
        dt1 = datetime.fromisoformat(timestamp1.replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(timestamp2.replace("Z", "+00:00"))

        diff = abs(dt1 - dt2)

        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        return ", ".join(parts) if parts else "less than a minute"

    except (ValueError, AttributeError):
        return "unknown"


def find_baseline(
    metrics: list[dict[str, Any]], source: str, current_run_id: str
) -> Optional[dict[str, Any]]:
    """
    Find the most recent baseline run for comparison.

    Args:
        metrics: List of consolidated metrics
        source: Source name
        current_run_id: Current run ID to exclude

    Returns:
        Baseline metric or None if not found
    """
    # Filter by source and exclude current run
    candidates = [
        m
        for m in metrics
        if m.get("source", "").lower() == source.lower() and m.get("run_id", "") != current_run_id
    ]

    if not candidates:
        return None

    # Sort by timestamp (descending)
    sorted_candidates = sorted(candidates, key=lambda m: m.get("timestamp", ""), reverse=True)

    return sorted_candidates[0]


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================


def export_comparison_data(
    current_metrics: list[dict[str, Any]], baseline_metrics: list[dict[str, Any]], output_file: Path
) -> dict[str, Any]:
    """
    Generate and export comparison data between two metric sets.

    Args:
        current_metrics: Current metrics
        baseline_metrics: Baseline metrics
        output_file: Path to output JSON file

    Returns:
        Comparison data dictionary
    """
    comparisons = []

    # Group by source
    sources = {m.get("source", "") for m in current_metrics}

    for source in sources:
        current_source = [m for m in current_metrics if m.get("source") == source]
        baseline_source = [m for m in baseline_metrics if m.get("source") == source]

        if not current_source or not baseline_source:
            continue

        # Use most recent from each
        current = sorted(current_source, key=lambda m: m.get("timestamp", ""), reverse=True)[0]
        baseline = sorted(baseline_source, key=lambda m: m.get("timestamp", ""), reverse=True)[0]

        comparison = calculate_delta(current, baseline)
        summary = generate_comparison_summary(current, baseline)

        comparisons.append({"source": source, "delta": comparison, "summary": summary})

    output_data = {
        "generated_at": datetime.now().isoformat(),
        "num_comparisons": len(comparisons),
        "comparisons": comparisons,
    }

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✓ Exported comparison data to: {output_file}")

    return output_data


def export_trend_analysis(
    metrics: list[dict[str, Any]], output_file: Path, metric_names: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Analyze and export trend data for multiple metrics.

    Args:
        metrics: List of consolidated metrics
        output_file: Path to output JSON file
        metric_names: List of metrics to analyze (auto-detect if None)

    Returns:
        Trend analysis data
    """
    if metric_names is None:
        metric_names = [
            "quality_pass_rate",
            "http_request_success_rate",
            "records_written",
            "deduplication_rate",
        ]

    # Group by source
    sources = {m.get("source", "") for m in metrics}

    trend_data = {}

    for source in sources:
        source_metrics = [m for m in metrics if m.get("source") == source]

        if len(source_metrics) < 2:
            continue

        # Generate comparisons
        comparisons = compare_multiple_runs(source_metrics)

        source_trends = {}
        for metric_name in metric_names:
            trend = identify_trends(comparisons, metric_name)
            source_trends[metric_name] = trend

        trend_data[source] = {
            "num_runs": len(source_metrics),
            "num_comparisons": len(comparisons),
            "trends": source_trends,
        }

    output = {
        "generated_at": datetime.now().isoformat(),
        "sources": list(sources),
        "metrics_analyzed": metric_names,
        "trend_data": trend_data,
    }

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    logger.info(f"✓ Exported trend analysis to: {output_file}")

    return output


def generate_comparison_report_markdown(comparison_data: dict[str, Any], output_file: Path) -> None:
    """
    Generate markdown report from comparison data.

    Args:
        comparison_data: Comparison data from export_comparison_data
        output_file: Path to markdown file
    """
    lines = [
        "# Metrics Comparison Report",
        "",
        f"**Generated:** {comparison_data['generated_at']}",
        f"**Comparisons:** {comparison_data['num_comparisons']}",
        "",
        "---",
        "",
    ]

    for comp in comparison_data["comparisons"]:
        source = comp["source"]
        summary = comp["summary"]

        lines.extend(
            [
                f"## {source}",
                "",
                f"**Current Run:** {summary['overview']['current_run']}",
                f"**Baseline Run:** {summary['overview']['baseline_run']}",
                f"**Time Between Runs:** {summary['overview']['time_between_runs']}",
                "",
                "### Key Metrics",
                "",
                "| Metric | Current | Baseline | Delta | % Change |",
                "|--------|---------|----------|-------|----------|",
            ]
        )

        for metric in summary["key_metrics"]:
            lines.append(
                f"| {metric['name']} | {metric['current']:.4f} | "
                f"{metric['baseline']:.4f} | {metric['delta']:+.4f} | "
                f"{metric['percent_change']:+.2f}% |"
            )

        lines.extend(["", "### Improvements", ""])
        if summary["improvements"]:
            for metric in summary["improvements"]:
                lines.append(
                    f"- ✅ **{metric['name']}**: {metric['delta']:+.4f} ({metric['percent_change']:+.2f}%)"
                )
        else:
            lines.append("- No significant improvements")

        lines.extend(["", "### Regressions", ""])
        if summary["regressions"]:
            for metric in summary["regressions"]:
                lines.append(
                    f"- ⚠️ **{metric['name']}**: {metric['delta']:+.4f} ({metric['percent_change']:+.2f}%)"
                )
        else:
            lines.append("- No significant regressions")

        lines.extend(["", "---", ""])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"✓ Generated comparison report: {output_file}")
