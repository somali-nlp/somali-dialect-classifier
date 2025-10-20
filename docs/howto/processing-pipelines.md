# Processing Pipelines Guide

**Last Updated**: 2025-10-19

This guide provides step-by-step walkthroughs for processing data from each supported source.

## Overview

The Somali Dialect Classifier supports **four primary data sources**, all integrated with production MLOps infrastructure:

1. **Wikipedia-Somali** - Encyclopedia articles (formal, educational content)
2. **BBC-Somali** - News articles (journalistic, current events)
3. **HuggingFace Datasets** - Large-scale web corpora (MC4 only)
4. **Språkbanken Corpora** - Academic corpora (23 diverse corpora from University of Gothenburg)

All processors follow the same three-phase pipeline with integrated observability:

1. **Download** - Fetch raw data (with metrics tracking)
2. **Extract** - Parse and stage data (with ledger state updates)
3. **Process** - Clean, filter, and write to silver dataset (with quality reports)

**MLOps Infrastructure:** All processors include structured logging, metrics collection, crawl ledger state tracking, deduplication, and automated quality reporting.

**Note**: Each source has a dedicated integration guide with comprehensive documentation. This guide provides quick-start examples and comparisons. For detailed documentation, see the integration guides linked below.

## Wikipedia-Somali Pipeline

### Quick Start

```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

processor = WikipediaSomaliProcessor(force=False)
processor.run()  # download() -> extract() -> process()
```

### Step-by-Step

```python
# Initialize processor
processor = WikipediaSomaliProcessor(force=False)

# Phase 1: Download Wikipedia dump
dump_path = processor.download()
# Creates: data/raw/source=Wikipedia-Somali/date_accessed=2025-10-16/sowiki-latest-pages-articles.xml.bz2

# Phase 2: Extract articles from dump
staging_path = processor.extract()
# Creates: data/staging/source=Wikipedia-Somali/date_accessed=2025-10-16/wikipedia-somali_20251016_143045_staging_extracted.txt

# Phase 3: Process and filter
processed_path = processor.process()
# Creates:
#   - data/processed/source=Wikipedia-Somali/date_accessed=2025-10-16/wikipedia-somali_20251016_143045_processed_cleaned.txt
#   - data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-10-16/wikipedia-somali_20251016_143045_silver_part-0000.parquet
#   - data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-10-16/wikipedia-somali_20251016_143045_silver_metadata.json
```

### Output Structure

```
data/
├── raw/
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-10-16/
│           └── sowiki-latest-pages-articles.xml.bz2
├── staging/
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-10-16/
│           └── wikipedia-somali_20251016_143045_staging_extracted.txt
├── processed/
│   └── source=Wikipedia-Somali/
│       └── date_accessed=2025-10-16/
│           └── wikipedia-somali_20251016_143045_processed_cleaned.txt
└── processed/silver/
    └── source=Wikipedia-Somali/
        └── date_accessed=2025-10-16/
            ├── wikipedia-somali_20251016_143045_silver_part-0000.parquet
            └── wikipedia-somali_20251016_143045_silver_metadata.json
```

**File Naming**: All files include run_id (`20251016_143045`) for traceability
**Partition Consistency**: All layers now use `date_accessed` (no more `date_processed`)

### Filters Applied

1. **min_length_filter** (threshold=50) - Removes stub articles
2. **langid_filter** (confidence=0.3) - Filters non-Somali content
3. **namespace_filter** - Skips Talk:, User:, Template: pages

### MLOps Outputs

Each run produces:
- **Metrics:** `data/metrics/{run_id}_discovery.json`, `{run_id}_extraction.json`
- **Quality Report:** `data/reports/{run_id}_quality_report.md`
- **Logs:** `logs/wikipedia_somali.log` (JSON format with run_id)

Quality report includes:
- ✅ Health status (Healthy/Warning/Critical)
- Processing success/failure rates
- Performance metrics (fetch duration p50/p95/p99)
- HTTP status distribution
- Automated recommendations

### Common Issues

**Issue**: Download hangs or times out
```python
# Solution: Set timeout explicitly
processor = WikipediaSomaliProcessor()
processor.timeout = 600  # 10 minutes
```

**Issue**: Out of memory during processing
```python
# Solution: Already fixed with default batch_size=5000
# Large dumps now write in batches automatically
```

---

## BBC-Somali Pipeline

### Quick Start

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

processor = BBCSomaliProcessor(max_articles=100, force=False)
processor.run()
```

### Step-by-Step

```python
# Initialize with article limit
processor = BBCSomaliProcessor(
    max_articles=100,  # Scrape up to 100 articles
    force=False
)

# Phase 1: Discover article URLs
raw_path = processor.download()
# Creates: data/raw/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_raw_article-links.json

# Phase 2: Scrape articles
staging_path = processor.extract()
# Creates: data/staging/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_staging_articles.jsonl

# Phase 3: Process and enrich
processed_path = processor.process()
# Creates:
#   - data/processed/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_processed_cleaned.txt
#   - data/processed/silver/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_silver_part-0000.parquet
#   - data/processed/silver/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_silver_metadata.json
```

### Filters Applied

1. **min_length_filter** (threshold=50)
2. **langid_filter** (confidence=0.5)
3. **dialect_heuristic_filter** (enrich_only=True) - Adds topic metadata:
   - Sports articles: `{"primary_dialect": "sports", "dialect_markers": {"sports": 3}}`
   - Politics articles: `{"primary_dialect": "politics", ...}`

### Topic Lexicons

The BBC processor enriches articles with topic markers:

```python
{
    "sports": ["kubadda", "ciyaaryahan", "kooxda", "tartanka"],
    "politics": ["xukuumad", "madaxweyne", "baarlamaan", "doorasho"],
    "economy": ["dhaqaale", "ganacsiga", "suuq", "lacagta"]
}
```

### Scraping Best Practices

```python
# Respect rate limits
import time
processor = BBCSomaliProcessor(max_articles=1000)
# Processor includes automatic 1-second delays between requests

# Resume interrupted scraping
# If scraping stops, rerun with force=False to skip cached articles
processor.run()  # Resumes from last scraped article
```

### MLOps Outputs

Each run produces:
- **Metrics:** `data/metrics/{run_id}_discovery.json`, `{run_id}_extraction.json`
- **Quality Report:** `data/reports/{run_id}_quality_report.md`
- **Logs:** `logs/bbc_somali.log` (JSON format with run_id)

Quality report includes:
- ✅ Health status (Healthy/Warning/Critical)
- Processing success/failure rates
- Performance metrics (fetch duration p50/p95/p99)
- HTTP status distribution
- Automated recommendations

### Common Issues

**Issue**: Empty article bodies
```bash
# Check logs for warnings:
# "Empty text extracted from {url} - BBC may have changed their HTML structure"
# This indicates BBC updated their site structure
```

**Issue**: Rate limiting (HTTP 429)
```python
# Solution: Reduce max_articles and run multiple batches
processor = BBCSomaliProcessor(max_articles=50)
```

---

## HuggingFace Datasets Pipeline

### Quick Start

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor

processor = create_mc4_processor(max_records=10000, force=False)
processor.run()
```

### Available Datasets

#### MC4 (Multilingual C4)

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor

processor = create_mc4_processor(max_records=10000)
processor.run()

# Dataset: allenai/c4
# Config: so (Somali)
# Records: ~2.5M
# License: ODC-BY-1.0
```

#### OSCAR-2301

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_oscar_processor

processor = create_oscar_processor(max_records=10000)
processor.run()

# Dataset: oscar-corpus/OSCAR-2301
# Config: so
# Records: ~1.2M
# License: CC0-1.0
# Note: Gated dataset - requires HF authentication
```

#### MADLAD-400

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_madlad400_processor

processor = create_madlad400_processor(max_records=10000)
processor.run()

# Dataset: allenai/madlad-400
# Split: clean
# Records: ~293K (clean) / 729K (noisy)
# License: ODC-BY-1.0
```

### Step-by-Step (MC4 Example)

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import HuggingFaceSomaliProcessor

# Initialize with streaming config
processor = HuggingFaceSomaliProcessor(
    dataset_name="allenai/c4",
    dataset_config="so",
    split="train",
    text_field="text",
    url_field="url",
    metadata_fields=["timestamp"],
    streaming_batch_size=5000,
    max_records=10000,  # Limit for testing
    force=False
)

# Phase 1: Create manifest
manifest_path = processor.download()
# Creates: data/raw/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/mc4_20251016_153000_raw_manifest.json

# Phase 2: Stream and batch to JSONL
staging_dir = processor.extract()
# Creates:
#   - data/staging/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/mc4_20251016_153000_staging_batch-000000.jsonl
#   - data/staging/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/mc4_20251016_153000_staging_batch-000001.jsonl
#   - ...
#   - data/staging/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/.extraction_complete

# Phase 3: Replay batches and filter
silver_path = processor.process()
# Creates:
#   - data/processed/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/mc4_20251016_153000_processed_cleaned.txt
#   - data/processed/silver/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/hf-mc4-so_20251016_153000_silver_part-0000.parquet
#   - data/processed/silver/source=HuggingFace-Somali_c4-so/date_accessed=2025-10-16/hf-mc4-so_20251016_153000_silver_metadata.json
```

### Manifest Format

```json
{
  "dataset_name": "allenai/c4",
  "dataset_config": "so",
  "split": "train",
  "revision": "main",
  "text_field": "text",
  "url_field": "url",
  "metadata_fields": ["timestamp"],
  "streaming_batch_size": 5000,
  "max_records": 10000,
  "created_at": "2025-10-16T10:30:00Z",
  "last_offset": 10000,
  "batches_completed": ["batch_000000.jsonl", "batch_000001.jsonl"],
  "total_records_extracted": 10000,
  "total_batches": 2,
  "manifest_version": "1.0"
}
```

### Resume Capability

If extraction is interrupted:

```python
# Rerun with force=False to resume from last_offset
processor = create_mc4_processor(max_records=100000, force=False)
processor.extract()  # Continues from where it stopped
```

### Filters Applied

1. **min_length_filter** (threshold=50)
2. **langid_filter** (confidence=0.5)

### Authentication (OSCAR)

OSCAR datasets are gated and require HuggingFace authentication:

```bash
# Install HF CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Accept terms at: https://huggingface.co/datasets/oscar-corpus/OSCAR-2301

# Then run processor
python -c "from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_oscar_processor; create_oscar_processor(max_records=1000).run()"
```

### Performance Tuning

```python
# Large batch size for fast sources
processor = HuggingFaceSomaliProcessor(
    dataset_name="allenai/c4",
    dataset_config="so",
    streaming_batch_size=10000,  # Default: 5000
    max_records=None  # Unlimited
)

# Small batch size for slow sources or limited disk
processor = HuggingFaceSomaliProcessor(
    dataset_name="oscar-corpus/OSCAR-2301",
    dataset_config="so",
    streaming_batch_size=1000,
    max_records=50000
)
```

### MLOps Outputs

Each run produces:
- **Metrics:** `data/metrics/{run_id}_discovery.json`, `{run_id}_extraction.json`
- **Quality Report:** `data/reports/{run_id}_quality_report.md`
- **Logs:** `logs/huggingface_somali.log` (JSON format with run_id)

Quality report includes:
- ✅ Health status (Healthy/Warning/Critical)
- Processing success/failure rates
- Performance metrics (fetch duration p50/p95/p99)
- HTTP status distribution
- Automated recommendations

---

## Språkbanken-Somali Pipeline

### Quick Start

```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import SprakbankenSomaliProcessor

# Process single corpus
processor = SprakbankenSomaliProcessor(corpus_id="cilmi")
processor.run()

# Process all 23 corpora
processor = SprakbankenSomaliProcessor(corpus_id="all")
processor.run()
```

### Available Corpora (23 total)

**News** (7 corpora): as-2001, as-2016, ah-2010-19, cb, cb-2001-03, cb-2016, ogaden
**Literature** (4 corpora): sheekooyin, sheekooying, suugaan, suugaan-turjuman
**Science** (2 corpora): cilmi, saynis-1980-89
**Health** (1 corpus): caafimaad-1972-79
**Children** (1 corpus): sheekooyin-carruureed
**Radio** (2 corpora): radioden2014, radioswe2014
**Translation** (1 corpus): tid-turjuman
**QA** (1 corpus): kqa
**Historical** (4 corpora): 1971-79, 1993-94, 2001, mk-1972-79

### Step-by-Step

```python
# Initialize processor
processor = SprakbankenSomaliProcessor(corpus_id="ogaden")

# Phase 1: Download corpus
raw_path = processor.download()
# Creates: data/raw/source=Sprakbanken-Somali-ogaden/date_accessed=2025-10-19/sprakbanken-ogaden_20251019_160000_raw_manifest.json

# Phase 2: Extract texts from XML
staging_path = processor.extract()
# Creates: data/staging/source=Sprakbanken-Somali-ogaden/date_accessed=2025-10-19/sprakbanken-ogaden_20251019_160000_staging_extracted.jsonl

# Phase 3: Process and enrich
processed_path = processor.process()
# Creates:
#   - data/processed/source=Sprakbanken-Somali-ogaden/date_accessed=2025-10-19/sprakbanken-ogaden_20251019_160000_processed_cleaned.txt
#   - data/processed/silver/source=Sprakbanken-Somali-ogaden/date_accessed=2025-10-19/sprakbanken-ogaden_20251019_160000_silver_part-0000.parquet
#   - data/processed/silver/source=Sprakbanken-Somali-ogaden/date_accessed=2025-10-19/sprakbanken-ogaden_20251019_160000_silver_metadata.json
```

### Filters Applied

1. **min_length_filter** (threshold=20 tokens) - Lower threshold for diverse content
2. **langid_filter** (confidence=0.3) - Relaxed for academic text

### Domain Enrichment

Each corpus is automatically tagged with its domain:

```python
{
    "domain": "news_regional",  # For ogaden corpus
    "source_metadata": {
        "repository": "Språkbanken",
        "institution": "University of Gothenburg",
        "corpus_id": "ogaden",
        "domain": "news_regional",
        "license": "CC BY 4.0"
    }
}
```

### MLOps Outputs

Each run produces:
- **Metrics:** `data/metrics/{run_id}_discovery.json`, `{run_id}_extraction.json`
- **Quality Report:** `data/reports/{run_id}_quality_report.md`
- **Logs:** `logs/sprakbanken_somali.log` (JSON format with run_id)

Quality report includes:
- ✅ Health status (Healthy/Warning/Critical)
- Processing success/failure rates
- Performance metrics (fetch duration p50/p95/p99)
- HTTP status distribution
- Automated recommendations

### Common Issues

**Issue**: XML parsing errors

```bash
# Solution: Re-download with force flag
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus ogaden --force
```

**Issue**: Empty output for specific corpus

```bash
# Solution: Check if corpus exists
python -m somali_dialect_classifier.cli.download_sprakbankensom --list

# Verify corpus info
python -m somali_dialect_classifier.cli.download_sprakbankensom --info ogaden
```

---

## CLI Usage

All processors have CLI wrappers:

### Wikipedia

```bash
# Download and process Wikipedia
wikisom-download

# Force reprocessing
wikisom-download --force
```

### BBC

```bash
# Download 100 articles
bbcsom-download --max-articles 100

# Download with force
bbcsom-download --max-articles 200 --force
```

### HuggingFace

```bash
# Download MC4 (10k records)
hfsom-download mc4 --max-records 10000

# Force reprocessing
hfsom-download mc4 --force
```

### Språkbanken

```bash
# List all available corpora
python -m somali_dialect_classifier.cli.download_sprakbankensom --list

# Get info about specific corpus
python -m somali_dialect_classifier.cli.download_sprakbankensom --info cilmi

# Download single corpus
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus ogaden

# Download all 23 corpora
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all

# Force reprocessing
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all --force
```

---

## Silver Dataset Schema

All processors write to a unified silver schema (v2.1):

```python
{
    "id": "uuid-v4",
    "text": "cleaned text content",
    "title": "article title",
    "source": "Wikipedia-Somali | BBC-Somali | HuggingFace-Somali_* | Sprakbanken-Somali-*",
    "source_type": "wiki | news | web | corpus",
    "url": "source URL",
    "source_id": "url-based hash",
    "date_published": "2025-10-16" (nullable),
    "date_accessed": "2025-10-16",
    "language": "so",
    "license": "CC-BY-SA-3.0 | BBC Terms of Use | ODC-BY-1.0 | CC BY 4.0",
    "topic": "category" (nullable),
    "tokens": 1234,
    "text_hash": "sha256 hash",
    "pipeline_version": "2.1.0",
    "domain": "news | encyclopedia | web | science | etc.",  # v2.0
    "embedding": null,  # v2.0 (placeholder for future use)
    "register": "formal | informal | colloquial",  # v2.1 (NEW)
    "source_metadata": {
        "detected_lang": "so",
        "lang_confidence": 0.85,
        "dialect_markers": {"sports": 2},
        "primary_dialect": "sports",
        "domain": "news_regional"  # Språkbanken-specific
    }
}
```

**Register field (NEW in v2.1)**:
- `"formal"` - All 4 current sources (Wikipedia, BBC, HuggingFace MC4, Språkbanken)
- `"informal"` - Future social media sources (TikTok, etc.)
- `"colloquial"` - Future conversational/speech sources

See [Silver Schema Reference](../reference/silver-schema.md) for complete field documentation.

---

## Comparison by Source

| Aspect | Wikipedia | BBC | HuggingFace | Språkbanken |
|--------|-----------|-----|-------------|-------------|
| **Content Type** | Encyclopedia | News | Web scrapes | Academic corpora |
| **Language Style** | Formal, educational | Journalistic | Informal, varied | Domain-specific |
| **Size** | ~50k articles | ~500+ articles | ~100k-200k records | 23 corpora (varied sizes) |
| **License** | CC-BY-SA-3.0 | BBC Terms of Use | ODC-BY-1.0 | CC BY 4.0 |
| **Update Frequency** | Weekly dumps | Daily (scraping) | Static snapshot | Static corpora |
| **Metadata Richness** | Medium | High (topics) | Low | Very High (domains, authors, dates) |
| **Processing Time** | ~5 minutes | ~1 hour (500 articles) | ~1.5 hours (100k) | ~30-60 minutes (all 23) |
| **Best For** | Formal baseline | Current events, topics | Large-scale training | Domain diversity |

---

## See Also

### Integration Guides (Comprehensive Documentation)

- **[Wikipedia Integration Guide](wikipedia-integration.md)** - Complete guide to Wikipedia dumps, XML parsing, and namespace filtering
- **[BBC Integration Guide](bbc-integration.md)** - Ethical web scraping, topic enrichment, and rate limiting
- **[HuggingFace Integration Guide](huggingface-integration.md)** - Streaming datasets, manifests, and JSONL batching
- **[Språkbanken Integration Guide](sprakbanken-integration.md)** - All 23 corpora, domain mapping, and metadata extraction

### Other Documentation

- [Configuration Guide](configuration.md) - Environment variables and config management
- [Custom Filters Guide](custom-filters.md) - Writing custom quality filters
- [API Reference](../reference/api.md) - Complete API documentation for all processors
- [Architecture Overview](../overview/architecture.md) - System design and patterns
- [Data Pipeline Overview](../overview/data-pipeline-architecture.md) - ETL architecture and medallion layers

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
