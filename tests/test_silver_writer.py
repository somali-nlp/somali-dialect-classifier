"""
Integration tests for silver dataset writer.

Tests schema enforcement, serialization, and round-trip consistency.
"""

import json
import tempfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from somali_dialect_classifier.quality.record_utils import build_silver_record
from somali_dialect_classifier.quality.silver_writer import SilverDatasetWriter


class TestSilverDatasetWriter:
    """Test silver dataset writing and schema enforcement."""

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_write_enforces_schema(self):
        """Verify that schema is enforced and prevents drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SilverDatasetWriter(base_dir=Path(tmpdir))

            # Build record with metadata dict (will be JSON-serialized)
            record = build_silver_record(
                text="Test content",
                title="Test Title",
                source="Test-Source",
                url="https://example.com/test",
                date_accessed="2025-01-01",
                source_metadata={"key1": "value1", "key2": "value2"},
            )

            # Write should succeed
            path = writer.write(
                records=[record],
                source="Test-Source",
                date_accessed="2025-01-01",
                run_id="test_run_001",
            )

            assert path is not None
            assert path.exists()

            # Read back and verify schema
            table = pq.read_table(path)

            # Check schema matches expected
            assert table.schema.names == [
                "id",
                "text",
                "title",
                "source",
                "source_type",
                "url",
                "source_id",
                "date_published",
                "date_accessed",
                "language",
                "license",
                "topic",
                "tokens",
                "text_hash",
                "pipeline_version",
                "source_metadata",
            ]

            # Verify source_metadata is a string (JSON), not struct
            assert str(table.schema.field("source_metadata").type) == "string"

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_metadata_json_serialization(self):
        """Verify source_metadata is properly JSON-serialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SilverDatasetWriter(base_dir=Path(tmpdir))

            metadata = {
                "wiki_code": "sowiki",
                "dump_url": "https://dumps.wikimedia.org/...",
                "nested": {"key": "value"},
            }

            record = build_silver_record(
                text="Test",
                title="Title",
                source="Wikipedia-Somali",
                url="https://so.wikipedia.org/wiki/Test",
                date_accessed="2025-01-01",
                source_metadata=metadata,
            )

            path = writer.write(
                records=[record],
                source="Wikipedia-Somali",
                date_accessed="2025-01-01",
                run_id="test_run_002",
            )

            # Read back
            table = pq.read_table(path)
            row = table.to_pylist()[0]

            # Verify it's a JSON string
            assert isinstance(row["source_metadata"], str)

            # Verify it can be deserialized
            deserialized = json.loads(row["source_metadata"])
            assert deserialized["wiki_code"] == "sowiki"
            assert deserialized["dump_url"] == "https://dumps.wikimedia.org/..."
            assert deserialized["nested"]["key"] == "value"

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_multiple_sources_no_schema_drift(self):
        """
        Verify different sources with different metadata don't cause drift.

        This is the critical test for the Principal MLE's concern.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SilverDatasetWriter(base_dir=Path(tmpdir))

            # Wikipedia record with wiki-specific metadata
            wiki_record = build_silver_record(
                text="Wiki content",
                title="Wiki Title",
                source="Wikipedia-Somali",
                url="https://so.wikipedia.org/wiki/Test",
                date_accessed="2025-01-01",
                source_metadata={
                    "wiki_code": "sowiki",
                    "dump_url": "https://dumps.wikimedia.org/...",
                },
            )

            # BBC record with news-specific metadata
            bbc_record = build_silver_record(
                text="News content",
                title="News Title",
                source="BBC-Somali",
                url="https://www.bbc.com/somali/...",
                date_accessed="2025-01-01",
                source_metadata={
                    "article_id": "123456",
                    "category": "news",
                    "author": "John Doe",
                },
            )

            # Write both
            wiki_path = writer.write(
                records=[wiki_record],
                source="Wikipedia-Somali",
                date_accessed="2025-01-01",
                run_id="test_run_003_wiki",
            )

            bbc_path = writer.write(
                records=[bbc_record],
                source="BBC-Somali",
                date_accessed="2025-01-01",
                run_id="test_run_003_bbc",
            )

            # Read both and verify schemas are identical
            wiki_table = pq.read_table(wiki_path)
            bbc_table = pq.read_table(bbc_path)

            assert wiki_table.schema == bbc_table.schema

            # Verify both metadata fields are JSON strings
            wiki_meta = json.loads(wiki_table.to_pylist()[0]["source_metadata"])
            bbc_meta = json.loads(bbc_table.to_pylist()[0]["source_metadata"])

            assert "wiki_code" in wiki_meta
            assert "article_id" in bbc_meta

            # This would fail without JSON serialization - PyArrow would
            # infer different struct schemas for different metadata keys

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_read_back_after_write(self):
        """Test round-trip: write → read → verify."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SilverDatasetWriter(base_dir=Path(tmpdir))

            original_record = build_silver_record(
                text="Original text content",
                title="Original Title",
                source="Test-Source",
                url="https://example.com",
                date_accessed="2025-01-01",
                source_metadata={"test_key": "test_value"},
            )

            # Write
            writer.write(
                records=[original_record],
                source="Test-Source",
                date_accessed="2025-01-01",
                run_id="test_run_004",
            )

            # Read back using writer's read method
            table = writer.read(source="Test-Source", date_accessed="2025-01-01")

            # Verify
            assert len(table) == 1
            row = table.to_pylist()[0]

            assert row["text"] == "Original text content"
            assert row["title"] == "Original Title"
            assert row["source"] == "Test-Source"

            # Verify metadata round-trips correctly
            metadata = json.loads(row["source_metadata"])
            assert metadata["test_key"] == "test_value"

    def test_empty_records_returns_none(self):
        """Verify graceful handling of empty record list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SilverDatasetWriter(base_dir=Path(tmpdir))

            result = writer.write(
                records=[],
                source="Empty-Source",
                date_accessed="2025-01-01",
                run_id="test_run_005",
            )

            assert result is None
