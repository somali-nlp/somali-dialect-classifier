"""
Tests for critical security fixes (CRIT-001, CRIT-002, HIGH-001, HIGH-002).

Tests validate:
1. Password validation in PostgresLedger (CRIT-001, CRIT-002)
2. SQL injection prevention in LIMIT clauses (HIGH-001)
3. Input validation for limit parameters
4. URL validation for SSRF protection (HIGH-002)

Created: 2025-12-30
Updated: 2025-12-30 (added HIGH-002 tests)
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from somali_dialect_classifier.ingestion.crawl_ledger import (
    CrawlLedger,
    CrawlState,
    SQLiteLedger,
)


class TestPasswordValidation:
    """Test CRIT-001 & CRIT-002: Hardcoded password removal."""

    def test_postgres_ledger_requires_password(self):
        """PostgresLedger should raise ValueError if password is None."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with pytest.raises(ValueError) as exc_info:
            PostgresLedger(password=None)

        assert "password is required" in str(exc_info.value).lower()
        assert "SDC_DB_PASSWORD" in str(exc_info.value) or "POSTGRES_PASSWORD" in str(
            exc_info.value
        )

    def test_postgres_ledger_accepts_explicit_password(self):
        """PostgresLedger should accept explicitly provided password."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        # Mock psycopg2 to avoid actual database connection
        with patch(
            "somali_dialect_classifier.database.postgres_ledger.ThreadedConnectionPool"
        ) as mock_pool:
            mock_pool.return_value = MagicMock()

            # Should not raise ValueError
            ledger = PostgresLedger(password="test_password")
            assert ledger is not None

    @patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password_from_env"})
    def test_crawl_ledger_uses_sdc_db_password(self):
        """CrawlLedger should use SDC_DB_PASSWORD environment variable."""
        with patch(
            "somali_dialect_classifier.database.postgres_ledger.ThreadedConnectionPool"
        ) as mock_pool:
            mock_pool.return_value = MagicMock()

            ledger = CrawlLedger(backend_type="postgres")
            # Should not raise ValueError because SDC_DB_PASSWORD is set
            assert ledger is not None

    @patch.dict(os.environ, {"POSTGRES_PASSWORD": "test_password_fallback"})
    def test_crawl_ledger_uses_postgres_password_fallback(self):
        """CrawlLedger should use POSTGRES_PASSWORD as fallback."""
        with patch(
            "somali_dialect_classifier.database.postgres_ledger.ThreadedConnectionPool"
        ) as mock_pool:
            mock_pool.return_value = MagicMock()

            ledger = CrawlLedger(backend_type="postgres")
            # Should not raise ValueError because POSTGRES_PASSWORD is set
            assert ledger is not None

    @patch.dict(os.environ, {}, clear=True)
    def test_crawl_ledger_postgres_fails_without_password(self):
        """CrawlLedger should fail when no password env var is set."""
        # Clear password environment variables
        os.environ.pop("SDC_DB_PASSWORD", None)
        os.environ.pop("POSTGRES_PASSWORD", None)

        with pytest.raises(ValueError) as exc_info:
            CrawlLedger(backend_type="postgres")

        assert "password is required" in str(exc_info.value).lower()


class TestSQLInjectionPrevention:
    """Test HIGH-001: SQL injection prevention in LIMIT clauses."""

    def test_sqlite_limit_with_malicious_input(self, tmp_path):
        """SQLiteLedger should reject SQL injection attempts in limit."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        # Add a test URL
        ledger.upsert_url(
            url="https://example.com/test",
            source="test",
            state=CrawlState.DISCOVERED,
        )

        # Try SQL injection via limit parameter
        with pytest.raises(ValueError) as exc_info:
            ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit="10; DROP TABLE crawl_ledger;")

        assert "must be a positive integer" in str(exc_info.value)

    def test_sqlite_limit_with_negative_value(self, tmp_path):
        """SQLiteLedger should reject negative limit values."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        with pytest.raises(ValueError) as exc_info:
            ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=-1)

        assert "must be a positive integer" in str(exc_info.value)

    def test_sqlite_limit_with_zero(self, tmp_path):
        """SQLiteLedger should reject zero limit values."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        with pytest.raises(ValueError) as exc_info:
            ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=0)

        assert "must be a positive integer" in str(exc_info.value)

    def test_sqlite_limit_with_float(self, tmp_path):
        """SQLiteLedger should reject float limit values."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        with pytest.raises(ValueError) as exc_info:
            ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=10.5)

        assert "must be a positive integer" in str(exc_info.value)

    def test_sqlite_limit_with_valid_integer(self, tmp_path):
        """SQLiteLedger should accept valid positive integer limit."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        # Add test URLs
        for i in range(10):
            ledger.upsert_url(
                url=f"https://example.com/test{i}",
                source="test",
                state=CrawlState.DISCOVERED,
            )

        # Should work with valid limit
        results = ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=5)
        assert len(results) == 5

    def test_sqlite_parameterized_query_prevents_injection(self, tmp_path):
        """Verify parameterized queries prevent SQL injection."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        # Add test URL
        ledger.upsert_url(
            url="https://example.com/test",
            source="test",
            state=CrawlState.DISCOVERED,
        )

        # Valid limit should work
        results = ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=10)
        assert len(results) == 1

        # Verify table still exists (wasn't dropped by injection attempt)
        count = ledger.connection.execute(
            "SELECT COUNT(*) as count FROM crawl_ledger"
        ).fetchone()
        assert count["count"] == 1

    def test_postgres_limit_validation(self):
        """PostgresLedger should validate limit parameter."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch(
            "somali_dialect_classifier.database.postgres_ledger.ThreadedConnectionPool"
        ) as mock_pool:
            mock_pool.return_value = MagicMock()
            ledger = PostgresLedger(password="test_password")

            # Mock connection and cursor
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            ledger.pool.getconn.return_value = mock_conn

            # Test invalid limit
            with pytest.raises(ValueError) as exc_info:
                ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit="malicious")

            assert "must be a positive integer" in str(exc_info.value)

    def test_postgres_parameterized_query_structure(self):
        """Verify PostgresLedger uses parameterized queries for LIMIT."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch(
            "somali_dialect_classifier.database.postgres_ledger.ThreadedConnectionPool"
        ) as mock_pool:
            mock_pool.return_value = MagicMock()
            ledger = PostgresLedger(password="test_password")

            # Mock connection and cursor
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            ledger.pool.getconn.return_value = mock_conn

            # Call with valid limit
            ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=10)

            # Verify execute was called with parameterized query
            assert mock_cursor.execute.called
            call_args = mock_cursor.execute.call_args[0]

            # Check that LIMIT is parameterized (not in f-string)
            query = call_args[0]
            assert "LIMIT %s" in query
            assert "LIMIT 10" not in query  # Should NOT be inline

            # Check parameters include the limit value
            params = call_args[1]
            assert 10 in params


class TestInputValidation:
    """Test comprehensive input validation."""

    def test_limit_validation_consistency_sqlite(self, tmp_path):
        """Ensure SQLiteLedger validates limit consistently."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        invalid_limits = [
            ("string", "string"),
            (None, None),  # None is valid (no limit)
            (-1, "negative"),
            (0, "zero"),
            (10.5, "float"),
            ([], "list"),
            ({}, "dict"),
        ]

        for limit_value, description in invalid_limits:
            if limit_value is None:
                # None is valid - should not raise
                continue

            with pytest.raises(ValueError, match="must be a positive integer"):
                ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=limit_value)

    def test_limit_none_allows_unlimited_results(self, tmp_path):
        """Verify that limit=None returns all results."""
        ledger = SQLiteLedger(db_path=tmp_path / "test.db")

        # Add 20 test URLs
        for i in range(20):
            ledger.upsert_url(
                url=f"https://example.com/test{i}",
                source="test",
                state=CrawlState.DISCOVERED,
            )

        # limit=None should return all 20
        results = ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=None)
        assert len(results) == 20

        # limit=10 should return only 10
        results = ledger.get_urls_by_state("test", CrawlState.DISCOVERED, limit=10)
        assert len(results) == 10


class TestSecurityRegression:
    """Regression tests to prevent reintroduction of vulnerabilities."""

    def test_no_hardcoded_passwords_in_defaults(self):
        """Ensure no hardcoded passwords in PostgresLedger defaults."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger
        import inspect

        sig = inspect.signature(PostgresLedger.__init__)
        password_param = sig.parameters.get("password")

        # Password default should be None
        assert password_param.default is None, "Password default must be None"

    def test_no_f_string_sql_in_get_urls_by_state_sqlite(self, tmp_path):
        """Ensure no f-string SQL concatenation in SQLiteLedger.get_urls_by_state."""
        import inspect
        from somali_dialect_classifier.ingestion.crawl_ledger import SQLiteLedger

        # Get source code
        source = inspect.getsource(SQLiteLedger.get_urls_by_state)

        # Should NOT contain f-string SQL concatenation like f" LIMIT {limit}"
        assert 'f" LIMIT {limit}"' not in source, "Found f-string SQL concatenation (SQL injection risk)"
        assert 'f" LIMIT {' not in source, "Found f-string SQL concatenation variant"

        # Should contain parameterized LIMIT
        assert "LIMIT ?" in source, "Missing parameterized LIMIT query"

    def test_no_f_string_sql_in_get_urls_by_state_postgres(self):
        """Ensure no f-string SQL concatenation in PostgresLedger.get_urls_by_state."""
        import inspect
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        # Get source code
        source = inspect.getsource(PostgresLedger.get_urls_by_state)

        # Should NOT contain f-string SQL concatenation
        assert 'f" LIMIT {limit}"' not in source, "Found f-string SQL concatenation (SQL injection risk)"
        assert 'f" LIMIT {' not in source, "Found f-string SQL concatenation variant"

        # Should contain parameterized LIMIT
        assert "LIMIT %s" in source, "Missing parameterized LIMIT query"


class TestURLValidationSSRFProtection:
    """Test HIGH-002: URL validation for SSRF protection."""

    def test_is_safe_url_allows_valid_urls(self):
        """Valid HTTP/HTTPS URLs should pass."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("https://example.com/page") is True
        assert is_safe_url("http://example.com/page") is True
        assert is_safe_url("https://bbc.com/somali/article") is True
        assert is_safe_url("http://www.example.org/path") is True

    def test_is_safe_url_blocks_file_urls(self):
        """File:// URLs should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("file:///etc/passwd") is False
        assert is_safe_url("file://C:/Windows/System32/config") is False

    def test_is_safe_url_blocks_localhost(self):
        """Localhost addresses should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("http://localhost:8080") is False
        assert is_safe_url("http://localhost/admin") is False
        assert is_safe_url("https://localhost") is False

    def test_is_safe_url_blocks_loopback_ips(self):
        """Loopback IP addresses should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("http://127.0.0.1:8080") is False
        assert is_safe_url("http://127.0.0.1/") is False
        assert is_safe_url("http://127.1.2.3/") is False  # Any 127.x.x.x
        assert is_safe_url("http://[::1]/") is False  # IPv6 loopback

    def test_is_safe_url_blocks_private_ips(self):
        """Private IP ranges (RFC 1918) should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        # 10.0.0.0/8
        assert is_safe_url("http://10.0.0.1/") is False
        assert is_safe_url("http://10.255.255.255/") is False

        # 192.168.0.0/16
        assert is_safe_url("http://192.168.1.1/") is False
        assert is_safe_url("http://192.168.0.1/") is False

        # 172.16.0.0/12
        assert is_safe_url("http://172.16.0.1/") is False
        assert is_safe_url("http://172.31.255.255/") is False
        assert is_safe_url("http://172.20.0.1/") is False

    def test_is_safe_url_blocks_link_local(self):
        """Link-local addresses should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        # AWS/Azure metadata endpoint
        assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False
        assert is_safe_url("http://169.254.0.1/") is False

    def test_is_safe_url_blocks_metadata_endpoints(self):
        """Cloud metadata endpoints should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("http://metadata.google.internal/") is False
        assert is_safe_url("http://metadata.azure.com/") is False
        assert is_safe_url("http://169.254.169.254/") is False

    def test_is_safe_url_blocks_data_urls(self):
        """Data: URLs should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("data:text/html,<script>alert('xss')</script>") is False

    def test_is_safe_url_blocks_ftp_urls(self):
        """FTP URLs should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("ftp://ftp.example.com/file.txt") is False

    def test_is_safe_url_blocks_javascript_urls(self):
        """JavaScript: URLs should be blocked."""
        from somali_dialect_classifier.infra.security import is_safe_url

        assert is_safe_url("javascript:alert('xss')") is False

    def test_is_safe_url_domain_whitelist(self):
        """Domain whitelist should be enforced when provided."""
        from somali_dialect_classifier.infra.security import is_safe_url

        allowed_domains = {"bbc.com", "bbc.co.uk"}

        # Allowed domains
        assert is_safe_url("https://bbc.com/article", allowed_domains=allowed_domains) is True
        assert is_safe_url("https://www.bbc.com/article", allowed_domains=allowed_domains) is True
        assert is_safe_url("https://bbc.co.uk/somali", allowed_domains=allowed_domains) is True

        # Blocked domains
        assert (
            is_safe_url("https://evil.com/article", allowed_domains=allowed_domains) is False
        )
        assert (
            is_safe_url("https://attacker.bbc.com.evil.com/", allowed_domains=allowed_domains)
            is False
        )

    def test_validate_url_for_source_valid_bbc_urls(self):
        """Valid BBC URLs should pass validation."""
        from somali_dialect_classifier.infra.security import validate_url_for_source

        bbc_domains = {"bbc.com", "bbc.co.uk"}

        valid, msg = validate_url_for_source(
            "https://www.bbc.com/somali/article", "bbc", bbc_domains
        )
        assert valid is True
        assert msg == ""

        valid, msg = validate_url_for_source(
            "https://bbc.co.uk/somali/topics", "bbc", bbc_domains
        )
        assert valid is True
        assert msg == ""

    def test_validate_url_for_source_rejects_ssrf(self):
        """SSRF attempts should be rejected with clear error messages."""
        from somali_dialect_classifier.infra.security import validate_url_for_source

        bbc_domains = {"bbc.com", "bbc.co.uk"}

        # Loopback
        valid, msg = validate_url_for_source("http://127.0.0.1/pwned", "bbc", bbc_domains)
        assert valid is False
        assert "SSRF" in msg
        assert "loopback" in msg.lower()

        # Private IP
        valid, msg = validate_url_for_source("http://192.168.1.1/internal", "bbc", bbc_domains)
        assert valid is False
        assert "SSRF" in msg
        assert "private IP" in msg.lower()

        # Link-local (AWS metadata)
        valid, msg = validate_url_for_source(
            "http://169.254.169.254/latest/meta-data/", "bbc", bbc_domains
        )
        assert valid is False
        assert "SSRF" in msg
        assert "link-local" in msg.lower()

    def test_validate_url_for_source_rejects_wrong_domain(self):
        """URLs from wrong domains should be rejected."""
        from somali_dialect_classifier.infra.security import validate_url_for_source

        bbc_domains = {"bbc.com", "bbc.co.uk"}

        valid, msg = validate_url_for_source("https://evil.com/article", "bbc", bbc_domains)
        assert valid is False
        assert "Domain not allowed" in msg
        assert "evil.com" in msg
        assert "bbc" in msg.lower()

    def test_validate_url_for_source_rejects_unsafe_scheme(self):
        """Unsafe URL schemes should be rejected."""
        from somali_dialect_classifier.infra.security import validate_url_for_source

        bbc_domains = {"bbc.com", "bbc.co.uk"}

        valid, msg = validate_url_for_source("file:///etc/passwd", "bbc", bbc_domains)
        assert valid is False
        assert "SSRF" in msg
        assert "unsafe scheme" in msg.lower()
        assert "file" in msg

    def test_bbc_processor_validates_rss_urls(self, tmp_path):
        """BBC processor should validate RSS feed URLs."""
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        # Mock config with malicious RSS feed
        with patch(
            "somali_dialect_classifier.ingestion.processors.bbc_somali_processor.get_config"
        ) as mock_config:
            mock_config.return_value.scraping.bbc.rss_feeds = [
                "http://127.0.0.1:8080/malicious-feed",  # SSRF attempt
                "https://www.bbc.com/somali/rss.xml",  # Valid
            ]
            mock_config.return_value.scraping.bbc.max_items_per_feed = 10
            mock_config.return_value.scraping.bbc.check_frequency_hours = 1
            mock_config.return_value.scraping.bbc.max_requests_per_hour = 100
            mock_config.return_value.scraping.bbc.backoff_multiplier = 2.0
            mock_config.return_value.scraping.bbc.max_backoff = 60
            mock_config.return_value.scraping.bbc.jitter = 0.1
            mock_config.return_value.data.raw_dir = tmp_path / "raw"
            mock_config.return_value.data.staging_dir = tmp_path / "staging"
            mock_config.return_value.data.processed_dir = tmp_path / "processed"
            mock_config.return_value.data.silver_dir = tmp_path / "silver"

            processor = BBCSomaliProcessor(max_articles=10)

            # Mock ledger and metrics
            processor.ledger = MagicMock()
            processor.ledger.should_fetch_rss.return_value = True
            processor.metrics = MagicMock()

            # Mock feedparser
            with patch(
                "somali_dialect_classifier.ingestion.processors.bbc_somali_processor.feedparser"
            ) as mock_feedparser:
                mock_feed = MagicMock()
                mock_feed.entries = []
                mock_feedparser.parse.return_value = mock_feed

                # Call _scrape_rss_feeds
                article_urls = processor._scrape_rss_feeds()

                # Verify:
                # 1. Malicious URL was rejected (not passed to feedparser)
                # 2. Valid URL was processed
                # 3. Security metric was incremented
                assert processor.metrics.increment.call_count > 0
                metric_calls = [call[0][0] for call in processor.metrics.increment.call_args_list]
                assert "urls_rejected_security" in metric_calls

    def test_bbc_processor_validates_article_urls_from_rss(self, tmp_path):
        """BBC processor should validate article URLs extracted from RSS."""
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        with patch(
            "somali_dialect_classifier.ingestion.processors.bbc_somali_processor.get_config"
        ) as mock_config:
            mock_config.return_value.scraping.bbc.rss_feeds = [
                "https://www.bbc.com/somali/rss.xml"
            ]
            mock_config.return_value.scraping.bbc.max_items_per_feed = 10
            mock_config.return_value.scraping.bbc.check_frequency_hours = 1
            mock_config.return_value.scraping.bbc.max_requests_per_hour = 100
            mock_config.return_value.scraping.bbc.backoff_multiplier = 2.0
            mock_config.return_value.scraping.bbc.max_backoff = 60
            mock_config.return_value.scraping.bbc.jitter = 0.1
            mock_config.return_value.data.raw_dir = tmp_path / "raw"
            mock_config.return_value.data.staging_dir = tmp_path / "staging"
            mock_config.return_value.data.processed_dir = tmp_path / "processed"
            mock_config.return_value.data.silver_dir = tmp_path / "silver"

            processor = BBCSomaliProcessor(max_articles=10)

            # Mock ledger and metrics
            processor.ledger = MagicMock()
            processor.ledger.should_fetch_rss.return_value = True
            processor.metrics = MagicMock()

            # Mock feedparser with mix of valid and malicious URLs
            with patch(
                "somali_dialect_classifier.ingestion.processors.bbc_somali_processor.feedparser"
            ) as mock_feedparser:
                mock_entry1 = MagicMock()
                mock_entry1.get.return_value = (
                    "http://10.0.0.1/internal/somali/articles/123"  # Private IP - SSRF
                )

                mock_entry2 = MagicMock()
                mock_entry2.get.return_value = (
                    "https://www.bbc.com/somali/articles/valid-article"  # Valid
                )

                mock_entry3 = MagicMock()
                mock_entry3.get.return_value = (
                    "http://169.254.169.254/somali/articles/aws-metadata"  # Link-local - SSRF
                )

                mock_feed = MagicMock()
                mock_feed.entries = [mock_entry1, mock_entry2, mock_entry3]
                mock_feedparser.parse.return_value = mock_feed

                # Call _scrape_rss_feeds
                article_urls = processor._scrape_rss_feeds()

                # Verify only valid URL was added
                assert len(article_urls) == 1
                assert article_urls[0] == "https://www.bbc.com/somali/articles/valid-article"

                # Verify security rejection metric was incremented
                metric_calls = [call[0][0] for call in processor.metrics.increment.call_args_list]
                assert "urls_rejected_security" in metric_calls


class TestURLValidationRegression:
    """Regression tests to ensure URL validation is applied consistently."""

    def test_no_unvalidated_feedparser_calls(self):
        """Ensure feedparser.parse() is not called with unvalidated URLs."""
        import inspect
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        # Get source code of _scrape_rss_feeds
        source = inspect.getsource(BBCSomaliProcessor._scrape_rss_feeds)

        # Should import validate_url_for_source
        assert "validate_url_for_source" in source, "Missing URL validation import"

        # Should validate feed_url before feedparser.parse
        assert "validate_url_for_source(feed_url" in source or "validate_url_for_source(\n" in source, "Feed URL not validated before parsing"

    def test_security_metrics_exist(self):
        """Ensure urls_rejected_security metric is tracked."""
        import inspect
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        source = inspect.getsource(BBCSomaliProcessor._scrape_rss_feeds)

        # Should increment security rejection metric
        assert (
            'increment("urls_rejected_security")' in source
        ), "Missing urls_rejected_security metric"
