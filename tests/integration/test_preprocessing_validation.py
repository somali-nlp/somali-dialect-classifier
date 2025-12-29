"""
Integration tests for preprocessing validation module.

Tests the validation of silver Parquet files against the IngestionOutputV1
contract, including both valid and invalid data scenarios.
"""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from somali_dialect_classifier.preprocessing.validator import (
    ValidationError,
    iter_validated_records,
    validate_silver_directory,
    validate_silver_parquet,
)


@pytest.fixture
def temp_silver_dir(tmp_path):
    """Create temporary silver directory structure."""
    silver_dir = tmp_path / "processed" / "silver"
    silver_dir.mkdir(parents=True)
    return silver_dir


@pytest.fixture
def valid_records():
    """Generate valid test records."""
    return [
        {
            "id": f"test-id-{i}",
            "text": f"This is valid Somali text number {i}.",
            "title": f"Test Article {i}",
            "source": "Test-Source",
            "source_type": "test",
            "url": f"https://example.com/article-{i}",
            "source_id": f"src-{i}",
            "date_published": "2025-11-27",
            "date_accessed": "2025-11-27",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "topic": "general",
            "tokens": 7 + i,
            "text_hash": f"hash-{i}",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "general",
            "embedding": None,
            "register": "formal",
            "run_id": "20251127_100000_test",
            "schema_version": "1.0",
        }
        for i in range(10)
    ]


@pytest.fixture
def invalid_records():
    """Generate invalid test records (missing required fields)."""
    return [
        {
            "id": "test-invalid-1",
            # Missing 'text' field
            "source": "Test-Source",
            "tokens": 5,
            "text_hash": "hash-invalid-1",
            "register": "formal",
        },
        {
            "id": "test-invalid-2",
            "text": "",  # Empty text
            "source": "Test-Source",
            "tokens": 0,
            "text_hash": "hash-invalid-2",
            "register": "formal",
        },
        {
            "id": "test-invalid-3",
            "text": "Valid text",
            "source": "Test-Source",
            "tokens": 2,
            "text_hash": "hash-invalid-3",
            "register": "invalid_register",  # Invalid register value
        },
    ]


def write_parquet_file(path: Path, records: list, schema: pa.Schema = None) -> Path:
    """Helper to write records to Parquet file."""
    if schema is None:
        # Use simplified schema for testing
        schema = pa.schema(
            [
                ("id", pa.string()),
                ("text", pa.string()),
                ("title", pa.string()),
                ("source", pa.string()),
                ("source_type", pa.string()),
                ("url", pa.string()),
                ("source_id", pa.string()),
                ("date_published", pa.string()),
                ("date_accessed", pa.string()),
                ("language", pa.string()),
                ("license", pa.string()),
                ("topic", pa.string()),
                ("tokens", pa.int64()),
                ("text_hash", pa.string()),
                ("pipeline_version", pa.string()),
                ("source_metadata", pa.string()),
                ("domain", pa.string()),
                ("embedding", pa.string()),
                ("register", pa.string()),
                ("run_id", pa.string()),
                ("schema_version", pa.string()),
            ]
        )

    table = pa.Table.from_pylist(records, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)
    return path


class TestValidateSilverParquet:
    """Test validate_silver_parquet function."""

    def test_validate_valid_parquet_file(self, temp_silver_dir, valid_records):
        """Test validation of valid Parquet file."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Write valid records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, valid_records)

        # Validate
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir)

        # Assert all records are valid
        assert valid_count == len(valid_records)
        assert invalid_count == 0
        assert len(errors) == 0

    def test_validate_invalid_parquet_file(self, temp_silver_dir, invalid_records):
        """Test validation of invalid Parquet file."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Write invalid records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, invalid_records)

        # Validate (no fail-fast)
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir, fail_fast=False)

        # Assert all records are invalid
        assert valid_count == 0
        assert invalid_count == len(invalid_records)
        assert len(errors) == len(invalid_records)

        # Check error details
        for error in errors:
            assert "record_index" in error
            assert "record_id" in error
            assert "errors" in error
            assert len(error["errors"]) > 0

    def test_validate_mixed_parquet_file(self, temp_silver_dir, valid_records, invalid_records):
        """Test validation of Parquet file with mixed valid/invalid records."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Mix valid and invalid records
        mixed_records = valid_records[:5] + invalid_records + valid_records[5:]

        # Write mixed records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, mixed_records)

        # Validate
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir)

        # Assert counts
        assert valid_count == len(valid_records)
        assert invalid_count == len(invalid_records)
        assert len(errors) == len(invalid_records)

    def test_validate_fail_fast_mode(self, temp_silver_dir, invalid_records):
        """Test fail-fast mode raises exception on first error."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Write invalid records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, invalid_records)

        # Validate with fail-fast mode should raise exception
        with pytest.raises(ValidationError) as exc_info:
            validate_silver_parquet(partition_dir, fail_fast=True)

        # Check exception message contains record info
        assert "record" in str(exc_info.value).lower()

    def test_validate_nonexistent_file(self, temp_silver_dir):
        """Test validation of non-existent file raises FileNotFoundError."""
        nonexistent_path = temp_silver_dir / "nonexistent" / "path"

        with pytest.raises(FileNotFoundError):
            validate_silver_parquet(nonexistent_path)


class TestIterValidatedRecords:
    """Test iter_validated_records function."""

    def test_iter_valid_records(self, temp_silver_dir, valid_records):
        """Test iteration over valid records."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Write valid records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, valid_records)

        # Iterate and collect records
        collected_records = list(iter_validated_records(partition_dir))

        # Assert all records were yielded
        assert len(collected_records) == len(valid_records)

        # Check record IDs match
        collected_ids = {r["id"] for r in collected_records}
        expected_ids = {r["id"] for r in valid_records}
        assert collected_ids == expected_ids

    def test_iter_mixed_records_fail_fast(self, temp_silver_dir, valid_records, invalid_records):
        """Test iteration with fail-fast mode raises on invalid record."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Mix valid and invalid records (invalid first)
        mixed_records = invalid_records[:1] + valid_records

        # Write mixed records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, mixed_records)

        # Iterate with fail-fast should raise on first invalid
        with pytest.raises(ValidationError):
            list(iter_validated_records(partition_dir, fail_fast=True))

    def test_iter_mixed_records_tolerant(self, temp_silver_dir, valid_records, invalid_records):
        """Test iteration in tolerant mode skips invalid records."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"

        # Mix valid and invalid records
        mixed_records = valid_records[:3] + invalid_records + valid_records[3:]

        # Write mixed records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, mixed_records)

        # Iterate in tolerant mode (fail_fast=False)
        collected_records = list(iter_validated_records(partition_dir, fail_fast=False))

        # Should only yield valid records
        assert len(collected_records) == len(valid_records)

        # Check all collected records are from valid set
        collected_ids = {r["id"] for r in collected_records}
        valid_ids = {r["id"] for r in valid_records}
        assert collected_ids == valid_ids


class TestValidateSilverDirectory:
    """Test validate_silver_directory function."""

    def test_validate_multiple_partitions(self, temp_silver_dir, valid_records):
        """Test validation of multiple partitions."""
        # Create multiple partitions
        sources = ["Source-A", "Source-B"]
        dates = ["2025-11-27", "2025-11-28"]

        for source in sources:
            for date in dates:
                partition_dir = temp_silver_dir / f"source={source}" / f"date_accessed={date}"
                parquet_file = partition_dir / "test_silver_part-0000.parquet"
                write_parquet_file(parquet_file, valid_records)

        # Validate all partitions
        results = validate_silver_directory(temp_silver_dir)

        # Should have 4 partitions (2 sources × 2 dates)
        assert len(results) == 4

        # All should be valid
        for _partition_path, (valid, invalid, errors) in results.items():
            assert valid == len(valid_records)
            assert invalid == 0
            assert len(errors) == 0

    def test_validate_with_source_filter(self, temp_silver_dir, valid_records):
        """Test validation with source filter."""
        # Create multiple sources
        sources = ["Source-A", "Source-B"]

        for source in sources:
            partition_dir = temp_silver_dir / f"source={source}" / "date_accessed=2025-11-27"
            parquet_file = partition_dir / "test_silver_part-0000.parquet"
            write_parquet_file(parquet_file, valid_records)

        # Validate only Source-A
        results = validate_silver_directory(temp_silver_dir, source_filter="Source-A")

        # Should only have 1 partition
        assert len(results) == 1

        # Check it's the right source
        partition_path = list(results.keys())[0]
        assert "Source-A" in partition_path

    def test_validate_mixed_quality_partitions(
        self, temp_silver_dir, valid_records, invalid_records
    ):
        """Test validation with mixed quality partitions."""
        # Create valid partition
        valid_partition = temp_silver_dir / "source=Valid-Source" / "date_accessed=2025-11-27"
        write_parquet_file(valid_partition / "test_silver_part-0000.parquet", valid_records)

        # Create invalid partition
        invalid_partition = temp_silver_dir / "source=Invalid-Source" / "date_accessed=2025-11-27"
        write_parquet_file(
            invalid_partition / "test_silver_part-0000.parquet",
            invalid_records,
        )

        # Validate all
        results = validate_silver_directory(temp_silver_dir)

        # Should have 2 partitions
        assert len(results) == 2

        # Check valid partition
        valid_result = [v for k, v in results.items() if "Valid-Source" in k][0]
        assert valid_result[0] == len(valid_records)  # valid count
        assert valid_result[1] == 0  # invalid count

        # Check invalid partition
        invalid_result = [v for k, v in results.items() if "Invalid-Source" in k][0]
        assert invalid_result[0] == 0  # valid count
        assert invalid_result[1] == len(invalid_records)  # invalid count


class TestStrictValidation:
    """Test strict validation behavior - no patching, fail-fast on invalid data."""

    def test_validation_rejects_missing_run_id(self, temp_silver_dir):
        """Test that validation rejects records with missing run_id."""
        # Create record without run_id
        invalid_record = {
            "id": "test-no-run-id",
            "text": "Valid text",
            "title": "Test",
            "source": "Test-Source",
            "source_type": "test",
            "url": "https://example.com",
            "source_id": "src-1",
            "date_published": "2025-11-27",
            "date_accessed": "2025-11-27",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "topic": "general",
            "tokens": 2,
            "text_hash": "hash-1",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "general",
            "embedding": None,
            "register": "formal",
            # "run_id": "20251127_100000_test",  # MISSING - should fail
            "schema_version": "1.0",
        }

        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, [invalid_record])

        # Validate - should find error
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir, fail_fast=False)

        assert valid_count == 0
        assert invalid_count == 1
        assert len(errors) == 1
        assert any("run_id" in err for err in errors[0]["errors"])
        # Error message will say "is None" or "missing" depending on how field is absent
        assert any("run_id" in err and ("none" in err.lower() or "missing" in err.lower()) for err in errors[0]["errors"])

    def test_validation_rejects_invalid_schema_version(self, temp_silver_dir):
        """Test that validation rejects records with schema_version != '1.0'."""
        # Create record with wrong schema version
        invalid_record = {
            "id": "test-bad-schema",
            "text": "Valid text",
            "title": "Test",
            "source": "Test-Source",
            "source_type": "test",
            "url": "https://example.com",
            "source_id": "src-1",
            "date_published": "2025-11-27",
            "date_accessed": "2025-11-27",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "topic": "general",
            "tokens": 2,
            "text_hash": "hash-1",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "general",
            "embedding": None,
            "register": "formal",
            "run_id": "20251127_100000_test",
            "schema_version": "2.0",  # Wrong version
        }

        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, [invalid_record])

        # Validate - should find error
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir, fail_fast=False)

        assert valid_count == 0
        assert invalid_count == 1
        assert len(errors) == 1
        assert any("schema_version" in err for err in errors[0]["errors"])
        assert any("1.0" in err for err in errors[0]["errors"])

    def test_validation_rejects_missing_schema_version(self, temp_silver_dir):
        """Test that validation rejects records with missing schema_version."""
        # Create record without schema_version
        invalid_record = {
            "id": "test-no-schema",
            "text": "Valid text",
            "title": "Test",
            "source": "Test-Source",
            "source_type": "test",
            "url": "https://example.com",
            "source_id": "src-1",
            "date_published": "2025-11-27",
            "date_accessed": "2025-11-27",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "topic": "general",
            "tokens": 2,
            "text_hash": "hash-1",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "general",
            "embedding": None,
            "register": "formal",
            "run_id": "20251127_100000_test",
            # "schema_version": "1.0",  # MISSING - should fail
        }

        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, [invalid_record])

        # Validate - should find error
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir, fail_fast=False)

        assert valid_count == 0
        assert invalid_count == 1
        assert len(errors) == 1
        assert any("schema_version" in err for err in errors[0]["errors"])

    def test_validation_provides_clear_error_messages(self, temp_silver_dir):
        """Test that validation provides clear, actionable error messages."""
        # Create record with multiple issues
        invalid_record = {
            "id": "",  # Empty ID
            "text": "   ",  # Whitespace-only text
            "title": "Test",
            "source": "Test-Source",
            "source_type": "test",
            "url": "https://example.com",
            "source_id": "src-1",
            "date_published": "2025-11-27",
            "date_accessed": "2025-11-27",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "topic": "general",
            "tokens": -5,  # Negative tokens
            "text_hash": "",  # Empty hash
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "general",
            "embedding": None,
            "register": "invalid_value",  # Invalid register
            "run_id": "",  # Empty run_id
            "schema_version": "1.0",
        }

        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, [invalid_record])

        # Validate - should find multiple specific errors
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir, fail_fast=False)

        assert valid_count == 0
        assert invalid_count == 1
        assert len(errors) == 1

        error_messages = errors[0]["errors"]
        assert len(error_messages) > 0

        # Check for specific clear error messages
        error_text = " ".join(error_messages).lower()
        assert "id" in error_text or "empty" in error_text
        assert "text" in error_text or "whitespace" in error_text
        assert "tokens" in error_text or "negative" in error_text
        assert "register" in error_text or "invalid" in error_text

    def test_validation_no_patching_occurs(self, temp_silver_dir):
        """Test that validation never patches or fixes records."""
        # Create invalid record
        invalid_record = {
            "id": "test-invalid",
            "text": "Valid text",
            "source": "Test-Source",
            "tokens": 2,
            "text_hash": "hash-1",
            "register": "formal",
            # Missing required fields: run_id, schema_version
        }

        partition_dir = temp_silver_dir / "source=Test-Source" / "date_accessed=2025-11-27"
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, [invalid_record])

        # Validate - should NOT patch the record
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir, fail_fast=False)

        # Record should still be invalid
        assert valid_count == 0
        assert invalid_count == 1

        # Verify original record is unchanged by re-reading
        import pyarrow.parquet as pq_read

        table = pq_read.read_table(partition_dir)
        records = table.to_pylist()
        assert len(records) == 1
        # Should NOT have run_id or schema_version added
        assert records[0].get("run_id") is None or records[0].get("run_id") == ""
        assert records[0].get("schema_version") is None or records[0].get("schema_version") == ""


class TestValidationEdgeCases:
    """Test edge cases in validation."""

    def test_validate_empty_partition(self, temp_silver_dir):
        """Test validation of partition with no records."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Empty-Source" / "date_accessed=2025-11-27"

        # Write empty Parquet file
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, [])

        # Validate
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir)

        # Should have zero counts
        assert valid_count == 0
        assert invalid_count == 0
        assert len(errors) == 0

    def test_validate_large_batch(self, temp_silver_dir, valid_records):
        """Test validation with large batch (>1000 records)."""
        # Create partition directory
        partition_dir = temp_silver_dir / "source=Large-Source" / "date_accessed=2025-11-27"

        # Create 2500 records to test batch processing
        large_records = []
        for i in range(2500):
            record = valid_records[0].copy()
            record["id"] = f"large-record-{i}"
            record["text"] = f"Large batch record {i}"
            large_records.append(record)

        # Write large batch
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, large_records)

        # Validate
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir)

        # All should be valid
        assert valid_count == 2500
        assert invalid_count == 0
        assert len(errors) == 0

    def test_validate_with_null_values(self, temp_silver_dir):
        """Test validation with records containing null values."""
        # Create records with null optional fields (should be valid)
        records_with_nulls = [
            {
                "id": "test-null-1",
                "text": "Valid text with null optionals",
                "title": None,  # Optional field
                "source": "Test-Source",
                "source_type": "test",
                "url": None,  # Optional field
                "source_id": None,
                "date_published": None,
                "date_accessed": "2025-11-27",
                "language": "so",
                "license": None,
                "topic": None,  # Optional field
                "tokens": 5,
                "text_hash": "hash-null-1",
                "pipeline_version": "2.1.0",
                "source_metadata": "{}",
                "domain": "general",
                "embedding": None,
                "register": "formal",
                "run_id": "20251127_100000_test",
                "schema_version": "1.0",
            }
        ]

        # Create partition directory
        partition_dir = temp_silver_dir / "source=Null-Source" / "date_accessed=2025-11-27"

        # Write records
        parquet_file = partition_dir / "test_silver_part-0000.parquet"
        write_parquet_file(parquet_file, records_with_nulls)

        # Validate
        valid_count, invalid_count, errors = validate_silver_parquet(partition_dir)

        # Should be valid (null optional fields are allowed)
        assert valid_count == 1
        assert invalid_count == 0
