"""
Contract tests for source name canonicalisation (TD-019).

Verifies that every registered processor exposes the canonical
``<source>-somali`` source name in ``processor.source`` and that
MetricsCollector is initialised with the same value.
"""

import pytest

from somdialc.ingestion.source_names import CANONICAL_SOURCES


class TestCanonicalSourcesConstant:
    """CANONICAL_SOURCES must be complete and well-formed."""

    def test_all_processors_have_canonical_entry(self):
        required_keys = {"wikipedia", "bbc", "sprakbanken", "tiktok", "huggingface"}
        assert required_keys.issubset(CANONICAL_SOURCES.keys()), (
            f"Missing keys in CANONICAL_SOURCES: {required_keys - set(CANONICAL_SOURCES.keys())}"
        )

    def test_all_values_follow_convention(self):
        for key, value in CANONICAL_SOURCES.items():
            assert value == f"{key}-somali", (
                f"CANONICAL_SOURCES[{key!r}] = {value!r} does not follow '<source>-somali' convention"
            )

    def test_no_uppercase_in_values(self):
        for key, value in CANONICAL_SOURCES.items():
            assert value == value.lower(), (
                f"CANONICAL_SOURCES[{key!r}] contains uppercase characters: {value!r}"
            )


class TestProcessorSourceNames:
    """Each processor's .source attribute must equal the canonical value."""

    def _make_wiki_processor(self):
        from unittest.mock import MagicMock, patch

        mock_ledger = MagicMock()
        mock_ledger.backend.get_url_state.return_value = None
        mock_ledger.get_conditional_headers.return_value = {}

        with patch(
            "somdialc.ingestion.processors.wikipedia_somali_processor.get_ledger",
            return_value=mock_ledger,
        ):
            from somdialc.ingestion.processors.wikipedia_somali_processor import (
                WikipediaSomaliProcessor,
            )

            return WikipediaSomaliProcessor(ledger=mock_ledger)

    def _make_bbc_processor(self):
        from unittest.mock import MagicMock, patch

        mock_ledger = MagicMock()

        with patch(
            "somdialc.ingestion.processors.bbc_somali_processor.get_ledger",
            return_value=mock_ledger,
        ):
            from somdialc.ingestion.processors.bbc_somali_processor import BBCSomaliProcessor

            return BBCSomaliProcessor(ledger=mock_ledger)

    def _make_sprakbanken_processor(self):
        from unittest.mock import MagicMock, patch

        mock_ledger = MagicMock()

        with patch(
            "somdialc.ingestion.processors.sprakbanken_somali_processor.get_ledger",
            return_value=mock_ledger,
        ):
            from somdialc.ingestion.processors.sprakbanken_somali_processor import (
                SprakbankenSomaliProcessor,
            )

            return SprakbankenSomaliProcessor(ledger=mock_ledger)

    def test_wikipedia_source_is_canonical(self):
        proc = self._make_wiki_processor()
        assert proc.source == CANONICAL_SOURCES["wikipedia"], (
            f"WikipediaSomaliProcessor.source = {proc.source!r}, expected {CANONICAL_SOURCES['wikipedia']!r}"
        )

    def test_bbc_source_is_canonical(self):
        proc = self._make_bbc_processor()
        assert proc.source == CANONICAL_SOURCES["bbc"], (
            f"BBCSomaliProcessor.source = {proc.source!r}, expected {CANONICAL_SOURCES['bbc']!r}"
        )

    def test_sprakbanken_source_is_canonical(self):
        proc = self._make_sprakbanken_processor()
        assert proc.source == CANONICAL_SOURCES["sprakbanken"], (
            f"SprakbankenSomaliProcessor.source = {proc.source!r}, expected {CANONICAL_SOURCES['sprakbanken']!r}"
        )

    def test_tiktok_source_is_canonical(self):
        from unittest.mock import MagicMock, patch

        mock_ledger = MagicMock()

        # TikTok imports get_ledger inline; patch at the canonical import location.
        with patch(
            "somdialc.ingestion.crawl_ledger.get_ledger",
            return_value=mock_ledger,
        ):
            from somdialc.ingestion.processors.tiktok_somali_processor import (
                TikTokSomaliProcessor,
            )

            proc = TikTokSomaliProcessor(
                apify_api_token="test-token",
                ledger=mock_ledger,
            )
        assert proc.source == CANONICAL_SOURCES["tiktok"], (
            f"TikTokSomaliProcessor.source = {proc.source!r}, expected {CANONICAL_SOURCES['tiktok']!r}"
        )


class TestMetricsCollectorReceivesCanonicalSource:
    """MetricsCollector must be initialised with processor.source (canonical form)."""

    def test_wikipedia_metrics_source_is_canonical(self):
        from unittest.mock import MagicMock, patch

        mock_ledger = MagicMock()
        mock_ledger.backend.get_url_state.return_value = None

        captured_sources: list[str] = []

        original_mc = __import__(
            "somdialc.infra.metrics", fromlist=["MetricsCollector"]
        ).MetricsCollector

        class CapturingMC(original_mc):
            def __init__(self, run_id, source, **kwargs):
                captured_sources.append(source)
                super().__init__(run_id, source, **kwargs)

        with (
            patch(
                "somdialc.ingestion.processors.wikipedia_somali_processor.get_ledger",
                return_value=mock_ledger,
            ),
            patch(
                "somdialc.ingestion.processors.wikipedia_somali_processor.MetricsCollector",
                CapturingMC,
            ),
        ):
            from somdialc.ingestion.processors.wikipedia_somali_processor import (
                WikipediaSomaliProcessor,
            )

            proc = WikipediaSomaliProcessor(ledger=mock_ledger)
            # Force metrics init by calling the factory directly
            proc._metrics_factory(proc.run_id, proc.source)

        assert any(s == CANONICAL_SOURCES["wikipedia"] for s in captured_sources), (
            f"No MetricsCollector was created with {CANONICAL_SOURCES['wikipedia']!r}; got {captured_sources}"
        )

    def test_bbc_discovery_metrics_source_is_canonical(self):
        """bbc/discovery.py must pass processor.source to MetricsCollector."""
        import somdialc.ingestion.processors.bbc.discovery as disc_module
        from unittest.mock import MagicMock, patch

        mock_processor = MagicMock()
        mock_processor.source = CANONICAL_SOURCES["bbc"]
        mock_processor.run_id = "test_run_bbc"
        mock_processor.force = False
        mock_processor.article_links_file = MagicMock()
        mock_processor.article_links_file.exists.return_value = False
        mock_processor.raw_dir = MagicMock()
        mock_processor.date_accessed = "2026-05-01"
        mock_processor.max_articles = None

        # _check_robots_txt, _scrape_rss_feeds return empty so we stop early
        mock_processor._check_robots_txt.return_value = None
        mock_processor._scrape_rss_feeds.return_value = []
        mock_processor._get_article_links.return_value = []
        mock_processor.ledger = MagicMock()
        mock_processor._export_stage_metrics = MagicMock()

        created_sources: list[str] = []

        class TrackingMC:
            def __init__(self, run_id, source, **kwargs):
                created_sources.append(source)

            def increment(self, *a, **kw):
                pass

            def export_json(self, *a, **kw):
                pass

        with (
            patch.object(disc_module, "MetricsCollector", TrackingMC),
            patch.object(disc_module, "set_context"),
        ):
            disc_module.download(mock_processor)

        assert created_sources == [CANONICAL_SOURCES["bbc"]], (
            f"Expected [{CANONICAL_SOURCES['bbc']!r}], got {created_sources}"
        )
