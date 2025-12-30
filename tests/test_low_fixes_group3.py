"""
Tests for LOW priority fixes Group 3: L7 (Configuration Logging) and L8 (ISO Date Validation).

L7: Configuration logging at pipeline startup with secret redaction
L8: ISO date format validation for ledger methods

Test Coverage:
- Configuration logging works and secrets are redacted
- ISO date validation accepts valid dates
- ISO date validation rejects invalid dates
- All ledger methods validate date parameters
"""

import json
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from somali_dialect_classifier.infra.logging_utils import validate_iso_date
from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger, SQLiteLedger


class TestIsoDateValidation:
    """Test ISO date format validation (L8)."""

    def test_valid_iso_date_format(self):
        """Test that valid ISO date formats are accepted."""
        # Valid dates
        valid_dates = [
            "2025-12-30",
            "2025-01-01",
            "2024-02-29",  # Leap year
            "2023-12-31",
        ]

        for date_str in valid_dates:
            result = validate_iso_date(date_str)
            assert result == date_str, f"Expected {date_str}, got {result}"

    def test_invalid_iso_date_format_raises_error(self):
        """Test that invalid ISO date formats raise ValueError."""
        # Invalid dates
        invalid_dates = [
            ("2025-13-01", "Invalid month"),
            ("2025-12-32", "Invalid day"),
            ("2023-02-29", "Not a leap year"),
            ("not-a-date", "Completely invalid"),
            ("2025/12/30", "Wrong separator"),
            ("30-12-2025", "Wrong order"),
            ("", "Empty string"),
            # Note: "2025-1-1" (missing leading zeros) is accepted by datetime.strptime
        ]

        for date_str, description in invalid_dates:
            with pytest.raises(ValueError, match="Invalid ISO date format"):
                validate_iso_date(date_str), f"Failed for {description}: {date_str}"

    def test_iso_date_validation_error_message(self):
        """Test that error messages contain the invalid date string."""
        invalid_date = "2025-13-45"

        with pytest.raises(ValueError) as exc_info:
            validate_iso_date(invalid_date)

        error_msg = str(exc_info.value)
        assert "2025-13-45" in error_msg
        assert "Invalid ISO date format" in error_msg


class TestLedgerDateValidation:
    """Test ISO date validation in ledger methods (L8)."""

    @pytest.fixture
    def ledger(self):
        """Create temporary SQLite ledger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_ledger.db"
            backend = SQLiteLedger(db_path)
            ledger = CrawlLedger(backend=backend)
            yield ledger
            ledger.close()

    def test_get_daily_quota_usage_valid_date(self, ledger):
        """Test get_daily_quota_usage accepts valid ISO date."""
        # Should not raise an error
        usage = ledger.get_daily_quota_usage("bbc", date="2025-12-30")

        assert usage["date"] == "2025-12-30"
        assert usage["source"] == "bbc"
        assert usage["records_ingested"] == 0

    def test_get_daily_quota_usage_invalid_date(self, ledger):
        """Test get_daily_quota_usage rejects invalid ISO date."""
        with pytest.raises(ValueError, match="Invalid ISO date format"):
            ledger.get_daily_quota_usage("bbc", date="2025-13-01")

    def test_get_daily_quota_usage_none_date_uses_today(self, ledger):
        """Test get_daily_quota_usage uses today when date is None."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        usage = ledger.get_daily_quota_usage("bbc", date=None)

        assert usage["date"] == today

    def test_increment_daily_quota_valid_date(self, ledger):
        """Test increment_daily_quota accepts valid ISO date."""
        usage = ledger.increment_daily_quota(
            "bbc", count=10, quota_limit=350, date="2025-12-30"
        )

        assert usage["date"] == "2025-12-30"
        assert usage["records_ingested"] == 10
        assert usage["quota_limit"] == 350

    def test_increment_daily_quota_invalid_date(self, ledger):
        """Test increment_daily_quota rejects invalid ISO date."""
        with pytest.raises(ValueError, match="Invalid ISO date format"):
            ledger.increment_daily_quota("bbc", count=10, date="not-a-date")

    def test_mark_quota_hit_valid_date(self, ledger):
        """Test mark_quota_hit accepts valid ISO date."""
        # First increment to create record
        ledger.increment_daily_quota("bbc", count=350, quota_limit=350, date="2025-12-30")

        # Then mark quota hit
        ledger.mark_quota_hit("bbc", items_remaining=100, quota_limit=350, date="2025-12-30")

        # Verify quota hit was recorded
        usage = ledger.get_daily_quota_usage("bbc", date="2025-12-30")
        assert usage["quota_hit"] is True
        assert usage["items_remaining"] == 100

    def test_mark_quota_hit_invalid_date(self, ledger):
        """Test mark_quota_hit rejects invalid ISO date."""
        with pytest.raises(ValueError, match="Invalid ISO date format"):
            ledger.mark_quota_hit("bbc", items_remaining=100, quota_limit=350, date="2025/12/30")

    def test_check_quota_available_valid_date(self, ledger):
        """Test check_quota_available accepts valid ISO date."""
        # Use quota
        ledger.increment_daily_quota("bbc", count=200, quota_limit=350, date="2025-12-30")

        # Check availability
        has_quota, remaining = ledger.check_quota_available(
            "bbc", quota_limit=350, date="2025-12-30"
        )

        assert has_quota is True
        assert remaining == 150

    def test_check_quota_available_invalid_date(self, ledger):
        """Test check_quota_available rejects invalid ISO date."""
        with pytest.raises(ValueError, match="Invalid ISO date format"):
            ledger.check_quota_available("bbc", quota_limit=350, date="30-12-2025")


class TestConfigurationLogging:
    """Test configuration logging at pipeline startup (L7)."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        mock_cfg = MagicMock()

        # Data directories
        mock_cfg.data.raw_dir = Path("data/raw")
        mock_cfg.data.staging_dir = Path("data/staging")
        mock_cfg.data.processed_dir = Path("data/processed")
        mock_cfg.data.silver_dir = Path("data/processed/silver")
        mock_cfg.data.metrics_dir = Path("data/metrics")
        mock_cfg.data.reports_dir = Path("data/reports")

        # Scraping configuration
        mock_cfg.scraping.bbc.max_articles = 100
        mock_cfg.scraping.bbc.min_delay = 1.0
        mock_cfg.scraping.bbc.max_delay = 3.0
        mock_cfg.scraping.bbc.timeout = 30

        mock_cfg.scraping.wikipedia.batch_size = 100
        mock_cfg.scraping.wikipedia.max_articles = None
        mock_cfg.scraping.wikipedia.timeout = 30

        mock_cfg.scraping.huggingface.streaming_batch_size = 5000
        mock_cfg.scraping.huggingface.max_records = None
        mock_cfg.scraping.huggingface.min_length_threshold = 100

        mock_cfg.scraping.sprakbanken.batch_size = 5000
        mock_cfg.scraping.sprakbanken.max_corpora = None
        mock_cfg.scraping.sprakbanken.timeout = 30

        mock_cfg.scraping.tiktok.apify_api_token = "sk_live_secret_token_12345678"
        mock_cfg.scraping.tiktok.max_comments_per_video = 1000

        # Database configuration
        mock_cfg.database.query_timeout = 30
        mock_cfg.database.min_connections = 2
        mock_cfg.database.max_connections = 10
        # Password should NOT be logged

        # Logging configuration
        mock_cfg.logging.level = "INFO"
        mock_cfg.logging.format = "json"

        return mock_cfg

    def test_configuration_logging_at_startup(self, mock_config, caplog):
        """Test that configuration is logged when pipeline is initialized."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=mock_config):
            with caplog.at_level(logging.INFO):
                # Initialize pipeline (should trigger config logging)
                processor = WikipediaSomaliProcessor(force=True)

                # Verify configuration logging occurred
                log_messages = [record.message for record in caplog.records]

                # Check for configuration header
                assert any("Pipeline Configuration:" in msg for msg in log_messages), \
                    "Configuration header not found in logs"

                # Check for JSON configuration
                config_logs = [msg for msg in log_messages if msg.startswith("{")]
                assert len(config_logs) > 0, "No JSON configuration found in logs"

    def test_secrets_are_redacted_in_logs(self, mock_config, caplog):
        """Test that secrets (API tokens, passwords) are redacted in logged configuration."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=mock_config):
            with caplog.at_level(logging.INFO):
                # Initialize pipeline
                processor = WikipediaSomaliProcessor(force=True)

                # Get all log messages
                all_logs = "\n".join([record.message for record in caplog.records])

                # Verify API token is redacted (should show last 4 chars only)
                assert "sk_live_secret_token_12345678" not in all_logs, \
                    "Unredacted API token found in logs!"

                # Verify redaction occurred (should see *** prefix)
                assert "***" in all_logs, "No redaction markers found in logs"

    def test_configuration_includes_data_directories(self, mock_config, caplog):
        """Test that logged configuration includes data directory paths."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=mock_config):
            with caplog.at_level(logging.INFO):
                processor = WikipediaSomaliProcessor(force=True)

                all_logs = "\n".join([record.message for record in caplog.records])

                # Find JSON configuration in logs
                json_matches = re.findall(r'\{.*"data_dirs".*\}', all_logs, re.DOTALL)
                assert len(json_matches) > 0, "No JSON configuration with data_dirs found"

                # Parse and verify
                config_json = json_matches[0]
                config_data = json.loads(config_json)

                assert "data_dirs" in config_data
                assert "raw" in config_data["data_dirs"]
                assert "staging" in config_data["data_dirs"]
                assert "processed" in config_data["data_dirs"]

    def test_configuration_includes_scraping_settings(self, mock_config, caplog):
        """Test that logged configuration includes scraping settings."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=mock_config):
            with caplog.at_level(logging.INFO):
                processor = WikipediaSomaliProcessor(force=True)

                all_logs = "\n".join([record.message for record in caplog.records])

                # Find JSON configuration
                json_matches = re.findall(r'\{.*"scraping".*\}', all_logs, re.DOTALL)
                assert len(json_matches) > 0

                config_json = json_matches[0]
                config_data = json.loads(config_json)

                assert "scraping" in config_data
                assert "bbc" in config_data["scraping"]
                assert "wikipedia" in config_data["scraping"]

    def test_configuration_includes_database_settings_without_password(self, mock_config, caplog):
        """Test that database config is logged but password is excluded."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=mock_config):
            with caplog.at_level(logging.INFO):
                processor = WikipediaSomaliProcessor(force=True)

                all_logs = "\n".join([record.message for record in caplog.records])

                # Find JSON configuration
                json_matches = re.findall(r'\{.*"database".*\}', all_logs, re.DOTALL)
                assert len(json_matches) > 0

                config_json = json_matches[0]
                config_data = json.loads(config_json)

                # Verify database config is present
                assert "database" in config_data
                assert config_data["database"]["query_timeout"] == 30
                assert config_data["database"]["min_connections"] == 2
                assert config_data["database"]["max_connections"] == 10

                # Verify password is NOT in config (should not be in dict at all)
                assert "password" not in config_data["database"], \
                    "Password should not be included in logged configuration!"

    def test_configuration_logging_failure_does_not_break_pipeline(self, mock_config):
        """Test that pipeline initialization succeeds even if config logging fails."""
        from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        # Create a mock that fails when trying to access logging configuration
        # but works for other accesses
        bad_config = MagicMock()
        bad_config.data = mock_config.data
        bad_config.scraping = mock_config.scraping
        bad_config.database = mock_config.database

        # Make logging attribute raise an exception
        bad_config.logging = MagicMock(side_effect=Exception("Logging config error"))

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=bad_config):
            # Pipeline should still initialize successfully
            # _log_configuration catches the exception and logs a warning
            processor = WikipediaSomaliProcessor(force=True)

            # Verify the processor was created successfully
            assert processor is not None
            assert processor.source == "wikipedia-somali"

    def test_pipeline_specific_settings_logged(self, mock_config, caplog):
        """Test that pipeline-specific settings (run_id, source, etc.) are logged."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        with patch("somali_dialect_classifier.ingestion.base_pipeline.get_config", return_value=mock_config):
            with caplog.at_level(logging.INFO):
                processor = WikipediaSomaliProcessor(force=True)

                all_logs = "\n".join([record.message for record in caplog.records])

                # Find JSON configuration
                json_matches = re.findall(r'\{.*"pipeline".*\}', all_logs, re.DOTALL)
                assert len(json_matches) > 0

                config_json = json_matches[0]
                config_data = json.loads(config_json)

                # Verify pipeline-specific settings
                assert "pipeline" in config_data
                assert config_data["pipeline"]["source"] == "wikipedia-somali"
                assert config_data["pipeline"]["force"] is True
                assert "batch_size" in config_data["pipeline"]  # batch_size can be None
                assert "run_id" in config_data["pipeline"]
                assert "date_accessed" in config_data["pipeline"]
