"""
Load testing for PostgreSQL backend.

Simulates production-scale concurrent operations to validate
performance and scalability at 10x current load.
"""

import os
import threading
import time

import pytest

from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger, CrawlState

# Skip all tests if PostgreSQL is not available
postgres_available = os.getenv("POSTGRES_HOST") is not None

pytestmark = pytest.mark.skipif(
    not postgres_available, reason="PostgreSQL not available (POSTGRES_HOST not set)"
)


@pytest.fixture
def ledger():
    """Create PostgreSQL ledger for load testing."""
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


class TestConcurrentWrites:
    """Test concurrent write operations."""

    def test_5_concurrent_sources(self, ledger):
        """
        Test 5 concurrent sources (realistic production scenario).

        Simulates quarterly refresh where all 5 sources run simultaneously.
        """
        errors = []
        metrics = {"total_writes": 0, "start_time": time.time()}

        def source_worker(source_id):
            """Simulate a source pipeline run."""
            try:
                source = f"source_{source_id}"
                for i in range(20):  # 20 URLs per source
                    url = f"https://example.com/{source}/url_{i}"
                    ledger.discover_url(url, source=source)
                    metrics["total_writes"] += 1
            except Exception as e:
                errors.append(f"Source {source_id}: {e}")

        # Start 5 concurrent sources
        threads = [threading.Thread(target=source_worker, args=(i,)) for i in range(5)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"

        # Performance check
        throughput = metrics["total_writes"] / duration
        print(f"\n5 sources - {metrics['total_writes']} writes in {duration:.2f}s")
        print(f"Throughput: {throughput:.1f} ops/s")

        # Should complete in reasonable time
        assert duration < 10, f"Test took {duration}s (expected < 10s)"
        assert throughput > 10, f"Throughput {throughput} ops/s too low"

    def test_10x_concurrent_writes(self, ledger):
        """
        Test 10x scale: 50 concurrent threads writing simultaneously.

        This simulates extreme load beyond expected production scale.
        """
        errors = []
        write_counts = {"total": 0}

        def worker(thread_id):
            try:
                for i in range(10):  # 10 URLs per thread
                    url = f"https://example.com/load_test/{thread_id}/{i}"
                    ledger.discover_url(url, source=f"source_{thread_id % 5}")
                    write_counts["total"] += 1
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

        # 50 concurrent threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        # Verify no deadlocks
        assert len(errors) == 0, f"Errors at 10x scale: {errors}"

        # Performance metrics
        throughput = write_counts["total"] / duration
        print(f"\n10x scale - {write_counts['total']} writes in {duration:.2f}s")
        print(f"Throughput: {throughput:.1f} ops/s")

        # Should handle load without deadlocks
        assert duration < 20, f"10x test took {duration}s (too slow)"
        assert write_counts["total"] == 500, "Not all writes completed"


class TestQueryPerformance:
    """Test query performance under load."""

    def test_concurrent_reads_and_writes(self, ledger):
        """Test concurrent reads and writes."""
        errors = []
        read_latencies = []
        write_latencies = []

        # Pre-populate data
        for i in range(100):
            ledger.discover_url(f"https://example.com/rw_test/{i}", source="test")

        def read_worker():
            try:
                for i in range(50):
                    start = time.time()
                    ledger.backend.get_url_state(f"https://example.com/rw_test/{i % 100}")
                    read_latencies.append(time.time() - start)
            except Exception as e:
                errors.append(f"Read error: {e}")

        def write_worker(worker_id):
            try:
                for i in range(50):
                    start = time.time()
                    ledger.discover_url(
                        f"https://example.com/rw_test/write_{worker_id}_{i}", source="test"
                    )
                    write_latencies.append(time.time() - start)
            except Exception as e:
                errors.append(f"Write error: {e}")

        # 5 readers + 5 writers
        readers = [threading.Thread(target=read_worker) for _ in range(5)]
        writers = [threading.Thread(target=write_worker, args=(i,)) for i in range(5)]

        threads = readers + writers

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent read/write: {errors}"

        # Calculate p95 latencies
        read_latencies.sort()
        write_latencies.sort()
        p95_read = read_latencies[int(len(read_latencies) * 0.95)] * 1000  # ms
        p95_write = write_latencies[int(len(write_latencies) * 0.95)] * 1000  # ms

        print("\nConcurrent read/write test:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  p95 read latency: {p95_read:.2f}ms")
        print(f"  p95 write latency: {p95_write:.2f}ms")

        # Performance checks
        assert p95_read < 100, f"p95 read latency {p95_read}ms exceeds 100ms"
        assert p95_write < 200, f"p95 write latency {p95_write}ms exceeds 200ms"

    def test_bulk_operations(self, ledger):
        """Test bulk insert and query operations."""
        # Bulk insert
        insert_start = time.time()
        for i in range(1000):
            ledger.discover_url(f"https://example.com/bulk/{i}", source="bulk_test")
        insert_duration = time.time() - insert_start

        # Bulk query
        query_start = time.time()
        results = ledger.backend.get_urls_by_state("bulk_test", CrawlState.DISCOVERED, limit=1000)
        query_duration = time.time() - query_start

        print("\nBulk operations:")
        print(f"  Insert: 1000 URLs in {insert_duration:.2f}s ({1000 / insert_duration:.1f} ops/s)")
        print(f"  Query: {len(results)} URLs in {query_duration:.2f}s")

        # Performance checks
        assert insert_duration < 15, f"Bulk insert took {insert_duration}s (too slow)"
        assert query_duration < 1, f"Bulk query took {query_duration}s (too slow)"
        assert len(results) >= 1000, f"Expected 1000+ results, got {len(results)}"


class TestConnectionPooling:
    """Test connection pool behavior."""

    def test_connection_pool_exhaustion(self, ledger):
        """Test behavior when connection pool is exhausted."""
        errors = []

        def heavy_worker(worker_id):
            try:
                # Each worker holds connection longer
                for i in range(5):
                    ledger.discover_url(
                        f"https://example.com/pool_test/{worker_id}/{i}", source="pool_test"
                    )
                    time.sleep(0.01)  # Simulate processing time
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # More threads than pool size (pool typically has 10 connections)
        threads = [threading.Thread(target=heavy_worker, args=(i,)) for i in range(20)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        # Should handle gracefully (queuing, not failing)
        print(f"\nConnection pool test: {len(threads)} threads in {duration:.2f}s")
        print(f"Errors: {len(errors)}")

        # Should complete without errors (connections reused from pool)
        assert len(errors) == 0, f"Connection pool errors: {errors}"
        assert duration < 15, f"Pool exhaustion test took {duration}s (too slow)"


class TestStressScenarios:
    """Test stress scenarios and edge cases."""

    def test_rapid_state_transitions(self, ledger):
        """Test rapid state transitions on same URL."""
        url = "https://example.com/rapid_state"

        # Rapid transitions: discovered -> fetched -> processed
        states = [
            (CrawlState.DISCOVERED, lambda: ledger.discover_url(url, source="stress")),
            (
                CrawlState.FETCHED,
                lambda: ledger.mark_fetched(url, http_status=200, source="stress"),
            ),
            (
                CrawlState.PROCESSED,
                lambda: ledger.mark_processed(
                    url, text_hash="hash", silver_id="s1", source="stress"
                ),
            ),
        ]

        for _ in range(10):  # Repeat 10 times
            for state, action in states:
                action()
                current_state = ledger.backend.get_url_state(url)
                assert current_state["state"] == state.value

        print("\nRapid state transitions: 30 transitions completed successfully")

    def test_concurrent_duplicate_detection(self, ledger):
        """Test concurrent duplicate detection."""
        text_hash = "shared_hash_123"
        url1 = "https://example.com/original"

        # Insert original
        ledger.discover_url(url1, source="dup_test")
        ledger.mark_processed(url1, text_hash=text_hash, silver_id="s1", source="dup_test")

        # Concurrent duplicate checks
        errors = []
        duplicate_counts = {"found": 0}

        def check_duplicate(thread_id):
            try:
                original = ledger.is_duplicate(text_hash)
                if original == url1:
                    duplicate_counts["found"] += 1
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=check_duplicate, args=(i,)) for i in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Duplicate detection errors: {errors}"
        assert duplicate_counts["found"] == 20, "Not all threads found duplicate"
        print("\nConcurrent duplicate detection: 20 threads succeeded")
