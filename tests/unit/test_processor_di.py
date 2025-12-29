"""
Unit tests for processor dependency injection.

Tests that all 5 processors accept optional dependencies for testability:
- ledger (CrawlLedger)
- metrics_factory (callable for MetricsCollector creation)
- http_session (requests.Session)

This enables full mocking and isolation in tests.
"""

from unittest.mock import Mock, MagicMock
import pytest
import requests

from somali_dialect_classifier.ingestion.processors.sprakbanken_somali_processor import (
    SprakbankenSomaliProcessor,
)
from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
    WikipediaSomaliProcessor,
)


class TestSprakbankenProcessorDI:
    """Test dependency injection for Språkbanken processor."""

    def test_accepts_mock_ledger(self):
        """Test that processor accepts a mock ledger."""
        # Arrange
        mock_ledger = Mock()
        mock_ledger.get_url_state = Mock(return_value=None)
        mock_ledger.check_quota_available = Mock(return_value=(True, 100))

        # Act
        processor = SprakbankenSomaliProcessor(
            corpus_id="somali-cilmi", ledger=mock_ledger
        )

        # Assert
        assert processor.ledger is mock_ledger
        assert processor.ledger.get_url_state(
            "https://example.com"
        ) is None  # Test mock works

    def test_accepts_mock_metrics_factory(self):
        """Test that processor accepts a mock metrics factory."""
        # Arrange
        mock_metrics = Mock()
        mock_factory = Mock(return_value=mock_metrics)

        # Act
        processor = SprakbankenSomaliProcessor(
            corpus_id="somali-cilmi", metrics_factory=mock_factory
        )

        # Assert
        # Factory is called lazily when download() is called
        # We can verify it's stored correctly
        assert processor._metrics_factory is mock_factory

    def test_accepts_mock_http_session(self):
        """Test that processor accepts a mock HTTP session."""
        # Arrange
        mock_session = Mock(spec=requests.Session)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.iter_content = Mock(return_value=[b"test data"])
        mock_session.get = Mock(return_value=mock_response)

        # Act
        processor = SprakbankenSomaliProcessor(
            corpus_id="somali-cilmi", http_session=mock_session
        )

        # Assert
        assert processor._http_session is mock_session
        # Verify lazy getter works
        session = processor._get_http_session()
        assert session is mock_session

    def test_default_behavior_unchanged(self):
        """Test that default behavior is preserved when no DI parameters provided."""
        # Act - create processor without DI parameters
        processor = SprakbankenSomaliProcessor(corpus_id="somali-cilmi")

        # Assert - defaults should be used
        assert processor.ledger is not None  # Should get default ledger
        assert processor._metrics_factory is not None  # Should have default factory
        assert processor._http_session is None  # Should be None until lazy init


class TestWikipediaProcessorDI:
    """Test dependency injection for Wikipedia processor."""

    def test_accepts_mock_ledger(self):
        """Test that Wikipedia processor accepts a mock ledger."""
        # Arrange
        mock_ledger = Mock()
        mock_ledger.backend = Mock()
        mock_ledger.backend.get_url_state = Mock(return_value=None)

        # Act
        processor = WikipediaSomaliProcessor(ledger=mock_ledger)

        # Assert
        assert processor.ledger is mock_ledger

    def test_accepts_mock_metrics_factory(self):
        """Test that Wikipedia processor accepts a mock metrics factory."""
        # Arrange
        mock_metrics = Mock()
        mock_factory = Mock(return_value=mock_metrics)

        # Act
        processor = WikipediaSomaliProcessor(metrics_factory=mock_factory)

        # Assert
        assert processor._metrics_factory is mock_factory

    def test_accepts_mock_http_session(self):
        """Test that Wikipedia processor accepts a mock HTTP session."""
        # Arrange
        mock_session = Mock(spec=requests.Session)

        # Act
        processor = WikipediaSomaliProcessor(http_session=mock_session)

        # Assert
        assert processor._http_session is mock_session

    def test_default_behavior_unchanged(self):
        """Test that default behavior is preserved for Wikipedia processor."""
        # Act
        processor = WikipediaSomaliProcessor()

        # Assert
        assert processor.ledger is not None
        assert processor._metrics_factory is not None
        assert processor._http_session is None  # Lazy init


class TestDIIntegration:
    """Integration tests demonstrating full mocking scenarios."""

    def test_full_mock_scenario_sprakbanken(self):
        """Demonstrate full mocking of all dependencies for Språkbanken processor."""
        # Arrange - create all mocks
        mock_ledger = MagicMock()
        mock_ledger.get_url_state.return_value = None
        mock_ledger.check_quota_available.return_value = (True, 100)

        mock_metrics = MagicMock()
        mock_metrics.increment = MagicMock()
        mock_factory = lambda run_id, source: mock_metrics

        mock_session = MagicMock(spec=requests.Session)

        # Act - inject all dependencies
        processor = SprakbankenSomaliProcessor(
            corpus_id="somali-cilmi",
            ledger=mock_ledger,
            metrics_factory=mock_factory,
            http_session=mock_session,
        )

        # Assert - all dependencies are mocked
        assert processor.ledger is mock_ledger
        assert processor._http_session is mock_session
        assert processor._metrics_factory is mock_factory

        # Verify lazy initialization works
        session = processor._get_http_session()
        assert session is mock_session


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing code."""

    def test_existing_code_still_works_sprakbanken(self):
        """Verify that existing code without DI parameters still works."""
        # This is how processors are currently instantiated
        processor = SprakbankenSomaliProcessor(corpus_id="somali-cilmi", force=False)

        # Should not raise any errors
        assert processor is not None
        assert processor.corpus_id == "somali-cilmi"

    def test_existing_code_still_works_wikipedia(self):
        """Verify that existing Wikipedia processor code still works."""
        processor = WikipediaSomaliProcessor(force=False)

        assert processor is not None
        assert processor.source == "wikipedia-somali"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
