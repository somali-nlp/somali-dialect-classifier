"""
Phase 2: Volume-Weighted Aggregation Demo

This script demonstrates how to use the aggregation module to calculate
meaningful cross-source metrics for the Somali NLP project.

It shows:
1. Loading real metrics from processing.json files
2. Volume-weighted vs simple average comparison
3. When to use harmonic mean
4. Compatibility validation
5. Real-world aggregation with BBC + Wikipedia + HuggingFace
"""

import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from somali_dialect_classifier.utils.aggregation import (
    calculate_volume_weighted_quality,
    calculate_weighted_harmonic_mean,
    aggregate_compatible_metrics,
    validate_metric_compatibility,
    calculate_aggregate_summary,
    AggregationMethod
)


def print_section(title: str):
    """Print a section header."""
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    print()


def load_processing_metrics(metrics_dir: Path, pattern: str = "*_processing.json"):
    """
    Load all processing metrics from a directory.

    Args:
        metrics_dir: Path to metrics directory
        pattern: Glob pattern for processing files

    Returns:
        List of metrics dicts
    """
    sources = []

    for metrics_file in sorted(metrics_dir.glob(pattern)):
        with open(metrics_file) as f:
            data = json.load(f)
            sources.append(data)

    return sources


def demo_simple_vs_weighted():
    """Demonstrate difference between simple and volume-weighted average."""
    print_section("1. Simple Average vs Volume-Weighted Average")

    # Scenario: BBC has 150 records at 84.7%, Wikipedia has 10,000 at 100%
    sources = [
        {
            "name": "BBC (small)",
            "records_written": 150,
            "layered_metrics": {"quality": {"quality_pass_rate": 0.847}}
        },
        {
            "name": "Wikipedia (large)",
            "records_written": 10000,
            "layered_metrics": {"quality": {"quality_pass_rate": 1.0}}
        }
    ]

    # Simple average (WRONG - treats all sources equally)
    simple_avg = (0.847 + 1.0) / 2
    print(f"Simple Average (WRONG):        {simple_avg:.1%}")
    print(f"  - Treats BBC (150) and Wikipedia (10,000) equally")
    print(f"  - Doesn't represent actual dataset quality")
    print()

    # Volume-weighted average (CORRECT)
    result = calculate_volume_weighted_quality(sources)
    weighted_avg = result["overall_quality_rate"]
    print(f"Volume-Weighted Average (CORRECT): {weighted_avg:.1%}")
    print(f"  - Total records: {result['total_records']:,}")
    print(f"  - BBC contributes: {result['source_breakdown'][0]['contribution']:.1%}")
    print(f"  - Wikipedia contributes: {result['source_breakdown'][1]['contribution']:.1%}")
    print()

    print(f"Difference: {abs(weighted_avg - simple_avg):.1%}")
    print("The weighted average better represents the overall dataset quality.")


def demo_harmonic_mean():
    """Demonstrate when harmonic mean is useful."""
    print_section("2. Harmonic Mean - Penalizing Poor Performers")

    # Scenario: One source has poor quality, others are good
    sources = [
        {
            "name": "Poor Source",
            "records_written": 100,
            "layered_metrics": {"quality": {"quality_pass_rate": 0.1}}  # 10%
        },
        {
            "name": "Good Source 1",
            "records_written": 100,
            "layered_metrics": {"quality": {"quality_pass_rate": 1.0}}  # 100%
        },
        {
            "name": "Good Source 2",
            "records_written": 100,
            "layered_metrics": {"quality": {"quality_pass_rate": 1.0}}  # 100%
        }
    ]

    # Arithmetic mean
    arithmetic = (0.1 + 1.0 + 1.0) / 3
    print(f"Arithmetic Mean:  {arithmetic:.1%}")
    print("  - Averages the three values equally")
    print()

    # Harmonic mean
    harmonic = aggregate_compatible_metrics(
        sources,
        "quality_pass_rate",
        method=AggregationMethod.HARMONIC_MEAN
    )
    print(f"Harmonic Mean:    {harmonic:.1%}")
    print("  - Penalizes the poor performer more heavily")
    print("  - Use when one bad source should pull down the overall metric")
    print()

    # Volume-weighted arithmetic
    weighted = calculate_volume_weighted_quality(sources)["overall_quality_rate"]
    print(f"Volume-Weighted:  {weighted:.1%}")
    print("  - All sources have equal volume, so same as arithmetic")
    print()

    print("WHEN TO USE:")
    print("  - Harmonic mean: When quality issues in ANY source are critical")
    print("  - Weighted arithmetic: When representing overall dataset (default)")


def demo_compatibility_validation():
    """Demonstrate metric compatibility validation."""
    print_section("3. Metric Compatibility Validation")

    sources = [
        {
            "snapshot": {"pipeline_type": "web_scraping", "source": "BBC"},
            "statistics": {"http_request_success_rate": 0.107}
        },
        {
            "snapshot": {"pipeline_type": "file_processing", "source": "Wikipedia"},
            "statistics": {"file_extraction_success_rate": 1.0}
        }
    ]

    print("Sources:")
    print("  - BBC (web_scraping): http_request_success_rate = 10.7%")
    print("  - Wikipedia (file_processing): file_extraction_success_rate = 100%")
    print()

    # Try to aggregate incompatible metrics
    print("Compatibility Checks:")
    print()

    test_metrics = [
        ("quality_pass_rate", True),
        ("deduplication_rate", True),
        ("http_request_success_rate", False),
        ("file_extraction_success_rate", False)
    ]

    for metric, should_be_compatible in test_metrics:
        is_compat, reason = validate_metric_compatibility(sources, metric)
        status = "✅ Compatible" if is_compat else "❌ Incompatible"
        print(f"{metric:35s} {status}")
        if reason:
            print(f"  └─ {reason[:70]}...")

    print()
    print("KEY TAKEAWAY:")
    print("  - ALWAYS validate compatibility before aggregating!")
    print("  - Phase 0 bug: averaged http_request_success_rate across pipeline types")
    print("  - Phase 2 fix: only aggregate semantically compatible metrics")


def demo_real_data():
    """Demonstrate aggregation with real data."""
    print_section("4. Real Data Aggregation (BBC + Wikipedia + HuggingFace)")

    # Real data from 20251026_100048 run
    sources = [
        {
            "snapshot": {
                "source": "BBC-Somali",
                "pipeline_type": "web_scraping",
                "records_written": 20,
                "bytes_downloaded": 99176
            },
            "statistics": {
                "quality_pass_rate": 1.0,
                "deduplication_rate": 0.0
            }
        },
        {
            "snapshot": {
                "source": "Wikipedia-Somali",
                "pipeline_type": "file_processing",
                "records_written": 9623,
                "bytes_downloaded": 14280506
            },
            "statistics": {
                "quality_pass_rate": 0.7075735294117646,
                "deduplication_rate": 0.0
            }
        },
        {
            "snapshot": {
                "source": "HuggingFace-Somali_c4-so",
                "pipeline_type": "stream_processing",
                "records_written": 19,
                "bytes_downloaded": 0
            },
            "statistics": {
                "quality_pass_rate": 0.95,
                "deduplication_rate": 0.0
            }
        }
    ]

    # Calculate aggregate summary
    summary = calculate_aggregate_summary(sources)

    print(f"Total Records:    {summary['total_records']:,}")
    print(f"Total Bytes:      {summary['total_bytes']:,} ({summary['total_bytes'] / 1_000_000:.1f} MB)")
    print(f"Sources:          {summary['sources_count']}")
    print(f"Pipeline Types:   {', '.join(summary['pipeline_types'])}")
    print()

    print("Quality Metrics:")
    print(f"  Overall Quality:     {summary['quality_metrics']['overall_quality_rate']:.1%}")
    print(f"  Deduplication Rate:  {summary['quality_metrics']['deduplication_rate']:.1%}")
    print()

    print("Source Contributions:")
    for source in summary['source_contributions']:
        print(f"  {source['source']:30s}")
        print(f"    Volume:       {source['volume']:6,} records ({source['contribution']*100:5.1f}%)")
        print(f"    Quality:      {source['quality_rate']*100:5.1f}%")
        print()

    print("INSIGHTS:")
    print(f"  - Wikipedia dominates with {summary['source_contributions'][1]['contribution']:.1%} of data")
    print(f"  - Overall quality ({summary['quality_metrics']['overall_quality_rate']:.1%}) is close to Wikipedia's")
    print(f"  - This shows volume-weighting works correctly!")


def demo_aggregation_methods():
    """Demonstrate different aggregation methods."""
    print_section("5. Aggregation Methods Comparison")

    sources = [
        {"name": "Source A", "records_written": 100, "layered_metrics": {"quality": {"quality_pass_rate": 0.8}}},
        {"name": "Source B", "records_written": 200, "layered_metrics": {"quality": {"quality_pass_rate": 0.9}}},
        {"name": "Source C", "records_written": 300, "layered_metrics": {"quality": {"quality_pass_rate": 0.7}}}
    ]

    print("Sources:")
    for source in sources:
        vol = source["records_written"]
        quality = source["layered_metrics"]["quality"]["quality_pass_rate"]
        print(f"  {source['name']}: {vol:3d} records, {quality:.1%} quality")
    print()

    print("Aggregation Methods:")

    # Volume-weighted mean
    vw_mean = aggregate_compatible_metrics(
        sources, "quality_pass_rate", AggregationMethod.VOLUME_WEIGHTED_MEAN
    )
    print(f"  Volume-Weighted Mean:   {vw_mean:.1%}")
    print(f"    = (100*0.8 + 200*0.9 + 300*0.7) / 600")
    print()

    # Harmonic mean
    harmonic = aggregate_compatible_metrics(
        sources, "quality_pass_rate", AggregationMethod.HARMONIC_MEAN
    )
    print(f"  Harmonic Mean:          {harmonic:.1%}")
    print(f"    = 3 / (1/0.8 + 1/0.9 + 1/0.7)")
    print()

    # MIN
    min_val = aggregate_compatible_metrics(
        sources, "quality_pass_rate", AggregationMethod.MIN
    )
    print(f"  MIN:                    {min_val:.1%}")
    print()

    # MAX
    max_val = aggregate_compatible_metrics(
        sources, "quality_pass_rate", AggregationMethod.MAX
    )
    print(f"  MAX:                    {max_val:.1%}")
    print()

    # SUM
    total_records = aggregate_compatible_metrics(
        sources, "records_written", AggregationMethod.SUM
    )
    print(f"  SUM (records):          {total_records:,}")
    print()

    print("WHEN TO USE EACH:")
    print("  - VOLUME_WEIGHTED_MEAN: Default, most representative of overall dataset")
    print("  - HARMONIC_MEAN: When poor performers should heavily impact aggregate")
    print("  - MIN: Worst-case scenario, conservative estimate")
    print("  - MAX: Best-case scenario, optimistic estimate")
    print("  - SUM: Total counts (records, bytes, etc.)")


def demo_load_from_files():
    """Demonstrate loading and aggregating from actual files."""
    print_section("6. Loading from Processing.json Files")

    # Check if data/metrics exists
    metrics_dir = Path(__file__).parent.parent / "data" / "metrics"

    if not metrics_dir.exists():
        print(f"Metrics directory not found: {metrics_dir}")
        print("Run the data collection pipeline first to generate metrics.")
        return

    # Load all processing.json files
    sources = load_processing_metrics(metrics_dir)

    if not sources:
        print("No processing metrics found.")
        print(f"Directory: {metrics_dir}")
        return

    print(f"Loaded {len(sources)} processing metrics from: {metrics_dir}")
    print()

    for source in sources:
        snapshot = source["snapshot"]
        stats = source["statistics"]
        print(f"  {snapshot['source']:30s}")
        print(f"    Records:     {snapshot['records_written']:6,}")
        print(f"    Quality:     {stats.get('quality_pass_rate', 0)*100:5.1f}%")
        print(f"    Pipeline:    {snapshot['pipeline_type']}")
        print()

    # Aggregate
    summary = calculate_aggregate_summary(sources)

    print("Aggregate Summary:")
    print(f"  Total Records:       {summary['total_records']:,}")
    print(f"  Total Bytes:         {summary['total_bytes']:,}")
    print(f"  Overall Quality:     {summary['quality_metrics']['overall_quality_rate']:.1%}")
    print(f"  Deduplication Rate:  {summary['quality_metrics']['deduplication_rate']:.1%}")


def main():
    """Run all demos."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                               ║")
    print("║                   PHASE 2: VOLUME-WEIGHTED AGGREGATION DEMO                  ║")
    print("║                                                                               ║")
    print("║  This demo shows how to safely aggregate metrics across data sources while   ║")
    print("║  avoiding the mistakes from Phase 0 (simple averaging of incompatible        ║")
    print("║  metrics).                                                                    ║")
    print("║                                                                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")

    demo_simple_vs_weighted()
    demo_harmonic_mean()
    demo_compatibility_validation()
    demo_real_data()
    demo_aggregation_methods()
    demo_load_from_files()

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("KEY PRINCIPLES:")
    print("  1. ✅ Only aggregate COMPATIBLE metrics")
    print("  2. ✅ Weight by data volume (records_written)")
    print("  3. ✅ Provide breakdown showing contribution")
    print("  4. ❌ NEVER aggregate incompatible metrics (validate first!)")
    print("  5. ✅ Support multiple aggregation methods for different use cases")
    print()
    print("NEXT STEPS:")
    print("  - Use calculate_aggregate_summary() for comprehensive analysis")
    print("  - Always validate compatibility with validate_metric_compatibility()")
    print("  - Consider harmonic mean when poor performers should heavily impact aggregate")
    print()


if __name__ == "__main__":
    main()
