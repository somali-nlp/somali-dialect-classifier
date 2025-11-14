"""
Tests for incremental processing functionality.

Tests cover:
- First run vs subsequent run behavior
- Timestamp-based filtering (Wikipedia)
- Corpus ID-based filtering (Språkbanken)
- Fail-safe handling (invalid timestamps, missing data)
- Metrics tracking
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    SprakbankenSomaliProcessor,
)
from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import (
    WikipediaSomaliProcessor,
)


@pytest.fixture
def temp_ledger():
    """Create temporary ledger for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        ledger = CrawlLedger(db_path=db_path)
        yield ledger
        ledger.close()


@pytest.fixture
def mock_wikipedia_processor():
    """Create mock Wikipedia processor."""
    with patch("somali_dialect_classifier.preprocessing.wikipedia_somali_processor.get_config"):
        processor = WikipediaSomaliProcessor(force=False)
        return processor


@pytest.fixture
def mock_sprakbanken_processor():
    """Create mock Språkbanken processor."""
    with patch("somali_dialect_classifier.preprocessing.sprakbanken_somali_processor.get_config"):
        processor = SprakbankenSomaliProcessor(corpus_id="somali-cilmi", force=False)
        return processor


class TestLedgerIncrementalMethods:
    """Test ledger methods for incremental processing."""

    def test_get_last_processing_time_first_run(self, temp_ledger):
        """Test get_last_processing_time returns None on first run."""
        last_time = temp_ledger.get_last_processing_time("wikipedia")
        assert last_time is None

    def test_get_last_processing_time_after_processing(self, temp_ledger):
        """Test get_last_processing_time returns timestamp after processing."""
        # Add a processed URL
        url = "https://so.wikipedia.org/wiki/Test"
        temp_ledger.discover_url(url, "wikipedia")
        temp_ledger.mark_processed(
            url=url, text_hash="abc123", silver_id="silver_001", source="wikipedia"
        )

        # Get last processing time
        last_time = temp_ledger.get_last_processing_time("wikipedia")

        assert last_time is not None
        assert isinstance(last_time, datetime)
        # Should be recent (within last minute)
        assert datetime.now(timezone.utc) - last_time < timedelta(minutes=1)

    def test_get_processed_urls(self, temp_ledger):
        """Test get_processed_urls returns all processed URLs."""
        # Add multiple processed URLs
        urls = [
            "https://so.wikipedia.org/wiki/Test1",
            "https://so.wikipedia.org/wiki/Test2",
            "https://so.wikipedia.org/wiki/Test3",
        ]

        for i, url in enumerate(urls):
            temp_ledger.discover_url(url, "wikipedia")
            temp_ledger.mark_processed(
                url=url, text_hash=f"hash{i}", silver_id=f"silver_{i}", source="wikipedia"
            )

        # Get processed URLs
        processed = temp_ledger.get_processed_urls("wikipedia")

        assert len(processed) == 3
        processed_urls = [r["url"] for r in processed]
        for url in urls:
            assert url in processed_urls


class TestWikipediaIncrementalProcessing:
    """Test Wikipedia incremental processing."""

    def test_first_run_processes_all(self, mock_wikipedia_processor, temp_ledger):
        """Test that first run processes all articles."""
        mock_wikipedia_processor.ledger = temp_ledger

        articles = [
            {"title": "Article1", "text": "Content1", "timestamp": "2024-01-01T00:00:00Z"},
            {"title": "Article2", "text": "Content2", "timestamp": "2024-01-02T00:00:00Z"},
            {"title": "Article3", "text": "Content3", "timestamp": "2024-01-03T00:00:00Z"},
        ]

        filtered, stats = mock_wikipedia_processor._filter_new_articles(articles)

        assert len(filtered) == 3
        assert stats["total"] == 3
        assert stats["new"] == 3
        assert stats["skipped"] == 0
        assert stats["last_processing_time"] is None

    def test_subsequent_run_filters_old(self, mock_wikipedia_processor, temp_ledger):
        """Test that subsequent runs filter old articles."""
        import time

        mock_wikipedia_processor.ledger = temp_ledger
        source = mock_wikipedia_processor.source

        # Simulate previous processing
        url = "https://so.wikipedia.org/wiki/OldArticle"
        temp_ledger.discover_url(url, source)
        temp_ledger.mark_processed(
            url=url, text_hash="old123", silver_id="silver_old", source=source
        )

        # Small delay to ensure processing time has passed
        time.sleep(0.1)

        # Create articles with varying timestamps relative to last processing
        last_processing_time = temp_ledger.get_last_processing_time(source)
        assert last_processing_time is not None

        # Create timestamps: one before, two after last processing
        articles = [
            {
                "title": "OldArticle",
                "text": "Old content",
                "timestamp": (last_processing_time - timedelta(days=1))
                .isoformat()
                .replace("+00:00", "Z"),
            },
            {
                "title": "RecentArticle",
                "text": "Recent content",
                "timestamp": (last_processing_time + timedelta(hours=1))
                .isoformat()
                .replace("+00:00", "Z"),
            },
            {
                "title": "NewArticle",
                "text": "New content",
                "timestamp": (last_processing_time + timedelta(hours=2))
                .isoformat()
                .replace("+00:00", "Z"),
            },
        ]

        filtered, stats = mock_wikipedia_processor._filter_new_articles(articles)

        # Should filter out old article, keep recent ones
        assert len(filtered) == 2
        assert stats["total"] == 3
        assert stats["new"] == 2
        assert stats["skipped"] == 1

    def test_no_new_records_skips_all(self, mock_wikipedia_processor, temp_ledger):
        """Test that run with no new articles skips all processing."""
        mock_wikipedia_processor.ledger = temp_ledger
        source = mock_wikipedia_processor.source

        # Simulate recent processing (1 hour ago)
        url = "https://so.wikipedia.org/wiki/RecentArticle"
        temp_ledger.discover_url(url, source)
        temp_ledger.mark_processed(
            url=url, text_hash="recent123", silver_id="silver_recent", source=source
        )

        # Create articles all older than last processing
        past_time = datetime.now(timezone.utc) - timedelta(days=1)
        articles = [
            {
                "title": "Article1",
                "text": "Content1",
                "timestamp": past_time.isoformat().replace("+00:00", "Z"),
            },
            {
                "title": "Article2",
                "text": "Content2",
                "timestamp": past_time.isoformat().replace("+00:00", "Z"),
            },
        ]

        filtered, stats = mock_wikipedia_processor._filter_new_articles(articles)

        assert len(filtered) == 0
        assert stats["new"] == 0
        assert stats["skipped"] == 2

    def test_invalid_timestamps_processed(self, mock_wikipedia_processor, temp_ledger):
        """Test that articles with invalid timestamps are processed (fail-safe)."""
        mock_wikipedia_processor.ledger = temp_ledger
        source = mock_wikipedia_processor.source

        # Simulate previous processing
        url = "https://so.wikipedia.org/wiki/OldArticle"
        temp_ledger.discover_url(url, source)
        temp_ledger.mark_processed(
            url=url, text_hash="old123", silver_id="silver_old", source=source
        )

        # Create articles with invalid/missing timestamps
        articles = [
            {"title": "NoTimestamp", "text": "Content1"},  # Missing timestamp
            {
                "title": "InvalidTimestamp",
                "text": "Content2",
                "timestamp": "invalid-date",
            },  # Invalid format
            {
                "title": "ValidNew",
                "text": "Content3",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        ]

        filtered, stats = mock_wikipedia_processor._filter_new_articles(articles)

        # All should be processed (fail-safe for invalid data)
        assert len(filtered) == 3
        assert stats["new"] == 3


class TestSprakbankenIncrementalProcessing:
    """Test Språkbanken incremental processing."""

    def test_extract_corpus_id_from_korp_url(self, mock_sprakbanken_processor):
        """Test corpus ID extraction from Korp URL."""
        url = "https://spraakbanken.gu.se/korp/?mode=somali#?corpus=somali-cilmi"
        corpus_id = mock_sprakbanken_processor._extract_corpus_id_from_url(url)
        assert corpus_id == "somali-cilmi"

    def test_extract_corpus_id_from_download_url(self, mock_sprakbanken_processor):
        """Test corpus ID extraction from download URL."""
        url = "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cilmi.xml.bz2"
        corpus_id = mock_sprakbanken_processor._extract_corpus_id_from_url(url)
        assert corpus_id == "somali-cilmi"

    def test_first_run_processes_all_corpora(self, mock_sprakbanken_processor, temp_ledger):
        """Test that first run processes all corpora."""
        mock_sprakbanken_processor.ledger = temp_ledger

        corpus_urls = [
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cilmi.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cb.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-bbc.xml.bz2",
        ]

        filtered, stats = mock_sprakbanken_processor._filter_new_corpora(corpus_urls)

        assert len(filtered) == 3
        assert stats["total"] == 3
        assert stats["new"] == 3
        assert stats["skipped"] == 0

    def test_subsequent_run_filters_processed_corpora(
        self, mock_sprakbanken_processor, temp_ledger
    ):
        """Test that subsequent runs filter already-processed corpora."""
        mock_sprakbanken_processor.ledger = temp_ledger
        source = mock_sprakbanken_processor.source

        # Simulate previous processing of one corpus
        url = "https://spraakbanken.gu.se/korp/?mode=somali#?corpus=somali-cilmi"
        temp_ledger.discover_url(url, source)
        temp_ledger.mark_processed(
            url=url, text_hash="cilmi123", silver_id="silver_cilmi", source=source
        )

        corpus_urls = [
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cilmi.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cb.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-bbc.xml.bz2",
        ]

        filtered, stats = mock_sprakbanken_processor._filter_new_corpora(corpus_urls)

        # Should skip somali-cilmi, process other two
        assert len(filtered) == 2
        assert stats["total"] == 3
        assert stats["new"] == 2
        assert stats["skipped"] == 1
        assert "somali-cilmi" in stats["processed_corpus_ids"]

    def test_all_corpora_processed_skips_all(self, mock_sprakbanken_processor, temp_ledger):
        """Test that when all corpora are processed, none are returned."""
        mock_sprakbanken_processor.ledger = temp_ledger
        source = mock_sprakbanken_processor.source

        # Simulate processing of all corpora
        for corpus_id in ["somali-cilmi", "somali-cb", "somali-bbc"]:
            url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}"
            temp_ledger.discover_url(url, source)
            temp_ledger.mark_processed(
                url=url,
                text_hash=f"{corpus_id}_hash",
                silver_id=f"silver_{corpus_id}",
                source=source,
            )

        corpus_urls = [
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cilmi.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cb.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-bbc.xml.bz2",
        ]

        filtered, stats = mock_sprakbanken_processor._filter_new_corpora(corpus_urls)

        assert len(filtered) == 0
        assert stats["new"] == 0
        assert stats["skipped"] == 3


class TestIncrementalProcessingMetrics:
    """Test metrics tracking for incremental processing."""

    def test_wikipedia_incremental_metrics(self, mock_wikipedia_processor, temp_ledger):
        """Test that Wikipedia incremental filtering produces correct metrics."""
        mock_wikipedia_processor.ledger = temp_ledger
        source = mock_wikipedia_processor.source

        # Simulate previous processing
        url = "https://so.wikipedia.org/wiki/OldArticle"
        temp_ledger.discover_url(url, source)
        temp_ledger.mark_processed(
            url=url, text_hash="old123", silver_id="silver_old", source=source
        )

        # Create mixed articles
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=1)
        articles = [
            {
                "title": "Old1",
                "text": "Content",
                "timestamp": past.isoformat().replace("+00:00", "Z"),
            },
            {
                "title": "Old2",
                "text": "Content",
                "timestamp": past.isoformat().replace("+00:00", "Z"),
            },
            {
                "title": "New",
                "text": "Content",
                "timestamp": now.isoformat().replace("+00:00", "Z"),
            },
        ]

        filtered, stats = mock_wikipedia_processor._filter_new_articles(articles)

        # Verify metrics
        assert stats["total"] == 3
        assert stats["new"] == 1
        assert stats["skipped"] == 2
        assert stats["last_processing_time"] is not None

        # Calculate efficiency gain
        efficiency_gain = (stats["skipped"] / stats["total"]) * 100
        assert efficiency_gain > 60  # Should be ~66%

    def test_sprakbanken_incremental_metrics(self, mock_sprakbanken_processor, temp_ledger):
        """Test that Språkbanken incremental filtering produces correct metrics."""
        mock_sprakbanken_processor.ledger = temp_ledger
        source = mock_sprakbanken_processor.source

        # Simulate processing 2 out of 3 corpora
        for corpus_id in ["somali-cilmi", "somali-cb"]:
            url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}"
            temp_ledger.discover_url(url, source)
            temp_ledger.mark_processed(
                url=url,
                text_hash=f"{corpus_id}_hash",
                silver_id=f"silver_{corpus_id}",
                source=source,
            )

        corpus_urls = [
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cilmi.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-cb.xml.bz2",
            "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-bbc.xml.bz2",
        ]

        filtered, stats = mock_sprakbanken_processor._filter_new_corpora(corpus_urls)

        # Verify metrics
        assert stats["total"] == 3
        assert stats["new"] == 1
        assert stats["skipped"] == 2

        # Calculate efficiency gain
        efficiency_gain = (stats["skipped"] / stats["total"]) * 100
        assert efficiency_gain > 60  # Should be ~66%


class TestFailSafeBehavior:
    """Test fail-safe behavior when ledger is unavailable."""

    def test_ledger_unavailable_processes_all(self, mock_wikipedia_processor):
        """Test that when ledger fails, all articles are processed."""
        # Set ledger to None to simulate failure
        mock_wikipedia_processor.ledger = None

        # Should not raise error, should process all
        last_time = mock_wikipedia_processor._get_last_processing_time()
        assert last_time is None

    def test_query_error_returns_empty_set(self, mock_sprakbanken_processor):
        """Test that query errors return empty set (fail-safe)."""
        # Create a mock ledger that raises exception
        mock_ledger = MagicMock()
        mock_ledger.get_processed_urls.side_effect = Exception("Database error")
        mock_sprakbanken_processor.ledger = mock_ledger

        # Should not raise error, should return empty set
        corpus_ids = mock_sprakbanken_processor._get_processed_corpus_ids()
        assert corpus_ids == set()
