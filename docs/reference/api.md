# API Reference

Comprehensive API documentation for the Somali Dialect Classifier preprocessing pipeline. This reference covers all public APIs, classes, functions, and their usage.

## Table of Contents

1. [Core Pipeline](#core-pipeline)
   - [BasePipeline](#basepipeline)
   - [RawRecord](#rawrecord)
2. [Processors](#processors)
   - [WikipediaSomaliProcessor](#wikipediasomaliprocessor)
   - [BBCSomaliProcessor](#bbcsomaliprocessor)
   - [HuggingFaceSomaliProcessor](#huggingfacesomaliprocessor)
   - [SprakbankenSomaliProcessor](#sprakbankensomaliprocessor)
3. [Text Cleaners](#text-cleaners)
   - [WikiMarkupCleaner](#wikimarkupcleaner)
   - [HTMLCleaner](#htmlcleaner)
   - [WhitespaceCleaner](#whitespacecleaner)
   - [TextCleaningPipeline](#textcleaningpipeline)
4. [Filters](#filters)
   - [min_length_filter](#min_length_filter)
   - [langid_filter](#langid_filter)
   - [dialect_heuristic_filter](#dialect_heuristic_filter)
   - [namespace_filter](#namespace_filter)
   - [custom_filter](#custom_filter)
5. [Record Utilities](#record-utilities)
   - [generate_text_hash](#generate_text_hash)
   - [generate_record_id](#generate_record_id)
   - [count_tokens](#count_tokens)
   - [build_silver_record](#build_silver_record)
6. [Silver Dataset Writer](#silver-dataset-writer)
   - [SilverDatasetWriter](#silverdatasetwriter)

---

## Core Pipeline

### BasePipeline

**Module**: `somali_dialect_classifier.preprocessing.base_pipeline`

Abstract base class providing shared orchestration logic for all data source processors.

#### Class Definition

```python
class BasePipeline(DataProcessor, ABC):
    """
    Reusable orchestration layer for all data sources.

    Provides:
    - Consistent directory structure
    - Shared processing flow (no duplication!)
    - Standardized logging
    - Silver dataset writing
    """
```

#### Constructor

```python
def __init__(
    self,
    source: str,
    log_frequency: int = 1000,
    batch_size: Optional[int] = None,
    force: bool = False,
)
```

**Parameters**:
- `source` (str): Source name (e.g., "Wikipedia-Somali", "BBC-Somali")
- `log_frequency` (int, optional): Log progress every N records. Default: 1000
- `batch_size` (int, optional): Write silver dataset in batches of N records. Default: None (write all at once)
- `force` (bool, optional): Force reprocessing even if output files exist. Default: False

**Example**:
```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

processor = WikipediaSomaliProcessor(force=True)
# Inherits BasePipeline initialization
```

#### Abstract Methods

Subclasses **must** implement these methods:

##### `_create_cleaner()`

```python
@abstractmethod
def _create_cleaner(self) -> TextCleaningPipeline:
    """
    Create source-specific text cleaner.

    Returns:
        TextCleaningPipeline configured for this source
    """
```

**Example**:
```python
def _create_cleaner(self) -> TextCleaningPipeline:
    return create_wikipedia_cleaner()
```

##### `_extract_records()`

```python
@abstractmethod
def _extract_records(self) -> Iterator[RawRecord]:
    """
    Extract records from staging file (source-specific).

    Yields:
        RawRecord objects with title, text, url, and metadata
    """
```

**Example**:
```python
def _extract_records(self) -> Iterator[RawRecord]:
    with open(self.staging_file, 'r') as f:
        for line in f:
            yield RawRecord(
                title="Example",
                text=line,
                url="https://example.com",
                metadata={}
            )
```

##### `_get_source_type()`

```python
@abstractmethod
def _get_source_type(self) -> str:
    """
    Get source type for silver records.

    Returns:
        Source type (e.g., "wiki", "news", "social")
    """
```

##### `_get_license()`

```python
@abstractmethod
def _get_license(self) -> str:
    """
    Get license information for silver records.

    Returns:
        License string (e.g., "CC-BY-SA-3.0", "BBC Terms of Use")
    """
```

##### `_get_language()`

```python
@abstractmethod
def _get_language(self) -> str:
    """
    Get language code for silver records.

    Returns:
        ISO 639-1 language code (e.g., "so" for Somali)
    """
```

##### `_get_source_metadata()`

```python
@abstractmethod
def _get_source_metadata(self) -> Dict[str, Any]:
    """
    Get source-specific metadata for silver records.

    Returns:
        Dictionary with source-specific metadata
    """
```

**Example**:
```python
def _get_source_metadata(self) -> Dict[str, Any]:
    return {
        "wiki_code": "sowiki",
        "dump_url": "https://dumps.wikimedia.org/sowiki/latest/..."
    }
```

##### `_get_register()` (New in v2.1)

```python
@abstractmethod
def _get_register(self) -> str:
    """
    Get linguistic register for silver records.

    Returns:
        Register string: "formal", "informal", or "colloquial"
    """
```

**Valid values**:
- `"formal"` - Standard, academic, or professional language
- `"informal"` - Casual but structured language
- `"colloquial"` - Conversational, dialectal variations

**Examples by processor**:
```python
# WikipediaSomaliProcessor
def _get_register(self) -> str:
    return "formal"  # Encyclopedic content

# BBCSomaliProcessor
def _get_register(self) -> str:
    return "formal"  # Professional journalism

# HuggingFaceSomaliProcessor
def _get_register(self) -> str:
    return "formal"  # Web corpus (mixed but generally formal)

# SprakbankenSomaliProcessor
def _get_register(self) -> str:
    return "formal"  # Academic corpora
```

#### Public Methods

##### `process()`

```python
def process(self) -> Path:
    """
    Shared processing orchestration.

    This method:
    1. Iterates through records from _extract_records()
    2. Cleans text using self.text_cleaner
    3. Applies record filters
    4. Builds silver records
    5. Logs progress consistently
    6. Writes to silver dataset

    Returns:
        Path to processed file
    """
```

**Example**:
```python
processor = WikipediaSomaliProcessor()
processor.download()
processor.extract()
output_path = processor.process()
print(f"Processed data written to: {output_path}")
```

##### `run()`

```python
def run(self) -> Path:
    """
    Template method - orchestrates full pipeline.

    Executes: download() → extract() → process()

    Returns:
        Path to processed file
    """
```

**Example**:
```python
processor = WikipediaSomaliProcessor()
output_path = processor.run()  # Downloads, extracts, and processes
```

##### `_register_filters()`

```python
def _register_filters(self) -> None:
    """
    Register record filters for quality control.

    Subclasses override this method to append filters to self.record_filters.
    """
```

**Example**:
```python
def _register_filters(self) -> None:
    from .filters import min_length_filter, langid_filter

    self.record_filters.append((min_length_filter, {"threshold": 50}))
    self.record_filters.append((langid_filter, {
        "allowed_langs": {"so"},
        "confidence_threshold": 0.5
    }))
```

#### Attributes

- `source` (str): Source name
- `log_frequency` (int): Progress logging frequency
- `batch_size` (Optional[int]): Batch size for writing
- `force` (bool): Force reprocessing flag
- `date_accessed` (str): ISO date when data was accessed
- `raw_dir` (Path): Raw data directory
- `staging_dir` (Path): Staging directory
- `processed_dir` (Path): Processed data directory
- `text_cleaner` (TextCleaningPipeline): Text cleaning pipeline
- `silver_writer` (SilverDatasetWriter): Silver dataset writer
- `record_filters` (List[Tuple[Callable, Dict]]): List of filter functions and kwargs

---

### RawRecord

**Module**: `somali_dialect_classifier.preprocessing.base_pipeline`

Intermediate representation between extraction and processing.

#### Class Definition

```python
class RawRecord:
    """
    Intermediate representation between extraction and processing.

    Decouples source-specific extraction from shared processing logic.
    """
```

#### Constructor

```python
def __init__(
    self,
    title: str,
    text: str,
    url: str,
    metadata: Optional[Dict[str, Any]] = None,
)
```

**Parameters**:
- `title` (str): Document title
- `text` (str): Raw text content (will be cleaned)
- `url` (str): Source URL
- `metadata` (Dict[str, Any], optional): Additional source-specific metadata. Default: {}

**Example**:
```python
from somali_dialect_classifier.preprocessing.base_pipeline import RawRecord

record = RawRecord(
    title="Soomaaliya",
    text="Soomaaliya waa dal ku yaal Geeska Afrika...",
    url="https://so.wikipedia.org/wiki/Soomaaliya",
    metadata={"category": "geography"}
)
```

---

## Processors

### WikipediaSomaliProcessor

**Module**: `somali_dialect_classifier.preprocessing.wikipedia_somali_processor`

Processor for downloading, extracting, and cleaning Somali Wikipedia data.

#### Class Definition

```python
class WikipediaSomaliProcessor(BasePipeline):
    """
    Processor for downloading, extracting, and cleaning Somali Wikipedia data.

    Inherits shared orchestration from BasePipeline and implements
    Wikipedia-specific logic (XML parsing, URL resolution).
    """
```

#### Constructor

```python
def __init__(self, force: bool = False)
```

**Parameters**:
- `force` (bool, optional): Force reprocessing even if output files exist. Default: False

**Example**:
```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

# Default usage
processor = WikipediaSomaliProcessor()

# Force reprocessing
processor = WikipediaSomaliProcessor(force=True)
```

#### Methods

##### `download()`

```python
def download(self) -> Path:
    """
    Download Wikipedia dump if not already present.

    Returns:
        Path to downloaded dump file
    """
```

**Example**:
```python
processor = WikipediaSomaliProcessor()
dump_path = processor.download()
# Downloads: data/raw/source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/sowiki-latest-pages-articles.xml.bz2
```

##### `extract()`

```python
def extract(self) -> Path:
    """
    Extract raw text from Wikipedia XML dump with memory-efficient streaming.

    Returns:
        Path to staging file with extracted text
    """
```

**Example**:
```python
processor = WikipediaSomaliProcessor()
processor.download()
staging_path = processor.extract()
# Extracts to: data/staging/source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/wikisom_raw.txt
```

##### `process()`

Inherited from `BasePipeline`. Processes extracted text and writes silver dataset.

#### Full Pipeline Example

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

# Option 1: Run full pipeline
processor = WikipediaSomaliProcessor()
output_path = processor.run()

# Option 2: Run stages separately
processor = WikipediaSomaliProcessor()
processor.download()
processor.extract()
processor.process()
```

---

### BBCSomaliProcessor

**Module**: `somali_dialect_classifier.preprocessing.bbc_somali_processor`

Processor for scraping, extracting, and cleaning BBC Somali news articles.

#### Class Definition

```python
class BBCSomaliProcessor(BasePipeline):
    """
    Processor for scraping, extracting, and cleaning BBC Somali news articles.

    Inherits shared orchestration from BasePipeline and implements
    BBC-specific scraping logic with ethical rate limiting.
    """
```

#### Constructor

```python
def __init__(
    self,
    max_articles: Optional[int] = None,
    delay_range: tuple = (3, 6),
    force: bool = False
)
```

**Parameters**:
- `max_articles` (int, optional): Maximum number of articles to scrape. Default: None (unlimited)
- `delay_range` (tuple, optional): (min, max) seconds to wait between requests. Default: (3, 6)
- `force` (bool, optional): Force reprocessing even if output files exist. Default: False

**Example**:
```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# Scrape 100 articles with default delays
processor = BBCSomaliProcessor(max_articles=100)

# More ethical scraping with longer delays
processor = BBCSomaliProcessor(max_articles=50, delay_range=(5, 10))

# Force re-scraping
processor = BBCSomaliProcessor(force=True)
```

#### Methods

##### `download()`

```python
def download(self) -> Path:
    """
    Discover and download article links (respects robots.txt).

    Returns:
        Path to article links file
    """
```

**Example**:
```python
processor = BBCSomaliProcessor(max_articles=100)
links_path = processor.download()
# Saves: data/raw/source=BBC-Somali/date_accessed=YYYY-MM-DD/article_links.json
```

##### `extract()`

```python
def extract(self) -> Path:
    """
    Scrape articles from discovered links.

    Returns:
        Path to scraped articles file
    """
```

**Example**:
```python
processor = BBCSomaliProcessor(max_articles=100)
processor.download()
articles_path = processor.extract()
# Saves: data/staging/source=BBC-Somali/date_accessed=YYYY-MM-DD/bbcsom_articles.json
```

#### Full Pipeline Example

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# Scrape 50 BBC Somali articles
processor = BBCSomaliProcessor(max_articles=50, delay_range=(4, 8))
output_path = processor.run()

# Silver dataset written to:
# data/processed/silver/source=BBC-Somali/date_accessed=YYYY-MM-DD/part-0000.parquet
```

---

### HuggingFaceSomaliProcessor

**Module**: `somali_dialect_classifier.preprocessing.huggingface_somali_processor`

Processor for streaming, extracting, and processing large-scale Somali datasets from HuggingFace Hub.

#### Class Definition

```python
class HuggingFaceSomaliProcessor(BasePipeline):
    """
    Processor for HuggingFace datasets with streaming and manifest-based versioning.

    Supports streaming mode for datasets larger than RAM with resume capability.
    Currently supports MC4 dataset only (OSCAR and MADLAD-400 excluded).
    """
```

#### Constructor

```python
def __init__(
    self,
    dataset_name: str,
    dataset_config: str,
    split: str = "train",
    text_field: str = "text",
    url_field: Optional[str] = None,
    metadata_fields: Optional[List[str]] = None,
    streaming_batch_size: int = 5000,
    max_records: Optional[int] = None,
    force: bool = False
)
```

**Parameters**:
- `dataset_name` (str): HuggingFace dataset identifier (e.g., "allenai/c4")
- `dataset_config` (str): Dataset configuration (e.g., "so" for Somali)
- `split` (str, optional): Dataset split. Default: "train"
- `text_field` (str, optional): Field containing text. Default: "text"
- `url_field` (str, optional): Field containing URL. Default: None
- `metadata_fields` (List[str], optional): Additional metadata fields to extract. Default: None
- `streaming_batch_size` (int, optional): Records per JSONL batch. Default: 5000
- `max_records` (int, optional): Maximum records to process. Default: None (unlimited)
- `force` (bool, optional): Force reprocessing. Default: False

**Example**:
```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import HuggingFaceSomaliProcessor

# Process MC4 dataset
processor = HuggingFaceSomaliProcessor(
    dataset_name="allenai/c4",
    dataset_config="so",
    split="train",
    text_field="text",
    url_field="url",
    metadata_fields=["timestamp"],
    streaming_batch_size=5000,
    max_records=10000
)

# Run full pipeline
output_path = processor.run()
```

#### Factory Functions

##### `create_mc4_processor()`

```python
def create_mc4_processor(
    max_records: Optional[int] = None,
    force: bool = False
) -> HuggingFaceSomaliProcessor:
    """Create pre-configured processor for MC4 dataset."""
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor

processor = create_mc4_processor(max_records=10000)
processor.run()
```

#### See Also

For comprehensive documentation on HuggingFace integration, including streaming architecture, manifest format, and resume capability, see [HuggingFace Integration Guide](../howto/huggingface-integration.md).

---

### SprakbankenSomaliProcessor

**Module**: `somali_dialect_classifier.preprocessing.sprakbanken_somali_processor`

Processor for downloading, extracting, and processing Somali corpora from University of Gothenburg's Språkbanken repository.

#### Class Definition

```python
class SprakbankenSomaliProcessor(BasePipeline):
    """
    Processor for Språkbanken Somali corpora.

    Supports 23 diverse corpora across multiple domains (news, literature,
    science, health, radio, etc.) from University of Gothenburg.
    """
```

#### Constructor

```python
def __init__(
    self,
    corpus_id: str,
    batch_size: int = 10000,
    force: bool = False
)
```

**Parameters**:
- `corpus_id` (str): Corpus identifier (e.g., "cilmi", "ogaden", "all" for all 23 corpora)
- `batch_size` (int, optional): Records per batch. Default: 10000
- `force` (bool, optional): Force reprocessing. Default: False

**Example**:
```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import SprakbankenSomaliProcessor

# Process single corpus
processor = SprakbankenSomaliProcessor(corpus_id="ogaden")
processor.run()

# Process all 23 corpora
processor_all = SprakbankenSomaliProcessor(corpus_id="all")
processor_all.run()
```

#### Helper Functions

##### `list_available_corpora()`

```python
def list_available_corpora() -> List[str]:
    """Return list of all 23 corpus IDs."""
```

##### `get_corpus_info()`

```python
def get_corpus_info(corpus_id: str) -> Dict[str, Any]:
    """Get metadata about specific corpus."""
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    list_available_corpora,
    get_corpus_info
)

# List all corpora
corpora = list_available_corpora()
print(f"Total corpora: {len(corpora)}")  # 23

# Get specific corpus info
info = get_corpus_info("ogaden")
print(f"Domain: {info['domain']}")  # "news_regional"
print(f"License: {info['license']}")  # "CC BY 4.0"
```

#### Available Corpora

**23 total corpora** organized by domain:
- **News** (7): as-2001, as-2016, ah-2010-19, cb, cb-2001-03, cb-2016, ogaden
- **Literature** (4): sheekooyin, sheekooying, suugaan, suugaan-turjuman
- **Science** (2): cilmi, saynis-1980-89
- **Health** (1): caafimaad-1972-79
- **Children** (1): sheekooyin-carruureed
- **Radio** (2): radioden2014, radioswe2014
- **Translation** (1): tid-turjuman
- **QA** (1): kqa
- **Historical** (4): 1971-79, 1993-94, 2001, mk-1972-79

#### See Also

For comprehensive documentation on Språkbanken integration, including all 23 corpora, domain mapping, and metadata extraction, see [Språkbanken Integration Guide](../howto/sprakbanken-integration.md).

---

## Text Cleaners

### WikiMarkupCleaner

**Module**: `somali_dialect_classifier.preprocessing.text_cleaners`

Removes Wikipedia-specific markup from text.

#### Class Definition

```python
class WikiMarkupCleaner:
    """Removes Wikipedia-specific markup from text."""
```

#### Methods

##### `clean()`

```python
def clean(self, text: str) -> str:
    """
    Remove Wikipedia markup from text.

    Args:
        text: Raw Wikipedia text with markup

    Returns:
        Cleaned text without markup
    """
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.text_cleaners import WikiMarkupCleaner

cleaner = WikiMarkupCleaner()
raw_text = "[[Soomaaliya|Somalia]] waa dal {{cite needed}}"
cleaned = cleaner.clean(raw_text)
print(cleaned)  # "Somalia waa dal"
```

**Removes**:
- Wiki links: `[[link|text]]` → `text`
- Simple links: `[[link]]` → `link`
- External links: `[link]` → `link`
- Templates: `{{template}}`
- References: `<ref>...</ref>`
- HTML tags: `<tag>`
- Section headings: `== Heading ==`
- List markers: `*, #, :, ;`

---

### HTMLCleaner

**Module**: `somali_dialect_classifier.preprocessing.text_cleaners`

Removes HTML tags and entities from text.

#### Class Definition

```python
class HTMLCleaner:
    """Removes HTML tags and entities from text."""
```

#### Methods

##### `clean()`

```python
def clean(self, text: str) -> str:
    """
    Remove HTML tags and entities.

    Args:
        text: Text with HTML markup

    Returns:
        Plain text without HTML
    """
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.text_cleaners import HTMLCleaner

cleaner = HTMLCleaner()
html_text = "<p>Warka &amp; macluumaadka <strong>muhiimka ah</strong></p>"
cleaned = cleaner.clean(html_text)
print(cleaned)  # "Warka & macluumaadka muhiimka ah"
```

**Removes**:
- HTML tags: `<p>`, `<div>`, `<strong>`, etc.
- HTML entities: `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#39;`, `&nbsp;`

---

### WhitespaceCleaner

**Module**: `somali_dialect_classifier.preprocessing.text_cleaners`

Normalizes whitespace in text.

#### Class Definition

```python
class WhitespaceCleaner:
    """Normalizes whitespace in text."""
```

#### Methods

##### `clean()`

```python
def clean(self, text: str) -> str:
    """
    Normalize whitespace (collapse multiple spaces/newlines).

    Args:
        text: Text with potentially excessive whitespace

    Returns:
        Text with normalized whitespace
    """
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.text_cleaners import WhitespaceCleaner

cleaner = WhitespaceCleaner()
messy_text = "Warka    \n\n\n\n  macluumaad"
cleaned = cleaner.clean(messy_text)
print(cleaned)  # "Warka\nmacluumaad"
```

---

### TextCleaningPipeline

**Module**: `somali_dialect_classifier.preprocessing.text_cleaners`

Composable text cleaning pipeline that chains multiple cleaners.

#### Class Definition

```python
class TextCleaningPipeline:
    """
    Composable text cleaning pipeline.
    """
```

#### Constructor

```python
def __init__(self, cleaners: list)
```

**Parameters**:
- `cleaners` (list): List of cleaner objects with `clean()` method

#### Methods

##### `clean()`

```python
def clean(self, text: str, min_length: int = 10) -> Optional[str]:
    """
    Run text through all cleaners in sequence.

    Args:
        text: Raw text to clean
        min_length: Minimum length threshold (return None if below)

    Returns:
        Cleaned text or None if below min_length threshold
    """
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.text_cleaners import (
    TextCleaningPipeline,
    WikiMarkupCleaner,
    WhitespaceCleaner
)

pipeline = TextCleaningPipeline([
    WikiMarkupCleaner(),
    WhitespaceCleaner()
])

raw_text = "[[Soomaaliya]]   \n\n\n  waa dal"
cleaned = pipeline.clean(raw_text)
print(cleaned)  # "Soomaaliya\nwaa dal"
```

#### Factory Functions

##### `create_wikipedia_cleaner()`

```python
def create_wikipedia_cleaner() -> TextCleaningPipeline:
    """
    Factory function to create standard Wikipedia cleaning pipeline.

    Returns:
        TextCleaningPipeline configured for Wikipedia text
    """
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.text_cleaners import create_wikipedia_cleaner

cleaner = create_wikipedia_cleaner()
cleaned = cleaner.clean("[[Link|text]]  with   markup")
```

##### `create_html_cleaner()`

```python
def create_html_cleaner() -> TextCleaningPipeline:
    """
    Factory function to create HTML cleaning pipeline for news articles.

    Returns:
        TextCleaningPipeline configured for HTML content (BBC, VOA, etc.)
    """
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.text_cleaners import create_html_cleaner

cleaner = create_html_cleaner()
cleaned = cleaner.clean("<p>Warka &amp; macluumaad</p>")
```

---

## Filters

All filter functions follow the same signature:

```python
def filter_func(cleaned_text: str, **kwargs) -> Tuple[bool, Dict[str, Any]]:
    """
    Filter function signature.

    Args:
        cleaned_text: Cleaned text content
        **kwargs: Filter-specific parameters

    Returns:
        Tuple of (passes, metadata_updates)
        - passes (bool): True if record passes filter
        - metadata_updates (dict): Metadata fields to merge into record
    """
```

### min_length_filter

**Module**: `somali_dialect_classifier.preprocessing.filters`

Filter records below minimum character length.

```python
def min_length_filter(
    cleaned_text: str,
    threshold: int = 50
) -> Tuple[bool, Dict[str, Any]]:
```

**Parameters**:
- `cleaned_text` (str): Cleaned text content
- `threshold` (int, optional): Minimum number of characters. Default: 50

**Returns**:
- `passes` (bool): True if `len(text) >= threshold`
- `metadata_updates` (dict): Empty dict (no metadata to add)

**Example**:
```python
from somali_dialect_classifier.preprocessing.filters import min_length_filter

# Short text (rejected)
passes, meta = min_length_filter("Warka", threshold=50)
print(passes)  # False

# Long text (accepted)
passes, meta = min_length_filter("A" * 100, threshold=50)
print(passes)  # True
```

---

### langid_filter

**Module**: `somali_dialect_classifier.preprocessing.filters`

Filter records not in allowed languages using heuristic detection.

```python
def langid_filter(
    cleaned_text: str,
    allowed_langs: Set[str] = {"so"},
    confidence_threshold: float = 0.5
) -> Tuple[bool, Dict[str, Any]]:
```

**Parameters**:
- `cleaned_text` (str): Cleaned text content
- `allowed_langs` (Set[str], optional): Set of allowed ISO 639-1 codes. Default: `{"so"}`
- `confidence_threshold` (float, optional): Minimum confidence (0-1). Default: 0.5

**Returns**:
- `passes` (bool): True if language in `allowed_langs` and confidence >= threshold
- `metadata_updates` (dict): `{"detected_lang": str, "lang_confidence": float}`

**Example**:
```python
from somali_dialect_classifier.preprocessing.filters import langid_filter

# Somali text (accepted)
passes, meta = langid_filter("Waxaan arkay wadanka Soomaaliya")
print(passes)  # True
print(meta)  # {"detected_lang": "so", "lang_confidence": 0.8}

# English text (rejected)
passes, meta = langid_filter("This is an English sentence")
print(passes)  # False
print(meta)  # {"detected_lang": "en", "lang_confidence": 0.7}
```

---

### dialect_heuristic_filter

**Module**: `somali_dialect_classifier.preprocessing.filters`

Apply dialect heuristics and optionally enrich metadata.

```python
def dialect_heuristic_filter(
    cleaned_text: str,
    ruleset: Dict[str, List[str]],
    enrich_only: bool = True
) -> Tuple[bool, Dict[str, Any]]:
```

**Parameters**:
- `cleaned_text` (str): Cleaned text content
- `ruleset` (Dict[str, List[str]]): Dict mapping dialect names to marker word lists
- `enrich_only` (bool, optional): If True, always pass but add metadata. Default: True

**Returns**:
- `passes` (bool): True if markers found OR `enrich_only=True`
- `metadata_updates` (dict): `{"dialect_markers": {...}, "primary_dialect": str, "total_dialect_markers": int}`

**Example**:
```python
from somali_dialect_classifier.preprocessing.filters import dialect_heuristic_filter

ruleset = {
    "northern": ["waxaan", "baan", "ayaan"],
    "southern": ["waan", "aan"]
}

# Text with northern dialect markers
text = "Waxaan arkay wadanka baan booqday"
passes, meta = dialect_heuristic_filter(text, ruleset, enrich_only=True)

print(passes)  # True (enrich_only=True)
print(meta["primary_dialect"])  # "northern"
print(meta["dialect_markers"])  # {"northern": 2, "southern": 0}
```

---

### namespace_filter

**Module**: `somali_dialect_classifier.preprocessing.filters`

Filter records based on title namespace (primarily for Wikipedia).

```python
def namespace_filter(
    title: str,
    text: str,
    skip_prefixes: List[str]
) -> Tuple[bool, Dict[str, Any]]:
```

**Parameters**:
- `title` (str): Page/article title
- `text` (str): Cleaned text content (unused, for signature consistency)
- `skip_prefixes` (List[str]): List of title prefixes to reject

**Returns**:
- `passes` (bool): True if title doesn't start with any `skip_prefix`
- `metadata_updates` (dict): `{"namespace": str}` if rejected, else `{}`

**Example**:
```python
from somali_dialect_classifier.preprocessing.filters import namespace_filter

skip_prefixes = ["Talk:", "User:", "Wikipedia:"]

# Main article (accepted)
passes, meta = namespace_filter("Soomaaliya", "", skip_prefixes)
print(passes)  # True

# Talk page (rejected)
passes, meta = namespace_filter("Talk:Soomaaliya", "", skip_prefixes)
print(passes)  # False
print(meta)  # {"namespace": "Talk:"}
```

---

### custom_filter

**Module**: `somali_dialect_classifier.preprocessing.filters`

Generic filter wrapper for custom predicates.

```python
def custom_filter(
    cleaned_text: str,
    predicate_func: callable,
    metadata_key: str = "custom_filter_result"
) -> Tuple[bool, Dict[str, Any]]:
```

**Parameters**:
- `cleaned_text` (str): Cleaned text content
- `predicate_func` (callable): Callable that returns `(bool, optional_value)`
- `metadata_key` (str, optional): Key to store result in metadata. Default: `"custom_filter_result"`

**Returns**:
- `passes` (bool): Result of `predicate_func`
- `metadata_updates` (dict): `{metadata_key: value}` if predicate returns value

**Example**:
```python
from somali_dialect_classifier.preprocessing.filters import custom_filter

def has_many_numbers(text):
    count = sum(c.isdigit() for c in text)
    return count > 5, count

text = "Sannadka 2025 waxaa lagu qiyaasay 123456"
passes, meta = custom_filter(text, has_many_numbers, "number_count")

print(passes)  # True
print(meta)  # {"number_count": 12}
```

---

## Record Utilities

### generate_text_hash

**Module**: `somali_dialect_classifier.preprocessing.record_utils`

Generate SHA256 hash of text content for deduplication.

```python
def generate_text_hash(text: str) -> str:
```

**Parameters**:
- `text` (str): Text content to hash

**Returns**:
- `str`: 64-character hex string (SHA256 hash)

**Example**:
```python
from somali_dialect_classifier.preprocessing.record_utils import generate_text_hash

text = "Soomaaliya waa dal ku yaal Geeska Afrika"
hash_value = generate_text_hash(text)
print(hash_value)  # "a3f8d9c2..."
print(len(hash_value))  # 64
```

---

### generate_record_id

**Module**: `somali_dialect_classifier.preprocessing.record_utils`

Generate deterministic ID from components.

```python
def generate_record_id(*components: str) -> str:
```

**Parameters**:
- `*components` (str): String components to combine for ID generation

**Returns**:
- `str`: 64-character hex string (SHA256 hash)

**Example**:
```python
from somali_dialect_classifier.preprocessing.record_utils import generate_record_id

record_id = generate_record_id("Wikipedia-Somali", "Soomaaliya", "https://...")
print(record_id)  # "b7d4e2a1..."
print(len(record_id))  # 64

# Same inputs = same ID (deterministic)
id2 = generate_record_id("Wikipedia-Somali", "Soomaaliya", "https://...")
assert record_id == id2
```

---

### count_tokens

**Module**: `somali_dialect_classifier.preprocessing.record_utils`

Simple whitespace-based token counting.

```python
def count_tokens(text: str) -> int:
```

**Parameters**:
- `text` (str): Text to count tokens in

**Returns**:
- `int`: Number of tokens

**Example**:
```python
from somali_dialect_classifier.preprocessing.record_utils import count_tokens

text = "Soomaaliya waa dal ku yaal Geeska Afrika"
token_count = count_tokens(text)
print(token_count)  # 7
```

---

### build_silver_record

**Module**: `somali_dialect_classifier.preprocessing.record_utils`

Build a standardized silver dataset record.

```python
def build_silver_record(
    text: str,
    title: str,
    source: str,
    url: str,
    date_accessed: str,
    source_type: str = "wiki",
    language: str = "so",
    license_str: str = "CC-BY-SA-3.0",
    pipeline_version: str = "2.1.0",
    source_metadata: Optional[dict] = None,
    date_published: Optional[str] = None,
    topic: Optional[str] = None,
    register: str = "formal",
) -> dict:
```

**Parameters**:
- `text` (str): Cleaned text content
- `title` (str): Document title
- `source` (str): Source name (e.g., "Wikipedia-Somali")
- `url` (str): Source URL
- `date_accessed` (str): ISO date when data was accessed
- `source_type` (str, optional): Type of source (wiki, news, social, etc.). Default: "wiki"
- `language` (str, optional): ISO 639-1 language code. Default: "so"
- `license_str` (str, optional): License identifier. Default: "CC-BY-SA-3.0"
- `pipeline_version` (str, optional): Version of processing pipeline. Default: "2.1.0"
- `source_metadata` (dict, optional): Additional source-specific metadata. Default: None
- `date_published` (str, optional): ISO date when content was published. Default: None
- `topic` (str, optional): Content topic/category. Default: None
- `register` (str, optional): Linguistic register. Default: "formal". Valid: "formal", "informal", "colloquial"

**Returns**:
- `dict`: Dictionary with standardized schema

**Schema** (v2.1):
```python
{
    "id": str,               # SHA256 hash of title + url
    "text": str,             # Cleaned text content
    "title": str,            # Document title
    "source": str,           # Source name
    "source_type": str,      # Source type (wiki, news, etc.)
    "url": str,              # Source URL
    "source_id": None,       # External source ID (if available)
    "date_published": str,   # ISO date published (optional)
    "date_accessed": str,    # ISO date accessed
    "language": str,         # ISO 639-1 language code
    "license": str,          # License string
    "topic": str,            # Topic/category (optional)
    "tokens": int,           # Token count
    "text_hash": str,        # SHA256 hash of text
    "pipeline_version": str, # Pipeline version
    "source_metadata": str,  # JSON-serialized metadata
    "domain": str,           # Content domain (v2.0)
    "embedding": str,        # Embedding vector (v2.0, currently null)
    "register": str,         # Linguistic register (v2.1): formal/informal/colloquial
}
```

**Example**:
```python
from somali_dialect_classifier.preprocessing.record_utils import build_silver_record

record = build_silver_record(
    text="Soomaaliya waa dal ku yaal Geeska Afrika",
    title="Soomaaliya",
    source="Wikipedia-Somali",
    url="https://so.wikipedia.org/wiki/Soomaaliya",
    date_accessed="2025-01-15",
    source_type="wiki",
    language="so",
    license_str="CC-BY-SA-3.0",
    source_metadata={"wiki_code": "sowiki"},
    register="formal"  # NEW in v2.1
)

print(record["id"])        # "a3f8d9c2..."
print(record["tokens"])    # 7
print(record["text_hash"]) # "b7d4e2a1..."
print(record["register"])  # "formal"
```

---

## Silver Dataset Writer

### SilverDatasetWriter

**Module**: `somali_dialect_classifier.preprocessing.silver_writer`

Writes records to silver dataset in Parquet format with partitioning and schema validation.

#### Class Definition

```python
class SilverDatasetWriter:
    """
    Writes records to silver dataset in Parquet format.

    Handles partitioning, schema validation, and file I/O.
    """
```

#### Schema (v2.1)

```python
SCHEMA = pa.schema([
    ("id", pa.string()),
    ("text", pa.string()),
    ("title", pa.string()),
    ("source", pa.string()),
    ("source_type", pa.string()),
    ("url", pa.string()),
    ("source_id", pa.string()),
    ("date_published", pa.string()),
    ("date_accessed", pa.string()),
    ("language", pa.string()),
    ("license", pa.string()),
    ("topic", pa.string()),
    ("tokens", pa.int64()),
    ("text_hash", pa.string()),
    ("pipeline_version", pa.string()),
    ("source_metadata", pa.string()),  # JSON string
    ("domain", pa.string()),            # v2.0
    ("embedding", pa.string()),         # v2.0
    ("register", pa.string()),          # v2.1 - NEW: formal/informal/colloquial
])
```

**Valid register values**: "formal", "informal", "colloquial"
**Validation**: `VALID_REGISTERS = {"formal", "informal", "colloquial"}`

#### Constructor

```python
def __init__(self, base_dir: Optional[Path] = None)
```

**Parameters**:
- `base_dir` (Path, optional): Base directory for silver datasets. Default: None (uses config default)

**Example**:
```python
from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter

# Use default config path
writer = SilverDatasetWriter()

# Use custom path
from pathlib import Path
writer = SilverDatasetWriter(base_dir=Path("/data/silver"))
```

#### Methods

##### `write()`

```python
def write(
    self,
    records: List[dict],
    source: str,
    date_accessed: str,
    partition_num: Optional[int] = None,
) -> Optional[Path]:
```

**Parameters**:
- `records` (List[dict]): List of record dictionaries
- `source` (str): Source name (e.g., "Wikipedia-Somali")
- `date_accessed` (str): ISO date for partitioning
- `partition_num` (int, optional): Partition number. Default: None (auto-increment)

**Returns**:
- `Path`: Path to written Parquet file, or None if no records

**Example**:
```python
from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter
from somali_dialect_classifier.preprocessing.record_utils import build_silver_record

writer = SilverDatasetWriter()

records = [
    build_silver_record(
        text="Text 1",
        title="Title 1",
        source="Wikipedia-Somali",
        url="https://example.com/1",
        date_accessed="2025-01-15"
    ),
    build_silver_record(
        text="Text 2",
        title="Title 2",
        source="Wikipedia-Somali",
        url="https://example.com/2",
        date_accessed="2025-01-15"
    ),
]

parquet_path = writer.write(
    records=records,
    source="Wikipedia-Somali",
    date_accessed="2025-01-15"
)

print(parquet_path)
# data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-01-15/part-0000.parquet
```

##### `read()`

```python
def read(self, source: str, date_accessed: str) -> pa.Table:
```

**Parameters**:
- `source` (str): Source name
- `date_accessed` (str): ISO date

**Returns**:
- `pa.Table`: PyArrow table with all records

**Example**:
```python
from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter

writer = SilverDatasetWriter()
table = writer.read(source="Wikipedia-Somali", date_accessed="2025-01-15")

print(f"Rows: {table.num_rows}")
print(f"Columns: {table.column_names}")

# Convert to pandas
df = table.to_pandas()
print(df.head())
```

---

## See Also

- [Configuration Guide](CONFIGURATION.md) - Environment variables and configuration
- [Architecture Documentation](ARCHITECTURE.md) - System design patterns
- [Data Pipeline](DATA_PIPELINE.md) - ETL pipeline details
- [Testing Guide](TESTING.md) - Testing strategies and examples
- [Deployment Guide](DEPLOYMENT.md) - Production deployment

---

**Version**: 1.0.0
**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
