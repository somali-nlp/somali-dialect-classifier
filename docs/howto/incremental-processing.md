# Incremental Processing

**Efficient quarterly refresh runs by skipping unchanged data and only processing new or updated records.**

**Last Updated:** 2025-11-21


---

## Table of Contents

- [Overview](#overview)
- [Benefits](#benefits)
- [How It Works](#how-it-works)
  - [Core Strategy](#core-strategy)
  - [Implementation Patterns](#implementation-patterns)
    - [Pattern 1: Timestamp-Based Filtering (Wikipedia)](#pattern-1-timestamp-based-filtering-wikipedia)
    - [Pattern 2: Resource ID-Based Filtering (Språkbanken)](#pattern-2-resource-id-based-filtering-språkbanken)
- [First Run vs Subsequent Runs](#first-run-vs-subsequent-runs)
  - [First Run Behavior](#first-run-behavior)
  - [Subsequent Run Behavior](#subsequent-run-behavior)
- [Configuration](#configuration)
  - [Forcing Full Re-Processing](#forcing-full-re-processing)
- [Fail-Safe Design](#fail-safe-design)
  - [Missing Timestamps](#missing-timestamps)
  - [Ledger Unavailable](#ledger-unavailable)
  - [Unknown Corpus IDs](#unknown-corpus-ids)
- [Metrics Interpretation](#metrics-interpretation)
  - [Wikipedia Incremental Metrics](#wikipedia-incremental-metrics)
  - [Språkbanken Incremental Metrics](#språkbanken-incremental-metrics)
- [Troubleshooting](#troubleshooting)
  - [Issue: All records filtered on first run](#issue-all-records-filtered-on-first-run)
  - [Issue: Too many records processed on subsequent run](#issue-too-many-records-processed-on-subsequent-run)
  - [Issue: Incremental filtering not working](#issue-incremental-filtering-not-working)
- [Performance Benchmarks](#performance-benchmarks)
  - [Wikipedia (14MB dump, 9,960 articles)](#wikipedia-14mb-dump-9960-articles)
  - [Språkbanken (66 corpora, 196KB)](#språkbanken-66-corpora-196kb)
- [Advanced Usage](#advanced-usage)
  - [Query Processing History](#query-processing-history)
  - [Custom Filtering Logic](#custom-filtering-logic)
- [Summary](#summary)

---
## Overview

Incremental processing enables efficient quarterly refresh runs by skipping unchanged data and only processing new or updated records. This feature achieves 90%+ efficiency gains by tracking processing history in the ledger and filtering records based on timestamps or resource identifiers.

## Benefits

- **Bandwidth savings**: 90%+ reduction in data downloads
- **Processing time**: 95% reduction in processing time for quarterly refreshes
- **Compute efficiency**: Only process changed data
- **Data freshness**: Easily keep datasets up-to-date with minimal overhead

## How It Works

### Core Strategy

1. **Track last successful processing time** in the ledger
2. **Filter records** based on timestamp (Wikipedia) or resource ID (Språkbanken)
3. **Skip unchanged sources** entirely
4. **Maintain full data quality** (no shortcuts on validation)

### Implementation Patterns

#### Pattern 1: Timestamp-Based Filtering (Wikipedia)

Used when records have reliable timestamps indicating when they were last modified.

```python
from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import WikipediaSomaliProcessor

# First run: Processes all 9,960 articles
processor = WikipediaSomaliProcessor()
processor.run()

# Subsequent run: Only processes articles modified since last run
# (typically 50-100 new/updated articles per quarter)
processor = WikipediaSomaliProcessor()
processor.run()  # Automatically filters based on ledger timestamps
```

**How it works:**
1. Query ledger for last successful processing time
2. Parse article timestamps from XML
3. Compare article timestamps with last processing time
4. Skip articles older than last processing time

**Metrics tracked:**
- `total`: Total articles in dump
- `new`: New articles to process
- `skipped`: Articles skipped (unchanged)
- `efficiency_gain_percent`: Percentage of work saved

#### Pattern 2: Resource ID-Based Filtering (Språkbanken)

Used when records represent discrete resources (e.g., corpora files) that don't change.

```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import SprakbankenSomaliProcessor

# First run: Downloads and processes all 66 corpora
processor = SprakbankenSomaliProcessor(corpus_id="all")
processor.run()

# Subsequent run: Only processes new corpora (if any)
processor = SprakbankenSomaliProcessor(corpus_id="all")
processor.run()  # Automatically skips already-processed corpora
```

**How it works:**
1. Query ledger for processed corpus IDs
2. Extract corpus IDs from URLs
3. Filter requested corpora against processed set
4. Skip already-processed corpora

**Metrics tracked:**
- `total`: Total corpora requested
- `new`: New corpora to download
- `skipped`: Corpora skipped (already processed)
- `processed_corpus_ids`: List of corpus IDs already processed

## First Run vs Subsequent Runs

### First Run Behavior
- No filtering applied
- All records processed
- Ledger populated with processing timestamps
- Baseline established for future runs

```
[INFO] First run detected - processing all articles
```

### Subsequent Run Behavior
- Filtering enabled automatically
- Only new/changed records processed
- Efficiency metrics tracked
- Ledger updated with new timestamps

```
[INFO] Filtering articles newer than 2025-11-10T12:00:00Z
[INFO] Filtered 9,910 unchanged articles, 50 new articles
```

## Configuration

Incremental processing is **enabled by default** and requires no configuration. The system automatically:
- Tracks processing timestamps in the ledger
- Filters records on subsequent runs
- Falls back to full processing if ledger unavailable

### Forcing Full Re-Processing

To bypass incremental filtering and re-process all records:

```python
# Force full re-processing
processor = WikipediaSomaliProcessor(force=True)
processor.run()
```

**When to use `force=True`:**
- After schema changes
- After cleaning/text processing updates
- After deduplication logic changes
- To recover from corrupted runs

## Fail-Safe Design

Incremental processing is designed to fail safely:

### Missing Timestamps
If article timestamps are invalid or missing, the article is processed (conservative approach).

```python
# Article with no timestamp → PROCESSED (fail-safe)
# Article with invalid timestamp → PROCESSED (fail-safe)
```

### Ledger Unavailable
If ledger query fails, all records are processed (conservative approach).

```python
# Ledger unavailable → process all records (fail-safe)
# Ledger query error → process all records (fail-safe)
```

### Unknown Corpus IDs
If corpus ID cannot be extracted from URL, the corpus is processed (conservative approach).

```python
# Cannot extract corpus ID → PROCESSED (fail-safe)
```

## Metrics Interpretation

### Wikipedia Incremental Metrics

```json
{
  "incremental_filtering": {
    "total": 9960,
    "new": 50,
    "skipped": 9910,
    "last_processing_time": "2025-11-10T12:00:00Z"
  }
}
```

**Interpretation:**
- **Efficiency gain**: 99.5% (9,910 / 9,960 articles skipped)
- **Time saved**: ~180 seconds (3 minutes)
- **Work remaining**: 50 articles to process

### Språkbanken Incremental Metrics

```json
{
  "incremental_filtering": {
    "total": 66,
    "new": 0,
    "skipped": 66,
    "processed_corpus_ids": ["somali-cilmi", "somali-cb", ...]
  }
}
```

**Interpretation:**
- **Efficiency gain**: 100% (all 66 corpora skipped)
- **Time saved**: Complete run skipped
- **Work remaining**: 0 corpora to process

## Troubleshooting

### Issue: All records filtered on first run

**Symptom:**
```
[INFO] Filtered 9,960 unchanged articles, 0 new articles
```

**Cause:** Ledger contains stale entries from previous runs

**Solution:**
1. Use `force=True` to bypass filtering
2. OR: Clean ledger for specific source:
   ```python
   from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

   ledger = get_ledger()
   # Option 1: Remove all processed URLs for source
   # (requires manual SQL)

   # Option 2: Force re-processing
   processor = WikipediaSomaliProcessor(force=True)
   processor.run()
   ```

### Issue: Too many records processed on subsequent run

**Symptom:**
```
[INFO] Filtered 0 unchanged articles, 9,960 new articles
```

**Cause:** Timestamps might be incorrect or last processing time not recorded

**Solution:**
1. Check ledger has processed entries:
   ```python
   ledger = get_ledger()
   last_time = ledger.get_last_processing_time("Wikipedia-Somali")
   print(f"Last processing time: {last_time}")
   ```

2. Verify article timestamps are being parsed correctly
3. Check ledger database integrity

### Issue: Incremental filtering not working

**Symptom:**
```
[INFO] First run detected - processing all articles
```
(even though you've run before)

**Cause:** Ledger not finding processed records for this source

**Solution:**
1. Verify source name matches ledger:
   ```python
   ledger = get_ledger()
   stats = ledger.get_statistics("Wikipedia-Somali")
   print(stats)  # Should show processed URLs
   ```

2. Check database path is correct:
   ```python
   from somali_dialect_classifier.config import get_config
   config = get_config()
   db_path = config.data.raw_dir.parent / "ledger" / "crawl_ledger.db"
   print(f"Ledger path: {db_path}")
   print(f"Exists: {db_path.exists()}")
   ```

## Performance Benchmarks

### Wikipedia (14MB dump, 9,960 articles)

| Run Type | Articles Processed | Time | Bandwidth | Efficiency Gain |
|----------|-------------------|------|-----------|-----------------|
| First Run | 9,960 | 3 min | 14MB | 0% (baseline) |
| Quarterly Refresh | 50 | 10 sec | 14MB | 99.5% (time) |
| Annual Savings | - | 12 min | 56MB | 95% avg |

### Språkbanken (66 corpora, 196KB)

| Run Type | Corpora Processed | Time | Bandwidth | Efficiency Gain |
|----------|------------------|------|-----------|-----------------|
| First Run | 66 | 2 min | 196KB | 0% (baseline) |
| Quarterly Refresh | 0 | 0 sec | 0KB | 100% |
| Annual Savings | - | 8 min | 784KB | 100% |

## Advanced Usage

### Query Processing History

```python
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()

# Get last processing time for a source
last_time = ledger.get_last_processing_time("Wikipedia-Somali")
print(f"Last processed: {last_time}")

# Get all processed URLs for a source
processed = ledger.get_processed_urls("sprakbanken", limit=10)
for record in processed:
    print(f"{record['url']} - {record['updated_at']}")

# Get processing statistics
stats = ledger.get_statistics("Wikipedia-Somali")
print(f"Total processed: {stats['by_state'].get('processed', 0)}")
```

### Custom Filtering Logic

To implement incremental processing for a new source:

```python
from datetime import datetime
from typing import Optional

def _get_last_processing_time(self) -> Optional[datetime]:
    """Get last processing time from ledger."""
    try:
        return self.ledger.get_last_processing_time(self.source)
    except Exception as e:
        self.logger.warning(f"Failed to get last processing time: {e}")
        return None  # Fail-safe: process all

def _filter_new_records(self, records: list[dict]) -> tuple[list[dict], dict]:
    """Filter records based on last processing time."""
    last_time = self._get_last_processing_time()

    if last_time is None:
        # First run: process all
        return records, {
            "total": len(records),
            "new": len(records),
            "skipped": 0
        }

    # Filter records newer than last_time
    new_records = [
        r for r in records
        if parse_timestamp(r.get("timestamp", "")) > last_time
    ]

    return new_records, {
        "total": len(records),
        "new": len(new_records),
        "skipped": len(records) - len(new_records)
    }
```

## Related Documentation

- [Crawl Ledger](../reference/api.md#crawl-ledger) - Persistent state tracking
- [Metrics Collection](../reference/metrics.md) - Performance tracking
- [Pipeline Architecture](../overview/architecture.md) - Overall design
- [Deduplication](deduplication.md) - Duplicate detection

## Summary

Incremental processing provides:
- **Automatic filtering** based on processing history
- **90%+ efficiency gains** on subsequent runs
- **Fail-safe design** (conservative when in doubt)
- **Zero configuration** required
- **Full metrics tracking** for visibility

The system is designed to be transparent, efficient, and safe - defaulting to processing records when in doubt to ensure no data loss.
**Maintainers**: Somali NLP Contributors
