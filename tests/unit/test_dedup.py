"""
Unit tests for deduplication engine LRU hash storage.

Tests memory-bounded LRU hash set implementation to prevent unbounded memory
growth during large-scale deduplication.

Requirements:
- Memory bounded to maxsize entries regardless of document count
- LRU eviction when at capacity
- No false positives (never mark unique as duplicate)
- Access order updates on __contains__ check
"""

import os
from unittest.mock import MagicMock

import pytest


class TestLRUHashSet:
    """Unit tests for LRUHashSet class."""

    def test_initialization(self):
        """Verify LRUHashSet initializes correctly."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=100)

        assert cache.maxsize == 100
        assert len(cache) == 0

    def test_initialization_invalid_maxsize(self):
        """Verify raises ValueError for invalid maxsize."""
        from somdialc.ingestion.dedup import LRUHashSet

        with pytest.raises(ValueError, match="maxsize must be positive"):
            LRUHashSet(maxsize=0)

        with pytest.raises(ValueError, match="maxsize must be positive"):
            LRUHashSet(maxsize=-10)

    def test_add_single_hash(self):
        """Verify adding single hash works."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=10)
        cache.add("hash1")

        assert len(cache) == 1
        assert "hash1" in cache

    def test_add_multiple_hashes(self):
        """Verify adding multiple hashes works."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=10)
        cache.add("hash1")
        cache.add("hash2")
        cache.add("hash3")

        assert len(cache) == 3
        assert "hash1" in cache
        assert "hash2" in cache
        assert "hash3" in cache

    def test_add_duplicate_hash_no_size_increase(self):
        """Verify adding duplicate hash doesn't increase size."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=10)
        cache.add("hash1")
        cache.add("hash1")  # Duplicate
        cache.add("hash1")  # Duplicate again

        assert len(cache) == 1
        assert "hash1" in cache

    def test_lru_eviction_at_capacity(self):
        """Verify LRU eviction when at capacity."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=3)

        # Add 3 hashes (fill to capacity)
        cache.add("hash1")
        cache.add("hash2")
        cache.add("hash3")

        assert len(cache) == 3

        # Add 4th hash (should evict hash1, the oldest)
        cache.add("hash4")

        assert len(cache) == 3  # Size bounded
        assert "hash1" not in cache  # Evicted
        assert "hash2" in cache
        assert "hash3" in cache
        assert "hash4" in cache

    def test_lru_eviction_order(self):
        """Verify LRU evicts oldest unused entries first."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=3)

        # Add 3 hashes
        cache.add("hash1")
        cache.add("hash2")
        cache.add("hash3")

        # Access hash1 (moves to end)
        assert "hash1" in cache

        # Add hash4 (should evict hash2, not hash1)
        cache.add("hash4")

        assert "hash1" in cache  # Still present (was accessed)
        assert "hash2" not in cache  # Evicted (oldest unused)
        assert "hash3" in cache
        assert "hash4" in cache

    def test_contains_updates_access_order(self):
        """Verify __contains__ updates access order."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=3)

        cache.add("hash1")
        cache.add("hash2")
        cache.add("hash3")

        # Access hash1 multiple times
        _ = "hash1" in cache
        _ = "hash1" in cache

        # Add 2 new hashes (should evict hash2 and hash3)
        cache.add("hash4")
        cache.add("hash5")

        assert "hash1" in cache  # Still present (recently accessed)
        assert "hash2" not in cache  # Evicted
        assert "hash3" not in cache  # Evicted
        assert "hash4" in cache
        assert "hash5" in cache

    def test_no_false_positives(self):
        """Verify NEVER marks unique items as duplicate."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=10)

        # Add some hashes
        cache.add("hash1")
        cache.add("hash2")

        # Check for non-existent hash
        assert "hash3" not in cache
        assert "hash999" not in cache
        assert "completely_different" not in cache

    def test_false_negatives_acceptable(self):
        """Verify false negatives occur after eviction (expected behavior)."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=2)

        cache.add("hash1")
        cache.add("hash2")
        cache.add("hash3")  # Evicts hash1

        # hash1 was evicted, so checking for it returns False (false negative)
        assert "hash1" not in cache
        assert "hash2" in cache
        assert "hash3" in cache

    def test_clear(self):
        """Verify clear() removes all hashes."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=10)

        cache.add("hash1")
        cache.add("hash2")
        cache.add("hash3")

        assert len(cache) == 3

        cache.clear()

        assert len(cache) == 0
        assert "hash1" not in cache
        assert "hash2" not in cache
        assert "hash3" not in cache

    def test_large_scale_eviction(self):
        """Verify eviction works correctly with many entries."""
        from somdialc.ingestion.dedup import LRUHashSet

        cache = LRUHashSet(maxsize=100)

        # Add 200 hashes (should evict first 100)
        for i in range(200):
            cache.add(f"hash{i}")

        assert len(cache) == 100

        # First 100 should be evicted
        for i in range(100):
            assert f"hash{i}" not in cache

        # Last 100 should remain
        for i in range(100, 200):
            assert f"hash{i}" in cache

    def test_memory_bounded(self):
        """Verify memory stays bounded even with unlimited additions."""
        from somdialc.ingestion.dedup import LRUHashSet

        maxsize = 1000
        cache = LRUHashSet(maxsize=maxsize)

        # Add 10x capacity
        for i in range(maxsize * 10):
            cache.add(f"hash{i}")

        # Size should never exceed maxsize
        assert len(cache) == maxsize
        assert len(cache) <= maxsize


class TestDedupEngineWithLRU:
    """Integration tests for DedupEngine with LRU hash storage."""

    def test_check_file_duplicate_uses_passed_ledger(self, tmp_path):
        """File dedup queries the ledger argument rather than a missing instance attribute."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        engine = DedupEngine(config=DedupConfig(enable_minhash=False))
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content for file-level dedup", encoding="utf-8")

        mock_ledger = MagicMock()
        mock_ledger.check_file_checksum.return_value = None

        is_duplicate, checksum = engine.check_file_duplicate(
            filepath=test_file,
            ledger=mock_ledger,
            source="test-source",
        )

        assert not is_duplicate
        assert checksum is not None
        mock_ledger.check_file_checksum.assert_called_once_with(checksum, "test-source")

    def test_dedup_engine_uses_lru_cache(self):
        """Verify DedupEngine initializes with LRUHashSet."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine, LRUHashSet

        config = DedupConfig(enable_minhash=False)
        engine = DedupEngine(config=config)

        assert isinstance(engine.seen_hashes, LRUHashSet)

    def test_dedup_engine_respects_env_cache_size(self, monkeypatch):
        """Verify DEDUP_CACHE_SIZE environment variable is respected."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        monkeypatch.setenv("DEDUP_CACHE_SIZE", "5000")

        config = DedupConfig(enable_minhash=False)
        engine = DedupEngine(config=config)

        assert engine.seen_hashes.maxsize == 5000

    def test_dedup_engine_default_cache_size(self):
        """Verify default cache size is 100,000."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        # Ensure env var not set
        if "DEDUP_CACHE_SIZE" in os.environ:
            del os.environ["DEDUP_CACHE_SIZE"]

        config = DedupConfig(enable_minhash=False)
        engine = DedupEngine(config=config)

        assert engine.seen_hashes.maxsize == 100_000

    def test_exact_duplicate_detection_with_lru(self):
        """Verify exact duplicate detection works with LRU cache."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        # Process same document twice
        is_dup1, _, _, hash1, _ = engine.process_document("Hello world", "url1")
        is_dup2, _, _, hash2, _ = engine.process_document("Hello world", "url2")

        assert not is_dup1  # First is unique
        assert is_dup2  # Second is duplicate
        assert hash1 == hash2

    def test_hash_to_url_bounded(self, monkeypatch):
        """Verify hash_to_url dict is bounded to same capacity."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        monkeypatch.setenv("DEDUP_CACHE_SIZE", "10")

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        # Process 20 unique documents (2x capacity)
        for i in range(20):
            engine.process_document(f"Document {i}", f"url{i}")

        # hash_to_url should not exceed capacity
        assert len(engine.hash_to_url) <= 10

    def test_no_false_positives_in_dedup_engine(self):
        """Verify DedupEngine never has false positives."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        # Process 100 unique documents
        results = []
        for i in range(100):
            is_dup, _, _, _, _ = engine.process_document(f"Unique doc {i}", f"url{i}")
            results.append(is_dup)

        # NONE should be marked as duplicate (all are unique)
        assert not any(results), "No unique documents should be marked as duplicates"

    def test_false_negatives_after_eviction(self, monkeypatch):
        """Verify false negatives occur after LRU eviction."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        monkeypatch.setenv("DEDUP_CACHE_SIZE", "5")

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        # Process 5 unique documents (fill cache)
        for i in range(5):
            engine.process_document(f"Doc {i}", f"url{i}")

        # Process 5 more (evicts first 5)
        for i in range(5, 10):
            engine.process_document(f"Doc {i}", f"url{i}")

        # Re-process first document (should NOT be detected as duplicate due to eviction)
        is_dup, _, _, _, _ = engine.process_document("Doc 0", "url0_duplicate")

        # This is a false negative (acceptable due to LRU eviction)
        assert not is_dup


class TestMemoryBenchmark:
    """Benchmark tests for memory usage (informational)."""

    def test_memory_usage_bounded(self, monkeypatch):
        """Benchmark: Verify memory stays bounded with large dataset."""
        import sys

        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        monkeypatch.setenv("DEDUP_CACHE_SIZE", "10000")

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        # Measure initial size
        initial_size = sys.getsizeof(engine.seen_hashes._store)

        # Process 50k unique documents (5x cache capacity)
        for i in range(50_000):
            engine.process_document(f"Document content number {i}", f"https://example.com/doc{i}")

        # Measure final size
        final_size = sys.getsizeof(engine.seen_hashes._store)

        # Cache should be at capacity
        assert len(engine.seen_hashes) == 10_000

        # Memory growth should be bounded (not proportional to 50k docs)
        # Final size should be roughly stable (within 2x of capacity-based size)
        print("\nMemory benchmark:")
        print(f"  Initial size: {initial_size:,} bytes")
        print(f"  Final size: {final_size:,} bytes")
        print(f"  Cache entries: {len(engine.seen_hashes):,}")
        print(f"  Capacity: {engine.seen_hashes.maxsize:,}")

        # Verify bounded (should not grow indefinitely)
        assert final_size < 10_000_000  # Less than 10MB for 10k entries


class TestMinHashLSHURLCollision:
    """LSH must accept multiple texts that share a URL (e.g., Sprakbanken corpora)."""

    def test_add_document_distinct_texts_same_url(self):
        """Distinct texts under one URL must both be indexed without raising."""
        pytest.importorskip("datasketch")

        from somdialc.ingestion.dedup.lsh import MinHashDeduplicator

        dedup = MinHashDeduplicator(
            enable_sharding=False,  # exercise the monolithic path explicitly
            similarity_threshold=0.5,
        )

        # Sprakbanken-style: corpus URL reused across many distinct texts.
        corpus_url = "https://spraakbanken.gu.se/korp/?mode=somali#?corpus=somali-1971-79"

        sig1 = dedup.add_document(
            corpus_url, "Buugaagta xisaabta hooyo iyo aabbe waxay barteen carruurta."
        )
        sig2 = dedup.add_document(
            corpus_url, "Geel iyo lo' iyo idaad badan ayuu reer guuraaga lahaa."
        )

        assert sig1 != sig2
        assert len(dedup.document_hashes) == 2
        # Both signatures map back to the shared URL.
        assert dedup.document_hashes[sig1] == corpus_url
        assert dedup.document_hashes[sig2] == corpus_url

    def test_add_document_idempotent_on_same_text(self):
        """Inserting the same text twice is a no-op, never raises."""
        pytest.importorskip("datasketch")

        from somdialc.ingestion.dedup.lsh import MinHashDeduplicator

        dedup = MinHashDeduplicator(enable_sharding=False)
        text = "Soomaaliya waa dal weyn oo ku yaalla geeska Afrika."

        sig_a = dedup.add_document("https://example.com/a", text)
        sig_b = dedup.add_document("https://example.com/b", text)

        assert sig_a == sig_b
        assert len(dedup.document_hashes) == 1


# Run with: pytest tests/unit/test_dedup.py -v -s
