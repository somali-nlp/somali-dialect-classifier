# System Architecture

This document provides a comprehensive overview of the Somali Dialect Classifier's architecture, design patterns, and technical decisions.

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Design Principles](#design-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Design Patterns](#design-patterns)
6. [Technology Stack](#technology-stack)
7. [Directory Structure](#directory-structure)

## High-Level Overview

The Somali Dialect Classifier is a data preprocessing pipeline system designed to collect, clean, and prepare Somali text data from multiple sources for downstream dialect classification tasks.

```
┌─────────────────┐
│  Data Sources   │
│  (Wikipedia,    │
│   BBC, HF, etc) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Raw Layer     │
│   (Bronze)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Staging Layer   │
│  (Extraction)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Processing Layer│
│ (Text Cleaning) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Quality Filters │
│   (Validation)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Silver Layer   │
│   (Parquet)     │
└─────────────────┘
```

### Data Lakehouse Architecture

The system implements a **medallion architecture** (Bronze → Silver → Gold):

- **Bronze (Raw)**: Immutable raw data from sources (XML, JSON, HTML)
- **Silver (Cleaned)**: Validated, deduplicated, schema-enforced Parquet datasets
- **Gold (Future)**: Aggregated, dialect-labeled, model-ready datasets

## Design Principles

### 1. Single Responsibility Principle (SRP)

Each component has one clear responsibility:

- **BasePipeline**: Orchestration and workflow
- **TextCleaners**: Text transformation
- **Filters**: Quality validation
- **SilverWriter**: Schema enforcement and I/O
- **RecordUtils**: Data structure utilities

### 2. Open/Closed Principle (OCP)

System is **open for extension, closed for modification**:

- New data sources extend `BasePipeline` without modifying base class
- New filters added via `_register_filters()` hook
- New cleaners composed via pipeline pattern

### 3. Dependency Inversion Principle (DIP)

High-level modules depend on abstractions:

```python
# Base contract (abstraction)
class BasePipeline(ABC):
    @abstractmethod
    def _extract_records(self) -> Iterator[RawRecord]:
        pass

# Concrete implementations depend on abstraction
class WikipediaSomaliProcessor(BasePipeline):
    def _extract_records(self):
        # Wikipedia-specific implementation
        pass
```

### 4. Don't Repeat Yourself (DRY)

Shared utilities prevent duplication:

- `text_cleaners.py`: HTML/Wiki markup cleaning (shared by BBC + Wikipedia)
- `record_utils.py`: Hashing, ID generation (shared by all processors)
- `silver_writer.py`: Parquet I/O (shared schema enforcement)

### 5. Configuration as Code

All runtime behavior configurable via:

- **Environment variables**: `SDC_DATA__RAW_DIR`, `SDC_SCRAPING__BBC__MAX_ARTICLES`
- **Config file**: `.env` in project root
- **Programmatic API**: `get_config().data.raw_dir`

## Component Architecture

### 1. Base Pipeline (`base_pipeline.py`)

**Purpose**: Template Method pattern for ETL orchestration

**Key Responsibilities**:
- Define processing workflow (extract → clean → filter → write)
- Manage logging and progress tracking
- Provide hook points for subclasses (`_register_filters`, `_extract_records`)
- Handle force reprocessing logic

**Key Methods**:
```python
def process(self) -> Path:
    """Main entry point - orchestrates full pipeline."""

def _extract_records(self) -> Iterator[RawRecord]:
    """Hook: Subclasses implement source-specific extraction."""

def _register_filters(self) -> None:
    """Hook: Subclasses register quality filters."""
```

**Design Pattern**: **Template Method** - Defines skeleton, subclasses fill in steps

### 2. Processors (`wikipedia_somali_processor.py`, `bbc_somali_processor.py`)

**Purpose**: Source-specific implementations

**Wikipedia Processor**:
- Extracts from MediaWiki XML dumps
- Parses Wiki markup syntax
- Filters namespace (Talk:, User:, etc.)
- Memory-safe streaming (10MB buffer threshold)

**BBC Processor**:
- Discovers articles from homepage + sitemap
- Respects `robots.txt` and rate limits
- Parses HTML with BeautifulSoup
- Caches article links with parameter validation

### 3. Text Cleaners (`text_cleaners.py`)

**Purpose**: Composable text transformation pipeline

**Design Pattern**: **Pipeline (Chain of Responsibility)**

```python
class TextCleaningPipeline:
    def __init__(self, cleaners: List[Callable[[str], str]]):
        self.cleaners = cleaners

    def clean(self, text: str) -> str:
        for cleaner in self.cleaners:
            text = cleaner(text)
        return text
```

**Available Cleaners**:
- `WikiMarkupCleaner`: Remove `[[links]]`, `{{templates}}`, `===headers===`
- `HTMLCleaner`: Strip tags, decode entities (`&amp;` → `&`)
- `WhitespaceCleaner`: Collapse newlines, normalize spaces

**Factory Functions**:
```python
create_wikipedia_cleaner() -> TextCleaningPipeline
create_html_cleaner() -> TextCleaningPipeline
```

### 4. Quality Filters (`filters.py`)

**Purpose**: Stateless validation and metadata enrichment

**Filter Signature**:
```python
def filter_func(cleaned_text: str, **kwargs) -> Tuple[bool, Dict[str, Any]]:
    """
    Returns:
        passes (bool): True if record should be kept
        metadata_updates (dict): Additional fields to add to record
    """
```

**Available Filters**:

1. **min_length_filter**: Length-based rejection
   ```python
   min_length_filter(text, threshold=50)
   # → (True, {}) if len(text) >= 50
   ```

2. **langid_filter**: Heuristic language detection
   ```python
   langid_filter(text, allowed_langs={"so"}, confidence_threshold=0.3)
   # → (True, {"detected_lang": "so", "lang_confidence": 0.85})
   ```

3. **dialect_heuristic_filter**: Topic marker enrichment
   ```python
   dialect_heuristic_filter(text, ruleset={"sports": ["kubadda", "kooxda"]})
   # → (True, {"dialect_markers": {"sports": 2}, "primary_dialect": "sports"})
   ```

4. **namespace_filter**: Wikipedia namespace validation
   ```python
   namespace_filter(title, skip_prefixes=["Talk:", "User:"])
   # → (False, {}) if title.startswith("Talk:")
   ```

5. **custom_filter**: Arbitrary predicates
   ```python
   custom_filter(text, predicate=lambda t: "news" in t.lower())
   # → (True, {"is_news": True})
   ```

**Design Pattern**: **Strategy** - Pluggable algorithms via function objects

### 5. Silver Writer (`silver_writer.py`)

**Purpose**: Schema enforcement and Parquet I/O

**Key Features**:
- **Explicit PyArrow schema** prevents drift
- **Partitioning**: `source=X/date_accessed=Y` for data organization
- **Atomic writes**: Tmp files + rename for crash safety
- **Metadata serialization**: JSON fields for complex data

**Schema**:
```python
SILVER_SCHEMA = pa.schema([
    ('id', pa.string()),                    # sha256 hash
    ('text', pa.string()),                  # cleaned text
    ('source', pa.string()),                # e.g., "Wikipedia-Somali"
    ('source_type', pa.string()),           # e.g., "encyclopedia"
    ('date_accessed', pa.date32()),         # collection date
    ('language', pa.string()),              # ISO 639-1 code
    ('license', pa.string()),               # e.g., "CC-BY-SA-3.0"
    ('token_count', pa.int32()),            # word count
    ('metadata', pa.string()),              # JSON serialized
])
```

### 6. Record Utilities (`record_utils.py`)

**Purpose**: Data structure helpers

**Key Functions**:
```python
text_hash(text: str) -> str
    """Deterministic SHA-256 hash for deduplication."""

generate_record_id(text: str, source: str) -> str
    """Unique ID: {source_prefix}_{text_hash}."""

count_tokens(text: str) -> int
    """Simple whitespace-based token counting."""

build_silver_record(...) -> Dict[str, Any]
    """Construct schema-compliant record dictionary."""
```

### 7. Configuration (`config.py`)

**Purpose**: Centralized configuration management

**Design Pattern**: **Singleton** via `get_config()`

**Configuration Hierarchy**:
```
1. Default values (in code)
2. .env file (if exists)
3. Environment variables (highest priority)
```

**Structure**:
```python
class Config:
    data: DataConfig              # Paths (raw_dir, silver_dir)
    scraping: ScrapingConfig      # Source-specific settings
    logging: LoggingConfig        # Log levels, formats
```

## Data Flow

### Processing Pipeline Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. RAW EXTRACTION                                            │
│    _extract_records() → Iterator[RawRecord]                  │
│    - Wikipedia: Parse XML dump                               │
│    - BBC: Scrape HTML pages                                  │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. TEXT CLEANING                                             │
│    text_cleaner.clean(raw_text) → cleaned_text               │
│    - Remove markup (Wiki/HTML)                               │
│    - Normalize whitespace                                    │
│    - Decode entities                                         │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. QUALITY FILTERING                                         │
│    for filter_func, kwargs in self.record_filters:           │
│        passes, metadata = filter_func(cleaned_text, **kwargs)│
│        if not passes: reject record                          │
│        else: merge metadata                                  │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. RECORD BUILDING                                           │
│    build_silver_record(...) → Dict[str, Any]                 │
│    - Generate ID (hash-based)                                │
│    - Add source metadata                                     │
│    - Serialize complex fields                                │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. BATCH WRITING                                             │
│    silver_writer.write(records, source, date)                │
│    - Validate schema                                         │
│    - Partition by source/date                                │
│    - Write Parquet atomically                                │
└──────────────────────────────────────────────────────────────┘
```

### Directory Partitioning Strategy

```
data/
├── raw/                                      # Bronze layer
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-01-15/
│           └── sowiki-latest-pages-articles.xml.bz2
│
├── staging/                                  # Intermediate extracts
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-01-15/
│           └── wikisom_raw.txt
│
└── processed/
    └── silver/                               # Silver layer
        └── source=Wikipedia-Somali/
            └── date_accessed=2025-01-15/
                └── part-0000.parquet         # Schema-enforced
```

**Benefits**:
- **Time-travel**: Query specific collection dates
- **Incremental updates**: Add new partitions without reprocessing
- **Source isolation**: Debug single source without affecting others
- **Hive-compatible**: Works with Spark, Athena, Presto

## Design Patterns

### 1. Template Method (BasePipeline)

**Problem**: Different sources share workflow but differ in details

**Solution**: Base class defines workflow, subclasses override hooks

```python
class BasePipeline:
    def process(self):              # Template method
        for record in self._extract_records():  # Hook 1
            cleaned = self.text_cleaner.clean(record.text)
            # ... filtering logic ...
        self._register_filters()    # Hook 2
```

### 2. Strategy (Filters)

**Problem**: Quality rules vary by source and change over time

**Solution**: Encapsulate algorithms as function objects

```python
# Filters are strategies that can be swapped/composed
processor.record_filters.append((min_length_filter, {"threshold": 50}))
processor.record_filters.append((langid_filter, {"confidence": 0.3}))
```

### 3. Pipeline (TextCleaners)

**Problem**: Text transformations need to be composable

**Solution**: Chain cleaners in sequence

```python
pipeline = TextCleaningPipeline([
    WikiMarkupCleaner(),
    WhitespaceCleaner(),
])
pipeline.clean(raw_text)  # Applies cleaners in order
```

### 4. Factory (Cleaner Creation)

**Problem**: Complex object construction

**Solution**: Factory functions hide complexity

```python
# Instead of:
pipeline = TextCleaningPipeline([
    WikiMarkupCleaner(),
    WhitespaceCleaner(min_length=50),
])

# Use:
pipeline = create_wikipedia_cleaner()
```

### 5. Iterator (Record Extraction)

**Problem**: Large datasets don't fit in memory

**Solution**: Lazy evaluation via generators

```python
def _extract_records(self) -> Iterator[RawRecord]:
    for page in self._parse_xml():  # Yields one at a time
        yield RawRecord(text=page.text, metadata=page.meta)
```

## Technology Stack

### Core Dependencies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Configuration** | pydantic-settings | Type-safe config with env var support |
| **CLI** | Built-in argparse | Command-line interfaces |
| **XML Parsing** | mwxml | MediaWiki dump processing |
| **HTML Parsing** | BeautifulSoup4 | Web scraping |
| **HTTP Client** | requests | API calls and downloads |
| **Data Format** | PyArrow/Parquet | Columnar storage |
| **Logging** | Python logging | Structured logging with rotation |

### Development Dependencies

| Tool | Purpose |
|------|---------|
| **pytest** | Unit and integration testing |
| **ruff** | Linting and formatting |
| **mypy** | Static type checking |
| **coverage** | Test coverage reporting |

### Optional MLOps Dependencies

| Tool | Purpose | Install With |
|------|---------|--------------|
| **MLflow** | Experiment tracking | `pip install -e ".[mlops]"` |
| **Weights & Biases** | Metric logging | `pip install -e ".[mlops]"` |
| **Prefect** | Workflow orchestration | `pip install -e ".[mlops]"` |
| **Great Expectations** | Data validation | `pip install -e ".[mlops]"` |

## Directory Structure

```
somali-dialect-classifier/
├── src/somali_dialect_classifier/
│   ├── __init__.py
│   ├── config.py                          # Configuration management
│   │
│   ├── cli/                               # Command-line interfaces
│   │   ├── download_wikisom.py
│   │   └── download_bbcsom.py
│   │
│   └── preprocessing/                     # Core ETL pipeline
│       ├── __init__.py
│       ├── base_pipeline.py              # Template method orchestration
│       ├── filters.py                    # Quality validation strategies
│       ├── text_cleaners.py              # Text transformation pipeline
│       ├── record_utils.py               # Data structure utilities
│       ├── silver_writer.py              # Schema enforcement & I/O
│       ├── wikipedia_somali_processor.py # Wikipedia implementation
│       └── bbc_somali_processor.py       # BBC implementation
│
├── tests/                                 # Test suite
│   ├── fixtures/                         # Test data
│   ├── test_filters.py                   # Filter unit tests (35 tests)
│   ├── test_force_reprocessing.py        # Force flag tests
│   ├── test_bbc_integration.py           # BBC end-to-end
│   ├── test_wikipedia_integration.py     # Wikipedia end-to-end
│   └── ...                               # 137 tests total
│
├── data/                                  # Data lakehouse (gitignored)
│   ├── raw/                              # Bronze layer
│   ├── staging/                          # Intermediate extracts
│   └── processed/silver/                 # Silver layer (Parquet)
│
├── logs/                                  # Runtime logs (gitignored)
├── scripts/                               # Utility scripts
├── docs/                                  # Technical documentation
└── .archive/                              # Dev artifacts (gitignored)
```

## Extension Points

### Adding a New Data Source

1. **Create processor class**:
   ```python
   class HuggingFaceProcessor(BasePipeline):
       def __init__(self, dataset_name: str, split: str = "train"):
           super().__init__(
               source=f"HuggingFace-{dataset_name}",
               log_frequency=10000,
               batch_size=1000
           )
   ```

2. **Implement extraction hook**:
   ```python
   def _extract_records(self) -> Iterator[RawRecord]:
       from datasets import load_dataset
       dataset = load_dataset(self.dataset_name, split=self.split, streaming=True)
       for item in dataset:
           yield RawRecord(text=item['text'], metadata={"id": item['id']})
   ```

3. **Register filters**:
   ```python
   def _register_filters(self):
       from .filters import min_length_filter, langid_filter
       self.record_filters.append((min_length_filter, {"threshold": 100}))
       self.record_filters.append((langid_filter, {"confidence_threshold": 0.3}))
   ```

4. **Create CLI entry point** in `cli/download_hf.py`

5. **Add tests** in `tests/test_hf_integration.py`

### Adding a Custom Filter

```python
# In filters.py or custom module
def profanity_filter(
    cleaned_text: str,
    banned_words: Set[str],
    **kwargs
) -> Tuple[bool, Dict[str, Any]]:
    """Filter out text containing profanity."""
    text_lower = cleaned_text.lower()
    violations = [word for word in banned_words if word in text_lower]

    passes = len(violations) == 0
    metadata = {"profanity_violations": violations} if violations else {}

    return passes, metadata

# In processor
def _register_filters(self):
    self.record_filters.append((profanity_filter, {
        "banned_words": {"badword1", "badword2"}
    }))
```

## Performance Considerations

### Memory Management

- **Streaming extraction**: Use `Iterator[RawRecord]` instead of loading all data
- **Batch writing**: Accumulate records before Parquet write (default: 1000)
- **Buffer limits**: Wikipedia processor caps buffers at 10MB

### Caching Strategy

- **BBC article discovery**: Cache links JSON with parameter validation
- **Wikipedia dumps**: Reuse downloaded XML unless forced
- **Force reprocessing**: `force=True` flag bypasses all caches

### Parallelization Opportunities

Current implementation is **single-threaded**. Future optimizations:

1. **Multi-process record extraction**: Pool workers for I/O-bound tasks
2. **Parallel text cleaning**: Process batches concurrently
3. **Distributed filter execution**: Spark/Dask for large-scale filtering

## Security Considerations

### Data Privacy

- **No PII collection**: Text-only, no usernames/emails stored
- **License compliance**: Metadata tracks source licenses

### Web Scraping Ethics

- **robots.txt compliance**: BBC scraper respects exclusion rules
- **Rate limiting**: 3-6 second delays between requests
- **User agent**: Identifies as research tool, not browser

### Dependency Security

- **No known vulnerabilities**: Regular `pip audit` checks
- **Pinned versions**: Lock file for reproducibility

## Future Enhancements

### Planned Features

1. **HuggingFace Dataset Processor**: Streaming support for mc4, oscar
2. **MLflow Integration**: Log filter statistics as metrics
3. **Great Expectations**: Schema validation and quality assertions
4. **DVC Integration**: Data version control for reproducibility
5. **Distributed Processing**: Spark/Ray backends for scalability

### API Stability

Current API is **stable** for:
- `BasePipeline` interface
- Filter signatures
- Silver schema
- Configuration structure

**Breaking changes** will follow semantic versioning:
- MAJOR version: Breaking API changes
- MINOR version: New features (backward compatible)
- PATCH version: Bug fixes
