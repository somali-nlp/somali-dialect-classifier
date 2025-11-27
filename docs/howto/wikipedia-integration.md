# Wikipedia-Somali Integration Guide

**Integrating and processing Somali Wikipedia content for dialect classification.**

**Last Updated:** 2025-11-21

This guide explains how to integrate and process Somali Wikipedia articles into your Somali Dialect Classifier pipeline.

## Table of Contents

1. [Overview](#overview)
2. [What is Wikipedia-Somali?](#what-is-wikipedia-somali)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Data Flow](#data-flow)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [Directory Structure](#directory-structure)
9. [Quality Filters](#quality-filters)
10. [Performance Considerations](#performance-considerations)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

---

## Overview

The Wikipedia-Somali processor downloads, extracts, and processes articles from the Somali Wikipedia (sowiki) to create high-quality training data for dialect classification. Wikipedia provides **formal, encyclopedic content** that represents standard written Somali.

### Key Features

- **Large corpus**: ~50,000+ articles covering diverse topics
- **Formal language**: Encyclopedia-style writing, standard orthography
- **Structured content**: Consistent formatting and organization
- **Open license**: CC-BY-SA-3.0 allows reuse and modification
- **Regular updates**: Wikipedia dumps available daily/weekly
- **Rich metadata**: Titles, categories, revision history

### Use Cases

- Training formal Somali language models
- Establishing baseline for standard Somali orthography
- Topic classification (geography, history, science, etc.)
- Named entity recognition (people, places, organizations)
- Comparative analysis with informal/dialectal sources (BBC, social media)

---

## What is Wikipedia-Somali?

### About Somali Wikipedia

[Somali Wikipedia](https://so.wikipedia.org) (sowiki) is the Somali-language edition of Wikipedia, the free online encyclopedia. As of 2025, it contains over 7,000 articles covering topics from Somali culture, history, and geography to general knowledge articles translated from other Wikipedias.

### Content Characteristics

**Language style**: Formal, encyclopedic Somali
- Standard orthography using Latin script
- Academic/educational tone
- Minimal dialectal variation (standardized)
- Technical terminology in various domains

**Topic distribution**:
- Geography and places (cities, regions, countries)
- History and historical figures
- Culture and society
- Science and technology
- Sports and entertainment
- Biographies of notable people

### MediaWiki XML Dumps

Wikipedia provides its data as **MediaWiki XML dumps** that contain:
- Page content in WikiMarkup format
- Revision history and metadata
- Page titles and namespaces
- Categories and links

**Dump files**:
- Format: Compressed XML (`.xml.bz2`)
- Size: ~50-100 MB compressed, ~500 MB uncompressed
- Update frequency: Weekly (latest dump always available)
- Download source: [Wikimedia Dumps](https://dumps.wikimedia.org/sowiki/)

---

## Installation

No additional dependencies are required beyond the base project requirements. The Wikipedia processor uses:

- `mwxml`: MediaWiki XML parsing (automatically installed with project)
- `requests`: HTTP downloads
- `bz2`: Decompression (Python standard library)

```bash
# Install project with all dependencies
pip install -e ".[config]"

# Verify mwxml is installed
python -c "import mwxml; print('mwxml OK')"
```

---

## Quick Start

### CLI Usage

```bash
# Download and process Wikipedia (simplest method)
wikisom-download

# Force reprocessing (rebuild even if files exist)
wikisom-download --force
```

### Python API Usage

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

# Process Wikipedia dump
processor = WikipediaSomaliProcessor()
processor.run()  # download() -> extract() -> process()
```

---

## MLOps Infrastructure Integration

This processor is fully integrated with production MLOps infrastructure:

**Structured Logging:**
```python
# Logs include run_id, source, phase automatically
{
  "run_id": "wiki_20250119_123456",
  "source": "Wikipedia-Somali",
  "phase": "fetch",
  "message": "...",
  ...
}
```

**Metrics Collected:**
- Discovery: `urls_discovered`, `pages_discovered`
- Fetch: `download_duration_ms`, `download_size_bytes`
- Processing: `records_processed`, `filter_statistics`

**Quality Reports:**
Generated automatically at `data/reports/{run_id}_quality_report.md`

**Resume Capability:**
The crawl ledger tracks processing state, enabling resume after interruptions:
```bash
# First run - process partial dump
wikisom-download

# Resume - skips already processed pages
wikisom-download  # Continues from last processed page
```

---

## Data Flow

The Wikipedia processor follows a multi-phase pipeline with **two-level discovery-stage deduplication**:

```
┌─────────────────────────────────────────────────────────┐
│ Discovery Stage: Dump-Level Check                      │
│ - Check if dump URL in ledger                         │
│ - Make HEAD request with If-None-Match/If-Modified    │
│ - If 304 Not Modified → EXIT (skip all below)         │
│ - If 200 OK → Continue to download                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 1: DOWNLOAD                                       │
│ - Download dump with ETag/Last-Modified tracking      │
│ - Mark dump URL as fetched with HTTP metadata         │
│ → Output: data/raw/.../sowiki-latest.xml.bz2          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2: PARSE                                          │
│ - Parse MediaWiki XML with mwxml                       │
│ - Extract main namespace articles (namespace=0)        │
│ - Collect article metadata (title, URL, timestamp)     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Discovery Stage: Article-Level Check                   │
│ - Query ledger for processed article URLs             │
│ - Filter out already-processed articles                │
│ - If all articles processed → EXIT                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 3: EXTRACT                                        │
│ - Convert WikiMarkup to plain text (new articles only) │
│ → Output: data/staging/.../extracted.txt              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 4: PROCESS                                        │
│ - Apply text cleaning pipeline                         │
│ - Execute quality filters                              │
│ - Build silver records with metadata                   │
│ → Output: data/processed/silver/.../part-0000.parquet │
└─────────────────────────────────────────────────────────┘
```

### Discovery-Stage Deduplication (Two Levels)

**Level 1: Dump-Level (HTTP Conditional Requests)**

Checks if the Wikipedia dump file itself has changed using standard HTTP mechanisms.

**Benefits:**
- Saves bandwidth: No re-download if dump unchanged (~7.2MB)
- Saves CPU: No parsing if dump unchanged (~44 seconds)
- Uses HTTP standard: ETag and Last-Modified headers (RFC 7232)

**Level 2: Article-Level (URL Filtering)**

When a new dump is downloaded (changed ETag), filters out articles already processed from previous dumps.

**Benefits:**
- Processes only new articles (typically 0-100 per day)
- Prevents duplicate silver records
- Enables incremental processing of growing corpus

**Expected Behavior:**

- **Run 1 (First time):** No ledger entries → Download dump → Parse 15,507 articles → Process 9,960 articles
- **Run 2 (Same dump):** HEAD request → **304 Not Modified** → Exit early (0 downloads, 0 processing)
- **Run 3 (New dump, 10 new articles):** HEAD request → 200 OK → Download → Parse 15,517 → Filter to 10 new → Process 10

### Phase 1: Download

```python
def download(self) -> Path:
    """Download Wikipedia dump from Wikimedia."""

    # URL construction
    url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

    # Skip if already downloaded (unless force=True)
    if raw_file.exists() and not self.force:
        logger.info(f"Dump already exists: {raw_file}")
        return raw_file

    # Stream download with progress tracking
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(raw_file, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
            f.write(chunk)
            downloaded += len(chunk)
            logger.info(f"Downloaded {downloaded}/{total_size} bytes")

    return raw_file
```

**Output**: `data/raw/source=Wikipedia-Somali/date_accessed=2025-10-19/sowiki-latest-pages-articles.xml.bz2`

### Phase 2: Extract

```python
def extract(self) -> Path:
    """Extract articles from MediaWiki XML dump."""

    import mwxml
    import bz2

    # Open compressed XML dump
    dump = mwxml.Dump.from_file(bz2.open(raw_file))

    # Stream articles to staging file
    with open(staging_file, 'w') as f:
        for page in dump:
            # Filter: Only main namespace articles
            if page.namespace != 0:
                continue

            # Get latest revision text
            for revision in page:
                text = revision.text or ""
                title = page.title

                # Write to staging
                f.write(f"TITLE: {title}\n")
                f.write(f"{text}\n")
                f.write("="*80 + "\n\n")
                break  # Only latest revision

    return staging_file
```

**Output**: `data/staging/source=Wikipedia-Somali/date_accessed=2025-10-19/wikisom_raw.txt`

### Phase 3: Process

```python
def process(self) -> Path:
    """Clean, filter, and write to silver dataset."""

    records = []

    for raw_record in self._extract_records():
        # 1. Clean text (remove WikiMarkup, normalize whitespace)
        cleaned_text = self.text_cleaner.clean(raw_record.text)

        # 2. Apply filters (length, language, namespace)
        passes_filters, metadata = self._apply_filters(cleaned_text, raw_record)

        if not passes_filters:
            continue

        # 3. Build silver record
        record = build_silver_record(
            text=cleaned_text,
            title=raw_record.title,
            source="Wikipedia-Somali",
            url=f"https://so.wikipedia.org/wiki/{raw_record.title}",
            date_accessed=self.date_accessed,
            source_type="wiki",
            language="so",
            license_str="CC-BY-SA-3.0",
            source_metadata=metadata
        )
        records.append(record)

    # 4. Write to Parquet
    self.silver_writer.write(records, "Wikipedia-Somali", self.date_accessed)
```

**Output**: `data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-10-19/part-0000.parquet`

---

## Configuration

### Environment Variables

```bash
# Set in .env file or export
SDC_SCRAPING__WIKIPEDIA__DOWNLOAD_URL="https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"
SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=5000
SDC_SCRAPING__WIKIPEDIA__MIN_LENGTH_THRESHOLD=50
SDC_SCRAPING__WIKIPEDIA__LANGID_CONFIDENCE_THRESHOLD=0.3
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_URL` | Wikimedia latest dump | URL to download XML dump from |
| `BATCH_SIZE` | 5000 | Records per Parquet write batch |
| `MIN_LENGTH_THRESHOLD` | 50 | Minimum characters for quality filter |
| `LANGID_CONFIDENCE_THRESHOLD` | 0.3 | Language detection confidence (0-1) |

### Programmatic Configuration

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

# Custom configuration
processor = WikipediaSomaliProcessor(force=True)

# Access config
from somali_dialect_classifier.config import get_config
config = get_config()
print(config.scraping.wikipedia.download_url)
```

---

## Usage Examples

### Example 1: Basic Processing

```bash
# CLI
wikisom-download
```

```python
# Python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

processor = WikipediaSomaliProcessor()
output_path = processor.run()
print(f"Processed data: {output_path}")
```

**Expected output**:
```
data/raw/.../sowiki-latest-pages-articles.xml.bz2  # 50-100 MB
data/staging/.../wikisom_raw.txt                   # 500 MB
data/processed/silver/.../part-0000.parquet        # 40 MB
```

### Example 2: Phased Processing

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

processor = WikipediaSomaliProcessor()

# Phase 1: Download only
dump_path = processor.download()
print(f"Downloaded to: {dump_path}")

# Phase 2: Extract only (requires download first)
staging_path = processor.extract()
print(f"Extracted to: {staging_path}")

# Phase 3: Process only (requires extract first)
silver_path = processor.process()
print(f"Processed to: {silver_path}")
```

### Example 3: Force Reprocessing

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

# Force rebuild (ignore existing files)
processor = WikipediaSomaliProcessor(force=True)
processor.run()
```

### Example 4: Custom Filters

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor
from somali_dialect_classifier.preprocessing.filters import custom_filter

# Create processor
processor = WikipediaSomaliProcessor()

# Add custom filter (e.g., only keep geography articles)
def is_geography(text: str) -> tuple:
    geography_terms = ["gobol", "magaalo", "waddan", "degmo"]
    has_geo = any(term in text.lower() for term in geography_terms)
    return has_geo, {"is_geography": has_geo}

processor.record_filters.append((custom_filter, {
    "predicate": is_geography,
    "metadata_key": "is_geography"
}))

# Process with custom filter
processor.process()
```

---

## Directory Structure

After running the Wikipedia processor:

```
data/
├── raw/
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-10-19/
│           └── sowiki-latest-pages-articles.xml.bz2  # Original dump (external source, no run_id)
│
├── staging/
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-10-19/
│           └── wikipedia-somali_20251019_143045_staging_extracted.txt  # Extracted text with run_id
│
├── processed/
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-10-19/
│           └── wikipedia-somali_20251019_143045_processed_cleaned.txt  # Cleaned text with run_id
│
└── processed/silver/
    └── source=Wikipedia-Somali/
        └── date_accessed=2025-10-19/
            ├── wikipedia-somali_20251019_143045_silver_part-0000.parquet  # Final dataset
            └── wikipedia-somali_20251019_143045_silver_metadata.json     # Metadata sidecar (NEW)
```

**File Naming Pattern**: `{source-slug}_{run_id}_{layer}_{descriptive-name}.{ext}`
- **run_id**: Timestamp format `YYYYMMDD_HHMMSS` (e.g., `20251019_143045`)
- **Traceability**: run_id links files to logs, metrics, and quality reports
- **Partition Consistency**: All layers use `date_accessed` (not `date_processed`)

### Silver Dataset Schema

Each record includes:

```python
{
    "id": "hash...",
    "text": "Cleaned article text",
    "title": "Article title",
    "source": "Wikipedia-Somali",
    "source_type": "wiki",
    "url": "https://so.wikipedia.org/wiki/Title",
    "date_accessed": "2025-10-19",
    "language": "so",
    "license": "CC-BY-SA-3.0",
    "tokens": 1234,
    "text_hash": "sha256...",
    "source_metadata": {
        "namespace": 0,
        "detected_lang": "so",
        "lang_confidence": 0.85
    }
}
```

---

## Quality Filters

The Wikipedia processor applies several quality filters:

### 1. Minimum Length Filter

**Purpose**: Remove stub articles and very short pages

```python
min_length_filter(cleaned_text, threshold=50)
```

- Rejects articles with < 50 characters
- Prevents low-quality stubs from entering dataset
- ~4-5% rejection rate on Somali Wikipedia

**Example rejection**:
```
Title: "Xamar"
Text: "Xamar waa magaalada caasimadda ah."  # Only 36 chars
Status: REJECTED (below 50 char threshold)
```

### 2. Language Identification Filter

**Purpose**: Filter non-Somali content (foreign language articles)

```python
langid_filter(cleaned_text, allowed_langs={"so"}, confidence_threshold=0.3)
```

- Uses heuristic Somali word vocabulary (120+ common words)
- Confidence threshold: 0.3 (relaxed for short articles)
- ~10-15% rejection rate on Somali Wikipedia

**Example rejection**:
```
Title: "Python (programming language)"
Text: "Python is a high-level programming language..."  # English
Status: REJECTED (detected_lang='en', confidence=0.9)
```

### 3. Namespace Filter

**Purpose**: Only include main namespace articles (exclude meta pages)

```python
namespace_filter(title, skip_prefixes=["Talk:", "User:", "Wikipedia:", "Template:", "Category:"])
```

**Wikipedia namespaces**:
- **Namespace 0** (main): Regular articles → ✅ **INCLUDE**
- **Namespace 1** (talk): Discussion pages → ❌ **EXCLUDE**
- **Namespace 2** (user): User pages → ❌ **EXCLUDE**
- **Namespace 4** (wikipedia): Project pages → ❌ **EXCLUDE**
- **Namespace 10** (template): Templates → ❌ **EXCLUDE**
- **Namespace 14** (category): Category pages → ❌ **EXCLUDE**

**Example filtering**:
```
Title: "Soomaaliya"           → PASS (namespace 0)
Title: "Talk:Soomaaliya"      → REJECT (namespace 1)
Title: "User:Ahmed"           → REJECT (namespace 2)
Title: "Template:Infobox"     → REJECT (namespace 10)
```

### Filter Statistics

After processing, the pipeline logs filter statistics:

```
INFO - Processing 50,000 records from Wikipedia-Somali
INFO - Filter statistics:
INFO -   filtered_by_min_length_filter: 2,300 records (4.6%)
INFO -   filtered_by_langid_filter: 5,700 records (11.4%)
INFO -   filtered_by_namespace_filter: 0 records (0.0%)  # Already filtered during extraction
INFO - Successfully processed 42,000 records (84.0%)
```

---

## Performance Considerations

### Download Speed

- **File size**: ~50-100 MB compressed
- **Download time**: 1-5 minutes (depends on internet speed)
- **Resumable**: Partial downloads NOT supported (full re-download on failure)

**Optimization tip**: Download once, process multiple times with `force=False`

### Extraction Speed

- **Throughput**: ~500-800 articles/second
- **Bottleneck**: XML parsing (CPU-bound)
- **Memory usage**: ~200 MB peak (streaming with 10MB buffer)

**Benchmarks** (M1 MacBook Pro):
- 50,000 articles: ~60-120 seconds extraction time
- Memory-safe: Uses streaming, not loading entire dump into RAM

### Processing Speed

- **Throughput**: ~300-500 records/second
- **Bottleneck**: Text cleaning (regex-heavy)
- **Batch writing**: 5000 records/batch (prevents memory overflow)

**Total pipeline time**: ~3-5 minutes for full Wikipedia dump

### Disk Usage

| Layer | Format | Size (50k articles) | Compression Ratio |
|-------|--------|---------------------|-------------------|
| Raw | XML.bz2 | 50-100 MB | 1x (baseline) |
| Staging | TXT | 500 MB | 0.1x (decompressed) |
| Processed | TXT | 450 MB | 0.11x |
| Silver | Parquet (snappy) | 40 MB | 12.5x (compressed) |

**Storage recommendation**: Keep raw and silver, delete staging and processed after verification.

---

## Troubleshooting

### Issue: Download Hangs or Times Out

**Symptoms**:
```
INFO - Downloading from https://dumps.wikimedia.org/...
(no progress for 5+ minutes)
```

**Solutions**:
1. Check internet connection
2. Verify Wikimedia dumps server is up: https://dumps.wikimedia.org/
3. Try manual download with `wget` or `curl`:
   ```bash
   wget https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2
   mv sowiki-latest-pages-articles.xml.bz2 data/raw/source=Wikipedia-Somali/date_accessed=$(date +%Y-%m-%d)/
   ```
4. Use older dump version (replace `latest` with specific date)

### Issue: "No module named 'mwxml'"

**Symptoms**:
```python
ModuleNotFoundError: No module named 'mwxml'
```

**Solution**:
```bash
pip install mwxml
# Or reinstall project with dependencies
pip install -e ".[config]"
```

### Issue: Out of Memory During Extraction

**Symptoms**:
```
MemoryError: Unable to allocate array
```

**Solution**: This should NOT happen with the current implementation (uses streaming). If it does:
1. Check `batch_size` configuration (default: 5000)
2. Reduce batch size in config:
   ```python
   from somali_dialect_classifier.config import get_config
   config = get_config()
   config.scraping.wikipedia.batch_size = 1000
   ```

### Issue: Empty Staging File

**Symptoms**:
```
data/staging/.../wikisom_raw.txt exists but is 0 bytes
```

**Solutions**:
1. Check if XML dump is corrupted:
   ```bash
   bzip2 -t data/raw/.../sowiki-latest-pages-articles.xml.bz2
   ```
2. Re-download with `force=True`:
   ```bash
   wikisom-download --force
   ```

### Issue: Processing Returns No Records

**Symptoms**:
```
INFO - Successfully processed 0 records (0.0%)
```

**Solutions**:
1. Check filter thresholds (may be too strict):
   ```python
   # Lower thresholds temporarily
   processor.record_filters = [
       (min_length_filter, {"threshold": 10}),  # Very low threshold
       (langid_filter, {"confidence_threshold": 0.1})  # Very relaxed
   ]
   ```
2. Check staging file manually:
   ```bash
   head -n 100 data/staging/.../wikisom_raw.txt
   ```

### Issue: Silver Dataset Schema Validation Error

**Symptoms**:
```
pa.ArrowInvalid: Field 'tokens' expected int32, got int64
```

**Solution**: This indicates a type mismatch in record building. File a bug report - this should not happen with the standard processor.

---

## Best Practices

### 1. Download Once, Process Many Times

```python
# Initial download
processor = WikipediaSomaliProcessor()
processor.download()

# Experiment with different filters (no re-download)
processor.force = False  # Skip existing files
processor.record_filters = [...]  # Custom filters
processor.extract()
processor.process()
```

### 2. Use Force Flag Judiciously

```python
# Force re-download (slow, only when necessary)
processor = WikipediaSomaliProcessor(force=True)
processor.download()  # Re-downloads entire dump

# Force reprocess only (faster, keeps download)
processor = WikipediaSomaliProcessor(force=True)
processor.download()  # Skipped (not forced)
processor.extract()   # Forced
processor.process()   # Forced
```

### 3. Monitor Filter Statistics

After processing, review logs to understand rejection rates:

```bash
# Check logs
tail -n 100 logs/download_wikisom.log | grep "filter"
```

High rejection rates (>20%) may indicate:
- Overly strict thresholds
- Language detection issues
- Unexpected content in Wikipedia dump

### 4. Validate Output Quality

```python
import pandas as pd

# Read silver dataset
df = pd.read_parquet("data/processed/silver/source=Wikipedia-Somali/")

# Quality checks
print(f"Total records: {len(df)}")
print(f"Average tokens: {df['tokens'].mean()}")
print(f"Language distribution: {df['language'].value_counts()}")
print(f"Source types: {df['source_type'].value_counts()}")

# Check for anomalies
short_articles = df[df['tokens'] < 100]
print(f"Short articles (<100 tokens): {len(short_articles)}")
```

### 5. Version Control Your Dumps

Keep track of which dump version you processed:

```bash
# Rename dump with date
mv data/raw/source=Wikipedia-Somali/date_accessed=2025-10-19/sowiki-latest-pages-articles.xml.bz2 \
   data/raw/source=Wikipedia-Somali/date_accessed=2025-10-19/sowiki-20251019-pages-articles.xml.bz2
```

### 6. Backup Silver Datasets

Silver datasets are your production asset - back them up:

```bash
# Compress and backup
tar -czf wikipedia-silver-20251019.tar.gz data/processed/silver/source=Wikipedia-Somali/

# Upload to cloud storage (example: S3)
aws s3 cp wikipedia-silver-20251019.tar.gz s3://somali-nlp-backups/
```

---

## Advanced Usage

### Custom Text Cleaning Pipeline

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor
from somali_dialect_classifier.preprocessing.text_cleaners import (
    TextCleaningPipeline,
    WikiMarkupCleaner,
    WhitespaceCleaner
)

class CustomCleaner:
    def clean(self, text: str) -> str:
        # Custom cleaning logic
        text = text.replace("CUSTOM_PATTERN", "")
        return text

processor = WikipediaSomaliProcessor()
processor.text_cleaner = TextCleaningPipeline([
    WikiMarkupCleaner(),
    CustomCleaner(),  # Insert custom cleaner
    WhitespaceCleaner()
])

processor.process()
```

### Selective Article Processing

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

class GeographyOnlyProcessor(WikipediaSomaliProcessor):
    def _extract_records(self):
        """Override to filter by category/title."""
        for record in super()._extract_records():
            if any(keyword in record.title.lower() for keyword in ["gobol", "magaalo", "waddan"]):
                yield record
```

### Parallel Processing

```python
from multiprocessing import Pool
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

def process_batch(batch_num):
    processor = WikipediaSomaliProcessor()
    # Process specific batch range
    # (requires custom implementation)
    pass

with Pool(4) as pool:
    pool.map(process_batch, range(4))
```

---

## Integration with Other Sources

Wikipedia data integrates seamlessly with other sources:

```python
from somali_dialect_classifier.preprocessing import (
    WikipediaSomaliProcessor,
    BBCSomaliProcessor,
    HuggingFaceSomaliProcessor,
    SprakbankenSomaliProcessor
)

# Process all sources
WikipediaSomaliProcessor().run()
BBCSomaliProcessor(max_articles=1000).run()
HuggingFaceSomaliProcessor(dataset_name="allenai/c4", max_records=10000).run()
SprakbankenSomaliProcessor(corpus_id="all").run()

# All write to same silver dataset with consistent schema
# Query by source type:
# df[df['source'] == 'Wikipedia-Somali']  # Formal, encyclopedic
# df[df['source'] == 'BBC-Somali']        # Journalistic, current events
```

---

## References

- **Somali Wikipedia**: https://so.wikipedia.org
- **Wikimedia Dumps**: https://dumps.wikimedia.org/sowiki/
- **MediaWiki XML Format**: https://www.mediawiki.org/wiki/Manual:Importing_XML_dumps
- **mwxml Documentation**: https://github.com/mediawiki-utilities/python-mwxml
- **License (CC-BY-SA-3.0)**: https://creativecommons.org/licenses/by-sa/3.0/

---

## Next Steps

After processing Wikipedia data:

1. **Verify Deduplication**: Discovery-stage deduplication now prevents duplicates automatically
   ```bash
   # Check ledger statistics to verify deduplication
   sqlite3 data/ledger/crawl_ledger.db \
     "SELECT state, COUNT(*) FROM crawl_ledger WHERE source='wikipedia' GROUP BY state;"

   # See comprehensive deduplication guide
   # docs/howto/deduplication.md
   ```

2. **Analyze**: Examine corpus statistics
   ```python
   import pandas as pd
   df = pd.read_parquet("data/processed/silver/source=Wikipedia-Somali/")
   print(df['tokens'].describe())
   ```

3. **Combine**: Merge with other sources for diverse training data
4. **Label**: Proceed to annotation phase for dialect labeling

---

## Related Documentation

- [Data Pipeline Overview](../overview/data-pipeline-architecture.md) - ETL architecture
- [Processing Pipelines Guide](processing-pipelines.md) - Walkthroughs for all sources
- [API Reference](../reference/api.md) - WikipediaSomaliProcessor API
- [Custom Filters Guide](custom-filters.md) - Creating custom quality filters
- [BBC Integration Guide](bbc-integration.md) - News article processing
- [HuggingFace Integration Guide](huggingface-integration.md) - Large-scale web corpora
- [Språkbanken Integration Guide](sprakbanken-integration.md) - Academic corpora

---

**Maintainers**: Somali NLP Contributors
