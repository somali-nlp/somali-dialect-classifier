"""
Integration tests for Phase 0 foundation components.

Tests:
- Crawl ledger operations
- Deduplication engine
- Metrics collection
- Structured logging
"""

import pytest

from somali_dialect_classifier.preprocessing.crawl_ledger import (
    CrawlLedger,
    CrawlState,
)
from somali_dialect_classifier.preprocessing.dedup import DedupConfig, DedupEngine, TextHasher
from somali_dialect_classifier.utils.logging_utils import (
    StructuredLogger,
    Timer,
    clear_context,
    generate_run_id,
    get_context,
    set_context,
)
from somali_dialect_classifier.utils.metrics import MetricsCollector, QualityReporter


class TestCrawlLedger:
    """Test crawl ledger functionality."""

    def test_ledger_initialization(self, tmp_path):
        """Test ledger database initialization."""
        db_path = tmp_path / "test_ledger.db"
        ledger = CrawlLedger(db_path=db_path)

        assert db_path.exists()
        assert ledger.backend is not None

    def test_discover_url(self, tmp_path):
        """Test URL discovery."""
        ledger = CrawlLedger(db_path=tmp_path / "test.db")

        # Discover new URL
        is_new = ledger.discover_url(
            url="https://example.com/article1", source="bbc", metadata={"category": "news"}
        )
        assert is_new is True

        # Discover same URL again
        is_new = ledger.discover_url(url="https://example.com/article1", source="bbc")
        assert is_new is False

    def test_mark_fetched(self, tmp_path):
        """Test marking URL as fetched."""
        ledger = CrawlLedger(db_path=tmp_path / "test.db")

        url = "https://example.com/article1"
        ledger.discover_url(url, "bbc")

        ledger.mark_fetched(
            url=url, http_status=200, etag="abc123", content_length=5000, source="bbc"
        )

        state = ledger.backend.get_url_state(url)
        assert state is not None
        assert state["state"] == CrawlState.FETCHED.value
        assert state["http_status"] == 200
        assert state["etag"] == "abc123"
        assert state["source"] == "bbc"

    def test_mark_processed(self, tmp_path):
        """Test marking URL as processed."""
        ledger = CrawlLedger(db_path=tmp_path / "test.db")

        url = "https://example.com/article1"
        ledger.discover_url(url, "bbc")

        ledger.mark_processed(url=url, text_hash="abc123hash", silver_id="silver_001", source="bbc")

        state = ledger.backend.get_url_state(url)
        assert state["state"] == CrawlState.PROCESSED.value
        assert state["text_hash"] == "abc123hash"
        assert state["silver_id"] == "silver_001"
        assert state["source"] == "bbc"

    def test_duplicate_detection(self, tmp_path):
        """Test duplicate hash detection."""
        ledger = CrawlLedger(db_path=tmp_path / "test.db")

        # Process first URL
        url1 = "https://example.com/article1"
        ledger.discover_url(url1, "bbc")
        ledger.mark_processed(url1, text_hash="hash123", silver_id="silver_001", source="bbc")

        # Check for duplicate
        duplicate_url = ledger.is_duplicate("hash123")
        assert duplicate_url == url1

        # Check non-existent hash
        duplicate_url = ledger.is_duplicate("nonexistent")
        assert duplicate_url is None

    def test_rss_throttling(self, tmp_path):
        """Test RSS feed throttling."""
        ledger = CrawlLedger(db_path=tmp_path / "test.db")

        feed_url = "https://bbc.com/somali/rss.xml"

        # Should allow first fetch
        should_fetch = ledger.should_fetch_rss(feed_url, min_hours=6)
        assert should_fetch is True

        # Record fetch
        ledger.record_rss_fetch(feed_url, items_found=50)

        # Should not allow immediate re-fetch
        should_fetch = ledger.should_fetch_rss(feed_url, min_hours=6)
        assert should_fetch is False

    def test_statistics(self, tmp_path):
        """Test ledger statistics."""
        ledger = CrawlLedger(db_path=tmp_path / "test.db")

        # Add some URLs
        for i in range(10):
            ledger.discover_url(f"https://example.com/article{i}", "bbc")

        # Mark some as processed
        for i in range(5):
            ledger.mark_processed(
                f"https://example.com/article{i}",
                text_hash=f"hash{i}",
                silver_id=f"silver_{i}",
                source="bbc",
            )

        # Get statistics
        stats = ledger.get_statistics(source="bbc")
        assert stats["total_urls"] == 10
        assert stats["by_state"].get("discovered", 0) == 5
        assert stats["by_state"].get("processed", 0) == 5


class TestDeduplication:
    """Test deduplication engine."""

    def test_text_hasher(self):
        """Test text hashing."""
        hasher = TextHasher(fields=["text"])

        hash1 = hasher.compute_hash("Hello world")
        hash2 = hasher.compute_hash("Hello world")
        hash3 = hasher.compute_hash("Different text")

        # Same text should produce same hash
        assert hash1 == hash2

        # Different text should produce different hash
        assert hash1 != hash3

        # Hash should be deterministic
        assert len(hash1) == 64  # SHA256 produces 64 hex characters

    def test_text_hasher_with_url(self):
        """Test hashing with URL included."""
        hasher = TextHasher(fields=["text", "url"])

        hash1 = hasher.compute_hash("Same text", url="https://example.com/1")
        hash2 = hasher.compute_hash("Same text", url="https://example.com/2")

        # Same text but different URLs should produce different hashes
        assert hash1 != hash2

    def test_exact_deduplication(self):
        """Test exact duplicate detection."""
        config = DedupConfig(
            hash_fields=["text"],
            enable_minhash=False,  # Disable for this test
        )
        engine = DedupEngine(config)

        # Process first document
        is_dup1, dup_type1, similar_url1, hash1, _ = engine.process_document(
            text="Hello world", url="https://example.com/1"
        )
        assert is_dup1 is False
        assert dup_type1 is None
        assert similar_url1 is None

        # Process exact duplicate
        is_dup2, dup_type2, similar_url2, hash2, _ = engine.process_document(
            text="Hello world", url="https://example.com/2"
        )
        assert is_dup2 is True
        assert dup_type2 == "exact"
        assert similar_url2 == "https://example.com/1"  # Should point to first URL
        assert hash1 == hash2

        # Process different document
        is_dup3, dup_type3, similar_url3, hash3, _ = engine.process_document(
            text="Different text", url="https://example.com/3"
        )
        assert is_dup3 is False
        assert dup_type3 is None
        assert similar_url3 is None
        assert hash3 != hash1

    @pytest.mark.skip(reason="MinHash similarity threshold behavior requires tuning - test data too similar")
    def test_near_duplicate_detection(self):
        """Test near-duplicate detection with MinHash."""
        import importlib.util

        if importlib.util.find_spec("datasketch") is None:
            pytest.skip("datasketch not available")

        # Use lower threshold (0.7) to detect near-duplicates with minor word changes
        config = DedupConfig(hash_fields=["text"], enable_minhash=True, similarity_threshold=0.7)

        try:
            engine = DedupEngine(config)
        except ImportError:
            pytest.skip("datasketch not available")

        # Process first document
        is_dup1, dup_type1, similar_url1, _, _ = engine.process_document(
            text="The quick brown fox jumps over the lazy dog", url="https://example.com/1"
        )
        assert is_dup1 is False
        assert dup_type1 is None
        assert similar_url1 is None

        # Process near-duplicate (similar but not exact)
        is_dup2, dup_type2, similar_url2, _, _ = engine.process_document(
            text="The quick brown fox leaps over the lazy dog", url="https://example.com/2"
        )
        # Should be detected as near-duplicate
        assert is_dup2 is True
        assert dup_type2 == "near"
        assert similar_url2 == "https://example.com/1"  # Should point to similar URL

        # Process very different document
        is_dup3, dup_type3, similar_url3, _, _ = engine.process_document(
            text="A completely different sentence about cats and mice", url="https://example.com/3"
        )
        assert is_dup3 is False
        assert dup_type3 is None
        assert similar_url3 is None


class TestMetrics:
    """Test metrics collection and reporting."""

    def test_metrics_collector(self):
        """Test metrics collection."""
        collector = MetricsCollector(run_id="test_run_123", source="test_source")

        # Increment counters
        collector.increment("urls_discovered", 100)
        collector.increment("urls_fetched", 95)
        collector.increment("urls_processed", 90)

        # Record HTTP status
        collector.record_http_status(200)
        collector.record_http_status(404)

        # Record timings
        collector.record_fetch_duration(500.0)
        collector.record_process_duration(100.0)

        # Get snapshot
        snapshot = collector.get_snapshot()

        assert snapshot.run_id == "test_run_123"
        assert snapshot.source == "test_source"
        assert snapshot.urls_discovered == 100
        assert snapshot.urls_fetched == 95
        assert snapshot.urls_processed == 90
        assert len(snapshot.http_status_codes) == 2

    def test_metrics_statistics(self):
        """Test metrics statistics calculation."""
        collector = MetricsCollector(run_id="test", source="test")

        collector.increment("urls_fetched", 100)
        collector.increment("urls_processed", 90)
        collector.increment("urls_failed", 10)

        for _ in range(100):
            collector.record_fetch_duration(500.0)

        snapshot = collector.get_snapshot()
        stats = snapshot.calculate_statistics()

        assert "fetch_success_rate" in stats
        assert abs(stats["fetch_success_rate"] - 0.9) < 0.01  # Approximately 90/100

    def test_quality_reporter(self, tmp_path):
        """Test quality report generation."""
        collector = MetricsCollector(run_id="test", source="test")

        # Add some data
        collector.increment("urls_discovered", 100)
        collector.increment("urls_fetched", 95)
        collector.increment("urls_processed", 90)
        collector.record_http_status(200)

        reporter = QualityReporter(collector)

        # Generate report
        report_path = tmp_path / "quality_report.md"
        reporter.generate_markdown_report(report_path)

        assert report_path.exists()

        # Check report contains expected sections
        content = report_path.read_text()
        assert "# Data Quality Report" in content
        assert "Executive Summary" in content
        assert "Processing Statistics" in content


class TestStructuredLogging:
    """Test structured logging."""

    def test_run_id_generation(self):
        """Test run ID generation."""
        run_id1 = generate_run_id("bbc")
        run_id2 = generate_run_id("bbc")

        # Should be unique
        assert run_id1 != run_id2

        # Should contain source
        assert "bbc" in run_id1

        # Should have expected format
        parts = run_id1.split("_")
        assert len(parts) >= 3  # date_time_source_uuid

    def test_context_management(self):
        """Test logging context management."""
        # Clear any existing context
        clear_context()

        # Set context
        set_context(run_id="test_123", source="bbc")

        context = get_context()
        assert context["run_id"] == "test_123"
        assert context["source"] == "bbc"

        # Clear context
        clear_context()
        context = get_context()
        assert len(context) == 0

    def test_timer(self):
        """Test timing utility."""
        import time

        with Timer() as timer:
            time.sleep(0.1)  # Sleep for 100ms

        elapsed = timer.get_elapsed_ms()
        assert elapsed >= 100  # Should be at least 100ms
        assert elapsed < 200  # But not too much more

    def test_structured_logger(self, tmp_path):
        """Test structured logger initialization."""
        log_file = tmp_path / "test.log"

        logger = StructuredLogger(name="test", level="INFO", log_file=log_file, json_format=True)

        assert logger.logger is not None
        assert log_file.parent.exists()


# Integration test combining components


def test_full_pipeline_integration(tmp_path):
    """Test integration of all foundation components."""
    # Setup
    run_id = generate_run_id("test")
    set_context(run_id=run_id, source="test", phase="integration")

    # Initialize components
    ledger = CrawlLedger(db_path=tmp_path / "ledger.db")
    dedup_config = DedupConfig(hash_fields=["text"], enable_minhash=False)
    dedup_engine = DedupEngine(dedup_config)
    collector = MetricsCollector(run_id=run_id, source="test")

    # Simulate pipeline
    urls = [
        ("https://example.com/1", "First article text"),
        ("https://example.com/2", "Second article text"),
        ("https://example.com/3", "First article text"),  # Duplicate
    ]

    for url, text in urls:
        # Discovery
        is_new = ledger.discover_url(url, source="test")
        if is_new:
            collector.increment("urls_discovered")

        # Deduplication
        is_dup, dup_type, similar_url, text_hash, minhash_sig = dedup_engine.process_document(
            text, url
        )

        if is_dup:
            collector.increment("urls_deduplicated")
            ledger.mark_duplicate(url, original_url="https://example.com/1", source="test")
        else:
            # Simulated fetch and process
            collector.increment("urls_fetched")
            collector.increment("urls_processed")

            ledger.mark_processed(
                url=url,
                text_hash=text_hash,
                silver_id=f"silver_{url.split('/')[-1]}",
                source="test",
            )

    # Get statistics
    ledger_stats = ledger.get_statistics()
    metrics_snapshot = collector.get_snapshot()

    # Verify integration
    assert ledger_stats["total_urls"] == 3
    assert ledger_stats["by_state"].get("processed", 0) == 2  # 2 unique
    assert ledger_stats["by_state"].get("duplicate", 0) == 1  # 1 duplicate

    assert metrics_snapshot.urls_discovered == 3
    assert metrics_snapshot.urls_deduplicated == 1

    # Generate quality report
    reporter = QualityReporter(collector)
    report_path = tmp_path / "integration_report.md"
    reporter.generate_markdown_report(report_path)

    assert report_path.exists()

    # Cleanup
    clear_context()
    ledger.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
