# Deduplication Strategy

**Comprehensive guide to discovery-stage deduplication, continuous streaming, and cross-run duplicate prevention.**

**Last Updated:** 2025-11-21

---

---

## Table of Contents

- [Overview](#overview)
- [Phase 1: Discovery-Stage Deduplication](#phase-1-discovery-stage-deduplication)
  - [Concept](#concept)
  - [Benefits](#benefits)
  - [Implementation Across Sources](#implementation-across-sources)
    - [Wikipedia](#wikipedia)
    - [BBC News](#bbc-news)
    - [HuggingFace Datasets](#huggingface-datasets)
    - [Språkbanken Corpora](#språkbanken-corpora)
    - [TikTok Comments](#tiktok-comments)
- [Continuous Streaming (HuggingFace)](#continuous-streaming-huggingface)
  - [Problem](#problem)
  - [Solution](#solution)
  - [Checkpoint Management](#checkpoint-management)
  - [Result](#result)
- [Phase 2: Extraction-Stage Deduplication](#phase-2-extraction-stage-deduplication)
  - [Concept](#concept)
  - [MinHash LSH](#minhash-lsh)
- [Phase 3: Processing-Stage Deduplication](#phase-3-processing-stage-deduplication)
  - [Concept](#concept)
  - [Cross-Dataset Deduplication](#cross-dataset-deduplication)
- [Crawl Ledger Schema](#crawl-ledger-schema)
  - [State Transitions](#state-transitions)
- [Testing Deduplication](#testing-deduplication)
  - [Test 1: Discovery-Stage Deduplication](#test-1-discovery-stage-deduplication)
  - [Test 2: Continuous Streaming](#test-2-continuous-streaming)
  - [Test 3: Cross-Run Deduplication](#test-3-cross-run-deduplication)
- [Force Reprocessing](#force-reprocessing)
- [Metrics](#metrics)
- [Troubleshooting](#troubleshooting)
  - [Issue: HuggingFace always replays JSONL instead of streaming new records](#issue-huggingface-always-replays-jsonl-instead-of-streaming-new-records)
  - [Issue: Ledger shows URLs as processed but silver dataset is empty](#issue-ledger-shows-urls-as-processed-but-silver-dataset-is-empty)
  - [Issue: Discovery dedup not working, re-downloading identical data](#issue-discovery-dedup-not-working-re-downloading-identical-data)

---

## Overview

The Somali Dialect Classifier implements a **three-phase deduplication strategy** to eliminate duplicate text across pipeline runs while minimizing bandwidth waste and computational overhead:

1. **Phase 1: Discovery-Stage Deduplication** - Check crawl ledger BEFORE fetching/streaming
2. **Phase 2: Extraction-Stage Deduplication** - In-memory exact and near-duplicate detection during extraction
3. **Phase 3: Processing-Stage Deduplication** - Cross-dataset LSH-based near-duplicate detection

This guide focuses on **Phase 1** (discovery-stage) and **continuous streaming**, which were recently implemented to prevent re-downloading already-processed records.

---

## Phase 1: Discovery-Stage Deduplication

### Concept

**Discovery-stage deduplication** checks the crawl ledger BEFORE fetching or streaming data from sources. If a URL/record is already marked as `processed` in the ledger, it is skipped entirely, saving bandwidth and processing time.

### Benefits

- **Bandwidth Savings**: Avoids re-downloading identical data
- **Faster Pipeline Runs**: Skips already-processed records immediately
- **Cost Reduction**: Reduces API calls for paid services (TikTok via Apify)
- **Idempotency**: Running the pipeline multiple times produces consistent results

### Implementation Across Sources

#### Wikipedia

Wikipedia implements **two-level discovery-stage deduplication**:

**Level 1: Dump-Level Deduplication (HTTP Conditional Requests)**

```python
# Check if dump URL should be fetched
dump_url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

if not ledger.should_fetch_url(dump_url, force=False):
    # Dump exists in ledger - check if it changed using HTTP conditional request
    headers = ledger.get_conditional_headers(dump_url)
    # headers = {"If-None-Match": "690684aa-e1fde6", "If-Modified-Since": "Sat, 01 Nov..."}

    response = requests.head(dump_url, headers=headers)

    if response.status_code == 304:  # Not Modified
        logger.info(f"Dump unchanged (304) - skipping all processing")
        return None  # Skip download, parse, and processing

    # 200 OK - dump changed, proceed to download
    logger.info(f"Dump changed (200) - downloading new version")

# Download and mark with ETag/Last-Modified
response = requests.get(dump_url)
ledger.mark_fetched(dump_url, etag=response.headers['ETag'],
                    last_modified=response.headers['Last-Modified'])
```

**Level 2: Article-Level Deduplication (URL Filtering)**

```python
# After parsing dump, filter already-processed articles
processed_records = ledger.get_processed_urls(source="wikipedia", limit=None)
processed_urls = {r['url'] for r in processed_records if 'url' in r}
logger.info(f"Found {len(processed_urls)} already-processed articles")

new_articles = []
for article in parsed_articles:
    if article['url'] in processed_urls:
        metrics.increment("articles_skipped_already_processed")
        continue
    new_articles.append(article)

logger.info(f"Article filtering: {len(parsed_articles)} → {len(new_articles)} new")
```

**Result:**
- Run 2 (same dump): HEAD request → 304 → Skip everything (~44s saved)
- Run 3 (new dump, 10 new articles): HEAD → 200 → Download → Filter → Process only 10 articles

#### BBC News

```python
# BBC discovers article URLs, then checks ledger before scraping
discovered_urls = discover_articles()  # From RSS feeds, topic pages, sitemap

for url in discovered_urls:
    if ledger.should_fetch_url(url, force=False):
        # Scrape article
        article = scrape_article(url)
        ledger.mark_fetched(url, http_status=200)
        ledger.mark_processed(url, text_hash=hash, silver_id=id, source="bbc")
    else:
        logger.info(f"Skipping already-processed article: {url}")
```

**Result**: BBC only scrapes NEW articles, skipping previously scraped ones.

#### HuggingFace Datasets

```python
# HuggingFace loads processed URLs from ledger before streaming
processed_urls = set()
if ledger:
    processed_urls = ledger.get_processed_urls(source="HuggingFace-Somali_c4-so")
    logger.info(f"PHASE 1 DEDUP: Loaded {len(processed_urls)} already-processed URLs")

# Stream dataset, skipping already-processed URLs
for record in dataset:
    url = record['url']
    if url in processed_urls:
        metrics.increment("records_skipped_discovery_dedup")
        continue

    # Process new record
    process_record(record)
    ledger.mark_processed(url, text_hash=hash, silver_id=id, source="HuggingFace-Somali_c4-so")
```

**Result**: HuggingFace skips records with URLs already in ledger, enabling continuous streaming.

#### Språkbanken Corpora

```python
# Språkbanken checks corpus ID in ledger before downloading XML
for corpus_id in corpora_to_process:
    corpus_url = f"https://spraakbanken.gu.se/lb/resurser/menota/{corpus_id}.xml.bz2"

    if ledger.should_fetch_url(corpus_url, force=False):
        # Download and extract corpus
        download_corpus(corpus_url)
        extract_corpus(corpus_file)
        ledger.mark_processed(corpus_url, text_hash=hash, silver_id=id, source="Sprakbanken-Somali")
    else:
        logger.info(f"Skipping already-downloaded corpus: {corpus_id}")
```

**Result**: Språkbanken only downloads NEW corpora, skipping already-downloaded ones.

#### TikTok Comments

```python
# TikTok checks video URLs in ledger before scraping via Apify
video_urls = discover_videos()

for video_url in video_urls:
    if ledger.should_fetch_url(video_url, force=False):
        # Scrape comments via Apify API (costs money per run)
        comments = scrape_tiktok_comments_apify(video_url)
        ledger.mark_fetched(video_url, http_status=200)
        for comment in comments:
            ledger.mark_processed(comment_url, text_hash=hash, silver_id=id, source="tiktok")
    else:
        logger.info(f"Skipping already-scraped video: {video_url}")
```

**Result**: TikTok only scrapes NEW videos, saving Apify API costs.

---

## Continuous Streaming (HuggingFace)

### Problem

Previously, when HuggingFace processor hit `max_records` limit and all records were already processed (duplicates), it would create `.extraction_complete` marker and stop streaming permanently.

On the next run, it would replay the cached JSONL files instead of continuing to stream NEW records from the dataset.

### Solution

Implement **conditional marker creation** based on why streaming stopped:

```python
# Track if stopped due to max_records limit or dataset exhaustion
stopped_at_limit = False

for i, record in enumerate(dataset_stream):
    # Check max_records limit
    if max_records and total_processed >= max_records:
        logger.info(f"Reached max_records limit: {max_records}")
        stopped_at_limit = True
        break

    # Process record...
    total_processed += 1

# Conditional marker creation
if not stopped_at_limit:
    # Dataset exhausted - mark extraction as complete
    extraction_complete_marker.touch()
    logger.info("Dataset exhausted - marking extraction as complete")
else:
    # Stopped at limit - more data available
    logger.info(f"Stopped at max_records limit - more data available to stream from offset {current_offset}")
```

### Checkpoint Management

HuggingFace processor saves checkpoints to enable resumption:

```python
# Save checkpoint every 1000 records
if total_processed % 1000 == 0:
    save_checkpoint({
        'last_index': current_offset,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'processed_count': total_processed
    })

# Load checkpoint on next run
checkpoint = load_checkpoint()
if checkpoint:
    start_offset = checkpoint['last_index']
    logger.info(f"Resuming from checkpoint: offset={start_offset}")
```

### Result

**Run 1**: Download 200 records (offset 0 → 200), all are NEW

```bash
somali-orchestrate --pipeline huggingface --max-hf-records 200
# Result: 190 records processed (10 filtered), checkpoint saved at offset 200
```

**Run 2**: Resume from offset 200, download next 200 records (offset 200 → 400)

```bash
somali-orchestrate --pipeline huggingface --max-hf-records 200
# Result: 191 records processed (9 filtered), checkpoint saved at offset 400
```

**Continuous streaming** allows incrementally downloading large datasets (e.g., MC4 with millions of records) in manageable batches.

---

## Phase 2: Extraction-Stage Deduplication

### Concept

During extraction, use **in-memory MinHash LSH** to detect near-duplicates within the current batch.

```python
from somali_dialect_classifier.preprocessing.dedup import DedupEngine, DedupConfig

# Configure deduplication
config = DedupConfig(
    hash_fields=["text", "url"],
    enable_minhash=True,
    similarity_threshold=0.85
)

dedup = DedupEngine(config)

for record in batch:
    # Compute content hash and MinHash signature
    text_hash, minhash_sig = dedup.get_content_hash(record)

    # Check for exact duplicates
    if dedup.is_exact_duplicate(text_hash):
        logger.info(f"Exact duplicate detected: {text_hash}")
        continue

    # Check for near-duplicates using LSH
    if dedup.is_near_duplicate(minhash_sig):
        logger.info(f"Near-duplicate detected (similarity >= 0.85)")
        continue

    # Process unique record
    process_record(record)
```

### MinHash LSH

**MinHash** represents documents as signatures (sets of hash values), enabling efficient similarity computation:

```
Document A: "Somali language is spoken in Somalia"
Document B: "Somali language is used in Somalia"

Jaccard Similarity: 0.88 (88% similar)
```

**LSH (Locality Sensitive Hashing)** indexes MinHash signatures for fast nearest-neighbor lookups.

---

## Phase 3: Processing-Stage Deduplication

### Concept

After all sources processed, use **persistent LSH index** to detect near-duplicates ACROSS datasets.

```python
# Save LSH index for cross-run deduplication
lsh_path = Path("data/ledger/lsh_index_huggingface.pkl")

config = DedupConfig(
    hash_fields=["text", "url"],
    enable_minhash=True,
    similarity_threshold=0.85,
    storage_path=lsh_path  # Enable persistence
)

dedup = DedupEngine(config)

# Add documents from current run
for record in silver_records:
    text_hash, minhash_sig = dedup.get_content_hash(record)
    dedup.add_document(text_hash, minhash_sig)

# Save LSH index to disk for next run
dedup.save_lsh_index()
logger.info(f"PHASE 3: Saved LSH index ({dedup.doc_count} documents) to {lsh_path}")
```

### Cross-Dataset Deduplication

Phase 3 enables detecting duplicates ACROSS sources:

```
BBC Article: "Somali government announces new policy"
HuggingFace Record: "Somalia govt announces new policy"

Jaccard Similarity: 0.87
Result: Marked as near-duplicate
```

---

## Crawl Ledger Schema

The crawl ledger is a SQLite database tracking URL states:

```sql
CREATE TABLE crawl_ledger (
    url TEXT PRIMARY KEY,
    state TEXT NOT NULL,  -- discovered, fetched, processed, failed, duplicate
    source TEXT,
    discovered_at TEXT,
    fetched_at TEXT,
    processed_at TEXT,
    http_status INTEGER,
    etag TEXT,
    last_modified TEXT,
    text_hash TEXT,
    minhash_signature BLOB,
    silver_id TEXT,
    error_message TEXT
);

CREATE INDEX idx_state ON crawl_ledger(state);
CREATE INDEX idx_source ON crawl_ledger(source);
CREATE INDEX idx_text_hash ON crawl_ledger(text_hash);
```

### State Transitions

```
discovered → fetched → processed
         ↘         ↘
          failed    duplicate
```

---

## Testing Deduplication

### Test 1: Discovery-Stage Deduplication

```bash
# Run 1: Download 5 BBC articles
somali-orchestrate --pipeline bbc --max-bbc-articles 5

# Result: 5 articles scraped, 173 URLs discovered, 5 processed

# Run 2: Same command
somali-orchestrate --pipeline bbc --max-bbc-articles 5

# Result: 5 articles skipped (already processed), 0 scraped
# Log: "Skipping already processed URL (state=processed): https://..."
```

### Test 2: Continuous Streaming

```bash
# Run 1: Download 200 HF records
somali-orchestrate --pipeline huggingface --max-hf-records 200

# Result: 190 records processed, checkpoint saved at offset 200

# Run 2: Download next 200 records
somali-orchestrate --pipeline huggingface --max-hf-records 200

# Result: 191 records processed, checkpoint saved at offset 400
# Log: "Resuming from checkpoint: offset=200"
# Log: "Stopped at max_records limit - more data available"
```

### Test 3: Cross-Run Deduplication

```bash
# Run 1: Process all sources
somali-orchestrate --pipeline all

# Result: Wikipedia 15K articles, BBC 5 articles, HF 190 records, etc.

# Run 2: Same command
somali-orchestrate --pipeline all

# Result:
# - Wikipedia: Skipped (dump URL already processed)
# - BBC: Skipped 5 articles, scraped 5 NEW articles
# - HuggingFace: Skipped 190 records, downloaded 200 NEW records (offset 200→400)
# - Språkbanken: Skipped (corpora already downloaded)
# - TikTok: Skipped all 5 videos
```

---

## Force Reprocessing

To bypass deduplication and reprocess everything:

```bash
# Force flag bypasses ledger checks
somali-orchestrate --pipeline all --force

# Result: All sources reprocessed, regardless of ledger state
```

---

## Metrics

Deduplication metrics are tracked in JSON files:

```json
{
  "records_skipped_discovery_dedup": 190,
  "records_skipped_exact_dedup": 5,
  "records_skipped_near_dedup": 3,
  "unique_documents": 182,
  "exact_duplicates": 5,
  "near_duplicates": 3
}
```

---

## Troubleshooting

### Issue: HuggingFace always replays JSONL instead of streaming new records

**Cause**: `.extraction_complete` marker exists even though dataset not exhausted

**Solution**: Delete marker file to resume streaming

```bash
rm data/staging/source=HuggingFace-Somali_c4-so/.extraction_complete
somali-orchestrate --pipeline huggingface --max-hf-records 200
```

### Issue: Ledger shows URLs as processed but silver dataset is empty

**Cause**: Processing phase failed but ledger already updated

**Solution**: Reset ledger for that source

```bash
# Reset ledger for specific source
sqlite3 data/ledger/crawl_ledger.db \
  "DELETE FROM crawl_ledger WHERE source = 'HuggingFace-Somali_c4-so';"

# Or reset entire ledger
rm data/ledger/crawl_ledger.db
```

### Issue: Discovery dedup not working, re-downloading identical data

**Cause**: Ledger tracking disabled or `url_field` not specified

**Solution**: Ensure `url_field` parameter passed to processor

```python
# ❌ Wrong: No url_field specified
processor = HuggingFaceSomaliProcessor(
    dataset_name="allenai/c4",
    text_field="text"
)

# ✅ Correct: url_field specified
processor = HuggingFaceSomaliProcessor(
    dataset_name="allenai/c4",
    text_field="text",
    url_field="url"  # Required for ledger tracking
)
```

---

## Related Documentation

- [HuggingFace Integration](huggingface-integration.md) - Streaming datasets and checkpoint management
- [Data Pipeline Guide](../guides/data-pipeline.md) - Complete pipeline overview
- [Architecture](../overview/data-pipeline-architecture.md) - Crawl ledger and deduplication architecture
- [Metrics Reference](../reference/metrics.md) - Deduplication metrics specification

---

**Maintainers**: Somali NLP Contributors
