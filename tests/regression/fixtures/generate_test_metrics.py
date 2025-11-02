#!/usr/bin/env python3
"""
Generate deterministic test fixtures for filter telemetry regression tests.

This script creates two canned metrics fixtures for CI testing:
1. GOOD fixture: Has populated filter_breakdown with filtering occurred
2. BAD fixture: Has empty filter_breakdown but records_filtered > 0 (REGRESSION BUG)

These fixtures ensure regression tests can run deterministically in CI without
requiring real pipeline execution.

Usage:
    python tests/regression/fixtures/generate_test_metrics.py

Output:
    tests/regression/fixtures/test_good_001_processing.json
    tests/regression/fixtures/test_bad_001_processing.json
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any


def create_good_fixture() -> Dict[str, Any]:
    """
    Create a GOOD metrics fixture with populated filter_breakdown.

    This fixture represents a healthy pipeline run where:
    - 200 records were filtered
    - filter_breakdown contains 200 total filters across 3 filter types
    - All filter keys exist in FILTER_CATALOG
    """
    return {
        "_schema_version": "3.0",
        "_pipeline_type": "test_fixture",
        "_timestamp": "2025-11-02T10:00:00.000000+00:00",
        "_run_id": "test_good_001",
        "_source": "Test-Source-Good",
        "layered_metrics": {
            "connectivity": {
                "connection_attempted": True,
                "connection_successful": True,
                "connection_duration_ms": 100.0,
                "connection_error": None
            },
            "extraction": {
                "stream_opened": True,
                "total_records_available": 500,
                "batches_attempted": 5,
                "batches_completed": 5,
                "batches_failed": 0,
                "records_fetched": 500
            },
            "quality": {
                "records_received": 500,
                "records_passed_filters": 300,
                "filter_breakdown": {
                    "min_length_filter": 120,
                    "emoji_only_comment": 50,
                    "text_too_short_after_cleanup": 30
                }
            },
            "volume": {
                "records_written": 300,
                "bytes_downloaded": 50000,
                "total_chars": 15000
            }
        },
        "legacy_metrics": {
            "snapshot": {
                "timestamp": "2025-11-02T10:00:00.000000+00:00",
                "run_id": "test_good_001",
                "source": "Test-Source-Good",
                "duration_seconds": 120.5,
                "pipeline_type": "test_fixture",
                "urls_discovered": 100,
                "urls_fetched": 100,
                "urls_processed": 100,
                "urls_failed": 0,
                "urls_skipped": 0,
                "urls_deduplicated": 0,
                "files_discovered": 0,
                "files_processed": 0,
                "records_extracted": 0,
                "datasets_opened": 0,
                "records_fetched": 500,
                "records_processed": 300,
                "batches_completed": 5,
                "bytes_downloaded": 50000,
                "records_written": 300,
                "records_filtered": 200,
                "http_status_codes": {},
                "filter_reasons": {
                    "min_length_filter": 120,
                    "emoji_only_comment": 50,
                    "text_too_short_after_cleanup": 30
                },
                "error_types": {},
                "fetch_durations_ms": [100.0, 105.0, 98.0, 102.0, 99.0],
                "process_durations_ms": [10.0, 12.0, 11.0, 10.5, 11.5],
                "text_lengths": [75, 82, 90, 65, 78, 88, 95, 70, 85, 92],
                "unique_hashes": 300,
                "duplicate_hashes": 0,
                "near_duplicates": 0
            },
            "statistics": {
                "http_request_success_rate": 1.0,
                "content_extraction_success_rate": 1.0,
                "http_request_failure_rate": 0.0,
                "quality_pass_rate": 0.6,
                "deduplication_rate": 0.0,
                "fetch_duration_stats": {
                    "min": 98.0,
                    "max": 105.0,
                    "mean": 100.8,
                    "median": 100.0,
                    "p95": 104.0,
                    "p99": 105.0
                },
                "text_length_stats": {
                    "min": 65,
                    "max": 95,
                    "mean": 82.0,
                    "median": 82.0,
                    "total_chars": 15000
                },
                "throughput": {
                    "urls_per_second": 0.83,
                    "bytes_per_second": 414.9,
                    "records_per_minute": 149.5
                }
            }
        }
    }


def create_bad_fixture() -> Dict[str, Any]:
    """
    Create a BAD metrics fixture with EMPTY filter_breakdown (REGRESSION BUG).

    This fixture represents a regression where:
    - 100 records were filtered (records_filtered = 100)
    - filter_breakdown is EMPTY {} (instrumentation broken)
    - This should trigger test failure: "filter_breakdown empty when filtering occurred"
    """
    return {
        "_schema_version": "3.0",
        "_pipeline_type": "test_fixture",
        "_timestamp": "2025-11-02T10:05:00.000000+00:00",
        "_run_id": "test_bad_001",
        "_source": "Test-Source-Bad",
        "layered_metrics": {
            "connectivity": {
                "connection_attempted": True,
                "connection_successful": True,
                "connection_duration_ms": 100.0,
                "connection_error": None
            },
            "extraction": {
                "stream_opened": True,
                "total_records_available": 400,
                "batches_attempted": 4,
                "batches_completed": 4,
                "batches_failed": 0,
                "records_fetched": 400
            },
            "quality": {
                "records_received": 400,
                "records_passed_filters": 300,
                "filter_breakdown": {}  # BUG: Empty despite filtering
            },
            "volume": {
                "records_written": 300,
                "bytes_downloaded": 40000,
                "total_chars": 12000
            }
        },
        "legacy_metrics": {
            "snapshot": {
                "timestamp": "2025-11-02T10:05:00.000000+00:00",
                "run_id": "test_bad_001",
                "source": "Test-Source-Bad",
                "duration_seconds": 115.3,
                "pipeline_type": "test_fixture",
                "urls_discovered": 80,
                "urls_fetched": 80,
                "urls_processed": 80,
                "urls_failed": 0,
                "urls_skipped": 0,
                "urls_deduplicated": 0,
                "files_discovered": 0,
                "files_processed": 0,
                "records_extracted": 0,
                "datasets_opened": 0,
                "records_fetched": 400,
                "records_processed": 300,
                "batches_completed": 4,
                "bytes_downloaded": 40000,
                "records_written": 300,
                "records_filtered": 100,  # BUG: Filtered records but no breakdown
                "http_status_codes": {},
                "filter_reasons": {},  # BUG: Empty breakdown
                "error_types": {},
                "fetch_durations_ms": [95.0, 100.0, 98.0, 97.0],
                "process_durations_ms": [9.0, 11.0, 10.0, 10.5],
                "text_lengths": [70, 75, 80, 85, 90, 95, 100, 105],
                "unique_hashes": 300,
                "duplicate_hashes": 0,
                "near_duplicates": 0
            },
            "statistics": {
                "http_request_success_rate": 1.0,
                "content_extraction_success_rate": 1.0,
                "http_request_failure_rate": 0.0,
                "quality_pass_rate": 0.75,
                "deduplication_rate": 0.0,
                "fetch_duration_stats": {
                    "min": 95.0,
                    "max": 100.0,
                    "mean": 97.5,
                    "median": 97.5,
                    "p95": 99.5,
                    "p99": 100.0
                },
                "text_length_stats": {
                    "min": 70,
                    "max": 105,
                    "mean": 87.5,
                    "median": 87.5,
                    "total_chars": 12000
                },
                "throughput": {
                    "urls_per_second": 0.69,
                    "bytes_per_second": 346.9,
                    "records_per_minute": 156.2
                }
            }
        }
    }


def main():
    """Generate test fixtures and save to files."""
    print("Generating test fixtures for filter telemetry regression tests...")

    # Create fixtures directory
    fixtures_dir = Path(__file__).parent
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Generate GOOD fixture
    good_fixture = create_good_fixture()
    good_path = fixtures_dir / "test_good_001_processing.json"
    with good_path.open("w", encoding="utf-8") as f:
        json.dump(good_fixture, f, indent=2, ensure_ascii=False)

    print(f"✅ Created GOOD fixture: {good_path}")
    print(f"   - Records filtered: {good_fixture['legacy_metrics']['snapshot']['records_filtered']}")
    print(f"   - Filter breakdown entries: {len(good_fixture['layered_metrics']['quality']['filter_breakdown'])}")

    # Generate BAD fixture
    bad_fixture = create_bad_fixture()
    bad_path = fixtures_dir / "test_bad_001_processing.json"
    with bad_path.open("w", encoding="utf-8") as f:
        json.dump(bad_fixture, f, indent=2, ensure_ascii=False)

    print(f"\n⚠️  Created BAD fixture (regression bug): {bad_path}")
    print(f"   - Records filtered: {bad_fixture['legacy_metrics']['snapshot']['records_filtered']}")
    print(f"   - Filter breakdown entries: {len(bad_fixture['layered_metrics']['quality']['filter_breakdown'])} (EMPTY - BUG)")

    print("\n📋 Fixture Summary:")
    print(f"   GOOD: {good_fixture['layered_metrics']['quality']['records_received']} received → "
          f"{good_fixture['layered_metrics']['quality']['records_passed_filters']} passed "
          f"({good_fixture['legacy_metrics']['snapshot']['records_filtered']} filtered)")
    print(f"   BAD:  {bad_fixture['layered_metrics']['quality']['records_received']} received → "
          f"{bad_fixture['layered_metrics']['quality']['records_passed_filters']} passed "
          f"({bad_fixture['legacy_metrics']['snapshot']['records_filtered']} filtered BUT no breakdown)")

    print("\n🔍 Next Steps:")
    print("   1. Run regression tests: pytest tests/regression/test_filter_telemetry.py -v")
    print("   2. BAD fixture should trigger test failure")
    print("   3. Check error message: 'Test-Source-Bad: 100 records filtered but filter_breakdown is empty'")


if __name__ == "__main__":
    main()
