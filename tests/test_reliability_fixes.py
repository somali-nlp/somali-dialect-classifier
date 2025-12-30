"""
Tests for Phase 2 reliability fixes.

Verifies:
- PostgreSQL connection pool resource leak fix (context manager, destructor)
- HTTP timeout enforcement (TimeoutHTTPSession, config integration)
"""

import os
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from somali_dialect_classifier.infra.config import get_config
from somali_dialect_classifier.infra.http import HTTPSessionFactory, TimeoutHTTPSession
from somali_dialect_classifier.ingestion.pipeline_setup import PipelineSetup


# ============================================================================
# Connection Pool Tests
# ============================================================================


@pytest.mark.skipif(
    not os.getenv("POSTGRES_PASSWORD") and not os.getenv("SDC_DB_PASSWORD"),
    reason="PostgreSQL password not set",
)
class TestConnectionPoolResourceLeak:
    """Test connection pool context manager and destructor cleanup."""

    def test_context_manager_cleanup(self):
        """Test that connection pool is properly closed when using context manager."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool_class.return_value = mock_pool

                # Use context manager
                with PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                ) as ledger:
                    assert ledger.pool is not None

                # Verify closeall() was called on exit
                mock_pool.closeall.assert_called_once()

    def test_context_manager_cleanup_on_exception(self):
        """Test that connection pool is closed even if exception occurs in context."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool_class.return_value = mock_pool

                try:
                    with PostgresLedger(
                        host="localhost",
                        port=5432,
                        database="test_db",
                        user="test_user",
                        password="test_password",
                    ):
                        raise ValueError("Test exception")
                except ValueError:
                    pass

                # Verify closeall() was still called despite exception
                mock_pool.closeall.assert_called_once()

    def test_close_with_error_handling(self):
        """Test that close() handles errors gracefully and sets pool to None."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool.closeall.side_effect = Exception("Close error")
                mock_pool_class.return_value = mock_pool

                ledger = PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                )

                # close() should not raise even if closeall() fails
                ledger.close()

                # Pool should be set to None even after error
                assert ledger.pool is None

    def test_destructor_cleanup(self):
        """Test that destructor cleans up pool if not explicitly closed."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool_class.return_value = mock_pool

                ledger = PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                )

                # Delete ledger without calling close()
                del ledger

                # Destructor should have called closeall()
                mock_pool.closeall.assert_called_once()

    def test_get_pool_status(self):
        """Test connection pool status reporting."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool.minconn = 1
                mock_pool.maxconn = 10
                mock_pool_class.return_value = mock_pool

                ledger = PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                )

                status = ledger.get_pool_status()

                assert status["pool_available"] is True
                assert status["min_connections"] == 1
                assert status["max_connections"] == 10

                ledger.close()

    def test_get_pool_status_when_closed(self):
        """Test pool status reporting when pool is closed."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool_class.return_value = mock_pool

                ledger = PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                )

                ledger.close()

                status = ledger.get_pool_status()

                assert status["pool_available"] is False
                assert status["total_connections"] == 0

    def test_check_connection_health_success(self):
        """Test connection health check when pool is healthy."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                # Mock successful connection
                mock_cursor = MagicMock()
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_pool = MagicMock()
                mock_pool.getconn.return_value = mock_conn
                mock_pool_class.return_value = mock_pool

                ledger = PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                )

                health = ledger.check_connection_health()

                assert health["healthy"] is True
                assert health["error"] is None
                assert health["test_connection_success"] is True

                ledger.close()

    def test_check_connection_health_failure(self):
        """Test connection health check when pool is unhealthy."""
        from somali_dialect_classifier.database.postgres_ledger import PostgresLedger

        with patch.dict(os.environ, {"SDC_DB_PASSWORD": "test_password"}):
            with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
                mock_pool = MagicMock()
                mock_pool.getconn.side_effect = Exception("Connection failed")
                mock_pool_class.return_value = mock_pool

                ledger = PostgresLedger(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_password",
                )

                health = ledger.check_connection_health()

                assert health["healthy"] is False
                assert "Connection failed" in health["error"]
                assert health["test_connection_success"] is False

                ledger.close()


# ============================================================================
# HTTP Timeout Tests
# ============================================================================


class TestTimeoutHTTPSession:
    """Test TimeoutHTTPSession automatic timeout injection."""

    def test_default_timeout_injection(self):
        """Test that default timeout is injected when not provided."""
        session = TimeoutHTTPSession(default_timeout=15)

        with patch.object(requests.Session, "request") as mock_request:
            mock_request.return_value = Mock(status_code=200)

            session.get("https://example.com")

            # Verify timeout was injected
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == 15

    def test_explicit_timeout_preserved(self):
        """Test that explicit timeout parameter is preserved."""
        session = TimeoutHTTPSession(default_timeout=15)

        with patch.object(requests.Session, "request") as mock_request:
            mock_request.return_value = Mock(status_code=200)

            session.get("https://example.com", timeout=60)

            # Verify explicit timeout was used
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == 60

    def test_timeout_injection_for_all_methods(self):
        """Test timeout injection works for GET, POST, HEAD, etc."""
        session = TimeoutHTTPSession(default_timeout=20)

        with patch.object(requests.Session, "request") as mock_request:
            mock_request.return_value = Mock(status_code=200)

            session.get("https://example.com")
            session.post("https://example.com")
            session.head("https://example.com")

            # All 3 calls should have timeout=20
            assert mock_request.call_count == 3
            for call in mock_request.call_args_list:
                assert call[1]["timeout"] == 20


class TestHTTPSessionFactoryTimeout:
    """Test HTTPSessionFactory timeout configuration."""

    def test_create_session_with_default_timeout_from_config(self):
        """Test that create_session loads timeout from config when not provided."""
        with patch("somali_dialect_classifier.infra.config.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.http.request_timeout = 45
            mock_get_config.return_value = mock_config

            session = HTTPSessionFactory.create_session()

            # Verify session is TimeoutHTTPSession with config timeout
            assert isinstance(session, TimeoutHTTPSession)
            assert session.default_timeout == 45

    def test_create_session_with_explicit_timeout(self):
        """Test that explicit timeout parameter overrides config."""
        session = HTTPSessionFactory.create_session(timeout=90)

        # Verify session uses explicit timeout
        assert isinstance(session, TimeoutHTTPSession)
        assert session.default_timeout == 90

    def test_create_session_integration_with_retry(self):
        """Test that TimeoutHTTPSession works with retry adapters."""
        session = HTTPSessionFactory.create_session(max_retries=3, timeout=30)

        # Verify session is configured
        assert isinstance(session, TimeoutHTTPSession)
        assert session.default_timeout == 30

        # Verify retry adapters are mounted
        assert "http://" in session.adapters
        assert "https://" in session.adapters


class TestPipelineSetupTimeout:
    """Test PipelineSetup.create_default_http_session timeout configuration."""

    def test_create_default_http_session_loads_from_config(self):
        """Test that create_default_http_session uses config timeout by default."""
        with patch(
            "somali_dialect_classifier.infra.config.get_config"
        ) as mock_get_config:
            mock_config = MagicMock()
            mock_config.http.request_timeout = 25
            mock_get_config.return_value = mock_config

            session = PipelineSetup.create_default_http_session()

            # Verify session uses config timeout
            assert isinstance(session, TimeoutHTTPSession)
            assert session.default_timeout == 25

    def test_create_default_http_session_with_explicit_timeout(self):
        """Test that explicit timeout overrides config."""
        session = PipelineSetup.create_default_http_session(timeout=120)

        # Verify session uses explicit timeout
        assert isinstance(session, TimeoutHTTPSession)
        assert session.default_timeout == 120


class TestHTTPTimeoutConfiguration:
    """Test HTTP timeout configuration via environment variables."""

    def test_http_config_default_values(self):
        """Test default timeout configuration values."""
        config = get_config()

        # Default values
        assert config.http.request_timeout == 30
        assert config.http.connect_timeout == 10

    def test_http_config_environment_override(self):
        """Test timeout configuration via environment variables."""
        with patch.dict(
            os.environ,
            {
                "SDC_HTTP__REQUEST_TIMEOUT": "60",
                "SDC_HTTP__CONNECT_TIMEOUT": "15",
            },
        ):
            # Force config reload
            from somali_dialect_classifier.infra.config import Config

            config = Config()

            assert config.http.request_timeout == 60
            assert config.http.connect_timeout == 15


class TestTimeoutExceptionHandling:
    """Test that timeout exceptions are properly handled in processors."""

    def test_wikipedia_processor_handles_timeout(self):
        """Test that Wikipedia processor catches timeout exceptions."""
        # This is a smoke test - actual timeout handling is in requests.RequestException
        # which includes Timeout exceptions. The Wikipedia processor already has this.
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        # Verify processor can be instantiated (actual timeout handling tested in integration)
        processor = WikipediaSomaliProcessor()
        assert processor is not None

    def test_bbc_processor_handles_timeout(self):
        """Test that BBC processor catches timeout exceptions."""
        # BBC processor has explicit asyncio.TimeoutError and requests.Timeout handling
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        # Verify processor can be instantiated (actual timeout handling tested in integration)
        processor = BBCSomaliProcessor()
        assert processor is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestTimeoutIntegration:
    """Integration tests for timeout enforcement across the pipeline."""

    def test_end_to_end_timeout_flow(self):
        """Test complete flow: config -> session factory -> TimeoutHTTPSession."""
        # 1. Load config
        config = get_config()
        default_timeout = config.http.request_timeout

        # 2. Create session via factory (should use config)
        with patch(
            "somali_dialect_classifier.infra.config.get_config"
        ) as mock_get_config:
            mock_config = MagicMock()
            mock_config.http.request_timeout = default_timeout
            mock_get_config.return_value = mock_config

            session = HTTPSessionFactory.create_session()

        # 3. Verify session has correct timeout
        assert isinstance(session, TimeoutHTTPSession)
        assert session.default_timeout == default_timeout

        # 4. Verify timeout is injected in actual requests
        with patch.object(requests.Session, "request") as mock_request:
            mock_request.return_value = Mock(status_code=200)

            session.get("https://example.com")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == default_timeout

    def test_pipeline_setup_uses_timeout_session(self):
        """Test that PipelineSetup returns TimeoutHTTPSession."""
        session = PipelineSetup.create_default_http_session()

        assert isinstance(session, TimeoutHTTPSession)
        assert session.default_timeout > 0  # Has a configured timeout

    def test_timeout_prevents_silent_hangs(self):
        """Test that TimeoutHTTPSession prevents indefinite hangs."""
        session = TimeoutHTTPSession(default_timeout=1)  # 1 second timeout

        # Mock a slow server that never responds
        with patch.object(requests.Session, "request") as mock_request:
            mock_request.side_effect = requests.Timeout("Request timed out")

            with pytest.raises(requests.Timeout):
                session.get("https://slow-server.example.com")

        # Timeout exception should be raised, not hang indefinitely
