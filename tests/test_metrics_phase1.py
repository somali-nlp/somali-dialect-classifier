"""
Test suite demonstrating Phase 1 metrics refactoring.

Shows before/after comparison for each pipeline type to validate:
1. Semantic accuracy of new metric names
2. BBC test limit bug fix
3. Backward compatibility
4. Metric semantics metadata
"""

import pytest
from somali_dialect_classifier.utils.metrics import (
    MetricsCollector,
    PipelineType,
    MetricSnapshot,
)


class TestWebScrapingMetrics:
    """Test web scraping metrics (BBC pipeline)."""

    def test_bbc_metrics_semantic_accuracy(self):
        """
        Test that web scraping metrics have semantically accurate names.

        BEFORE: fetch_success_rate (confusing - fetch what? HTTP? Content?)
        AFTER: http_request_success_rate + content_extraction_success_rate
        """
        # Simulate BBC web scraping
        collector = MetricsCollector(
            run_id="test_bbc",
            source="BBC-Somali",
            pipeline_type=PipelineType.WEB_SCRAPING
        )

        # Simulate: 20 URLs attempted, 18 succeeded, 2 failed
        collector.increment("urls_discovered", 20)
        collector.increment("urls_fetched", 18)
        collector.increment("urls_failed", 2)
        collector.increment("urls_processed", 15)  # 15 passed quality filters
        collector.increment("urls_deduplicated", 3)  # 3 duplicates

        # Record HTTP status codes
        for _ in range(18):
            collector.record_http_status(200)
        for _ in range(2):
            collector.record_http_status(404)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # NEW METRICS: Semantically accurate
        assert "http_request_success_rate" in stats
        assert "content_extraction_success_rate" in stats

        # Validate values
        assert stats["http_request_success_rate"] == 18 / 20  # 90%
        assert stats["content_extraction_success_rate"] == 1.0  # 100% of fetched

        # Quality filtering is separate from HTTP success
        assert stats["quality_pass_rate"] == 15 / 15  # 100% (15 non-dup, 15 passed)

        # BACKWARD COMPATIBILITY: Old metric still available
        assert "fetch_success_rate" in stats
        assert stats["fetch_success_rate"] == stats["http_request_success_rate"]

        # METADATA: Semantic descriptions available
        assert "_metric_semantics" in stats
        assert "http_request_success_rate" in stats["_metric_semantics"]
        assert "Network-level HTTP success" in stats["_metric_semantics"]["http_request_success_rate"]

        # DEPRECATION WARNINGS: Present for old metrics
        assert "_deprecation_warnings" in stats
        assert len(stats["_deprecation_warnings"]) > 0
        assert "deprecated" in stats["_deprecation_warnings"][0].lower()

    def test_bbc_test_limit_bug_fix(self):
        """
        Test that BBC test limit bug is fixed.

        BUG: Used urls_discovered as denominator (includes skipped URLs)
        FIX: Use urls_fetched + urls_failed (only attempted URLs)
        """
        collector = MetricsCollector(
            run_id="test_bbc_limit",
            source="BBC-Somali",
            pipeline_type=PipelineType.WEB_SCRAPING
        )

        # Simulate: 1000 URLs discovered, but only 20 attempted (test limit)
        collector.increment("urls_discovered", 1000)
        collector.increment("urls_fetched", 18)
        collector.increment("urls_failed", 2)

        # Record HTTP status
        for _ in range(18):
            collector.record_http_status(200)
        for _ in range(2):
            collector.record_http_status(404)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # BEFORE (bug): 18/1000 = 1.8% (misleadingly low)
        # AFTER (fixed): 18/20 = 90% (accurate)
        assert stats["http_request_success_rate"] == 18 / 20  # 90%

        # Verify calculation uses attempted URLs, not discovered
        total_attempted = snapshot.urls_fetched + snapshot.urls_failed
        assert total_attempted == 20
        assert stats["http_request_success_rate"] == snapshot.urls_fetched / total_attempted


class TestFileProcessingMetrics:
    """Test file processing metrics (Wikipedia, Språkbanken pipelines)."""

    def test_wikipedia_metrics_semantic_accuracy(self):
        """
        Test that file processing metrics have semantically accurate names.

        BEFORE: fetch_success_rate (misleading - no HTTP fetching happens)
        AFTER: file_extraction_success_rate + record_parsing_success_rate
        """
        collector = MetricsCollector(
            run_id="test_wikipedia",
            source="Wikipedia-Somali",
            pipeline_type=PipelineType.FILE_PROCESSING
        )

        # Simulate: 1 dump file discovered, extracted 10000 records
        collector.increment("files_discovered", 1)
        collector.increment("files_processed", 1)
        collector.increment("records_extracted", 10000)
        collector.increment("records_written", 9500)  # 500 filtered by quality

        # Simulate deduplication by recording hashes
        for _ in range(500):
            collector.record_hash("duplicate_hash")  # Same hash = duplicate
        for i in range(9500):
            collector.record_hash(f"unique_hash_{i}")  # Unique hashes

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # NEW METRICS: Semantically accurate
        assert "file_extraction_success_rate" in stats
        assert "record_parsing_success_rate" in stats

        # Validate values
        assert stats["file_extraction_success_rate"] == 1.0  # 100% files extracted
        assert stats["record_parsing_success_rate"] == 1.0  # 100% records parsed

        # Quality filtering: 9500 records written out of (10000 - 500 duplicates) = 9500 non-dup
        non_dup = 10000 - 500
        assert stats["quality_pass_rate"] == pytest.approx(9500 / non_dup, rel=0.01)

        # BACKWARD COMPATIBILITY
        assert "fetch_success_rate" in stats
        assert stats["fetch_success_rate"] == stats["file_extraction_success_rate"]

        # METADATA
        assert "_metric_semantics" in stats
        assert "local file I/O" in stats["_metric_semantics"]["file_extraction_success_rate"]

    def test_file_processing_no_files_tracked(self):
        """
        Test fallback when files_discovered = 0 but records extracted.

        This happens when file discovery isn't tracked separately.
        """
        collector = MetricsCollector(
            run_id="test_sprakbanken",
            source="Sprakbanken-Somali",
            pipeline_type=PipelineType.FILE_PROCESSING
        )

        # No file tracking, but records extracted
        collector.increment("records_extracted", 5000)
        collector.increment("records_written", 4800)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # Should assume 100% file extraction if records were extracted
        assert stats["file_extraction_success_rate"] == 1.0
        assert stats["record_parsing_success_rate"] == 1.0


class TestStreamProcessingMetrics:
    """Test stream processing metrics (HuggingFace pipeline)."""

    def test_huggingface_metrics_semantic_accuracy(self):
        """
        Test that stream processing metrics have semantically accurate names.

        BEFORE: fetch_success_rate = 100% (misleading - only 20 records fetched)
        AFTER: stream_connection_success_rate + record_retrieval_success_rate + dataset_coverage_rate
        """
        collector = MetricsCollector(
            run_id="test_huggingface",
            source="HuggingFace-C4-SO",
            pipeline_type=PipelineType.STREAM_PROCESSING
        )

        # Simulate: Stream connected, 20 records fetched, 0 passed quality
        collector.increment("datasets_opened", 1)
        collector.increment("records_fetched", 20)
        collector.increment("records_processed", 0)  # All failed quality
        collector.increment("batches_completed", 1)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # NEW METRICS: Semantically accurate
        assert "stream_connection_success_rate" in stats
        assert "record_retrieval_success_rate" in stats
        assert "dataset_coverage_rate" in stats

        # Validate values
        assert stats["stream_connection_success_rate"] == 1.0  # Connected
        assert stats["record_retrieval_success_rate"] == 1.0  # All requested records received
        assert stats["dataset_coverage_rate"] is None  # Unknown (dataset size not tracked)

        # Quality filtering shows the real issue
        assert stats["quality_pass_rate"] == 0.0  # 0% passed quality (the real problem)

        # BEFORE (misleading): fetch_success_rate = 100% (hides that only 20 records fetched)
        # AFTER (accurate): Shows connection succeeded, but coverage unknown

        # BACKWARD COMPATIBILITY
        assert "fetch_success_rate" in stats
        assert stats["fetch_success_rate"] == stats["stream_connection_success_rate"]

        # METADATA
        assert "_metric_semantics" in stats
        assert "boolean" in stats["_metric_semantics"]["stream_connection_success_rate"].lower()

    def test_stream_connection_failure(self):
        """Test metrics when stream connection fails."""
        collector = MetricsCollector(
            run_id="test_huggingface_fail",
            source="HuggingFace-C4-SO",
            pipeline_type=PipelineType.STREAM_PROCESSING
        )

        # No records fetched (connection failed)
        # (no increments made)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # All metrics should be 0
        assert stats["stream_connection_success_rate"] == 0.0
        assert stats["record_retrieval_success_rate"] == 0.0
        assert stats["dataset_coverage_rate"] is None
        assert stats["quality_pass_rate"] == 0.0


class TestMetricSemantics:
    """Test metric semantics metadata functionality."""

    def test_all_pipelines_have_semantics(self):
        """Test that all pipeline types provide semantic metadata."""
        pipeline_types = [
            PipelineType.WEB_SCRAPING,
            PipelineType.FILE_PROCESSING,
            PipelineType.STREAM_PROCESSING,
        ]

        for pipeline_type in pipeline_types:
            collector = MetricsCollector(
                run_id=f"test_{pipeline_type.value}",
                source="Test",
                pipeline_type=pipeline_type
            )

            # Add minimal data
            if pipeline_type == PipelineType.WEB_SCRAPING:
                collector.increment("urls_fetched", 1)
            elif pipeline_type == PipelineType.FILE_PROCESSING:
                collector.increment("records_extracted", 1)
            elif pipeline_type == PipelineType.STREAM_PROCESSING:
                collector.increment("records_fetched", 1)

            snapshot = collector.get_snapshot()
            stats = snapshot.calculate_statistics()

            # Verify semantics exist
            assert "_metric_semantics" in stats
            assert len(stats["_metric_semantics"]) > 0

            # Verify deprecation warnings exist
            assert "_deprecation_warnings" in stats

    def test_semantic_descriptions_are_helpful(self):
        """Test that semantic descriptions are human-readable."""
        collector = MetricsCollector(
            run_id="test_semantics",
            source="Test",
            pipeline_type=PipelineType.WEB_SCRAPING
        )
        collector.increment("urls_fetched", 1)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        semantics = stats["_metric_semantics"]

        # Each description should be a helpful string
        for metric_name, description in semantics.items():
            assert isinstance(description, str)
            assert len(description) > 10  # Not empty
            # Description should mention key terms from the metric name or be a deprecation notice
            key_terms = ["http", "request", "content", "extract", "quality", "dedup", "duplicat", "deprecated", "record", "filter", "success"]
            assert any(term in description.lower() for term in key_terms), f"No key terms found in: {description}"


class TestBackwardCompatibility:
    """Test backward compatibility with old metric names."""

    def test_old_metrics_still_available(self):
        """Test that old metric names are still accessible."""
        pipeline_types = [
            PipelineType.WEB_SCRAPING,
            PipelineType.FILE_PROCESSING,
            PipelineType.STREAM_PROCESSING,
        ]

        for pipeline_type in pipeline_types:
            collector = MetricsCollector(
                run_id=f"test_{pipeline_type.value}",
                source="Test",
                pipeline_type=pipeline_type
            )

            # Add minimal data
            if pipeline_type == PipelineType.WEB_SCRAPING:
                collector.increment("urls_fetched", 10)
                collector.increment("urls_failed", 0)
            elif pipeline_type == PipelineType.FILE_PROCESSING:
                collector.increment("files_discovered", 1)
                collector.increment("files_processed", 1)
            elif pipeline_type == PipelineType.STREAM_PROCESSING:
                collector.increment("records_fetched", 10)

            snapshot = collector.get_snapshot()
            stats = snapshot.calculate_statistics()

            # Old metric should still exist
            assert "fetch_success_rate" in stats

            # Verify it's aliased to the correct new metric
            if pipeline_type == PipelineType.WEB_SCRAPING:
                assert stats["fetch_success_rate"] == stats["http_request_success_rate"]
            elif pipeline_type == PipelineType.FILE_PROCESSING:
                assert stats["fetch_success_rate"] == stats["file_extraction_success_rate"]
            elif pipeline_type == PipelineType.STREAM_PROCESSING:
                assert stats["fetch_success_rate"] == stats["stream_connection_success_rate"]

    def test_quality_pass_rate_unchanged(self):
        """Test that quality_pass_rate calculation uses new correct formula."""
        collector = MetricsCollector(
            run_id="test_quality",
            source="Test",
            pipeline_type=PipelineType.WEB_SCRAPING
        )

        collector.increment("urls_fetched", 100)
        collector.increment("urls_deduplicated", 10)
        collector.increment("urls_processed", 80)  # 80 passed quality
        collector.increment("records_filtered", 10)  # 10 failed quality

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        # Quality pass rate should be: records_written / (records_written + records_filtered)
        # Note: urls_processed = records_written for web scraping
        expected_quality_rate = 80 / (80 + 10)  # 80 / 90 = 0.8888
        assert stats["quality_pass_rate"] == expected_quality_rate


def test_demonstration_output():
    """
    Demonstration test showing before/after metrics for all pipeline types.

    Run this test to see the improved metric semantics in action.
    """
    print("\n" + "=" * 80)
    print("METRICS PHASE 1 REFACTORING DEMONSTRATION")
    print("=" * 80)

    # ============================================================
    # WEB SCRAPING DEMONSTRATION
    # ============================================================
    print("\n📡 WEB SCRAPING (BBC)")
    print("-" * 80)

    bbc_collector = MetricsCollector(
        run_id="demo_bbc",
        source="BBC-Somali",
        pipeline_type=PipelineType.WEB_SCRAPING
    )

    # Simulate realistic BBC scenario
    bbc_collector.increment("urls_discovered", 187)
    bbc_collector.increment("urls_fetched", 177)
    bbc_collector.increment("urls_failed", 10)
    bbc_collector.increment("urls_processed", 150)
    bbc_collector.increment("urls_deduplicated", 10)

    for _ in range(177):
        bbc_collector.record_http_status(200)
    for _ in range(10):
        bbc_collector.record_http_status(404)

    bbc_stats = bbc_collector.get_snapshot().calculate_statistics()

    print("NEW METRICS (Phase 1):")
    print(f"  http_request_success_rate: {bbc_stats['http_request_success_rate']:.1%}")
    print(f"  content_extraction_success_rate: {bbc_stats['content_extraction_success_rate']:.1%}")
    print(f"  quality_pass_rate: {bbc_stats['quality_pass_rate']:.1%}")
    print(f"\nOLD METRIC (deprecated, backward compatible):")
    print(f"  fetch_success_rate: {bbc_stats['fetch_success_rate']:.1%}")
    print(f"\nSEMANTICS:")
    print(f"  {bbc_stats['_metric_semantics']['http_request_success_rate']}")

    # ============================================================
    # FILE PROCESSING DEMONSTRATION
    # ============================================================
    print("\n" + "=" * 80)
    print("\n📁 FILE PROCESSING (Wikipedia)")
    print("-" * 80)

    wiki_collector = MetricsCollector(
        run_id="demo_wikipedia",
        source="Wikipedia-Somali",
        pipeline_type=PipelineType.FILE_PROCESSING
    )

    wiki_collector.increment("files_discovered", 1)
    wiki_collector.increment("files_processed", 1)
    wiki_collector.increment("records_extracted", 10000)
    wiki_collector.increment("records_written", 10000)

    wiki_stats = wiki_collector.get_snapshot().calculate_statistics()

    print("NEW METRICS (Phase 1):")
    print(f"  file_extraction_success_rate: {wiki_stats['file_extraction_success_rate']:.1%}")
    print(f"  record_parsing_success_rate: {wiki_stats['record_parsing_success_rate']:.1%}")
    print(f"  quality_pass_rate: {wiki_stats['quality_pass_rate']:.1%}")
    print(f"\nOLD METRIC (deprecated, backward compatible):")
    print(f"  fetch_success_rate: {wiki_stats['fetch_success_rate']:.1%}")
    print(f"\nSEMANTICS:")
    print(f"  {wiki_stats['_metric_semantics']['file_extraction_success_rate']}")

    # ============================================================
    # STREAM PROCESSING DEMONSTRATION
    # ============================================================
    print("\n" + "=" * 80)
    print("\n🌊 STREAM PROCESSING (HuggingFace)")
    print("-" * 80)

    hf_collector = MetricsCollector(
        run_id="demo_huggingface",
        source="HuggingFace-C4-SO",
        pipeline_type=PipelineType.STREAM_PROCESSING
    )

    hf_collector.increment("datasets_opened", 1)
    hf_collector.increment("records_fetched", 20)
    hf_collector.increment("records_processed", 0)  # All failed quality

    hf_stats = hf_collector.get_snapshot().calculate_statistics()

    print("NEW METRICS (Phase 1):")
    print(f"  stream_connection_success_rate: {hf_stats['stream_connection_success_rate']:.1%}")
    print(f"  record_retrieval_success_rate: {hf_stats['record_retrieval_success_rate']:.1%}")
    print(f"  dataset_coverage_rate: {hf_stats['dataset_coverage_rate']} (unknown)")
    print(f"  quality_pass_rate: {hf_stats['quality_pass_rate']:.1%}")
    print(f"\nOLD METRIC (deprecated, backward compatible):")
    print(f"  fetch_success_rate: {hf_stats['fetch_success_rate']:.1%}")
    print(f"\nSEMANTICS:")
    print(f"  {hf_stats['_metric_semantics']['stream_connection_success_rate']}")

    print("\n" + "=" * 80)
    print("✅ Phase 1 refactoring complete - metrics are now semantically accurate!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Run demonstration
    test_demonstration_output()
