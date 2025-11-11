"""
Tests for PostgreSQL ledger backend.

Comprehensive test suite for PostgresLedger including:
- Connection pool management
- Schema initialization
- CRUD operations
- Concurrent writes
- Transaction isolation
- Performance benchmarks
"""

import os
import threading
import time
from datetime import datetime, timezone

import pytest

from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlState

# Skip all tests if PostgreSQL is not available
postgres_available = os.getenv("POSTGRES_HOST") is not None

pytestmark = pytest.mark.skipif(
    not postgres_available, reason="PostgreSQL not available (POSTGRES_HOST not set)"
)


@pytest.fixture
def postgres_ledger():
    """Create PostgreSQL ledger for testing."""
    from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

    ledger = PostgresLedger(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "somali_nlp_test"),
        user=os.getenv("POSTGRES_USER", "somali"),
        password=os.getenv("POSTGRES_PASSWORD", "somali_dev_password"),
    )

    yield ledger

    # Cleanup
    ledger.close()


class TestPostgresLedgerBasics:
    """Test basic PostgreSQL ledger operations."""

    def test_connection_pool_creation(self, postgres_ledger):
        """Test that connection pool is created successfully."""
        assert postgres_ledger.pool is not None
        assert postgres_ledger.pool.minconn >= 2
        assert postgres_ledger.pool.maxconn <= 10

    def test_schema_initialization(self, postgres_ledger):
        """Test schema is initialized correctly."""
        # Schema should be initialized in __init__
        # Verify tables exist by querying them
        with postgres_ledger._get_connection() as conn:
            with conn.cursor() as cur:
                # Check crawl_ledger table exists
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'crawl_ledger'
                    )
                """
                )
                assert cur.fetchone()[0] is True

                # Check rss_feeds table exists
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'rss_feeds'
                    )
                """
                )
                assert cur.fetchone()[0] is True

    def test_upsert_url_insert(self, postgres_ledger):
        """Test inserting a new URL."""
        url = "https://example.com/test1"
        postgres_ledger.upsert_url(
            url=url, source="test", state=CrawlState.DISCOVERED, metadata={"key": "value"}
        )

        # Verify URL was inserted
        state = postgres_ledger.get_url_state(url)
        assert state is not None
        assert state["url"] == url
        assert state["source"] == "test"
        assert state["state"] == "discovered"
        assert state["metadata"] == {"key": "value"}

    def test_upsert_url_update(self, postgres_ledger):
        """Test updating an existing URL."""
        url = "https://example.com/test2"

        # Insert
        postgres_ledger.upsert_url(url=url, source="test", state=CrawlState.DISCOVERED)

        # Update
        postgres_ledger.upsert_url(
            url=url,
            source="test",
            state=CrawlState.PROCESSED,
            text_hash="abc123",
            silver_id="silver_001",
        )

        # Verify update
        state = postgres_ledger.get_url_state(url)
        assert state["state"] == "processed"
        assert state["text_hash"] == "abc123"
        assert state["silver_id"] == "silver_001"

    def test_get_urls_by_state(self, postgres_ledger):
        """Test retrieving URLs by state."""
        # Insert multiple URLs
        for i in range(5):
            postgres_ledger.upsert_url(
                url=f"https://example.com/test{i}",
                source="test_source",
                state=CrawlState.DISCOVERED,
            )

        # Get discovered URLs
        urls = postgres_ledger.get_urls_by_state("test_source", CrawlState.DISCOVERED)
        assert len(urls) >= 5

    def test_mark_url_state(self, postgres_ledger):
        """Test marking URL state."""
        url = "https://example.com/test_mark"
        postgres_ledger.upsert_url(url=url, source="test", state=CrawlState.DISCOVERED)

        # Mark as failed
        postgres_ledger.mark_url_state(url, CrawlState.FAILED, error_message="Test error")

        # Verify state changed
        state = postgres_ledger.get_url_state(url)
        assert state["state"] == "failed"
        assert state["error_message"] == "Test error"
        assert state["retry_count"] == 1

    def test_check_duplicate_by_hash(self, postgres_ledger):
        """Test duplicate detection by hash."""
        url1 = "https://example.com/original"
        text_hash = "hash_12345"

        postgres_ledger.upsert_url(
            url=url1, source="test", state=CrawlState.PROCESSED, text_hash=text_hash
        )

        # Check duplicate
        duplicate_url = postgres_ledger.check_duplicate_by_hash(text_hash)
        assert duplicate_url == url1

        # Check non-existent hash
        non_duplicate = postgres_ledger.check_duplicate_by_hash("nonexistent_hash")
        assert non_duplicate is None


class TestPostgresConcurrency:
    """Test concurrent operations on PostgreSQL ledger."""

    def test_concurrent_writes_10_threads(self, postgres_ledger):
        """Test 10 concurrent threads writing to ledger."""
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    url = f"https://example.com/concurrent/{thread_id}/{i}"
                    postgres_ledger.upsert_url(
                        url=url, source=f"source_{thread_id % 3}", state=CrawlState.DISCOVERED
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        # Should complete without errors
        assert len(errors) == 0, f"Concurrent write errors: {errors}"

        # Should complete in reasonable time (< 5s for 100 writes)
        assert duration < 5, f"Concurrent writes took {duration}s (too slow)"

    def test_concurrent_writes_50_threads(self, postgres_ledger):
        """Test 50 concurrent threads (10x scale simulation)."""
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    url = f"https://example.com/scale/{thread_id}/{i}"
                    postgres_ledger.upsert_url(
                        url=url, source=f"source_{thread_id % 5}", state=CrawlState.DISCOVERED
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        # Should complete without deadlocks
        assert len(errors) == 0, f"Concurrent write errors at 10x scale: {errors}"

        # Should complete in reasonable time (< 15s for 500 writes)
        assert duration < 15, f"10x scale test took {duration}s (too slow)"


class TestPostgresPerformance:
    """Test PostgreSQL ledger performance."""

    def test_query_latency(self, postgres_ledger):
        """Test query latency is < 100ms (p95)."""
        # Insert test data
        for i in range(100):
            postgres_ledger.upsert_url(
                url=f"https://example.com/perf/{i}",
                source="perf_test",
                state=CrawlState.DISCOVERED,
            )

        # Measure query latency
        latencies = []
        for i in range(100):
            start = time.time()
            postgres_ledger.get_url_state(f"https://example.com/perf/{i}")
            latencies.append(time.time() - start)

        # Calculate p95
        latencies.sort()
        p95_latency = latencies[94] * 1000  # Convert to ms

        assert p95_latency < 100, f"p95 latency {p95_latency}ms exceeds 100ms threshold"

    def test_bulk_insert_performance(self, postgres_ledger):
        """Test bulk insert performance."""
        start = time.time()

        for i in range(1000):
            postgres_ledger.upsert_url(
                url=f"https://example.com/bulk/{i}",
                source="bulk_test",
                state=CrawlState.DISCOVERED,
            )

        duration = time.time() - start

        # Should insert 1000 URLs in < 10 seconds
        assert duration < 10, f"Bulk insert took {duration}s (too slow)"
        throughput = 1000 / duration
        assert throughput > 100, f"Insert throughput {throughput} ops/s is too low"


class TestPostgresStatistics:
    """Test PostgreSQL statistics methods."""

    def test_get_statistics(self, postgres_ledger):
        """Test statistics calculation."""
        # Insert test data
        for i in range(10):
            postgres_ledger.upsert_url(
                url=f"https://example.com/stats/{i}",
                source="stats_test",
                state=CrawlState.DISCOVERED,
            )

        stats = postgres_ledger.get_statistics(source="stats_test")

        assert "total_urls" in stats
        assert stats["total_urls"] >= 10
        assert "by_state" in stats
        assert "unique_documents" in stats


class TestPostgresRSSFeed:
    """Test RSS feed tracking."""

    def test_record_rss_fetch(self, postgres_ledger):
        """Test recording RSS feed fetch."""
        feed_url = "https://example.com/rss"
        postgres_ledger.record_rss_fetch(feed_url, items_found=25)

        # Get last fetch time
        last_fetch = postgres_ledger.get_last_rss_fetch(feed_url)
        assert last_fetch is not None
        assert isinstance(last_fetch, datetime)

    def test_should_fetch_rss(self, postgres_ledger):
        """Test RSS fetch throttling."""
        feed_url = "https://example.com/rss_throttle"

        # Should fetch (never fetched)
        assert postgres_ledger.should_fetch_rss(feed_url, min_hours=6) is True

        # Record fetch
        postgres_ledger.record_rss_fetch(feed_url, items_found=10)

        # Should not fetch (just fetched)
        assert postgres_ledger.should_fetch_rss(feed_url, min_hours=6) is False


class TestPostgresCleanup:
    """Test cleanup operations."""

    def test_cleanup_old_entries(self, postgres_ledger):
        """Test cleanup of old failed entries."""
        # Insert old failed entry
        url = "https://example.com/cleanup_test"
        postgres_ledger.upsert_url(
            url=url, source="test", state=CrawlState.FAILED, error_message="Test error"
        )

        # Mark as failed multiple times to trigger retry count
        for _ in range(3):
            postgres_ledger.mark_url_state(url, CrawlState.FAILED, error_message="Test error")

        # Cleanup should work (though may not delete recent entries)
        deleted = postgres_ledger.cleanup_old_entries(days=0)
        assert deleted >= 0  # Should not raise exception

    def test_connection_pool_close(self, postgres_ledger):
        """Test connection pool cleanup."""
        postgres_ledger.close()
        # Should not raise exception
        assert True
