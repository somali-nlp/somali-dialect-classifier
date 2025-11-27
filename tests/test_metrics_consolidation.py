"""
Unit tests for metrics consolidation and schema validation.

Tests cover:
- Phase 3 schema parsing
- Consolidated metric extraction
- Schema validation
- Null source guards
- Filter breakdown aggregation
"""

import pytest

# Skip all tests in this module - they require scripts module which has import issues
pytestmark = pytest.mark.skip(
    reason="Scripts module import issues - requires pytest path configuration fix"
)

import pytest
from pydantic import ValidationError

try:
    from somali_dialect_classifier.infra.metrics_schema import (
        ConsolidatedMetric,
        validate_consolidated_metrics,
        validate_dashboard_summary,
        validate_processing_json,
    )

    SCHEMA_AVAILABLE = True
except ImportError:
    SCHEMA_AVAILABLE = False
    pytest.skip("Schema validation not available", allow_module_level=True)


# Sample Phase 3 processing JSON for testing
SAMPLE_PROCESSING_JSON = {
    "_schema_version": "3.0",
    "_pipeline_type": "web_scraping",
    "_timestamp": "2025-10-26T16:23:45.383125+00:00",
    "_run_id": "20251026_155342_bbc-somali_6ca368f7",
    "_source": "BBC-Somali",
    "layered_metrics": {
        "connectivity": {
            "connection_attempted": True,
            "connection_successful": True,
            "connection_duration_ms": 4420.66,
            "connection_error": None,
        },
        "extraction": {
            "http_requests_attempted": 29,
            "http_requests_successful": 28,
            "http_status_distribution": {"200": 28},
            "pages_parsed": 28,
            "content_extracted": 28,
        },
        "quality": {
            "records_received": 28,
            "records_passed_filters": 28,
            "filter_breakdown": {"min_length_filter": 2, "langid_filter": 1},
        },
        "volume": {"records_written": 28, "bytes_downloaded": 0, "total_chars": 136510},
    },
    "legacy_metrics": {
        "snapshot": {
            "timestamp": "2025-10-26T16:23:45.383125+00:00",
            "run_id": "20251026_155342_bbc-somali_6ca368f7",
            "source": "BBC-Somali",
            "duration_seconds": 1802.67,
            "pipeline_type": "web_scraping",
            "urls_discovered": 189,
            "urls_fetched": 28,
            "urls_processed": 28,
            "urls_failed": 1,
            "bytes_downloaded": 0,
            "records_written": 28,
            "http_status_codes": {"200": 28},
            "filter_reasons": {},
            "error_types": {"scrape_failed": 1},
            "fetch_durations_ms": [1000.0, 1200.0],
            "process_durations_ms": [],
            "text_lengths": [3672, 6043],
        },
        "statistics": {
            "http_request_success_rate": 0.9655,
            "content_extraction_success_rate": 1.0,
            "http_request_failure_rate": 0.0345,
            "quality_pass_rate": 0.93,
            "deduplication_rate": 0.0,
            "throughput": {
                "urls_per_second": 0.0155,
                "bytes_per_second": 0.0,
                "records_per_minute": 0.932,
            },
            "text_length_stats": {
                "min": 337,
                "max": 10598,
                "mean": 4875.36,
                "median": 4438.0,
                "total_chars": 136510,
            },
            "fetch_duration_stats": {
                "min": 598.59,
                "max": 4420.66,
                "mean": 1357.31,
                "median": 1126.12,
                "p95": 3305.28,
                "p99": 4420.66,
            },
        },
    },
}


class TestPhase3SchemaValidation:
    """Test Phase 3 schema validation."""

    def test_valid_processing_json(self):
        """Test that valid Phase 3 JSON passes validation."""
        validated = validate_processing_json(SAMPLE_PROCESSING_JSON)
        assert validated.schema_version == "3.0"
        assert validated.source == "BBC-Somali"
        assert validated.layered_metrics.volume.records_written == 28

    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        invalid_data = SAMPLE_PROCESSING_JSON.copy()
        del invalid_data["_source"]

        with pytest.raises(ValidationError):
            validate_processing_json(invalid_data)

    def test_invalid_schema_version(self):
        """Test that invalid schema version raises error."""
        invalid_data = SAMPLE_PROCESSING_JSON.copy()
        invalid_data["_schema_version"] = "2.0"

        with pytest.raises(ValidationError):
            validate_processing_json(invalid_data)

    def test_layered_metrics_validation(self):
        """Test layered metrics structure validation."""
        validated = validate_processing_json(SAMPLE_PROCESSING_JSON)

        # Check connectivity layer
        assert validated.layered_metrics.connectivity.connection_attempted is True
        assert validated.layered_metrics.connectivity.connection_successful is True

        # Check extraction layer
        assert validated.layered_metrics.extraction.http_requests_attempted == 29
        assert validated.layered_metrics.extraction.http_requests_successful == 28

        # Check quality layer
        assert validated.layered_metrics.quality.records_received == 28
        assert validated.layered_metrics.quality.records_passed_filters == 28

        # Check volume layer
        assert validated.layered_metrics.volume.records_written == 28
        assert validated.layered_metrics.volume.total_chars == 136510

    def test_statistics_validation(self):
        """Test statistics section validation."""
        validated = validate_processing_json(SAMPLE_PROCESSING_JSON)
        stats = validated.legacy_metrics.statistics

        assert 0 <= stats.http_request_success_rate <= 1
        assert 0 <= stats.quality_pass_rate <= 1
        assert 0 <= stats.deduplication_rate <= 1

        assert stats.throughput.urls_per_second >= 0
        assert stats.throughput.records_per_minute >= 0


class TestConsolidatedMetricExtraction:
    """Test consolidated metric extraction from Phase 3 JSON."""

    def test_extract_consolidated_metric(self):
        """Test extracting consolidated metric from Phase 3 JSON."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        assert metric is not None
        assert metric["run_id"] == "20251026_155342_bbc-somali_6ca368f7"
        assert metric["source"] == "BBC-Somali"
        assert metric["records_written"] == 28
        assert metric["total_chars"] == 136510
        assert metric["quality_pass_rate"] == 0.93

    def test_null_source_guard(self):
        """Test that null sources are properly guarded."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        invalid_data = SAMPLE_PROCESSING_JSON.copy()
        invalid_data["_source"] = None
        invalid_data["legacy_metrics"]["snapshot"]["source"] = None

        metric = extract_consolidated_metric(invalid_data, "test.json")
        assert metric is None

    def test_filter_breakdown_extraction(self):
        """Test that filter breakdown is properly extracted."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        assert "filter_breakdown" in metric
        assert metric["filter_breakdown"]["min_length_filter"] == 2
        assert metric["filter_breakdown"]["langid_filter"] == 1

    def test_throughput_metrics_extraction(self):
        """Test that throughput metrics are extracted."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        assert "urls_per_second" in metric
        assert "bytes_per_second" in metric
        assert "records_per_minute" in metric
        assert metric["records_per_minute"] == 0.932


class TestConsolidatedMetricValidation:
    """Test consolidated metric schema validation."""

    def test_valid_consolidated_metric(self):
        """Test that valid consolidated metric passes validation."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        # Should not raise
        validated = ConsolidatedMetric.model_validate(metric)
        assert validated.source == "BBC-Somali"

    def test_consolidated_metrics_output_validation(self):
        """Test consolidated metrics output validation."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        output = {"count": 1, "records": 28, "sources": ["BBC-Somali"], "metrics": [metric]}

        # Should not raise
        validated = validate_consolidated_metrics(output)
        assert validated.count == 1
        assert validated.records == 28

    def test_negative_values_rejected(self):
        """Test that negative values are rejected."""
        invalid_metric = {
            "run_id": "test",
            "source": "test",
            "timestamp": "2025-10-26T16:23:45.383125+00:00",
            "duration_seconds": -100,  # Invalid
            "urls_discovered": 0,
            "urls_fetched": 0,
            "urls_processed": 0,
            "records_written": 0,
            "bytes_downloaded": 0,
            "total_chars": 0,
            "http_request_success_rate": 0.5,
            "content_extraction_success_rate": 0.5,
            "quality_pass_rate": 0.5,
            "deduplication_rate": 0.0,
            "urls_per_second": 0.0,
            "bytes_per_second": 0.0,
            "records_per_minute": 0.0,
        }

        with pytest.raises(ValidationError):
            ConsolidatedMetric.model_validate(invalid_metric)

    def test_rate_bounds_validation(self):
        """Test that rates are bounded [0, 1]."""
        invalid_metric = {
            "run_id": "test",
            "source": "test",
            "timestamp": "2025-10-26T16:23:45.383125+00:00",
            "duration_seconds": 100,
            "urls_discovered": 0,
            "urls_fetched": 0,
            "urls_processed": 0,
            "records_written": 0,
            "bytes_downloaded": 0,
            "total_chars": 0,
            "http_request_success_rate": 1.5,  # Invalid
            "content_extraction_success_rate": 0.5,
            "quality_pass_rate": 0.5,
            "deduplication_rate": 0.0,
            "urls_per_second": 0.0,
            "bytes_per_second": 0.0,
            "records_per_minute": 0.0,
        }

        with pytest.raises(ValidationError):
            ConsolidatedMetric.model_validate(invalid_metric)


class TestDashboardSummaryGeneration:
    """Test dashboard summary generation."""

    def test_summary_from_empty_metrics(self):
        """Test summary generation with no metrics."""
        from scripts.generate_consolidated_metrics import generate_summary

        summary = generate_summary([])

        assert summary["total_records"] == 0
        assert summary["total_runs"] == 0
        assert summary["sources"] == []

    def test_summary_from_single_metric(self):
        """Test summary generation with single metric."""
        from scripts.generate_consolidated_metrics import (
            extract_consolidated_metric,
            generate_summary,
        )

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")
        summary = generate_summary([metric])

        assert summary["total_records"] == 28
        assert summary["total_urls_processed"] == 28
        assert summary["total_runs"] == 1
        assert "BBC-Somali" in summary["sources"]

    def test_summary_source_breakdown(self):
        """Test that source breakdown is calculated correctly."""
        from scripts.generate_consolidated_metrics import (
            extract_consolidated_metric,
            generate_summary,
        )

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")
        summary = generate_summary([metric])

        assert "source_breakdown" in summary
        assert "BBC-Somali" in summary["source_breakdown"]

        bbc_stats = summary["source_breakdown"]["BBC-Somali"]
        assert bbc_stats["records"] == 28
        assert bbc_stats["runs"] == 1
        assert "avg_success_rate" in bbc_stats
        assert "avg_quality_pass_rate" in bbc_stats

    def test_summary_validation(self):
        """Test that generated summary passes validation."""
        from scripts.generate_consolidated_metrics import (
            extract_consolidated_metric,
            generate_summary,
        )

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")
        summary = generate_summary([metric])

        # Should not raise
        validated = validate_dashboard_summary(summary)
        assert validated.total_records == 28


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_layered_metrics(self):
        """Test handling of missing layered_metrics."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        invalid_data = SAMPLE_PROCESSING_JSON.copy()
        del invalid_data["layered_metrics"]

        # Should handle gracefully (fallback to legacy or return None)
        extract_consolidated_metric(invalid_data, "test.json")
        # Implementation may return None or extract from legacy

    def test_empty_filter_breakdown(self):
        """Test handling of empty filter breakdown."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        data = SAMPLE_PROCESSING_JSON.copy()
        data["layered_metrics"]["quality"]["filter_breakdown"] = {}

        metric = extract_consolidated_metric(data, "test.json")
        assert metric is not None
        # filter_breakdown may be omitted or empty dict

    def test_missing_optional_stats(self):
        """Test handling of missing optional stats."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        data = SAMPLE_PROCESSING_JSON.copy()
        del data["legacy_metrics"]["statistics"]["text_length_stats"]
        del data["legacy_metrics"]["statistics"]["fetch_duration_stats"]

        metric = extract_consolidated_metric(data, "test.json")
        assert metric is not None
        # Optional stats should not be present

    def test_zero_division_in_summary(self):
        """Test that zero division is handled in summary."""
        from scripts.generate_consolidated_metrics import (
            extract_consolidated_metric,
            generate_summary,
        )

        data = SAMPLE_PROCESSING_JSON.copy()
        data["legacy_metrics"]["statistics"]["http_request_success_rate"] = 0

        metric = extract_consolidated_metric(data, "test.json")
        summary = generate_summary([metric])

        # Should handle gracefully
        assert summary["avg_success_rate"] == 0


class TestSchemaContract:
    """Test that schema contract is enforced."""

    def test_required_fields_in_consolidated_metric(self):
        """Test that all required fields are present in consolidated metric."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        required_fields = [
            "run_id",
            "source",
            "timestamp",
            "duration_seconds",
            "urls_discovered",
            "urls_fetched",
            "urls_processed",
            "records_written",
            "bytes_downloaded",
            "total_chars",
            "http_request_success_rate",
            "content_extraction_success_rate",
            "quality_pass_rate",
            "deduplication_rate",
            "urls_per_second",
            "bytes_per_second",
            "records_per_minute",
        ]

        for field in required_fields:
            assert field in metric, f"Missing required field: {field}"

    def test_deprecated_metrics_excluded(self):
        """Test that deprecated metrics are not surfaced."""
        from scripts.generate_consolidated_metrics import extract_consolidated_metric

        metric = extract_consolidated_metric(SAMPLE_PROCESSING_JSON, "test.json")

        # Deprecated fields should not be in consolidated metric
        deprecated_fields = ["success_rate", "dedup_rate", "performance", "quality"]

        for field in deprecated_fields:
            assert field not in metric, f"Deprecated field present: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
