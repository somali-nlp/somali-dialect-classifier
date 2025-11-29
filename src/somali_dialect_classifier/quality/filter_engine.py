"""
FilterEngine: Centralized filter execution and statistics tracking.

Responsibilities:
- Execute quality filters on records
- Track filter execution statistics
- Provide filter pass/fail reasons
- Support extensible filter registration
"""

import logging
from collections import Counter
from typing import Any, Callable, Optional

from .filters.catalog import get_filter_label

logger = logging.getLogger(__name__)


class FilterEngine:
    """
    Execute and manage filters for data quality.

    The FilterEngine applies registered filters to records and tracks
    why records are filtered out.

    Example:
        ```python
        from somali_dialect_classifier.quality.filter_functions import (
            min_length_filter,
            topic_lexicon_enrichment_filter
        )
        from somali_dialect_classifier.pipeline.filter_engine import FilterEngine

        engine = FilterEngine()

        # Register filters
        engine.register_filter(min_length_filter, {'min_length': 10})
        engine.register_filter(topic_lexicon_enrichment_filter)

        # Apply to records
        filtered_records = engine.apply_filters(records)

        # Check statistics
        stats = engine.get_statistics()
        print(f"Filtered: {stats['total_filtered']}")
        print(f"Reasons: {stats['filter_reasons']}")
        ```

    **Note:** Filter import paths will change in a future release when
    preprocessing module is reorganized. Check documentation for updates.

    Attributes:
        filters (list): List of registered filter functions
        filter_reasons (dict): Count of records filtered by each reason
    """

    def __init__(self):
        """Initialize filter engine with empty filter list."""
        self.filters: list[tuple[Callable, dict[str, Any]]] = []
        self.filter_stats: Counter = Counter()

    def register_filter(self, filter_func: Callable, kwargs: dict[str, Any] = None) -> None:
        """
        Register a filter function to be applied.

        Args:
            filter_func: Filter function from preprocessing.filters
            kwargs: Optional dict of filter parameters

        Example:
            ```python
            from somali_dialect_classifier.quality.filter_functions import min_length_filter

            engine.register_filter(min_length_filter, {'min_length': 10})
            ```
        """
        self.filters.append((filter_func, kwargs or {}))

    def apply_filters(
        self, cleaned_text: str, record_title: str = ""
    ) -> tuple[bool, Optional[str], dict[str, Any]]:
        """
        Apply all registered filters to cleaned text.

        Args:
            cleaned_text: Cleaned text to filter
            record_title: Optional record title for debug logging

        Returns:
            Tuple of (passed, reason_if_failed, metadata_updates):
                - passed: True if all filters pass, False otherwise
                - reason_if_failed: Name of filter that failed (None if passed)
                - metadata_updates: Dictionary of metadata updates from filters

        Example:
            >>> passed, reason, metadata = engine.apply_filters("Hello world")
            >>> if not passed:
            ...     print(f"Filtered by: {reason}")
        """
        filter_metadata = {}

        for filter_func, filter_kwargs in self.filters:
            try:
                passes, metadata_updates = filter_func(cleaned_text, **filter_kwargs)

                if not passes:
                    # Record failed this filter
                    filter_name = filter_func.__name__
                    self.filter_stats[f"filtered_by_{filter_name}"] += 1

                    # Debug log for filter rejections
                    if record_title:
                        logger.debug(f"Record '{record_title[:50]}...' filtered by {filter_name}")

                    return False, filter_name, filter_metadata

                # Merge metadata updates from filter
                filter_metadata.update(metadata_updates)

            except Exception as e:
                # Log filter errors but don't fail pipeline
                filter_name = filter_func.__name__
                logger.warning(
                    f"Filter {filter_name} raised error on '{record_title[:50] if record_title else 'record'}': {e}"
                )
                # Treat as pass to avoid data loss from buggy filters
                continue

        return True, None, filter_metadata

    def get_filter_stats(self) -> dict[str, int]:
        """
        Get filter execution statistics.

        Returns:
            Dictionary mapping filter_name -> count of filtered records

        Example:
            >>> stats = engine.get_filter_stats()
            >>> for filter_name, count in stats.items():
            ...     print(f"{filter_name}: {count}")
        """
        return dict(self.filter_stats)

    def get_human_readable_stats(self) -> dict[str, tuple[str, int]]:
        """
        Get filter statistics with human-readable labels.

        Returns:
            Dictionary mapping filter_name -> (human_label, count)

        Example:
            >>> stats = engine.get_human_readable_stats()
            >>> for filter_name, (label, count) in stats.items():
            ...     print(f"{label}: {count} records")
        """
        readable_stats = {}
        for filter_key, count in self.filter_stats.items():
            # Remove "filtered_by_" prefix
            clean_key = filter_key.replace("filtered_by_", "")
            label = get_filter_label(clean_key)
            readable_stats[clean_key] = (label, count)
        return readable_stats

    def reset_stats(self) -> None:
        """Reset filter statistics (useful for testing or batch processing)."""
        self.filter_stats.clear()
