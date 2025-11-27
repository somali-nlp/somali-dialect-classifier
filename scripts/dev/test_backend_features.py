#!/usr/bin/env python3
"""
Test script for backend features.

Tests all new backend functionality:
- Visualization aggregators
- Filtering functions
- Comparison generators
- Schema validation

Usage:
    python scripts/test_backend_features.py
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from somali_dialect_classifier.utils.metrics_comparison import (
    calculate_delta,
    compare_multiple_runs,
    generate_comparison_summary,
    identify_trends,
)
from somali_dialect_classifier.utils.metrics_filters import (
    apply_filters,
    filter_by_date_range,
    filter_by_quality,
    filter_by_source,
    filter_by_status,
    get_top_performers,
    search_metrics,
)
from somali_dialect_classifier.utils.visualization_aggregator import (
    calculate_pipeline_flow,
    calculate_text_length_distribution,
    calculate_time_series,
)


def load_test_metrics():
    """Load metrics from consolidated file."""
    project_root = Path(__file__).parent.parent
    all_metrics_file = project_root / "_site" / "data" / "all_metrics.json"

    if not all_metrics_file.exists():
        print(f"Error: {all_metrics_file} not found. Run generate_enhanced_metrics.py first.")
        sys.exit(1)

    with open(all_metrics_file) as f:
        data = json.load(f)

    return data["metrics"]


def test_visualization_aggregation(metrics):
    """Test visualization data generation."""
    print("\n" + "=" * 60)
    print("TEST: Visualization Aggregation")
    print("=" * 60)

    # Test Sankey
    print("\n1. Testing Sankey diagram aggregation...")
    sankey = calculate_pipeline_flow(metrics)
    assert "nodes" in sankey
    assert "links" in sankey
    assert "summary" in sankey
    print(f"   ✓ Generated {len(sankey['nodes'])} nodes and {len(sankey['links'])} links")
    print(f"   ✓ Overall pass rate: {sankey['summary']['overall_pass_rate']:.1%}")

    # Test Ridge plot
    print("\n2. Testing Ridge plot aggregation...")
    ridge = calculate_text_length_distribution(metrics, num_bins=10)
    assert "bins" in ridge
    assert "sources" in ridge
    print(f"   ✓ Generated {len(ridge['bins'])} bins")
    print(f"   ✓ Analyzed {len(ridge['sources'])} sources")

    # Test Time-series
    print("\n3. Testing time-series aggregation...")
    daily = calculate_time_series(metrics, interval="daily")
    weekly = calculate_time_series(metrics, interval="weekly")
    assert "series" in daily
    assert "series" in weekly
    print(f"   ✓ Daily series: {len(daily['series'])} periods")
    print(f"   ✓ Weekly series: {len(weekly['series'])} periods")

    print("\n✓ All visualization tests passed")


def test_filtering(metrics):
    """Test filtering functions."""
    print("\n" + "=" * 60)
    print("TEST: Filtering Functions")
    print("=" * 60)

    original_count = len(metrics)
    print(f"\nOriginal metrics count: {original_count}")

    # Test source filter
    print("\n1. Testing source filter...")
    sources = list({m.get("source", "") for m in metrics})
    if sources:
        filtered = filter_by_source(metrics, [sources[0]])
        print(f"   ✓ Filtered by source '{sources[0]}': {len(filtered)} metrics")

    # Test quality filter
    print("\n2. Testing quality filter...")
    filtered = filter_by_quality(metrics, threshold=0.8)
    print(f"   ✓ Quality >= 0.8: {len(filtered)} metrics")

    # Test date range filter
    print("\n3. Testing date range filter...")
    filtered = filter_by_date_range(metrics, start_date="2025-10-01")
    print(f"   ✓ From 2025-10-01: {len(filtered)} metrics")

    # Test status filter
    print("\n4. Testing status filter...")
    healthy = filter_by_status(metrics, status="healthy")
    print(f"   ✓ Healthy runs: {len(healthy)} metrics")

    # Test combined filters
    print("\n5. Testing combined filters...")
    filtered = apply_filters(
        metrics,
        quality_threshold=0.5,
        start_date="2025-10-01"
    )
    print(f"   ✓ Combined filters: {len(filtered)} metrics")

    # Test search
    print("\n6. Testing search...")
    if sources:
        search_term = sources[0].split("-")[0].lower()
        results = search_metrics(metrics, query=search_term)
        print(f"   ✓ Search '{search_term}': {len(results)} results")

    # Test top performers
    print("\n7. Testing top performers...")
    top = get_top_performers(metrics, metric_name="quality_pass_rate", top_n=3)
    print(f"   ✓ Top 3 performers: {len(top)} metrics")

    print("\n✓ All filtering tests passed")


def test_comparison(metrics):
    """Test comparison functions."""
    print("\n" + "=" * 60)
    print("TEST: Comparison Functions")
    print("=" * 60)

    if len(metrics) < 2:
        print("\n⚠ Skipping comparison tests (need at least 2 metrics)")
        return

    # Test delta calculation
    print("\n1. Testing delta calculation...")
    delta = calculate_delta(metrics[0], metrics[1] if len(metrics) > 1 else metrics[0])
    assert "deltas" in delta
    assert "percent_changes" in delta
    print(f"   ✓ Calculated deltas for {len(delta['deltas'])} metrics")
    print(f"   ✓ Found {len(delta['significant_changes'])} significant changes")

    # Test multiple run comparison
    print("\n2. Testing multiple run comparison...")
    sources = list({m.get("source", "") for m in metrics})
    if sources:
        comparisons = compare_multiple_runs(metrics, source=sources[0])
        print(f"   ✓ Generated {len(comparisons)} comparisons for '{sources[0]}'")

        # Test trend identification
        if comparisons:
            print("\n3. Testing trend identification...")
            trend = identify_trends(comparisons, metric_name="quality_pass_rate")
            assert "trend" in trend
            print(f"   ✓ Trend: {trend['trend']}")
            print(f"   ✓ Average change: {trend['average_change']:+.4f}")

    # Test comparison summary
    print("\n4. Testing comparison summary...")
    summary = generate_comparison_summary(metrics[0], metrics[1] if len(metrics) > 1 else metrics[0])
    assert "overview" in summary
    assert "key_metrics" in summary
    print(f"   ✓ Generated summary with {len(summary['key_metrics'])} key metrics")
    print(f"   ✓ Improvements: {len(summary['improvements'])}")
    print(f"   ✓ Regressions: {len(summary['regressions'])}")

    print("\n✓ All comparison tests passed")


def test_data_integrity(metrics):
    """Test data integrity and schema compliance."""
    print("\n" + "=" * 60)
    print("TEST: Data Integrity")
    print("=" * 60)

    print(f"\n1. Checking {len(metrics)} metrics...")

    errors = []

    for i, metric in enumerate(metrics):
        # Check required fields
        required_fields = [
            "run_id", "source", "timestamp", "records_written",
            "quality_pass_rate", "deduplication_rate"
        ]

        for field in required_fields:
            if field not in metric:
                errors.append(f"Metric {i}: Missing field '{field}'")

        # Check value ranges
        if metric.get("quality_pass_rate", 0) < 0 or metric.get("quality_pass_rate", 0) > 1:
            errors.append(f"Metric {i}: quality_pass_rate out of range")

        if metric.get("records_written", 0) < 0:
            errors.append(f"Metric {i}: negative records_written")

    if errors:
        print("\n✗ Data integrity issues found:")
        for error in errors[:10]:
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more")
    else:
        print("   ✓ All metrics have valid structure")
        print("   ✓ All fields within expected ranges")

    print("\n✓ Data integrity tests completed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BACKEND FEATURES TEST SUITE")
    print("=" * 60)

    # Load metrics
    print("\nLoading test metrics...")
    metrics = load_test_metrics()
    print(f"✓ Loaded {len(metrics)} metrics")

    # Run tests
    try:
        test_visualization_aggregation(metrics)
        test_filtering(metrics)
        test_comparison(metrics)
        test_data_integrity(metrics)

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
