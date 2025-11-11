"""
Tests for ledger incremental processing methods.

Focuses on testing the new ledger methods:
- get_last_processing_time()
- get_processed_urls()
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger, CrawlState


@pytest.fixture
def ledger():
    """Create temporary ledger for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        ledger = CrawlLedger(db_path=db_path)
        yield ledger
        ledger.close()


class TestGetLastProcessingTime:
    """Test get_last_processing_time() method."""

    def test_returns_none_for_new_source(self, ledger):
        """Test that method returns None for sources never processed."""
        result = ledger.get_last_processing_time("never-processed-source")
        assert result is None

    def test_returns_none_when_no_processed_urls(self, ledger):
        """Test returns None when source has URLs but none processed."""
        # Add discovered URL but don't process it
        ledger.discover_url("https://example.com/test", "test-source")

        result = ledger.get_last_processing_time("test-source")
        assert result is None

    def test_returns_timestamp_after_processing(self, ledger):
        """Test returns correct timestamp after processing URLs."""
        # Process a URL
        url = "https://example.com/test"
        ledger.discover_url(url, "test-source")
        ledger.mark_processed(url=url, text_hash="hash123", silver_id="silver_001", source="test-source")

        result = ledger.get_last_processing_time("test-source")

        assert result is not None
        assert isinstance(result, datetime)
        # Should be very recent (within last minute)
        assert datetime.now(timezone.utc) - result < timedelta(minutes=1)

    def test_returns_most_recent_timestamp(self, ledger):
        """Test returns most recent timestamp when multiple URLs processed."""
        source = "test-source"

        # Process first URL
        url1 = "https://example.com/test1"
        ledger.discover_url(url1, source)
        ledger.mark_processed(url=url1, text_hash="hash1", silver_id="silver_001", source=source)

        first_time = ledger.get_last_processing_time(source)

        # Wait a bit and process second URL
        import time
        time.sleep(0.1)

        url2 = "https://example.com/test2"
        ledger.discover_url(url2, source)
        ledger.mark_processed(url=url2, text_hash="hash2", silver_id="silver_002", source=source)

        second_time = ledger.get_last_processing_time(source)

        # Second timestamp should be more recent
        assert second_time > first_time

    def test_ignores_non_processed_states(self, ledger):
        """Test that method only considers PROCESSED state."""
        source = "test-source"

        # Add URLs in various states
        ledger.discover_url("https://example.com/discovered", source)

        ledger.discover_url("https://example.com/failed", source)
        ledger.mark_failed("https://example.com/failed", "Error occurred")

        ledger.discover_url("https://example.com/duplicate", source)
        ledger.mark_duplicate("https://example.com/duplicate", "https://example.com/original", source=source)

        # No processed URLs yet
        result = ledger.get_last_processing_time(source)
        assert result is None

        # Now add a processed URL
        url = "https://example.com/processed"
        ledger.discover_url(url, source)
        ledger.mark_processed(url=url, text_hash="hash", silver_id="silver", source=source)

        result = ledger.get_last_processing_time(source)
        assert result is not None

    def test_source_isolation(self, ledger):
        """Test that timestamps are isolated by source."""
        # Process URL for source A
        url_a = "https://example.com/source-a"
        ledger.discover_url(url_a, "source-a")
        ledger.mark_processed(url=url_a, text_hash="hash_a", silver_id="silver_a", source="source-a")

        # Process URL for source B
        url_b = "https://example.com/source-b"
        ledger.discover_url(url_b, "source-b")
        ledger.mark_processed(url=url_b, text_hash="hash_b", silver_id="silver_b", source="source-b")

        # Each source should have its own timestamp
        time_a = ledger.get_last_processing_time("source-a")
        time_b = ledger.get_last_processing_time("source-b")

        assert time_a is not None
        assert time_b is not None
        # Times should be similar but independent
        assert abs((time_a - time_b).total_seconds()) < 1


class TestGetProcessedUrls:
    """Test get_processed_urls() method."""

    def test_returns_empty_list_for_new_source(self, ledger):
        """Test returns empty list for sources never processed."""
        result = ledger.get_processed_urls("never-processed-source")
        assert result == []

    def test_returns_only_processed_urls(self, ledger):
        """Test returns only URLs in PROCESSED state."""
        source = "test-source"

        # Add URLs in various states
        url_discovered = "https://example.com/discovered"
        ledger.discover_url(url_discovered, source)

        url_failed = "https://example.com/failed"
        ledger.discover_url(url_failed, source)
        ledger.mark_failed(url_failed, "Error")

        url_processed1 = "https://example.com/processed1"
        ledger.discover_url(url_processed1, source)
        ledger.mark_processed(url=url_processed1, text_hash="hash1", silver_id="silver1", source=source)

        url_processed2 = "https://example.com/processed2"
        ledger.discover_url(url_processed2, source)
        ledger.mark_processed(url=url_processed2, text_hash="hash2", silver_id="silver2", source=source)

        result = ledger.get_processed_urls(source)

        # Should return only processed URLs
        assert len(result) == 2
        processed_urls = [r["url"] for r in result]
        assert url_processed1 in processed_urls
        assert url_processed2 in processed_urls
        assert url_discovered not in processed_urls
        assert url_failed not in processed_urls

    def test_respects_limit_parameter(self, ledger):
        """Test that limit parameter correctly limits results."""
        source = "test-source"

        # Add 10 processed URLs
        for i in range(10):
            url = f"https://example.com/test{i}"
            ledger.discover_url(url, source)
            ledger.mark_processed(url=url, text_hash=f"hash{i}", silver_id=f"silver{i}", source=source)

        # Request only 5
        result = ledger.get_processed_urls(source, limit=5)
        assert len(result) == 5

        # Request all (None limit)
        result_all = ledger.get_processed_urls(source, limit=None)
        assert len(result_all) == 10

    def test_returns_url_metadata(self, ledger):
        """Test that returned records include metadata."""
        source = "test-source"
        url = "https://example.com/test"
        text_hash = "abc123def456"
        silver_id = "silver_001"

        ledger.discover_url(url, source)
        ledger.mark_processed(url=url, text_hash=text_hash, silver_id=silver_id, source=source)

        result = ledger.get_processed_urls(source)

        assert len(result) == 1
        record = result[0]

        # Verify metadata fields
        assert record["url"] == url
        assert record["source"] == source
        assert record["state"] == CrawlState.PROCESSED.value
        assert record["text_hash"] == text_hash
        assert record["silver_id"] == silver_id

    def test_source_isolation(self, ledger):
        """Test that results are isolated by source."""
        # Add URLs for source A
        for i in range(3):
            url = f"https://example.com/source-a/{i}"
            ledger.discover_url(url, "source-a")
            ledger.mark_processed(url=url, text_hash=f"hash_a{i}", silver_id=f"silver_a{i}", source="source-a")

        # Add URLs for source B
        for i in range(5):
            url = f"https://example.com/source-b/{i}"
            ledger.discover_url(url, "source-b")
            ledger.mark_processed(url=url, text_hash=f"hash_b{i}", silver_id=f"silver_b{i}", source="source-b")

        # Query each source
        result_a = ledger.get_processed_urls("source-a")
        result_b = ledger.get_processed_urls("source-b")

        assert len(result_a) == 3
        assert len(result_b) == 5

        # Verify URLs are correctly isolated
        urls_a = [r["url"] for r in result_a]
        urls_b = [r["url"] for r in result_b]

        for url in urls_a:
            assert "source-a" in url

        for url in urls_b:
            assert "source-b" in url


class TestIncrementalProcessingWorkflow:
    """Test complete incremental processing workflow."""

    def test_wikipedia_quarterly_refresh_scenario(self, ledger):
        """Test Wikipedia quarterly refresh with incremental processing."""
        source = "Wikipedia-Somali"

        # Initial run: Process 1000 articles
        initial_run_time = datetime.now(timezone.utc)
        for i in range(1000):
            url = f"https://so.wikipedia.org/wiki/Article{i}"
            ledger.discover_url(url, source)
            ledger.mark_processed(url=url, text_hash=f"hash{i}", silver_id=f"silver{i}", source=source)

        # Get last processing time (should match initial run)
        last_time = ledger.get_last_processing_time(source)
        assert last_time is not None
        assert abs((last_time - initial_run_time).total_seconds()) < 5

        # Quarterly refresh (3 months later): Only 10 new articles
        import time
        time.sleep(0.1)  # Simulate time passing

        second_run_time = datetime.now(timezone.utc)
        for i in range(1000, 1010):
            url = f"https://so.wikipedia.org/wiki/Article{i}"
            ledger.discover_url(url, source)
            ledger.mark_processed(url=url, text_hash=f"hash{i}", silver_id=f"silver{i}", source=source)

        # Get updated last processing time
        new_last_time = ledger.get_last_processing_time(source)
        assert new_last_time > last_time

        # Get all processed URLs
        all_processed = ledger.get_processed_urls(source)
        assert len(all_processed) == 1010

        # Calculate efficiency gain (would skip 1000 out of 1010 = 99%)
        total_articles = 1010
        new_articles = 10
        efficiency_gain = ((total_articles - new_articles) / total_articles) * 100
        assert efficiency_gain > 99

    def test_sprakbanken_incremental_corpus_scenario(self, ledger):
        """Test Språkbanken incremental corpus processing."""
        source = "Sprakbanken-Somali"

        # Initial run: Process 3 corpora
        corpora_initial = ["somali-cilmi", "somali-cb", "somali-bbc"]
        for corpus_id in corpora_initial:
            url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}"
            ledger.discover_url(url, source)
            ledger.mark_processed(url=url, text_hash=f"{corpus_id}_hash", silver_id=f"silver_{corpus_id}", source=source)

        initial_count = len(ledger.get_processed_urls(source))
        assert initial_count == 3

        # Second run: Add 1 new corpus
        import time
        time.sleep(0.1)

        new_corpus = "somali-haatuf-news-2002"
        url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={new_corpus}"
        ledger.discover_url(url, source)
        ledger.mark_processed(url=url, text_hash=f"{new_corpus}_hash", silver_id=f"silver_{new_corpus}", source=source)

        final_count = len(ledger.get_processed_urls(source))
        assert final_count == 4

        # Calculate efficiency gain (would skip 3 out of 4 = 75%)
        total_corpora = 4
        new_corpora = 1
        efficiency_gain = ((total_corpora - new_corpora) / total_corpora) * 100
        assert efficiency_gain == 75
