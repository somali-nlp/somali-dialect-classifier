"""
Contract tests for BasePipeline.

These tests ensure that:
1. Any processor inheriting from BasePipeline implements required abstract methods
2. The processor behaves correctly (returns proper types, handles errors, etc.)
3. New processors (HuggingFace, VOA, etc.) will automatically be validated

Usage:
    To test a new processor, add it to the PROCESSOR_CLASSES list.
"""

import pytest
from pathlib import Path
from typing import Iterator
import tempfile
import shutil

from somali_dialect_classifier.preprocessing.base_pipeline import BasePipeline, RawRecord
from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import WikipediaSomaliProcessor
from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor


# List of all processor classes to test
# Add new processors here to automatically validate them
PROCESSOR_CLASSES = [
    WikipediaSomaliProcessor,
    BBCSomaliProcessor,
]


class TestBasePipelineContract:
    """Contract tests that all BasePipeline subclasses must pass."""

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_processor_implements_required_methods(self, processor_class):
        """Test that processor implements all required abstract methods."""
        # Should be instantiable (all abstract methods implemented)
        try:
            if processor_class == BBCSomaliProcessor:
                processor = processor_class(max_articles=10)
            else:
                processor = processor_class()
        except TypeError as e:
            pytest.fail(f"{processor_class.__name__} failed to instantiate: {e}")

        # Required methods from DataProcessor
        assert hasattr(processor, 'download'), f"{processor_class.__name__} missing download()"
        assert hasattr(processor, 'extract'), f"{processor_class.__name__} missing extract()"
        assert hasattr(processor, 'process'), f"{processor_class.__name__} missing process()"
        assert hasattr(processor, 'save'), f"{processor_class.__name__} missing save()"
        assert hasattr(processor, 'run'), f"{processor_class.__name__} missing run()"

        # Required abstract methods from BasePipeline
        assert hasattr(processor, '_create_cleaner'), f"{processor_class.__name__} missing _create_cleaner()"
        assert hasattr(processor, '_extract_records'), f"{processor_class.__name__} missing _extract_records()"
        assert hasattr(processor, '_get_source_type'), f"{processor_class.__name__} missing _get_source_type()"
        assert hasattr(processor, '_get_license'), f"{processor_class.__name__} missing _get_license()"
        assert hasattr(processor, '_get_language'), f"{processor_class.__name__} missing _get_language()"
        assert hasattr(processor, '_get_source_metadata'), f"{processor_class.__name__} missing _get_source_metadata()"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_processor_has_required_attributes(self, processor_class):
        """Test that processor has required attributes from BasePipeline."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        # Attributes set by BasePipeline.__init__
        assert hasattr(processor, 'source'), f"{processor_class.__name__} missing source"
        assert hasattr(processor, 'date_accessed'), f"{processor_class.__name__} missing date_accessed"
        assert hasattr(processor, 'raw_dir'), f"{processor_class.__name__} missing raw_dir"
        assert hasattr(processor, 'staging_dir'), f"{processor_class.__name__} missing staging_dir"
        assert hasattr(processor, 'processed_dir'), f"{processor_class.__name__} missing processed_dir"
        assert hasattr(processor, 'text_cleaner'), f"{processor_class.__name__} missing text_cleaner"
        assert hasattr(processor, 'silver_writer'), f"{processor_class.__name__} missing silver_writer"
        assert hasattr(processor, 'logger'), f"{processor_class.__name__} missing logger"
        assert hasattr(processor, 'log_frequency'), f"{processor_class.__name__} missing log_frequency"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_source_naming_convention(self, processor_class):
        """Test that source name follows naming convention."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        # Source should be non-empty
        assert processor.source, f"{processor_class.__name__} has empty source"

        # Source should follow pattern: Provider-Language
        assert '-' in processor.source, f"{processor_class.__name__} source doesn't follow 'Provider-Language' pattern"

        # Should end with -Somali or similar
        assert 'Somali' in processor.source or 'so' in processor.source.lower(), \
            f"{processor_class.__name__} source doesn't indicate Somali language"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_get_source_type_returns_string(self, processor_class):
        """Test that _get_source_type returns a non-empty string."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        source_type = processor._get_source_type()
        assert isinstance(source_type, str), f"{processor_class.__name__}._get_source_type() must return string"
        assert source_type, f"{processor_class.__name__}._get_source_type() returned empty string"

        # Should be one of the known types
        valid_types = ['wiki', 'news', 'social_media', 'book', 'transcript', 'web']
        assert source_type in valid_types, \
            f"{processor_class.__name__}._get_source_type() returned '{source_type}', " \
            f"expected one of {valid_types}"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_get_license_returns_string(self, processor_class):
        """Test that _get_license returns a non-empty string."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        license_str = processor._get_license()
        assert isinstance(license_str, str), f"{processor_class.__name__}._get_license() must return string"
        assert license_str, f"{processor_class.__name__}._get_license() returned empty string"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_get_language_returns_iso_code(self, processor_class):
        """Test that _get_language returns valid ISO 639-1 code."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        language = processor._get_language()
        assert isinstance(language, str), f"{processor_class.__name__}._get_language() must return string"

        # Should be 2-character ISO 639-1 code
        assert len(language) == 2, \
            f"{processor_class.__name__}._get_language() should return 2-char ISO code, got '{language}'"

        # For Somali processors, should be 'so'
        assert language == 'so', \
            f"{processor_class.__name__}._get_language() should return 'so' for Somali, got '{language}'"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_get_source_metadata_returns_dict(self, processor_class):
        """Test that _get_source_metadata returns a dictionary."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        metadata = processor._get_source_metadata()
        assert isinstance(metadata, dict), \
            f"{processor_class.__name__}._get_source_metadata() must return dict"

        # Metadata can be empty, but should be a dict
        # All values should be JSON-serializable
        import json
        try:
            json.dumps(metadata)
        except (TypeError, ValueError) as e:
            pytest.fail(f"{processor_class.__name__}._get_source_metadata() returned non-JSON-serializable dict: {e}")

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_create_cleaner_returns_pipeline(self, processor_class):
        """Test that _create_cleaner returns a TextCleaningPipeline."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        cleaner = processor._create_cleaner()

        # Should have a clean() method
        assert hasattr(cleaner, 'clean'), \
            f"{processor_class.__name__}._create_cleaner() must return object with clean() method"
        assert callable(cleaner.clean), \
            f"{processor_class.__name__}._create_cleaner().clean must be callable"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_extract_records_returns_iterator(self, processor_class):
        """Test that _extract_records returns an iterator of RawRecord."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        # _extract_records should be callable
        assert callable(processor._extract_records), \
            f"{processor_class.__name__}._extract_records must be callable"

        # Should return an iterator
        result = processor._extract_records()
        assert hasattr(result, '__iter__'), \
            f"{processor_class.__name__}._extract_records() must return an iterator"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_directory_structure_uses_partitioning(self, processor_class):
        """Test that processor uses source partitioning in directory structure."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        # Raw dir should include source partitioning
        assert f"source={processor.source}" in str(processor.raw_dir), \
            f"{processor_class.__name__} raw_dir doesn't use source partitioning"

        # Should include date_accessed partitioning
        assert f"date_accessed=" in str(processor.raw_dir), \
            f"{processor_class.__name__} raw_dir doesn't use date_accessed partitioning"

    @pytest.mark.parametrize("processor_class", PROCESSOR_CLASSES)
    def test_process_returns_path(self, processor_class):
        """Test that process() returns a Path object."""
        if processor_class == BBCSomaliProcessor:
            processor = processor_class(max_articles=10)
        else:
            processor = processor_class()

        # process() should return Path type (won't run it, just check signature)
        import inspect
        sig = inspect.signature(processor.process)
        assert sig.return_annotation == Path or 'Path' in str(sig.return_annotation), \
            f"{processor_class.__name__}.process() should return Path"


class TestRawRecord:
    """Tests for RawRecord dataclass."""

    def test_raw_record_creation(self):
        """Test that RawRecord can be created with required fields."""
        record = RawRecord(
            title="Test Title",
            text="Test text content",
            url="https://example.com",
            metadata={"key": "value"}
        )

        assert record.title == "Test Title"
        assert record.text == "Test text content"
        assert record.url == "https://example.com"
        assert record.metadata == {"key": "value"}

    def test_raw_record_metadata_defaults_to_empty_dict(self):
        """Test that metadata defaults to empty dict."""
        record = RawRecord(
            title="Test",
            text="Text",
            url="https://example.com"
        )

        assert record.metadata == {}


class TestProcessorAdditionGuide:
    """
    Guide for adding new processors.

    When adding a new processor (e.g., VOASomaliProcessor, HuggingFaceProcessor):

    1. Inherit from BasePipeline:
        class VOASomaliProcessor(BasePipeline):
            def __init__(self):
                super().__init__(source="VOA-Somali")

    2. Implement required abstract methods:
        - _create_cleaner() -> TextCleaningPipeline
        - _extract_records() -> Iterator[RawRecord]
        - _get_source_type() -> str
        - _get_license() -> str
        - _get_language() -> str
        - _get_source_metadata() -> Dict[str, Any]

    3. Add to PROCESSOR_CLASSES list above

    4. Run tests:
        pytest tests/test_base_pipeline_contract.py -v

    All contract tests will automatically validate your new processor!
    """

    def test_guide_exists(self):
        """This test ensures the guide docstring is present."""
        assert self.__class__.__doc__ is not None
        assert "VOASomaliProcessor" in self.__class__.__doc__
