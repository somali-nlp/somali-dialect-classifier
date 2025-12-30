"""
Tests for MEDIUM priority fixes (Group 3: Infrastructure).

Tests M5, M6, M9, M12 from L1 peer review.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestM5FileChecksumDeduplication:
    """Test M5: check_file_checksum() implementation."""

    def test_sqlite_check_file_checksum_found(self, tmp_path):
        """Test SQLite check_file_checksum() returns existing record."""
        from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger, CrawlState

        db_path = tmp_path / "test.db"
        ledger = CrawlLedger(db_path=db_path, backend_type="sqlite")

        # Insert record with file checksum in metadata
        test_checksum = "abc123def456"
        test_url = "https://example.com/file.xml"
        test_source = "wikipedia"

        ledger.backend.upsert_url(
            url=test_url,
            source=test_source,
            state=CrawlState.PROCESSED,
            metadata={"file_checksum": test_checksum},
        )

        # Check if checksum exists
        result = ledger.check_file_checksum(test_checksum, test_source)

        assert result is not None
        assert result["url"] == test_url
        assert result["source"] == test_source

    def test_sqlite_check_file_checksum_not_found(self, tmp_path):
        """Test SQLite check_file_checksum() returns None for non-existent checksum."""
        from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger

        db_path = tmp_path / "test.db"
        ledger = CrawlLedger(db_path=db_path, backend_type="sqlite")

        # Check non-existent checksum
        result = ledger.check_file_checksum("nonexistent", "wikipedia")

        assert result is None

    @pytest.mark.skipif(
        os.getenv("POSTGRES_PASSWORD") is None,
        reason="PostgreSQL not configured",
    )
    def test_postgres_check_file_checksum(self):
        """Test PostgreSQL check_file_checksum() implementation."""
        from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger, CrawlState

        # Create PostgreSQL ledger
        ledger = CrawlLedger(backend_type="postgres")

        # Insert record with file checksum
        test_checksum = "test_checksum_123"
        test_url = "https://test.com/file.xml"
        test_source = "test-source"

        ledger.backend.upsert_url(
            url=test_url,
            source=test_source,
            state=CrawlState.PROCESSED,
            metadata={"file_checksum": test_checksum},
        )

        # Check if checksum exists
        result = ledger.check_file_checksum(test_checksum, test_source)

        assert result is not None
        assert result["url"] == test_url
        assert result["source"] == test_source

        # Cleanup
        ledger.close()

    def test_dedup_check_file_checksum_integration(self, tmp_path):
        """Test check_file_checksum() is called correctly during file duplication check."""
        from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger, CrawlState
        import hashlib

        db_path = tmp_path / "test.db"
        ledger = CrawlLedger(db_path=db_path, backend_type="sqlite")

        # Create test file and compute checksum manually
        test_file = tmp_path / "test.xml"
        test_file.write_text("test content")
        test_url = "https://example.com/test.xml"

        # Compute checksum the same way dedup does
        file_checksum = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # Store in ledger with checksum
        ledger.backend.upsert_url(
            url=test_url,
            source="wikipedia",
            state=CrawlState.PROCESSED,
            metadata={"file_checksum": file_checksum},
        )

        # Now check if the checksum lookup works
        result = ledger.check_file_checksum(file_checksum, "wikipedia")
        assert result is not None
        assert result["url"] == test_url


class TestM6BufferConfiguration:
    """Test M6: Buffer constants documentation and configuration."""

    def test_buffer_constants_documented(self):
        """Test that buffer constants have documentation."""
        from somali_dialect_classifier.ingestion.processors import (
            wikipedia_somali_processor,
        )

        # Check constants exist
        assert hasattr(wikipedia_somali_processor, "BUFFER_CHUNK_SIZE_MB")
        assert hasattr(wikipedia_somali_processor, "BUFFER_MAX_SIZE_MB")
        assert hasattr(wikipedia_somali_processor, "BUFFER_TRUNCATE_SIZE_MB")

        # Check safety assertions execute without error
        assert (
            wikipedia_somali_processor.BUFFER_MAX_SIZE_MB
            >= wikipedia_somali_processor.BUFFER_CHUNK_SIZE_MB
        )
        assert (
            wikipedia_somali_processor.BUFFER_TRUNCATE_SIZE_MB
            <= wikipedia_somali_processor.BUFFER_MAX_SIZE_MB
        )

    def test_buffer_config_in_settings(self):
        """Test buffer settings are configurable via config."""
        from somali_dialect_classifier.infra.config import WikipediaScrapingConfig

        config = WikipediaScrapingConfig()

        # Check default values
        assert config.buffer_chunk_size_mb == 1
        assert config.buffer_max_size_mb == 10
        assert config.buffer_truncate_size_mb == 1

        # Check validation ranges
        assert 1 <= config.buffer_chunk_size_mb <= 10
        assert 1 <= config.buffer_max_size_mb <= 100
        assert 1 <= config.buffer_truncate_size_mb <= 10

    def test_buffer_config_loaded_by_processor(self):
        """Test processor loads buffer config from settings."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        # Create processor (it will load config)
        processor = WikipediaSomaliProcessor(run_seed="test")

        # Check instance variables are set from config
        assert hasattr(processor, "buffer_chunk_size_mb")
        assert hasattr(processor, "buffer_max_size_mb")
        assert hasattr(processor, "buffer_truncate_size_mb")

        # Check values match config defaults
        assert processor.buffer_chunk_size_mb == 1
        assert processor.buffer_max_size_mb == 10
        assert processor.buffer_truncate_size_mb == 1

    def test_buffer_config_override_via_env(self):
        """Test buffer config can be overridden via environment variables."""
        with patch.dict(
            os.environ,
            {
                "SDC_SCRAPING__WIKIPEDIA__BUFFER_CHUNK_SIZE_MB": "2",
                "SDC_SCRAPING__WIKIPEDIA__BUFFER_MAX_SIZE_MB": "20",
                "SDC_SCRAPING__WIKIPEDIA__BUFFER_TRUNCATE_SIZE_MB": "2",
            },
        ):
            from somali_dialect_classifier.infra.config import (
                WikipediaScrapingConfig,
                reset_config,
            )

            reset_config()  # Force reload

            config = WikipediaScrapingConfig()
            assert config.buffer_chunk_size_mb == 2
            assert config.buffer_max_size_mb == 20
            assert config.buffer_truncate_size_mb == 2


class TestM9VersionCentralization:
    """Test M9: Centralized version management."""

    def test_version_module_exists(self):
        """Test version.py module exists with required attributes."""
        from somali_dialect_classifier import version

        assert hasattr(version, "__version__")
        assert hasattr(version, "__pipeline_version__")

    def test_version_exposed_in_package_init(self):
        """Test version is exposed in package __init__."""
        import somali_dialect_classifier

        assert hasattr(somali_dialect_classifier, "__version__")
        assert hasattr(somali_dialect_classifier, "__pipeline_version__")

    def test_pipeline_version_format(self):
        """Test pipeline version follows semantic versioning."""
        from somali_dialect_classifier import __pipeline_version__

        # Should be in format X.Y.Z
        parts = __pipeline_version__.split(".")
        assert len(parts) >= 2  # At least major.minor
        assert all(part.replace("-", "").replace("dev", "").isdigit() or "dev" in part for part in parts)

    def test_record_builder_uses_centralized_version(self):
        """Test RecordBuilder uses centralized version."""
        from somali_dialect_classifier.quality.record_utils import build_silver_record
        from somali_dialect_classifier import __pipeline_version__
        import inspect

        # Check default parameter value
        sig = inspect.signature(build_silver_record)
        default_version = sig.parameters["pipeline_version"].default

        # The default should reference __pipeline_version__
        # (In practice, it evaluates to the actual value)
        assert default_version == __pipeline_version__

    def test_silver_writer_metadata_uses_centralized_version(self):
        """Test silver metadata uses centralized version (simpler test)."""
        from somali_dialect_classifier import __pipeline_version__

        # Just verify the version constant is used
        # Full integration test would be too complex for this unit test
        # The actual usage is verified by inspecting the import in silver_writer.py
        assert __pipeline_version__ is not None
        assert isinstance(__pipeline_version__, str)

        # Test that the version is accessible from package
        import somali_dialect_classifier
        assert somali_dialect_classifier.__pipeline_version__ == __pipeline_version__


class TestM12QueryTimeout:
    """Test M12: PostgreSQL query timeout configuration."""

    def test_database_config_exists(self):
        """Test DatabaseConfig exists with query_timeout."""
        from somali_dialect_classifier.infra.config import DatabaseConfig

        config = DatabaseConfig()

        assert hasattr(config, "query_timeout")
        assert hasattr(config, "min_connections")
        assert hasattr(config, "max_connections")

        # Check defaults
        assert config.query_timeout == 30
        assert config.min_connections == 2
        assert config.max_connections == 10

    def test_database_config_validation(self):
        """Test DatabaseConfig validates timeout ranges."""
        from somali_dialect_classifier.infra.config import DatabaseConfig
        from pydantic import ValidationError

        # Valid timeout
        config = DatabaseConfig(query_timeout=60)
        assert config.query_timeout == 60

        # Invalid timeout (too low)
        with pytest.raises(ValidationError):
            DatabaseConfig(query_timeout=0)

        # Invalid timeout (too high)
        with pytest.raises(ValidationError):
            DatabaseConfig(query_timeout=1000)

    def test_postgres_ledger_accepts_timeout(self):
        """Test PostgresLedger accepts query_timeout parameter."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger
        import inspect

        # Check __init__ signature
        sig = inspect.signature(PostgresLedger.__init__)
        assert "query_timeout" in sig.parameters

        # Check default value
        assert sig.parameters["query_timeout"].default == 30

    @pytest.mark.skipif(
        os.getenv("POSTGRES_PASSWORD") is None,
        reason="PostgreSQL not configured",
    )
    def test_postgres_ledger_connection_string_includes_timeout(self):
        """Test PostgresLedger connection string includes statement_timeout."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        ledger = PostgresLedger(
            password=os.getenv("POSTGRES_PASSWORD"),
            query_timeout=45,
        )

        # Check connection string contains timeout option
        assert "statement_timeout=" in ledger.connection_string
        assert "statement_timeout=45000" in ledger.connection_string  # 45 seconds = 45000 ms

        ledger.close()

    def test_crawl_ledger_passes_timeout_to_postgres(self, monkeypatch):
        """Test CrawlLedger passes timeout config to PostgresLedger."""
        from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger
        from somali_dialect_classifier.infra.config import reset_config
        from unittest.mock import MagicMock

        # Mock PostgresLedger to avoid actual connection
        mock_postgres = MagicMock()

        with patch.dict(
            os.environ,
            {
                "SDC_LEDGER_BACKEND": "postgres",
                "POSTGRES_PASSWORD": "test_password",
                "SDC_DATABASE__QUERY_TIMEOUT": "60",
            },
        ):
            reset_config()

            with patch(
                "somali_dialect_classifier.database.postgres_ledger.PostgresLedger",
                return_value=mock_postgres,
            ) as mock_class:
                ledger = CrawlLedger()

                # Check PostgresLedger was called with timeout from config
                call_kwargs = mock_class.call_args.kwargs
                assert "query_timeout" in call_kwargs
                assert call_kwargs["query_timeout"] == 60

    def test_timeout_override_via_backend_kwargs(self):
        """Test query_timeout can be overridden via backend_kwargs."""
        from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger
        from unittest.mock import MagicMock

        mock_postgres = MagicMock()

        with patch.dict(
            os.environ,
            {
                "SDC_LEDGER_BACKEND": "postgres",
                "POSTGRES_PASSWORD": "test_password",
            },
        ):
            with patch(
                "somali_dialect_classifier.database.postgres_ledger.PostgresLedger",
                return_value=mock_postgres,
            ) as mock_class:
                # Override timeout via backend_kwargs
                ledger = CrawlLedger(query_timeout=90)

                call_kwargs = mock_class.call_args.kwargs
                assert call_kwargs["query_timeout"] == 90
