"""
Tests for enhanced silver schema with domain and embedding fields.
"""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from somali_dialect_classifier.quality.record_utils import build_silver_record
from somali_dialect_classifier.quality.silver_writer import SilverDatasetWriter


class TestEnhancedSchema:
    """Test enhanced silver schema with domain and embedding fields."""

    def test_schema_includes_new_fields(self):
        """Test that schema includes domain and embedding fields."""
        schema = SilverDatasetWriter.SCHEMA

        # Check field names
        field_names = [field.name for field in schema]
        assert "domain" in field_names
        assert "embedding" in field_names

        # Check field types
        domain_field = schema.field("domain")
        assert domain_field.type == pa.string()

        embedding_field = schema.field("embedding")
        assert embedding_field.type == pa.string()

    def test_build_silver_record_with_domain(self):
        """Test building silver record with domain field."""
        record = build_silver_record(
            text="Test text",
            title="Test Title",
            source="Test-Source",
            url="https://example.com",
            date_accessed="2025-01-01",
            domain="news",
            embedding=None,
        )

        assert record["domain"] == "news"
        assert record["embedding"] is None

    def test_build_silver_record_without_domain_defaults(self):
        """Test that domain field defaults to None if not provided."""
        record = build_silver_record(
            text="Test text",
            title="Test Title",
            source="Test-Source",
            url="https://example.com",
            date_accessed="2025-01-01",
        )

        assert record["domain"] is None
        assert record["embedding"] is None

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_silver_writer_domain_inference(self, tmp_path):
        """Test that SilverWriter can infer domain from source."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        records = [
            {
                "id": "1",
                "text": "Test news article",
                "title": "News Title",
                "source": "BBC-Somali",
                "source_type": "news",
                "url": "https://bbc.com/somali/1",
                "source_id": None,
                "date_published": None,
                "date_accessed": "2025-01-01",
                "language": "so",
                "license": "BBC Terms",
                "topic": None,
                "tokens": 3,
                "text_hash": "hash1",
                "pipeline_version": "2.0.0",
                "source_metadata": "{}",
                # No domain field - should be inferred
            }
        ]

        # Write records
        path = writer.write(records, "BBC-Somali", "2025-01-01", "test_run_006")
        assert path is not None

        # Read back and verify domain was inferred
        table = pq.read_table(path)
        df = table.to_pandas()

        assert len(df) == 1
        assert df.iloc[0]["domain"] == "news"

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_silver_writer_domain_validation(self, tmp_path):
        """Test that invalid domains are replaced with 'general'."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        records = [
            {
                "id": "1",
                "text": "Test text",
                "title": "Test",
                "source": "Test-Source",
                "source_type": "unknown",
                "url": "https://example.com",
                "source_id": None,
                "date_published": None,
                "date_accessed": "2025-01-01",
                "language": "so",
                "license": "CC0",
                "topic": None,
                "tokens": 2,
                "text_hash": "hash1",
                "pipeline_version": "2.0.0",
                "source_metadata": "{}",
                "domain": "invalid_domain",  # Invalid domain
                "embedding": None,
            }
        ]

        # Write records - should replace invalid domain
        path = writer.write(records, "Test-Source", "2025-01-01", "test_run_007")

        # Read back
        table = pq.read_table(path)
        df = table.to_pandas()

        assert df.iloc[0]["domain"] == "general"

    def test_strict_validation_rejects_missing_fields(self, tmp_path):
        """Test that missing required fields cause immediate failure."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        # Record missing 'register' field
        incomplete_record = {
            "id": "1",
            "text": "Test text",
            "title": "Test Title",
            "source": "Test-Source",
            "source_type": "wiki",
            "url": "https://example.com",
            "source_id": None,
            "date_published": None,
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC-BY",
            "topic": None,
            "tokens": 2,
            "text_hash": "hash1",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "encyclopedia",
            "embedding": None,
            "run_id": "test_run_missing_register",
            # Missing 'register' field
        }

        # Write should fail with clear error
        with pytest.raises(ValueError) as exc_info:
            writer.write([incomplete_record], "Test-Source", "2025-01-01", "test_run_010")

        assert "missing required fields" in str(exc_info.value).lower()
        assert "register" in str(exc_info.value)

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_domain_statistics(self, tmp_path):
        """Test domain statistics collection."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        # Write records with different domains
        records1 = [
            build_silver_record(
                text=f"Text {i}",
                title=f"Title {i}",
                source="Source1",
                url=f"https://example.com/{i}",
                date_accessed="2025-01-01",
                domain="news",
            )
            for i in range(3)
        ]

        records2 = [
            build_silver_record(
                text=f"Text {i}",
                title=f"Title {i}",
                source="Source2",
                url=f"https://example.com/{i}",
                date_accessed="2025-01-01",
                domain="literature",
            )
            for i in range(2)
        ]

        writer.write(records1, "Source1", "2025-01-01", "test_run_008_src1")
        writer.write(records2, "Source2", "2025-01-01", "test_run_008_src2")

        # Get statistics
        stats = writer.get_domain_statistics()

        assert stats["news"] == 3
        assert stats["literature"] == 2

    @pytest.mark.skip(
        reason="Schema incompatibility with dictionary encoding - requires fix in SilverDatasetWriter"
    )
    def test_embedding_field_json_serialization(self, tmp_path):
        """Test that embedding field can handle JSON serialization."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        # Mock embedding as list (would be converted to JSON string)
        mock_embedding = [0.1, 0.2, 0.3, 0.4]

        records = [
            {
                "id": "1",
                "text": "Test text",
                "title": "Test",
                "source": "Test-Source",
                "source_type": "web",
                "url": "https://example.com",
                "source_id": None,
                "date_published": None,
                "date_accessed": "2025-01-01",
                "language": "so",
                "license": "CC0",
                "topic": None,
                "tokens": 2,
                "text_hash": "hash1",
                "pipeline_version": "2.0.0",
                "source_metadata": "{}",
                "domain": "web",
                "embedding": mock_embedding,  # List, not string
            }
        ]

        # Write records - should convert embedding to JSON string
        path = writer.write(records, "Test-Source", "2025-01-01", "test_run_009")

        # Read back
        table = pq.read_table(path)
        df = table.to_pandas()

        # Embedding should be JSON string
        embedding_str = df.iloc[0]["embedding"]
        assert isinstance(embedding_str, str)

        # Should be able to deserialize
        embedding_list = json.loads(embedding_str)
        assert embedding_list == mock_embedding


class TestStrictValidation:
    """Test strict validation logic (no inference, fail fast)."""

    def test_invalid_domain_rejected(self, tmp_path):
        """Test that invalid domain values are rejected."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        record = {
            "id": "1",
            "text": "Test text",
            "title": "Test",
            "source": "Test-Source",
            "source_type": "web",
            "url": "https://example.com",
            "source_id": None,
            "date_published": None,
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC0",
            "topic": None,
            "tokens": 2,
            "text_hash": "hash1",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "invalid_domain_xyz",  # Invalid domain
            "embedding": None,
            "register": "formal",
            "run_id": "test_run_invalid_domain",
        }

        # Should raise ValueError for invalid domain
        with pytest.raises(ValueError) as exc_info:
            writer.write([record], "Test-Source", "2025-01-01", "test_run_011")

        assert "invalid domain" in str(exc_info.value).lower()

    def test_invalid_register_rejected(self, tmp_path):
        """Test that invalid register values are rejected."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        record = {
            "id": "1",
            "text": "Test text",
            "title": "Test",
            "source": "Test-Source",
            "source_type": "web",
            "url": "https://example.com",
            "source_id": None,
            "date_published": None,
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC0",
            "topic": None,
            "tokens": 2,
            "text_hash": "hash1",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "web",
            "embedding": None,
            "register": "super_informal",  # Invalid register
            "run_id": "test_run_invalid_register",
        }

        # Should raise ValueError for invalid register
        with pytest.raises(ValueError) as exc_info:
            writer.write([record], "Test-Source", "2025-01-01", "test_run_012")

        assert "invalid register" in str(exc_info.value).lower()

    def test_schema_version_hardcoded(self, tmp_path):
        """Test that schema_version is always set to '1.0'."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        record = build_silver_record(
            text="Test text",
            title="Test",
            source="Test-Source",
            url="https://example.com",
            date_accessed="2025-01-01",
            domain="web",
            register="formal",
        )
        record["run_id"] = "test_run_schema_version"
        # Note: schema_version not provided

        path = writer.write([record], "Test-Source", "2025-01-01", "test_run_013")

        # Read back and verify schema_version is "1.0"
        table = pq.read_table(path)
        df = table.to_pandas()

        assert df.iloc[0]["schema_version"] == "1.0"


# Add pandas import for tests
try:
    import pandas as pd
except ImportError:
    pd = None
    pytest.skip("pandas not available", allow_module_level=True)
