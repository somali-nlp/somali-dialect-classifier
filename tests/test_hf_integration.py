"""
Integration tests for HuggingFace datasets processor.

Uses small dataset samples (5 records) to avoid network I/O in CI.
Validates schema mapping, field extraction, and filter integration.
"""

import json

import pytest

try:
    from datasets import Dataset

    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False

# Skip ALL tests in this module - HuggingFace processor features not fully implemented
pytestmark = [
    pytest.mark.skip(
        reason="HuggingFace processor features not fully implemented - requires backend engineer"
    ),
    pytest.mark.skipif(not DATASETS_AVAILABLE, reason="datasets library not installed"),
]

from somali_dialect_classifier.ingestion.processors.huggingface_somali_processor import (
    HuggingFaceSomaliProcessor,
    create_mc4_processor,
)


@pytest.fixture
def temp_work_dir(tmp_path, monkeypatch):
    """Create temporary working directory for tests."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    return work_dir


@pytest.fixture
def mock_hf_dataset():
    """Create small mock HF dataset for testing."""
    data = {
        "text": [
            "Muqdisho waa magaalada caasimadda ah ee Soomaaliya. Waxay ku taalla xeebta Badweynta Hindi.",
            "Soomaaliya waa waddan ku yaal Geeska Afrika. Waxay ku taalla bariga Afrika.",
            "Waxaan jeclahay inaan barto afka Soomaaliga. Waa af qurux badan.",
            "This is English text that should be filtered out by language detection.",
            "Short",  # Will be filtered by min_length
        ],
        "url": [
            "https://example.com/article1",
            "https://example.com/article2",
            "https://example.com/article3",
            "https://example.com/article4",
            "https://example.com/article5",
        ],
        "timestamp": [
            "2023-01-01",
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
        ],
    }
    return Dataset.from_dict(data)


class TestHuggingFaceSomaliProcessor:
    """Test HuggingFace datasets processor."""

    def test_processor_initialization(self):
        """Test processor can be initialized."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            dataset_config="so",
            split="train",
            text_field="text",
        )

        assert processor.dataset_name == "test/dataset"
        assert processor.dataset_config == "so"
        assert processor.split == "train"
        # Source format: HuggingFace-Somali_{dataset_slug}-{config}
        assert processor.source == "HuggingFace-Somali_dataset-so"

    def test_manifest_creation(self, temp_work_dir, monkeypatch):
        """Test manifest file is created correctly."""

        # Mock load_dataset to avoid network call
        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test-revision"
                info = type(
                    "obj",
                    (object,),
                    {"description": "Test dataset", "license": "MIT", "features": {}},
                )

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.ingestion.processors.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            dataset_config="so",
            split="train",
            text_field="text",
            url_field="url",
            metadata_fields=["timestamp"],
        )

        manifest_path = processor.download()

        assert manifest_path.exists()
        assert manifest_path.name == "dataset_manifest.json"  # Should match dataset slug

        # Verify manifest content
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["dataset_name"] == "test/dataset"
        assert manifest["dataset_config"] == "so"
        assert manifest["split"] == "train"
        assert manifest["text_field"] == "text"
        assert manifest["url_field"] == "url"
        assert manifest["metadata_fields"] == ["timestamp"]
        assert manifest["last_offset"] == 0
        assert manifest["batches_completed"] == []
        assert "created_at" in manifest

    def test_field_mapping(self):
        """Test HF record is correctly mapped to RawRecord."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            dataset_config="so",
            split="train",
            text_field="text",
            url_field="url",
            metadata_fields=["timestamp"],
        )

        hf_record = {
            "text": "Muqdisho waa magaalada caasimadda ah.",
            "url": "https://example.com/article",
            "timestamp": "2023-01-01",
            "extra_field": "ignored",
        }

        raw_record = processor._map_to_raw_record(hf_record)

        assert raw_record.text == "Muqdisho waa magaalada caasimadda ah."
        assert raw_record.url == "https://example.com/article"
        assert raw_record.metadata["timestamp"] == "2023-01-01"
        assert raw_record.metadata["hf_dataset"] == "test/dataset"
        assert raw_record.metadata["hf_config"] == "so"
        assert "extra_field" not in raw_record.metadata

    def test_title_generation_from_text(self):
        """Test title is generated from text if not specified."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        hf_record = {
            "text": "This is a long piece of text that should be truncated to 50 characters for the title field."
        }

        raw_record = processor._map_to_raw_record(hf_record)

        assert len(raw_record.title) <= 53  # 50 chars + "..."
        assert raw_record.title.endswith("...")

    def test_url_generation_if_missing(self):
        """Test URL is generated if not specified."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            dataset_config="so",
            text_field="text",
        )

        hf_record = {"text": "Test text"}

        raw_record = processor._map_to_raw_record(hf_record)

        assert raw_record.url == "hf://test/dataset/so"

    def test_batch_writing(self, temp_work_dir):
        """Test JSONL batch files are written correctly."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        batch = [
            {"text": "First record", "id": 1},
            {"text": "Second record", "id": 2},
            {"text": "Third record", "id": 3},
        ]

        batch_file = temp_work_dir / "test_batch.jsonl"
        processor._write_batch(batch, batch_file)

        assert batch_file.exists()

        # Verify content
        with open(batch_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3

        for i, line in enumerate(lines):
            record = json.loads(line)
            assert record["text"] == batch[i]["text"]
            assert record["id"] == batch[i]["id"]

    def test_filters_are_registered(self):
        """Test quality filters are registered."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        assert len(processor.record_filters) == 2  # min_length + langid

        # Verify filter names
        filter_funcs = [f[0].__name__ for f in processor.record_filters]
        assert "min_length_filter" in filter_funcs
        assert "langid_filter" in filter_funcs

    def test_source_type_inference(self):
        """Test source type is inferred from dataset name."""
        news_processor = HuggingFaceSomaliProcessor(dataset_name="allenai/gdelt", text_field="text")
        assert news_processor._get_source_type() == "news"

        social_processor = HuggingFaceSomaliProcessor(
            dataset_name="twitter/somali-tweets", text_field="text"
        )
        assert social_processor._get_source_type() == "social"

        web_processor = HuggingFaceSomaliProcessor(
            dataset_name="mc4", dataset_config="so", text_field="text"
        )
        assert web_processor._get_source_type() == "web"

    def test_license_inference(self):
        """Test license is inferred from dataset name."""
        mc4_processor = HuggingFaceSomaliProcessor(
            dataset_name="mc4", dataset_config="so", text_field="text"
        )
        assert mc4_processor._get_license() == "ODC-BY-1.0"

        oscar_processor = HuggingFaceSomaliProcessor(
            dataset_name="oscar-corpus/OSCAR-2301", dataset_config="so", text_field="text"
        )
        assert oscar_processor._get_license() == "CC0-1.0"


class TestHFFactoryFunctions:
    """Test factory functions for common datasets."""

    def test_create_mc4_processor(self):
        """Test MC4 processor factory."""
        processor = create_mc4_processor(max_records=1000)

        assert processor.dataset_name == "allenai/c4"
        assert processor.dataset_config == "so"
        assert processor.split == "train"
        assert processor.text_field == "text"
        assert processor.url_field == "url"
        assert "timestamp" in processor.metadata_fields
        assert processor.max_records == 1000

    # ============================================================================
    # REMOVED: OSCAR and MADLAD-400 Factory Tests
    # ============================================================================
    #
    # Tests for create_oscar_processor() and create_madlad400_processor() have
    # been REMOVED because these processors are no longer supported.
    #
    # See:
    # - docs/decisions/003-madlad-400-exclusion.md (MADLAD-400)
    # - docs/decisions/001-oscar-exclusion.md (OSCAR)
    #
    # Use create_mc4_processor() instead.
    # ============================================================================


class TestHFIntegration:
    """End-to-end integration tests with small samples."""

    @pytest.mark.skip(reason="Requires network access - run manually")
    def test_mc4_integration_small_sample(self, temp_work_dir):
        """Test MC4 pipeline with 5 record sample."""
        processor = create_mc4_processor(max_records=5)

        # Download (create manifest)
        manifest_path = processor.download()
        assert manifest_path.exists()

        # Extract (stream and batch)
        staging_dir = processor.extract()
        assert staging_dir.exists()

        # Find batch files
        batch_files = list(staging_dir.glob("batch_*.jsonl"))
        assert len(batch_files) >= 1

        # Process (clean, filter, write silver)
        silver_path = processor.process()
        assert silver_path.exists()
        assert silver_path.suffix == ".parquet"

    # ============================================================================
    # REMOVED: OSCAR Integration Test
    # ============================================================================
    #
    # test_oscar_integration_small_sample() has been REMOVED because
    # create_oscar_processor() is no longer supported.
    #
    # See: docs/decisions/001-oscar-exclusion.md
    # ============================================================================

    def test_resume_capability(self, temp_work_dir, monkeypatch):
        """Test extraction can resume from last offset."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
            streaming_batch_size=2,
        )

        # Create manifest with last_offset = 2
        manifest_dir = processor.raw_dir
        manifest_dir.mkdir(parents=True, exist_ok=True)
        dataset_slug = "dataset"  # test/dataset -> "dataset"
        manifest_file = manifest_dir / f"{dataset_slug}_manifest.json"

        manifest = {
            "dataset_name": "test/dataset",
            "dataset_config": None,
            "split": "train",
            "text_field": "text",
            "last_offset": 2,
            "batches_completed": ["batch_000000.jsonl"],
            "streaming_batch_size": 2,
        }

        with open(manifest_file, "w") as f:
            json.dump(manifest, f)

        # Mock load_dataset to return 5 records
        def mock_load_dataset(*args, **kwargs):
            data = [{"text": f"Record {i}"} for i in range(5)]
            return iter(data)

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.ingestion.processors.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

            # Extract should start from offset 2 (skip first 2 records)
            processor.extract()

            # Verify manifest updated
            with open(manifest_file) as f:
                updated_manifest = json.load(f)

            assert updated_manifest["last_offset"] >= 2


class TestHFConfiguration:
    """Test HF configuration integration."""

    def test_config_values_used(self, monkeypatch):
        """Test processor uses config values."""
        # Override config
        monkeypatch.setenv("SDC_SCRAPING__HUGGINGFACE__STREAMING_BATCH_SIZE", "1000")
        monkeypatch.setenv("SDC_SCRAPING__HUGGINGFACE__MIN_LENGTH_THRESHOLD", "200")

        # Force reload config with new env vars
        from somali_dialect_classifier.infra.config import reset_config

        reset_config()

        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        # Verify config loaded
        assert processor.hf_config.streaming_batch_size == 1000
        assert processor.hf_config.min_length_threshold == 200

    def test_filter_threshold_from_config(self):
        """Test filter uses threshold from config."""
        # Reset config to defaults
        from somali_dialect_classifier.infra.config import reset_config

        reset_config()

        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        # Find min_length_filter
        min_length_filter = None
        for filter_func, kwargs in processor.record_filters:
            if filter_func.__name__ == "min_length_filter":
                min_length_filter = kwargs
                break

        assert min_length_filter is not None
        # Should use config value (default 100)
        assert min_length_filter["threshold"] == 100


class TestHFErrorHandling:
    """Test error handling and edge cases."""

    def test_missing_text_field(self):
        """Test error handling when text field missing."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="content",  # Wrong field name
        )

        hf_record = {"text": "Content here"}  # Field is "text" not "content"

        raw_record = processor._map_to_raw_record(hf_record)

        # Should handle gracefully with empty text
        assert raw_record.text == ""

    def test_extraction_without_download(self, temp_work_dir):
        """Test extract fails if download not run first."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        with pytest.raises(FileNotFoundError, match="Manifest not found"):
            processor.extract()

    def test_process_without_extract(self, temp_work_dir, monkeypatch):
        """Test process fails if extract not run first."""
        processor = HuggingFaceSomaliProcessor(
            dataset_name="test/dataset",
            text_field="text",
        )

        # Create manifest
        def mock_load_dataset(*args, **kwargs):
            class MockDataset:
                revision = "test"
                info = None

            return MockDataset()

        if DATASETS_AVAILABLE:
            monkeypatch.setattr(
                "somali_dialect_classifier.ingestion.processors.huggingface_somali_processor.load_dataset",
                mock_load_dataset,
            )

            processor.download()

            # Try to process without extract
            with pytest.raises(FileNotFoundError, match="Staging directory not found"):
                processor.process()
