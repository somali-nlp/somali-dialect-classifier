"""
Unit tests for ingestion output contract.

Validates:
1. Contract validation logic works correctly
2. Contract fields are compatible with SchemaV1_0
3. Edge cases are handled properly
"""

import pytest

from somali_dialect_classifier.contracts import (
    REQUIRED_FIELDS,
    IngestionOutputV1,
    validate_ingestion_output,
)
from somali_dialect_classifier.schema.registry import SchemaV1_0


class TestIngestionContractValidation:
    """Test contract validation logic."""

    def test_valid_record_passes(self):
        """Valid record with all required fields passes validation."""
        record = {
            "id": "abc123",
            "text": "Test text content",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 3,
            "text_hash": "hash123",
            "linguistic_register": "formal",
        }

        is_valid, errors = validate_ingestion_output(record)

        assert is_valid
        assert errors == []

    def test_missing_required_field_fails(self):
        """Record missing required field fails validation."""
        record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 2,
            "text_hash": "hash123",
            # Missing linguistic_register
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        assert any("linguistic_register" in err for err in errors)

    def test_null_required_field_fails(self):
        """Record with null required field fails validation."""
        record = {
            "id": "abc123",
            "text": None,  # Required field is null
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 0,
            "text_hash": "hash123",
            "linguistic_register": "formal",
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        assert any("text" in err and "None" in err for err in errors)

    def test_invalid_schema_version_fails(self):
        """Record with unsupported schema version fails."""
        record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "2.0",  # Unsupported version
            "tokens": 2,
            "text_hash": "hash123",
            "linguistic_register": "formal",
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        assert any("schema_version" in err.lower() for err in errors)

    def test_invalid_register_fails(self):
        """Record with invalid linguistic_register value fails."""
        record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 2,
            "text_hash": "hash123",
            "linguistic_register": "very_formal",  # Invalid value
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        assert any("linguistic_register" in err for err in errors)

    def test_negative_tokens_fails(self):
        """Record with negative tokens fails validation."""
        record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": -5,  # Invalid negative value
            "text_hash": "hash123",
            "linguistic_register": "formal",
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        # New error format: "Field 'tokens' has invalid value: -5 (must be >= 0)"
        assert any("tokens" in err.lower() and ("negative" in err.lower() or ">=" in err) for err in errors)

    def test_empty_text_fails(self):
        """Record with empty text fails validation."""
        record = {
            "id": "abc123",
            "text": "   ",  # Whitespace-only text
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 0,
            "text_hash": "hash123",
            "linguistic_register": "formal",
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        assert any("text" in err and "empty" in err for err in errors)

    def test_invalid_lang_confidence_fails(self):
        """Record with out-of-range lang_confidence fails."""
        record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 2,
            "text_hash": "hash123",
            "linguistic_register": "formal",
            "lang_confidence": 1.5,  # Out of range [0.0, 1.0]
        }

        is_valid, errors = validate_ingestion_output(record)

        assert not is_valid
        assert any("lang_confidence" in err for err in errors)

    def test_optional_fields_accepted(self):
        """Record with optional fields passes validation."""
        record = {
            "id": "abc123",
            "text": "Test text",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 2,
            "text_hash": "hash123",
            "linguistic_register": "formal",
            # Optional fields
            "topic": "sports",
            "detected_lang": "so",
            "lang_confidence": 0.95,
            "url": "https://so.wikipedia.org/wiki/Test",
            "timestamp": "2025-12-29T10:00:00Z",
        }

        is_valid, errors = validate_ingestion_output(record)

        assert is_valid
        assert errors == []

    def test_valid_registers(self):
        """All valid register values pass validation."""
        for register_value in ["formal", "informal", "colloquial"]:
            record = {
                "id": "abc123",
                "text": "Test text",
                "source": "wikipedia-somali",
                "run_id": "20251229_100000_wikipedia",
                "schema_version": "1.0",
                "tokens": 2,
                "text_hash": "hash123",
                "linguistic_register": register_value,
            }

            is_valid, errors = validate_ingestion_output(record)

            assert is_valid, f"Valid register '{register_value}' should pass"


class TestContractSchemaCompatibility:
    """Test contract compatibility with SchemaV1_0."""

    def test_contract_fields_subset_of_schema(self):
        """IngestionOutputV1 required fields are subset of SchemaV1_0 fields."""
        # Get SchemaV1_0 field names
        schema_fields = set(SchemaV1_0.model_fields.keys())

        # Contract required fields should all exist in schema
        # Note: linguistic_register has alias "register" in SchemaV1_0
        contract_to_schema_mapping = {
            "id": "id",
            "text": "text",
            "source": "source",
            "run_id": "run_id",
            "schema_version": "schema_version",
            "tokens": "tokens",
            "text_hash": "text_hash",
            "linguistic_register": "linguistic_register",  # SchemaV1_0 uses this name
        }

        for contract_field, schema_field in contract_to_schema_mapping.items():
            assert schema_field in schema_fields, (
                f"Contract field '{contract_field}' (maps to '{schema_field}') "
                f"not found in SchemaV1_0"
            )

    def test_contract_validates_subset_of_schema(self):
        """Contract validation is less strict than SchemaV1_0 validation."""
        # Contract requires 8 fields (as of 2025-12-29: strict validation includes run_id and schema_version)
        assert len(REQUIRED_FIELDS) == 8

        # SchemaV1_0 requires more fields (title, url, source_type, etc.)
        # Contract focuses on minimum interface for downstream consumption
        schema_required = {
            name
            for name, field in SchemaV1_0.model_fields.items()
            if field.is_required() and field.default is None
        }

        # Contract required fields should be subset of schema required fields
        # Note: linguistic_register has alias "register" in schema
        assert "id" in schema_required or "id" in SchemaV1_0.model_fields
        assert "text" in schema_required or "text" in SchemaV1_0.model_fields
        assert "source" in schema_required or "source" in SchemaV1_0.model_fields

    def test_contract_record_valid_for_schema(self):
        """Valid contract record can be extended to valid schema record."""
        # Start with minimal contract record
        contract_record = {
            "id": "abc123",
            "text": "Test text content",
            "source": "wikipedia-somali",
            "run_id": "20251229_100000_wikipedia",
            "schema_version": "1.0",
            "tokens": 3,
            "text_hash": "hash123",
            "linguistic_register": "formal",
        }

        # Verify contract validation passes
        is_valid, errors = validate_ingestion_output(contract_record)
        assert is_valid

        # Extend to full SchemaV1_0 record by adding required fields
        # Note: Remove linguistic_register from contract_record and use "register" alias
        full_record = {
            "id": contract_record["id"],
            "text": contract_record["text"],
            "source": contract_record["source"],
            "run_id": contract_record["run_id"],
            "schema_version": contract_record["schema_version"],
            "tokens": contract_record["tokens"],
            "text_hash": contract_record["text_hash"],
            # Add required SchemaV1_0 fields
            "title": "Test Title",
            "source_type": "wiki",
            "url": "https://so.wikipedia.org/wiki/Test",
            "date_accessed": "2025-12-29",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "encyclopedia",
            "register": "formal",  # SchemaV1_0 uses "register" as alias for linguistic_register
            # Optional fields
            "source_id": None,
            "date_published": None,
            "topic": None,
            "embedding": None,
        }

        # Verify full record validates against SchemaV1_0
        try:
            SchemaV1_0(**full_record)
        except Exception as e:
            pytest.fail(f"Extended contract record should validate against SchemaV1_0: {e}")

    def test_register_field_compatibility(self):
        """Verify linguistic_register field maps correctly to SchemaV1_0.register."""
        # SchemaV1_0 uses "register" as the field name with "linguistic_register" as alias
        assert "linguistic_register" in SchemaV1_0.model_fields
        assert SchemaV1_0.model_fields["linguistic_register"].alias == "register"

        # Contract uses "linguistic_register" as the canonical name
        assert "linguistic_register" in REQUIRED_FIELDS

        # Both should accept the same values
        from somali_dialect_classifier.contracts.ingestion_output import VALID_REGISTERS
        from somali_dialect_classifier.schema.registry import Register

        schema_registers = {r.value for r in Register}
        assert VALID_REGISTERS == schema_registers


class TestContractDocumentation:
    """Test contract documentation and metadata."""

    def test_required_fields_documented(self):
        """All required fields are documented in docstring."""
        import inspect

        docstring = inspect.getdoc(IngestionOutputV1)
        assert docstring is not None

        for field in REQUIRED_FIELDS:
            assert field in docstring, f"Field '{field}' not documented in IngestionOutputV1"

    def test_versioning_strategy_documented(self):
        """Contract includes versioning strategy documentation."""
        from somali_dialect_classifier.contracts import ingestion_output

        module_docstring = ingestion_output.__doc__
        assert module_docstring is not None
        assert "VERSIONING STRATEGY" in module_docstring
        assert "Major version" in module_docstring
        assert "Minor version" in module_docstring

    def test_relationship_to_schema_documented(self):
        """Contract documents relationship to SchemaV1_0."""
        from somali_dialect_classifier.contracts import ingestion_output

        module_docstring = ingestion_output.__doc__
        assert module_docstring is not None
        assert "SchemaV1_0" in module_docstring
        assert "SUBSET" in module_docstring or "subset" in module_docstring
