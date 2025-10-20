# Filters Reference

**Complete API reference for built-in data quality filters.**

**Last Updated**: 2025-10-20

---

## Overview

Filters are stateless functions that validate and enrich records during pipeline processing. All filters follow a consistent signature and return both a pass/fail boolean and optional metadata updates.

**Module**: `somali_dialect_classifier.preprocessing.filters`

**Design Philosophy**:
- **Stateless**: No side effects, thread-safe
- **Composable**: Chain multiple filters together
- **Extensible**: Easy to add custom filters
- **Informative**: Return metadata for observability

---

## Table of Contents

- [Filter Signature](#filter-signature)
- [Built-in Filters](#built-in-filters)
  - [min_length_filter](#min_length_filter)
  - [langid_filter](#langid_filter)
  - [dialect_heuristic_filter](#dialect_heuristic_filter)
  - [namespace_filter](#namespace_filter)
  - [custom_filter](#custom_filter)
- [Convenience Constructors](#convenience-constructors)
- [Usage Examples](#usage-examples)
- [Custom Filter Development](#custom-filter-development)

---

## Filter Signature

All filters follow this signature:

```python
def filter_func(
    cleaned_text: str,
    **kwargs
) -> Tuple[bool, Dict[str, Any]]:
    """
    Args:
        cleaned_text: Pre-cleaned text content
        **kwargs: Filter-specific configuration

    Returns:
        (passes, metadata_updates)
        - passes: True if record should be kept, False to reject
        - metadata_updates: Dict of fields to merge into source_metadata
    """
```

**Key Points**:
- **Input**: Cleaned text (after HTML/markup removal, whitespace normalization)
- **Returns**: Tuple of (bool, dict)
- **Stateless**: No internal state, no side effects
- **Metadata**: Can enrich records without rejecting them

---

## Built-in Filters

### min_length_filter

Rejects records below a minimum character threshold.

#### Signature

```python
def min_length_filter(
    cleaned_text: str,
    threshold: int = 50
) -> Tuple[bool, Dict[str, Any]]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cleaned_text` | `str` | Required | Pre-cleaned text content |
| `threshold` | `int` | `50` | Minimum number of characters |

#### Returns

- **passes**: `True` if `len(cleaned_text) >= threshold`, else `False`
- **metadata_updates**: `{}` (no metadata added)

#### Use Cases

- Remove stub articles with minimal content
- Filter social media posts that are too short
- Ensure minimum context for language detection
- Discard non-informative records

#### Examples

```python
from somali_dialect_classifier.preprocessing.filters import min_length_filter

# Short text - rejected
passes, meta = min_length_filter("Very short text", threshold=50)
assert passes == False
assert meta == {}

# Long text - accepted
long_text = "A" * 100
passes, meta = min_length_filter(long_text, threshold=50)
assert passes == True

# Custom threshold
passes, meta = min_length_filter("Hello world", threshold=10)
assert passes == True
```

#### Performance

- **Time Complexity**: O(1) - only computes string length
- **Memory**: O(1) - no allocations
- **Throughput**: ~10M records/second on modern hardware

#### Common Thresholds

| Source Type | Recommended Threshold | Rationale |
|-------------|----------------------|-----------|
| News Articles | 100-200 chars | Full sentences with context |
| Wikipedia | 50-100 chars | Short stubs still useful |
| Social Media | 20-50 chars | Accept short posts |
| Corpus Text | 200+ chars | Longer context for dialect |

---

### langid_filter

Detects language using heuristics and rejects non-target languages.

#### Signature

```python
def langid_filter(
    cleaned_text: str,
    allowed_langs: Set[str] = {"so"},
    confidence_threshold: float = 0.5
) -> Tuple[bool, Dict[str, Any]]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cleaned_text` | `str` | Required | Pre-cleaned text content |
| `allowed_langs` | `Set[str]` | `{"so"}` | Set of ISO 639-1 language codes |
| `confidence_threshold` | `float` | `0.5` | Minimum confidence (0-1) to accept |

#### Returns

- **passes**: `True` if detected language is in `allowed_langs` with confidence >= threshold
- **metadata_updates**:
  ```python
  {
      "detected_lang": str,      # ISO 639-1 code: "so", "en", "other", "unknown"
      "lang_confidence": float   # Confidence score (0-1), rounded to 2 decimals
  }
  ```

#### Detection Algorithm

The filter uses a heuristic approach optimized for Somali:

1. **Somali Word Matching**: Checks against 120+ common Somali words
2. **English Word Matching**: Checks against 15 common English words
3. **Script Analysis**: Detects non-Latin scripts
4. **Scoring**: Computes word frequency ratios

**Formula**:
```
somali_score = (somali_word_count / total_words)
english_score = (english_word_count / total_words)

if somali_score > english_score and somali_score > 0.1:
    detected_lang = "so"
    confidence = min(0.9, somali_score * 2)
elif english_score > 0.15:
    detected_lang = "en"
    confidence = min(0.9, english_score * 2)
else:
    detected_lang = "so" or "other" (based on script)
```

#### Use Cases

- Filter English/multilingual contamination from Somali datasets
- Identify code-switching in social media posts
- Quality control for corpus purity
- Enrich metadata with language confidence for downstream filtering

#### Examples

```python
from somali_dialect_classifier.preprocessing.filters import langid_filter

# Somali text - accepted
somali_text = "Waxaan arkay dadka badan oo socda magaalada"
passes, meta = langid_filter(somali_text, allowed_langs={"so"})
assert passes == True
assert meta["detected_lang"] == "so"
assert meta["lang_confidence"] >= 0.5

# English text - rejected
english_text = "This is an English sentence with many words"
passes, meta = langid_filter(english_text, allowed_langs={"so"})
assert passes == False
assert meta["detected_lang"] == "en"

# Custom confidence threshold
mixed_text = "Waxaan saw the movie last night"  # Code-switching
passes, meta = langid_filter(mixed_text, confidence_threshold=0.8)
# May pass or fail depending on word ratio

# Multi-language acceptance
passes, meta = langid_filter(english_text, allowed_langs={"en", "so"})
assert passes == True  # English accepted
```

#### Somali Word Vocabulary

The filter recognizes 120+ common Somali words including:

**Common Function Words**:
- `waa`, `iyo`, `oo`, `ah`, `ka`, `ku`, `la`, `si`, `ee`

**Verbs**:
- `yahay`, `tahay`, `yidhi`, `sheegayaa`, `dhaqato`

**Nouns**:
- `wadanka`, `magaalada`, `dadka`, `qofka`, `dhulka`

**Domain-Specific**:
- Sports: `kubadda`, `koob`, `ciyaaraha`
- Geography: `degaan`, `jasiirad`, `webiga`
- Politics: `dowladda`, `jamhuuriyada`, `dastuurka`

#### Performance

- **Time Complexity**: O(n) where n = number of words
- **Memory**: O(1) - uses precomputed word sets
- **Throughput**: ~50K records/second
- **Accuracy**: ~85% for pure Somali/English, lower for code-switching

#### Limitations

1. **No ML Model**: Uses heuristics, not deep learning
2. **Code-Switching**: May misclassify mixed-language text
3. **Short Texts**: Confidence drops below 20 words
4. **Dialect Variation**: May not recognize regional vocabulary

**Recommendation**: For production, consider integrating `fasttext` or `langdetect` for improved accuracy.

---

### dialect_heuristic_filter

Enriches metadata with dialect markers based on lexicon matching.

#### Signature

```python
def dialect_heuristic_filter(
    cleaned_text: str,
    ruleset: Dict[str, List[str]],
    enrich_only: bool = True
) -> Tuple[bool, Dict[str, Any]]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cleaned_text` | `str` | Required | Pre-cleaned text content |
| `ruleset` | `Dict[str, List[str]]` | Required | Mapping of dialect/topic names to marker words |
| `enrich_only` | `bool` | `True` | If `True`, always pass (enrichment only); if `False`, reject if no markers found |

#### Returns

- **passes**: `True` if markers found OR `enrich_only=True`
- **metadata_updates**:
  ```python
  {
      "dialect_markers": Dict[str, int],  # Marker counts per dialect
      "primary_dialect": str,             # Dialect with most markers
      "total_dialect_markers": int        # Total markers found
  }
  ```

#### Use Cases

- **Topic Enrichment**: Tag articles by subject (sports, politics, culture)
- **Dialect Tagging**: Mark regional language variants (Northern, Southern, etc.)
- **Domain Classification**: Categorize by domain (news, medical, legal)
- **Metadata for Downstream**: Add features for ML classification

#### Examples

##### Basic Topic Enrichment

```python
from somali_dialect_classifier.preprocessing.filters import dialect_heuristic_filter

# Define topic ruleset
topics = {
    "sports": ["kubadda", "ciyaaryahan", "koob", "gool"],
    "politics": ["dowladda", "madaxweyne", "xubnaha", "baarlamaan"],
    "culture": ["suugaan", "hees", "dhaqan", "hidde"]
}

# Sports article
sports_text = "Ciyaaryahan kubadda cagta ayaa gool dhalay xilli koowaad"
passes, meta = dialect_heuristic_filter(sports_text, topics)

assert passes == True  # Always passes in enrich_only mode
assert meta["primary_dialect"] == "sports"
assert meta["dialect_markers"]["sports"] >= 2
assert meta["total_dialect_markers"] >= 2

# Political article
politics_text = "Dowladda waxay sheegtay in xubnaha baarlamaanka ay..."
passes, meta = dialect_heuristic_filter(politics_text, topics)
assert meta["primary_dialect"] == "politics"

# Mixed content
mixed_text = "Madaxweynaha wuxuu daawatay ciyaartii kubadda"
passes, meta = dialect_heuristic_filter(mixed_text, topics)
# primary_dialect will be whichever has more markers
```

##### Strict Filtering (Reject No Markers)

```python
# Require at least one marker
passes, meta = dialect_heuristic_filter(
    "Generic text with no markers",
    ruleset=topics,
    enrich_only=False
)
assert passes == False  # Rejected
assert meta["primary_dialect"] == "unknown"
```

##### Regional Dialect Classification

```python
# Define regional dialects (example - not linguistically validated)
dialects = {
    "northern": ["xamar", "muqdisho", "berbera"],
    "southern": ["kismaayo", "jubbada", "shabeellaha"],
    "central": ["galmudug", "hiiraan"]
}

text = "Magaalada Kismaayo oo ku taalo Jubbada Hoose"
passes, meta = dialect_heuristic_filter(text, dialects)
assert meta["primary_dialect"] == "southern"
```

#### Algorithm

1. **Tokenization**: Split text into words (case-insensitive)
2. **Matching**: For each dialect ruleset, count exact word matches
3. **Scoring**: Identify dialect with highest match count
4. **Metadata**: Return counts and primary dialect

**Pseudocode**:
```
dialect_counts = {dialect: 0 for dialect in ruleset}
words = set(text.lower().split())

for dialect, markers in ruleset:
    for marker in markers:
        if marker.lower() in words:
            dialect_counts[dialect] += 1

primary_dialect = argmax(dialect_counts)
```

#### Performance

- **Time Complexity**: O(w * d * m) where w=words, d=dialects, m=markers per dialect
- **Memory**: O(w) for word set
- **Throughput**: ~10K records/second with 5 dialects × 20 markers each

#### Best Practices

1. **Curate Lexicons**: Use domain experts to build marker lists
2. **Balance Rulesets**: Ensure each dialect has similar marker counts
3. **Case-Insensitive**: Filter handles lowercasing automatically
4. **Whole Words**: Uses word boundaries, not substring matching
5. **Enrich First, Filter Later**: Use `enrich_only=True` and filter downstream based on metadata

#### Limitations

1. **Lexicon-Based**: Requires manual curation of marker words
2. **No Context**: Doesn't understand word semantics or syntax
3. **Ambiguity**: Some words may appear in multiple dialects
4. **Short Texts**: Low recall on texts with few words

---

### namespace_filter

Filters Wikipedia pages by namespace prefix.

#### Signature

```python
def namespace_filter(
    title: str,
    text: str,
    skip_prefixes: List[str]
) -> Tuple[bool, Dict[str, Any]]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str` | Required | Article/page title |
| `text` | `str` | Required | Text content (unused, for signature consistency) |
| `skip_prefixes` | `List[str]` | Required | List of namespace prefixes to reject |

#### Returns

- **passes**: `True` if title doesn't start with any skip prefix
- **metadata_updates**: `{"namespace": str}` if rejected (contains matched prefix), else `{}`

#### Use Cases

- **Wikipedia Filtering**: Remove non-article pages (Talk, User, Template, etc.)
- **Corpus Curation**: Focus on main namespace articles
- **Quality Control**: Exclude meta-pages and discussion pages

#### Wikipedia Namespaces

Common namespaces to skip:

| Prefix | Purpose | Include? |
|--------|---------|----------|
| _(none)_ | Main articles | ✅ Include |
| `Talk:` | Article discussions | ❌ Skip |
| `User:` | User pages | ❌ Skip |
| `Wikipedia:` | Project pages | ❌ Skip |
| `File:` | Media descriptions | ❌ Skip |
| `MediaWiki:` | Interface messages | ❌ Skip |
| `Template:` | Reusable templates | ❌ Skip |
| `Help:` | Help pages | ❌ Skip |
| `Category:` | Category pages | ❌ Skip |
| `Portal:` | Portal pages | ❌ Skip |
| `Draft:` | Draft articles | ⚠️ Consider |

#### Examples

```python
from somali_dialect_classifier.preprocessing.filters import namespace_filter

skip_namespaces = [
    "Talk:", "User:", "Wikipedia:", "File:",
    "Template:", "Help:", "Category:", "Portal:"
]

# Main article - accepted
passes, meta = namespace_filter(
    title="Soomaaliya",
    text="Article content...",
    skip_prefixes=skip_namespaces
)
assert passes == True
assert meta == {}

# Talk page - rejected
passes, meta = namespace_filter(
    title="Talk:Soomaaliya",
    text="Discussion content...",
    skip_prefixes=skip_namespaces
)
assert passes == False
assert meta == {"namespace": "Talk:"}

# User page - rejected
passes, meta = namespace_filter(
    title="User:JohnDoe/Sandbox",
    text="",
    skip_prefixes=skip_namespaces
)
assert passes == False
assert meta["namespace"] == "User:"
```

#### Integration with BasePipeline

```python
class WikipediaSomaliProcessor(BasePipeline):
    def _register_filters(self):
        skip_prefixes = [
            "Wikipedia:", "Talk:", "User:", "File:",
            "Template:", "Help:", "Category:", "Portal:"
        ]

        return [
            (min_length_filter, {"threshold": 50}),
            (langid_filter, {"allowed_langs": {"so"}}),
            # namespace_filter handled specially with title parameter
        ]

    def _apply_namespace_filter(self, record):
        passes, meta = namespace_filter(
            title=record["title"],
            text=record["text"],
            skip_prefixes=self.skip_prefixes
        )
        if not passes:
            self.metrics.increment("filter_rejections_namespace")
        return passes, meta
```

#### Performance

- **Time Complexity**: O(n * m) where n=prefixes, m=avg prefix length
- **Memory**: O(1)
- **Throughput**: ~100K records/second

---

### custom_filter

Generic wrapper for arbitrary filtering logic.

#### Signature

```python
def custom_filter(
    cleaned_text: str,
    predicate_func: Callable,
    metadata_key: str = "custom_filter_result"
) -> Tuple[bool, Dict[str, Any]]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cleaned_text` | `str` | Required | Pre-cleaned text content |
| `predicate_func` | `Callable` | Required | Function returning `bool` or `(bool, value)` |
| `metadata_key` | `str` | `"custom_filter_result"` | Key to store result in metadata |

#### Returns

- **passes**: Result of `predicate_func(cleaned_text)`
- **metadata_updates**: `{metadata_key: value}` if predicate returns value, else `{}`

#### Use Cases

- **Ad-Hoc Filtering**: Quick custom logic without defining new filter functions
- **Prototyping**: Test filtering ideas before formalizing
- **Complex Logic**: Wrap sophisticated predicates as filters
- **Metadata Extraction**: Compute and store derived features

#### Examples

##### Simple Boolean Predicate

```python
from somali_dialect_classifier.preprocessing.filters import custom_filter

# Define predicate
def has_urls(text):
    return "http://" in text or "https://" in text

# Use filter
text_with_url = "Visit https://example.com for more"
passes, meta = custom_filter(text_with_url, has_urls)
assert passes == True
assert meta == {}  # No metadata returned
```

##### Predicate with Value

```python
def count_numbers(text):
    count = sum(c.isdigit() for c in text)
    return count < 10, count  # (passes, value)

text = "Call me at 1234567890"
passes, meta = custom_filter(
    text,
    count_numbers,
    metadata_key="digit_count"
)
assert passes == False  # More than 10 digits
assert meta["digit_count"] == 10
```

##### Complex Filtering Logic

```python
import re

def detect_spam(text):
    spam_patterns = [
        r'click here',
        r'limited time offer',
        r'call now',
        r'\$\$\$'
    ]
    spam_count = sum(
        1 for pattern in spam_patterns
        if re.search(pattern, text, re.IGNORECASE)
    )
    is_spam = spam_count >= 2
    return not is_spam, spam_count  # Invert: pass if NOT spam

text = "CLICK HERE for a LIMITED TIME OFFER!!!"
passes, meta = custom_filter(text, detect_spam, "spam_score")
assert passes == False
assert meta["spam_score"] == 2
```

##### Metadata-Only Filter

```python
def compute_readability(text):
    words = text.split()
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    return True, round(avg_word_length, 2)  # Always pass, just enrich

text = "This is a sample text"
passes, meta = custom_filter(text, compute_readability, "avg_word_length")
assert passes == True
assert meta["avg_word_length"] > 0
```

#### Performance

- **Time Complexity**: Depends on predicate function
- **Memory**: O(1) for wrapper, depends on predicate
- **Throughput**: Varies based on predicate complexity

#### Best Practices

1. **Keep Predicates Pure**: No side effects, no state
2. **Return Tuples for Metadata**: Use `(bool, value)` when enriching
3. **Choose Descriptive Keys**: Use meaningful `metadata_key` names
4. **Document Predicates**: Add docstrings explaining logic
5. **Consider Formalization**: If predicate is reused, create dedicated filter function

---

## Convenience Constructors

Pre-configured filter chains for common source types.

### create_wikipedia_filters

```python
def create_wikipedia_filters(
    min_length: int = 50,
    skip_prefixes: List[str] = None
) -> List[Tuple[callable, Dict[str, Any]]]
```

**Returns**: Standard filter chain for Wikipedia sources

**Filters Included**:
1. `min_length_filter` (threshold=min_length)
2. `langid_filter` (allowed_langs={"so"}, confidence=0.5)

**Note**: `namespace_filter` requires title parameter, handle separately in processor.

**Example**:
```python
from somali_dialect_classifier.preprocessing.filters import create_wikipedia_filters

filters = create_wikipedia_filters(min_length=100)
# Apply in processor._register_filters()
```

### create_news_filters

```python
def create_news_filters(
    min_length: int = 50,
    dialect_ruleset: Dict[str, List[str]] = None
) -> List[Tuple[callable, Dict[str, Any]]]
```

**Returns**: Standard filter chain for news sources (BBC, VOA, etc.)

**Filters Included**:
1. `min_length_filter` (threshold=min_length)
2. `langid_filter` (allowed_langs={"so"}, confidence=0.5)
3. `dialect_heuristic_filter` (if ruleset provided, enrich_only=True)

**Example**:
```python
topics = {
    "sports": ["kubadda", "ciyaaryahan"],
    "politics": ["dowladda", "madaxweyne"]
}

filters = create_news_filters(min_length=100, dialect_ruleset=topics)
```

### create_hf_filters

```python
def create_hf_filters(
    min_length: int = 50,
    allowed_langs: Set[str] = None
) -> List[Tuple[callable, Dict[str, Any]]]
```

**Returns**: Standard filter chain for HuggingFace datasets

**Filters Included**:
1. `min_length_filter` (threshold=min_length)
2. `langid_filter` (allowed_langs=allowed_langs or {"so"}, confidence=0.5)

**Example**:
```python
filters = create_hf_filters(min_length=75, allowed_langs={"so", "en"})
```

---

## Usage Examples

### Integrating Filters in Pipelines

```python
from somali_dialect_classifier.preprocessing.base_pipeline import BasePipeline
from somali_dialect_classifier.preprocessing.filters import (
    min_length_filter,
    langid_filter,
    dialect_heuristic_filter
)

class BBCSomaliProcessor(BasePipeline):
    def _register_filters(self):
        topics = {
            "sports": ["kubadda", "ciyaaraha"],
            "politics": ["dowladda", "madaxweyne"],
            "culture": ["suugaan", "dhaqan"]
        }

        return [
            (min_length_filter, {"threshold": 100}),
            (langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.6}),
            (dialect_heuristic_filter, {"ruleset": topics, "enrich_only": True})
        ]
```

### Filter Statistics

```python
# In BasePipeline.process()
for record in records:
    cleaned_text = self._clean_text(record["text"])

    # Apply filters
    passed_all = True
    for filter_func, kwargs in self.filters:
        passes, metadata_updates = filter_func(cleaned_text, **kwargs)

        if not passes:
            # Track rejection
            filter_name = filter_func.__name__
            self.metrics.increment(f"filter_rejections_{filter_name}")
            passed_all = False
            break

        # Merge metadata
        record.setdefault("source_metadata", {}).update(metadata_updates)

    if passed_all:
        accepted_records.append(record)
```

### Custom Filter Examples

#### URL Presence Filter

```python
def has_urls_filter(cleaned_text: str, require: bool = False) -> Tuple[bool, Dict]:
    import re
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, cleaned_text)

    if require:
        passes = len(urls) > 0
    else:
        passes = len(urls) == 0  # Reject if URLs found

    return passes, {"url_count": len(urls)}
```

#### Profanity Filter

```python
def profanity_filter(cleaned_text: str, blocklist: Set[str]) -> Tuple[bool, Dict]:
    words = cleaned_text.lower().split()
    found_profanity = [word for word in words if word in blocklist]

    passes = len(found_profanity) == 0
    return passes, {"profanity_count": len(found_profanity)}
```

#### Sentence Count Filter

```python
def min_sentences_filter(cleaned_text: str, min_sentences: int = 3) -> Tuple[bool, Dict]:
    import re
    sentences = re.split(r'[.!?]+', cleaned_text)
    sentence_count = len([s for s in sentences if s.strip()])

    passes = sentence_count >= min_sentences
    return passes, {"sentence_count": sentence_count}
```

---

## Custom Filter Development

### Template

```python
def my_custom_filter(
    cleaned_text: str,
    param1: Any,
    param2: Any = default_value
) -> Tuple[bool, Dict[str, Any]]:
    """
    Brief description of what this filter does.

    Args:
        cleaned_text: Pre-cleaned text content
        param1: Description of required parameter
        param2: Description of optional parameter (default: default_value)

    Returns:
        (passes, metadata_updates)
        - passes: True if record should be kept
        - metadata_updates: Dict of fields to add to source_metadata

    Example:
        >>> passes, meta = my_custom_filter("sample text", param1=value)
        >>> passes
        True
    """
    # 1. Extract features from text
    feature = extract_feature(cleaned_text, param1, param2)

    # 2. Determine pass/fail
    passes = feature meets_criteria

    # 3. Prepare metadata
    metadata_updates = {
        "feature_name": feature,
        "other_metric": computed_value
    }

    return passes, metadata_updates
```

### Best Practices

1. **Stateless**: No internal state, no class variables
2. **Pure Functions**: Same input → same output
3. **Efficient**: Avoid expensive operations (network calls, disk I/O)
4. **Documented**: Clear docstring with examples
5. **Tested**: Unit tests with edge cases
6. **Type Hints**: Full type annotations
7. **Informative Metadata**: Add useful fields for debugging/analysis

### Testing Filters

```python
import pytest
from somali_dialect_classifier.preprocessing.filters import my_custom_filter

def test_my_custom_filter_accepts_valid():
    text = "valid input text"
    passes, meta = my_custom_filter(text, param1=value)
    assert passes == True
    assert "feature_name" in meta

def test_my_custom_filter_rejects_invalid():
    text = "invalid input"
    passes, meta = my_custom_filter(text, param1=value)
    assert passes == False

def test_my_custom_filter_metadata():
    text = "test text"
    passes, meta = my_custom_filter(text, param1=value)
    assert meta["feature_name"] == expected_value

@pytest.mark.parametrize("text,expected", [
    ("case1", True),
    ("case2", False),
    ("case3", True),
])
def test_my_custom_filter_parametrized(text, expected):
    passes, meta = my_custom_filter(text, param1=value)
    assert passes == expected
```

---

## Related Documentation

- **[Custom Filters Guide](../howto/custom-filters.md)** - Step-by-step tutorial for creating filters
- **[API Reference](api.md)** - Complete API documentation
- **[Architecture](../overview/architecture.md)** - Filter framework design
- **[Filter Framework ADR](../decisions/002-filter-framework.md)** - Design decisions

---

**Version**: 1.0.0
**Last Updated**: 2025-10-20
**Maintained By**: Somali NLP Team
**License**: MIT License
