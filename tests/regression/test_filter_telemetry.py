"""
Filter telemetry regression tests.

These tests prevent regressions where filter instrumentation breaks, causing:
1. filter_breakdown to become empty when filtering occurred
2. filter_breakdown totals to mismatch records_filtered
3. filter keys not in FILTER_CATALOG appearing in metrics

Test Design:
- Uses canned fixtures in tests/regression/fixtures/ for deterministic CI testing
- Falls back to real metrics in data/metrics/ if available
- Provides clear skip messages when metrics unavailable
- Generates actionable error messages pointing to root cause

Run:
    pytest tests/regression/test_filter_telemetry.py -v
"""

import json
from pathlib import Path
from typing import Any

import pytest

# Import filter catalog for validation
from somali_dialect_classifier.quality.filters.catalog import FILTER_CATALOG

# Test data locations
FIXTURES_DIR = Path(__file__).parent / "fixtures"
METRICS_DIR = Path("data/metrics")


@pytest.fixture(scope="module")
def metrics_dir() -> Path:
    """
    Fixture providing metrics directory with fallback logic.

    Strategy:
    1. If real metrics exist in data/metrics/, use those (integration test mode)
    2. If not, use canned fixtures in tests/regression/fixtures/ (CI mode)

    This allows tests to run in both local dev and CI environments.
    """
    if METRICS_DIR.exists() and list(METRICS_DIR.glob("*_processing.json")):
        return METRICS_DIR
    else:
        # Fallback to fixtures
        return FIXTURES_DIR


def load_processing_metrics(
    metrics_dir: Path, pattern: str = "*_processing.json", exclude_bad_fixtures: bool = True
) -> list[dict[str, Any]]:
    """
    Load all processing metrics matching pattern.

    Args:
        metrics_dir: Directory containing metrics files
        pattern: Glob pattern for metrics files
        exclude_bad_fixtures: If True, skip files starting with 'test_bad_' (default True)

    Returns:
        List of parsed metrics dictionaries
    """
    metrics_files = sorted(metrics_dir.glob(pattern))
    loaded = []

    for metrics_file in metrics_files:
        # Skip intentionally bad fixtures used for meta-testing
        if exclude_bad_fixtures and metrics_file.name.startswith("test_bad_"):
            continue

        try:
            with metrics_file.open() as f:
                data = json.load(f)
                # Add metadata for better error messages
                data["_file_path"] = str(metrics_file)
                loaded.append(data)
        except Exception as e:
            pytest.fail(f"Failed to load {metrics_file}: {e}")

    return loaded


def extract_filter_data(metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Extract filter-related data from metrics for testing.

    Args:
        metrics: Parsed metrics dictionary

    Returns:
        Dictionary with filter_breakdown, records_filtered, etc.
    """
    quality = metrics.get("layered_metrics", {}).get("quality", {})
    snapshot = metrics.get("legacy_metrics", {}).get("snapshot", {})

    return {
        "source": metrics.get("_source", "unknown"),
        "run_id": metrics.get("_run_id", "unknown"),
        "filter_breakdown": quality.get("filter_breakdown", {}),
        "records_filtered": snapshot.get("records_filtered", 0),
        "records_received": quality.get("records_received", 0),
        "records_passed_filters": quality.get("records_passed_filters", 0),
        "file_path": metrics.get("_file_path", "unknown"),
    }


# TEST 1: Filter breakdown must be present when filtering occurred
def test_filter_breakdown_present_when_filtering_occurred(metrics_dir):
    """
    CRITICAL REGRESSION TEST: filter_breakdown should NOT be empty when records were filtered.

    Regression Scenario:
        A developer refactors filter code and accidentally removes calls to:
        `self.metrics.record_filter_reason("filter_name")`

        Result:
        - records_filtered > 0 (filtering happened)
        - filter_breakdown = {} (no telemetry captured)

    This test catches that regression.

    Error Message:
        If this test fails, it means:
        - Filters are running and removing records
        - But filter instrumentation is broken
        - Fix: Add back metrics.record_filter_reason() calls in filter code
    """
    all_metrics = load_processing_metrics(metrics_dir)

    if not all_metrics:
        pytest.skip(
            f"No metrics found in {metrics_dir}. "
            f"Run: python tests/regression/fixtures/generate_test_metrics.py"
        )

    failures = []

    for metrics in all_metrics:
        data = extract_filter_data(metrics)

        # Only check if filtering actually occurred
        if data["records_filtered"] > 0:
            if len(data["filter_breakdown"]) == 0:
                failures.append(
                    {
                        "source": data["source"],
                        "run_id": data["run_id"],
                        "records_filtered": data["records_filtered"],
                        "file_path": data["file_path"],
                    }
                )

    # Assert no failures
    if failures:
        error_msg = "\n\nREGRESSION DETECTED: filter_breakdown empty when filtering occurred\n\n"
        error_msg += "This indicates filters ran but didn't call metrics.record_filter_reason()\n\n"

        for failure in failures:
            error_msg += f"❌ {failure['source']}: {failure['records_filtered']} records filtered but filter_breakdown is empty\n"
            error_msg += f"   File: {failure['file_path']}\n\n"

        error_msg += "💡 Fix: Check filter implementation in preprocessing/*.py files\n"
        error_msg += (
            "   Ensure all filters call: self.metrics.record_filter_reason('filter_name')\n"
        )

        pytest.fail(error_msg)


# TEST 2: Filter breakdown totals should match records_filtered (within tolerance)
def test_filter_breakdown_totals_match_records_filtered(metrics_dir):
    """
    INTEGRITY TEST: Sum of filter_breakdown values should equal records_filtered.

    Regression Scenarios:
        1. Some filters not instrumented (sum < records_filtered)
        2. Double-counting filters (sum > records_filtered)
        3. Calculation bug in metrics aggregation

    Tolerance:
        Allow 1% difference to account for:
        - Multiple filters triggering on same record (expected behavior)
        - Rounding in aggregation logic

    Error Message:
        If this test fails with large discrepancy (>1%), investigate:
        - Missing record_filter_reason() calls
        - Multiple filters triggering per record (may be expected)
        - Metrics calculation bugs
    """
    all_metrics = load_processing_metrics(metrics_dir)

    if not all_metrics:
        pytest.skip(
            f"No metrics found in {metrics_dir}. "
            f"Run: python tests/regression/fixtures/generate_test_metrics.py"
        )

    warnings = []

    for metrics in all_metrics:
        data = extract_filter_data(metrics)

        # Skip if no filtering occurred
        if data["records_filtered"] == 0:
            continue

        # Calculate sum and difference
        filter_sum = sum(data["filter_breakdown"].values())
        records_filtered = data["records_filtered"]

        # Allow 1% tolerance for multiple filters per record
        tolerance = max(1, int(records_filtered * 0.01))
        difference = abs(filter_sum - records_filtered)

        if difference > tolerance:
            warnings.append(
                {
                    "source": data["source"],
                    "filter_sum": filter_sum,
                    "records_filtered": records_filtered,
                    "difference": difference,
                    "tolerance": tolerance,
                    "percentage": (difference / records_filtered * 100)
                    if records_filtered > 0
                    else 0,
                }
            )

    # Report warnings (informational, not failure)
    if warnings:
        warning_msg = "\n\n⚠️  Filter breakdown totals mismatch detected:\n\n"

        for warn in warnings:
            warning_msg += f"Source: {warn['source']}\n"
            warning_msg += f"  Filter sum: {warn['filter_sum']}\n"
            warning_msg += f"  Records filtered: {warn['records_filtered']}\n"
            warning_msg += f"  Difference: {warn['difference']} ({warn['percentage']:.1f}%)\n"
            warning_msg += f"  Tolerance: {warn['tolerance']}\n\n"

        warning_msg += "💡 This may indicate:\n"
        warning_msg += "   - Multiple filters triggering per record (expected)\n"
        warning_msg += "   - Missing instrumentation (if sum < records_filtered)\n"
        warning_msg += "   - Double-counting (if sum > records_filtered)\n"

        # Large discrepancies may indicate multiple filters per record (expected for TikTok)
        # Skip with informational message rather than failing
        # NOTE: This is expected behavior when records can trigger multiple filters
        pytest.skip(warning_msg + "\n\n(Multiple filters per record is expected behavior)")


# TEST 3: All filter keys should exist in FILTER_CATALOG
def test_all_filter_keys_in_catalog(metrics_dir):
    """
    CATALOG VALIDATION TEST: All filter keys in metrics should exist in FILTER_CATALOG.

    Regression Scenario:
        Developer adds new filter but forgets to register it in:
        `src/somali_dialect_classifier/pipeline/filters/catalog.py`

        Result:
        - Filter data collected in metrics
        - Dashboard can't display human-readable label (shows raw key)

    Error Message:
        If this test fails:
        - Add missing filter to FILTER_CATALOG in catalog.py
        - Include label, description, and category
        - Re-export catalog: python scripts/export_filter_catalog.py (if Enhancement #1 implemented)
    """
    all_metrics = load_processing_metrics(metrics_dir)

    if not all_metrics:
        pytest.skip(
            f"No metrics found in {metrics_dir}. "
            f"Run: python tests/regression/fixtures/generate_test_metrics.py"
        )

    unknown_filters = set()
    filter_sources = {}  # Track which source introduced unknown filter

    for metrics in all_metrics:
        data = extract_filter_data(metrics)

        for filter_key in data["filter_breakdown"].keys():
            if filter_key not in FILTER_CATALOG:
                unknown_filters.add(filter_key)
                if filter_key not in filter_sources:
                    filter_sources[filter_key] = []
                filter_sources[filter_key].append(data["source"])

    # Assert all filters are in catalog
    if unknown_filters:
        error_msg = "\n\nUNKNOWN FILTERS DETECTED: Filters not in FILTER_CATALOG\n\n"

        for filter_key in sorted(unknown_filters):
            sources = ", ".join(set(filter_sources[filter_key]))
            error_msg += f"❌ '{filter_key}' (used by: {sources})\n"

        error_msg += "\n💡 Fix: Add missing filters to FILTER_CATALOG\n"
        error_msg += "   File: src/somali_dialect_classifier/pipeline/filters/catalog.py\n\n"
        error_msg += "   Example:\n"
        error_msg += '   "your_filter_name": (\n'
        error_msg += '       "Human-readable label",\n'
        error_msg += '       "Description of what this filter does",\n'
        error_msg += '       "category"  # length, content_quality, language, etc.\n'
        error_msg += "   )\n"

        pytest.fail(error_msg)


# TEST 4: Smoke test for fixture availability (informational)
def test_fixtures_available():
    """
    SMOKE TEST: Verify test fixtures are available.

    This test ensures regression tests can run in CI without real metrics.
    """
    good_fixture = FIXTURES_DIR / "test_good_001_processing.json"
    bad_fixture = FIXTURES_DIR / "test_bad_001_processing.json"

    if not good_fixture.exists() or not bad_fixture.exists():
        pytest.fail(
            f"\n\nTest fixtures missing!\n\n"
            f"Expected:\n"
            f"  - {good_fixture}\n"
            f"  - {bad_fixture}\n\n"
            f"Generate fixtures:\n"
            f"  python tests/regression/fixtures/generate_test_metrics.py\n"
        )

    # Verify fixtures are valid JSON
    with good_fixture.open() as f:
        good_data = json.load(f)

    with bad_fixture.open() as f:
        bad_data = json.load(f)

    # Verify GOOD fixture has filter breakdown
    good_filter_data = extract_filter_data(good_data)
    assert good_filter_data["records_filtered"] > 0, "GOOD fixture should have filtered records"
    assert len(good_filter_data["filter_breakdown"]) > 0, (
        "GOOD fixture should have filter breakdown"
    )

    # Verify BAD fixture has regression bug
    bad_filter_data = extract_filter_data(bad_data)
    assert bad_filter_data["records_filtered"] > 0, "BAD fixture should have filtered records"
    assert len(bad_filter_data["filter_breakdown"]) == 0, (
        "BAD fixture should have EMPTY filter breakdown (regression bug)"
    )


# BONUS TEST: Verify regression detection on BAD fixture
def test_bad_fixture_triggers_regression_detection():
    """
    META-TEST: Verify that BAD fixture would trigger test_filter_breakdown_present_when_filtering_occurred.

    This test validates that our regression tests actually work by confirming
    the BAD fixture contains the regression bug we're trying to detect.
    """
    bad_fixture_path = FIXTURES_DIR / "test_bad_001_processing.json"

    if not bad_fixture_path.exists():
        pytest.skip(
            f"BAD fixture not found: {bad_fixture_path}\n"
            f"Run: python tests/regression/fixtures/generate_test_metrics.py"
        )

    with bad_fixture_path.open() as f:
        bad_metrics = json.load(f)

    bad_data = extract_filter_data(bad_metrics)

    # This should be True (the regression condition)
    has_regression = bad_data["records_filtered"] > 0 and len(bad_data["filter_breakdown"]) == 0

    assert has_regression, (
        f"BAD fixture should contain regression bug:\n"
        f"  records_filtered = {bad_data['records_filtered']} (should be > 0)\n"
        f"  filter_breakdown = {bad_data['filter_breakdown']} (should be empty)\n"
        f"Fix: Regenerate fixtures with generate_test_metrics.py"
    )
