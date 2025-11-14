"""
Tests for RecordBuilder service.

Verifies silver record construction.
"""

import pytest

from somali_dialect_classifier.preprocessing.raw_record import RawRecord
from somali_dialect_classifier.preprocessing.record_builder import RecordBuilder


class TestRecordBuilder:
    """Test suite for RecordBuilder."""

    def test_initialization(self):
        """Test RecordBuilder initialization."""
        builder = RecordBuilder(
            source="Test-Source",
            date_accessed="2025-01-01",
            run_id="test_run_123",
            schema_version="1.0",
        )
        assert builder.source == "Test-Source"
        assert builder.date_accessed == "2025-01-01"
        assert builder.run_id == "test_run_123"
        assert builder.schema_version == "1.0"

    def test_build_silver_record(self):
        """Test building a silver record."""
        builder = RecordBuilder(
            source="Test-Source", date_accessed="2025-01-01", run_id="test_run_123"
        )
        raw_record = RawRecord(
            title="Test Title",
            text="Original raw text",
            url="https://example.com/test",
            metadata={"category": "test", "date_published": "2025-01-01"},
        )
        record = builder.build_silver_record(
            raw_record=raw_record,
            cleaned_text="Cleaned text content",
            filter_metadata={"langid": "so"},
            source_type="news",
            license_str="CC-BY-SA-3.0",
            domain="news",
            register="formal",
        )
        # Verify core fields
        assert record["title"] == "Test Title"
        assert record["text"] == "Cleaned text content"
        assert record["url"] == "https://example.com/test"
        assert record["source"] == "Test-Source"
        assert record["source_type"] == "news"
        assert record["license"] == "CC-BY-SA-3.0"
        assert record["domain"] == "news"
        assert record["register"] == "formal"
        # Verify provenance fields
        assert record["schema_version"] == "1.0"
        assert record["run_id"] == "test_run_123"
        assert record["date_accessed"] == "2025-01-01"
        # Verify computed fields
        assert "id" in record
        assert "text_hash" in record
        assert record["tokens"] > 0

    def test_metadata_merging(self):
        """Test that metadata from multiple sources is merged correctly."""
        builder = RecordBuilder(
            source="Test-Source", date_accessed="2025-01-01", run_id="test_run_123"
        )
        raw_record = RawRecord(
            title="Test",
            text="Text",
            url="https://example.com",
            metadata={"from_raw": "value1", "shared": "raw_value"},
        )
        source_metadata = {"from_source": "value2", "shared": "source_value"}
        filter_metadata = {"from_filter": "value3", "shared": "filter_value"}
        record = builder.build_silver_record(
            raw_record=raw_record,
            cleaned_text="Cleaned",
            filter_metadata=filter_metadata,
            source_type="web",
            license_str="MIT",
            domain="general",
            register="informal",
            source_metadata=source_metadata,
        )
        # Parse source_metadata JSON string
        import json

        merged = json.loads(record["source_metadata"])
        # Later values should override earlier ones
        assert merged["shared"] == "filter_value"
        assert merged["from_raw"] == "value1"
        assert merged["from_source"] == "value2"
        assert merged["from_filter"] == "value3"

    def test_source_id_extraction(self):
        """Test that source_id is extracted from metadata."""
        builder = RecordBuilder(
            source="Test-Source", date_accessed="2025-01-01", run_id="test_run_123"
        )
        # Test with corpus_id
        raw_record1 = RawRecord(
            title="Test",
            text="Text",
            url="https://example.com",
            metadata={"corpus_id": "corpus_123"},
        )
        record1 = builder.build_silver_record(
            raw_record=raw_record1,
            cleaned_text="Cleaned",
            filter_metadata={},
            source_type="corpus",
            license_str="MIT",
            domain="general",
            register="formal",
        )
        assert record1["source_id"] == "corpus_123"
        # Test with source_id
        raw_record2 = RawRecord(
            title="Test",
            text="Text",
            url="https://example.com",
            metadata={"source_id": "source_456"},
        )
        record2 = builder.build_silver_record(
            raw_record=raw_record2,
            cleaned_text="Cleaned",
            filter_metadata={},
            source_type="news",
            license_str="MIT",
            domain="news",
            register="formal",
        )
        assert record2["source_id"] == "source_456"

    def test_add_metadata(self):
        """Test adding additional metadata to a record."""
        builder = RecordBuilder(
            source="Test-Source", date_accessed="2025-01-01", run_id="test_run_123"
        )
        record = {"id": "test_id", "text": "test"}
        updated = builder.add_metadata(record, processing_duration=1.5, quality_score=0.95)
        assert updated["processing_duration"] == 1.5
        assert updated["quality_score"] == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
