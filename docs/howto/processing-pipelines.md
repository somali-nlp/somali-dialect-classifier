# Processing Pipelines Guide

**Last Updated**: 2025-11-01

This guide provides step-by-step walkthroughs for processing data from each supported source.

## Overview

The Somali Dialect Classifier supports **five primary data sources**, all integrated with production MLOps infrastructure:

1. **Wikipedia-Somali** - Encyclopedia articles (formal, educational content)
2. **BBC-Somali** - News articles (journalistic, current events)
3. **HuggingFace Datasets** - Large-scale web corpora (MC4 only)
4. **Språkbanken Corpora** - Academic corpora (23 diverse corpora from University of Gothenburg)
5. **TikTok Comments** - Social media comments (colloquial, conversational Somali)

All processors follow the same three-phase pipeline with integrated observability:

1. **Download** - Fetch raw data (with metrics tracking)
2. **Extract** - Parse and stage data (with ledger state updates)
3. **Process** - Clean, filter, and write to silver dataset (with quality reports)

**MLOps Infrastructure:** All processors include structured logging, metrics collection, crawl ledger state tracking, deduplication, and automated quality reporting.

**Note**: Each source has a dedicated integration guide with comprehensive documentation. This guide provides quick-start examples and comparisons. For detailed documentation, see the integration guides linked below.

## Quick Start

### Run Individual Pipelines

```bash
# Wikipedia (formal encyclopedia content)
wikisom-download

# BBC Somali (news articles)
bbcsom-download --max-articles 100

# HuggingFace MC4 (web corpus)
hfsom-download mc4 --max-records 10000

# Språkbanken (academic corpora)
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all

# TikTok (social media comments)
tiktoksom-download --video-urls data/tiktok_urls.txt
```

### Orchestrate Multiple Pipelines

```bash
# Run ALL five sources (Wikipedia, BBC, HuggingFace, Språkbanken, TikTok)
somali-orchestrate --pipeline all \
  --max-bbc-articles 100 \
  --max-hf-records 10000 \
  --tiktok-video-urls data/tiktok_urls.txt

# Run specific sources only
somali-orchestrate --pipeline all \
  --skip-sources huggingface,sprakbanken

# Run TikTok only
somali-orchestrate --pipeline tiktok \
  --tiktok-video-urls data/tiktok_urls.txt

# Combine formal and colloquial sources
somali-orchestrate --pipeline all \
  --skip-sources huggingface \
  --max-bbc-articles 50
```

**Note:** TikTok pipeline requires:
- Apify API token (set via `SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN` env var)
- Video URLs file (default: `data/tiktok_urls.txt`)

---

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
# Expected duration: ~85-100 minutes for 100 articles
```

### Step-by-Step

```python
# Initialize with article limit
processor = BBCSomaliProcessor(
    max_articles=100,  # Scrape up to 100 articles
    force=False
)

# Phase 1: Discover article URLs (fast - ~1-2 minutes)
raw_path = processor.download()
# Creates: data/raw/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_raw_article-links.json

# Phase 2: Scrape articles (longest phase - ~50-60 seconds per article)
staging_path = processor.extract()
# Creates: data/staging/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_staging_articles.jsonl
# Expected duration for 100 articles: ~85-100 minutes

# Phase 3: Process and enrich (fast - ~2-5 minutes for 100 articles)
processed_path = processor.process()
# Creates:
#   - data/processed/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_processed_cleaned.txt
#   - data/processed/silver/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_silver_part-0000.parquet
#   - data/processed/silver/source=BBC-Somali/date_accessed=2025-10-16/bbc-somali_20251016_150230_silver_metadata.json
```

### Performance Expectations

**Scraping is intentionally slow due to external factors:**
- **Per article**: 50-60 seconds average (BBC server response time + network latency)
- **10 articles**: ~10 minutes (testing/development)
- **50 articles**: ~45-50 minutes (small datasets)
- **100 articles**: ~85-100 minutes (production datasets)

The primary bottleneck is BBC's server processing time (~45-55s per article), not code efficiency. This is expected and normal for ethical web scraping. See the [BBC Integration Guide](bbc-integration.md#performance-characteristics) for detailed performance analysis.

### Filters Applied

1. **min_length_filter** (threshold=50)
2. **langid_filter** (confidence=0.5)
3. **topic_lexicon_enrichment_filter** (enrich_only=True) - Adds topic metadata:
   - Sports articles: `{"primary_dialect": "sports", "dialect_markers": {"sports": 3}}`
   - Politics articles: `{"primary_dialect": "politics", ...}`
   - Note: Field names use "dialect" for backward compatibility, but actually represent topics

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

## TikTok Comments Pipeline

### Quick Start

```bash
# Download comments from video URLs
tiktoksom-download --video-urls data/tiktok_urls.txt

# Or use orchestration
somali-orchestrate --pipeline tiktok \
  --tiktok-video-urls data/tiktok_urls.txt
```

### Prerequisites

1. **Apify API Token**:
   ```bash
   # Get token from https://console.apify.com/account/integrations
   export SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=apify_api_YOUR_TOKEN

   # Or add to .env file
   echo 'SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=apify_api_YOUR_TOKEN' >> .env
   ```

2. **Video URLs File**:
   Create `data/tiktok_urls.txt` with one URL per line:
   ```
   https://www.tiktok.com/@somaliuser1/video/7123456789012345678
   https://www.tiktok.com/@somaliuser2/video/7234567890123456789
   https://www.tiktok.com/@somaliuser3/video/7345678901234567890
   ```

### Step-by-Step

```python
from somali_dialect_classifier.preprocessing import TikTokSomaliProcessor

# Initialize processor
processor = TikTokSomaliProcessor(
    video_urls_file="data/tiktok_urls.txt",
    max_total_comments=30000,  # Total budget across all videos
    max_comments_per_video=500,  # Per-video limit
    apify_api_token="apify_api_YOUR_TOKEN",  # Or set via env var
    force=False
)

# Phase 1: Prepare video URLs manifest
manifest_path = processor.download()
# Creates: data/raw/source=TikTok-Somali/date_accessed=2025-10-31/tiktok-somali_20251031_064341_raw_manifest.json

# Phase 2: Scrape comments via Apify
staging_path = processor.extract()
# Creates:
#   - data/raw/source=TikTok-Somali/date_accessed=2025-10-31/tiktok-somali_20251031_064341_raw_apify-dataset.json
#   - data/staging/source=TikTok-Somali/date_accessed=2025-10-31/tiktok-somali_20251031_064341_staging_comments.jsonl
# Expected duration: ~2 minutes for 5 videos (~1,200 comments)

# Phase 3: Process and clean
processed_path = processor.process()
# Creates:
#   - data/processed/source=TikTok-Somali/date_accessed=2025-10-31/tiktok-somali_20251031_064341_processed_cleaned.txt
#   - data/processed/silver/source=TikTok-Somali/date_accessed=2025-10-31/tiktok-somali_20251031_064341_silver_part-0000.parquet
#   - data/processed/silver/source=TikTok-Somali/date_accessed=2025-10-31/tiktok-somali_20251031_064341_silver_metadata.json
```

### Performance Expectations

**Fast scraping via Apify API:**
- **5 videos**: ~2 minutes (~1,200 comments)
- **10 videos**: ~3-4 minutes (~2,400 comments)
- **50 videos**: ~10-15 minutes (~12,000 comments)

**Actual production run (2025-10-31):**
- 5 videos → 1,176 raw comments → 321 linguistic comments (27% emoji-only filtered)
- Total time: ~2 minutes
- Cost: ~$0.01-0.05

The primary speed factor is Apify's actor execution time. The scraper is significantly faster than BBC scraping because it uses an API actor rather than direct web scraping.

### Filters Applied

1. **emoji_only_filter** - Removes comments with only emojis (e.g., "😂😂😂")
2. **min_length_filter** (threshold=3 characters) - Very permissive for social media
3. **langid_filter** (disabled by default) - Optional language detection
4. **exact_duplicate_removal** - Fuzzy deduplication disabled to preserve paid data

**Note:** TikTok pipeline uses minimal filtering because you pay for every comment scraped. The goal is to preserve as much linguistic data as possible.

### Data Preservation Strategy

**Key principle:** You pay for every comment, so we keep them ALL!

- **No fuzzy deduplication:** MinHash disabled (only exact duplicates removed)
- **Minimal filtering:** Only emoji-only comments removed
- **All metadata preserved:** Author, timestamps, likes, replies
- **Expected yield:** ~73% linguistic comments (27% emoji-only)

### Cost Management

```bash
# Small test run (100 comments, ~$0.10)
tiktoksom-download --video-urls data/test_urls.txt --max-comments 100

# Budget-conscious collection (5k comments, ~$5)
tiktoksom-download --video-urls data/tiktok_urls.txt --max-comments 5000

# Production collection (30k comments, ~$30-40)
tiktoksom-download --video-urls data/tiktok_urls.txt --max-comments 30000

# Limit per-video to avoid over-collecting from viral videos
tiktoksom-download --video-urls data/tiktok_urls.txt \
  --max-comments 30000 \
  --max-per-video 500
```

**Pricing:**
- **Raw cost:** $1 per 1,000 Apify results
- **Effective cost:** ~$3.67 per 1,000 linguistic comments (after emoji filtering)
- **Target budget:** 30,000 comments = ~$39 (within Apify Starter plan)

See [TikTok Cost Analysis](../cost-analysis/tiktok-apify-costs.md) for detailed breakdown.

### Orchestration Integration

TikTok integrates seamlessly with other pipelines via the orchestration CLI:

```bash
# Run TikTok with Wikipedia and BBC (mix formal + colloquial)
somali-orchestrate --pipeline all \
  --skip-sources huggingface,sprakbanken \
  --max-bbc-articles 100 \
  --tiktok-video-urls data/tiktok_urls.txt

# TikTok-only via orchestration
somali-orchestrate --pipeline tiktok \
  --tiktok-video-urls data/tiktok_urls.txt \
  --tiktok-api-token YOUR_TOKEN

# All five sources for comprehensive dataset
somali-orchestrate --pipeline all \
  --max-bbc-articles 200 \
  --max-hf-records 50000 \
  --tiktok-video-urls data/tiktok_urls.txt
```

**Orchestration parameters:**
- `--pipeline tiktok` - Run TikTok only
- `--pipeline all` - Include TikTok with other sources
- `--tiktok-video-urls PATH` - Path to video URLs file (default: `data/tiktok_urls.txt`)
- `--tiktok-api-token TOKEN` - Apify API token (optional if set via env var)
- `--tiktok-user-id ID` - Optional Apify user ID

### MLOps Outputs

Each run produces:
- **Metrics:** `data/metrics/{run_id}_discovery.json`, `{run_id}_extraction.json`, `{run_id}_processing.json`
- **Quality Report:** `data/reports/{run_id}_extraction_quality_report.md`, `{run_id}_final_quality_report.md`
- **Logs:** `logs/tiktok_somali.log` (JSON format with run_id)

Quality report includes:
- ✅ Health status (Healthy/Warning/Critical)
- Processing success/failure rates
- Performance metrics (Apify actor runtime)
- Comment yield statistics (emoji-only filter rate)
- Cost tracking and recommendations

### Common Issues

**Issue**: "Apify API token not provided"
```bash
# Solution: Set environment variable
export SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=apify_api_YOUR_TOKEN

# Or use CLI flag
tiktoksom-download --video-urls data/tiktok_urls.txt --api-token apify_api_YOUR_TOKEN
```

**Issue**: "No valid URLs found in file"
```bash
# Solution: Check file format
cat data/tiktok_urls.txt

# Ensure URLs start with https://
# Valid format: https://www.tiktok.com/@username/video/1234567890

# Remove comments and empty lines
grep -v '^#' data/tiktok_urls.txt | grep -v '^$' > data/tiktok_urls_clean.txt
```

**Issue**: Apify run failed
```bash
# Solution: Check Apify console
# Visit https://console.apify.com/actors/runs
# Common causes:
#   - Invalid video URLs (not public/accessible)
#   - Age-restricted content
#   - Rate limits (reduce video count)
#   - Insufficient Apify credits
```

**Issue**: Low comment yield
```bash
# Solution: Curate better video URLs
# - Select videos with 100+ comments
# - Verify Somali language content
# - Check video engagement before adding to list
# - Mix popular creators and topics
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

### TikTok

```bash
# Download comments (uses data/tiktok_urls.txt by default)
tiktoksom-download --video-urls data/tiktok_urls.txt

# With API token override
tiktoksom-download --video-urls data/tiktok_urls.txt --api-token apify_api_YOUR_TOKEN

# With comment limits
tiktoksom-download --video-urls data/tiktok_urls.txt \
  --max-comments 10000 \
  --max-per-video 500

# Force reprocessing
tiktoksom-download --video-urls data/tiktok_urls.txt --force
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
- `"formal"` - Wikipedia, BBC, HuggingFace MC4, Språkbanken
- `"colloquial"` - TikTok (social media comments)
- `"informal"` - Future conversational/speech sources

See [Silver Schema Reference](../reference/silver-schema.md) for complete field documentation.

---


---

## Filter Telemetry

### Overview

Filter telemetry tracks which filters reject records and provides counts for each filter reason. This enables:

- **Filter effectiveness monitoring** - Which filters remove most content?
- **Quality diagnostics** - Why is a specific source underperforming?
- **Pipeline optimization** - Which filter thresholds should be adjusted?

All processors track filter applications during the quality validation phase. The results are available in three places:

1. **Raw metrics JSON** - `data/metrics/{run_id}_extraction.json` (contains `filter_breakdown`)
2. **Quality reports** - `data/reports/{run_id}_final_quality_report.md` (human-readable summaries)
3. **Dashboard** - Quality Insights tab shows filter footprint charts for each source

### Finding Filter Breakdowns

#### In Metrics JSON

```bash
# View filter breakdown for a specific run
cat data/metrics/20251101_132706_bbc-somali_e02325d4_extraction.json | jq '.layered_metrics.quality.filter_breakdown'

# Output example:
# {
#   "min_length_filter": 45,
#   "langid_filter": 12,
#   "dialect_heuristic_filter": 3
# }
```

#### In Consolidated Dashboard Data

```bash
# View all filters across all sources
cat _site/data/all_metrics.json | jq '.metrics[].filter_breakdown'

# Filter by specific source
cat _site/data/all_metrics.json | jq '.metrics[] | select(.source == "TikTok-Somali") | .filter_breakdown'
```

### Filter Catalog

All available filters are defined in the central filter catalog: `src/somali_dialect_classifier/pipeline/filters/catalog.py`

This catalog provides:
- **Human-readable labels** - "Minimum length (50 chars)" instead of "min_length_filter"
- **Descriptions** - Why each filter exists and what it checks
- **Categories** - Filters grouped by type (length, language, content)

For the complete list of available filters, see the [Filter Catalog Reference](../reference/filters.md).

**Dynamic Loading (New in v2.0):** The dashboard now loads filter metadata dynamically from a JSON export of the Python catalog, eliminating manual label synchronization.

```bash
# Export filter catalog for dashboard
python scripts/export_filter_catalog.py

# Output: dashboard/data/filter_catalog.json
```

### Filter Registration

**IMPORTANT:** Filters must be registered using the correct signature pattern. The `FilterEngine.register_filter()` method expects separate parameters, not tuples.

**Correct Pattern:**
```python
from somali_dialect_classifier.preprocessing.filters import (
    min_length_filter,
    langid_filter,
    topic_lexicon_enrichment_filter
)

class BBCSomaliProcessor(BasePipeline):
    def _register_filters(self):
        """Register filters with correct signature."""
        # CORRECT: Pass function and kwargs separately
        self.filter_engine.register_filter(
            min_length_filter,
            {"threshold": 50}
        )

        self.filter_engine.register_filter(
            langid_filter,
            {"allowed_langs": {"so"}, "confidence_threshold": 0.5}
        )

        self.filter_engine.register_filter(
            topic_lexicon_enrichment_filter,
            {"ruleset": topic_lexicons, "enrich_only": True}
        )
```

**Incorrect Pattern (DO NOT USE):**
```python
# WRONG: Do not pass tuples
self.filter_engine.register_filter((min_length_filter, {"threshold": 50}))

# WRONG: Do not unpack tuples in for loop
filters = [
    (min_length_filter, {"threshold": 50}),
    (langid_filter, {"allowed_langs": {"so"}})
]
for filter_spec in filters:
    self.filter_engine.register_filter(filter_spec)  # WRONG!
```

**Why This Matters:**
- Incorrect registration causes filters to fail silently
- Metrics will show incorrect filter statistics
- Records that should be filtered may pass through
- Fixed in Phase A of Stage 1 implementation (2025-11-13)

### Adding New Filters

To add a new filter and have it tracked in telemetry:

**Step 1:** Define filter in catalog
```python
# src/somali_dialect_classifier/pipeline/filters/catalog.py
FILTER_CATALOG["my_new_filter"] = (
    "Filter Label",
    "Description of what this filter does",
    "category"  # length, language, content, etc.
)
```

**Step 2:** Implement filter logic
```python
# In your processor (e.g., wikipedia_somali_processor.py)
def apply_my_new_filter(text):
    if some_condition_fails:
        if hasattr(self, 'metrics') and self.metrics:
            self.metrics.record_filter_reason("my_new_filter")
        return None
    return text
```

**Step 3:** Register filter in processor
```python
def _register_filters(self):
    # CORRECT: Separate parameters
    self.filter_engine.register_filter(
        my_new_filter,
        {"param1": value1, "param2": value2}
    )
```

**Step 4:** Update dashboard labels
```javascript
// dashboard/js/core/aggregates.js
const FILTER_REASON_LABELS = {
    "my_new_filter": "Filter Label",  // Match catalog label
    // ... existing filters
}
```

### Example Filter Breakdown JSON

```json
{
  "_schema_version": "3.0",
  "_source": "BBC-Somali",
  "_run_id": "20251101_132706_bbc-somali_e02325d4",
  "layered_metrics": {
    "quality": {
      "records_received": 500,
      "records_passed_filters": 430,
      "filter_breakdown": {
        "min_length_filter": 45,
        "langid_filter": 15,
        "topic_lexicon_enrichment_filter": 10
      }
    }
  }
}
```

### Historical Analytics (New in v2.0)

**Export filter metrics to Parquet for trend analysis and data warehouse integration:**

```bash
# Export all historical filter metrics
python scripts/export_filters_to_parquet.py

# Query with DuckDB
python scripts/query_filter_history.py

# Outputs:
#   - data/warehouse/filter_history.parquet/ (partitioned by source and month)
#   - Query results showing filter trends over time
```

**Example queries:**

```python
import duckdb

con = duckdb.connect()

# Top filters by volume (last 90 days)
query = """
SELECT
    filter_label,
    filter_category,
    SUM(records_filtered) AS total_filtered,
    AVG(records_filtered::FLOAT / total_records_filtered) AS avg_percentage
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY filter_label, filter_category
ORDER BY total_filtered DESC
"""

df = con.execute(query).df()
print(df)
```

See [Filter Analytics Guide](filter-analytics.md) for comprehensive examples, Jupyter notebooks, and data warehouse integration.

### Regression Testing (New in v2.0)

**Automated tests prevent filter telemetry regressions:**

```bash
# Run regression tests
pytest tests/regression/test_filter_telemetry.py -v

# Expected output:
# test_filter_breakdown_not_empty_when_filtering ... PASSED
# test_filter_breakdown_sum_consistency ... PASSED
# test_critical_filters_tracked ... PASSED
```

**What regression tests check:**

1. **Coverage:** `filter_breakdown` not empty when `records_filtered > 0`
2. **Consistency:** Sum of filter counts ≤ total records filtered
3. **Critical filters:** Source-specific filters are tracked (e.g., TikTok must track `emoji_only_comment`)

**Updating test baselines:**

```bash
# Generate new baseline after intentional filter changes
python tests/regression/fixtures/generate_test_metrics.py

# Commit with explanation
git add tests/regression/fixtures/
git commit -m "test: update filter baselines after adding profanity_filter"
```

See [CONTRIBUTING.md](../../CONTRIBUTING.md#regression-tests) for complete testing guide.

### See Also

- **[Metrics Schema Reference](../reference/metrics-schema.md#filter-telemetry)** - Complete `filter_breakdown` field specification
- **[Filter Catalog Reference](../reference/filters.md)** - All available filters with descriptions
- **[TikTok Integration Guide](tiktok-integration.md#filter-telemetry)** - TikTok-specific filter stages
- **[Filter Analytics Guide](filter-analytics.md)** - Historical analysis with Parquet export (NEW)
- **[CI Monitoring Guide](ci-metrics-anomaly-detection.md)** - Automated anomaly detection (NEW)

## Comparison by Source

| Aspect | Wikipedia | BBC | HuggingFace | Språkbanken | TikTok |
|--------|-----------|-----|-------------|-------------|---------|
| **Content Type** | Encyclopedia | News | Web scrapes | Academic corpora | Social media comments |
| **Language Style** | Formal, educational | Journalistic | Informal, varied | Domain-specific | Colloquial, conversational |
| **Register** | Formal | Formal | Formal | Formal | Colloquial |
| **Size** | ~50k articles | ~500+ articles | ~100k-200k records | 23 corpora (varied) | 300-1,500 per run |
| **License** | CC-BY-SA-3.0 | BBC Terms of Use | ODC-BY-1.0 | CC BY 4.0 | TikTok Terms of Service |
| **Update Frequency** | Weekly dumps | Daily (scraping) | Static snapshot | Static corpora | On-demand (API) |
| **Metadata Richness** | Medium | High (topics) | Low | Very High (domains) | High (engagement, authors) |
| **Processing Time** | ~5 minutes | ~10 min (10 articles)<br>~1.5 hrs (100 articles)<br>~7-8 hrs (500 articles) | ~1.5 hours (100k) | ~30-60 min (all 23) | ~2 min (5 videos)<br>~10-15 min (50 videos) |
| **Performance Note** | Fast (local XML) | Slow (server response)<br>~50-60s per article | Medium (streaming) | Fast (static files) | Fast (API actor) |
| **Cost** | Free | Free (ethical scraping) | Free | Free | $1 per 1k comments<br>(~$3.67 per 1k linguistic) |
| **Best For** | Formal baseline | Current events, topics | Large-scale training | Domain diversity | Dialect diversity, colloquial Somali |

---

## See Also

### Integration Guides (Comprehensive Documentation)

- **[Wikipedia Integration Guide](wikipedia-integration.md)** - Complete guide to Wikipedia dumps, XML parsing, and namespace filtering
- **[BBC Integration Guide](bbc-integration.md)** - Ethical web scraping, topic enrichment, and rate limiting
- **[HuggingFace Integration Guide](huggingface-integration.md)** - Streaming datasets, manifests, and JSONL batching
- **[Språkbanken Integration Guide](sprakbanken-integration.md)** - All 23 corpora, domain mapping, and metadata extraction
- **[TikTok Integration Guide](tiktok-integration.md)** - Apify API setup, video curation, cost management, and colloquial Somali collection

### Other Documentation

- [Configuration Guide](configuration.md) - Environment variables and config management
- [Custom Filters Guide](custom-filters.md) - Writing custom quality filters
- [API Reference](../reference/api.md) - Complete API documentation for all processors
- [Architecture Overview](../overview/architecture.md) - System design and patterns
- [Data Pipeline Overview](../overview/data-pipeline-architecture.md) - ETL architecture and medallion layers

---

**Last Updated**: 2025-11-01
**Maintainers**: Somali NLP Contributors
