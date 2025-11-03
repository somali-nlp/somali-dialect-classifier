"""
Unit tests for HuggingFace datasets processor.

Tests processor initialization, file creation, and integration with base pipeline contract.
"""

from pathlib import Path

import pytest

try:
    from datasets import Dataset

    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False

from somali_dialect_classifier.preprocessing.huggingface_somali_processor import (
    create_mc4_processor,
)

pytestmark = pytest.mark.skipif(not DATASETS_AVAILABLE, reason="datasets library not installed")


@pytest.fixture
def temp_work_dir(tmp_path, monkeypatch):
    """Create temporary working directory for tests."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    return work_dir


class TestHFProcessorFiles:
    """Test that HFDatasets processor creates all expected files."""

    def test_processed_file_is_set(self):
        """Test that processed_file is set during initialization."""
        processor = create_mc4_processor(max_records=10)

        assert hasattr(processor, "processed_file")
        assert processor.processed_file is not None
        assert processor.processed_file.name == "c4_processed.txt"

    def test_manifest_uses_dataset_slug(self, temp_work_dir, monkeypatch):
        """Test that manifest file uses dataset-specific naming."""

        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test-revision"
                info = None

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.preprocessing.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

        processor = create_mc4_processor(max_records=10)
        manifest_path = processor.download()

        assert manifest_path.name == "c4_manifest.json"  # Not hf_manifest.json
        assert manifest_path.exists()

    def test_processed_file_written_after_process(self, temp_work_dir, monkeypatch):
        """Test that processed text file is written during process()."""
        # Create mock dataset with text long enough to pass min_length filter (100 chars)
        mock_data = [
            {
                "text": "Muqdisho waa magaalada caasimadda ah ee Soomaaliya. Waxay ku taalla xeebta Badweynta Hindi ee koonfurta Soomaaliya.",
                "url": "http://ex.com/1",
                "timestamp": "2023-01-01",
            },
            {
                "text": "Soomaaliya waa waddan ku yaal Geeska Afrika. Waxay ku taalla bariga Afrika oo waxay leedahay xeeb dheer.",
                "url": "http://ex.com/2",
                "timestamp": "2023-01-02",
            },
        ]

        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test"
                info = None

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.preprocessing.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

        processor = create_mc4_processor(max_records=10)

        # Setup: create manifest, staging, and mock JSONL batch
        processor.download()

        staging_dir = processor.staging_dir
        staging_dir.mkdir(parents=True, exist_ok=True)

        # Write mock JSONL batch
        batch_file = staging_dir / "batch_000000.jsonl"
        import json

        with open(batch_file, "w", encoding="utf-8") as f:
            for record in mock_data:
                f.write(json.dumps(record) + "\n")

        # Mark extraction complete
        (staging_dir / ".extraction_complete").touch()

        # Process
        processor.process()

        # Assert: processed_file was created
        assert processor.processed_file.exists(), f"Expected {processor.processed_file} to exist"

        # Verify content format
        with open(processor.processed_file, encoding="utf-8") as f:
            content = f.read()

        # Should contain both texts
        assert "Muqdisho" in content
        assert "Soomaaliya" in content

    def test_manifest_contains_audit_metadata(self, temp_work_dir, monkeypatch):
        """Test that manifest contains audit fields for Ops."""

        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test"
                info = None

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.preprocessing.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

        processor = create_mc4_processor(max_records=10)
        manifest_path = processor.download()

        # Read manifest
        import json

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Check audit fields exist
        assert "total_records_extracted" in manifest
        assert "total_batches" in manifest
        assert "manifest_version" in manifest
        assert manifest["manifest_version"] == "1.0"

    def test_process_always_returns_path_or_raises(self, temp_work_dir, monkeypatch):
        """Test that process() always returns a Path or raises an exception (never returns None)."""
        # Create mock dataset with text long enough to pass min_length filter (100 chars)
        mock_data = [
            {
                "text": "Muqdisho waa magaalada ugu weyn ee Soomaaliya. Waxay ku taalla xeebta Badweynta Hindi ee koonfurta Soomaaliya oo waxay leedahay taariikhda dheer.",
                "url": "http://ex.com/1",
                "timestamp": "2023-01-01",
            },
        ]

        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test"
                info = None

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.preprocessing.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

        processor = create_mc4_processor(max_records=10)

        # Setup: create manifest, staging, and mock JSONL batch
        processor.download()

        staging_dir = processor.staging_dir
        staging_dir.mkdir(parents=True, exist_ok=True)

        # Write mock JSONL batch
        batch_file = staging_dir / "batch_000000.jsonl"
        import json

        with open(batch_file, "w", encoding="utf-8") as f:
            for record in mock_data:
                f.write(json.dumps(record) + "\n")

        # Mark extraction complete
        (staging_dir / ".extraction_complete").touch()

        # Process and verify return value
        result = processor.process()
        assert result is not None, "process() must not return None"
        assert isinstance(result, Path), f"process() must return Path, got {type(result)}"

    def test_process_raises_on_empty_results(self, temp_work_dir, monkeypatch):
        """Test that process() raises ValueError when all records are filtered."""
        # Create mock dataset with text that will be filtered
        mock_data = [
            {"text": "x", "url": "http://ex.com/1", "timestamp": "2023-01-01"},  # Too short
        ]

        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test"
                info = None

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.preprocessing.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

        processor = create_mc4_processor(max_records=10)

        # Setup: create manifest, staging, and mock JSONL batch
        processor.download()

        staging_dir = processor.staging_dir
        staging_dir.mkdir(parents=True, exist_ok=True)

        # Write mock JSONL batch
        batch_file = staging_dir / "batch_000000.jsonl"
        import json

        with open(batch_file, "w", encoding="utf-8") as f:
            for record in mock_data:
                f.write(json.dumps(record) + "\n")

        # Mark extraction complete
        (staging_dir / ".extraction_complete").touch()

        # Process should raise ValueError
        with pytest.raises(ValueError, match="No records passed filters"):
            processor.process()


# ============================================================================
# REMOVED: MADLAD-400 and OSCAR Tests
# ============================================================================
#
# Tests for create_madlad400_processor() and create_oscar_processor() have been
# REMOVED because these processors are no longer supported.
#
# Reasons:
# - MADLAD-400: Incompatible with datasets>=3.0 (uses deprecated dataset scripts)
# - OSCAR: Requires authentication, has less data than MC4
#
# See:
# - docs/decisions/003-madlad-400-exclusion.md
# - docs/decisions/001-oscar-exclusion.md
# - MADLAD400_STATUS.md
#
# Use create_mc4_processor() for all HuggingFace data needs.
# ============================================================================
