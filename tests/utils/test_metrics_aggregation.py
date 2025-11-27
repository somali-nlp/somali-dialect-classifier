"""Tests for metrics aggregation utilities."""
import json
import pytest
from pathlib import Path
from somali_dialect_classifier.infra.metrics_aggregation import (
    extract_consolidated_metric,
    load_metrics_from_file,
    load_all_processing_metrics,
    aggregate_metrics_across_sources,
    calculate_metric_statistics,
)


# Sample Phase 3 processing JSON for testing (without schema validation)
# This matches the fallback structure the function handles
SAMPLE_PHASE3_DATA = {
    "_source": "test-source",
    "_run_id": "test-run-123",
    "_timestamp": "2025-11-15T10:00:00Z",
    "_pipeline_type": "web_scraping",
    "layered_metrics": {
        "connectivity": {
            "connection_attempted": True,
            "connection_successful": True
        },
        "extraction": {
            "stream_opened": True
        },
        "quality": {
            "records_received": 100,
            "records_passed_filters": 80,
            "filter_breakdown": {
                "length_filter": 10,
                "language_filter": 5,
                "empty_filter": 5
            }
        },
        "volume": {
            "records_written": 80,
            "bytes_downloaded": 1024000,
            "total_chars": 50000
        }
    },
    "legacy_metrics": {
        "snapshot": {
            "source": "test-source",
            "run_id": "test-run-123",
            "timestamp": "2025-11-15T10:00:00Z",
            "pipeline_type": "web_scraping",
            "urls_discovered": 150,
            "urls_fetched": 120,
            "urls_processed": 100,
            "records_extracted": 90,
            "duration_seconds": 300,
            "bytes_downloaded": 1024000,
            "records_written": 80
        },
        "statistics": {
            "http_request_success_rate": 0.95,
            "content_extraction_success_rate": 0.90,
            "quality_pass_rate": 0.80,
            "deduplication_rate": 0.10,
            "throughput": {
                "urls_per_second": 0.4,
                "bytes_per_second": 3413.33,
                "records_per_minute": 16.0
            },
            "text_length_stats": {
                "mean": 625.0,
                "median": 600.0,
                "min": 100,
                "max": 2000
            },
            "fetch_duration_stats": {
                "mean": 2.5,
                "median": 2.0,
                "min": 0.5,
                "max": 10.0
            }
        }
    }
}


# Sample Phase 2 (flat) data for backward compatibility testing
SAMPLE_PHASE2_DATA = {
    "records_processed": 100,
    "records_failed": 20,
    "quality_pass_rate": 0.80
}


class TestExtractConsolidatedMetric:
    """Test extract_consolidated_metric function."""

    def test_extract_from_phase3_with_validation(self):
        """Test extraction from Phase 3 structure with schema validation."""
        metric = extract_consolidated_metric(SAMPLE_PHASE3_DATA, "test.json")

        assert metric is not None
        assert metric["source"] == "test-source"
        assert metric["run_id"] == "test-run-123"
        assert metric["records_written"] == 80
        assert metric["bytes_downloaded"] == 1024000
        assert metric["quality_pass_rate"] == 0.80
        assert metric["urls_per_second"] == 0.4

    def test_extract_includes_filter_breakdown(self):
        """Test that filter breakdown is properly extracted."""
        metric = extract_consolidated_metric(SAMPLE_PHASE3_DATA, "test.json")

        assert "filter_breakdown" in metric
        assert metric["filter_breakdown"]["length_filter"] == 10
        assert metric["filter_breakdown"]["language_filter"] == 5

    def test_extract_includes_optional_stats(self):
        """Test that optional stats are included when present."""
        metric = extract_consolidated_metric(SAMPLE_PHASE3_DATA, "test.json")

        assert "text_length_stats" in metric
        assert metric["text_length_stats"]["mean"] == 625.0
        assert "fetch_duration_stats" in metric
        assert metric["fetch_duration_stats"]["median"] == 2.0

    def test_extract_missing_source(self):
        """Test handling of missing source field."""
        data = SAMPLE_PHASE3_DATA.copy()
        data["_source"] = None
        data["legacy_metrics"]["snapshot"]["source"] = None

        metric = extract_consolidated_metric(data, "test.json")
        assert metric is None

    def test_extract_missing_run_id(self):
        """Test handling of missing run_id field."""
        data = SAMPLE_PHASE3_DATA.copy()
        data["_run_id"] = None
        data["legacy_metrics"]["snapshot"]["run_id"] = None

        metric = extract_consolidated_metric(data, "test.json")
        assert metric is None

    def test_extract_handles_missing_optional_stats(self):
        """Test that missing optional stats don't break extraction."""
        data = SAMPLE_PHASE3_DATA.copy()
        del data["legacy_metrics"]["statistics"]["text_length_stats"]
        del data["legacy_metrics"]["statistics"]["fetch_duration_stats"]

        metric = extract_consolidated_metric(data, "test.json")
        assert metric is not None
        assert "text_length_stats" not in metric
        assert "fetch_duration_stats" not in metric

    def test_extract_empty_filter_breakdown(self):
        """Test handling of empty filter breakdown."""
        data = SAMPLE_PHASE3_DATA.copy()
        data["layered_metrics"]["quality"]["filter_breakdown"] = {}

        metric = extract_consolidated_metric(data, "test.json")
        assert metric is not None
        # Empty filter_breakdown should not be included
        assert "filter_breakdown" not in metric or metric["filter_breakdown"] == {}


class TestLoadMetricsFromFile:
    """Test load_metrics_from_file function."""

    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON file."""
        metrics_file = tmp_path / "test.json"
        metrics_file.write_text(json.dumps(SAMPLE_PHASE3_DATA))

        data = load_metrics_from_file(metrics_file)
        assert data == SAMPLE_PHASE3_DATA

    def test_load_missing_file(self, tmp_path):
        """Test loading non-existent file raises FileNotFoundError."""
        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            load_metrics_from_file(missing_file)

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises JSONDecodeError."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_metrics_from_file(invalid_file)


class TestLoadAllProcessingMetrics:
    """Test load_all_processing_metrics function."""

    def test_load_multiple_files(self, tmp_path):
        """Test loading multiple processing JSON files."""
        # Create test files
        (tmp_path / "source1_20251115_processing.json").write_text(
            json.dumps(SAMPLE_PHASE3_DATA)
        )

        data2 = SAMPLE_PHASE3_DATA.copy()
        data2["_source"] = "source2"
        data2["_run_id"] = "run-456"
        data2["legacy_metrics"]["snapshot"]["source"] = "source2"
        data2["legacy_metrics"]["snapshot"]["run_id"] = "run-456"
        (tmp_path / "source2_20251115_processing.json").write_text(
            json.dumps(data2)
        )

        metrics = load_all_processing_metrics(tmp_path)

        assert len(metrics) == 2
        assert metrics[0]["source"] == "test-source"
        assert metrics[1]["source"] == "source2"

    def test_load_empty_directory(self, tmp_path):
        """Test loading from empty directory returns empty list."""
        metrics = load_all_processing_metrics(tmp_path)
        assert metrics == []

    def test_load_missing_directory(self, tmp_path):
        """Test loading from non-existent directory returns empty list."""
        missing_dir = tmp_path / "missing"
        metrics = load_all_processing_metrics(missing_dir)
        assert metrics == []

    def test_load_ignores_invalid_files(self, tmp_path):
        """Test that invalid files are skipped gracefully."""
        # Create valid file
        (tmp_path / "valid_20251115_processing.json").write_text(
            json.dumps(SAMPLE_PHASE3_DATA)
        )

        # Create invalid file
        (tmp_path / "invalid_20251115_processing.json").write_text(
            "{ invalid json }"
        )

        metrics = load_all_processing_metrics(tmp_path)

        # Should only load the valid file
        assert len(metrics) == 1
        assert metrics[0]["source"] == "test-source"

    def test_load_skips_malformed_metrics(self, tmp_path):
        """Test that files with missing required fields are skipped."""
        # Create file with missing source
        incomplete_data = SAMPLE_PHASE3_DATA.copy()
        incomplete_data["_source"] = None
        incomplete_data["legacy_metrics"]["snapshot"]["source"] = None

        (tmp_path / "incomplete_20251115_processing.json").write_text(
            json.dumps(incomplete_data)
        )

        metrics = load_all_processing_metrics(tmp_path)
        assert metrics == []


class TestAggregateMetricsAcrossSources:
    """Test aggregate_metrics_across_sources function."""

    def test_aggregate_single_metric(self, tmp_path):
        """Test aggregating a single metric across sources."""
        # Create test files for different sources
        data1 = SAMPLE_PHASE3_DATA.copy()
        data1["_source"] = "wikipedia"
        data1["legacy_metrics"]["snapshot"]["source"] = "wikipedia"
        data1["layered_metrics"]["volume"]["records_written"] = 100
        (tmp_path / "wikipedia_20251115_processing.json").write_text(
            json.dumps(data1)
        )

        data2 = SAMPLE_PHASE3_DATA.copy()
        data2["_source"] = "bbc-somali"
        data2["_run_id"] = "run-456"
        data2["legacy_metrics"]["snapshot"]["source"] = "bbc-somali"
        data2["legacy_metrics"]["snapshot"]["run_id"] = "run-456"
        data2["layered_metrics"]["volume"]["records_written"] = 50
        (tmp_path / "bbc-somali_20251115_processing.json").write_text(
            json.dumps(data2)
        )

        sources = ['wikipedia', 'bbc-somali']
        result = aggregate_metrics_across_sources(
            tmp_path,
            sources,
            'records_written'
        )

        assert result['wikipedia'] == 100
        assert result['bbc-somali'] == 50

    def test_aggregate_missing_source(self, tmp_path):
        """Test aggregating when source file is missing."""
        sources = ['missing-source']
        result = aggregate_metrics_across_sources(
            tmp_path,
            sources,
            'records_written'
        )

        assert result['missing-source'] is None

    def test_aggregate_uses_most_recent_file(self, tmp_path):
        """Test that most recent file is used when multiple exist."""
        # Create older file
        data1 = SAMPLE_PHASE3_DATA.copy()
        data1["_source"] = "test"
        data1["legacy_metrics"]["snapshot"]["source"] = "test"
        data1["layered_metrics"]["volume"]["records_written"] = 100
        (tmp_path / "test_20251101_processing.json").write_text(
            json.dumps(data1)
        )

        # Create newer file (alphabetically later = more recent)
        data2 = SAMPLE_PHASE3_DATA.copy()
        data2["_source"] = "test"
        data2["legacy_metrics"]["snapshot"]["source"] = "test"
        data2["layered_metrics"]["volume"]["records_written"] = 200
        (tmp_path / "test_20251115_processing.json").write_text(
            json.dumps(data2)
        )

        sources = ['test']
        result = aggregate_metrics_across_sources(
            tmp_path,
            sources,
            'records_written'
        )

        # Should use the most recent file (20251115)
        assert result['test'] == 200


class TestCalculateMetricStatistics:
    """Test calculate_metric_statistics function."""

    def test_calculate_basic_statistics(self):
        """Test calculating statistics from valid values."""
        values = [100, 200, 150, 300]
        stats = calculate_metric_statistics(values)

        assert stats['mean'] == 187.5
        assert stats['median'] == 175.0
        assert stats['min'] == 100
        assert stats['max'] == 300
        assert stats['sum'] == 750
        assert stats['count'] == 4

    def test_calculate_with_none_values(self):
        """Test that None values are filtered out."""
        values = [100, None, 200, None, 300]
        stats = calculate_metric_statistics(values)

        assert stats['count'] == 3  # None values filtered
        assert stats['mean'] == 200.0
        assert stats['sum'] == 600

    def test_calculate_empty_list(self):
        """Test statistics with empty list."""
        stats = calculate_metric_statistics([])

        assert stats['count'] == 0
        assert stats['sum'] == 0.0
        assert stats['mean'] == 0.0

    def test_calculate_all_none_values(self):
        """Test statistics with all None values."""
        values = [None, None, None]
        stats = calculate_metric_statistics(values)

        assert stats['count'] == 0
        assert stats['sum'] == 0.0

    def test_calculate_single_value(self):
        """Test statistics with single value."""
        values = [42]
        stats = calculate_metric_statistics(values)

        assert stats['count'] == 1
        assert stats['mean'] == 42
        assert stats['median'] == 42
        assert stats['min'] == 42
        assert stats['max'] == 42
        assert stats['sum'] == 42

    def test_calculate_with_floats(self):
        """Test statistics with floating point values."""
        values = [1.5, 2.5, 3.5]
        stats = calculate_metric_statistics(values)

        assert stats['mean'] == 2.5
        assert stats['median'] == 2.5
        assert stats['sum'] == 7.5
        assert stats['count'] == 3
