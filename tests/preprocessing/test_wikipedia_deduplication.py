"""
Unit tests for Wikipedia two-level deduplication.

Tests both:
- Level 1: Dump-level deduplication (HTTP conditional requests)
- Level 2: Article-level deduplication (URL filtering)
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest
import requests

from somali_dialect_classifier.preprocessing.crawl_ledger import (
    CrawlLedger,
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
def mock_processor(temp_ledger):
    """Create Wikipedia processor with mocked dependencies."""
    with patch(
        "somali_dialect_classifier.preprocessing.wikipedia_somali_processor.get_ledger"
    ) as mock_get_ledger:
        mock_get_ledger.return_value = temp_ledger

        with patch(
            "somali_dialect_classifier.preprocessing.wikipedia_somali_processor.get_config"
        ) as mock_config:
            # Mock config to avoid file system dependencies
            config = Mock()
            config.data.raw_dir = Path(tempfile.gettempdir()) / "test_raw"
            config.data.staging_dir = Path(tempfile.gettempdir()) / "test_staging"
            config.data.processed_dir = Path(tempfile.gettempdir()) / "test_processed"
            mock_config.return_value = config

            processor = WikipediaSomaliProcessor()
            processor.ledger = temp_ledger

            # Mock metrics to avoid file system dependencies
            processor.metrics = Mock()
            processor.metrics.increment = Mock()
            processor.metrics.add_custom_metric = Mock()

            yield processor


class TestFilterAlreadyProcessed:
    """Test _filter_already_processed method."""

    def test_all_articles_new(self, mock_processor):
        """Test filtering when all articles are new."""
        articles = [
            {"url": "https://so.wikipedia.org/wiki/Article1", "title": "A1", "text": "Text 1"},
            {"url": "https://so.wikipedia.org/wiki/Article2", "title": "A2", "text": "Text 2"},
            {"url": "https://so.wikipedia.org/wiki/Article3", "title": "A3", "text": "Text 3"},
        ]

        filtered = mock_processor._filter_already_processed(articles)

        assert len(filtered) == 3
        assert filtered == articles
        # Should not increment skip counter
        mock_processor.metrics.increment.assert_not_called()

    def test_all_articles_already_processed(self, mock_processor, temp_ledger):
        """Test filtering when all articles already processed."""
        articles = [
            {"url": "https://so.wikipedia.org/wiki/Article1", "title": "A1", "text": "Text 1"},
            {"url": "https://so.wikipedia.org/wiki/Article2", "title": "A2", "text": "Text 2"},
        ]

        # Mark all articles as processed in ledger
        for article in articles:
            temp_ledger.discover_url(article["url"], "wikipedia")
            temp_ledger.mark_processed(
                url=article["url"],
                text_hash=f"hash_{article['title']}",
                silver_id=f"silver_{article['title']}",
                source="wikipedia",
            )

        filtered = mock_processor._filter_already_processed(articles)

        assert len(filtered) == 0
        # Should increment skip counter for each skipped article
        assert mock_processor.metrics.increment.call_count == 2

    def test_mixed_new_and_processed_articles(self, mock_processor, temp_ledger):
        """Test filtering with mix of new and processed articles."""
        articles = [
            {"url": "https://so.wikipedia.org/wiki/Article1", "title": "A1", "text": "Text 1"},
            {"url": "https://so.wikipedia.org/wiki/Article2", "title": "A2", "text": "Text 2"},
            {"url": "https://so.wikipedia.org/wiki/Article3", "title": "A3", "text": "Text 3"},
        ]

        # Mark only first article as processed
        temp_ledger.discover_url(articles[0]["url"], "wikipedia")
        temp_ledger.mark_processed(
            url=articles[0]["url"], text_hash="hash_A1", silver_id="silver_A1", source="wikipedia"
        )

        filtered = mock_processor._filter_already_processed(articles)

        assert len(filtered) == 2
        assert filtered[0]["url"] == "https://so.wikipedia.org/wiki/Article2"
        assert filtered[1]["url"] == "https://so.wikipedia.org/wiki/Article3"
        # Should increment skip counter once
        assert mock_processor.metrics.increment.call_count == 1

    def test_handles_missing_url(self, mock_processor, caplog):
        """Test graceful handling of articles with missing URL."""
        articles = [
            {"url": "https://so.wikipedia.org/wiki/Article1", "title": "A1", "text": "Text 1"},
            {"title": "A2", "text": "Text 2"},  # Missing URL
            {"url": "https://so.wikipedia.org/wiki/Article3", "title": "A3", "text": "Text 3"},
        ]

        filtered = mock_processor._filter_already_processed(articles)

        # Should skip article with missing URL
        assert len(filtered) == 2
        assert "article missing url" in caplog.text.lower()

    def test_handles_ledger_query_error(self, mock_processor, caplog):
        """Test graceful degradation when ledger query fails."""
        articles = [
            {"url": "https://so.wikipedia.org/wiki/Article1", "title": "A1", "text": "Text 1"},
        ]

        # Mock ledger to raise exception
        mock_processor.ledger.get_processed_urls = Mock(side_effect=Exception("DB error"))

        # Should not crash, should process all articles
        filtered = mock_processor._filter_already_processed(articles)

        assert len(filtered) == 1
        assert "Failed to load processed URLs" in caplog.text

    def test_source_isolation(self, mock_processor, temp_ledger):
        """Test that only Wikipedia URLs are considered."""
        articles = [
            {"url": "https://so.wikipedia.org/wiki/Article1", "title": "A1", "text": "Text 1"},
            {"url": "https://so.wikipedia.org/wiki/Article2", "title": "A2", "text": "Text 2"},
        ]

        # Mark articles as processed for DIFFERENT source
        for article in articles:
            temp_ledger.discover_url(article["url"], "bbc")
            temp_ledger.mark_processed(
                url=article["url"],
                text_hash=f"hash_{article['title']}",
                silver_id=f"silver_{article['title']}",
                source="bbc",
            )

        # Should NOT filter out articles (different source)
        filtered = mock_processor._filter_already_processed(articles)

        assert len(filtered) == 2

    def test_large_article_set_performance(self, mock_processor, temp_ledger):
        """Test performance with large number of articles."""
        # Create 1000 articles
        articles = [
            {
                "url": f"https://so.wikipedia.org/wiki/Article{i}",
                "title": f"A{i}",
                "text": f"Text {i}",
            }
            for i in range(1000)
        ]

        # Mark half as processed
        for i in range(0, 1000, 2):
            temp_ledger.discover_url(articles[i]["url"], "wikipedia")
            temp_ledger.mark_processed(
                url=articles[i]["url"],
                text_hash=f"hash_{i}",
                silver_id=f"silver_{i}",
                source="wikipedia",
            )

        filtered = mock_processor._filter_already_processed(articles)

        # Should have 500 new articles
        assert len(filtered) == 500
        # Should have skipped 500 articles
        assert mock_processor.metrics.increment.call_count == 500


class TestLedgerGetLastSuccessfulRun:
    """Test get_last_successful_run method."""

    def test_returns_none_for_new_source(self, temp_ledger):
        """Test returns None when source never run."""
        result = temp_ledger.get_last_successful_run("never-run-source")
        assert result is None

    def test_returns_timestamp_after_processing(self, temp_ledger):
        """Test returns correct timestamp after processing."""
        datetime.now(timezone.utc)

        url = "https://example.com/test"
        temp_ledger.discover_url(url, "test-source")
        temp_ledger.mark_processed(
            url=url, text_hash="hash123", silver_id="silver_001", source="test-source"
        )

        result = temp_ledger.get_last_successful_run("test-source")

        assert result is not None
        assert isinstance(result, datetime)
        # Should be very recent (within last minute)
        time_diff = (datetime.now(timezone.utc) - result).total_seconds()
        assert time_diff < 60

    def test_returns_most_recent_timestamp(self, temp_ledger):
        """Test returns most recent timestamp when multiple URLs processed."""
        import time

        source = "test-source"

        # Process first URL
        url1 = "https://example.com/test1"
        temp_ledger.discover_url(url1, source)
        temp_ledger.mark_processed(
            url=url1, text_hash="hash1", silver_id="silver_001", source=source
        )

        first_time = temp_ledger.get_last_successful_run(source)

        # Wait a bit
        time.sleep(0.2)

        # Process second URL
        url2 = "https://example.com/test2"
        temp_ledger.discover_url(url2, source)
        temp_ledger.mark_processed(
            url=url2, text_hash="hash2", silver_id="silver_002", source=source
        )

        second_time = temp_ledger.get_last_successful_run(source)

        # Second timestamp should be more recent
        assert second_time > first_time

    def test_ignores_non_processed_states(self, temp_ledger):
        """Test that only PROCESSED state is considered."""
        source = "test-source"

        # Add URLs in various states
        url_failed = "https://example.com/failed"
        temp_ledger.discover_url(url_failed, source)
        temp_ledger.mark_failed(url_failed, "Error occurred")

        url_duplicate = "https://example.com/duplicate"
        temp_ledger.discover_url(url_duplicate, source)
        temp_ledger.mark_duplicate(url_duplicate, "https://example.com/original", source=source)

        # Should return None because no PROCESSED records
        result = temp_ledger.get_last_successful_run(source)
        assert result is None


class TestLedgerGetFirstSuccessfulRun:
    """Test get_first_successful_run method."""

    def test_returns_none_for_new_source(self, temp_ledger):
        """Test returns None when source never run."""
        result = temp_ledger.get_first_successful_run("never-run-source")
        assert result is None

    def test_returns_first_timestamp(self, temp_ledger):
        """Test returns first timestamp when multiple URLs processed."""
        import time

        source = "test-source"

        # Process first URL
        url1 = "https://example.com/test1"
        temp_ledger.discover_url(url1, source)
        temp_ledger.mark_processed(
            url=url1, text_hash="hash1", silver_id="silver_001", source=source
        )

        first_time = temp_ledger.get_first_successful_run(source)

        # Wait a bit
        time.sleep(0.2)

        # Process second URL
        url2 = "https://example.com/test2"
        temp_ledger.discover_url(url2, source)
        temp_ledger.mark_processed(
            url=url2, text_hash="hash2", silver_id="silver_002", source=source
        )

        second_time = temp_ledger.get_first_successful_run(source)

        # First time should remain the same
        assert second_time == first_time

    def test_ignores_failed_states(self, temp_ledger):
        """Test that only PROCESSED state is considered."""
        source = "test-source"

        # Add failed records
        url_failed = "https://example.com/failed"
        temp_ledger.discover_url(url_failed, source)
        temp_ledger.mark_failed(url_failed, "Error")

        # Should return None
        result = temp_ledger.get_first_successful_run(source)
        assert result is None


class TestWikipediaIntegrationScenarios:
    """Integration tests for Wikipedia deduplication scenarios."""

    def test_first_run_processes_all_articles(self, mock_processor):
        """Test that first run processes all articles."""
        articles = [
            {
                "url": f"https://so.wikipedia.org/wiki/Article{i}",
                "title": f"A{i}",
                "text": f"Text {i}",
            }
            for i in range(100)
        ]

        filtered = mock_processor._filter_already_processed(articles)

        # First run should process all articles
        assert len(filtered) == 100

    def test_second_run_skips_all_articles(self, mock_processor, temp_ledger):
        """Test that second run skips all previously processed articles."""
        articles = [
            {
                "url": f"https://so.wikipedia.org/wiki/Article{i}",
                "title": f"A{i}",
                "text": f"Text {i}",
            }
            for i in range(100)
        ]

        # First run: process all
        filtered_first = mock_processor._filter_already_processed(articles)
        assert len(filtered_first) == 100

        # Mark all as processed
        for article in articles:
            temp_ledger.discover_url(article["url"], "wikipedia")
            temp_ledger.mark_processed(
                url=article["url"],
                text_hash=f"hash_{article['title']}",
                silver_id=f"silver_{article['title']}",
                source="wikipedia",
            )

        # Reset metrics mock
        mock_processor.metrics.increment.reset_mock()

        # Second run: skip all
        filtered_second = mock_processor._filter_already_processed(articles)
        assert len(filtered_second) == 0
        assert mock_processor.metrics.increment.call_count == 100

    def test_incremental_processing_only_new_articles(self, mock_processor, temp_ledger):
        """Test that only new articles are processed in incremental runs."""
        # First batch of articles
        initial_articles = [
            {
                "url": f"https://so.wikipedia.org/wiki/Article{i}",
                "title": f"A{i}",
                "text": f"Text {i}",
            }
            for i in range(100)
        ]

        # Mark as processed
        for article in initial_articles:
            temp_ledger.discover_url(article["url"], "wikipedia")
            temp_ledger.mark_processed(
                url=article["url"],
                text_hash=f"hash_{article['title']}",
                silver_id=f"silver_{article['title']}",
                source="wikipedia",
            )

        # New batch with overlap
        new_articles = [
            {
                "url": f"https://so.wikipedia.org/wiki/Article{i}",
                "title": f"A{i}",
                "text": f"Text {i}",
            }
            for i in range(90, 110)  # 90-99 are duplicates, 100-109 are new
        ]

        filtered = mock_processor._filter_already_processed(new_articles)

        # Should only have 10 new articles (100-109)
        assert len(filtered) == 10
        for article in filtered:
            article_num = int(article["url"].split("Article")[-1])
            assert article_num >= 100


class TestDumpLevelDeduplication:
    """Test dump-level deduplication with HTTP conditional requests."""

    def test_304_not_modified_skips_everything(self, mock_processor, temp_ledger):
        """Test that 304 response skips download, parse, and processing."""
        dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

        # Mark dump URL as already processed in ledger
        temp_ledger.discover_url(dump_url, "wikipedia")
        temp_ledger.mark_fetched(
            url=dump_url,
            http_status=200,
            etag="old-etag-12345",
            last_modified="Sat, 01 Nov 2025 22:07:38 GMT",
            content_length=1000000,
            source="wikipedia",
        )

        # Create mock session
        mock_session = Mock()
        mock_head_response = Mock()
        mock_head_response.status_code = 304
        mock_session.head.return_value = mock_head_response

        # Mock _get_http_session to return our mock session
        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            result = mock_processor.download()

            # Should return None (skip signal)
            assert result is None

            # Should have made HEAD request with conditional headers
            mock_session.head.assert_called_once()
            call_args = mock_session.head.call_args
            headers = call_args.kwargs.get("headers", call_args.args[1] if len(call_args.args) > 1 else {})
            assert "If-None-Match" in headers
            assert headers["If-None-Match"] == "old-etag-12345"

    def test_200_with_new_etag_downloads_dump(self, mock_processor, temp_ledger):
        """Test that 200 OK with different ETag downloads new dump."""
        dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

        # Mark dump URL as already fetched with old ETag
        temp_ledger.discover_url(dump_url, "wikipedia")
        temp_ledger.mark_fetched(
            url=dump_url,
            http_status=200,
            etag="old-etag",
            last_modified="Sat, 01 Nov 2025 22:07:38 GMT",
            source="wikipedia",
        )

        # Create mock session
        mock_session = Mock()

        # Mock HEAD returning 200 (dump changed)
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {
            "ETag": "new-etag-67890",
            "Last-Modified": "Sun, 02 Nov 2025 01:00:00 GMT",
        }
        mock_session.head.return_value = mock_head_response

        # Mock GET for actual download
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            "ETag": "new-etag-67890",
            "Last-Modified": "Sun, 02 Nov 2025 01:00:00 GMT",
            "Content-Length": "2000000",
        }
        mock_get_response.iter_content = Mock(return_value=[b"test data chunk"])
        mock_session.get.return_value = mock_get_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            result = mock_processor.download()

            # Should download and return path
            assert result is not None
            assert result.name.endswith(".bz2")

            # Should have made GET request
            mock_session.get.assert_called()

    def test_first_run_downloads_without_conditional_request(self, mock_processor, temp_ledger):
        """Test that first run (URL not in ledger) downloads normally."""
        # Don't add dump URL to ledger (first run)

        # Create mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "ETag": "first-etag-abcdef",
            "Last-Modified": "Mon, 03 Nov 2025 10:00:00 GMT",
            "Content-Length": "1500000",
        }
        mock_response.iter_content = Mock(return_value=[b"first download data"])
        mock_session.get.return_value = mock_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            result = mock_processor.download()

            # Should download
            assert result is not None

            # Should NOT make conditional HEAD request (first run)
            mock_session.head.assert_not_called()

            # Should have made GET request
            mock_session.get.assert_called()

    def test_conditional_request_headers_sent_correctly(self, mock_processor, temp_ledger):
        """Test that conditional headers are sent correctly in HEAD request."""
        dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

        # Mark dump with both ETag and Last-Modified
        temp_ledger.discover_url(dump_url, "wikipedia")
        temp_ledger.mark_fetched(
            url=dump_url,
            http_status=200,
            etag='"etag-value-123"',
            last_modified="Wed, 05 Nov 2025 14:30:00 GMT",
            source="wikipedia",
        )

        # Create mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 304
        mock_session.head.return_value = mock_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            mock_processor.download()

            # Verify headers
            call_args = mock_session.head.call_args
            headers = call_args.kwargs.get("headers", call_args.args[1] if len(call_args.args) > 1 else {})

            assert "If-None-Match" in headers
            assert headers["If-None-Match"] == '"etag-value-123"'
            assert "If-Modified-Since" in headers
            assert headers["If-Modified-Since"] == "Wed, 05 Nov 2025 14:30:00 GMT"

    def test_head_request_failure_proceeds_with_download(self, mock_processor, temp_ledger):
        """Test that HEAD request failure gracefully falls back to download."""
        dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

        temp_ledger.discover_url(dump_url, "wikipedia")
        temp_ledger.mark_fetched(
            url=dump_url, http_status=200, etag="old-etag", source="wikipedia"
        )

        # Create mock session
        mock_session = Mock()
        # Mock HEAD to raise exception
        mock_session.head.side_effect = requests.RequestException("Connection timeout")

        # Mock GET for fallback download
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {"Content-Length": "1000000", "ETag": "new-etag"}
        mock_get_response.iter_content = Mock(return_value=[b"fallback data"])
        mock_session.get.return_value = mock_get_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            result = mock_processor.download()

            # Should proceed with download despite HEAD failure
            assert result is not None
            mock_session.get.assert_called()

    def test_metrics_tracked_for_304_skip(self, mock_processor, temp_ledger):
        """Test that metrics are tracked when dump is skipped (304)."""
        dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

        temp_ledger.discover_url(dump_url, "wikipedia")
        temp_ledger.mark_fetched(
            url=dump_url, http_status=200, etag="current-etag", source="wikipedia"
        )

        # Create mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 304
        mock_session.head.return_value = mock_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            mock_processor.download()

            # Should have incremented skip metric
            mock_processor.metrics.increment.assert_any_call("dumps_skipped_not_modified")

    def test_etag_stored_in_ledger_after_download(self, mock_processor, temp_ledger):
        """Test that ETag and Last-Modified are stored in ledger after download."""
        # Create mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "ETag": "new-etag-xyz",
            "Last-Modified": "Thu, 06 Nov 2025 09:00:00 GMT",
            "Content-Length": "3000000",
        }
        mock_response.iter_content = Mock(return_value=[b"new dump data"])
        mock_session.get.return_value = mock_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            mock_processor.download()

            # Verify ledger was updated with HTTP metadata
            dump_url = mock_processor.dump_url
            state = temp_ledger.backend.get_url_state(dump_url)

            assert state is not None
            assert state["etag"] == "new-etag-xyz"
            assert state["last_modified"] == "Thu, 06 Nov 2025 09:00:00 GMT"


class TestRunMethodIntegration:
    """Test run() method with two-level deduplication."""

    def test_run_with_304_returns_none(self, mock_processor, temp_ledger):
        """Test that run() returns None when dump is unchanged (304)."""
        dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

        temp_ledger.discover_url(dump_url, "wikipedia")
        temp_ledger.mark_fetched(
            url=dump_url, http_status=200, etag="current-etag", source="wikipedia"
        )

        # Create mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 304
        mock_session.head.return_value = mock_response

        with patch.object(mock_processor, "_get_http_session", return_value=mock_session):
            result = mock_processor.run()

            # Should return None (nothing to process)
            assert result is None

    def test_run_with_no_new_articles_returns_none(self, mock_processor, temp_ledger):
        """Test that run() returns None when all articles already processed."""
        # Mock download to return a path
        with patch.object(mock_processor, "download", return_value=Path("/tmp/dump.xml.bz2")):
            # Mock extract to return None (no new articles)
            with patch.object(mock_processor, "extract", return_value=None):
                result = mock_processor.run()

                # Should return None (no new articles)
                assert result is None

    def test_run_with_new_articles_processes_successfully(self, mock_processor):
        """Test that run() processes new articles and returns silver path."""
        staging_file = Path("/tmp/staging.txt")
        silver_file = Path("/tmp/silver.parquet")

        # Mock download, extract, process
        with patch.object(mock_processor, "download", return_value=Path("/tmp/dump.xml.bz2")):
            with patch.object(mock_processor, "extract", return_value=staging_file):
                with patch.object(mock_processor, "process", return_value=silver_file):
                    result = mock_processor.run()

                    # Should return silver path
                    assert result == silver_file
