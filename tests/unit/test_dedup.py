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


class TestRedirectStubDedup:
    """TD-021: identical text under different URLs/titles must be deduplicated.

    Simulates Wikipedia redirect/stub pages where the cleaned text is byte-for-byte
    identical but the page title and URL differ (e.g., 'SOFEN' vs
    'Somali Formal Education Network (SOFEN)').
    """

    def test_second_record_with_same_text_is_duplicate(self):
        """process_document: second call with identical text → is_duplicate=True."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        text = "SOFEN waa hay'ad waxbarashada rasmiga ah ee Soomaaliya."

        is_dup1, _, _, hash1, _ = engine.process_document(
            text, "https://so.wikipedia.org/wiki/SOFEN"
        )
        is_dup2, _, canonical, hash2, _ = engine.process_document(
            text, "https://so.wikipedia.org/wiki/Somali_Formal_Education_Network"
        )

        assert not is_dup1, "First occurrence must not be flagged as duplicate"
        assert is_dup2, "Second occurrence with identical text must be flagged as duplicate"
        assert hash1 == hash2
        assert canonical == "https://so.wikipedia.org/wiki/SOFEN"

    def test_unique_texts_are_not_flagged(self):
        """process_document: different texts are never duplicates."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        text_a = "Soomaaliya waa dal weyn oo ku yaalla Geeska Afrika."
        text_b = "Muqdisho waa caasimadda Jamhuuriyadda Federaalka Soomaaliya."

        is_dup_a, *_ = engine.process_document(text_a, "https://so.wikipedia.org/wiki/Somalia")
        is_dup_b, *_ = engine.process_document(text_b, "https://so.wikipedia.org/wiki/Mogadishu")

        assert not is_dup_a
        assert not is_dup_b

    def test_four_redirect_variants_deduplicated(self):
        """All four redirect titles for same stub text → only first is kept."""
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine

        config = DedupConfig(enable_minhash=False, hash_fields=["text"])
        engine = DedupEngine(config=config)

        stub_text = "SOFEN waa ururka waxbarashada."
        variants = [
            ("SOFEN", "https://so.wikipedia.org/wiki/SOFEN"),
            ("Sofen", "https://so.wikipedia.org/wiki/Sofen"),
            (
                "Somali Formal Education Network",
                "https://so.wikipedia.org/wiki/Somali_Formal_Education_Network",
            ),
            (
                "SOMALI FORMAL EDUCATION NETWORK (SOFEN)",
                "https://so.wikipedia.org/wiki/SOMALI_FORMAL_EDUCATION_NETWORK",
            ),
        ]

        results = []
        for _title, url in variants:
            is_dup, *_ = engine.process_document(stub_text, url)
            results.append(is_dup)

        assert results[0] is False, "First variant must be unique"
        assert all(results[1:]), "Remaining variants must be flagged as duplicates"


class TestBasePipelineDedupGuard:
    """TD-021: BasePipeline._process_record_stream must reject exact-text duplicates.

    The dedup guard fires AFTER text cleaning so that normalised text hashes
    correctly identify pages that have identical content despite different
    raw markup, titles, or URLs.
    """

    def _build_processor(self, tmp_path):
        """Return a minimal concrete subclass of BasePipeline with a real DedupEngine."""

        from somdialc.ingestion.base_pipeline import BasePipeline
        from somdialc.ingestion.dedup import DedupConfig, DedupEngine
        from somdialc.quality.text_cleaners import TextCleaningPipeline, WhitespaceCleaner

        staging = tmp_path / "staging.jsonl"

        class MinimalProcessor(BasePipeline):
            def __init__(self, records, dedup_engine, **kw):
                self._records = records
                self.dedup = dedup_engine
                self.ledger = None
                super().__init__(source="wikipedia-somali", **kw)
                self.staging_file = staging

            def _extract_records(self):
                yield from self._records

            def _create_cleaner(self):
                return TextCleaningPipeline([WhitespaceCleaner()])

            def _get_source_type(self):
                return "wiki"

            def _get_license(self):
                return "CC-BY-SA-3.0"

            def _get_source_metadata(self):
                return {}

            def _get_domain(self):
                return "encyclopedia"

            def _get_register(self):
                return "encyclopedic"

            def download(self):
                return None

            def extract(self):
                return self.staging_file

        dedup = DedupEngine(DedupConfig(enable_minhash=False, hash_fields=["text"]))
        return MinimalProcessor, dedup, staging

    def test_identical_text_records_deduplicated_in_process(self, tmp_path):
        """_process_record_stream drops second record whose cleaned text is identical."""
        from unittest.mock import MagicMock, patch

        from somdialc.ingestion.base_pipeline import RawRecord

        minimal_processor_cls, dedup, staging = self._build_processor(tmp_path)

        text = "Cunto samaysiga waa farshaxan aad loo jeclahay."
        records = [
            RawRecord(
                title="Cunto samaysiga",
                text=text,
                url="https://so.wikipedia.org/wiki/Cunto_samaysiga",
            ),
            RawRecord(title="Karinta", text=text, url="https://so.wikipedia.org/wiki/Karinta"),
        ]
        staging.touch()

        with patch("somdialc.infra.tracking.MLFlowTracker"):
            proc = minimal_processor_cls(records=records, dedup_engine=dedup)
            proc.metrics = MagicMock()

        processed_file = tmp_path / "processed.txt"
        checkpoint = tmp_path / "ckpt.json"

        with open(processed_file, "w") as fout:
            n_processed, n_filtered, written = proc._process_record_stream(
                last_processed_index=0,
                checkpoint_path=checkpoint,
                fout=fout,
            )

        assert n_processed == 1, f"Expected 1 unique record, got {n_processed}"
        assert n_filtered == 1, f"Expected 1 filtered record (duplicate), got {n_filtered}"

    def test_different_text_records_both_kept(self, tmp_path):
        """_process_record_stream keeps all records when texts differ."""
        from unittest.mock import MagicMock, patch

        from somdialc.ingestion.base_pipeline import RawRecord

        minimal_processor_cls, dedup, staging = self._build_processor(tmp_path)

        staging.touch()

        records = [
            RawRecord(
                title="Soomaaliya",
                text="Soomaaliya waa dal weyn oo ku yaalla Geeska Afrika.",
                url="https://so.wikipedia.org/wiki/Soomaaliya",
            ),
            RawRecord(
                title="Muqdisho",
                text="Muqdisho waa caasimadda Jamhuuriyadda Federaalka Soomaaliya.",
                url="https://so.wikipedia.org/wiki/Muqdisho",
            ),
            RawRecord(
                title="Afrika",
                text="Afrika waa qaaradda ugu weyn adduunka marka loo eego tirada dadka.",
                url="https://so.wikipedia.org/wiki/Afrika",
            ),
        ]

        with patch("somdialc.infra.tracking.MLFlowTracker"):
            proc = minimal_processor_cls(records=records, dedup_engine=dedup)
            proc.metrics = MagicMock()

        processed_file = tmp_path / "processed2.txt"
        checkpoint = tmp_path / "ckpt2.json"

        with open(processed_file, "w") as fout:
            n_processed, n_filtered, written = proc._process_record_stream(
                last_processed_index=0,
                checkpoint_path=checkpoint,
                fout=fout,
            )

        assert n_processed == 3, f"Expected 3 unique records, got {n_processed}"
        assert n_filtered == 0, f"Expected 0 filtered records, got {n_filtered}"


# Run with: pytest tests/unit/test_dedup.py -v -s
