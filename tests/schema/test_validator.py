"""
Tests for schema validator.

Tests record and DataFrame validation.
"""

import pandas as pd
import pytest

from somali_dialect_classifier.schema.validator import SchemaValidator


class TestSchemaValidator:
    """Test SchemaValidator functionality."""

    @pytest.fixture
    def validator(self):
        """Fixture providing validator instance."""
        return SchemaValidator()

    @pytest.fixture
    def valid_record(self):
        """Fixture providing a valid record."""
        return {
            "id": "abc123",
            "text": "Test text content.",
            "title": "Test Title",
            "source": "Wikipedia-Somali",
            "source_type": "wiki",
            "url": "https://so.wikipedia.org/wiki/Test",
            "source_id": None,
            "date_published": None,
            "date_accessed": "2025-01-15",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "topic": None,
            "tokens": 5,
            "text_hash": "def456",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "encyclopedia",
            "embedding": None,
            "register": "formal",
            "schema_version": "1.0",
            "run_id": "20250115_120000",
        }

    def test_validate_record_valid(self, validator, valid_record):
        """Test validation passes for valid record."""
        is_valid, errors = validator.validate_record(valid_record)
        assert is_valid
        assert errors == []

    def test_validate_record_invalid_empty_text(self, validator, valid_record):
        """Test validation fails for empty text."""
        valid_record["text"] = ""
        is_valid, errors = validator.validate_record(valid_record)
        assert not is_valid
        assert len(errors) > 0
        assert "text" in errors[0].lower()

    def test_validate_record_invalid_source(self, validator, valid_record):
        """Test validation fails for invalid source."""
        valid_record["source"] = "InvalidSource"
        is_valid, errors = validator.validate_record(valid_record)
        assert not is_valid
        assert len(errors) > 0
        assert "source" in errors[0].lower()

    def test_validate_record_missing_field(self, validator, valid_record):
        """Test validation fails for missing required field."""
        del valid_record["text"]
        is_valid, errors = validator.validate_record(valid_record)
        assert not is_valid
        assert len(errors) > 0

    def test_validate_record_extra_field(self, validator, valid_record):
        """Test validation fails for extra field."""
        valid_record["extra_field"] = "not allowed"
        is_valid, errors = validator.validate_record(valid_record)
        assert not is_valid
        assert len(errors) > 0

    def test_validate_record_with_version(self, validator, valid_record):
        """Test validation with explicit version."""
        is_valid, errors = validator.validate_record(valid_record, version="1.0")
        assert is_valid
        assert errors == []

    def test_validate_dataframe_all_valid(self, validator, valid_record):
        """Test DataFrame validation with all valid records."""
        df = pd.DataFrame([valid_record, valid_record.copy()])
        all_valid, validated_df = validator.validate_dataframe(df)

        assert all_valid
        assert "_validation_valid" in validated_df.columns
        assert "_validation_errors" in validated_df.columns
        assert all(validated_df["_validation_valid"])

    def test_validate_dataframe_some_invalid(self, validator, valid_record):
        """Test DataFrame validation with some invalid records."""
        invalid_record = valid_record.copy()
        invalid_record["text"] = ""  # Invalid

        df = pd.DataFrame([valid_record, invalid_record, valid_record.copy()])
        all_valid, validated_df = validator.validate_dataframe(df)

        assert not all_valid
        assert "_validation_valid" in validated_df.columns
        assert "_validation_errors" in validated_df.columns

        # Check counts
        valid_count = validated_df["_validation_valid"].sum()
        invalid_count = (~validated_df["_validation_valid"]).sum()
        assert valid_count == 2
        assert invalid_count == 1

        # Check error messages
        invalid_rows = validated_df[~validated_df["_validation_valid"]]
        assert len(invalid_rows) == 1
        assert len(invalid_rows.iloc[0]["_validation_errors"]) > 0

    def test_add_schema_version(self, validator, valid_record):
        """Test adding schema_version to DataFrame."""
        del valid_record["schema_version"]  # Remove existing
        df = pd.DataFrame([valid_record])

        df_with_version = validator.add_schema_version(df)

        assert "schema_version" in df_with_version.columns
        assert all(df_with_version["schema_version"] == "1.0")

        # Original df not modified
        assert "schema_version" not in df.columns

    def test_add_schema_version_custom(self, validator, valid_record):
        """Test adding custom schema version."""
        del valid_record["schema_version"]
        df = pd.DataFrame([valid_record])

        df_with_version = validator.add_schema_version(df, version="1.1")

        assert all(df_with_version["schema_version"] == "1.1")

    def test_get_validation_report(self, validator, valid_record):
        """Test validation report generation."""
        invalid_record = valid_record.copy()
        invalid_record["text"] = ""

        df = pd.DataFrame([valid_record, invalid_record, valid_record.copy()])
        _, validated_df = validator.validate_dataframe(df)

        report = validator.get_validation_report(validated_df)

        assert report["total_records"] == 3
        assert report["valid_records"] == 2
        assert report["invalid_records"] == 1
        assert 60.0 < report["validation_rate"] < 70.0  # ~66.7%
        assert isinstance(report["error_summary"], dict)
        assert len(report["error_summary"]) > 0

    def test_get_validation_report_without_validation(self, validator, valid_record):
        """Test validation report fails without validation columns."""
        df = pd.DataFrame([valid_record])

        with pytest.raises(ValueError, match="must be validated first"):
            validator.get_validation_report(df)

    def test_validate_dataframe_empty(self, validator):
        """Test validation of empty DataFrame."""
        df = pd.DataFrame()
        all_valid, validated_df = validator.validate_dataframe(df)

        assert all_valid  # No records to validate
        assert len(validated_df) == 0

    def test_validate_record_returns_detailed_errors(self, validator, valid_record):
        """Test validation returns detailed error messages."""
        valid_record["text"] = ""
        valid_record["tokens"] = -5
        valid_record["source"] = "Invalid"

        is_valid, errors = validator.validate_record(valid_record)

        assert not is_valid
        assert len(errors) >= 3  # At least 3 errors
        assert any("text" in err for err in errors)
        assert any("tokens" in err for err in errors)
        assert any("source" in err for err in errors)
