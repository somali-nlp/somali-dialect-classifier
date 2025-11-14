"""
Test backend compatibility between SQLite and PostgreSQL.

Ensures both backends provide identical API and behavior.
"""

import os
import tempfile
from pathlib import Path

import pytest

from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger

# Skip PostgreSQL tests if not available
postgres_available = os.getenv("POSTGRES_HOST") is not None


@pytest.fixture
def sqlite_ledger():
    """Create SQLite ledger for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ledger = CrawlLedger(backend_type="sqlite", db_path=db_path)
        yield ledger
        ledger.close()


@pytest.fixture
def postgres_ledger():
    """Create PostgreSQL ledger for testing."""
    if not postgres_available:
        pytest.skip("PostgreSQL not available")

    ledger = CrawlLedger(
        backend_type="postgres",
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "somali_nlp_test"),
        user=os.getenv("POSTGRES_USER", "somali"),
        password=os.getenv("POSTGRES_PASSWORD", "somali_dev_password"),
    )
    yield ledger
    ledger.close()


class TestBackendAPIs:
    """Test that both backends support the same API."""

    def test_discover_url_sqlite(self, sqlite_ledger):
        """Test discover_url on SQLite."""
        url = "https://example.com/sqlite_test"
        is_new = sqlite_ledger.discover_url(url, source="test")
        assert is_new is True

        # Duplicate discovery
        is_new = sqlite_ledger.discover_url(url, source="test")
        assert is_new is False

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_discover_url_postgres(self, postgres_ledger):
        """Test discover_url on PostgreSQL."""
        url = "https://example.com/postgres_test"
        is_new = postgres_ledger.discover_url(url, source="test")
        assert is_new is True

        # Duplicate discovery
        is_new = postgres_ledger.discover_url(url, source="test")
        assert is_new is False

    def test_mark_fetched_sqlite(self, sqlite_ledger):
        """Test mark_fetched on SQLite."""
        url = "https://example.com/sqlite_fetch"
        sqlite_ledger.discover_url(url, source="test")
        sqlite_ledger.mark_fetched(url, http_status=200, etag="abc123", source="test")

        state = sqlite_ledger.backend.get_url_state(url)
        assert state["state"] == "fetched"
        assert state["http_status"] == 200
        assert state["etag"] == "abc123"

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_mark_fetched_postgres(self, postgres_ledger):
        """Test mark_fetched on PostgreSQL."""
        url = "https://example.com/postgres_fetch"
        postgres_ledger.discover_url(url, source="test")
        postgres_ledger.mark_fetched(url, http_status=200, etag="abc123", source="test")

        state = postgres_ledger.backend.get_url_state(url)
        assert state["state"] == "fetched"
        assert state["http_status"] == 200
        assert state["etag"] == "abc123"

    def test_mark_processed_sqlite(self, sqlite_ledger):
        """Test mark_processed on SQLite."""
        url = "https://example.com/sqlite_processed"
        sqlite_ledger.discover_url(url, source="test")
        sqlite_ledger.mark_processed(
            url, text_hash="hash123", silver_id="silver_001", source="test"
        )

        state = sqlite_ledger.backend.get_url_state(url)
        assert state["state"] == "processed"
        assert state["text_hash"] == "hash123"
        assert state["silver_id"] == "silver_001"

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_mark_processed_postgres(self, postgres_ledger):
        """Test mark_processed on PostgreSQL."""
        url = "https://example.com/postgres_processed"
        postgres_ledger.discover_url(url, source="test")
        postgres_ledger.mark_processed(
            url, text_hash="hash123", silver_id="silver_001", source="test"
        )

        state = postgres_ledger.backend.get_url_state(url)
        assert state["state"] == "processed"
        assert state["text_hash"] == "hash123"
        assert state["silver_id"] == "silver_001"

    def test_is_duplicate_sqlite(self, sqlite_ledger):
        """Test is_duplicate on SQLite."""
        url = "https://example.com/sqlite_dup"
        text_hash = "duplicate_hash"

        sqlite_ledger.discover_url(url, source="test")
        sqlite_ledger.mark_processed(url, text_hash=text_hash, silver_id="s1", source="test")

        # Check duplicate
        original = sqlite_ledger.is_duplicate(text_hash)
        assert original == url

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_is_duplicate_postgres(self, postgres_ledger):
        """Test is_duplicate on PostgreSQL."""
        url = "https://example.com/postgres_dup"
        text_hash = "duplicate_hash_pg"

        postgres_ledger.discover_url(url, source="test")
        postgres_ledger.mark_processed(url, text_hash=text_hash, silver_id="s1", source="test")

        # Check duplicate
        original = postgres_ledger.is_duplicate(text_hash)
        assert original == url


class TestBackendSelection:
    """Test backend selection mechanism."""

    def test_explicit_sqlite_backend(self):
        """Test explicit SQLite backend selection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "explicit.db"
            ledger = CrawlLedger(backend_type="sqlite", db_path=db_path)
            assert ledger.backend_type == "sqlite"
            ledger.close()

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_explicit_postgres_backend(self):
        """Test explicit PostgreSQL backend selection."""
        ledger = CrawlLedger(
            backend_type="postgres",
            host=os.getenv("POSTGRES_HOST", "localhost"),
            database=os.getenv("POSTGRES_DB", "somali_nlp_test"),
        )
        assert ledger.backend_type == "postgres"
        ledger.close()

    def test_environment_variable_backend_selection(self):
        """Test backend selection via environment variable."""
        # Save original
        original = os.environ.get("SDC_LEDGER_BACKEND")

        try:
            # Test SQLite via env
            os.environ["SDC_LEDGER_BACKEND"] = "sqlite"
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "env.db"
                ledger = CrawlLedger(db_path=db_path)
                assert ledger.backend_type == "sqlite"
                ledger.close()
        finally:
            # Restore original
            if original:
                os.environ["SDC_LEDGER_BACKEND"] = original
            else:
                os.environ.pop("SDC_LEDGER_BACKEND", None)

    def test_invalid_backend_type(self):
        """Test that invalid backend type raises error."""
        with pytest.raises(ValueError, match="Unknown backend type"):
            CrawlLedger(backend_type="invalid_backend")


class TestBackendBehaviorParity:
    """Test that both backends produce identical behavior."""

    def test_statistics_parity(self, sqlite_ledger):
        """Test that statistics have same structure."""
        # Insert test data
        for i in range(5):
            sqlite_ledger.discover_url(f"https://example.com/stats/{i}", source="test")

        stats = sqlite_ledger.get_statistics(source="test")

        # Verify structure
        assert "total_urls" in stats
        assert "by_state" in stats
        assert "unique_documents" in stats
        assert "dedup_rate" in stats

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_statistics_parity_postgres(self, postgres_ledger):
        """Test that PostgreSQL statistics have same structure."""
        # Insert test data
        for i in range(5):
            postgres_ledger.discover_url(f"https://example.com/stats_pg/{i}", source="test")

        stats = postgres_ledger.get_statistics(source="test")

        # Verify structure
        assert "total_urls" in stats
        assert "by_state" in stats
        assert "unique_documents" in stats
        assert "dedup_rate" in stats

    def test_get_pending_urls_sqlite(self, sqlite_ledger):
        """Test get_pending_urls on SQLite."""
        for i in range(3):
            sqlite_ledger.discover_url(f"https://example.com/pending/{i}", source="test")

        pending = sqlite_ledger.get_pending_urls("test", limit=10)
        assert len(pending) >= 3

    @pytest.mark.skipif(not postgres_available, reason="PostgreSQL not available")
    def test_get_pending_urls_postgres(self, postgres_ledger):
        """Test get_pending_urls on PostgreSQL."""
        for i in range(3):
            postgres_ledger.discover_url(f"https://example.com/pending_pg/{i}", source="test")

        pending = postgres_ledger.get_pending_urls("test", limit=10)
        assert len(pending) >= 3
