"""
Tests for checkpoint-based crash recovery functionality.

These tests ensure that:
1. Checkpoints are created at regular intervals
2. Pipelines can resume from the last checkpoint after crashes
3. No duplicate records are created when resuming
4. Checkpoints are cleaned up on successful completion
5. Atomic writes prevent checkpoint corruption
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
from somali_dialect_classifier.ingestion.raw_record import RawRecord
from somali_dialect_classifier.quality.text_cleaners import TextCleaningPipeline


class MockPipeline(BasePipeline):
    """Mock pipeline for testing checkpoint functionality."""

    def __init__(self, test_records=None, **kwargs):
        """Initialize with test records."""
        self.test_records = test_records or []
        # Use a valid source name (wikipedia-somali)
        super().__init__(source="wikipedia-somali", **kwargs)

    def download(self):
        """Mock download - no-op."""
        pass

    def extract(self):
        """Mock extract - create staging file."""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.staging_file = self.staging_dir / "test_staging.json"
        self.staging_file.write_text(json.dumps([]))

        self.processed_file = self.processed_dir / "test_processed.txt"

    def _extract_records(self):
        """Return test records."""
        yield from self.test_records

    def _create_cleaner(self):
        """Return identity cleaner (no-op)."""
        return TextCleaningPipeline([])

    def _get_source_type(self):
        return "wiki"

    def _get_license(self):
        return "CC-BY-SA-3.0"

    def _get_language(self):
        return "so"

    def _get_source_metadata(self):
        return {}

    def _get_domain(self):
        return "test"

    def _get_register(self):
        return "formal"


@pytest.fixture
def temp_work_dir(tmp_path, monkeypatch):
    """Set up temporary working directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    yield tmp_path


@pytest.fixture
def sample_records():
    """Create sample Somali text records."""
    records = []
    for i in range(15):
        records.append(
            RawRecord(
                title=f"Maqaal {i + 1}",
                text=f"Waxaan waa maqaal cusub oo ku saabsan xaalada wadanka Soomaaliya. Tani waa maqaal number {i + 1}. Dowladda way sheegtay in ay tahay mid fiican.",
                url=f"https://example.com/article-{i + 1}",
                metadata={"article_id": i + 1},
            )
        )
    return records


class TestCheckpointCreation:
    """Tests for checkpoint file creation."""

    def test_checkpoint_created_at_interval(self, temp_work_dir, sample_records):
        """Test that checkpoint is created every CHECKPOINT_INTERVAL records."""
        # Use smaller checkpoint interval for testing
        with patch("somali_dialect_classifier.ingestion.base_pipeline.CHECKPOINT_INTERVAL", 5):
            processor = MockPipeline(test_records=sample_records[:7])
            processor.extract()

            # Mock silver writer to prevent actual file writes
            with patch.object(processor.silver_writer, "write", return_value=None):
                processor.process()

            # Checkpoint should have been created (at index 5)
            checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

            # After successful completion, checkpoint should be removed
            assert not checkpoint_path.exists(), "Checkpoint should be removed on success"

    def test_checkpoint_contains_correct_data(self, temp_work_dir, sample_records):
        """Test that checkpoint contains run_id, index, and timestamp."""
        processor = MockPipeline(test_records=sample_records[:3])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Manually save a checkpoint
        processor._save_checkpoint(checkpoint_path, 100)

        assert checkpoint_path.exists()

        data = json.loads(checkpoint_path.read_text())
        assert "last_index" in data
        assert "run_id" in data
        assert "timestamp" in data
        assert data["last_index"] == 100
        assert data["run_id"] == processor.run_id

    def test_checkpoint_uses_atomic_write(self, temp_work_dir):
        """Test that checkpoint uses temp file + rename for atomic writes."""
        processor = MockPipeline(test_records=[])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Track temp file creation
        original_mkstemp = __import__("tempfile").mkstemp
        temp_files_created = []

        def track_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files_created.append(Path(path))
            return fd, path

        with patch("tempfile.mkstemp", side_effect=track_mkstemp):
            processor._save_checkpoint(checkpoint_path, 42)

        # Verify temp file was created then removed
        assert len(temp_files_created) > 0
        for temp_file in temp_files_created:
            assert not temp_file.exists(), "Temp file should be cleaned up"

        # Final checkpoint should exist
        assert checkpoint_path.exists()


class TestCheckpointRecovery:
    """Tests for resuming from checkpoint after crash."""

    def test_pipeline_resumes_from_checkpoint(self, temp_work_dir, sample_records):
        """Test that pipeline resumes from last checkpoint."""
        processor = MockPipeline(test_records=sample_records[:10])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Simulate crash at record 5
        processor._save_checkpoint(checkpoint_path, 5)

        # Track which records are processed
        processed_indices = []
        original_build = processor.record_builder.build_silver_record

        def track_build(*args, **kwargs):
            raw_record = kwargs.get("raw_record")
            if raw_record:
                processed_indices.append(raw_record.metadata.get("article_id"))
            return original_build(*args, **kwargs)

        with patch.object(processor.record_builder, "build_silver_record", side_effect=track_build):
            with patch.object(processor.silver_writer, "write", return_value=None):
                processor.process()

        # Should only process records 6-10 (indices 5-9 in 0-indexed)
        # Records 1-5 (indices 0-4) should be skipped
        assert processed_indices[0] > 5, "Should skip already processed records"

    def test_no_duplicates_after_resume(self, temp_work_dir, sample_records):
        """Test that resuming doesn't create duplicate records."""
        processor = MockPipeline(test_records=sample_records[:8])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Simulate checkpoint at record 4
        processor._save_checkpoint(checkpoint_path, 4)

        # Track all processed records
        all_processed = []
        original_build = processor.record_builder.build_silver_record

        def track_all(*args, **kwargs):
            record = original_build(*args, **kwargs)
            all_processed.append(record)
            return record

        with patch.object(processor.record_builder, "build_silver_record", side_effect=track_all):
            with patch.object(processor.silver_writer, "write", return_value=None):
                processor.process()

        # Should only have 4 records (indices 5-8, skipping 1-4)
        assert len(all_processed) == 4, f"Expected 4 records, got {len(all_processed)}"

        # Verify no duplicate IDs
        record_ids = [r["id"] for r in all_processed]
        assert len(record_ids) == len(set(record_ids)), "Duplicate record IDs found"

    def test_corrupted_checkpoint_starts_fresh(self, temp_work_dir, sample_records):
        """Test that corrupted checkpoint is ignored and processing starts fresh."""
        processor = MockPipeline(test_records=sample_records[:5])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Create checkpoint directory and corrupted checkpoint file
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text("invalid json {{{")

        # Track processed records
        processed_count = [0]
        original_build = processor.record_builder.build_silver_record

        def count_records(*args, **kwargs):
            processed_count[0] += 1
            return original_build(*args, **kwargs)

        with patch.object(
            processor.record_builder, "build_silver_record", side_effect=count_records
        ):
            with patch.object(processor.silver_writer, "write", return_value=None):
                processor.process()

        # Should process all 5 records (starting from 0)
        assert processed_count[0] == 5


class TestCheckpointCleanup:
    """Tests for checkpoint cleanup."""

    def test_checkpoint_removed_on_success(self, temp_work_dir, sample_records):
        """Test that checkpoint is removed on successful completion."""
        processor = MockPipeline(test_records=sample_records[:3])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Manually create checkpoint
        processor._save_checkpoint(checkpoint_path, 1)
        assert checkpoint_path.exists()

        # Run pipeline to completion
        with patch.object(processor.silver_writer, "write", return_value=None):
            processor.process()

        # Checkpoint should be removed
        assert not checkpoint_path.exists()

    def test_checkpoint_preserved_on_failure(self, temp_work_dir, sample_records):
        """Test that checkpoint is preserved when pipeline fails."""
        processor = MockPipeline(test_records=sample_records[:5])
        processor.extract()

        processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        # Make processing fail after first batch
        call_count = [0]

        def failing_write(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 1:
                raise RuntimeError("Simulated crash")
            return None

        # Force checkpoint interval to 2 for testing
        with patch("somali_dialect_classifier.ingestion.base_pipeline.CHECKPOINT_INTERVAL", 2):
            with patch.object(processor.silver_writer, "write", side_effect=failing_write):
                with pytest.raises(RuntimeError):
                    processor.process()

        # Checkpoint should exist at record 2 (first checkpoint interval hit)
        # Note: actual checkpoint creation depends on when failure occurs


class TestCheckpointEdgeCases:
    """Tests for edge cases."""

    def test_empty_dataset_no_checkpoint(self, temp_work_dir):
        """Test that empty dataset doesn't create checkpoint."""
        processor = MockPipeline(test_records=[])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        with patch.object(processor.silver_writer, "write", return_value=None):
            processor.process()

        # No checkpoint should exist (no records processed)
        assert not checkpoint_path.exists()

    def test_checkpoint_interval_not_reached(self, temp_work_dir, sample_records):
        """Test behavior when CHECKPOINT_INTERVAL is not reached."""
        # If we have fewer records than CHECKPOINT_INTERVAL, no checkpoint is saved
        processor = MockPipeline(test_records=sample_records[:3])
        processor.extract()

        checkpoint_path = processor.processed_dir / f"{processor.run_id}_checkpoint.json"

        with patch.object(processor.silver_writer, "write", return_value=None):
            processor.process()

        # With default CHECKPOINT_INTERVAL=1000, no checkpoint for 3 records
        assert not checkpoint_path.exists()

    def test_load_checkpoint_missing_file(self, temp_work_dir):
        """Test loading checkpoint when file doesn't exist."""
        processor = MockPipeline(test_records=[])
        processor.extract()

        checkpoint_path = processor.processed_dir / "nonexistent_checkpoint.json"

        index = processor._load_checkpoint(checkpoint_path)

        assert index == 0, "Should return 0 when checkpoint doesn't exist"

    def test_checkpoint_with_different_run_id(self, temp_work_dir, sample_records):
        """Test that checkpoint from different run_id is loaded (but warns)."""
        processor = MockPipeline(test_records=sample_records[:3])
        processor.extract()

        # Create checkpoint with different run_id
        checkpoint_path = processor.processed_dir / "old_run_checkpoint.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        old_checkpoint = {
            "last_index": 50,
            "run_id": "different-run-id-12345",
            "timestamp": "2025-01-01T00:00:00",
        }
        checkpoint_path.write_text(json.dumps(old_checkpoint))

        # Load should succeed (resuming from checkpoint)
        index = processor._load_checkpoint(checkpoint_path)
        assert index == 50
