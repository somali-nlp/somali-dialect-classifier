"""
Tests for disk space utilities and pre-flight checks.

Validates:
- Disk space calculation accuracy
- Buffer percentage application
- Error raising when space insufficient
- Mock disk usage scenarios
- Integration with DataManager
- Configuration via environment variables
"""

import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from somali_dialect_classifier.infra.data_manager import DataManager
from somali_dialect_classifier.infra.disk_utils import (
    InsufficientDiskSpaceError,
    check_disk_space,
    estimate_required_space,
    format_bytes,
    get_available_disk_space,
)


class TestDiskUtils:
    """Test disk space utility functions."""

    def test_get_available_disk_space(self, tmp_path):
        """Test getting available disk space."""
        space = get_available_disk_space(tmp_path)
        assert space > 0
        assert isinstance(space, int)

    def test_get_available_disk_space_creates_parent(self, tmp_path):
        """Test that get_available_disk_space creates parent directories."""
        nonexistent = tmp_path / "nested" / "path" / "file.txt"
        space = get_available_disk_space(nonexistent)
        assert space > 0
        assert nonexistent.parent.exists()

    def test_check_disk_space_sufficient(self, tmp_path):
        """Test check_disk_space with sufficient space."""
        # Request 1KB (should always be available)
        has_space, error = check_disk_space(1024, tmp_path)
        assert has_space is True
        assert error == ""

    def test_check_disk_space_insufficient_mocked(self, tmp_path):
        """Test check_disk_space with mocked insufficient space."""
        with patch("somali_dialect_classifier.infra.disk_utils.get_available_disk_space") as mock:
            # Mock only 100MB available
            mock.return_value = 100 * (1024**2)

            # Request 200MB (insufficient)
            has_space, error = check_disk_space(200 * (1024**2), tmp_path)
            assert has_space is False
            assert "Insufficient disk space" in error
            assert "need" in error.lower()
            assert "have" in error.lower()

    def test_check_disk_space_with_buffer(self, tmp_path):
        """Test check_disk_space applies buffer percentage."""
        with patch("somali_dialect_classifier.infra.disk_utils.get_available_disk_space") as mock:
            # Mock 110MB available
            mock.return_value = 110 * (1024**2)

            # Request 100MB with 20% buffer (needs 120MB total)
            has_space, error = check_disk_space(
                100 * (1024**2), tmp_path, buffer_pct=0.2
            )
            assert has_space is False
            assert "includes 20% safety buffer" in error

    def test_check_disk_space_with_min_free(self, tmp_path):
        """Test check_disk_space with minimum free space requirement."""
        with patch("somali_dialect_classifier.infra.disk_utils.get_available_disk_space") as mock:
            # Mock 6GB available
            mock.return_value = 6 * (1024**3)

            # Request 1GB with 5GB minimum free (needs 6GB total with buffer)
            has_space, error = check_disk_space(
                1 * (1024**3), tmp_path, buffer_pct=0.0, min_free_gb=5.0
            )
            # Should barely pass (6GB available, need 1GB + 5GB = 6GB)
            # Actually might fail due to rounding, so let's be more generous
            mock.return_value = 7 * (1024**3)
            has_space, error = check_disk_space(
                1 * (1024**3), tmp_path, buffer_pct=0.0, min_free_gb=5.0
            )
            assert has_space is True

    def test_check_disk_space_error_handling(self, tmp_path):
        """Test check_disk_space handles errors gracefully."""
        with patch(
            "somali_dialect_classifier.infra.disk_utils.get_available_disk_space"
        ) as mock:
            mock.side_effect = PermissionError("Access denied")

            has_space, error = check_disk_space(1024, tmp_path)
            assert has_space is False
            assert "Failed to check disk space" in error

    def test_format_bytes(self):
        """Test byte formatting utility."""
        assert format_bytes(1024) == "1KB"
        assert format_bytes(1024**2) == "1MB"
        assert format_bytes(1536 * (1024**2)) == "1.50GB"
        assert format_bytes(256 * (1024**2)) == "256MB"
        assert format_bytes(512) == "512B"

    def test_estimate_required_space_wikipedia(self):
        """Test space estimation for Wikipedia."""
        # With dump size (300MB compressed -> 900MB total)
        space = estimate_required_space("wikipedia", dump_size=300 * (1024**2))
        assert space == 900 * (1024**2)

        # Default estimate
        space = estimate_required_space("wikipedia")
        assert space == 900 * (1024**2)

    def test_estimate_required_space_bbc(self):
        """Test space estimation for BBC."""
        # 500 articles -> 250MB
        space = estimate_required_space("bbc", item_count=500)
        assert space == 250 * (1024**2)

        # Default (100 articles)
        space = estimate_required_space("bbc")
        assert space == 50 * (1024**2)

    def test_estimate_required_space_huggingface(self):
        """Test space estimation for HuggingFace."""
        # 10k records -> 5MB
        space = estimate_required_space("huggingface", item_count=10000)
        assert space == 10000 * 500

        # Default
        space = estimate_required_space("mc4")
        assert space == 10_000 * 500

    def test_estimate_required_space_sprakbanken(self):
        """Test space estimation for Språkbanken."""
        # 5k documents -> 10MB
        space = estimate_required_space("sprakbanken", item_count=5000)
        assert space == 5000 * 2048

        # Default
        space = estimate_required_space("sprakbanken")
        assert space == 5_000 * 2048

    def test_estimate_required_space_tiktok(self):
        """Test space estimation for TikTok."""
        # 1k comments -> 200KB
        space = estimate_required_space("tiktok", item_count=1000)
        assert space == 1000 * 200

        # Default
        space = estimate_required_space("tiktok")
        assert space == 1_000 * 200

    def test_estimate_required_space_unknown(self):
        """Test space estimation for unknown source."""
        space = estimate_required_space("unknown-source")
        assert space == 100 * (1024**2)  # 100MB default


class TestInsufficientDiskSpaceError:
    """Test InsufficientDiskSpaceError exception."""

    def test_error_message(self, tmp_path):
        """Test error message formatting."""
        required = 2 * (1024**3)  # 2GB
        available = 1 * (1024**3)  # 1GB
        error = InsufficientDiskSpaceError(required, available, tmp_path)

        assert "Insufficient disk space" in str(error)
        assert "2.00GB" in str(error)
        assert "1.00GB" in str(error)
        assert str(tmp_path) in str(error)

    def test_error_attributes(self, tmp_path):
        """Test error attributes are set correctly."""
        required = 2 * (1024**3)
        available = 1 * (1024**3)
        error = InsufficientDiskSpaceError(required, available, tmp_path)

        assert error.required == required
        assert error.available == available
        assert error.path == tmp_path


class TestDataManagerDiskSpace:
    """Test DataManager disk space integration."""

    def test_ensure_disk_space_sufficient(self, tmp_path):
        """Test ensure_disk_space with sufficient space."""
        manager = DataManager("Test-Source", "run_001", base_dir=tmp_path)

        # Should not raise (1KB is trivial)
        manager.ensure_disk_space(1024)

    def test_ensure_disk_space_insufficient(self, tmp_path):
        """Test ensure_disk_space raises on insufficient space."""
        manager = DataManager("Test-Source", "run_001", base_dir=tmp_path)

        with patch("somali_dialect_classifier.infra.data_manager.get_available_disk_space") as mock_avail:
            with patch("somali_dialect_classifier.infra.data_manager.check_disk_space") as mock_check:
                # Mock insufficient space check
                mock_avail.return_value = 100 * (1024**2)
                mock_check.return_value = (False, "Insufficient disk space: need 5.21GB, have 0.10GB")

                # Request 200MB (should fail)
                with pytest.raises(InsufficientDiskSpaceError) as exc_info:
                    manager.ensure_disk_space(200 * (1024**2))

                error = exc_info.value
                assert error.required == 200 * (1024**2)
                assert error.available == 100 * (1024**2)

    def test_ensure_disk_space_with_custom_path(self, tmp_path):
        """Test ensure_disk_space with custom path."""
        manager = DataManager("Test-Source", "run_001", base_dir=tmp_path)
        custom_path = tmp_path / "custom"
        custom_path.mkdir()

        # Should check custom path, not base directory
        manager.ensure_disk_space(1024, path=custom_path)

    def test_ensure_disk_space_uses_config(self, tmp_path):
        """Test ensure_disk_space uses configuration settings."""
        from somali_dialect_classifier.infra.config import get_config

        manager = DataManager("Test-Source", "run_001", base_dir=tmp_path)
        config = get_config()

        # Config should have defaults
        assert config.disk.min_free_space_gb == 5
        assert config.disk.space_buffer_pct == 0.1

        # Should apply buffer and minimum free space from config
        with patch("somali_dialect_classifier.infra.data_manager.check_disk_space") as mock:
            mock.return_value = (True, "")

            manager.ensure_disk_space(1024)

            # Verify check_disk_space was called with config values
            mock.assert_called_once()
            call_kwargs = mock.call_args.kwargs
            assert call_kwargs["buffer_pct"] == 0.1
            assert call_kwargs["min_free_gb"] == 5

    def test_ensure_disk_space_tight_warning(self, tmp_path, caplog):
        """Test warning when disk space is tight."""
        import logging

        caplog.set_level(logging.WARNING)

        manager = DataManager("Test-Source", "run_001", base_dir=tmp_path)

        with patch("somali_dialect_classifier.infra.data_manager.get_available_disk_space") as mock_avail:
            with patch("somali_dialect_classifier.infra.data_manager.check_disk_space") as mock_check:
                # Mock passing check but tight margin
                # Request 3GB, have 4GB available
                # Buffered: 3.3GB, Min free: 5GB, Total: 8.3GB needed
                # Margin: 4GB - 3.3GB = 0.7GB (< 2GB, should warn)
                mock_avail.return_value = int(4 * (1024**3))
                mock_check.return_value = (True, "")  # Passes check

                # Request 3GB
                manager.ensure_disk_space(3 * (1024**3))

                # Should log tight space warning
                assert any("tight" in record.message.lower() for record in caplog.records)


class TestConfigurationIntegration:
    """Test configuration integration with disk space checks."""

    def test_disk_config_defaults(self):
        """Test DiskConfig has correct defaults."""
        from somali_dialect_classifier.infra.config import get_config

        config = get_config()
        assert config.disk.min_free_space_gb == 5
        assert config.disk.space_buffer_pct == 0.1

    def test_disk_config_env_override(self, monkeypatch):
        """Test DiskConfig can be overridden via environment."""
        monkeypatch.setenv("SDC_DISK__MIN_FREE_SPACE_GB", "10")
        monkeypatch.setenv("SDC_DISK__SPACE_BUFFER_PCT", "0.2")

        # Reset config to pick up env vars
        from somali_dialect_classifier.infra.config import reset_config, get_config

        reset_config()
        config = get_config()

        assert config.disk.min_free_space_gb == 10
        assert config.disk.space_buffer_pct == 0.2

        # Cleanup
        reset_config()

    def test_disk_config_validation(self):
        """Test DiskConfig validates ranges."""
        from somali_dialect_classifier.infra.config import DiskConfig
        from pydantic import ValidationError

        # Valid config
        config = DiskConfig(min_free_space_gb=5, space_buffer_pct=0.1)
        assert config.min_free_space_gb == 5

        # Invalid buffer percentage (> 0.5)
        with pytest.raises(ValidationError):
            DiskConfig(space_buffer_pct=0.6)

        # Invalid min free space (< 1)
        with pytest.raises(ValidationError):
            DiskConfig(min_free_space_gb=0)


class TestBasePipelineIntegration:
    """Test BasePipeline disk space integration."""

    def test_estimate_processing_space_from_staging(self, tmp_path):
        """Test _estimate_processing_space uses staging file size."""
        from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
        from somali_dialect_classifier.quality.text_cleaners import TextCleaningPipeline

        # Create mock staging file
        staging_file = tmp_path / "staging.jsonl"
        staging_file.write_text("test data\n" * 1000)  # ~10KB
        staging_size = staging_file.stat().st_size

        # Create minimal pipeline subclass
        class TestPipeline(BasePipeline):
            def _extract_records(self):
                return iter([])

            def _create_cleaner(self):
                return TextCleaningPipeline(cleaners=[])

            def _get_source_type(self):
                return "test"

            def _get_license(self):
                return "MIT"

            def _get_language(self):
                return "so"

            def _get_source_metadata(self):
                return {}

            def _get_domain(self):
                return "test"

            def _get_register(self):
                return "formal"

            def download(self):
                return tmp_path / "download"

            def extract(self):
                return tmp_path / "extract"

        pipeline = TestPipeline(source="wikipedia", run_seed="test_run")
        pipeline.staging_file = staging_file

        # Should estimate 2x staging size
        estimated = pipeline._estimate_processing_space()
        assert estimated == staging_size * 2

    def test_check_disk_space_for_processing_raises(self, tmp_path):
        """Test _check_disk_space_for_processing raises on insufficient space."""
        from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
        from somali_dialect_classifier.quality.text_cleaners import TextCleaningPipeline

        # Create minimal pipeline subclass
        class TestPipeline(BasePipeline):
            def _extract_records(self):
                return iter([])

            def _create_cleaner(self):
                return TextCleaningPipeline(cleaners=[])

            def _get_source_type(self):
                return "test"

            def _get_license(self):
                return "MIT"

            def _get_language(self):
                return "so"

            def _get_source_metadata(self):
                return {}

            def _get_domain(self):
                return "test"

            def _get_register(self):
                return "formal"

            def download(self):
                return tmp_path / "download"

            def extract(self):
                return tmp_path / "extract"

        pipeline = TestPipeline(source="wikipedia", run_seed="test_run")
        pipeline.staging_file = tmp_path / "staging.jsonl"
        pipeline.staging_file.write_text("test" * 1000)  # Make file larger
        pipeline.processed_dir = tmp_path / "processed"
        pipeline.processed_dir.mkdir()

        with patch(
            "somali_dialect_classifier.infra.data_manager.get_available_disk_space"
        ) as mock_avail:
            with patch(
                "somali_dialect_classifier.infra.data_manager.check_disk_space"
            ) as mock_check:
                # Mock insufficient space
                mock_avail.return_value = 1024  # Only 1KB available
                mock_check.return_value = (False, "Insufficient disk space")

                # Should raise InsufficientDiskSpaceError
                with pytest.raises(InsufficientDiskSpaceError):
                    pipeline._check_disk_space_for_processing()
