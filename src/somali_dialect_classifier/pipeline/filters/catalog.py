"""
Filter catalog for quality validation pipeline.

This module provides a centralized registry of all quality filters used across
different data sources (Wikipedia, BBC Somali, TikTok, HuggingFace, Språkbanken).

Single source of truth for filter labels, descriptions, and categories.
Eliminates parallel label maintenance between Python and JavaScript.

Usage:
    >>> from somali_dialect_classifier.pipeline.filters import get_filter_label
    >>> get_filter_label("min_length_filter")
    'Minimum length (50 chars)'

    >>> from somali_dialect_classifier.pipeline.filters import export_for_javascript
    >>> labels = export_for_javascript()
    >>> # Save to JSON for dashboard consumption
"""

import logging
import warnings

# Configure logger
logger = logging.getLogger(__name__)


# Filter catalog: filter_key -> (human_label, description, category)
FILTER_CATALOG: dict[str, tuple[str, str, str]] = {
    # Length-based filters
    "min_length_filter": (
        "Minimum length (50 chars)",
        "Text must be at least 50 characters after cleaning",
        "length",
    ),
    "text_too_short_after_cleanup": (
        "Very short text (<3 chars)",
        "Text has fewer than 3 characters after removing symbols/emojis",
        "length",
    ),
    # Content quality filters
    "emoji_only_comment": (
        "Emoji-only comment",
        "Comment contains only emojis, symbols, or punctuation with no linguistic content",
        "content_quality",
    ),
    "empty_after_cleaning": (
        "Empty after cleaning",
        "Text becomes empty after removing special characters and whitespace",
        "content_quality",
    ),
    # Language detection filters
    "langid_filter": (
        "Language ID (non-Somali)",
        "Text identified as non-Somali language by language detection",
        "language",
    ),
    # Domain-specific filters
    "dialect_heuristic_filter": (
        "Dialect heuristics",
        "Text failed dialect-specific heuristic checks",
        "dialect",
    ),
    "namespace_filter": (
        "Wikipedia namespace exclusion",
        "Wikipedia pages from excluded namespaces (e.g., Talk, User, Template)",
        "namespace",
    ),
    # Placeholder filters for future enhancements
    "profanity_filter": (
        "Profanity detected",
        "Text contains profane or offensive language",
        "content_quality",
    ),
    "duplicate_content": (
        "Duplicate content",
        "Text is a duplicate or near-duplicate of existing content",
        "deduplication",
    ),
    "encoding_error": (
        "Encoding errors",
        "Text contains encoding errors or malformed characters",
        "encoding",
    ),
    "bot_generated": (
        "Bot-generated content",
        "Text appears to be bot-generated or automated",
        "content_quality",
    ),
    "spam_detected": (
        "Spam detected",
        "Text identified as spam or promotional content",
        "content_quality",
    ),
    "invalid_characters": (
        "Invalid characters",
        "Text contains invalid or non-printable characters",
        "encoding",
    ),
}


def get_filter_label(filter_key: str) -> str:
    """
    Get human-readable label for a filter key.

    Args:
        filter_key: Filter identifier (e.g., "min_length_filter")

    Returns:
        Human-readable label (e.g., "Minimum length (50 chars)")
        Falls back to sanitized filter_key if not found in catalog

    Example:
        >>> get_filter_label("emoji_only_comment")
        'Emoji-only comment'

        >>> get_filter_label("unknown_filter")
        'Unknown Filter'  # Fallback with warning logged
    """
    if filter_key in FILTER_CATALOG:
        return FILTER_CATALOG[filter_key][0]

    # Fallback: log warning and return sanitized key
    logger.warning(f"Unknown filter key: '{filter_key}' not in FILTER_CATALOG")
    warnings.warn(
        f"FILTER_CATALOG_MISS: filter_key='{filter_key}'", stacklevel=2, category=UserWarning
    )
    return sanitize_filter_key(filter_key)


def get_filter_description(filter_key: str) -> str:
    """
    Get detailed description for a filter key.

    Args:
        filter_key: Filter identifier

    Returns:
        Detailed description of what the filter does

    Example:
        >>> get_filter_description("min_length_filter")
        'Text must be at least 50 characters after cleaning'
    """
    if filter_key in FILTER_CATALOG:
        return FILTER_CATALOG[filter_key][1]

    logger.warning(f"Unknown filter key: '{filter_key}' not in FILTER_CATALOG")
    return f"No description available for '{filter_key}'"


def get_filter_category(filter_key: str) -> str:
    """
    Get category for a filter key.

    Categories: 'length', 'content_quality', 'language', 'dialect',
                'namespace', 'deduplication', 'encoding'

    Args:
        filter_key: Filter identifier

    Returns:
        Category string (e.g., "length", "content_quality")

    Example:
        >>> get_filter_category("emoji_only_comment")
        'content_quality'
    """
    if filter_key in FILTER_CATALOG:
        return FILTER_CATALOG[filter_key][2]

    logger.warning(f"Unknown filter key: '{filter_key}' not in FILTER_CATALOG")
    return "unknown"


def export_for_javascript() -> dict[str, str]:
    """
    Export filter labels for dashboard consumption.

    Future enhancement: Generate JSON file for dynamic loading.
    Current usage: Copy-paste into dashboard/js/core/aggregates.js

    Returns:
        Dictionary mapping filter_key -> human_label

    Example:
        >>> labels = export_for_javascript()
        >>> labels["min_length_filter"]
        'Minimum length (50 chars)'

        >>> import json
        >>> with open("dashboard/data/filter_labels.json", "w") as f:
        ...     json.dump(labels, f, indent=2)
    """
    return {key: label for key, (label, _, _) in FILTER_CATALOG.items()}


def sanitize_filter_key(raw_reason: str) -> str:
    """
    Convert raw filter reason to human-readable label.

    Fallback for filters not yet in FILTER_CATALOG.
    Converts snake_case to Title Case.

    Args:
        raw_reason: Raw filter key (e.g., "min_length_filter")

    Returns:
        Human-readable label (e.g., "Min Length Filter")

    Example:
        >>> sanitize_filter_key("min_length_filter")
        'Min Length Filter'

        >>> sanitize_filter_key("emoji_only_comment")
        'Emoji Only Comment'
    """
    # Convert snake_case to Title Case
    words = raw_reason.replace("_", " ").split()
    return " ".join(word.capitalize() for word in words)


def get_all_categories() -> dict[str, list]:
    """
    Get all filters grouped by category.

    Returns:
        Dictionary mapping category -> list of filter keys

    Example:
        >>> categories = get_all_categories()
        >>> categories["length"]
        ['min_length_filter', 'text_too_short_after_cleanup']
    """
    categories: dict[str, list] = {}
    for key, (_, _, category) in FILTER_CATALOG.items():
        if category not in categories:
            categories[category] = []
        categories[category].append(key)
    return categories


def validate_filter_breakdown(filter_breakdown: dict[str, int]) -> dict[str, int]:
    """
    Validate and sanitize filter breakdown from metrics.

    Logs warnings for unknown filter keys but allows data through.

    Args:
        filter_breakdown: Dictionary of filter_key -> count

    Returns:
        Validated filter breakdown with warnings logged

    Example:
        >>> breakdown = {
        ...     "min_length_filter": 100,
        ...     "unknown_filter": 50
        ... }
        >>> validated = validate_filter_breakdown(breakdown)
        # Logs warning for "unknown_filter"
    """
    validated = {}
    for key, count in filter_breakdown.items():
        if key not in FILTER_CATALOG:
            logger.warning(
                f"Unknown filter in breakdown: '{key}' with count {count}. "
                f"Consider adding to FILTER_CATALOG."
            )
        validated[key] = count
    return validated
