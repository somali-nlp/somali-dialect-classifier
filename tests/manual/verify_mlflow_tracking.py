import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil
from typing import Any, Iterator

from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
from somali_dialect_classifier.ingestion.raw_record import RawRecord
from somali_dialect_classifier.quality.text_cleaners import TextCleaningPipeline

class DummyPipeline(BasePipeline):
    def _extract_records(self) -> Iterator[RawRecord]:
        yield RawRecord(
            url="http://example.com/1",
            text="Dummy text content",
            title="Dummy Title",
            metadata={}
        )

    def _create_cleaner(self) -> TextCleaningPipeline:
        cleaner = MagicMock()
        cleaner.clean.return_value = "Cleaned dummy text"
        return cleaner

    def _get_source_type(self) -> str:
        return "web"

    def _get_license(self) -> str:
        return "MIT"

    def _get_language(self) -> str:
        return "so"

    def _get_source_metadata(self) -> dict[str, Any]:
        return {}

    def _get_domain(self) -> str:
        return "test"

    def _get_register(self) -> str:
        return "formal"

    def download(self) -> None:
        pass

    def extract(self) -> None:
        pass

class TestMLflowIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/manual/temp_data")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock dependencies
        self.mock_data_manager = MagicMock()
        self.mock_filter_engine = MagicMock()
        self.mock_filter_engine.apply_filters.return_value = (True, None, {})
        self.mock_record_builder = MagicMock()
        self.mock_record_builder.build_silver_record.return_value = {
            "id": "123", "text_hash": "abc", "text": "Cleaned dummy text"
        }
        self.mock_validation_service = MagicMock()
        self.mock_validation_service.validate_record.return_value = (True, [])

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch("somali_dialect_classifier.ingestion.base_pipeline.MLFlowTracker")
    @patch("somali_dialect_classifier.ingestion.base_pipeline.PipelineSetup")
    def test_pipeline_success_flow(self, mock_setup, mock_tracker_cls):
        # Setup mocks
        mock_tracker = mock_tracker_cls.return_value
        mock_setup.sanitize_and_validate_source.return_value = "dummy"
        mock_setup.get_directory_paths.return_value = (
            self.test_dir / "raw",
            self.test_dir / "staging",
            self.test_dir / "processed"
        )
        # Fix: Return injected dependencies
        mock_setup.create_filter_engine.side_effect = lambda x: x
        mock_setup.create_record_builder.side_effect = lambda s, d, r, rb: rb
        mock_setup.create_validation_service.side_effect = lambda x: x
        
        # Initialize pipeline
        pipeline = DummyPipeline(
            source="dummy",
            data_manager=self.mock_data_manager,
            filter_engine=self.mock_filter_engine,
            record_builder=self.mock_record_builder,
            validation_service=self.mock_validation_service
        )
        
        # Mock file existence
        pipeline.staging_file = self.test_dir / "staging.jsonl"
        pipeline.staging_file.touch()
        pipeline.processed_file = self.test_dir / "processed" / "dummy_processed.jsonl"
        
        # Run process
        pipeline.process()
        
        # Assertions
        mock_tracker.start_run.assert_called_once()
        mock_tracker.set_tags.assert_called()
        
        # Verify context tags
        call_args = mock_tracker.set_tags.call_args[0][0]
        self.assertIn("git_commit", call_args)
        self.assertIn("config_hash", call_args)
        self.assertIn("hostname", call_args)
        
        # Verify metrics
        mock_tracker.log_metrics.assert_called()
        metrics = mock_tracker.log_metrics.call_args[0][0]
        self.assertIn("quality_pass_rate", metrics)
        self.assertEqual(metrics["records_processed"], 1)
        
        # Verify success status
        mock_tracker.set_tag.assert_any_call("status", "success")
        mock_tracker.end_run.assert_called_once()

    @patch("somali_dialect_classifier.ingestion.base_pipeline.MLFlowTracker")
    @patch("somali_dialect_classifier.ingestion.base_pipeline.PipelineSetup")
    def test_pipeline_failure_flow(self, mock_setup, mock_tracker_cls):
        # Setup mocks
        mock_tracker = mock_tracker_cls.return_value
        mock_setup.sanitize_and_validate_source.return_value = "dummy"
        mock_setup.get_directory_paths.return_value = (
            self.test_dir / "raw",
            self.test_dir / "staging",
            self.test_dir / "processed"
        )
        # Fix: Return injected dependencies
        mock_setup.create_filter_engine.side_effect = lambda x: x
        mock_setup.create_record_builder.side_effect = lambda s, d, r, rb: rb
        mock_setup.create_validation_service.side_effect = lambda x: x
        
        # Initialize pipeline
        pipeline = DummyPipeline(
            source="dummy",
            data_manager=self.mock_data_manager,
            filter_engine=self.mock_filter_engine,
            record_builder=self.mock_record_builder,
            validation_service=self.mock_validation_service
        )
        
        # Mock file existence
        pipeline.staging_file = self.test_dir / "staging.jsonl"
        pipeline.staging_file.touch()
        pipeline.processed_file = self.test_dir / "processed" / "dummy_processed.jsonl"
        
        # Simulate error during extraction
        pipeline._extract_records = MagicMock(side_effect=RuntimeError("Simulated failure"))
        
        # Run process and expect exception
        with self.assertRaises(RuntimeError):
            pipeline.process()
        
        # Assertions
        mock_tracker.start_run.assert_called_once()
        
        # Verify failure tags
        mock_tracker.set_tags.assert_called()
        # Check specifically for failure tags in one of the calls
        failure_tags_called = False
        for call in mock_tracker.set_tags.call_args_list:
            tags = call[0][0]
            if tags.get("status") == "failed":
                self.assertEqual(tags["error_type"], "RuntimeError")
                self.assertEqual(tags["error_message"], "Simulated failure")
                failure_tags_called = True
        
        self.assertTrue(failure_tags_called, "Failure tags were not set")
        
        # Verify end_run called even after failure
        mock_tracker.end_run.assert_called_once()

if __name__ == "__main__":
    unittest.main()
