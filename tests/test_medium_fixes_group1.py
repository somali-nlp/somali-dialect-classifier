"""
Tests for MEDIUM priority error handling and validation fixes (M1, M2, M7, M8).

These tests verify the improvements made to:
- M1: BasePipeline._export_stage_metrics() error handling
- M2: FilterEngine.apply_filters() input validation
- M7: FilterEngine strict mode for exception handling
- M8: SilverWriter enhanced error messages
"""

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
from somali_dialect_classifier.quality.filter_engine import FilterEngine
from somali_dialect_classifier.quality.silver_writer import SilverDatasetWriter


# ==============================================================================
# Helper: Minimal Test Pipeline
# ==============================================================================


class MinimalTestPipeline(BasePipeline):
    """Minimal BasePipeline implementation for testing."""

    def download(self):
        return None

    def extract(self):
        return None

    def _extract_records(self):
        yield {"text": "test"}

    def _register_filters(self):
        pass

    def _create_cleaner(self):
        return MagicMock()

    def _get_source_type(self):
        return "wiki"

    def _get_license(self):
        return "CC-BY-SA-3.0"

    def _get_language(self):
        return "so"

    def _get_source_metadata(self):
        return {}

    def _get_domain(self, record):
        return "encyclopedia"

    def _get_register(self, record):
        return "formal"


# ==============================================================================
# M1: BasePipeline._export_stage_metrics() Error Handling
# ==============================================================================


class TestM1MetricsExportErrorHandling:
    """Test M1: Improved error handling in _export_stage_metrics()."""

    def test_metrics_export_attribute_error_debug_logged(self, tmp_path, caplog):
        """Test AttributeError is logged at DEBUG level (test environment)."""
        pipeline = MinimalTestPipeline(
            source="wikipedia",
            force=False
        )

        # Mock metrics with AttributeError on export_json
        pipeline.metrics = Mock()
        pipeline.metrics.export_json.side_effect = AttributeError("test attribute error")

        # Call _export_stage_metrics
        with caplog.at_level(logging.DEBUG):
            pipeline._export_stage_metrics("discovery")

        # Should log at DEBUG level (not WARNING)
        # We verify that an AttributeError doesn't raise WARNING
        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert not any("Failed to export" in msg for msg in warning_messages), \
            "AttributeError should not trigger WARNING log"

    def test_metrics_export_unexpected_error_warning_logged(self, tmp_path, caplog):
        """Test unexpected errors are logged at WARNING level."""
        pipeline = MinimalTestPipeline(
            source="wikipedia",
            force=False
        )

        # Mock metrics with unexpected error
        pipeline.metrics = Mock()
        pipeline.metrics.export_json.side_effect = IOError("Disk full")

        with caplog.at_level(logging.WARNING):
            pipeline._export_stage_metrics("extraction")

        # Should log at WARNING level
        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("Failed to export extraction metrics" in msg for msg in warning_messages)

    def test_metrics_export_failure_tracked_in_metrics(self, tmp_path):
        """Test metric export failures are tracked in metrics counter."""
        pipeline = MinimalTestPipeline(
            source="wikipedia",
            force=False
        )

        # Create real metrics object that can track increment
        from somali_dialect_classifier.infra.metrics import MetricsCollector
        pipeline.metrics = MetricsCollector(run_id="test-run", source="wikipedia")

        # Mock export_json to raise error
        original_increment = pipeline.metrics.increment
        pipeline.metrics.export_json = Mock(side_effect=ValueError("Test error"))

        pipeline._export_stage_metrics("processing")

        # Verify metrics_export_failed was incremented
        assert pipeline.metrics.counters.get("metrics_export_failed", 0) >= 1

    def test_metrics_export_success_info_logged(self, tmp_path, caplog):
        """Test successful export is logged at INFO level."""
        pipeline = MinimalTestPipeline(
            source="wikipedia",
            force=False
        )

        # Mock metrics with successful export
        pipeline.metrics = Mock()
        pipeline.metrics.export_json = Mock()

        with caplog.at_level(logging.INFO):
            pipeline._export_stage_metrics("discovery")

        # Should log success at INFO level
        info_messages = [r.message for r in caplog.records if r.levelname == "INFO"]
        assert any("Exported discovery metrics" in msg for msg in info_messages)


# ==============================================================================
# M2: FilterEngine.apply_filters() Input Validation
# ==============================================================================


class TestM2FilterEngineInputValidation:
    """Test M2: Input validation in FilterEngine.apply_filters()."""

    def test_apply_filters_rejects_none_input(self):
        """Test that None input raises ValueError."""
        engine = FilterEngine()

        with pytest.raises(ValueError, match="cleaned_text must be string, got NoneType"):
            engine.apply_filters(None)

    def test_apply_filters_rejects_integer_input(self):
        """Test that integer input raises ValueError."""
        engine = FilterEngine()

        with pytest.raises(ValueError, match="cleaned_text must be string, got int"):
            engine.apply_filters(123)

    def test_apply_filters_rejects_list_input(self):
        """Test that list input raises ValueError."""
        engine = FilterEngine()

        with pytest.raises(ValueError, match="cleaned_text must be string, got list"):
            engine.apply_filters(["text"])

    def test_apply_filters_rejects_empty_string(self):
        """Test that empty string is rejected early."""
        engine = FilterEngine()

        passed, reason, metadata = engine.apply_filters("")

        assert passed is False
        assert reason == "empty_after_cleaning"
        assert metadata == {}

    def test_apply_filters_rejects_whitespace_only(self):
        """Test that whitespace-only string is rejected."""
        engine = FilterEngine()

        passed, reason, metadata = engine.apply_filters("   \n\t   ")

        assert passed is False
        assert reason == "empty_after_cleaning"
        assert metadata == {}

    def test_apply_filters_accepts_valid_string(self):
        """Test that valid non-empty string is accepted."""
        engine = FilterEngine()

        # Register a simple passing filter
        def always_pass(text, **kwargs):
            return True, {}

        engine.register_filter(always_pass)

        passed, reason, metadata = engine.apply_filters("Valid text content")

        assert passed is True
        assert reason is None

    def test_apply_filters_input_validation_prevents_filter_errors(self):
        """Test that input validation prevents filters from receiving invalid input."""
        engine = FilterEngine()

        # Register filter that would fail on non-string
        def length_filter(text, **kwargs):
            return len(text) > 10, {}

        engine.register_filter(length_filter)

        # This should raise ValueError BEFORE reaching the filter
        with pytest.raises(ValueError, match="cleaned_text must be string"):
            engine.apply_filters(None)


# ==============================================================================
# M7: FilterEngine Strict Mode for Exception Handling
# ==============================================================================


class TestM7FilterEngineStrictMode:
    """Test M7: FilterEngine strict mode for exception handling."""

    def test_strict_mode_disabled_by_default(self):
        """Test that strict_mode defaults to False."""
        engine = FilterEngine()
        assert engine.strict_mode is False

    def test_strict_mode_enabled_via_init(self):
        """Test that strict_mode can be enabled via __init__."""
        engine = FilterEngine(strict_mode=True)
        assert engine.strict_mode is True

    def test_permissive_mode_passes_on_filter_error(self, caplog):
        """Test that permissive mode (default) passes records on filter error."""
        engine = FilterEngine(strict_mode=False)

        # Register filter that raises exception
        def buggy_filter(text, **kwargs):
            raise ValueError("Intentional test error")

        engine.register_filter(buggy_filter)

        with caplog.at_level(logging.WARNING):
            passed, reason, metadata = engine.apply_filters("test text", "test record")

        # Should PASS in permissive mode
        assert passed is True
        assert reason is None

        # Should log warning about pass-through
        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("treated as PASS (permissive mode)" in msg for msg in warning_messages)

    def test_strict_mode_rejects_on_filter_error(self, caplog):
        """Test that strict mode rejects records on filter error."""
        engine = FilterEngine(strict_mode=True)

        # Register filter that raises exception
        def buggy_filter(text, **kwargs):
            raise ValueError("Intentional test error")

        engine.register_filter(buggy_filter)

        with caplog.at_level(logging.ERROR):
            passed, reason, metadata = engine.apply_filters("test text", "test record")

        # Should FAIL in strict mode
        assert passed is False
        assert reason == "buggy_filter_error"

        # Should log error with traceback
        error_messages = [r.message for r in caplog.records if r.levelname == "ERROR"]
        assert any("buggy_filter raised error" in msg for msg in error_messages)

    def test_filter_error_stats_tracked(self):
        """Test that filter errors are tracked in statistics."""
        engine = FilterEngine(strict_mode=False)

        def buggy_filter(text, **kwargs):
            raise RuntimeError("Test error")

        engine.register_filter(buggy_filter)

        # Apply filter multiple times
        for _ in range(3):
            engine.apply_filters("test text")

        # Check that error count is tracked
        stats = engine.get_filter_stats()
        assert stats.get("filter_error_buggy_filter", 0) == 3

    def test_filter_error_includes_full_traceback(self, caplog):
        """Test that filter errors log full traceback for debugging."""
        engine = FilterEngine()

        def buggy_filter(text, **kwargs):
            raise ValueError("Detailed error message")

        engine.register_filter(buggy_filter)

        with caplog.at_level(logging.ERROR):
            engine.apply_filters("test text", "test record")

        # Should have error record with exc_info
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_records) > 0
        assert error_records[0].exc_info is not None

    def test_multiple_filters_with_strict_mode(self):
        """Test that strict mode stops on first filter error."""
        engine = FilterEngine(strict_mode=True)

        call_count = {"filter1": 0, "filter2": 0}

        def buggy_filter1(text, **kwargs):
            call_count["filter1"] += 1
            raise ValueError("Error in filter 1")

        def normal_filter2(text, **kwargs):
            call_count["filter2"] += 1
            return True, {}

        engine.register_filter(buggy_filter1)
        engine.register_filter(normal_filter2)

        passed, reason, metadata = engine.apply_filters("test text")

        # Should fail on first filter
        assert passed is False
        assert reason == "buggy_filter1_error"

        # First filter should have been called
        assert call_count["filter1"] == 1

        # Second filter should NOT have been called (stopped early)
        assert call_count["filter2"] == 0


# ==============================================================================
# M8: SilverWriter Enhanced Error Messages
# ==============================================================================


class TestM8SilverWriterEnhancedErrors:
    """Test M8: Enhanced error messages in SilverDatasetWriter validation."""

    def test_invalid_domain_error_includes_source(self, tmp_path):
        """Test that invalid domain error includes source context."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        records = [
            {
                "id": "test-id-123",
                "text": "Test content",
                "title": "Test Title",
                "url": "https://so.wikipedia.org/wiki/Test",
                "source": "Wikipedia-Somali",
                "run_id": "run-abc123",
                "source_type": "wiki",
                "language": "so",
                "license": "CC-BY-SA-3.0",
                "tokens": 10,
                "text_hash": "abc123",
                "pipeline_version": "1.0.0",
                "source_metadata": "{}",
                "domain": "invalid_domain",  # INVALID
                "register": "formal",
                "date_accessed": "2025-12-30",
            }
        ]

        with pytest.raises(ValueError) as exc_info:
            writer.write(
                records=records,
                source="Wikipedia-Somali",
                date_accessed="2025-12-30",
                run_id="run-abc123"
            )

        error_msg = str(exc_info.value)

        # Should include source
        assert "Wikipedia-Somali" in error_msg

        # Should include run_id
        assert "run-abc123" in error_msg

        # Should include record ID
        assert "test-id-123" in error_msg

        # Should include invalid domain
        assert "invalid_domain" in error_msg

        # Should include guidance
        assert "Check processor's _get_domain() method" in error_msg

    def test_invalid_register_error_includes_source(self, tmp_path):
        """Test that invalid register error includes source context."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        records = [
            {
                "id": "test-id-456",
                "text": "Test content",
                "title": "Test Title",
                "url": "https://www.bbc.com/somali/test",
                "source": "BBC-Somali",
                "run_id": "run-xyz789",
                "source_type": "news",
                "language": "so",
                "license": "BBC-TOS",
                "tokens": 10,
                "text_hash": "def456",
                "pipeline_version": "1.0.0",
                "source_metadata": "{}",
                "domain": "news",
                "register": "invalid_register",  # INVALID
                "date_accessed": "2025-12-30",
            }
        ]

        with pytest.raises(ValueError) as exc_info:
            writer.write(
                records=records,
                source="BBC-Somali",
                date_accessed="2025-12-30",
                run_id="run-xyz789"
            )

        error_msg = str(exc_info.value)

        # Should include source
        assert "BBC-Somali" in error_msg

        # Should include run_id
        assert "run-xyz789" in error_msg

        # Should include record ID
        assert "test-id-456" in error_msg

        # Should include invalid register
        assert "invalid_register" in error_msg

        # Should include guidance
        assert "Check processor's _get_register() method" in error_msg

    def test_error_message_with_missing_source_fields(self, tmp_path):
        """Test that error message gracefully handles missing source/run_id fields."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        # Record missing source and run_id (but has all other required fields)
        records = [
            {
                "id": "test-id-789",
                "text": "Test content",
                "title": "Test Title",
                "url": "https://example.com",
                # Missing "source" and "run_id" - will be extracted as "unknown"
                "source_type": "unknown",
                "language": "so",
                "license": "Unknown",
                "tokens": 10,
                "text_hash": "abc123",
                "pipeline_version": "1.0.0",
                "source_metadata": "{}",
                "domain": "invalid_domain",  # Invalid to trigger error
                "register": "formal",
                "date_accessed": "2025-12-30",
            }
        ]

        # This will fail on missing required fields first
        with pytest.raises(ValueError) as exc_info:
            writer.write(
                records=records,
                source="Unknown-Source",
                date_accessed="2025-12-30",
                run_id="unknown-run"
            )

        error_msg = str(exc_info.value)

        # Should mention missing required fields (source and run_id)
        assert "missing required fields" in error_msg.lower()

    def test_valid_records_pass_without_error(self, tmp_path):
        """Test that valid records with proper source/run_id pass validation."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        records = [
            {
                "id": "valid-id-1",
                "text": "Valid test content",
                "title": "Valid Title",
                "url": "https://so.wikipedia.org/wiki/Test",
                "source": "Wikipedia-Somali",
                "run_id": "run-valid-123",
                "source_type": "wiki",
                "language": "so",
                "license": "CC-BY-SA-3.0",
                "tokens": 15,
                "text_hash": "abc123def456",
                "pipeline_version": "1.0.0",
                "source_metadata": "{}",
                "domain": "encyclopedia",
                "register": "formal",
                "date_accessed": "2025-12-30",
            }
        ]

        # Should not raise any errors
        result_path = writer.write(
            records=records,
            source="Wikipedia-Somali",
            date_accessed="2025-12-30",
            run_id="run-valid-123"
        )

        assert result_path is not None
        assert result_path.exists()


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestMediumFixesIntegration:
    """Integration tests verifying all fixes work together."""

    def test_pipeline_with_strict_filter_engine(self, tmp_path):
        """Test pipeline integration with strict mode FilterEngine."""

        class StrictTestPipeline(MinimalTestPipeline):
            def _extract_records(self):
                yield {"text": "valid text content", "title": "Test"}

            def _register_filters(self):
                # Use strict mode for testing
                self.filter_engine = FilterEngine(strict_mode=True)

                def buggy_filter(text, **kwargs):
                    if "error" in text:
                        raise ValueError("Intentional error")
                    return True, {}

                self.filter_engine.register_filter(buggy_filter)

            def _create_cleaner(self):
                return MagicMock(clean=lambda x: x)

        pipeline = StrictTestPipeline(
            source="wikipedia",
            force=True
        )

        # This should work (no "error" in text)
        # Note: This test verifies integration, not full pipeline run
        assert pipeline.filter_engine.strict_mode is True

    def test_enhanced_error_debugging_flow(self, tmp_path, caplog):
        """Test complete error debugging flow with all fixes."""
        writer = SilverDatasetWriter(base_dir=tmp_path)

        # Create record with invalid domain from specific processor
        invalid_record = {
            "id": "debug-test-1",
            "text": "Test",
            "title": "Test",
            "url": "https://huggingface.co/test",
            "source": "HuggingFace-MC4",
            "run_id": "run-debug-001",
            "source_type": "corpus",
            "language": "so",
            "license": "CC0",
            "tokens": 5,
            "text_hash": "xyz789",
            "pipeline_version": "1.0.0",
            "source_metadata": "{}",
            "domain": "wrong_domain",  # Invalid
            "register": "formal",
            "date_accessed": "2025-12-30",
        }

        with pytest.raises(ValueError) as exc_info:
            writer.write(
                records=[invalid_record],
                source="HuggingFace-MC4",
                date_accessed="2025-12-30",
                run_id="run-debug-001"
            )

        # Error message should give clear debugging path
        error_msg = str(exc_info.value)
        assert "HuggingFace-MC4" in error_msg  # Know which processor
        assert "run-debug-001" in error_msg    # Know which run
        assert "debug-test-1" in error_msg     # Know which record
        assert "_get_domain()" in error_msg    # Know which method to fix
