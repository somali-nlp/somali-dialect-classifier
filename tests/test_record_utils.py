"""
Unit tests for record utilities.

Pure functions are trivial to test without mocks.
"""

import json

from somali_dialect_classifier.quality.record_utils import (
    build_silver_record,
    count_tokens,
    generate_record_id,
    generate_text_hash,
)


class TestHashGeneration:
    """Test hash generation functions."""

    def test_text_hash_deterministic(self):
        """Same text should produce same hash."""
        text = "hello world"
        hash1 = generate_text_hash(text)
        hash2 = generate_text_hash(text)
        assert hash1 == hash2

    def test_text_hash_different(self):
        """Different text should produce different hash."""
        hash1 = generate_text_hash("hello")
        hash2 = generate_text_hash("world")
        assert hash1 != hash2

    def test_text_hash_length(self):
        """SHA256 should produce 64-character hex string."""
        hash_val = generate_text_hash("test")
        assert len(hash_val) == 64

    def test_record_id_deterministic(self):
        """Same components should produce same ID."""
        id1 = generate_record_id("title", "url")
        id2 = generate_record_id("title", "url")
        assert id1 == id2

    def test_record_id_different(self):
        """Different components should produce different ID."""
        id1 = generate_record_id("title1", "url1")
        id2 = generate_record_id("title2", "url2")
        assert id1 != id2


class TestTokenCounting:
    """Test token counting."""

    def test_count_tokens_simple(self):
        assert count_tokens("hello world") == 2

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0  # Empty string after split

    def test_count_tokens_multiple_spaces(self):
        assert count_tokens("word1    word2") == 2


class TestBuildSilverRecord:
    """Test silver record building."""

    def test_build_record_minimal(self):
        record = build_silver_record(
            text="Test content",
            title="Test Title",
            source="Wikipedia-Somali",
            url="https://so.wikipedia.org/wiki/Test",
            date_accessed="2025-01-01",
        )

        assert record["text"] == "Test content"
        assert record["title"] == "Test Title"
        assert record["source"] == "Wikipedia-Somali"
        assert record["url"] == "https://so.wikipedia.org/wiki/Test"
        assert record["date_accessed"] == "2025-01-01"
        assert "id" in record
        assert "text_hash" in record
        assert "tokens" in record

    def test_build_record_with_metadata(self):
        metadata = {"wiki_code": "sowiki", "dump_url": "https://..."}
        record = build_silver_record(
            text="Test",
            title="Title",
            source="Wikipedia-Somali",
            url="https://...",
            date_accessed="2025-01-01",
            source_metadata=metadata,
        )

        # Verify metadata is JSON-serialized (string, not dict)
        assert isinstance(record["source_metadata"], str)
        assert json.loads(record["source_metadata"]) == metadata

    def test_build_record_defaults(self):
        record = build_silver_record(
            text="Test",
            title="Title",
            source="Wikipedia-Somali",
            url="https://...",
            date_accessed="2025-01-01",
        )

        assert record["source_type"] == "wiki"
        assert record["language"] == "so"
        assert record["license"] == "CC-BY-SA-3.0"
        assert record["pipeline_version"] == "2.1.0"  # Updated to current version
        # Verify empty metadata is JSON-serialized empty object
        assert record["source_metadata"] == "{}"
        assert json.loads(record["source_metadata"]) == {}
        assert record["date_published"] is None
        assert record["topic"] is None
