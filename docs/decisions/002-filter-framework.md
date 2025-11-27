# ADR 002: Filter Framework Implementation

**Architectural Decision Record documenting Principal MLE feedback implementation for filter framework and processors.**

**Last Updated:** 2025-11-21

This document outlines the implementation of the Principal MLE's feedback on silver floor hooks, filter framework, and HuggingFace processor.

## Overview

**Status**: ✅ **COMPLETE** - All components implemented and tested

### Completed Components

1. ✅ **Filter Framework** ([filters.py](src/somali_dialect_classifier/preprocessing/filters.py))
2. ✅ **BasePipeline Hook Interface** ([base_pipeline.py](src/somali_dialect_classifier/preprocessing/base_pipeline.py))
3. ✅ **Filter Statistics Logging** with Counter
4. ✅ **Wikipedia Processor Retrofit** with filters
5. ✅ **BBC Processor Retrofit** with filters and topic enrichment
6. ✅ **HuggingFaceSomaliProcessor Implementation** with streaming support
7. ✅ **Comprehensive Unit Tests** for all filters ([test_filters.py](tests/test_filters.py))
8. ✅ **Integration Tests** for Wikipedia, BBC, and HF processors
9. ✅ **HF Processor Tests** with fixtures ([test_hf_processor.py](tests/test_hf_processor.py), [test_hf_integration.py](tests/test_hf_integration.py))
10. ✅ **Configuration Externalization** via environment variables
11. ✅ **Documentation** - HUGGINGFACE_DATASETS.md, HUGGINGFACE_DATA_FLOW.md

### Recent Principal MLE Review Fixes

1. ✅ **BUG FIX**: `HuggingFaceSomaliProcessor.process()` now raises `ValueError` instead of returning `None` when all records filtered
2. ✅ **HIGH RISK FIX**: `BasePipeline` default `batch_size` changed from `None` to `5000` to prevent OOM on large sources
3. ✅ **RISK FIX**: HF source slug changed to filesystem-friendly format (no spaces/parentheses)
4. ✅ **RISK FIX**: Contract tests made tolerant of missing optional `datasets` library
5. ✅ **RISK FIX**: BBC scraper hardened with semantic selectors (replaced transient CSS classes)
6. ✅ **RISK FIX**: BBC scraper now logs warnings on empty text extraction

---

---

## Table of Contents

- [Overview](#overview)
  - [Completed Components](#completed-components)
  - [Recent Principal MLE Review Fixes](#recent-principal-mle-review-fixes)
- [1. Silver Floor Hooks - Filter Framework ✅](#1-silver-floor-hooks-filter-framework-)
  - [Architecture](#architecture)
  - [Implemented Filters](#implemented-filters)
    - [1. `min_length_filter(cleaned_text, threshold=50)`](#1-minlengthfiltercleanedtext-threshold50)
    - [2. `langid_filter(cleaned_text, allowed_langs={"so"}, confidence_threshold=0.5)`](#2-langidfiltercleanedtext-allowedlangsso-confidencethreshold05)
    - [3. `topic_lexicon_enrichment_filter(cleaned_text, ruleset, enrich_only=True)`](#3-topiclexiconenrichmentfiltercleanedtext-ruleset-enrichonlytrue)
    - [4. `namespace_filter(title, text, skip_prefixes)`](#4-namespacefiltertitle-text-skipprefixes)
    - [5. `custom_filter(cleaned_text, predicate_func, metadata_key)`](#5-customfiltercleanedtext-predicatefunc-metadatakey)
  - [Convenience Constructors](#convenience-constructors)
- [2. BasePipeline Integration ✅](#2-basepipeline-integration-)
  - [Hook Interface](#hook-interface)
  - [Execution Flow in `process()`](#execution-flow-in-process)
  - [Logging Output](#logging-output)
- [3. Retrofitted Processors ✅](#3-retrofitted-processors-)
  - [Wikipedia Processor](#wikipedia-processor)
  - [BBC Processor](#bbc-processor)
- [4. HuggingFace Datasets Processor ⏳](#4-huggingface-datasets-processor-)
  - [Architecture](#architecture)
  - [Method Implementations](#method-implementations)
    - [`download()` - Manifest Generation](#download-manifest-generation)
    - [`extract()` - Streaming Materialization](#extract-streaming-materialization)
    - [`_extract_records()` - Replay JSONL](#extractrecords-replay-jsonl)
    - [`_register_filters()` - Standard HF Filters](#registerfilters-standard-hf-filters)
  - [Usage Example](#usage-example)
- [5. Testing Strategy ⏳](#5-testing-strategy-)
  - [Unit Tests for Filters](#unit-tests-for-filters)
  - [Integration Tests](#integration-tests)
  - [HF Processor Smoke Tests](#hf-processor-smoke-tests)
- [6. Configuration & Best Practices](#6-configuration-best-practices)
  - [Externalizing Filter Thresholds](#externalizing-filter-thresholds)
  - [MLflow Integration](#mlflow-integration)
  - [Data Quality Assertions](#data-quality-assertions)
- [7. Documentation Updates](#7-documentation-updates)
  - [README Section (to be added)](#readme-section-to-be-added)
- [Data Quality Filters](#data-quality-filters)
  - [Default Filters](#default-filters)
  - [Custom Filters](#custom-filters)
  - [Filter Statistics](#filter-statistics)
  - [Configuration](#configuration)
- [Summary](#summary)
  - [✅ All Tasks Complete](#-all-tasks-complete)
  - [Key Achievements](#key-achievements)
  - [Outstanding Items (Future Work)](#outstanding-items-future-work)

---

## 1. Silver Floor Hooks - Filter Framework ✅

### Architecture

**Location**: `src/somali_dialect_classifier/preprocessing/filters.py`

All filters follow a **stateless function signature**:

```python
def filter_func(cleaned_text: str, **kwargs) -> Tuple[bool, Dict[str, Any]]:
    """
    Args:
        cleaned_text: Post-cleaning text
        **kwargs: Filter-specific parameters

    Returns:
        (passes, metadata_updates)
        - passes: True if record should be kept
        - metadata_updates: Dict to merge into record metadata
    """
    pass
```

### Implemented Filters

#### 1. `min_length_filter(cleaned_text, threshold=50)`
- Rejects records below character threshold
- **Returns**: `(len(text) >= threshold, {})`
- **Use case**: Remove stub articles, test data

#### 2. `langid_filter(cleaned_text, allowed_langs={"so"}, confidence_threshold=0.5)`
- Detects language using heuristics (Somali word lists vs English)
- **Returns**: `(lang in allowed_langs and conf >= threshold, {"detected_lang": str, "lang_confidence": float})`
- **Enriches**: Adds language detection metadata
- **Use case**: Filter out English/mixed-language content

#### 3. `topic_lexicon_enrichment_filter(cleaned_text, ruleset, enrich_only=True)`
- Matches text against topic lexicons for enrichment (NOT dialect classification)
- **Returns**: `(passes, {"dialect_markers": {...}, "primary_dialect": str})` (field names unchanged for compatibility)
- **Enrichment mode** (`enrich_only=True`): Always passes, adds metadata
- **Filter mode** (`enrich_only=False`): Rejects if no markers found
- **Use case**: Topic classification (sports/politics), metadata enrichment for downstream analysis
- **Note**: Previously named `dialect_heuristic_filter` (renamed 2025-11-13)

#### 4. `namespace_filter(title, text, skip_prefixes)`
- Wikipedia-specific: rejects pages by title prefix
- **Returns**: `(not starts_with_prefix, {"namespace": str} if rejected)`
- **Use case**: Skip "Talk:", "User:", "Template:" pages

#### 5. `custom_filter(cleaned_text, predicate_func, metadata_key)`
- Generic wrapper for ad-hoc predicates
- **Use case**: One-off filtering without defining new functions

### Convenience Constructors

```python
# Pre-configured filter chains for each source type
filters = create_wikipedia_filters(min_length=50, skip_prefixes=[...])
filters = create_news_filters(min_length=50, dialect_ruleset={...})
filters = create_hf_filters(min_length=50, allowed_langs={"so"})
```

---

## 2. BasePipeline Integration ✅

### Hook Interface

**Location**: `src/somali_dialect_classifier/preprocessing/base_pipeline.py`

```python
class BasePipeline(DataProcessor, ABC):
    def __init__(self, source, log_frequency, batch_size, force):
        ...
        # Record filters for quality control
        self.record_filters: List[Tuple[Callable, Dict[str, Any]]] = []
        self._register_filters()  # Subclasses override

    def _register_filters(self) -> None:
        """Subclasses override to append filters."""
        pass  # Base: no filters by default
```

### Execution Flow in `process()`

```python
def process(self) -> Path:
    filter_stats = Counter()  # Track drop reasons

    for raw_record in self._extract_records():
        cleaned = self.text_cleaner.clean(raw_record.text)

        if not cleaned:
            filter_stats["empty_after_cleaning"] += 1
            continue

        # Execute filters in sequence
        filter_metadata = {}
        passed_all_filters = True

        for filter_func, filter_kwargs in self.record_filters:
            passes, metadata_updates = filter_func(cleaned, **filter_kwargs)

            if not passes:
                filter_stats[f"filtered_by_{filter_func.__name__}"] += 1
                self.logger.debug(f"Filtered '{record.title}' by {filter_func.__name__}")
                passed_all_filters = False
                break

            filter_metadata.update(metadata_updates)  # Accumulate enrichments

        if not passed_all_filters:
            continue

        # Merge filter metadata into record
        merged_metadata = {**source_meta, **raw_record.metadata, **filter_metadata}

        # Build silver record with enriched metadata
        record = build_silver_record(..., source_metadata=merged_metadata)
```

### Logging Output

```
============================================================
Processing complete: 8543 records
Filtered: 2157 records
Filter statistics:
  filtered_by_min_length_filter: 1204 records
  filtered_by_langid_filter: 953 records
  empty_after_cleaning: 0 records
============================================================
```

**Benefits**:
- **Audit trail**: Per-filter drop counts
- **Debugging**: Debug logs show which records failed which filters
- **Graceful degradation**: Filter exceptions logged as warnings, don't fail pipeline

---

## 3. Retrofitted Processors ✅

### Wikipedia Processor

**Location**: `src/somali_dialect_classifier/preprocessing/wikipedia_somali_processor.py`

```python
def _register_filters(self) -> None:
    from somali_dialect_classifier.preprocessing.filters import (
        min_length_filter,
        langid_filter
    )

    self.record_filters.append((min_length_filter, {"threshold": 50}))
    self.record_filters.append((langid_filter, {
        "allowed_langs": {"so"},
        "confidence_threshold": 0.5
    }))
```

**Effect**:
- Removes stub articles (<50 chars)
- Filters out English/non-Somali pages
- Metadata enriched with `detected_lang`, `lang_confidence`

### BBC Processor

**Location**: `src/somali_dialect_classifier/preprocessing/bbc_somali_processor.py`

```python
def _register_filters(self) -> None:
    from somali_dialect_classifier.preprocessing.filters import (
        min_length_filter,
        langid_filter,
        topic_lexicon_enrichment_filter
    )

    self.record_filters.append((min_length_filter, {"threshold": 50}))
    self.record_filters.append((langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.5}))

    topic_lexicons = {
        "sports": ["kubadda", "ciyaaryahan", "kooxda", "tartanka"],
        "politics": ["xukuumad", "madaxweyne", "baarlamaan", "doorasho"],
        "economy": ["dhaqaale", "ganacsiga", "suuq", "lacagta"],
    }

    self.record_filters.append((topic_lexicon_enrichment_filter, {
        "ruleset": topic_lexicons,
        "enrich_only": True  # Don't filter, just enrich
    }))
```

**Effect**:
- Same length/language filtering as Wikipedia
- **Topic enrichment**: Adds `{"dialect_markers": {"sports": 2, "politics": 0, ...}, "primary_dialect": "sports"}` (field names use "dialect" for compatibility, but represent topics)
- Useful for downstream dialect scoring models
- `enrich_only=True` means articles pass even without matches

---

## 4. HuggingFace Datasets Processor ⏳

**Status**: Design complete, implementation pending

### Architecture

```python
class HuggingFaceSomaliProcessor(BasePipeline):
    """
    Processor for HuggingFace datasets with streaming support.

    Key features:
    - Streaming to handle large datasets (mc4, oscar, etc.)
    - Batched JSONL materialization for restart-ability
    - Flexible field mapping for diverse schemas
    - Manifest tracking for versioning
    """

    def __init__(
        self,
        dataset_name: str,  # e.g., "mc4"
        config_name: str,   # e.g., "so" for Somali subset
        split: str = "train",
        streaming_filters: Dict[str, Any] = None,  # Server-side pushdown
        metadata_fields: Dict[str, str] = None,    # Field mapping
        batch_size: int = 10000,
        force: bool = False
    ):
        super().__init__(source=f"HF-{dataset_name}", force=force)
        self.dataset_name = dataset_name
        self.config_name = config_name
        self.split = split
        self.streaming_filters = streaming_filters or {}
        self.metadata_fields = metadata_fields or {
            "url": "url",
            "date_published": "timestamp",
        }
        self.batch_size_hf = batch_size

        # File paths
        self.manifest_file = self.raw_dir / "manifest.json"
        # staging_dir contains batch-####.jsonl files
```

### Method Implementations

#### `download()` - Manifest Generation

```python
def download(self) -> Path:
    """
    Write manifest with dataset parameters (no actual download).

    Returns:
        Path to manifest file
    """
    self.raw_dir.mkdir(parents=True, exist_ok=True)

    # Check if manifest exists and matches
    if self.manifest_file.exists() and not self.force:
        with open(self.manifest_file, 'r') as f:
            cached = json.load(f)

        # Validate parameters match
        if (cached["dataset_name"] == self.dataset_name and
            cached["config_name"] == self.config_name and
            cached["split"] == self.split):
            self.logger.info(f"Manifest already exists: {self.manifest_file}")
            return self.manifest_file

    manifest = {
        "dataset_name": self.dataset_name,
        "config_name": self.config_name,
        "split": self.split,
        "streaming_filters": self.streaming_filters,
        "metadata_fields": self.metadata_fields,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "date_accessed": self.date_accessed,
    }

    with open(self.manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    self.logger.info(f"Manifest written: {self.manifest_file}")
    return self.manifest_file
```

#### `extract()` - Streaming Materialization

```python
def extract(self) -> Path:
    """
    Stream dataset and materialize to batched JSONL files.

    Returns:
        Path to staging directory containing batch-####.jsonl files
    """
    from datasets import load_dataset

    self.staging_dir.mkdir(parents=True, exist_ok=True)

    # Check if staging already done
    existing_batches = list(self.staging_dir.glob("batch-*.jsonl"))
    if existing_batches and not self.force:
        self.logger.info(f"Staging exists: {len(existing_batches)} batches")
        return self.staging_dir

    # Load in streaming mode
    self.logger.info(f"Loading {self.dataset_name} ({self.config_name}, {self.split}) in streaming mode...")

    dataset = load_dataset(
        self.dataset_name,
        self.config_name,
        split=self.split,
        streaming=True,
        **self.streaming_filters  # e.g., {"language": "so"} for server-side filtering
    )

    # Stream and batch
    batch_num = 0
    batch = []
    total_rows = 0

    for row in tqdm(dataset, desc="Streaming dataset", unit=" rows"):
        batch.append(row)
        total_rows += 1

        if len(batch) >= self.batch_size_hf:
            # Write batch to JSONL
            batch_file = self.staging_dir / f"batch-{batch_num:04d}.jsonl"
            with open(batch_file, 'w') as f:
                for item in batch:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            self.logger.info(f"Wrote batch {batch_num} ({len(batch)} rows)")
            batch_num += 1
            batch = []

    # Write final batch
    if batch:
        batch_file = self.staging_dir / f"batch-{batch_num:04d}.jsonl"
        with open(batch_file, 'w') as f:
            for item in batch:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        self.logger.info(f"Wrote final batch {batch_num} ({len(batch)} rows)")

    self.logger.info(f"Streaming complete: {total_rows} rows in {batch_num+1} batches")
    return self.staging_dir
```

#### `_extract_records()` - Replay JSONL

```python
def _extract_records(self) -> Iterator[RawRecord]:
    """
    Replay records from staged JSONL files.

    Yields:
        RawRecord objects with mapped fields
    """
    batch_files = sorted(self.staging_dir.glob("batch-*.jsonl"))

    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            for line in f:
                row = json.loads(line)

                # Extract fields using mapping
                title = row.get("title", row.get("id", "Untitled"))
                text = row.get("text", "")
                url = row.get(self.metadata_fields.get("url", "url"), "")

                # Build metadata from mapped fields
                metadata = {}
                for meta_key, row_key in self.metadata_fields.items():
                    if row_key in row and meta_key not in ["title", "text", "url"]:
                        metadata[meta_key] = row[row_key]

                yield RawRecord(
                    title=title,
                    text=text,
                    url=url,
                    metadata=metadata
                )
```

#### `_register_filters()` - Standard HF Filters

```python
def _register_filters(self) -> None:
    """Register standard filters for HuggingFace datasets."""
    from somali_dialect_classifier.preprocessing.filters import create_hf_filters

    # Use convenience constructor
    for filter_func, kwargs in create_hf_filters(min_length=50):
        self.record_filters.append((filter_func, kwargs))
```

### Usage Example

```python
# Example: Process mc4 Somali subset
processor = HuggingFaceSomaliProcessor(
    dataset_name="mc4",
    config_name="so",  # Somali
    split="train",
    streaming_filters={},  # No server-side filters needed
    metadata_fields={
        "url": "url",
        "date_published": "timestamp"
    },
    batch_size=10000,
    force=False
)

# Run full pipeline
processor.run()  # download() -> extract() -> process()

# Output:
# - data/raw/source=HF-mc4/date_accessed=2025-10-15/manifest.json
# - data/staging/source=HF-mc4/date_accessed=2025-10-15/batch-0000.jsonl
# - data/staging/source=HF-mc4/date_accessed=2025-10-15/batch-0001.jsonl
# - ...
# - data/processed/source=HF-mc4/date_processed=2025-10-15/hf-mc4.txt
# - data/processed/silver/source=HF-mc4/date_accessed=2025-10-15/part-0000.parquet
```

---

## 5. Testing Strategy ⏳

### Unit Tests for Filters

**Location**: `tests/test_filters.py` (to be created)

```python
class TestMinLengthFilter:
    def test_passes_long_text(self):
        passes, meta = min_length_filter("A" * 100, threshold=50)
        assert passes
        assert meta == {}

    def test_rejects_short_text(self):
        passes, meta = min_length_filter("Short", threshold=50)
        assert not passes


class TestLangidFilter:
    def test_detects_somali(self):
        somali_text = "Waxaan arkay nin Soomaaliyeed oo ka socda magaalada"
        passes, meta = langid_filter(somali_text, allowed_langs={"so"})
        assert passes
        assert meta["detected_lang"] == "so"
        assert meta["lang_confidence"] > 0.5

    def test_rejects_english(self):
        english_text = "This is an English text about Somalia"
        passes, meta = langid_filter(english_text, allowed_langs={"so"})
        assert not passes
        assert meta["detected_lang"] == "en"


class TestDialectHeuristicFilter:
    def test_enriches_with_markers(self):
        ruleset = {"sports": ["kubadda"], "politics": ["xukuumad"]}
        text = "Kubadda cagta waa ciyaar aad u xiiso badan"
        passes, meta = topic_lexicon_enrichment_filter(text, ruleset, enrich_only=True)

        assert passes
        assert meta["dialect_markers"]["sports"] > 0
        assert meta["primary_dialect"] == "sports"

    def test_filters_when_enrich_only_false(self):
        ruleset = {"sports": ["kubadda"]}
        text = "Text with no markers"
        passes, meta = topic_lexicon_enrichment_filter(text, ruleset, enrich_only=False)

        assert not passes
        assert meta["primary_dialect"] == "unknown"
```

### Integration Tests

**Location**: Update existing `tests/test_wikipedia_integration.py` and `tests/test_bbc_integration.py`

```python
# tests/test_wikipedia_integration.py
class TestWikipediaFiltering:
    def test_short_pages_filtered(self, compressed_wiki_fixture, temp_data_dir):
        """Test that short Wikipedia pages are filtered out."""
        processor = WikipediaSomaliProcessor()
        # ... run pipeline ...

        # Read silver dataset
        parquet_files = list(Path("data/processed/silver").rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # All records should be >= 50 chars (min_length_filter threshold)
        assert all(df['text'].str.len() >= 50)

    def test_english_pages_filtered(self, compressed_wiki_fixture, temp_data_dir):
        """Test that English pages are filtered out."""
        # Add English page to fixture
        # Run pipeline
        # Assert no English pages in output


# tests/test_bbc_integration.py
class TestBBCFiltering:
    def test_topic_enrichment(self, temp_data_dir):
        """Test that BBC articles get topic metadata."""
        # Create fixture with sports article containing "kubadda"
        processor = BBCSomaliProcessor(max_articles=10)
        # ... run pipeline ...

        # Read silver dataset
        parquet_files = list(Path("data/processed/silver").rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # Check that metadata includes dialect markers
        first_record_meta = json.loads(df.iloc[0]['source_metadata'])
        assert 'dialect_markers' in first_record_meta
        assert 'primary_dialect' in first_record_meta
```

### HF Processor Smoke Tests

**Location**: `tests/test_hf_integration.py` (to be created)

```python
class TestHFProcessor:
    def test_smoke_test_with_small_sample(self):
        """Smoke test with take(5) to avoid large downloads in CI."""
        from datasets import load_dataset

        # Load tiny sample
        dataset = load_dataset("mc4", "so", split="train", streaming=True)
        sample = list(dataset.take(5))

        # Create processor
        processor = HuggingFaceSomaliProcessor(
            dataset_name="mc4",
            config_name="so",
            split="train"
        )

        # Mock extract() to use our small sample instead of streaming
        # ... implementation ...

        # Run process()
        result = processor.process()

        assert result.exists()
        # Verify silver dataset created
        assert len(list(Path("data/processed/silver").rglob("*.parquet"))) > 0
```

---

## 6. Configuration & Best Practices

### Externalizing Filter Thresholds

**Recommendation**: Add filter configuration to `config.py`

```python
# config.py
class FilteringConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='SDC_FILTERING__',
        env_file='.env',
    )

    min_length_threshold: int = Field(default=50)
    lang_confidence_threshold: float = Field(default=0.5)
    allowed_languages: Set[str] = Field(default={"so"})


class Config(BaseSettings):
    ...
    filtering: FilteringConfig = Field(default_factory=FilteringConfig)
```

**Usage in processors**:

```python
def _register_filters(self) -> None:
    from somali_dialect_classifier.preprocessing.filters import (
        min_length_filter,
        langid_filter
    )
    from ..config import get_config

    config = get_config()

    self.record_filters.append((min_length_filter, {
        "threshold": config.filtering.min_length_threshold
    }))
    self.record_filters.append((langid_filter, {
        "allowed_langs": config.filtering.allowed_languages,
        "confidence_threshold": config.filtering.lang_confidence_threshold
    }))
```

### MLflow Integration

**For Ops auditing of filter drift**:

```python
# In process() method, after completion
if mlflow.active_run():
    mlflow.log_metrics({
        "records_processed": records_processed,
        "records_filtered": records_filtered,
        "filter_rate": records_filtered / (records_processed + records_filtered)
    })

    # Log per-filter counts
    for filter_reason, count in filter_stats.items():
        mlflow.log_metric(f"filter/{filter_reason}", count)
```

### Data Quality Assertions

**Great Expectations integration** (future):

```python
# After writing silver dataset
import great_expectations as ge

df = ge.read_parquet(parquet_path)

# Schema validation
assert df.expect_column_to_exist("text")
assert df.expect_column_to_exist("detected_lang")

# Quality checks
assert df.expect_column_values_to_be_in_set("language", ["so"])
assert df.expect_column_values_to_not_be_null("text")
assert df.expect_column_values_to_match_regex("text", r".{50,}")  # Min length
```

---

## 7. Documentation Updates

### README Section (to be added)

```markdown
## Data Quality Filters

All processors use a pluggable filter framework to ensure silver dataset quality.

### Default Filters

**All Sources**:
- `min_length_filter`: Removes records < 50 characters
- `langid_filter`: Removes non-Somali content (confidence < 50%)

**BBC News**:
- Additional `topic_lexicon_enrichment_filter` for topic enrichment (renamed from `dialect_heuristic_filter`)

### Custom Filters

Create custom filters for your data source:

\```python
from somali_dialect_classifier.preprocessing import BasePipeline
from somali_dialect_classifier.preprocessing.filters import min_length_filter

class MyProcessor(BasePipeline):
    def _register_filters(self):
        # Add standard filters
        self.record_filters.append((min_length_filter, {"threshold": 100}))

        # Add custom filter
        def my_filter(text, pattern):
            import re
            return bool(re.search(pattern, text)), {}

        self.record_filters.append((my_filter, {"pattern": r"\d{4}"}))
\```

### Filter Statistics

After processing, check logs for filter statistics:

\```
Processing complete: 8543 records
Filtered: 2157 records
Filter statistics:
  filtered_by_min_length_filter: 1204 records
  filtered_by_langid_filter: 953 records
\```

### Configuration

Override filter thresholds via environment variables:

\```bash
export SDC_FILTERING__MIN_LENGTH_THRESHOLD=100
export SDC_FILTERING__LANG_CONFIDENCE_THRESHOLD=0.7
\```
```

---

## Summary

### ✅ All Tasks Complete

1. **Complete Filter Framework** with 5 filters + convenience constructors
2. **BasePipeline Hook Interface** with `_register_filters()` override point
3. **Filter Execution** integrated in `process()` with error handling
4. **Filter Statistics** logged with Counter
5. **Wikipedia Retrofit** with min_length + langid filters
6. **BBC Retrofit** with min_length + langid + topic enrichment
7. **HuggingFaceSomaliProcessor** fully implemented with streaming JSONL batching
8. **Comprehensive unit tests** covering all filters (28+ tests)
9. **Integration test suite** for Wikipedia/BBC/HF processors
10. **Configuration externalization** via pydantic-settings
11. **Documentation** - 1200+ lines across HUGGINGFACE_DATASETS.md and HUGGINGFACE_DATA_FLOW.md
12. **Principal MLE Review Fixes** - All 6 critical/high-risk/risk items addressed

### Key Achievements

- **Zero breaking changes**: Existing processors work unchanged
- **Opt-in filtering**: Base implementation has empty filter list
- **Metadata enrichment**: Filters can add fields without rejecting
- **Audit trail**: Per-filter drop counts logged
- **Graceful degradation**: Filter exceptions don't crash pipeline
- **Extensible**: New processors inherit filter framework automatically
- **Production-ready**: Handles OOM scenarios, filesystem compatibility, empty data edge cases
- **Test coverage**: 165+ tests including contract tests, integration tests, and unit tests
- **Robust BBC scraper**: Multi-level semantic selector fallback strategy

### Outstanding Items (Future Work)

1. **MLflow Integration** - Hook up filter statistics to MLflow tracking (design documented)
2. **Great Expectations** - Add data quality assertions (example provided)
3. **Precision/Recall Evaluation** - Benchmark heuristic filter accuracy against labeled test set
4. **Documentation Restructure** - Reorganize docs/ into MkDocs/Sphinx-ready structure (see Principal MLE recommendations)
5. **Orchestration** - Add Prefect/Dagster flows for scheduled pipeline runs
6. **Labeling Strategy** - Define annotation guidelines and active learning approach for model training phase

---

**Date**: 2025-10-20
**Status**: Accepted

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
