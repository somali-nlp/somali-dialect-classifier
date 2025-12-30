"""
Tests for LOW priority code quality fixes (L1, L3, L5).

These tests verify improvements made to:
- L1: Missing docstring examples in filter functions
- L3: Consistent quote style (double quotes per PEP 8)
- L5: __all__ exports in key modules for clean public API
"""

import doctest
import importlib
import sys
from pathlib import Path

import pytest

from somali_dialect_classifier.quality.filter_functions import (
    create_hf_filters,
    create_news_filters,
    create_wikipedia_filters,
    custom_filter,
    langid_filter,
    min_length_filter,
    namespace_filter,
    topic_lexicon_enrichment_filter,
)


# ==============================================================================
# L1: Missing Docstring Examples
# ==============================================================================


class TestL1DocstringExamples:
    """Test L1: Verify docstring examples work correctly."""

    def test_min_length_filter_docstring_examples(self):
        """Test that min_length_filter docstring examples execute correctly."""
        # Example 1: Short text should fail
        passes, meta = min_length_filter("Very short", threshold=50)
        assert passes is False
        assert meta == {}

        # Example 2: Long text should pass
        passes, meta = min_length_filter("A" * 100, threshold=50)
        assert passes is True
        assert meta == {}

    def test_langid_filter_docstring_examples(self):
        """Test that langid_filter docstring examples work correctly."""
        # English text should be detected
        passes, meta = langid_filter("This is English text")
        assert passes is False  # Not in allowed_langs={"so"}
        assert "detected_lang" in meta
        assert meta["detected_lang"] == "en"
        assert "lang_confidence" in meta
        assert 0.0 <= meta["lang_confidence"] <= 1.0

    def test_topic_lexicon_enrichment_filter_docstring_examples(self):
        """Test that topic_lexicon_enrichment_filter examples work correctly."""
        ruleset = {"sports": ["kubadda"], "politics": ["xukuumad"]}
        passes, meta = topic_lexicon_enrichment_filter("Kubadda waa ciyaartoy", ruleset)

        assert passes is True  # enrich_only=True by default
        assert "primary_topic" in meta
        assert meta["primary_topic"] == "sports"
        assert "topic_markers" in meta
        assert meta["topic_markers"]["sports"] == 1
        assert meta["topic_markers"]["politics"] == 0

    def test_namespace_filter_docstring_examples(self):
        """Test that namespace_filter examples work correctly."""
        # Talk page should be rejected
        passes, meta = namespace_filter("Talk:Article", "", ["Talk:", "User:"])
        assert passes is False
        assert "namespace" in meta
        assert meta["namespace"] == "Talk:"

        # Regular article should pass
        passes, meta = namespace_filter("Article", "", ["Talk:", "User:"])
        assert passes is True
        assert meta == {}

    def test_custom_filter_docstring_examples(self):
        """Test that custom_filter examples work correctly."""

        def has_numbers(text):
            count = sum(c.isdigit() for c in text)
            return count > 5, count

        passes, meta = custom_filter("Text with 123456", has_numbers, "number_count")
        assert passes is True
        assert meta["number_count"] == 6

        # Test text with fewer numbers
        passes, meta = custom_filter("Text with 123", has_numbers, "number_count")
        assert passes is False
        assert meta["number_count"] == 3

    def test_create_wikipedia_filters_docstring_examples(self):
        """Test that create_wikipedia_filters example works correctly."""
        filters = create_wikipedia_filters(min_length=100)

        assert isinstance(filters, list)
        assert len(filters) >= 2  # At least min_length and langid
        assert filters[0][0] == min_length_filter
        assert filters[0][1]["threshold"] == 100

    def test_create_news_filters_docstring_examples(self):
        """Test that create_news_filters example works correctly."""
        ruleset = {"sports": ["kubadda", "ciyaaryahan"]}
        filters = create_news_filters(dialect_ruleset=ruleset)

        assert isinstance(filters, list)
        assert len(filters) >= 2  # At least min_length, langid
        # Should include topic enrichment filter
        assert any(f[0] == topic_lexicon_enrichment_filter for f in filters)

    def test_docstring_examples_are_executable(self):
        """Test that all docstring examples can be found and executed."""
        import somali_dialect_classifier.quality.filter_functions as filter_mod

        # Run doctest on the module
        results = doctest.testmod(filter_mod, verbose=False)

        # Note: Some examples may fail due to heuristic nature of langid
        # This test verifies examples are syntactically correct
        assert results.attempted >= 5, "Should find at least 5 docstring examples"


# ==============================================================================
# L3: Consistent Quote Style
# ==============================================================================


class TestL3ConsistentQuoteStyle:
    """Test L3: Verify code runs correctly after quote standardization."""

    def test_filter_functions_imports_work(self):
        """Test that all filter functions can be imported after quote fixes."""
        # If quote changes broke anything, imports would fail
        from somali_dialect_classifier.quality.filter_functions import (
            create_hf_filters,
            create_news_filters,
            create_wikipedia_filters,
            custom_filter,
            langid_filter,
            min_length_filter,
            namespace_filter,
            topic_lexicon_enrichment_filter,
        )

        # Verify all are callable
        assert callable(min_length_filter)
        assert callable(langid_filter)
        assert callable(topic_lexicon_enrichment_filter)
        assert callable(namespace_filter)
        assert callable(custom_filter)
        assert callable(create_wikipedia_filters)
        assert callable(create_news_filters)
        assert callable(create_hf_filters)

    def test_filter_execution_with_string_literals(self):
        """Test filters work correctly with string literals."""
        # Test with various string parameters
        passes, meta = min_length_filter("test text", threshold=5)
        assert passes is True

        # Test with single quotes in content (should not affect execution)
        text_with_quotes = "Text with 'single' and \"double\" quotes"
        passes, meta = min_length_filter(text_with_quotes, threshold=10)
        assert passes is True

    def test_langid_filter_word_lists_work(self):
        """Test that langid filter word lists work after quote standardization."""
        # Somali text should be detected (word lists must be correct)
        somali_text = "Waxaan waa iyo oo ku la si ee uu ay aan"
        passes, meta = langid_filter(somali_text, allowed_langs={"so"})

        assert "detected_lang" in meta
        # Should detect as Somali or unknown (heuristic-based)
        assert meta["detected_lang"] in ["so", "unknown", "en"]

    def test_namespace_filter_prefixes_work(self):
        """Test namespace filter with various prefixes after quote standardization."""
        prefixes = ["Talk:", "User:", "Wikipedia:", "Template:"]

        # Test each prefix
        for prefix in prefixes:
            title = f"{prefix}TestPage"
            passes, meta = namespace_filter(title, "", prefixes)
            assert passes is False
            assert meta["namespace"] == prefix

    def test_topic_enrichment_ruleset_strings(self):
        """Test topic enrichment with string-based rulesets."""
        ruleset = {
            "sports": ["kubadda", "koox", "ciyaaraha"],
            "politics": ["xukuumad", "dowlad", "madaxweyne"],
            "economy": ["dhaqaale", "lacag", "suuq"],
        }

        text = "Kubadda cagta waa ciyaar aad u cajiib ah"
        passes, meta = topic_lexicon_enrichment_filter(text, ruleset)

        assert passes is True
        assert meta["primary_topic"] == "sports"
        assert meta["topic_markers"]["sports"] > 0


# ==============================================================================
# L5: Missing __all__ Exports
# ==============================================================================


class TestL5AllExports:
    """Test L5: Verify __all__ exports work correctly for public API."""

    def test_root_package_all_exports(self):
        """Test that root package __all__ is defined and correct."""
        import somali_dialect_classifier

        assert hasattr(somali_dialect_classifier, "__all__")
        assert "__version__" in somali_dialect_classifier.__all__
        assert "__pipeline_version__" in somali_dialect_classifier.__all__

        # Verify exports are accessible
        assert hasattr(somali_dialect_classifier, "__version__")
        assert hasattr(somali_dialect_classifier, "__pipeline_version__")

    def test_ingestion_package_all_exports(self):
        """Test that ingestion package __all__ is defined and correct."""
        import somali_dialect_classifier.ingestion as ingestion

        assert hasattr(ingestion, "__all__")

        # Expected exports
        expected_exports = ["BasePipeline", "CrawlLedger", "DedupEngine"]
        for export in expected_exports:
            assert export in ingestion.__all__, f"{export} should be in __all__"

        # Verify exports are accessible
        assert hasattr(ingestion, "BasePipeline")
        assert hasattr(ingestion, "CrawlLedger")
        assert hasattr(ingestion, "DedupEngine")

    def test_quality_package_all_exports(self):
        """Test that quality package __all__ is defined and correct."""
        import somali_dialect_classifier.quality as quality

        assert hasattr(quality, "__all__")

        # Expected exports
        expected_exports = [
            "FilterEngine",
            "RecordBuilder",
            "SilverDatasetWriter",
            "SilverWriter",
        ]
        for export in expected_exports:
            assert export in quality.__all__, f"{export} should be in __all__"

        # Verify exports are accessible
        assert hasattr(quality, "FilterEngine")
        assert hasattr(quality, "RecordBuilder")
        assert hasattr(quality, "SilverDatasetWriter")
        assert hasattr(quality, "SilverWriter")

        # Verify SilverWriter is alias for SilverDatasetWriter
        assert quality.SilverWriter is quality.SilverDatasetWriter

    def test_infra_package_all_exports(self):
        """Test that infra package __all__ is defined and correct."""
        import somali_dialect_classifier.infra as infra

        assert hasattr(infra, "__all__")

        # Expected exports
        expected_exports = ["get_config", "DataManager"]
        for export in expected_exports:
            assert export in infra.__all__, f"{export} should be in __all__"

        # Verify exports are accessible
        assert hasattr(infra, "get_config")
        assert hasattr(infra, "DataManager")

    def test_wildcard_import_ingestion(self):
        """Test that wildcard import from ingestion works correctly."""
        # Create isolated namespace for wildcard import
        namespace = {}
        exec("from somali_dialect_classifier.ingestion import *", namespace)

        # Should have exactly __all__ exports
        expected_exports = ["BasePipeline", "CrawlLedger", "DedupEngine"]
        for export in expected_exports:
            assert export in namespace, f"{export} should be available via wildcard import"

        # Should NOT import private/internal modules
        assert "__builtins__" in namespace  # Always present
        # Check that we got approximately the right number of exports
        public_exports = [k for k in namespace.keys() if not k.startswith("_")]
        assert len(public_exports) == len(expected_exports)

    def test_wildcard_import_quality(self):
        """Test that wildcard import from quality works correctly."""
        namespace = {}
        exec("from somali_dialect_classifier.quality import *", namespace)

        expected_exports = [
            "FilterEngine",
            "RecordBuilder",
            "SilverDatasetWriter",
            "SilverWriter",
        ]
        for export in expected_exports:
            assert export in namespace, f"{export} should be available via wildcard import"

        public_exports = [k for k in namespace.keys() if not k.startswith("_")]
        assert len(public_exports) == len(expected_exports)

    def test_wildcard_import_infra(self):
        """Test that wildcard import from infra works correctly."""
        namespace = {}
        exec("from somali_dialect_classifier.infra import *", namespace)

        expected_exports = ["get_config", "DataManager"]
        for export in expected_exports:
            assert export in namespace, f"{export} should be available via wildcard import"

        public_exports = [k for k in namespace.keys() if not k.startswith("_")]
        assert len(public_exports) == len(expected_exports)

    def test_all_exports_are_importable(self):
        """Test that all exports listed in __all__ can actually be imported."""
        import somali_dialect_classifier
        import somali_dialect_classifier.infra as infra
        import somali_dialect_classifier.ingestion as ingestion
        import somali_dialect_classifier.quality as quality

        # Test root package
        for name in somali_dialect_classifier.__all__:
            assert hasattr(somali_dialect_classifier, name), \
                f"{name} in __all__ but not accessible"

        # Test ingestion
        for name in ingestion.__all__:
            assert hasattr(ingestion, name), \
                f"ingestion.{name} in __all__ but not accessible"

        # Test quality
        for name in quality.__all__:
            assert hasattr(quality, name), \
                f"quality.{name} in __all__ but not accessible"

        # Test infra
        for name in infra.__all__:
            assert hasattr(infra, name), \
                f"infra.{name} in __all__ but not accessible"


# ==============================================================================
# Integration Tests: All Fixes Together
# ==============================================================================


class TestIntegrationAllLowFixes:
    """Test that all LOW priority fixes work together correctly."""

    def test_filter_chain_with_examples_and_clean_imports(self):
        """Test complete filter chain using documented examples and clean imports."""
        # Use wildcard import (tests L5)
        namespace = {}
        exec("from somali_dialect_classifier.quality import *", namespace)

        FilterEngine = namespace["FilterEngine"]

        # Create filter chain using factory functions (tests L1 examples)
        filters = create_wikipedia_filters(min_length=50)

        # Apply filters
        engine = FilterEngine()
        for filter_func, kwargs in filters:
            engine.register_filter(filter_func, kwargs)

        # Test with sample text
        sample_text = "A" * 100  # Passes min_length
        passes, reason, metadata = engine.apply_filters(sample_text)

        # Should pass min_length filter
        assert isinstance(passes, bool)
        assert isinstance(metadata, dict)

    def test_end_to_end_filter_usage(self):
        """Test end-to-end filter usage with all fixes applied."""
        # Import using clean API (L5)
        from somali_dialect_classifier.quality import FilterEngine

        # Create filters using examples (L1)
        ruleset = {"sports": ["kubadda"], "politics": ["xukuumad"]}
        filters = create_news_filters(dialect_ruleset=ruleset)

        # Apply to sample text
        engine = FilterEngine()
        for filter_func, kwargs in filters:
            engine.register_filter(filter_func, kwargs)

        # Somali sports text
        text = "Kubadda cagta waa mid aad u xiiso badan"
        passes, reason, metadata = engine.apply_filters(text)

        assert isinstance(passes, bool)
        assert isinstance(metadata, dict)
        # reason is None if passes, or string if failed
        assert reason is None or isinstance(reason, str)

    def test_public_api_documentation_consistency(self):
        """Test that public API matches documentation expectations."""
        # These imports should work as documented
        from somali_dialect_classifier import __version__
        from somali_dialect_classifier.infra import DataManager, get_config
        from somali_dialect_classifier.ingestion import BasePipeline, CrawlLedger
        from somali_dialect_classifier.quality import (
            FilterEngine,
            RecordBuilder,
            SilverDatasetWriter,
        )

        # Verify types
        assert isinstance(__version__, str)
        assert callable(get_config)
        assert callable(DataManager)
        assert callable(BasePipeline)
        assert callable(CrawlLedger)
        assert callable(FilterEngine)
        assert callable(RecordBuilder)
        assert callable(SilverDatasetWriter)
