"""
Tests for FilterEngine service.

Verifies filter execution and statistics tracking.
"""

import pytest

from somali_dialect_classifier.pipeline.filter_engine import FilterEngine


def sample_filter_pass(cleaned_text: str, **kwargs) -> tuple[bool, dict]:
    """Sample filter that always passes."""
    return True, {"sample_metadata": "value"}


def sample_filter_fail(cleaned_text: str, **kwargs) -> tuple[bool, dict]:
    """Sample filter that always fails."""
    return False, {}


def min_length_filter(cleaned_text: str, threshold: int = 10, **kwargs) -> tuple[bool, dict]:
    """Sample min length filter."""
    return len(cleaned_text) >= threshold, {"length": len(cleaned_text)}


class TestFilterEngine:
    """Test suite for FilterEngine."""

    def test_initialization(self):
        """Test FilterEngine initialization."""
        engine = FilterEngine()
        assert engine.filters == []
        assert len(engine.filter_stats) == 0

    def test_register_filter(self):
        """Test filter registration."""
        engine = FilterEngine()
        engine.register_filter(sample_filter_pass, {"key": "value"})
        assert len(engine.filters) == 1
        assert engine.filters[0][0] == sample_filter_pass
        assert engine.filters[0][1] == {"key": "value"}

    def test_apply_filters_all_pass(self):
        """Test apply_filters when all filters pass."""
        engine = FilterEngine()
        engine.register_filter(sample_filter_pass)
        passed, reason, metadata = engine.apply_filters("test text")
        assert passed is True
        assert reason is None
        assert "sample_metadata" in metadata

    def test_apply_filters_one_fails(self):
        """Test apply_filters when one filter fails."""
        engine = FilterEngine()
        engine.register_filter(sample_filter_pass)
        engine.register_filter(sample_filter_fail)
        passed, reason, metadata = engine.apply_filters("test text")
        assert passed is False
        assert reason == "sample_filter_fail"
        assert "sample_metadata" in metadata  # Metadata from first filter

    def test_apply_filters_with_kwargs(self):
        """Test apply_filters with filter kwargs."""
        engine = FilterEngine()
        engine.register_filter(min_length_filter, {"threshold": 5})
        passed, reason, metadata = engine.apply_filters("short")
        assert passed is True
        engine2 = FilterEngine()
        engine2.register_filter(min_length_filter, {"threshold": 10})
        passed, reason, metadata = engine2.apply_filters("short")
        assert passed is False

    def test_filter_stats(self):
        """Test filter statistics tracking."""
        engine = FilterEngine()
        engine.register_filter(min_length_filter, {"threshold": 10})
        engine.apply_filters("short text", "Test Record 1")
        engine.apply_filters("another short", "Test Record 2")
        engine.apply_filters("this text is long enough for the filter", "Test Record 3")
        stats = engine.get_filter_stats()
        assert "filtered_by_min_length_filter" in stats
        assert stats["filtered_by_min_length_filter"] == 2

    def test_get_human_readable_stats(self):
        """Test human-readable filter statistics."""
        engine = FilterEngine()
        engine.register_filter(min_length_filter, {"threshold": 10})
        engine.apply_filters("short")
        readable_stats = engine.get_human_readable_stats()
        assert "min_length_filter" in readable_stats
        label, count = readable_stats["min_length_filter"]
        assert count == 1
        assert isinstance(label, str)

    def test_reset_stats(self):
        """Test filter statistics reset."""
        engine = FilterEngine()
        engine.register_filter(sample_filter_fail)
        engine.apply_filters("test")
        assert len(engine.get_filter_stats()) > 0
        engine.reset_stats()
        assert len(engine.get_filter_stats()) == 0

    def test_filter_exception_handling(self):
        """Test that filter exceptions are handled gracefully."""

        def buggy_filter(cleaned_text: str, **kwargs) -> tuple[bool, dict]:
            raise ValueError("Simulated filter error")

        engine = FilterEngine()
        engine.register_filter(buggy_filter)
        engine.register_filter(sample_filter_pass)
        # Should continue processing despite exception
        passed, reason, metadata = engine.apply_filters("test text", "Test Record")
        assert passed is True  # Buggy filter treated as pass
        assert "sample_metadata" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
