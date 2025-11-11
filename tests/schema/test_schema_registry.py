"""
Tests for schema registry.

Tests SchemaV1_0 validation and schema retrieval.
"""

import pytest
from pydantic import ValidationError

from somali_dialect_classifier.schema.registry import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_REGISTRY,
    SchemaV1_0,
    get_current_schema,
    get_schema,
)


class TestSchemaRegistry:
    """Test schema registry functions."""

    def test_get_schema_valid(self):
        """Test retrieving valid schema version."""
        schema = get_schema("1.0")
        assert schema == SchemaV1_0

    def test_get_schema_invalid(self):
        """Test retrieving invalid schema version raises error."""
        with pytest.raises(ValueError, match="Unknown schema version"):
            get_schema("99.0")

    def test_get_current_schema(self):
        """Test getting current schema."""
        schema = get_current_schema()
        assert schema == SchemaV1_0
        assert CURRENT_SCHEMA_VERSION == "1.0"

    def test_schema_registry_structure(self):
        """Test schema registry has expected structure."""
        assert isinstance(SCHEMA_REGISTRY, dict)
        assert "1.0" in SCHEMA_REGISTRY
        assert SCHEMA_REGISTRY["1.0"] == SchemaV1_0


class TestSchemaV1_0Validation:
    """Test SchemaV1_0 validation rules."""

    @pytest.fixture
    def valid_record(self):
        """Fixture providing a valid record."""
        return {
            "id": "abc123",
            "text": "This is test text content.",
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

    def test_valid_record(self, valid_record):
        """Test validation passes for valid record."""
        record = SchemaV1_0(**valid_record)
        assert record.schema_version == "1.0"
        assert record.text == "This is test text content."

    def test_empty_text_rejected(self, valid_record):
        """Test empty text is rejected."""
        valid_record["text"] = ""
        with pytest.raises(ValidationError, match="text cannot be empty"):
            SchemaV1_0(**valid_record)

    def test_whitespace_only_text_rejected(self, valid_record):
        """Test whitespace-only text is rejected."""
        valid_record["text"] = "   \n\t  "
        with pytest.raises(ValidationError, match="text cannot be empty"):
            SchemaV1_0(**valid_record)

    def test_invalid_source_rejected(self, valid_record):
        """Test invalid source identifier is rejected."""
        valid_record["source"] = "InvalidSource"
        with pytest.raises(ValidationError, match="source must start with"):
            SchemaV1_0(**valid_record)

    def test_valid_sources_accepted(self, valid_record):
        """Test all valid sources are accepted."""
        valid_sources = [
            "Wikipedia-Somali",
            "BBC-Somali",
            "Sprakbanken-Somali",
            "TikTok-Somali",
            "HuggingFace-Somali",
            "huggingface-somali_mc4",  # with suffix
        ]
        for source in valid_sources:
            valid_record["source"] = source
            record = SchemaV1_0(**valid_record)
            assert record.source == source

    def test_invalid_source_type_rejected(self, valid_record):
        """Test invalid source_type is rejected."""
        valid_record["source_type"] = "invalid"
        with pytest.raises(ValidationError, match="source_type must be one of"):
            SchemaV1_0(**valid_record)

    def test_valid_source_types_accepted(self, valid_record):
        """Test all valid source types are accepted."""
        valid_types = ["wiki", "news", "corpus", "web", "social"]
        for source_type in valid_types:
            valid_record["source_type"] = source_type
            record = SchemaV1_0(**valid_record)
            assert record.source_type == source_type

    def test_invalid_register_rejected(self, valid_record):
        """Test invalid register is rejected."""
        valid_record["register"] = "invalid"
        with pytest.raises(ValidationError, match="register must be one of"):
            SchemaV1_0(**valid_record)

    def test_valid_registers_accepted(self, valid_record):
        """Test all valid registers are accepted."""
        valid_registers = ["formal", "informal", "colloquial"]
        for register in valid_registers:
            valid_record["register"] = register
            record = SchemaV1_0(**valid_record)
            # Use linguistic_register to access the field
            assert record.linguistic_register == register

    def test_invalid_language_rejected(self, valid_record):
        """Test invalid language code is rejected."""
        valid_record["language"] = "en"
        with pytest.raises(ValidationError, match="language must be"):
            SchemaV1_0(**valid_record)

    def test_valid_languages_accepted(self, valid_record):
        """Test valid Somali language codes are accepted."""
        valid_langs = ["so", "som"]
        for lang in valid_langs:
            valid_record["language"] = lang
            record = SchemaV1_0(**valid_record)
            assert record.language == lang

    def test_negative_tokens_rejected(self, valid_record):
        """Test negative token count is rejected."""
        valid_record["tokens"] = -1
        # Updated regex to match Pydantic v2 error message
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            SchemaV1_0(**valid_record)

    def test_excessive_tokens_rejected(self, valid_record):
        """Test suspiciously high token count is rejected."""
        valid_record["tokens"] = 2_000_000
        with pytest.raises(ValidationError, match="tokens suspiciously high"):
            SchemaV1_0(**valid_record)

    def test_valid_token_range_accepted(self, valid_record):
        """Test reasonable token counts are accepted."""
        valid_counts = [1, 100, 10000, 100000]
        for count in valid_counts:
            valid_record["tokens"] = count
            record = SchemaV1_0(**valid_record)
            assert record.tokens == count

    def test_invalid_date_format_rejected(self, valid_record):
        """Test invalid date format is rejected."""
        valid_record["date_accessed"] = "2025/01/15"  # Wrong format
        with pytest.raises(ValidationError, match="date must be in ISO 8601 format"):
            SchemaV1_0(**valid_record)

    def test_valid_date_formats_accepted(self, valid_record):
        """Test valid ISO 8601 date formats are accepted."""
        valid_dates = [
            "2025-01-15",  # Date only
            "2025-01-15T10:30:00Z",  # Datetime with Z
            "2025-01-15T10:30:00+00:00",  # Datetime with timezone
        ]
        for date in valid_dates:
            valid_record["date_accessed"] = date
            record = SchemaV1_0(**valid_record)
            assert record.date_accessed == date

    def test_optional_fields_can_be_none(self, valid_record):
        """Test optional fields can be None."""
        optional_fields = [
            "source_id",
            "date_published",
            "topic",
            "embedding",
        ]
        for field in optional_fields:
            valid_record[field] = None
            record = SchemaV1_0(**valid_record)
            assert getattr(record, field) is None

    def test_extra_fields_rejected(self, valid_record):
        """Test extra fields are rejected (strict validation)."""
        valid_record["extra_field"] = "not allowed"
        # Updated regex to match Pydantic v2 error message
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SchemaV1_0(**valid_record)

    def test_missing_required_field_rejected(self, valid_record):
        """Test missing required field is rejected."""
        del valid_record["text"]
        # Updated regex to match Pydantic v2 error message
        with pytest.raises(ValidationError, match="Field required"):
            SchemaV1_0(**valid_record)

    def test_schema_version_defaults_to_1_0(self, valid_record):
        """Test schema_version defaults to 1.0 if not provided."""
        del valid_record["schema_version"]
        record = SchemaV1_0(**valid_record)
        assert record.schema_version == "1.0"

    def test_language_defaults_to_so(self, valid_record):
        """Test language defaults to 'so' if not provided."""
        del valid_record["language"]
        record = SchemaV1_0(**valid_record)
        assert record.language == "so"

    def test_source_metadata_defaults_to_empty_json(self, valid_record):
        """Test source_metadata defaults to empty JSON string."""
        del valid_record["source_metadata"]
        record = SchemaV1_0(**valid_record)
        assert record.source_metadata == "{}"
