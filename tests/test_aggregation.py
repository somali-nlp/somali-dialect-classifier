"""
Tests for volume-weighted aggregation functions (Phase 2).

This test suite validates:
1. Volume-weighted mean vs simple average shows difference
2. Harmonic mean penalizes outliers correctly
3. Compatibility validation catches mistakes
4. Handles zero records gracefully
5. Breakdown shows source contributions accurately
"""

import pytest

from somali_dialect_classifier.utils.aggregation import (
    AggregationMethod,
    _extract_metrics,
    aggregate_compatible_metrics,
    calculate_aggregate_summary,
    calculate_volume_weighted_quality,
    calculate_weighted_harmonic_mean,
    validate_metric_compatibility,
)


class TestVolumeWeightedAggregation:
    """Test volume-weighted aggregation functions."""

    def test_volume_weighted_vs_simple_average(self):
        """
        Test that volume-weighted mean differs from simple average.

        Scenario: BBC has 150 records at 84.7% quality, Wikipedia has 10,000 at 100%
        - Simple average: (0.847 + 1.0) / 2 = 0.9235 (92.35%)
        - Volume-weighted: (150*0.847 + 10000*1.0) / 10150 = 0.998 (99.8%)
        """
        sources = [
            {
                "name": "BBC",
                "records_written": 150,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.847}},
            },
            {
                "name": "Wikipedia",
                "records_written": 10000,
                "layered_metrics": {"quality": {"quality_pass_rate": 1.0}},
            },
        ]

        result = calculate_volume_weighted_quality(sources)

        # Simple average would be 0.9235
        simple_avg = (0.847 + 1.0) / 2
        assert simple_avg == pytest.approx(0.9235, abs=0.001)

        # Volume-weighted should be ~0.998
        weighted_avg = result["overall_quality_rate"]
        assert weighted_avg == pytest.approx(0.998, abs=0.001)

        # They should be different!
        assert abs(weighted_avg - simple_avg) > 0.05, (
            "Volume-weighted should differ significantly from simple average"
        )

        # Verify breakdown
        assert result["total_records"] == 10150
        assert result["sources_count"] == 2
        assert len(result["source_breakdown"]) == 2

        # BBC contributes ~1.5% of data
        bbc_contribution = next(s for s in result["source_breakdown"] if s["source"] == "BBC")
        assert bbc_contribution["contribution"] == pytest.approx(0.0148, abs=0.001)

        # Wikipedia contributes ~98.5% of data
        wiki_contribution = next(
            s for s in result["source_breakdown"] if s["source"] == "Wikipedia"
        )
        assert wiki_contribution["contribution"] == pytest.approx(0.9852, abs=0.001)

    def test_harmonic_mean_penalizes_outliers(self):
        """
        Test that harmonic mean penalizes low performers more than arithmetic mean.

        Scenario: Three sources with 10%, 100%, 100% quality
        - Arithmetic mean: (0.1 + 1.0 + 1.0) / 3 = 0.7 (70%)
        - Harmonic mean: 3 / (1/0.1 + 1/1.0 + 1/1.0) = 0.25 (25%)
        """
        sources = [
            {
                "name": "Poor Source",
                "records_written": 100,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.1}},
            },
            {
                "name": "Good Source 1",
                "records_written": 100,
                "layered_metrics": {"quality": {"quality_pass_rate": 1.0}},
            },
            {
                "name": "Good Source 2",
                "records_written": 100,
                "layered_metrics": {"quality": {"quality_pass_rate": 1.0}},
            },
        ]

        # Arithmetic mean (simple average)
        arithmetic = (0.1 + 1.0 + 1.0) / 3
        assert arithmetic == pytest.approx(0.7, abs=0.01)

        # Harmonic mean (unweighted)
        harmonic = aggregate_compatible_metrics(
            sources, "quality_pass_rate", method=AggregationMethod.HARMONIC_MEAN
        )
        assert harmonic == pytest.approx(0.25, abs=0.01)

        # Harmonic should be lower (more pessimistic)
        assert harmonic < arithmetic, "Harmonic mean should penalize poor performers"

    def test_weighted_harmonic_mean(self):
        """
        Test weighted harmonic mean with different data volumes.

        If the poor performer has much less data, weighted harmonic should be higher.
        """
        sources = [
            {
                "name": "Poor Small Source",
                "records_written": 10,  # Only 10 records
                "layered_metrics": {"quality": {"quality_pass_rate": 0.1}},
            },
            {
                "name": "Good Large Source",
                "records_written": 10000,  # 10,000 records
                "layered_metrics": {"quality": {"quality_pass_rate": 1.0}},
            },
        ]

        # Unweighted harmonic mean
        unweighted = calculate_weighted_harmonic_mean(sources)

        # Volume-weighted arithmetic mean
        weighted_arithmetic = calculate_volume_weighted_quality(sources)["overall_quality_rate"]

        # Weighted harmonic should be between unweighted harmonic and weighted arithmetic
        # But still lower than arithmetic due to harmonic penalty
        assert unweighted < weighted_arithmetic

    def test_compatibility_validation_accepts_compatible_metrics(self):
        """Test that compatible metrics pass validation."""
        sources = [
            {"snapshot": {"pipeline_type": "web_scraping"}, "statistics": {}},
            {"snapshot": {"pipeline_type": "file_processing"}, "statistics": {}},
        ]

        # These should all be compatible across different pipeline types
        compatible_metrics = [
            "quality_pass_rate",
            "deduplication_rate",
            "records_written",
            "bytes_downloaded",
        ]

        for metric in compatible_metrics:
            is_compat, reason = validate_metric_compatibility(sources, metric)
            assert is_compat, f"{metric} should be compatible across all pipeline types"
            assert reason is None

    def test_compatibility_validation_rejects_incompatible_metrics(self):
        """Test that incompatible metrics fail validation."""
        sources = [
            {"snapshot": {"pipeline_type": "web_scraping"}, "statistics": {}},
            {"snapshot": {"pipeline_type": "file_processing"}, "statistics": {}},
        ]

        # HTTP metrics only valid for web_scraping
        is_compat, reason = validate_metric_compatibility(sources, "http_request_success_rate")
        assert not is_compat, (
            "http_request_success_rate should NOT be compatible across different pipeline types"
        )
        assert reason is not None
        assert "different pipeline types" in reason.lower()

    def test_compatibility_validation_allows_same_pipeline_type(self):
        """Test that pipeline-specific metrics work when all sources have same type."""
        sources = [
            {"snapshot": {"pipeline_type": "web_scraping"}, "statistics": {}},
            {"snapshot": {"pipeline_type": "web_scraping"}, "statistics": {}},
        ]

        # HTTP metrics valid when all are web_scraping
        is_compat, reason = validate_metric_compatibility(sources, "http_request_success_rate")
        assert is_compat, (
            "http_request_success_rate should be compatible when all sources are web_scraping"
        )
        assert reason is None

    def test_handles_zero_records_gracefully(self):
        """Test that aggregation handles zero records without crashing."""
        # Empty sources list
        result = calculate_volume_weighted_quality([])
        assert result["overall_quality_rate"] == 0.0
        assert result["total_records"] == 0
        assert result["sources_count"] == 0
        assert len(result["source_breakdown"]) == 0

        # Sources with zero records
        sources = [
            {
                "name": "Empty Source",
                "records_written": 0,
                "layered_metrics": {"quality": {"quality_pass_rate": 1.0}},
            }
        ]
        result = calculate_volume_weighted_quality(sources)
        assert result["overall_quality_rate"] == 0.0
        assert result["total_records"] == 0

    def test_breakdown_shows_source_contributions(self):
        """Test that breakdown accurately shows each source's contribution."""
        sources = [
            {
                "name": "Source A",
                "records_written": 1000,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.9}},
            },
            {
                "name": "Source B",
                "records_written": 2000,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.8}},
            },
            {
                "name": "Source C",
                "records_written": 1000,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.95}},
            },
        ]

        result = calculate_volume_weighted_quality(sources)

        # Total should be 4000
        assert result["total_records"] == 4000

        # Check contributions
        breakdown = {s["source"]: s for s in result["source_breakdown"]}

        assert breakdown["Source A"]["contribution"] == pytest.approx(0.25, abs=0.001)  # 1000/4000
        assert breakdown["Source B"]["contribution"] == pytest.approx(0.50, abs=0.001)  # 2000/4000
        assert breakdown["Source C"]["contribution"] == pytest.approx(0.25, abs=0.001)  # 1000/4000

        # Contributions should sum to 1.0
        total_contribution = sum(s["contribution"] for s in result["source_breakdown"])
        assert total_contribution == pytest.approx(1.0, abs=0.001)

    def test_aggregation_methods(self):
        """Test different aggregation methods."""
        sources = [
            {
                "name": "A",
                "records_written": 100,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.8}},
            },
            {
                "name": "B",
                "records_written": 200,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.9}},
            },
            {
                "name": "C",
                "records_written": 300,
                "layered_metrics": {"quality": {"quality_pass_rate": 0.7}},
            },
        ]

        # MIN
        min_val = aggregate_compatible_metrics(sources, "quality_pass_rate", AggregationMethod.MIN)
        assert min_val == 0.7

        # MAX
        max_val = aggregate_compatible_metrics(sources, "quality_pass_rate", AggregationMethod.MAX)
        assert max_val == 0.9

        # SUM (for records_written)
        sum_val = aggregate_compatible_metrics(sources, "records_written", AggregationMethod.SUM)
        assert sum_val == 600

    def test_processing_json_format(self):
        """Test that aggregation works with real processing.json format."""
        sources = [
            {
                "snapshot": {
                    "source": "BBC-Somali",
                    "pipeline_type": "web_scraping",
                    "records_written": 20,
                    "bytes_downloaded": 99176,
                },
                "statistics": {"quality_pass_rate": 1.0, "deduplication_rate": 0.0},
            },
            {
                "snapshot": {
                    "source": "Wikipedia-Somali",
                    "pipeline_type": "file_processing",
                    "records_written": 9623,
                    "bytes_downloaded": 14280506,
                },
                "statistics": {"quality_pass_rate": 0.7075735294117646, "deduplication_rate": 0.0},
            },
        ]

        result = calculate_volume_weighted_quality(sources)

        # Should work without errors
        assert result["total_records"] == 9643
        assert result["sources_count"] == 2

        # Weighted average: (20*1.0 + 9623*0.7076) / 9643 = 0.709
        expected = (20 * 1.0 + 9623 * 0.7075735294117646) / 9643
        assert result["overall_quality_rate"] == pytest.approx(expected, abs=0.001)


class TestExtractMetrics:
    """Test the _extract_metrics helper function."""

    def test_extract_from_flat_format(self):
        """Test extraction from flat format with layered_metrics."""
        source = {
            "name": "Test Source",
            "records_written": 100,
            "layered_metrics": {"quality": {"quality_pass_rate": 0.85}},
        }

        weight, value, name = _extract_metrics(source, "quality_pass_rate")
        assert weight == 100
        assert value == 0.85
        assert name == "Test Source"

    def test_extract_from_processing_json_format(self):
        """Test extraction from processing.json format."""
        source = {
            "snapshot": {"source": "BBC-Somali", "records_written": 20},
            "statistics": {"quality_pass_rate": 1.0},
        }

        weight, value, name = _extract_metrics(source, "quality_pass_rate")
        assert weight == 20
        assert value == 1.0
        assert name == "BBC-Somali"

    def test_extract_handles_percentage_conversion(self):
        """Test that values > 1.0 are converted from percentage to rate."""
        source = {
            "name": "Test",
            "records_written": 100,
            "layered_metrics": {
                "quality": {"quality_pass_rate": 85.0}  # 85% as number
            },
        }

        weight, value, name = _extract_metrics(source, "quality_pass_rate")
        assert value == 0.85  # Should be converted to rate


class TestAggregrateSummary:
    """Test the calculate_aggregate_summary function."""

    def test_comprehensive_summary(self):
        """Test comprehensive aggregate summary."""
        sources = [
            {
                "snapshot": {
                    "source": "BBC-Somali",
                    "pipeline_type": "web_scraping",
                    "records_written": 20,
                    "bytes_downloaded": 99176,
                },
                "statistics": {"quality_pass_rate": 1.0, "deduplication_rate": 0.0},
            },
            {
                "snapshot": {
                    "source": "Wikipedia-Somali",
                    "pipeline_type": "file_processing",
                    "records_written": 9623,
                    "bytes_downloaded": 14280506,
                },
                "statistics": {"quality_pass_rate": 0.7075735294117646, "deduplication_rate": 0.0},
            },
            {
                "snapshot": {
                    "source": "HuggingFace-Somali_c4-so",
                    "pipeline_type": "stream_processing",
                    "records_written": 19,
                    "bytes_downloaded": 0,
                },
                "statistics": {"quality_pass_rate": 0.95, "deduplication_rate": 0.0},
            },
        ]

        summary = calculate_aggregate_summary(sources)

        # Check totals
        assert summary["total_records"] == 20 + 9623 + 19
        assert summary["total_bytes"] == 99176 + 14280506 + 0
        assert summary["sources_count"] == 3

        # Check pipeline types
        assert len(summary["pipeline_types"]) == 3
        assert "web_scraping" in summary["pipeline_types"]
        assert "file_processing" in summary["pipeline_types"]
        assert "stream_processing" in summary["pipeline_types"]

        # Check quality metrics
        assert "overall_quality_rate" in summary["quality_metrics"]
        assert "deduplication_rate" in summary["quality_metrics"]
        assert "source_breakdown" in summary["quality_metrics"]

    def test_summary_with_empty_sources(self):
        """Test summary with no sources."""
        summary = calculate_aggregate_summary([])

        assert summary["total_records"] == 0
        assert summary["total_bytes"] == 0
        assert summary["sources_count"] == 0
        assert len(summary["pipeline_types"]) == 0


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_real_data_bbc_wikipedia_hf(self):
        """Test aggregation with real data from actual run."""
        # Real data from 20251026_100048 run
        sources = [
            {
                "snapshot": {
                    "source": "BBC-Somali",
                    "pipeline_type": "web_scraping",
                    "records_written": 20,
                    "bytes_downloaded": 99176,
                },
                "statistics": {
                    "quality_pass_rate": 1.0,
                    "deduplication_rate": 0.0,
                    "http_request_success_rate": 0.10695187165775401,
                },
            },
            {
                "snapshot": {
                    "source": "Wikipedia-Somali",
                    "pipeline_type": "file_processing",
                    "records_written": 9623,
                    "bytes_downloaded": 14280506,
                },
                "statistics": {
                    "quality_pass_rate": 0.7075735294117646,
                    "deduplication_rate": 0.0,
                    "file_extraction_success_rate": 1.0,
                },
            },
            {
                "snapshot": {
                    "source": "HuggingFace-Somali_c4-so",
                    "pipeline_type": "stream_processing",
                    "records_written": 19,
                    "bytes_downloaded": 0,
                },
                "statistics": {
                    "quality_pass_rate": 0.95,
                    "deduplication_rate": 0.0,
                    "stream_connection_success_rate": 1.0,
                },
            },
        ]

        # Calculate overall quality (should be dominated by Wikipedia since it has 99.6% of records)
        result = calculate_volume_weighted_quality(sources)

        # Wikipedia dominates with 9623/9662 = 99.6% of data
        # So weighted quality should be very close to Wikipedia's 70.76%
        assert result["overall_quality_rate"] == pytest.approx(0.708, abs=0.01)

        # Verify we can't aggregate http_request_success_rate across different pipeline types
        is_compat, reason = validate_metric_compatibility(sources, "http_request_success_rate")
        assert not is_compat
        assert "different pipeline types" in reason.lower()

    def test_phase0_vs_phase2_comparison(self):
        """
        Test that shows the difference between Phase 0 (wrong) and Phase 2 (correct).

        Phase 0 Bug: Averaged incompatible metrics
        Phase 2 Fix: Only aggregate compatible metrics with volume weighting
        """
        sources = [
            {
                "snapshot": {
                    "source": "BBC-Somali",
                    "pipeline_type": "web_scraping",
                    "records_written": 20,
                    "bytes_downloaded": 99176,
                },
                "statistics": {
                    "quality_pass_rate": 1.0,
                    "http_request_success_rate": 0.107,  # 10.7% - misleading if averaged!
                },
            },
            {
                "snapshot": {
                    "source": "Wikipedia-Somali",
                    "pipeline_type": "file_processing",
                    "records_written": 10000,
                    "bytes_downloaded": 14280506,
                },
                "statistics": {
                    "quality_pass_rate": 1.0,
                    "file_extraction_success_rate": 1.0,  # 100% - can't average with HTTP!
                },
            },
        ]

        # Phase 0 would have done: (0.107 + 1.0) / 2 = 0.5535 (55.35%) ← WRONG!
        phase0_wrong = (0.107 + 1.0) / 2
        assert phase0_wrong == pytest.approx(0.5535, abs=0.001)

        # Phase 2: Validate that we can't aggregate incompatible metrics
        is_compat, _ = validate_metric_compatibility(sources, "http_request_success_rate")
        assert not is_compat, "Phase 2 should reject incompatible metric aggregation"

        # Phase 2: But we CAN aggregate quality_pass_rate (compatible)
        is_compat, _ = validate_metric_compatibility(sources, "quality_pass_rate")
        assert is_compat, "Phase 2 should allow compatible metric aggregation"

        # Phase 2: Volume-weighted quality
        result = calculate_volume_weighted_quality(sources)
        # (20*1.0 + 10000*1.0) / 10020 = 1.0 (100%)
        assert result["overall_quality_rate"] == pytest.approx(1.0, abs=0.001)
