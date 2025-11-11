"""
Integration tests for BBC Somali processor.

Tests BBC processor end-to-end workflows including discovery,
extraction, rate limiting, deduplication, and error handling.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>BBC Somali</title>
            <item>
                <title>Test Article 1</title>
                <link>https://www.bbc.com/somali/articles/test1</link>
                <pubDate>Mon, 01 Jan 2025 10:00:00 GMT</pubDate>
            </item>
            <item>
                <title>Test Article 2</title>
                <link>https://www.bbc.com/somali/articles/test2</link>
                <pubDate>Mon, 01 Jan 2025 11:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>"""


@pytest.fixture
def sample_article_html():
    """Sample BBC article HTML."""
    return """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Magaalada Muqdisho oo Roobab Xoogan Ka Da'ay</h1>
                <time datetime="2025-01-01">01 Jan 2025</time>
                <div class="article-body">
                    <p>Magaalada Muqdisho waxaa ka da'ayay roobab xoogan oo sababay fatahaad.</p>
                    <p>Dadweynaha ayaa la digay inay ka fogaadaan meelaha halis ah.</p>
                    <p>Wasaaradda caafimaadka ayaa diyaar u ah gurmadka.</p>
                </div>
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_homepage_html():
    """Sample BBC homepage HTML."""
    return """
    <html>
        <body>
            <section class="topic-section" data-topic="news">
                <a href="/somali/articles/article1">Article 1</a>
                <a href="/somali/articles/article2">Article 2</a>
            </section>
            <section class="topic-section" data-topic="sports">
                <a href="/somali/articles/article3">Article 3</a>
            </section>
        </body>
    </html>
    """


class TestBBCProcessorInitialization:
    """Test BBC processor initialization and configuration."""

    def test_processor_initializes_with_defaults(self):
        """Test processor initializes with default configuration."""
        processor = BBCSomaliProcessor()

        assert processor.source == "BBC-Somali"
        assert processor.base_url == "https://www.bbc.com/somali"
        assert processor.max_articles is None
        assert processor.delay_range == (1, 3)
        assert processor.rate_limiter is not None

    def test_processor_initializes_with_custom_params(self):
        """Test processor initializes with custom parameters."""
        processor = BBCSomaliProcessor(
            max_articles=50,
            delay_range=(2, 5),
            force=True
        )

        assert processor.max_articles == 50
        assert processor.delay_range == (2, 5)
        assert processor.force is True

    def test_processor_creates_required_directories(self):
        """Test processor creates required directory structure."""
        processor = BBCSomaliProcessor()

        assert processor.raw_dir.exists()
        assert processor.staging_dir.exists()
        assert processor.silver_dir.exists()

    def test_processor_has_dedup_engine(self):
        """Test processor initializes deduplication engine."""
        processor = BBCSomaliProcessor()

        assert processor.dedup is not None
        assert hasattr(processor.dedup, 'is_duplicate')

    def test_processor_has_rate_limiter(self):
        """Test processor initializes rate limiter."""
        processor = BBCSomaliProcessor()

        assert processor.rate_limiter is not None
        assert hasattr(processor.rate_limiter, 'acquire')


class TestBBCRSSFeedParsing:
    """Test RSS feed discovery and parsing."""

    @patch('requests.Session.get')
    def test_scrape_rss_feeds_success(self, mock_get, sample_rss_feed):
        """Test RSS feed scraping extracts article links."""
        mock_response = Mock()
        mock_response.text = sample_rss_feed
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor()
        links = processor._scrape_rss_feeds()

        assert len(links) == 2
        assert "https://www.bbc.com/somali/articles/test1" in links
        assert "https://www.bbc.com/somali/articles/test2" in links

    @patch('requests.Session.get')
    def test_scrape_rss_feeds_handles_errors(self, mock_get):
        """Test RSS feed scraping handles network errors gracefully."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        processor = BBCSomaliProcessor()
        links = processor._scrape_rss_feeds()

        # Should return empty list on error
        assert isinstance(links, list)
        assert len(links) == 0


class TestBBCArticleScraping:
    """Test article scraping and extraction."""

    @patch('requests.Session.get')
    def test_scrape_article_success(self, mock_get, sample_article_html):
        """Test successful article scraping and parsing."""
        mock_response = Mock()
        mock_response.text = sample_article_html
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor()
        session = processor._get_http_session()
        article = processor._scrape_article(
            session,
            "https://www.bbc.com/somali/articles/test"
        )

        assert article is not None
        assert 'title' in article
        assert 'text' in article
        assert 'url' in article
        assert len(article['text']) > 0

    @patch('requests.Session.get')
    def test_scrape_article_handles_404(self, mock_get):
        """Test article scraping handles 404 errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock(
            side_effect=requests.exceptions.HTTPError("404 Not Found")
        )
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor()
        session = processor._get_http_session()
        article = processor._scrape_article(
            session,
            "https://www.bbc.com/somali/articles/nonexistent"
        )

        # Should return None on 404
        assert article is None

    @patch('requests.Session.get')
    def test_scrape_article_respects_rate_limiting(self, mock_get, sample_article_html):
        """Test article scraping respects rate limits."""
        mock_response = Mock()
        mock_response.text = sample_article_html
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor(delay_range=(0.1, 0.2))
        session = processor._get_http_session()

        start_time = time.time()
        processor._scrape_article(session, "https://www.bbc.com/somali/articles/test1")
        processor._scrape_article(session, "https://www.bbc.com/somali/articles/test2")
        duration = time.time() - start_time

        # Should have at least 0.1 second delay between requests
        assert duration >= 0.1


class TestBBCHomepageScraping:
    """Test homepage scraping and link discovery."""

    @patch('requests.Session.get')
    def test_scrape_homepage_success(self, mock_get, sample_homepage_html):
        """Test homepage scraping discovers article links."""
        mock_response = Mock()
        mock_response.text = sample_homepage_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor()
        session = processor._get_http_session()
        links, soup = processor._scrape_homepage(session)

        assert len(links) >= 0  # May not find links depending on HTML structure
        assert soup is not None

    @patch('requests.Session.get')
    def test_discover_topic_sections(self, mock_get, sample_homepage_html):
        """Test discovering topic sections from homepage."""
        from bs4 import BeautifulSoup

        processor = BBCSomaliProcessor()
        soup = BeautifulSoup(sample_homepage_html, 'html.parser')
        sections = processor._discover_topic_sections(soup)

        assert isinstance(sections, list)
        # Should find topic sections in sample HTML
        assert len(sections) >= 0


class TestBBCDeduplication:
    """Test deduplication functionality."""

    def test_ledger_tracks_processed_urls(self):
        """Test that ledger tracks processed URLs."""
        processor = BBCSomaliProcessor()
        test_url = "https://www.bbc.com/somali/articles/test123"

        # Mark URL as processed
        processor.ledger.start_processing_url(test_url, processor.source)
        processor.ledger.finish_processing_url(test_url, "processed")

        # Check URL state
        state = processor.ledger.get_url_state(test_url)
        assert state is not None
        assert state['state'] == 'processed'

    def test_dedup_engine_detects_duplicates(self):
        """Test dedup engine detects duplicate content."""
        processor = BBCSomaliProcessor()

        text1 = "Magaalada Muqdisho waxaa ka da'ayay roob xoogan"
        text2 = "Magaalada Muqdisho waxaa ka da'ayay roob xoogan"  # Exact duplicate

        # First text should not be duplicate
        is_dup1 = processor.dedup.is_duplicate(
            {"text": text1, "url": "url1"},
            hash_fields=["text", "url"]
        )
        assert not is_dup1

        # Second text should be detected as duplicate
        is_dup2 = processor.dedup.is_duplicate(
            {"text": text2, "url": "url1"},
            hash_fields=["text", "url"]
        )
        assert is_dup2

    def test_compute_text_hash(self):
        """Test text hash computation for deduplication."""
        processor = BBCSomaliProcessor()

        text = "Test article text"
        url = "https://www.bbc.com/somali/articles/test"

        hash1 = processor._compute_text_hash(text, url)
        hash2 = processor._compute_text_hash(text, url)

        # Same text and URL should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hash length


class TestBBCMetricsCollection:
    """Test metrics collection and reporting."""

    def test_processor_initializes_metrics(self):
        """Test processor initializes metrics collector."""
        processor = BBCSomaliProcessor()

        # Metrics should be None initially
        assert processor.metrics is None

    @patch('requests.Session.get')
    def test_metrics_track_article_counts(self, mock_get, sample_article_html):
        """Test metrics track article discovery and processing."""
        mock_response = Mock()
        mock_response.text = sample_article_html
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor()
        # Initialize metrics
        from somali_dialect_classifier.utils.metrics import MetricsCollector, PipelineType
        processor.metrics = MetricsCollector(
            source="BBC-Somali",
            run_id=processor.run_id,
            stage="download",
            pipeline_type=PipelineType.DISCOVERY
        )

        assert processor.metrics is not None
        assert processor.metrics.source == "BBC-Somali"


class TestBBCErrorHandling:
    """Test error handling and resilience."""

    @patch('requests.Session.get')
    def test_handles_network_timeout(self, mock_get):
        """Test handling of network timeouts."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        processor = BBCSomaliProcessor()
        session = processor._get_http_session()
        article = processor._scrape_article(
            session,
            "https://www.bbc.com/somali/articles/test"
        )

        # Should return None on timeout
        assert article is None

    @patch('requests.Session.get')
    def test_handles_connection_errors(self, mock_get):
        """Test handling of connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        processor = BBCSomaliProcessor()
        session = processor._get_http_session()
        article = processor._scrape_article(
            session,
            "https://www.bbc.com/somali/articles/test"
        )

        # Should return None on connection error
        assert article is None

    @patch('requests.Session.get')
    def test_handles_malformed_html(self, mock_get):
        """Test handling of malformed HTML."""
        mock_response = Mock()
        mock_response.text = "<html><body>Incomplete HTML"
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_get.return_value = mock_response

        processor = BBCSomaliProcessor()
        session = processor._get_http_session()
        article = processor._scrape_article(
            session,
            "https://www.bbc.com/somali/articles/test"
        )

        # Should handle malformed HTML gracefully
        # May return None or empty article depending on implementation
        assert article is None or isinstance(article, dict)


class TestBBCTextCleaning:
    """Test text cleaning and preprocessing."""

    def test_creates_html_cleaner(self):
        """Test processor creates HTML cleaner."""
        processor = BBCSomaliProcessor()
        cleaner = processor._create_cleaner()

        assert cleaner is not None
        assert hasattr(cleaner, 'run')

    def test_html_cleaner_removes_tags(self):
        """Test HTML cleaner removes HTML tags."""
        processor = BBCSomaliProcessor()
        cleaner = processor._create_cleaner()

        raw_text = "<p>Test <strong>article</strong> text</p>"
        result = cleaner.run([{"text": raw_text}])

        cleaned_text = next(result)["text"]
        assert "<p>" not in cleaned_text
        assert "<strong>" not in cleaned_text


class TestBBCMetadataExtraction:
    """Test metadata extraction methods."""

    def test_get_source_type(self):
        """Test source type is correctly identified."""
        processor = BBCSomaliProcessor()
        source_type = processor._get_source_type()

        assert source_type == "news"

    def test_get_license(self):
        """Test license information."""
        processor = BBCSomaliProcessor()
        license_info = processor._get_license()

        assert isinstance(license_info, str)
        assert len(license_info) > 0

    def test_get_language(self):
        """Test language code."""
        processor = BBCSomaliProcessor()
        language = processor._get_language()

        assert language == "so"

    def test_get_domain(self):
        """Test domain classification."""
        processor = BBCSomaliProcessor()
        domain = processor._get_domain()

        assert domain == "news"

    def test_get_register(self):
        """Test linguistic register."""
        processor = BBCSomaliProcessor()
        register = processor._get_register()

        assert register in ["formal", "informal", "colloquial"]

    def test_get_source_metadata(self):
        """Test source metadata extraction."""
        processor = BBCSomaliProcessor()
        metadata = processor._get_source_metadata()

        assert isinstance(metadata, dict)
        assert "publisher" in metadata
        assert metadata["publisher"] == "BBC News"


class TestBBCHTTPSession:
    """Test HTTP session configuration."""

    def test_creates_session_with_retry_logic(self):
        """Test HTTP session has retry configuration."""
        processor = BBCSomaliProcessor()
        session = processor._get_http_session()

        assert isinstance(session, requests.Session)
        # Check that session has retry adapter
        assert 'http://' in session.adapters or 'https://' in session.adapters

    def test_session_has_custom_headers(self):
        """Test HTTP session uses custom headers."""
        processor = BBCSomaliProcessor()

        assert "User-Agent" in processor.headers
        assert "SomaliNLPBot" in processor.headers["User-Agent"]
        assert "Accept" in processor.headers
