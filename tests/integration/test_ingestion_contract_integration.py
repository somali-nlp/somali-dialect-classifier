"""
Integration tests for ingestion output contract.

Validates that actual silver Parquet files produced by the pipeline
satisfy the IngestionOutputV1 contract.
"""

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from somali_dialect_classifier.contracts import validate_ingestion_output
from somali_dialect_classifier.quality.record_builder import RecordBuilder
from somali_dialect_classifier.quality.silver_writer import SilverDatasetWriter


class RawRecordMock:
    """Mock RawRecord for testing."""

    def __init__(self, title, text, url, metadata):
        self.title = title
        self.text = text
        self.url = url
        self.metadata = metadata


class TestSilverParquetContractCompliance:
    """Test that silver Parquet files comply with ingestion contract."""

    def test_silver_writer_produces_contract_compliant_records(self, tmp_path):
        """Records written by SilverDatasetWriter satisfy contract."""
        # Create sample records using RecordBuilder (mimics real pipeline)
        builder = RecordBuilder(
            source="Wikipedia-Somali",
            date_accessed="2025-12-29",
            run_id="20251229_100000_wikipedia",
        )

        raw_record = RawRecordMock(
            title="Test Article",
            text="Original text content",
            url="https://so.wikipedia.org/wiki/Test",
            metadata={"topic": "science"},
        )

        silver_record = builder.build_silver_record(
            raw_record=raw_record,
            cleaned_text="Cleaned text content",
            filter_metadata={"langid": "so"},
            source_type="wiki",
            license_str="CC-BY-SA-3.0",
            domain="encyclopedia",
            register="formal",
        )

        # Write to Parquet
        writer = SilverDatasetWriter(base_dir=tmp_path)
        parquet_path = writer.write(
            records=[silver_record],
            source="Wikipedia-Somali",
            date_accessed="2025-12-29",
            run_id="20251229_100000_wikipedia",
        )

        # Read back and validate contract compliance
        # Note: Use ParquetFile to read single file directly
        pf = pq.ParquetFile(parquet_path)
        table = pf.read()
        records = table.to_pylist()

        assert len(records) == 1
        record = records[0]

        # Validate against contract
        is_valid, errors = validate_ingestion_output(record)

        assert is_valid, f"Contract validation failed: {errors}"

    def test_multiple_sources_all_contract_compliant(self, tmp_path):
        """Records from different sources all satisfy contract."""
        sources = [
            ("Wikipedia-Somali", "wiki", "encyclopedia", "CC-BY-SA-3.0"),
            ("BBC-Somali", "news", "news", "ODC-BY-1.0"),
            ("Sprakbanken-Somali", "corpus", "literature", "CC-BY-4.0"),
        ]

        for source_name, source_type, domain, license_str in sources:
            builder = RecordBuilder(
                source=source_name,
                date_accessed="2025-12-29",
                run_id=f"20251229_100000_{source_name.lower()}",
            )

            raw_record = RawRecordMock(
                title="Test Document",
                text="Original text",
                url=f"https://example.com/{source_name}",
                metadata={},
            )

            silver_record = builder.build_silver_record(
                raw_record=raw_record,
                cleaned_text="Cleaned test text",
                filter_metadata={},
                source_type=source_type,
                license_str=license_str,
                domain=domain,
                register="formal",
            )

            # Validate against contract
            is_valid, errors = validate_ingestion_output(silver_record)

            assert is_valid, f"Source {source_name} failed contract validation: {errors}"

    def test_contract_catches_missing_required_field(self):
        """Contract validation detects missing required fields."""
        # Create incomplete record (missing text_hash)
        incomplete_record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 2,
            # Missing text_hash
            "linguistic_register": "formal",
        }

        is_valid, errors = validate_ingestion_output(incomplete_record)

        assert not is_valid
        assert any("text_hash" in err for err in errors)

    def test_batch_write_all_records_contract_compliant(self, tmp_path):
        """Multiple records in batch write all satisfy contract."""
        builder = RecordBuilder(
            source="Wikipedia-Somali",
            date_accessed="2025-12-29",
            run_id="20251229_100000_wikipedia",
        )

        # Create multiple records
        records = []
        for i in range(10):
            raw_record = RawRecordMock(
                title=f"Article {i}",
                text=f"Original text {i}",
                url=f"https://so.wikipedia.org/wiki/Article{i}",
                metadata={},
            )

            silver_record = builder.build_silver_record(
                raw_record=raw_record,
                cleaned_text=f"Cleaned text content {i}",
                filter_metadata={},
                source_type="wiki",
                license_str="CC-BY-SA-3.0",
                domain="encyclopedia",
                register="formal",
            )
            records.append(silver_record)

        # Write batch
        writer = SilverDatasetWriter(base_dir=tmp_path)
        parquet_path = writer.write(
            records=records,
            source="Wikipedia-Somali",
            date_accessed="2025-12-29",
            run_id="20251229_100000_wikipedia",
        )

        # Read and validate all records
        # Note: Use ParquetFile to read single file directly
        pf = pq.ParquetFile(parquet_path)
        table = pf.read()
        stored_records = table.to_pylist()

        assert len(stored_records) == 10

        for idx, record in enumerate(stored_records):
            is_valid, errors = validate_ingestion_output(record)
            assert is_valid, f"Record {idx} failed contract validation: {errors}"

    def test_optional_fields_preserved(self, tmp_path):
        """Optional contract fields are preserved in storage."""
        builder = RecordBuilder(
            source="BBC-Somali",
            date_accessed="2025-12-29",
            run_id="20251229_100000_bbc",
        )

        raw_record = RawRecordMock(
            title="News Article",
            text="Original news text",
            url="https://bbc.com/somali/article",
            metadata={
                "topic": "politics",
                "date_published": "2025-12-28",
            },
        )

        # Add enrichment metadata that maps to optional fields
        filter_metadata = {
            "detected_lang": "so",
            "lang_confidence": 0.98,
        }

        silver_record = builder.build_silver_record(
            raw_record=raw_record,
            cleaned_text="Cleaned news text",
            filter_metadata=filter_metadata,
            source_type="news",
            license_str="ODC-BY-1.0",
            domain="news",
            register="formal",
        )

        # Write to Parquet
        writer = SilverDatasetWriter(base_dir=tmp_path)
        parquet_path = writer.write(
            records=[silver_record],
            source="BBC-Somali",
            date_accessed="2025-12-29",
            run_id="20251229_100000_bbc",
        )

        # Read back
        # Note: Use ParquetFile to read single file directly
        pf = pq.ParquetFile(parquet_path)
        table = pf.read()
        stored_record = table.to_pylist()[0]

        # Validate contract compliance
        is_valid, errors = validate_ingestion_output(stored_record)
        assert is_valid

        # Verify optional fields preserved (in source_metadata)
        import json

        source_metadata = json.loads(stored_record["source_metadata"])
        assert "detected_lang" in source_metadata
        assert "lang_confidence" in source_metadata

    def test_different_registers_all_valid(self, tmp_path):
        """All valid register values pass contract validation."""
        for register_value in ["formal", "informal", "colloquial"]:
            builder = RecordBuilder(
                source="Test-Source",
                date_accessed="2025-12-29",
                run_id=f"20251229_100000_{register_value}",
            )

            raw_record = RawRecordMock(
                title="Test",
                text="Original",
                url="https://example.com",
                metadata={},
            )

            silver_record = builder.build_silver_record(
                raw_record=raw_record,
                cleaned_text="Cleaned text",
                filter_metadata={},
                source_type="wiki",
                license_str="CC-BY-SA-3.0",
                domain="general",
                register=register_value,
            )

            is_valid, errors = validate_ingestion_output(silver_record)
            assert is_valid, f"Register '{register_value}' failed validation: {errors}"


@pytest.mark.skipif(
    not Path(
        "/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/"
        "somali-dialect-classifier/data/processed/silver"
    ).exists(),
    reason="Silver dataset not present (requires data ingestion)",
)
class TestRealSilverDatasetCompliance:
    """Test contract compliance on real silver datasets (if available)."""

    def test_existing_silver_datasets_contract_compliant(self):
        """Existing silver Parquet files satisfy contract (if present)."""
        silver_base = Path(
            "/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/"
            "somali-dialect-classifier/data/processed/silver"
        )

        # Find all source directories
        source_dirs = [d for d in silver_base.glob("source=*") if d.is_dir()]

        if not source_dirs:
            pytest.skip("No silver datasets found")

        validation_results = []

        # Sample up to 100 records from each source
        for source_dir in source_dirs[:5]:  # Limit to first 5 sources
            for date_dir in list(source_dir.glob("date_accessed=*"))[:3]:  # First 3 dates
                try:
                    table = pq.read_table(date_dir)
                    records = table.to_pylist()

                    # Validate sample of records
                    sample_size = min(100, len(records))
                    for record in records[:sample_size]:
                        is_valid, errors = validate_ingestion_output(record)
                        validation_results.append(
                            {
                                "source": source_dir.name,
                                "date": date_dir.name,
                                "valid": is_valid,
                                "errors": errors,
                            }
                        )

                except Exception as e:
                    # Log but don't fail on read errors
                    pytest.skip(f"Could not read {date_dir}: {e}")

        if not validation_results:
            pytest.skip("No records validated")

        # Check overall compliance rate
        total_records = len(validation_results)
        valid_records = sum(1 for r in validation_results if r["valid"])
        compliance_rate = valid_records / total_records * 100

        # Report failures
        failures = [r for r in validation_results if not r["valid"]]
        if failures:
            failure_summary = "\n".join(
                f"  - {f['source']}/{f['date']}: {f['errors']}" for f in failures[:10]
            )
            assert compliance_rate >= 95.0, (
                f"Contract compliance rate {compliance_rate:.1f}% below 95%:\n{failure_summary}"
            )

        assert compliance_rate == 100.0, (
            f"Contract compliance: {compliance_rate:.1f}% ({valid_records}/{total_records} records)"
        )
