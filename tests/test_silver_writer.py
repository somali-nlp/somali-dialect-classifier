"""
Integration tests for silver dataset writer.

Tests schema enforcement, sidecar placement, and round-trip consistency.
"""

import json

import pyarrow.parquet as pq
import pytest

from somali_dialect_classifier.quality.record_utils import build_silver_record
from somali_dialect_classifier.quality.silver_writer import SilverDatasetWriter


def _build_test_record(source: str, url: str, date_accessed: str, **overrides) -> dict:
    """Create a contract-compliant silver record for tests."""
    record = build_silver_record(
        text=overrides.pop("text", "Test content for silver writer"),
        title=overrides.pop("title", "Test Title"),
        source=source,
        url=url,
        date_accessed=date_accessed,
        source_type=overrides.pop("source_type", "wiki"),
        license_str=overrides.pop("license_str", "CC-BY-SA-3.0"),
        source_metadata=overrides.pop("source_metadata", {"fixture": True}),
        domain=overrides.pop("domain", "encyclopedia"),
        register=overrides.pop("register", "formal"),
        source_id=overrides.pop("source_id", None),
        date_published=overrides.pop("date_published", None),
        topic=overrides.pop("topic", None),
        embedding=overrides.pop("embedding", None),
    )
    record["run_id"] = overrides.pop("run_id", "test_run_001")
    record["schema_version"] = overrides.pop("schema_version", "1.0")
    record.update(overrides)
    return record


class TestSilverDatasetWriter:
    """Test silver dataset writing and schema enforcement."""

    def test_write_enforces_schema_and_separates_sidecars(self, tmp_path):
        """Writer stores parquet in partitions and sidecars under _metadata."""
        writer = SilverDatasetWriter(base_dir=tmp_path)
        date_accessed = "2025-01-01"
        record = _build_test_record(
            source="Test-Source",
            url="https://example.com/test",
            date_accessed=date_accessed,
            run_id="test_run_001",
        )

        path = writer.write(
            records=[record],
            source="Test-Source",
            date_accessed=date_accessed,
            run_id="test_run_001",
        )

        assert path is not None
        assert path.exists()

        table = pq.ParquetFile(path).read()
        assert table.schema.names == SilverDatasetWriter.SCHEMA.names
        assert str(table.schema.field("source_metadata").type) == "string"

        partition_dir = tmp_path / "source=Test-Source" / f"date_accessed={date_accessed}"
        metadata_dir = (
            tmp_path / "_metadata" / "source=Test-Source" / f"date_accessed={date_accessed}"
        )
        metadata_files = list(metadata_dir.glob("*.json"))

        assert not list(partition_dir.glob("*.json"))
        assert len(metadata_files) == 1
        assert metadata_files[0].name == "test-source_test_run_001_silver_metadata.json"

    def test_metadata_json_serialization(self, tmp_path):
        """source_metadata remains a JSON string across write/read."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        record = _build_test_record(
            source="Wikipedia-Somali",
            url="https://so.wikipedia.org/wiki/Test",
            date_accessed="2025-01-01",
            run_id="test_run_002",
            source_metadata={
                "wiki_code": "sowiki",
                "dump_url": "https://dumps.wikimedia.org/...",
                "nested": {"key": "value"},
            },
        )

        path = writer.write(
            records=[record],
            source="Wikipedia-Somali",
            date_accessed="2025-01-01",
            run_id="test_run_002",
        )

        row = pq.ParquetFile(path).read().to_pylist()[0]
        assert isinstance(row["source_metadata"], str)

        deserialized = json.loads(row["source_metadata"])
        assert deserialized["wiki_code"] == "sowiki"
        assert deserialized["dump_url"] == "https://dumps.wikimedia.org/..."
        assert deserialized["nested"]["key"] == "value"

    def test_multiple_sources_no_schema_drift(self, tmp_path):
        """Different metadata payloads still produce identical parquet schema."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        wiki_record = _build_test_record(
            source="Wikipedia-Somali",
            url="https://so.wikipedia.org/wiki/Test",
            date_accessed="2025-01-01",
            run_id="test_run_003_wiki",
            source_metadata={"wiki_code": "sowiki", "dump_url": "https://dumps.wikimedia.org/..."},
        )
        bbc_record = _build_test_record(
            source="BBC-Somali",
            url="https://www.bbc.com/somali/test",
            date_accessed="2025-01-01",
            run_id="test_run_003_bbc",
            source_type="news",
            license_str="ODC-BY-1.0",
            domain="news",
            source_metadata={"article_id": "123456", "category": "news", "author": "John Doe"},
        )

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

        wiki_table = pq.ParquetFile(wiki_path).read()
        bbc_table = pq.ParquetFile(bbc_path).read()

        assert wiki_table.schema == bbc_table.schema
        assert "wiki_code" in json.loads(wiki_table.to_pylist()[0]["source_metadata"])
        assert "article_id" in json.loads(bbc_table.to_pylist()[0]["source_metadata"])

    def test_read_back_after_write_ignores_non_parquet_files(self, tmp_path):
        """writer.read() only reads parquet fragments, even if other files exist."""
        writer = SilverDatasetWriter(base_dir=tmp_path)
        date_accessed = "2025-01-01"

        record = _build_test_record(
            source="Test-Source",
            url="https://example.com",
            date_accessed=date_accessed,
            run_id="test_run_004",
            source_metadata={"test_key": "test_value"},
        )

        writer.write(
            records=[record],
            source="Test-Source",
            date_accessed=date_accessed,
            run_id="test_run_004",
        )

        partition_dir = tmp_path / "source=Test-Source" / f"date_accessed={date_accessed}"
        (partition_dir / "unexpected.json").write_text('{"ignore": true}', encoding="utf-8")

        table = writer.read(source="Test-Source", date_accessed=date_accessed)
        row = table.to_pylist()[0]

        assert len(table) == 1
        assert row["text"] == "Test content for silver writer"
        assert row["title"] == "Test Title"
        assert row["source"] == "Test-Source"
        assert json.loads(row["source_metadata"])["test_key"] == "test_value"

    def test_get_domain_statistics_reads_only_parquet_files(self, tmp_path):
        """Domain stats ignore sidecars and aggregate parquet content correctly."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        writer.write(
            records=[
                _build_test_record(
                    source="Source-1",
                    url="https://example.com/1",
                    date_accessed="2025-01-01",
                    run_id="stats_run_001",
                    domain="news",
                    source_type="news",
                    license_str="ODC-BY-1.0",
                )
            ],
            source="Source-1",
            date_accessed="2025-01-01",
            run_id="stats_run_001",
        )
        writer.write(
            records=[
                _build_test_record(
                    source="Source-2",
                    url="https://example.com/2",
                    date_accessed="2025-01-01",
                    run_id="stats_run_002",
                    domain="literature",
                    source_type="corpus",
                    license_str="CC-BY-4.0",
                )
            ],
            source="Source-2",
            date_accessed="2025-01-01",
            run_id="stats_run_002",
        )

        stats = writer.get_domain_statistics()

        assert stats["news"] == 1
        assert stats["literature"] == 1

    def test_empty_records_returns_none(self, tmp_path):
        """Writer returns None for an empty batch."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        result = writer.write(
            records=[],
            source="Empty-Source",
            date_accessed="2025-01-01",
            run_id="test_run_005",
        )

        assert result is None

    def test_write_accepts_linguistic_register_alias(self, tmp_path):
        """Writer accepts contract-style linguistic_register and stores register."""
        writer = SilverDatasetWriter(base_dir=tmp_path)
        record = _build_test_record(
            source="Test-Source",
            url="https://example.com/alias",
            date_accessed="2025-01-01",
            run_id="test_run_alias",
        )
        record["linguistic_register"] = record.pop("register")

        path = writer.write(
            records=[record],
            source="Test-Source",
            date_accessed="2025-01-01",
            run_id="test_run_alias",
        )

        stored = pq.ParquetFile(path).read().to_pylist()[0]
        assert stored["register"] == "formal"
        assert stored["schema_version"] == "1.0"

    def test_write_rejects_invalid_schema_version_without_patching(self, tmp_path):
        """Writer fails on invalid schema_version instead of silently overwriting it."""
        writer = SilverDatasetWriter(base_dir=tmp_path)
        record = _build_test_record(
            source="Test-Source",
            url="https://example.com/schema",
            date_accessed="2025-01-01",
            run_id="test_run_schema",
            schema_version="2.0",
        )

        with pytest.raises(ValueError, match="schema_version"):
            writer.write(
                records=[record],
                source="Test-Source",
                date_accessed="2025-01-01",
                run_id="test_run_schema",
            )

        assert record["schema_version"] == "2.0"
