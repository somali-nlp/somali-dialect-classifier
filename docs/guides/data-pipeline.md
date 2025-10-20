# Data Collection and Processing Pipeline

**Production-ready infrastructure for collecting, processing, and curating Somali language data from multiple sources.**

---

## Overview

The Somali Dialect Classifier employs a comprehensive data pipeline that collects text from four diverse sources, applies quality filters, removes duplicates, and outputs a unified silver dataset ready for model training.

### Key Features

- **Four Production Data Sources** - Wikipedia, BBC News, HuggingFace Datasets, Språkbanken Corpora
- **Structured Logging** - JSON logs with automatic context injection (run_id, source, phase)
- **Metrics Collection** - Discovery, fetch, processing metrics with automated quality reports
- **Crawl Ledger** - Persistent URL state tracking with resume capability and conditional requests
- **Two-Tier Deduplication** - Exact SHA256 hashing + MinHash LSH for near-duplicates
- **Quality Filters** - Pluggable filter framework (length, language, dialect heuristics)
- **Unified Silver Dataset** - Consistent Parquet schema across all sources
- **Workflow Orchestration** - Prefect-based coordination for parallel execution

---

## Architecture

### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                              │
├──────────────┬─────────────┬─────────────────┬───────────────┤
│  Wikipedia   │  BBC News   │  HuggingFace    │  Språkbanken  │
│  ~50K docs   │  News       │  MC4: ~100-200K │  23 corpora   │
└──────┬───────┴──────┬──────┴────────┬────────┴───────┬───────┘
       │              │               │                │
       ▼              ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY PHASE                          │
│  • URL Discovery & Ledger Tracking                         │
│  • RSS Feed Scraping (BBC)                                 │
│  • Manifest Creation (HuggingFace)                         │
│  • Corpus Listing (Språkbanken)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   EXTRACTION PHASE                          │
│  • HTTP Fetching with Conditional Requests                 │
│  • Adaptive Rate Limiting                                  │
│  • XML/JSON Parsing                                        │
│  • JSONL Batching (Streaming)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING PHASE                           │
│  • Text Cleaning (WikiMarkup, HTML, Whitespace)           │
│  • Quality Filters (Length, Language, Dialect)            │
│  • Hash Computation & Deduplication                        │
│  • Metadata Enrichment                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               SILVER DATASET (Parquet)                      │
│  • Unified Schema Across All Sources                       │
│  • Partitioned by Source & Date                            │
│  • Ready for Model Training                                │
└─────────────────────────────────────────────────────────────┘
```

### Core Infrastructure

#### 1. Crawl Ledger

Persistent SQLite database tracking URL states:

- **States**: discovered, fetched, processed, failed, skipped, duplicate
- **HTTP Metadata**: ETag, Last-Modified (for conditional requests)
- **Deduplication**: text_hash, minhash_signature
- **RSS Throttling**: Frequency-limited feed checking

```python
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()

# Discover URLs
ledger.discover_url("https://example.com/article", "bbc", metadata={...})

# Check if should fetch (skip if already processed)
if ledger.should_fetch_url(url, force=False):
    # Fetch with conditional headers
    headers = ledger.get_conditional_headers(url)
    # ... fetch logic ...
    ledger.mark_fetched(url, http_status=200, etag=etag)

# Get statistics
stats = ledger.get_statistics("bbc")
print(stats)
# {
#   "total_urls": 1234,
#   "by_state": {"processed": 1000, "duplicate": 50, ...},
#   "dedup_rate": 0.05
# }
```

#### 2. Deduplication Engine

Two-tier deduplication system:

- **Exact Duplicates**: SHA256 hash comparison
- **Near-Duplicates**: MinHash LSH with 85% similarity threshold

```python
from somali_dialect_classifier.preprocessing.dedup import DedupEngine, DedupConfig

config = DedupConfig(
    hash_fields=["text", "url"],
    enable_minhash=True,
    similarity_threshold=0.85
)
dedup = DedupEngine(config)

# Check exact duplicate
text_hash = dedup.hasher.compute_hash(text=text, url=url)
if dedup.hasher.is_duplicate(text_hash):
    print("Exact duplicate found!")

# Check near-duplicate
is_dup, similar_url, minhash_sig = dedup.process_document(text, url)
if is_dup:
    print(f"Near-duplicate of: {similar_url}")
```

#### 3. Structured Logging

JSON logs with automatic context injection:

```python
from somali_dialect_classifier.utils.logging_utils import (
    StructuredLogger, set_context, generate_run_id
)

logger = StructuredLogger("BBC-Somali", level="INFO", json_format=True)
run_id = generate_run_id("bbc")
set_context(run_id=run_id, source="BBC-Somali", phase="fetch")

logger.info("Article fetched", url="...", http_status=200)
# Output: {"timestamp": "...", "run_id": "...", "source": "BBC-Somali",
#          "phase": "fetch", "message": "Article fetched", "url": "...", ...}
```

#### 4. Metrics Collection

Automated metrics tracking with quality reports:

```python
from somali_dialect_classifier.utils.metrics import MetricsCollector, QualityReporter

metrics = MetricsCollector(run_id, "BBC-Somali")

# Track metrics
metrics.increment('urls_discovered')
metrics.record_fetch_duration(timer.get_elapsed_ms())
metrics.record_http_status(200)

# Export metrics
metrics.export_json("data/metrics/20250119_bbc_discovery.json")

# Generate quality report
QualityReporter(metrics).generate_markdown_report("data/reports/quality_report.md")
```

Quality reports include:
- ✅ **HEALTHY** - Success rate > 90%
- ⚠️ **WARNING** - Success rate 70-90%
- ❌ **CRITICAL** - Success rate < 70%

---

## Data Sources

### 1. Wikipedia Somali (~50,000 articles)

**Source**: Wikimedia dumps (sowiki)
**License**: CC-BY-SA-3.0
**Format**: XML (bz2 compressed)
**Domain**: Encyclopedia

```bash
# Run Wikipedia pipeline
wikisom-download

# Or with Python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor
processor = WikipediaSomaliProcessor(force=False)
processor.process()
```

**Features**:
- Memory-efficient XML streaming
- Namespace filtering (skips Talk:, User:, Template:, etc.)
- URL discovery and ledger tracking
- Exact and near-duplicate detection

### 2. BBC Somali News (Variable, news articles)

**Source**: BBC Somali website
**License**: BBC Terms of Use
**Format**: HTML scraping
**Domain**: News

```bash
# Run BBC pipeline
bbcsom-download --max-articles 500

# Or with Python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor
processor = BBCSomaliProcessor(max_articles=500, force=False)
processor.process()
```

**Features**:
- **RSS Feeds** - Primary source with frequency throttling (24-hour default)
- **Web Scraping** - Fallback if RSS yields < 50 articles
- **Adaptive Rate Limiting** - Exponential backoff with jitter
- **Conditional Requests** - If-None-Match/If-Modified-Since headers
- **Ethical Scraping** - Respects robots.txt, 3-6 second delays, max 60 req/hour

**RSS Configuration**:
```python
# In config.py or .env
SDC_SCRAPING__BBC__RSS_FEEDS='["https://www.bbc.com/somali/index.xml"]'
SDC_SCRAPING__BBC__CHECK_FREQUENCY_HOURS=24
SDC_SCRAPING__BBC__MAX_ITEMS_PER_FEED=100
```

### 3. HuggingFace Datasets (~100K-200K records)

**Source**: HuggingFace Hub (MC4 - Multilingual C4)
**License**: ODC-BY-1.0
**Format**: Streaming Parquet
**Domain**: Web

```bash
# Run HuggingFace pipeline
hfsom-download mc4 --max-records 10000

# Or with Python
from somali_dialect_classifier.preprocessing import create_mc4_processor
processor = create_mc4_processor(max_records=10000, force=False)
processor.process()
```

**Features**:
- **Streaming Mode** - No memory limits, processes records on-the-fly
- **JSONL Batching** - 5K records per batch for resume capability
- **Schema Mapping** - Handles MC4, OSCAR, CulturaX, and other formats
- **Revision Pinning** - Lock to specific dataset version for reproducibility
- **Manifest Versioning** - Tracks dataset name, config, revision, commit hash

**Revision Pinning**:
```python
# In config.py or .env
SDC_SCRAPING__HUGGINGFACE__REVISION="abc123def456"  # Git commit hash
```

### 4. Språkbanken Corpora (23 corpora)

**Source**: University of Gothenburg Språkbanken
**License**: CC BY 4.0
**Format**: XML (bz2 compressed)
**Domains**: News, Literature, Science, Health, Radio, Historical

```bash
# List available corpora
python -m somali_dialect_classifier.cli.download_sprakbankensom --list

# Download all 23 corpora
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all

# Or specific corpus
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus cilmi
```

**Available Corpora**:
- **News**: as-2001, as-2016, ah-2010-19, cb-*, ogaden (6 corpora)
- **Literature**: sheekooyin*, suugaan* (4 corpora)
- **Science**: cilmi, saynis-1980-89 (2 corpora)
- **Health**: caafimaad-1972-79 (1 corpus)
- **Radio**: radioden2014, radioswe2014 (2 corpora)
- **Historical**: 1971-79, 1993-94, 2001, mk-1972-79 (4 corpora)
- **Translation**: turjuman variants (2 corpora)
- **QA**: kqa (1 corpus)

**Features**:
- Rich metadata (dates, authors, publishers, genres, regions)
- Domain-specific content with automatic classification
- Sentence-level tokenization

---

## Unified Silver Dataset

All sources write to a consistent Parquet schema:

```python
{
    "id": "uuid-v4",
    "text": "cleaned text content",
    "title": "article/document title",
    "source": "Wikipedia-Somali | BBC-Somali | HuggingFace-Somali_* | Sprakbanken-Somali-*",
    "source_type": "wiki | news | web | corpus",
    "language": "so",
    "license": "CC-BY-SA-3.0 | BBC Terms of Use | ODC-BY-1.0 | CC BY 4.0",
    "tokens": 1234,
    "url": "source URL",
    "date_accessed": "2025-01-19",
    "date_published": "optional publication date",
    "domain": "encyclopedia | news | web | science | literature | ...",
    "source_metadata": {
        "detected_lang": "so",
        "lang_confidence": 0.85,
        "dialect_markers": {"sports": 2},
        # Source-specific fields
    }
}
```

**Storage Structure**:
```
data/processed/silver/
├── source=Wikipedia-Somali/date_accessed=2025-01-19/
│   └── part-0000.parquet
├── source=BBC-Somali/date_accessed=2025-01-19/
│   └── part-0000.parquet
├── source=HuggingFace-Somali_c4/date_accessed=2025-01-19/
│   └── part-0000.parquet
└── source=Sprakbanken-Somali-All/date_accessed=2025-01-19/
    └── part-0000.parquet
```

---

## Quality Filters

All pipelines use pluggable filters for data quality:

### Built-in Filters

1. **min_length_filter** - Removes short texts
2. **langid_filter** - Detects and filters non-Somali content
3. **dialect_heuristic_filter** - Enriches with topic/dialect markers
4. **namespace_filter** - Wikipedia-specific page filtering

### Usage Example

```python
from somali_dialect_classifier.preprocessing.base_pipeline import BasePipeline

class MyProcessor(BasePipeline):
    def _register_filters(self):
        from .filters import min_length_filter, langid_filter

        # Minimum length (50 characters)
        self.record_filters.append((min_length_filter, {"threshold": 50}))

        # Language detection (Somali only, 0.3 confidence)
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": 0.3
        }))
```

### Custom Filters

```python
def custom_news_filter(text: str, keywords: List[str]) -> Tuple[bool, Dict]:
    """Filter for news articles containing specific keywords."""
    has_keyword = any(word in text.lower() for word in keywords)
    return has_keyword, {"matched_keywords": has_keyword}

# Register custom filter
self.record_filters.append((custom_news_filter, {
    "keywords": ["wararka", "xog", "sheegay"]
}))
```

---

## Workflow Orchestration

### Running Individual Pipelines

```bash
# Wikipedia
wikisom-download

# BBC (limit to 500 articles)
bbcsom-download --max-articles 500

# HuggingFace MC4 (limit to 10K records)
hfsom-download mc4 --max-records 10000

# Språkbanken (all corpora)
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all
```

### Orchestrated Execution (All Pipelines)

```bash
# Run all pipelines in parallel
somali-orchestrate --pipeline all

# Run specific pipeline
somali-orchestrate --pipeline wikipedia --force

# Run all with limits
somali-orchestrate --pipeline all --max-bbc-articles 500 --max-hf-records 10000
```

### Prefect Workflows

```python
from somali_dialect_classifier.orchestration import run_all_pipelines

# Run all pipelines concurrently
result = run_all_pipelines(
    force=False,
    max_bbc_articles=500,
    max_hf_records=10000,
    run_wikipedia=True,
    run_bbc=True,
    run_huggingface=True,
    run_sprakbanken=True,
)

print(f"Successful: {len(result['successful'])}")
print(f"Failed: {len(result['failed'])}")
```

---

## Configuration

### Environment Variables

```bash
# Data paths
export SDC_DATA__RAW_DIR=/custom/path/raw
export SDC_DATA__SILVER_DIR=/custom/path/silver

# BBC scraping
export SDC_SCRAPING__BBC__MAX_ARTICLES=1000
export SDC_SCRAPING__BBC__MAX_REQUESTS_PER_HOUR=60
export SDC_SCRAPING__BBC__CHECK_FREQUENCY_HOURS=24

# HuggingFace
export SDC_SCRAPING__HUGGINGFACE__MAX_RECORDS=50000
export SDC_SCRAPING__HUGGINGFACE__REVISION=abc123def456

# Logging
export SDC_LOGGING__LEVEL=DEBUG
```

### Configuration File (.env)

```bash
# Create .env in project root
cat > .env << EOF
SDC_DATA__RAW_DIR=/data/somali/raw
SDC_SCRAPING__BBC__MAX_ARTICLES=500
SDC_SCRAPING__BBC__DELAY_RANGE=[3,6]
SDC_LOGGING__LEVEL=INFO
EOF
```

### Programmatic Configuration

```python
from somali_dialect_classifier.config import get_config

config = get_config()
print(config.data.raw_dir)
print(config.scraping.bbc.max_articles)
```

---

## Monitoring and Quality

### Metrics Files

After each run, metrics are exported to `data/metrics/`:

```json
{
  "run_id": "20250119_103045_bbc_a1b2c3d4",
  "source": "BBC-Somali",
  "phase": "fetch",
  "urls_discovered": 1234,
  "urls_fetched": 1000,
  "urls_failed": 34,
  "urls_deduplicated": 50,
  "near_duplicates": 15,
  "avg_fetch_duration_ms": 345.6
}
```

### Quality Reports

Generated in `data/reports/` with health indicators:

```markdown
# Quality Report: BBC-Somali

**Run ID**: 20250119_103045_bbc_a1b2c3d4
**Status**: ✅ HEALTHY
**Success Rate**: 96.6% (1000/1034)

## Metrics Summary

- URLs Discovered: 1,234
- URLs Fetched: 1,000
- URLs Failed: 34
- Duplicates Detected: 50
- Near-Duplicates: 15

## Health Indicators

✅ Success Rate: 96.6% (Target: >90%)
✅ Avg Fetch Duration: 345ms (Target: <1000ms)
⚠️ Duplicate Rate: 5.0% (Target: <10%)
```

### Ledger Statistics

```bash
# Check ledger statistics
python -c "
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger
ledger = get_ledger()
stats = ledger.get_statistics('bbc')
print(stats)
"
```

---

## Troubleshooting

### Common Issues

**1. Empty Text Extraction (BBC)**

BBC HTML structure may have changed. Check scraper selectors in `bbc_somali_processor.py`.

```python
# Update semantic selectors if needed
main_content = soup.find('main') or soup.find(role='main')
```

**2. High Duplicate Rate**

Expected for incremental runs. The ledger tracks already-processed URLs.

```bash
# Force reprocessing to skip ledger
bbcsom-download --force
```

**3. Rate Limiting Errors (HTTP 429)**

Adaptive rate limiter will automatically back off. Adjust configuration:

```bash
export SDC_SCRAPING__BBC__MAX_REQUESTS_PER_HOUR=30
export SDC_SCRAPING__BBC__MAX_BACKOFF=600
```

**4. Memory Errors (HuggingFace)**

Reduce batch size:

```bash
export SDC_SCRAPING__HUGGINGFACE__STREAMING_BATCH_SIZE=2000
```

**5. Ledger Database Locked**

Close other processes accessing the ledger:

```bash
# Check for lock
fuser data/ledger/crawl_ledger.db

# Force unlock (last resort)
rm data/ledger/crawl_ledger.db-wal
```

### Debug Logging

```bash
# Enable debug logs
export SDC_LOGGING__LEVEL=DEBUG

# Run pipeline
bbcsom-download --max-articles 10

# Check logs
tail -f logs/download_bbcsom.log
```

### Testing Individual Components

```python
# Test deduplication
from somali_dialect_classifier.preprocessing.dedup import DedupEngine, DedupConfig

config = DedupConfig(enable_minhash=True)
dedup = DedupEngine(config)

text_hash = dedup.hasher.compute_hash("test text", "http://example.com")
is_dup = dedup.hasher.is_duplicate(text_hash)
print(f"Duplicate: {is_dup}")

# Test filters
from somali_dialect_classifier.preprocessing.filters import min_length_filter, langid_filter

passes, metadata = min_length_filter("short", threshold=50)
print(f"Passes min length: {passes}")

passes, metadata = langid_filter("Waa maxay barnaamijkan?", allowed_langs={"so"})
print(f"Passes language filter: {passes}, confidence: {metadata}")
```

---

## Performance Optimization

### Parallel Execution

Use orchestrator for concurrent pipeline execution:

```bash
# All pipelines run in parallel
somali-orchestrate --pipeline all
```

### Incremental Processing

Pipelines automatically skip already-processed URLs via ledger:

```bash
# First run - processes all URLs
bbcsom-download

# Second run - skips processed URLs
bbcsom-download  # Only fetches new articles
```

### Resource Management

**CPU**: Streaming processing keeps memory usage low
**Network**: Adaptive rate limiting prevents overload
**Storage**: Parquet compression reduces disk usage by ~70%

---

## Next Steps

After data collection:

1. **Explore Silver Dataset**
   ```python
   import pyarrow.parquet as pq

   table = pq.read_table("data/processed/silver/")
   df = table.to_pandas()
   print(df.describe())
   ```

2. **Data Analysis**
   - Analyze text lengths
   - Check language distribution
   - Identify dialect markers

3. **Model Training**
   - Convert Parquet to HuggingFace datasets
   - Fine-tune transformer models
   - Evaluate dialect classification

---

## References

- [Architecture Overview](../overview/architecture.md)
- [API Reference](../reference/api.md)
- [Integration Guides](../howto/processing-pipelines.md)
- [Deployment Guide](../operations/deployment.md)

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
