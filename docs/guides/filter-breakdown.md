# Filter Breakdown Explanation

**Deep dive into understanding quality filter impact and optimization.**

**Last Updated**: 2025-10-27
**Audience**: Data scientists, ML engineers, pipeline developers

---

## Table of Contents

- [Why Wikipedia Shows 63.6% Quality Rate](#why-wikipedia-shows-636-quality-rate)
- [Filter Descriptions](#filter-descriptions)
- [Expected vs Actual Impact](#expected-vs-actual-impact)
- [Adjusting Filter Thresholds](#adjusting-filter-thresholds)
- [Filter Decision Tree](#filter-decision-tree)
- [Case Studies](#case-studies)

---

## Why Wikipedia Shows 63.6% Quality Rate

### The Numbers

From a typical Wikipedia run:

```
Records Extracted: 15,136
Records Written: 9,623
Quality Pass Rate: 63.6%

Filter Breakdown:
  - min_length_filter: 4,128 rejected (74.9% of filtered)
  - langid_filter: 1,185 rejected (21.5% of filtered)
  - empty_after_cleaning: 200 rejected (3.6% of filtered)
Total Filtered: 5,513
```

### Why This Is Normal

Wikipedia contains many **stub articles** - very short pages with minimal content:

**Example Stub**:
```
Magaalada Berbera waa magaalo ku taala Somaliland.
(Translation: The city of Berbera is a city located in Somaliland.)
```

**Character count**: 55 characters
**Filter threshold**: 50 characters minimum
**Result**: Passes, but barely

**Shorter example**:
```
Waa magaalo.
(Translation: It is a city.)
```

**Character count**: 13 characters
**Result**: Rejected by min_length_filter

### Distribution Analysis

Wikipedia article length distribution:

```
0-50 chars:    27.3% (stubs, rejected)
50-100 chars:  15.8% (very short articles)
100-500 chars: 31.2% (short articles)
500-2000 chars: 18.5% (medium articles)
2000+ chars:    7.2% (long articles)
```

**Why we filter short articles**:
1. Insufficient context for dialect classification
2. Often just definitions or placeholders
3. Limited training value for ML models
4. May be translation stubs or redirects

### Comparison with Other Sources

| Source | Quality Pass Rate | Reason for Rate |
|--------|------------------|-----------------|
| **Wikipedia** | 60-70% | Many stubs, strict length filter |
| **BBC Somali** | 75-90% | Professional journalism, consistent quality |
| **HuggingFace mC4** | 60-80% | Web-crawled, variable quality |
| **Språkbanken** | 80-95% | Curated linguistic corpus |

**Takeaway**: Wikipedia's lower rate is expected and not a quality issue.

---

## Filter Descriptions

### 1. min_length_filter

**Purpose**: Remove texts with insufficient content

**How It Works**:
```python
def min_length_filter(cleaned_text: str, threshold: int = 50) -> Tuple[bool, Dict]:
    """
    Reject if len(cleaned_text) < threshold.

    Args:
        cleaned_text: Text after HTML/markup removal
        threshold: Minimum character count (default: 50)

    Returns:
        (passes, metadata)
    """
    passes = len(cleaned_text) >= threshold
    return passes, {}
```

**Threshold Guidelines**:

| Source Type | Recommended Threshold | Rationale |
|-------------|----------------------|-----------|
| **News Articles** | 100-200 | Full sentences with context |
| **Wikipedia** | 50-100 | Short stubs still useful |
| **Social Media** | 20-50 | Accept short posts |
| **Corpus Text** | 200+ | Longer context for dialect |

**Current Settings**:
- Wikipedia: 50 characters
- BBC: 100 characters
- HuggingFace: 75 characters
- Språkbanken: 50 characters

**Impact Example**:

```
Text: "Soomaaliya waa dal."
Length: 20 characters
Threshold: 50
Result: Rejected

Text: "Soomaaliya waa dal ku taala geeska Afrika. Waxay leedahay taariikh dheer oo ah mid xiiso leh."
Length: 95 characters
Threshold: 50
Result: Passes
```

**When to Adjust**:
- **Lower threshold** if you need more data volume and short texts are acceptable
- **Raise threshold** if you need longer context for classification tasks

**Typical Rejection Rate**:
- Wikipedia: 30-50%
- News sources: 5-15%
- Social media: 10-25%

---

### 2. langid_filter

**Purpose**: Detect and remove non-Somali text

**How It Works**:

```python
def langid_filter(
    cleaned_text: str,
    allowed_langs: Set[str] = {"so"},
    confidence_threshold: float = 0.5
) -> Tuple[bool, Dict]:
    """
    Detect language and reject if not in allowed set.

    Uses heuristic approach:
    1. Count Somali word markers
    2. Count English word markers
    3. Detect non-Latin scripts
    4. Compute confidence score

    Returns:
        (passes, {"detected_lang": str, "lang_confidence": float})
    """
```

**Detection Algorithm**:

1. **Somali Word Matching**:
   - Check against 120+ common Somali words
   - Examples: `waa`, `iyo`, `oo`, `yahay`, `wadanka`

2. **English Word Matching**:
   - Check against common English words
   - Examples: `the`, `is`, `and`, `of`, `to`

3. **Scoring**:
   ```python
   somali_score = somali_word_count / total_words
   english_score = english_word_count / total_words

   if somali_score > english_score and somali_score > 0.1:
       detected_lang = "so"
       confidence = min(0.9, somali_score * 2)
   elif english_score > 0.15:
       detected_lang = "en"
       confidence = min(0.9, english_score * 2)
   else:
       detected_lang = "other" or "so" (based on script)
   ```

**Example Classifications**:

```
Text: "Waxaan arkay dadka badan oo socda magaalada"
Detection: Somali (confidence: 0.85)
Result: Passes

Text: "This is an English sentence with many words"
Detection: English (confidence: 0.88)
Result: Rejected

Text: "Waxaan saw the movie last night"
Detection: Somali (confidence: 0.42) or English (confidence: 0.40)
Result: Depends on threshold
```

**Confidence Threshold Impact**:

| Threshold | Effect | Use Case |
|-----------|--------|----------|
| 0.3 | Very permissive | Accept code-switching, low-resource scenarios |
| 0.5 | Balanced (default) | General purpose |
| 0.7 | Strict | High-purity corpus, minimal contamination |
| 0.9 | Very strict | Only obviously Somali text |

**False Positives/Negatives**:

**False Negative** (Incorrectly rejected):
```
Text: "2025-ka waxaa la abaabulayaa shir caalami ah"
Issue: Date prefix "2025-ka" may confuse detector
Solution: Lower threshold or improve word list
```

**False Positive** (Incorrectly accepted):
```
Text: "Somalia is a country in the Horn of Africa"
Issue: Contains "Somalia" which matches word list
Solution: Raise threshold or improve detection
```

**Typical Rejection Rate**:
- Wikipedia: 15-25% (some English redirects/templates)
- BBC: 5-10% (occasional multilingual content)
- Web corpus: 20-40% (high contamination)

---

### 3. empty_after_cleaning

**Purpose**: Remove texts that become empty after markup/HTML removal

**How It Works**:

```python
def empty_after_cleaning_filter(text: str) -> Tuple[bool, Dict]:
    """
    Check if text is empty or only whitespace after cleaning.

    Cleaning steps:
    1. Remove HTML tags
    2. Remove URLs
    3. Remove excessive whitespace
    4. Strip leading/trailing whitespace

    Returns:
        (passes, {}) where passes=False if empty
    """
    cleaned = clean_text(text)
    passes = len(cleaned.strip()) > 0
    return passes, {}
```

**Common Causes of Empty Text**:

1. **Pure HTML Pages**:
   ```html
   <div class="template">
     <img src="logo.png" alt="Logo">
   </div>
   ```
   After cleaning: `` (empty)

2. **Navigation/Menu Pages**:
   ```html
   <nav>
     <a href="/page1">Link 1</a>
     <a href="/page2">Link 2</a>
   </nav>
   ```
   After cleaning: `` (empty, only links)

3. **Redirect Pages**:
   ```
   #REDIRECT [[Actual Article Name]]
   ```
   After cleaning: `` (empty, just redirect markup)

4. **Image Gallery Pages**:
   ```html
   <gallery>
     <img src="1.jpg">
     <img src="2.jpg">
   </gallery>
   ```
   After cleaning: `` (empty, only images)

**Source-Specific Patterns**:

**Wikipedia**:
- Template pages
- Redirect pages
- Category pages
- File description pages

**Web Corpus**:
- Cookie notices
- Login forms
- Error pages
- Advertisement placeholders

**Typical Rejection Rate**:
- Wikipedia: 3-5%
- BBC: 1-2%
- Web corpus: 5-10%

---

### 4. namespace_filter (Wikipedia Only)

**Purpose**: Remove non-article Wikipedia pages

**How It Works**:

```python
def namespace_filter(
    title: str,
    text: str,
    skip_prefixes: List[str]
) -> Tuple[bool, Dict]:
    """
    Check if title starts with namespace prefix.

    Args:
        title: Page title (e.g., "Talk:Soomaaliya")
        skip_prefixes: List of namespace prefixes to reject

    Returns:
        (passes, metadata)
    """
    for prefix in skip_prefixes:
        if title.startswith(prefix):
            return False, {"namespace": prefix}
    return True, {}
```

**Wikipedia Namespaces**:

| Namespace | Example | Purpose | Include? |
|-----------|---------|---------|----------|
| _(main)_ | `Soomaaliya` | Encyclopedia articles | ✅ Yes |
| `Talk:` | `Talk:Soomaaliya` | Article discussions | ❌ No |
| `User:` | `User:JohnDoe` | User profile pages | ❌ No |
| `Wikipedia:` | `Wikipedia:About` | Project meta pages | ❌ No |
| `File:` | `File:Flag.png` | Media descriptions | ❌ No |
| `Template:` | `Template:Infobox` | Reusable templates | ❌ No |
| `Help:` | `Help:Editing` | Help documentation | ❌ No |
| `Category:` | `Category:Cities` | Category pages | ❌ No |

**Impact**:

```
Total Wikipedia pages: 100,000
Main namespace articles: 60,000 (60%)
Non-article pages: 40,000 (40%)

After namespace filtering:
  Kept: 60,000
  Rejected: 40,000
```

**Typical Rejection Rate**: 30-45% of total pages

---

## Expected vs Actual Impact

### Filter Cascade Effect

Filters are applied **sequentially**. Order matters!

```
Input: 15,136 records

Filter 1 (min_length):
  Rejected: 4,128
  Remaining: 11,008

Filter 2 (langid):
  Rejected: 1,185
  Remaining: 9,823

Filter 3 (empty_after_cleaning):
  Rejected: 200
  Remaining: 9,623

Output: 9,623 records (63.6% pass rate)
```

**Key Insight**: Later filters operate on already-filtered data, so their absolute rejection counts are lower.

### Expected Impact by Source

#### Wikipedia

| Filter | Expected Rejection % | Actual (Typical) | Reason for Difference |
|--------|---------------------|------------------|---------------------|
| namespace | 30-40% | 35% | Consistent |
| min_length | 20-30% | 27% | Many stubs |
| langid | 10-20% | 8% | Better than expected |
| empty | 3-5% | 1.3% | Good cleaning |
| **Total** | **50-70%** | **63.6%** | **Within expected range** |

#### BBC Somali

| Filter | Expected Rejection % | Actual (Typical) | Reason for Difference |
|--------|---------------------|------------------|---------------------|
| min_length | 5-10% | 7% | Professional content |
| langid | 5-10% | 6% | Occasional English |
| empty | 1-2% | 1% | Clean HTML parsing |
| **Total** | **10-25%** | **14%** | **Good quality source** |

#### HuggingFace mC4

| Filter | Expected Rejection % | Actual (Typical) | Reason for Difference |
|--------|---------------------|------------------|---------------------|
| min_length | 15-25% | 22% | Variable web content |
| langid | 20-35% | 28% | Web contamination |
| empty | 5-10% | 7% | Some scraped junk |
| **Total** | **35-55%** | **48%** | **Web corpus typical** |

---

## Adjusting Filter Thresholds

### Decision Framework

**Question 1: Do I need more data volume?**
- **Yes** → Consider lowering thresholds
- **No** → Keep current thresholds or raise for higher quality

**Question 2: Is downstream task sensitive to text length?**
- **Yes** (e.g., long-form classification) → Raise min_length
- **No** (e.g., short-text sentiment) → Lower min_length

**Question 3: Can my model handle code-switching?**
- **Yes** → Lower langid confidence threshold
- **No** → Raise langid confidence threshold

**Question 4: Is data diversity more important than purity?**
- **Yes** → Accept more borderline cases
- **No** → Be strict on all filters

### Adjustment Examples

#### Scenario 1: Need More Training Data

**Goal**: Increase Wikipedia records from 9,623 to ~12,000

**Current**: min_length threshold = 50 characters

**Experiment**:
```python
# Test with threshold = 30
results = test_filter_threshold("min_length", threshold=30)

# Results:
#   Records: 12,450 (+29%)
#   Quality check: Manual review of 100 samples
#     - Acceptable: 88%
#     - Too short: 12%

# Decision: Adopt threshold=30 for Wikipedia
```

**Implementation**:
```python
class WikipediaSomaliProcessor(BasePipeline):
    def _register_filters(self):
        return [
            (min_length_filter, {"threshold": 30}),  # Changed from 50
            (langid_filter, {"allowed_langs": {"so"}}),
        ]
```

#### Scenario 2: Reduce Language Contamination

**Goal**: Remove more borderline English text from corpus

**Current**: langid confidence = 0.5

**Experiment**:
```python
# Test with confidence = 0.7
results = test_filter_threshold("langid", confidence_threshold=0.7)

# Results:
#   Additional rejections: 8.2%
#   False negative check: 3 Somali texts incorrectly rejected per 1000
#   Contamination reduction: 45% fewer English texts

# Decision: Adopt confidence=0.7 for web corpus sources
```

#### Scenario 3: Balance Volume and Quality

**Goal**: Find optimal tradeoff for BBC source

**Current**: min_length = 100, langid = 0.5

**Grid Search**:
```python
thresholds = {
    "min_length": [50, 75, 100, 150],
    "langid_confidence": [0.4, 0.5, 0.6, 0.7]
}

best_config = grid_search(thresholds, target_volume=5000, min_quality=0.85)

# Best result:
#   min_length: 75
#   langid_confidence: 0.6
#   Records: 5,234
#   Quality: 87%
```

### Validation Workflow

```python
def validate_threshold_change(
    filter_name: str,
    old_value: Any,
    new_value: Any,
    sample_size: int = 1000
):
    """
    Validate proposed threshold change.

    Steps:
    1. Run pipeline with new threshold on sample
    2. Compare record count vs. baseline
    3. Manual quality check on random sample
    4. Check downstream task performance
    5. Generate recommendation report

    Returns:
        ValidationReport with recommendation
    """
```

**Validation Checklist**:
- [ ] Record count change within acceptable range (-10% to +50%)
- [ ] Manual quality check of 100 random samples (>85% acceptable)
- [ ] No increase in obviously bad records
- [ ] Downstream model performance not degraded
- [ ] Stakeholder approval for significant changes

---

## Filter Decision Tree

### For Each Record

```
Start
  │
  ├─ Is text empty after cleaning?
  │    Yes ─▶ [REJECT: empty_after_cleaning]
  │    No ─▶ Continue
  │
  ├─ Is title in excluded namespace? (Wikipedia only)
  │    Yes ─▶ [REJECT: namespace_filter]
  │    No ─▶ Continue
  │
  ├─ Is text length < min_length threshold?
  │    Yes ─▶ [REJECT: min_length_filter]
  │    No ─▶ Continue
  │
  ├─ Detect language
  │    │
  │    ├─ Language not in allowed_langs?
  │    │    Yes ─▶ [REJECT: langid_filter]
  │    │    No ─▶ Continue
  │    │
  │    ├─ Confidence < confidence_threshold?
  │    │    Yes ─▶ [REJECT: langid_filter]
  │    │    No ─▶ Continue
  │
  └─ All filters passed ─▶ [ACCEPT: Write to silver dataset]
```

### Optimization: Short-Circuit Early

```python
# Apply cheapest filters first to reject quickly
filter_order = [
    (empty_after_cleaning, {}),         # O(1) - cheapest
    (min_length_filter, {"threshold": 50}),  # O(1) - very cheap
    (langid_filter, {"confidence_threshold": 0.5}),  # O(n) - expensive
]

# This order minimizes wasted computation on records
# that would be rejected by cheaper filters
```

---

## Case Studies

### Case Study 1: Wikipedia Quality Optimization

**Initial State**:
```
Records extracted: 15,136
Records written: 6,845
Quality pass rate: 45.2%

Filter breakdown:
  - min_length (threshold=100): 6,234 rejected
  - langid (confidence=0.7): 1,857 rejected
  - empty: 200 rejected
```

**Problem**: Too aggressive filtering, losing useful short articles

**Analysis**:
- Reviewed 200 rejected records
- Found 65% were acceptable quality despite < 100 chars
- Many were valid geographic stubs, biographical entries

**Solution**:
```python
# Lower min_length to 50 for Wikipedia
# Lower langid confidence to 0.5

New results:
  Records written: 9,623 (+40%)
  Quality pass rate: 63.6%
  Manual quality check: 89% acceptable (sample of 100)
```

**Outcome**: Significantly more data with acceptable quality

---

### Case Study 2: BBC Language Contamination

**Initial State**:
```
Records extracted: 1,245
Records written: 1,068
Quality pass rate: 85.8%

Filter breakdown:
  - min_length: 89 rejected
  - langid: 74 rejected
  - empty: 14 rejected
```

**Problem**: Manual review found 12% of written records contained English text

**Analysis**:
- Current langid confidence: 0.5
- Many borderline cases (Somali with English names/terms)
- Acceptable for most use cases, but problematic for pure Somali corpus

**Solution**:
```python
# Raise langid confidence to 0.7 for BBC

New results:
  Records written: 945 (-11.5%)
  Quality pass rate: 75.9%
  English contamination: 2.8% (down from 12%)
```

**Outcome**: Purer corpus, acceptable volume reduction

---

### Case Study 3: HuggingFace Corpus Balancing

**Initial State**:
```
Records fetched: 50,000
Records written: 28,345
Quality pass rate: 56.7%

Filter breakdown:
  - min_length (threshold=75): 11,234 rejected
  - langid (confidence=0.5): 9,876 rejected
  - empty: 545 rejected
```

**Problem**: Need 40,000+ records for training, but maintain quality

**Experiments**:

**Option A**: Lower min_length to 50
```
Records written: 35,678 (+26%)
Quality pass rate: 71.4%
Manual check: 81% acceptable (below target of 85%)
```

**Option B**: Lower langid confidence to 0.4
```
Records written: 34,123 (+20%)
Quality pass rate: 68.2%
Manual check: 76% acceptable (too low)
```

**Option C**: Increase fetch size to 70,000, keep filters
```
Records written: 39,683 (+40%)
Quality pass rate: 56.7% (unchanged)
Manual check: 88% acceptable (good)
```

**Solution**: Adopted Option C - more source data rather than looser filters

**Outcome**: Met volume target while maintaining quality

---

## Related Documentation

- [Filters API Reference](../reference/filters.md) - Complete filter documentation
- [Custom Filters Guide](../howto/custom-filters.md) - Creating new filters
- [Metrics Reference](../reference/metrics.md) - Understanding quality metrics
- [Dashboard User Guide](dashboard-user-guide.md) - Interpreting dashboard

---

**Have Questions?**
Open an issue with the `filters` label or consult the [Troubleshooting Guide](../howto/troubleshooting.md).
