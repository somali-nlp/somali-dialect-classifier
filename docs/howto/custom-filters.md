# Custom Filters Guide

**Last Updated**: 2025-10-16

This guide shows you how to write and register custom quality filters for your data pipelines.

## Filter Basics

### Filter Signature

All filters follow this signature:

```python
def my_filter(cleaned_text: str, **kwargs) -> Tuple[bool, Dict[str, Any]]:
    """
    Args:
        cleaned_text: Text after cleaning pipeline
        **kwargs: Filter-specific parameters

    Returns:
        (passes, metadata_updates)
        - passes: True if record should be kept, False to filter out
        - metadata_updates: Dict to merge into silver record metadata
    """
    # Filter logic here
    passes = some_condition(cleaned_text)
    metadata = {"filter_info": "value"}
    return passes, metadata
```

### Key Principles

1. **Stateless**: Filters should not maintain state between records
2. **Fast**: Filters run on every record, optimize for performance
3. **Two-mode**: Can reject records OR enrich metadata (or both)
4. **Error-tolerant**: Exceptions are caught and logged, don't crash pipeline

---

## Example 1: Length Filter

### Basic Implementation

```python
def min_length_filter(cleaned_text: str, threshold: int = 50) -> Tuple[bool, Dict[str, Any]]:
    """Reject records shorter than threshold."""
    passes = len(cleaned_text) >= threshold
    return passes, {}
```

### Usage

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

class MyProcessor(BBCSomaliProcessor):
    def _register_filters(self):
        # Add length filter with custom threshold
        self.record_filters.append((min_length_filter, {"threshold": 100}))
```

---

## Example 2: Keyword Filter

### Implementation

```python
from typing import Tuple, Dict, Any, Set

def keyword_filter(
    cleaned_text: str,
    required_keywords: Set[str],
    case_sensitive: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """
    Keep only records containing at least one required keyword.

    Args:
        cleaned_text: Cleaned text
        required_keywords: Set of keywords (e.g., {"Somalia", "Somali"})
        case_sensitive: Whether matching is case-sensitive

    Returns:
        (passes, metadata) where metadata includes matched keywords
    """
    text = cleaned_text if case_sensitive else cleaned_text.lower()
    keywords = required_keywords if case_sensitive else {k.lower() for k in required_keywords}

    matched = {kw for kw in keywords if kw in text}
    passes = len(matched) > 0

    metadata = {
        "matched_keywords": list(matched),
        "keyword_count": len(matched)
    }

    return passes, metadata
```

### Usage

```python
class MyProcessor(BasePipeline):
    def _register_filters(self):
        # Only keep articles mentioning Somali cities
        somali_cities = {"Muqdisho", "Hargeysa", "Kismaayo", "Berbera"}

        self.record_filters.append((keyword_filter, {
            "required_keywords": somali_cities,
            "case_sensitive": False
        }))
```

---

## Example 3: Date Range Filter

### Implementation

```python
from datetime import datetime, date
from typing import Tuple, Dict, Any, Optional

def date_range_filter(
    cleaned_text: str,
    raw_metadata: Dict[str, Any],  # Access to raw record metadata
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Filter records by publication date range.

    Note: This filter needs access to raw_metadata, so it must be called differently.
    See usage example below.
    """
    date_published = raw_metadata.get('date_published')

    if not date_published:
        # No date - decision depends on strictness
        return False, {"filter_reason": "missing_date"}

    # Parse date
    if isinstance(date_published, str):
        try:
            pub_date = datetime.fromisoformat(date_published).date()
        except ValueError:
            return False, {"filter_reason": "invalid_date_format"}
    elif isinstance(date_published, date):
        pub_date = date_published
    else:
        return False, {"filter_reason": "invalid_date_type"}

    # Check range
    if start_date and pub_date < start_date:
        return False, {"filter_reason": "before_start_date", "pub_date": pub_date.isoformat()}

    if end_date and pub_date > end_date:
        return False, {"filter_reason": "after_end_date", "pub_date": pub_date.isoformat()}

    return True, {"pub_date_validated": pub_date.isoformat()}
```

### Usage

This filter needs access to raw metadata, so you'll need to modify your processor:

```python
class DateFilteredProcessor(BBCSomaliProcessor):
    def _register_filters(self):
        # Standard filters first
        super()._register_filters()

        # Add date filter
        from datetime import date
        self.record_filters.append((date_range_filter, {
            "start_date": date(2024, 1, 1),
            "end_date": date(2025, 12, 31),
            "raw_metadata": None  # Will be passed dynamically
        }))

    def process(self) -> Path:
        # Override process() to inject raw_metadata into filter calls
        # (Advanced - see base_pipeline.py for full implementation)
        pass
```

---

## Example 4: Regex Pattern Filter

### Implementation

```python
import re
from typing import Tuple, Dict, Any

def regex_filter(
    cleaned_text: str,
    pattern: str,
    invert: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """
    Filter records based on regex pattern.

    Args:
        cleaned_text: Cleaned text
        pattern: Regex pattern (e.g., r"\\d{4}" to find years)
        invert: If True, REJECT matches instead of keeping them

    Returns:
        (passes, metadata)
    """
    match = re.search(pattern, cleaned_text)
    passes = (match is not None) if not invert else (match is None)

    metadata = {}
    if match:
        metadata["regex_match"] = match.group(0)
        metadata["regex_match_pos"] = match.span()

    return passes, metadata
```

### Usage

```python
class RegexProcessor(BasePipeline):
    def _register_filters(self):
        # Only keep articles with 4-digit years
        self.record_filters.append((regex_filter, {
            "pattern": r"\\d{4}",
            "invert": False
        }))

        # Or reject articles with email addresses
        self.record_filters.append((regex_filter, {
            "pattern": r"[\\w.-]+@[\\w.-]+\\.\\w+",
            "invert": True
        }))
```

---

## Example 5: Enrichment-Only Filter

Filters don't have to reject records - they can just add metadata:

### Implementation

```python
def sentiment_enrichment_filter(
    cleaned_text: str,
    positive_words: Set[str],
    negative_words: Set[str]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Add sentiment markers to metadata without filtering.

    Always returns (True, metadata) so no records are rejected.
    """
    text_lower = cleaned_text.lower()

    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)

    sentiment_score = pos_count - neg_count

    metadata = {
        "positive_word_count": pos_count,
        "negative_word_count": neg_count,
        "sentiment_score": sentiment_score,
        "sentiment": "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 else "neutral"
    }

    return True, metadata  # Always pass
```

### Usage

```python
positive_words = {"wanaagsan", "fiican", "farxad"}
negative_words = {"xun", "dhibaato", "cabasho"}

self.record_filters.append((sentiment_enrichment_filter, {
    "positive_words": positive_words,
    "negative_words": negative_words
}))
```

---

## Example 6: Chained Filters

Combine multiple filters for complex logic:

```python
class NewsProcessor(BasePipeline):
    def _register_filters(self):
        from somali_dialect_classifier.preprocessing.filters import (
            min_length_filter,
            langid_filter
        )

        # Filter 1: Minimum length
        self.record_filters.append((min_length_filter, {
            "threshold": 100
        }))

        # Filter 2: Language detection
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": 0.7
        }))

        # Filter 3: Must contain news keywords
        news_keywords = {"wararka", "sheegay", "shir", "dowlad"}
        self.record_filters.append((keyword_filter, {
            "required_keywords": news_keywords,
            "case_sensitive": False
        }))

        # Filter 4: Sentiment enrichment (no rejection)
        self.record_filters.append((sentiment_enrichment_filter, {
            "positive_words": {"wanaagsan", "guul"},
            "negative_words": {"xun", "dhibaato"}
        }))
```

**Execution**: Filters run sequentially. If any filter returns `False`, the record is rejected and subsequent filters don't run.

---

## Advanced: Configurable Filters

### Externalize Configuration

```python
# config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class CustomFilterConfig(BaseSettings):
    keyword_list: List[str] = Field(default=["Soomaaliya", "Muqdisho"])
    min_keyword_count: int = Field(default=1)

    class Config:
        env_prefix = 'SDC_CUSTOM_FILTER__'
```

### Use in Processor

```python
from somali_dialect_classifier.config import get_config

class ConfigurableProcessor(BasePipeline):
    def _register_filters(self):
        config = get_config()
        custom_config = config.custom_filter  # Assuming added to main config

        self.record_filters.append((keyword_filter, {
            "required_keywords": set(custom_config.keyword_list),
            "case_sensitive": False
        }))
```

### Override via Environment

```bash
export SDC_CUSTOM_FILTER__KEYWORD_LIST='["Soomaaliya","Hargeysa","Kismaayo"]'
export SDC_CUSTOM_FILTER__MIN_KEYWORD_COUNT=2

python your_script.py
```

---

## Testing Filters

### Unit Test Template

```python
# tests/test_custom_filters.py
import pytest
from your_module import keyword_filter

class TestKeywordFilter:
    def test_passes_with_match(self):
        text = "Muqdisho waa magaalada ugu weyn ee Soomaaliya"
        keywords = {"Muqdisho", "Soomaaliya"}

        passes, metadata = keyword_filter(text, required_keywords=keywords)

        assert passes
        assert "Muqdisho" in metadata["matched_keywords"]
        assert "Soomaaliya" in metadata["matched_keywords"]
        assert metadata["keyword_count"] == 2

    def test_rejects_without_match(self):
        text = "This is an English article"
        keywords = {"Muqdisho", "Soomaaliya"}

        passes, metadata = keyword_filter(text, required_keywords=keywords)

        assert not passes
        assert metadata["matched_keywords"] == []
        assert metadata["keyword_count"] == 0

    def test_case_insensitive(self):
        text = "muqdisho waa magaalo"  # lowercase
        keywords = {"Muqdisho"}  # capitalized

        passes, metadata = keyword_filter(
            text,
            required_keywords=keywords,
            case_sensitive=False
        )

        assert passes
```

---

## Best Practices

### 1. Keep Filters Fast

```python
# BAD: O(n²) complexity
def slow_filter(text, keywords):
    for word in text.split():
        for keyword in keywords:
            if keyword in word:
                return True, {}
    return False, {}

# GOOD: O(n) complexity
def fast_filter(text, keywords):
    text_lower = text.lower()
    matched = {kw for kw in keywords if kw in text_lower}
    return len(matched) > 0, {"matched": list(matched)}
```

### 2. Handle Edge Cases

```python
def robust_filter(text, threshold):
    # Handle None or empty text
    if not text or not isinstance(text, str):
        return False, {"error": "invalid_text"}

    # Handle negative threshold
    if threshold < 0:
        threshold = 0

    passes = len(text) >= threshold
    return passes, {}
```

### 3. Provide Useful Metadata

```python
def informative_filter(text, pattern):
    match = re.search(pattern, text)

    if not match:
        return False, {
            "filter_reason": "no_pattern_match",
            "pattern": pattern
        }

    return True, {
        "pattern_matched": match.group(0),
        "match_position": match.span(),
        "pattern": pattern
    }
```

### 4. Document Your Filters

```python
def well_documented_filter(
    cleaned_text: str,
    threshold: int = 50
) -> Tuple[bool, Dict[str, Any]]:
    """
    Filter out short texts below character threshold.

    This filter is useful for removing stub articles, test data, or
    incomplete scrapes that don't have enough content for meaningful analysis.

    Args:
        cleaned_text: Text after HTML/whitespace cleaning
        threshold: Minimum character count (default: 50)

    Returns:
        (passes, metadata) tuple where:
        - passes: True if len(text) >= threshold
        - metadata: Empty dict (no enrichment)

    Example:
        >>> passes, meta = well_documented_filter("Short text", threshold=20)
        >>> assert passes == False

    Note:
        Counts characters, not tokens. For token-based filtering,
        use token_count_filter instead.
    """
    passes = len(cleaned_text) >= threshold
    return passes, {}
```

---

## See Also

- [Filter Reference](../reference/filters.md) - API docs for built-in filters
- [Processing Pipelines](processing-pipelines.md) - How to use filters in pipelines
- [Architecture](../overview/architecture.md) - Filter framework design
- [Filter Framework Decision](../decisions/002-filter-framework.md) - Design rationale

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
