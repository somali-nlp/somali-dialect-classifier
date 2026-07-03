"""Unit tests for somdialc.quality.filters.catalog.

Covers the filter label/description/category lookup helpers and the
unknown-filter-key fallback paths used by the dashboard export pipeline.
"""

import pytest

from somdialc.quality.filters.catalog import (
    FILTER_CATALOG,
    export_for_javascript,
    get_all_categories,
    get_filter_category,
    get_filter_description,
    get_filter_label,
    sanitize_filter_key,
    validate_filter_breakdown,
)


class TestGetFilterLabel:
    def test_known_filter_returns_catalog_label(self):
        assert get_filter_label("min_length_filter") == "Minimum length (50 chars)"

    def test_unknown_filter_falls_back_to_sanitized_key(self):
        with pytest.warns(UserWarning, match="FILTER_CATALOG_MISS"):
            label = get_filter_label("some_new_filter")
        assert label == "Some New Filter"


class TestGetFilterDescription:
    def test_known_filter_returns_description(self):
        desc = get_filter_description("min_length_filter")
        assert "50 characters" in desc

    def test_unknown_filter_returns_placeholder(self):
        desc = get_filter_description("mystery_filter")
        assert "No description available" in desc
        assert "mystery_filter" in desc


class TestGetFilterCategory:
    def test_known_filter_returns_category(self):
        assert get_filter_category("emoji_only_comment") == "content_quality"

    def test_unknown_filter_returns_unknown(self):
        assert get_filter_category("mystery_filter") == "unknown"


class TestExportForJavascript:
    def test_exports_all_catalog_entries(self):
        labels = export_for_javascript()
        assert len(labels) == len(FILTER_CATALOG)
        assert labels["min_length_filter"] == "Minimum length (50 chars)"

    def test_values_are_plain_strings(self):
        labels = export_for_javascript()
        assert all(isinstance(v, str) for v in labels.values())


class TestSanitizeFilterKey:
    def test_converts_snake_case_to_title_case(self):
        assert sanitize_filter_key("min_length_filter") == "Min Length Filter"

    def test_single_word(self):
        assert sanitize_filter_key("spam") == "Spam"


class TestGetAllCategories:
    def test_groups_filters_by_category(self):
        categories = get_all_categories()
        assert "min_length_filter" in categories["length"]
        assert "text_too_short_after_cleanup" in categories["length"]

    def test_every_catalog_entry_is_categorized(self):
        categories = get_all_categories()
        all_keys = {key for keys in categories.values() for key in keys}
        assert all_keys == set(FILTER_CATALOG.keys())


class TestValidateFilterBreakdown:
    def test_known_keys_pass_through_unchanged(self):
        breakdown = {"min_length_filter": 100, "langid_filter": 50}
        assert validate_filter_breakdown(breakdown) == breakdown

    def test_unknown_keys_pass_through_with_warning_logged(self, caplog):
        breakdown = {"unknown_filter": 25}
        with caplog.at_level("WARNING"):
            result = validate_filter_breakdown(breakdown)
        assert result == {"unknown_filter": 25}
        assert "Unknown filter in breakdown" in caplog.text

    def test_empty_breakdown_returns_empty(self):
        assert validate_filter_breakdown({}) == {}
