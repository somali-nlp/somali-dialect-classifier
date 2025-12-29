"""
Record filters for silver dataset quality control.

Filters are stateless functions that accept cleaned text and return:
(bool, metadata_updates)

- bool: True if record passes, False if it should be dropped
- metadata_updates: dict of fields to merge into record metadata (empty if no updates)

Usage:
    from somali_dialect_classifier.quality.filter_functions import min_length_filter

    passes, meta = min_length_filter("Short text", threshold=50)
    # passes=False, meta={}

Filters can be chained in BasePipeline to enforce data quality standards
across all sources (Wikipedia, BBC, HuggingFace, etc.).
"""

from typing import Any, Callable, Optional


def min_length_filter(cleaned_text: str, threshold: int = 50) -> tuple[bool, dict[str, Any]]:
    """
    Filter records below minimum character length.

    Args:
        cleaned_text: Cleaned text content
        threshold: Minimum number of characters (default: 50)

    Returns:
        (passes, metadata_updates)
        - passes: True if text length >= threshold
        - metadata_updates: Empty dict (no metadata to add)

    Example:
        >>> passes, meta = min_length_filter("Very short", threshold=50)
        >>> passes
        False
        >>> passes, meta = min_length_filter("A" * 100, threshold=50)
        >>> passes
        True
    """
    passes = len(cleaned_text) >= threshold
    return passes, {}


def langid_filter(
    cleaned_text: str, allowed_langs: Optional[set[str]] = None, confidence_threshold: float = 0.5
) -> tuple[bool, dict[str, Any]]:
    """
    Filter records not in allowed languages using heuristic detection.

    Uses simple heuristics rather than langid library for better Somali detection:
    - Checks for Somali-specific characters and patterns
    - Falls back to basic Latin script detection

    Args:
        cleaned_text: Cleaned text content
        allowed_langs: Set of allowed ISO 639-1 codes (default: {"so"})
        confidence_threshold: Minimum confidence (0-1) for acceptance (default: 0.5)

    Returns:
        (passes, metadata_updates)
        - passes: True if language is in allowed_langs with sufficient confidence
        - metadata_updates: {"detected_lang": str, "lang_confidence": float}

    Example:
        >>> passes, meta = langid_filter("This is English text")
        >>> passes
        False
        >>> meta["detected_lang"]
        'en'
    """
    # Simple heuristic for Somali detection
    # Somali uses Latin script with specific diacritic patterns
    if allowed_langs is None:
        allowed_langs = {"so"}
    detected_lang = "unknown"
    confidence = 0.0

    # Basic length check
    if len(cleaned_text.strip()) < 10:
        return False, {"detected_lang": "unknown", "lang_confidence": 0.0}

    # Count Somali-specific patterns
    somali_score = 0.0

    # Somali common words (expanded vocabulary for better detection)
    somali_words = {
        "waa",
        "iyo",
        "oo",
        "ah",
        "ka",
        "ku",
        "la",
        "si",
        "ee",
        "uu",
        "ay",
        "aan",
        "soo",
        "buu",
        "way",
        "waxaa",
        "dheh",
        "waxay",
        "waxey",
        "inay",
        "mida",
        "qabiilada",
        "hadlayo",
        "kuwaasi",
        "dhaqan",
        "deegaano",
        "tirsan",
        "wadanka",
        "soomaaliya",
        "degaan",
        "caasimada",
        "sida",
        "sanad",
        "dhaqaaqeen",
        "degmooyinka",
        "badweynta",
        "dhaxeysa",
        "iyadoo",
        "xiriir",
        "leeyahay",
        "webiga",
        "hoose",
        "sheegayaa",
        "laga",
        "ahayd",
        "ugu",
        "horaysa",
        "ciyaaraha",
        "kubadda",
        "koobkii",
        "koob",
        "koox",
        "kooxo",
        "xilli",
        "wada",
        "wadan",
        "reer",
        "mudane",
        "naxariistee",
        "carabka",
        "qiraayaan",
        "marka",
        "markii",
        "markaas",
        "dhulka",
        "tusaale",
        "ahaan",
        "todobaadood",
        "isbuuc",
        "aqoonyahan",
        "joogto",
        "jiray",
        "waqtiga",
        "waqti",
        "gudaha",
        "taalaa",
        "qiyaasaa",
        "bari",
        "beri",
        "qof",
        "dad",
        "suuq",
        "qayb",
        "qoran",
        "nool",
        "afka",
        "jir",
        "jira",
        "tahay",
        "yahay",
        "yidhi",
        "idhi",
        "qiimaha",
        "geel",
        "geela",
        "gob",
        "jasiirad",
        "jamhuuriyada",
        "yaalo",
        "yaalaa",
        "gaarka",
        "dastuurka",
        "cusub",
        "hore",
        "aduun",
        "aduunka",
        "aqoonsado",
        "xuquuq",
        "dhul",
        "dhashay",
        "magaalo",
        "magaalada",
        "mucaarad",
        "burbur",
        "burburki",
        "kacaan",
        "kacaanka",
        "carbeed",
        "sidoo",
        "aqoon",
        "rasmi",
        "weli",
        "dhaqaalaha",
        "dhaqaale",
        "xubin",
        "sare",
        "sarre",
        "hees",
        "heeso",
        "suugaan",
        "guri",
        "guryo",
        "cunto",
        "gaajo",
        "baahi",
        "yiraahdo",
        "xoolo",
        "beer",
        "beero",
        "dhaqato",
        "roob",
        "abaar",
        "xeeb",
        "xeebta",
        "yaqaanaa",
        "suuban",
        "fiican",
        "xil",
        "xilsaaray",
        "tiro",
        "qabtaan",
        "dowlad",
        "dowladda",
        "dhexe",
        "arrin",
        "arrimaha",
        "luqadaha",
        "tira",
    }

    words = cleaned_text.lower().split()
    if len(words) > 0:
        somali_word_count = sum(1 for w in words if w in somali_words)
        somali_score = somali_word_count / len(words)

    # English detection (basic heuristic)
    english_words = {
        "the",
        "is",
        "and",
        "or",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "from",
        "by",
        "about",
        "as",
        "it",
        "was",
    }

    if len(words) > 0:
        english_word_count = sum(1 for w in words if w in english_words)
        english_score = english_word_count / len(words)

        # Simple decision
        if somali_score > english_score and somali_score > 0.1:
            detected_lang = "so"
            confidence = min(0.9, somali_score * 2)  # Scale up but cap at 0.9
        elif english_score > 0.15:
            detected_lang = "en"
            confidence = min(0.9, english_score * 2)
        else:
            # Check for non-Latin scripts (very basic)
            non_latin_chars = sum(1 for c in cleaned_text if ord(c) > 127 and ord(c) < 591)
            if non_latin_chars > len(cleaned_text) * 0.3:
                detected_lang = "other"
                confidence = 0.7
            else:
                # Assume Somali if mostly Latin with no strong English signature
                detected_lang = "so"
                confidence = 0.6

    passes = detected_lang in allowed_langs and confidence >= confidence_threshold

    metadata_updates = {"detected_lang": detected_lang, "lang_confidence": round(confidence, 2)}

    return passes, metadata_updates


def topic_lexicon_enrichment_filter(
    cleaned_text: str, ruleset: dict[str, list[str]], enrich_only: bool = True
) -> tuple[bool, dict[str, Any]]:
    """
    Enrich records with topic markers based on lexicon matching.

    IMPORTANT: This filter performs TOPIC ENRICHMENT, NOT DIALECT DETECTION.
    It identifies domain/topic indicators (sports, politics, economy) based on
    keyword matching. Future supervised dialect classification will be implemented
    separately in Stage 2+.

    Scans text for topic/domain markers from lexicon lists (e.g., sports,
    politics, economy). Primarily used for metadata enrichment rather than
    filtering.

    Args:
        cleaned_text: Cleaned text content
        ruleset: Dict mapping topic/category names to lists of marker words
                 Example: {"sports": ["kubadda", "kooxda"], "politics": ["xukuumad", "madaxweyne"]}
        enrich_only: If True, always pass but add metadata (default: True)
                     If False, reject if no markers found

    Returns:
        (passes, metadata_updates)
        - passes: True if markers found OR enrich_only=True
        - metadata_updates: {"topic_markers": {...}, "primary_topic": str, "total_topic_markers": int}

    Example:
        >>> ruleset = {"sports": ["kubadda"], "politics": ["xukuumad"]}
        >>> passes, meta = topic_lexicon_enrichment_filter("Kubadda waa ciyaartoy", ruleset)
        >>> passes
        True
        >>> meta["primary_topic"]
        'sports'
        >>> meta["topic_markers"]
        {'sports': 1, 'politics': 0}
    """
    if not ruleset:
        # No ruleset provided, pass through
        return True, {}

    # Count matches for each topic
    topic_counts = dict.fromkeys(ruleset, 0)
    text_lower = cleaned_text.lower()
    words = set(text_lower.split())

    for topic, markers in ruleset.items():
        for marker in markers:
            marker_lower = marker.lower()
            # Check for whole word matches
            if marker_lower in words:
                topic_counts[topic] += 1

    # Determine primary topic
    total_markers = sum(topic_counts.values())
    primary_topic = "unknown"

    if total_markers > 0:
        primary_topic = max(topic_counts, key=topic_counts.get)

    metadata_updates = {
        "topic_markers": topic_counts,
        "primary_topic": primary_topic,
        "total_topic_markers": total_markers,
    }

    # Pass if markers found OR if enrich_only mode
    passes = enrich_only or total_markers > 0

    return passes, metadata_updates


def namespace_filter(
    title: str, text: str, skip_prefixes: list[str]
) -> tuple[bool, dict[str, Any]]:
    """
    Filter records based on title namespace (primarily for Wikipedia).

    Rejects pages with titles matching skip patterns (e.g., "Talk:",
    "User:", "Wikipedia:", etc.).

    Args:
        title: Page/article title
        text: Cleaned text content (unused, for signature consistency)
        skip_prefixes: List of title prefixes to reject

    Returns:
        (passes, metadata_updates)
        - passes: True if title doesn't start with any skip_prefix
        - metadata_updates: {"namespace": str} if rejected, else {}

    Example:
        >>> passes, meta = namespace_filter("Talk:Article", "", ["Talk:", "User:"])
        >>> passes
        False
        >>> meta["namespace"]
        'Talk:'
    """
    for prefix in skip_prefixes:
        if title.startswith(prefix):
            return False, {"namespace": prefix}

    return True, {}


def custom_filter(
    cleaned_text: str, predicate_func: Callable, metadata_key: str = "custom_filter_result"
) -> tuple[bool, dict[str, Any]]:
    """
    Generic filter wrapper for custom predicates.

    Allows processors to inject arbitrary filtering logic without
    defining new filter functions.

    Args:
        cleaned_text: Cleaned text content
        predicate_func: Callable that returns (bool, optional_value)
        metadata_key: Key to store result in metadata if predicate returns value

    Returns:
        (passes, metadata_updates)
        - passes: Result of predicate_func
        - metadata_updates: {metadata_key: value} if predicate returns value

    Example:
        >>> def has_numbers(text):
        ...     count = sum(c.isdigit() for c in text)
        ...     return count > 5, count
        >>> passes, meta = custom_filter("Text with 123456", has_numbers, "number_count")
        >>> passes
        True
        >>> meta["number_count"]
        6
    """
    result = predicate_func(cleaned_text)

    if isinstance(result, tuple):
        passes, value = result
        metadata_updates = {metadata_key: value} if value is not None else {}
    else:
        passes = bool(result)
        metadata_updates = {}

    return passes, metadata_updates


# Convenience constructors for common filter configurations


def create_wikipedia_filters(
    min_length: int = 50, skip_prefixes: Optional[list[str]] = None
) -> list[tuple[Callable, dict[str, Any]]]:
    """
    Create standard filter chain for Wikipedia sources.

    Args:
        min_length: Minimum text length (default: 50)
        skip_prefixes: Namespace prefixes to skip (default: Wikipedia defaults)

    Returns:
        List of (filter_func, kwargs) tuples ready for BasePipeline

    Example:
        >>> filters = create_wikipedia_filters(min_length=100)
        >>> # Pass to processor: processor.record_filters = filters
    """
    if skip_prefixes is None:
        skip_prefixes = [
            "Wikipedia:",
            "Talk:",
            "User:",
            "File:",
            "MediaWiki:",
            "Template:",
            "Help:",
            "Category:",
            "Portal:",
            "Draft:",
        ]

    return [
        (min_length_filter, {"threshold": min_length}),
        (langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.5}),
        # namespace_filter requires title, handled specially in processor
    ]


def create_news_filters(
    min_length: int = 50, dialect_ruleset: Optional[dict[str, list[str]]] = None
) -> list[tuple[Callable, dict[str, Any]]]:
    """
    Create standard filter chain for news sources (BBC, VOA, etc.).

    Args:
        min_length: Minimum text length (default: 50)
        dialect_ruleset: Optional dialect lexicons for enrichment

    Returns:
        List of (filter_func, kwargs) tuples ready for BasePipeline

    Example:
        >>> ruleset = {"sports": ["kubadda", "ciyaaryahan"]}
        >>> filters = create_news_filters(dialect_ruleset=ruleset)
    """
    filters = [
        (min_length_filter, {"threshold": min_length}),
        (langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.5}),
    ]

    if dialect_ruleset:
        filters.append(
            (topic_lexicon_enrichment_filter, {"ruleset": dialect_ruleset, "enrich_only": True})
        )

    return filters


def create_hf_filters(
    min_length: int = 50, allowed_langs: Optional[set[str]] = None
) -> list[tuple[Callable, dict[str, Any]]]:
    """
    Create standard filter chain for HuggingFace datasets.

    Args:
        min_length: Minimum text length (default: 50)
        allowed_langs: Allowed languages (default: {"so"})

    Returns:
        List of (filter_func, kwargs) tuples ready for BasePipeline
    """
    if allowed_langs is None:
        allowed_langs = {"so"}

    return [
        (min_length_filter, {"threshold": min_length}),
        (langid_filter, {"allowed_langs": allowed_langs, "confidence_threshold": 0.5}),
    ]
