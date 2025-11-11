"""
Tests for ValidationService.

Verifies schema validation functionality.
"""

import pytest

from somali_dialect_classifier.schema.validation_service import ValidationService


class TestValidationService:
    """Test suite for ValidationService."""

    def test_initialization(self):
        """Test ValidationService initialization."""
        service = ValidationService()
        assert service.validation_failures == 0
        assert service.schema_version is None

    def test_initialization_with_version(self):
        """Test ValidationService initialization with specific schema version."""
        service = ValidationService(schema_version="1.0")
        assert service.schema_version == "1.0"

    def test_validate_valid_record(self):
        """Test validating a valid record."""
        service = ValidationService()
        valid_record = {
            "id": "test_id_123",
            "text": "This is a test record with sufficient content.",
            "title": "Test Title",
            "source": "wikipedia-somali",
            "source_type": "wiki",
            "url": "https://so.wikipedia.org/wiki/Test",
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "tokens": 10,
            "text_hash": "abcdef1234567890" * 4,  # 64 chars
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "encyclopedia",
            "register": "formal",
            "schema_version": "1.0",
            "run_id": "test_run_123"
        }
        is_valid, errors = service.validate_record(valid_record)
        assert is_valid is True
        assert errors == []
        assert service.validation_failures == 0

    def test_validate_invalid_record(self):
        """Test validating an invalid record."""
        service = ValidationService()
        invalid_record = {
            "id": "test_id",
            "text": "",  # Empty text (invalid)
            "title": "Test",
            "source": "invalid-source",  # Invalid source
            "source_type": "invalid_type",  # Invalid type
            "url": "https://example.com",
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "MIT",
            "tokens": -1,  # Invalid token count
            "text_hash": "hash",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "test",
            "register": "invalid_register",  # Invalid register
            "schema_version": "1.0",
            "run_id": "test_run"
        }
        is_valid, errors = service.validate_record(invalid_record)
        assert is_valid is False
        assert len(errors) > 0
        assert service.validation_failures == 1

    def test_get_validation_errors(self):
        """Test getting detailed validation errors."""
        service = ValidationService()
        invalid_record = {
            "id": "test_id",
            "text": "",  # Empty text
            "title": "Test",
            "source": "wikipedia-somali",
            "source_type": "wiki",
            "url": "https://example.com",
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "tokens": 0,
            "text_hash": "hash",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "test",
            "register": "formal",
            "schema_version": "1.0",
            "run_id": "test_run"
        }
        errors = service.get_validation_errors(invalid_record)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_get_failure_count(self):
        """Test getting validation failure count."""
        service = ValidationService()
        assert service.get_failure_count() == 0
        # Validate invalid records
        invalid_record = {
            "id": "test_id",
            "text": "",  # Empty
            "title": "Test",
            "source": "wikipedia-somali",
            "source_type": "wiki",
            "url": "https://example.com",
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "tokens": 0,
            "text_hash": "hash",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "test",
            "register": "formal",
            "schema_version": "1.0",
            "run_id": "test_run"
        }
        service.validate_record(invalid_record)
        service.validate_record(invalid_record)
        assert service.get_failure_count() == 2

    def test_reset_failures(self):
        """Test resetting validation failure counter."""
        service = ValidationService()
        invalid_record = {
            "id": "test_id",
            "text": "",
            "title": "Test",
            "source": "wikipedia-somali",
            "source_type": "wiki",
            "url": "https://example.com",
            "date_accessed": "2025-01-01",
            "language": "so",
            "license": "CC-BY-SA-3.0",
            "tokens": 0,
            "text_hash": "hash",
            "pipeline_version": "2.1.0",
            "source_metadata": "{}",
            "domain": "test",
            "register": "formal",
            "schema_version": "1.0",
            "run_id": "test_run"
        }
        service.validate_record(invalid_record)
        assert service.get_failure_count() > 0
        service.reset_failures()
        assert service.get_failure_count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
