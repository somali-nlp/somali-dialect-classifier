"""
Example: Aggregate Metrics Workflow

This script demonstrates how to use aggregation functions in a GitHub
workflow or CI/CD pipeline to calculate overall metrics from multiple
data sources.

Usage:
    python aggregate_metrics_workflow.py <metrics_dir>

Example:
    python aggregate_metrics_workflow.py data/metrics
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from somali_dialect_classifier.utils import (
    calculate_aggregate_summary,
    validate_metric_compatibility,
    aggregate_compatible_metrics,
    AggregationMethod
)


def load_latest_processing_metrics(metrics_dir: Path) -> List[Dict[str, Any]]:
    """
    Load the most recent processing metrics for each source.

    Args:
        metrics_dir: Path to metrics directory

    Returns:
        List of latest processing metrics per source
    """
    # Group by source name
    source_files = {}

    for metrics_file in sorted(metrics_dir.glob("*_processing.json")):
        # Extract source name from filename (e.g., "20251026_100048_bbc-somali_9589c2c5_processing.json")
        parts = metrics_file.stem.split("_")
        if len(parts) >= 4:
            # Source name is parts[2] (bbc-somali, wikipedia-somali, etc.)
            source_name = parts[2]

            # Keep only the latest file for each source (sorted by timestamp)
            if source_name not in source_files or metrics_file > source_files[source_name]:
                source_files[source_name] = metrics_file

    # Load the metrics
    sources = []
    for source_name, metrics_file in sorted(source_files.items()):
        with open(metrics_file) as f:
            data = json.load(f)
            sources.append(data)
            print(f"Loaded: {metrics_file.name}")

    return sources


def calculate_workflow_metrics(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate workflow-level aggregate metrics.

    Args:
        sources: List of source metrics

    Returns:
        Workflow-level aggregate metrics
    """
    # Calculate comprehensive summary
    summary = calculate_aggregate_summary(sources)

    # Add additional workflow-specific metrics
    workflow_metrics = {
        "workflow_summary": {
            "total_sources": summary["sources_count"],
            "total_records": summary["total_records"],
            "total_bytes": summary["total_bytes"],
            "total_bytes_mb": round(summary["total_bytes"] / 1_000_000, 2),
            "pipeline_types": summary["pipeline_types"]
        },
        "quality_metrics": {
            "overall_quality_rate": summary["quality_metrics"]["overall_quality_rate"],
            "overall_quality_percentage": round(
                summary["quality_metrics"]["overall_quality_rate"] * 100, 2
            ),
            "deduplication_rate": summary["quality_metrics"]["deduplication_rate"],
            "deduplication_percentage": round(
                summary["quality_metrics"]["deduplication_rate"] * 100, 2
            )
        },
        "source_contributions": summary["source_contributions"],
        "status": _determine_workflow_status(summary)
    }

    return workflow_metrics


def _determine_workflow_status(summary: Dict[str, Any]) -> str:
    """
    Determine overall workflow status based on aggregate metrics.

    Args:
        summary: Aggregate summary

    Returns:
        Status: "healthy", "degraded", or "unhealthy"
    """
    quality_rate = summary["quality_metrics"]["overall_quality_rate"]

    if quality_rate >= 0.9:
        return "healthy"
    elif quality_rate >= 0.7:
        return "degraded"
    else:
        return "unhealthy"


def generate_workflow_report(workflow_metrics: Dict[str, Any]) -> str:
    """
    Generate markdown report for workflow metrics.

    Args:
        workflow_metrics: Workflow-level metrics

    Returns:
        Markdown report string
    """
    lines = []

    # Header
    lines.extend([
        "# Workflow Aggregate Metrics Report",
        "",
        "## Summary",
        ""
    ])

    # Workflow summary
    ws = workflow_metrics["workflow_summary"]
    qm = workflow_metrics["quality_metrics"]
    status = workflow_metrics["status"]

    status_emoji = {
        "healthy": "✅",
        "degraded": "⚠️",
        "unhealthy": "❌"
    }

    lines.extend([
        f"**Status:** {status_emoji.get(status, '❓')} {status.upper()}",
        "",
        f"- **Total Sources:** {ws['total_sources']}",
        f"- **Total Records:** {ws['total_records']:,}",
        f"- **Total Data:** {ws['total_bytes_mb']:.1f} MB",
        f"- **Pipeline Types:** {', '.join(ws['pipeline_types'])}",
        "",
        "## Quality Metrics",
        "",
        f"- **Overall Quality Rate:** {qm['overall_quality_percentage']:.1f}%",
        f"- **Deduplication Rate:** {qm['deduplication_percentage']:.1f}%",
        "",
        "## Source Contributions",
        "",
        "| Source | Volume | Contribution | Quality |",
        "|--------|--------|--------------|---------|"
    ])

    for source in workflow_metrics["source_contributions"]:
        lines.append(
            f"| {source['source']:30s} | "
            f"{source['volume']:7,} | "
            f"{source['contribution']*100:6.1f}% | "
            f"{source['quality_rate']*100:6.1f}% |"
        )

    lines.extend(["", "---", ""])

    return "\n".join(lines)


def main():
    """Main workflow execution."""
    if len(sys.argv) < 2:
        print("Usage: python aggregate_metrics_workflow.py <metrics_dir>")
        print()
        print("Example:")
        print("  python aggregate_metrics_workflow.py data/metrics")
        sys.exit(1)

    metrics_dir = Path(sys.argv[1])

    if not metrics_dir.exists():
        print(f"Error: Metrics directory not found: {metrics_dir}")
        sys.exit(1)

    print("=" * 80)
    print("WORKFLOW: Aggregate Metrics Calculation")
    print("=" * 80)
    print()

    # Load latest processing metrics
    print("Loading processing metrics...")
    sources = load_latest_processing_metrics(metrics_dir)

    if not sources:
        print("No processing metrics found!")
        sys.exit(1)

    print(f"Loaded {len(sources)} sources")
    print()

    # Calculate workflow metrics
    print("Calculating aggregate metrics...")
    workflow_metrics = calculate_workflow_metrics(sources)

    # Generate report
    report = generate_workflow_report(workflow_metrics)

    # Save report
    output_dir = metrics_dir.parent / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "workflow_aggregate_report.md"

    with open(output_file, 'w') as f:
        f.write(report)

    print(f"Report saved to: {output_file}")
    print()

    # Save JSON metrics
    json_output = metrics_dir / "workflow_aggregate_metrics.json"
    with open(json_output, 'w') as f:
        json.dump(workflow_metrics, f, indent=2, default=str)

    print(f"JSON metrics saved to: {json_output}")
    print()

    # Print summary to console
    print("=" * 80)
    print(report)
    print("=" * 80)

    # Exit with status code based on workflow status
    status = workflow_metrics["status"]
    if status == "healthy":
        sys.exit(0)
    elif status == "degraded":
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Error


if __name__ == "__main__":
    main()
