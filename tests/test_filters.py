"""
Unit tests for record filters.

Tests all filter functions to ensure correct behavior for quality control.
"""

import pytest
from somali_dialect_classifier.preprocessing.filters import (
    min_length_filter,
    langid_filter,
    dialect_heuristic_filter,
    namespace_filter,
    custom_filter,
    create_wikipedia_filters,
    create_news_filters,
    create_hf_filters,
)


class TestMinLengthFilter:
    """Tests for minimum length filter."""

    def test_passes_long_text(self):
        """Test that long text passes filter."""
        text = "A" * 100
        passes, meta = min_length_filter(text, threshold=50)

        assert passes is True
        assert meta == {}

    def test_rejects_short_text(self):
        """Test that short text is rejected."""
        text = "Short"
        passes, meta = min_length_filter(text, threshold=50)

        assert passes is False
        assert meta == {}

    def test_exactly_at_threshold(self):
        """Test text exactly at threshold length."""
        text = "A" * 50
        passes, meta = min_length_filter(text, threshold=50)

        assert passes is True

    def test_one_below_threshold(self):
        """Test text one character below threshold."""
        text = "A" * 49
        passes, meta = min_length_filter(text, threshold=50)

        assert passes is False

    def test_custom_threshold(self):
        """Test with custom threshold value."""
        text = "A" * 75
        passes, meta = min_length_filter(text, threshold=100)

        assert passes is False

    def test_empty_string(self):
        """Test empty string is rejected."""
        passes, meta = min_length_filter("", threshold=50)

        assert passes is False


class TestLangidFilter:
    """Tests for language identification filter."""

    def test_detects_somali_text(self):
        """Test that Somali text is correctly identified."""
        # Use text with many common Somali words
        somali_text = "Waxaan waa iyo oo ku la si ee uu ay aan soo buu way waxaa"
        passes, meta = langid_filter(somali_text, allowed_langs={"so"}, confidence_threshold=0.3)

        assert passes is True
        assert "detected_lang" in meta
        assert "lang_confidence" in meta
        # Should detect as Somali or unknown (both acceptable for this heuristic)
        assert meta["detected_lang"] in ["so", "unknown"]
        assert 0.0 <= meta["lang_confidence"] <= 1.0

    def test_rejects_english_text(self):
        """Test that English text is rejected."""
        english_text = "This is an English text about Somalia and its beautiful culture"
        passes, meta = langid_filter(english_text, allowed_langs={"so"})

        assert passes is False
        assert meta["detected_lang"] == "en"

    def test_enriches_metadata_with_language(self):
        """Test that metadata includes language detection results."""
        text = "Waxaan waa iyo oo ku la"
        passes, meta = langid_filter(text, allowed_langs={"so"})

        assert "detected_lang" in meta
        assert "lang_confidence" in meta
        assert isinstance(meta["lang_confidence"], (int, float))

    def test_confidence_threshold(self):
        """Test confidence threshold filtering."""
        # Ambiguous text might have low confidence
        text = "Text text text"
        passes, meta = langid_filter(text, allowed_langs={"so"}, confidence_threshold=0.9)

        # Should fail due to high confidence requirement
        assert passes is False or meta["lang_confidence"] >= 0.9

    def test_multiple_allowed_languages(self):
        """Test allowing multiple languages."""
        english_text = "This is English text with the and is"
        passes, meta = langid_filter(english_text, allowed_langs={"so", "en"})

        # Should pass since English is now allowed
        assert passes is True
        assert meta["detected_lang"] in {"so", "en"}

    def test_very_short_text(self):
        """Test that very short text is handled gracefully."""
        passes, meta = langid_filter("Hi", allowed_langs={"so"})

        assert passes is False
        assert meta["detected_lang"] == "unknown"
        assert meta["lang_confidence"] == 0.0


class TestDialectHeuristicFilter:
    """Tests for dialect/topic heuristic filter."""

    def test_enriches_with_topic_markers(self):
        """Test that topic markers are detected and added to metadata."""
        ruleset = {
            "sports": ["kubadda", "ciyaaryahan"],
            "politics": ["xukuumad", "madaxweyne"],
        }
        text = "Kubadda cagta waa ciyaar aad u xiiso badan"

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=True)

        assert passes is True
        assert "dialect_markers" in meta
        assert "primary_dialect" in meta
        assert meta["dialect_markers"]["sports"] > 0
        assert meta["primary_dialect"] == "sports"

    def test_identifies_primary_dialect(self):
        """Test that primary dialect is correctly identified."""
        ruleset = {
            "sports": ["kubadda"],
            "politics": ["xukuumad", "baarlamaan", "madaxweyne"],
        }
        text = "Xukuumad cusub oo baarlamaan ka dhiganaya madaxweyne"

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=True)

        assert meta["primary_dialect"] == "politics"
        assert meta["dialect_markers"]["politics"] == 3

    def test_enrich_only_mode_always_passes(self):
        """Test that enrich_only mode never rejects records."""
        ruleset = {"sports": ["kubadda"]}
        text = "Text with no markers at all"

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=True)

        assert passes is True
        assert meta["primary_dialect"] == "unknown"
        assert meta["total_dialect_markers"] == 0

    def test_filter_mode_rejects_without_markers(self):
        """Test that filter mode rejects records without markers."""
        ruleset = {"sports": ["kubadda"]}
        text = "Text with no markers"

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=False)

        assert passes is False
        assert meta["primary_dialect"] == "unknown"

    def test_filter_mode_passes_with_markers(self):
        """Test that filter mode passes records with markers."""
        ruleset = {"sports": ["kubadda"]}
        text = "Kubadda cagta waa xiiso badan"

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=False)

        assert passes is True
        assert meta["total_dialect_markers"] > 0

    def test_case_insensitive_matching(self):
        """Test that marker matching is case-insensitive."""
        ruleset = {"sports": ["kubadda"]}
        text = "KUBADDA CAGTA"  # All caps

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=True)

        assert meta["dialect_markers"]["sports"] > 0

    def test_empty_ruleset(self):
        """Test behavior with empty ruleset."""
        passes, meta = dialect_heuristic_filter("Some text", {}, enrich_only=True)

        assert passes is True
        assert meta == {}

    def test_multiple_markers_in_text(self):
        """Test counting multiple marker occurrences."""
        ruleset = {"sports": ["kubadda", "ciyaaryahan", "kooxda"]}
        text = "Kubadda iyo ciyaaryahan kooxda"

        passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=True)

        assert meta["dialect_markers"]["sports"] == 3


class TestNamespaceFilter:
    """Tests for namespace filter (Wikipedia-specific)."""

    def test_rejects_talk_pages(self):
        """Test that Talk: pages are rejected."""
        passes, meta = namespace_filter("Talk:Article", "", ["Talk:", "User:"])

        assert passes is False
        assert meta["namespace"] == "Talk:"

    def test_rejects_user_pages(self):
        """Test that User: pages are rejected."""
        passes, meta = namespace_filter("User:John", "", ["Talk:", "User:"])

        assert passes is False
        assert meta["namespace"] == "User:"

    def test_passes_regular_articles(self):
        """Test that regular articles pass."""
        passes, meta = namespace_filter("Somalia", "", ["Talk:", "User:"])

        assert passes is True
        assert meta == {}

    def test_checks_all_prefixes(self):
        """Test that all skip prefixes are checked."""
        skip_prefixes = ["Talk:", "User:", "Template:", "Category:"]

        assert namespace_filter("Talk:X", "", skip_prefixes)[0] is False
        assert namespace_filter("User:X", "", skip_prefixes)[0] is False
        assert namespace_filter("Template:X", "", skip_prefixes)[0] is False
        assert namespace_filter("Category:X", "", skip_prefixes)[0] is False

    def test_empty_skip_list(self):
        """Test with empty skip list."""
        passes, meta = namespace_filter("Any:Title", "", [])

        assert passes is True


class TestCustomFilter:
    """Tests for custom filter wrapper."""

    def test_simple_predicate(self):
        """Test with simple boolean predicate."""
        def has_digit(text):
            return any(c.isdigit() for c in text)

        passes, meta = custom_filter("Text with 123", has_digit)
        assert passes is True

        passes, meta = custom_filter("Text without digits", has_digit)
        assert passes is False

    def test_predicate_with_value(self):
        """Test predicate that returns (bool, value)."""
        def count_digits(text):
            count = sum(c.isdigit() for c in text)
            return count > 5, count

        passes, meta = custom_filter("123456", count_digits, "digit_count")

        assert passes is True
        assert meta["digit_count"] == 6

    def test_predicate_returning_none_value(self):
        """Test that None values don't create metadata."""
        def check_length(text):
            return len(text) > 10, None

        passes, meta = custom_filter("Short", check_length)

        assert passes is False
        assert meta == {}


class TestConvenienceConstructors:
    """Tests for convenience filter constructor functions."""

    def test_create_wikipedia_filters(self):
        """Test Wikipedia filter chain creation."""
        filters = create_wikipedia_filters(min_length=100)

        assert len(filters) >= 2
        assert any("min_length" in str(f[0].__name__) for f in filters)
        assert any("langid" in str(f[0].__name__) for f in filters)

    def test_create_wikipedia_filters_custom_threshold(self):
        """Test Wikipedia filters with custom threshold."""
        filters = create_wikipedia_filters(min_length=200)

        # Find min_length filter and check threshold
        min_length_configs = [f[1] for f in filters if "min_length" in f[0].__name__]
        assert len(min_length_configs) > 0
        assert min_length_configs[0]["threshold"] == 200

    def test_create_news_filters(self):
        """Test news filter chain creation."""
        filters = create_news_filters(min_length=50)

        assert len(filters) >= 2
        assert any("min_length" in f[0].__name__ for f in filters)
        assert any("langid" in f[0].__name__ for f in filters)

    def test_create_news_filters_with_dialect_ruleset(self):
        """Test news filters with dialect enrichment."""
        ruleset = {"sports": ["kubadda"], "politics": ["xukuumad"]}
        filters = create_news_filters(dialect_ruleset=ruleset)

        assert len(filters) >= 3
        assert any("dialect" in f[0].__name__ for f in filters)

    def test_create_hf_filters(self):
        """Test HuggingFace filter chain creation."""
        filters = create_hf_filters(min_length=50, allowed_langs={"so", "en"})

        assert len(filters) >= 2

        # Check langid filter has correct allowed_langs
        langid_configs = [f[1] for f in filters if "langid" in f[0].__name__]
        assert len(langid_configs) > 0
        assert langid_configs[0]["allowed_langs"] == {"so", "en"}


class TestFilterIntegration:
    """Integration tests for filter combinations."""

    def test_filter_chain_execution(self):
        """Test executing multiple filters in sequence."""
        # Create a realistic filter chain
        filters = [
            (min_length_filter, {"threshold": 20}),
            (langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.5}),
        ]

        # Test text that should pass all filters
        somali_text = "Waxaan waa iyo oo ku la si ee uu ay aan soo buu way waxaa dheh"
        all_passed = True
        accumulated_meta = {}

        for filter_func, kwargs in filters:
            passes, meta = filter_func(somali_text, **kwargs)
            if not passes:
                all_passed = False
                break
            accumulated_meta.update(meta)

        assert all_passed is True
        assert "detected_lang" in accumulated_meta

    def test_short_circuit_on_first_failure(self):
        """Test that filter chain stops on first failure."""
        filters = [
            (min_length_filter, {"threshold": 1000}),  # Will fail
            (langid_filter, {"allowed_langs": {"so"}}),
        ]

        text = "Short text"

        # First filter should fail, second shouldn't execute
        passes, meta = filters[0][0](text, **filters[0][1])
        assert passes is False

        # In real pipeline, we'd stop here
