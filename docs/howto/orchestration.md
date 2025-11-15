# Pipeline Orchestration Guide

**Last Updated**: 2025-11-11

## Overview

Pipeline orchestration coordinates the execution of all five data source processors with smart scheduling, cadence-based refresh logic, and distributed locking to prevent concurrent runs. The orchestrator manages:

- **Refresh cadences** - Each source has a configured refresh interval (1-30 days)
- **Initial collection phase** - First 6 days run all sources daily to build baseline dataset
- **Incremental processing** - Subsequent runs only process new/changed data (90%+ efficiency)
- **Distributed locking** - Prevents concurrent pipeline runs from corrupting data
- **Quality monitoring** - Unified metrics collection across all sources

## Quick Start

### Run All Pipelines

```bash
# Run all five sources (BBC, Wikipedia, TikTok, Språkbanken, HuggingFace)
somali-orchestrate --pipeline all

# With limits for testing
somali-orchestrate --pipeline all \
  --max-bbc-articles 100 \
  --max-hf-records 10000
```

### Run Specific Pipeline

```bash
# BBC Somali only
somali-orchestrate --pipeline bbc --max-bbc-articles 500

# Wikipedia only
somali-orchestrate --pipeline wikipedia

# TikTok only (requires Apify API token)
somali-orchestrate --pipeline tiktok --tiktok-video-urls data/tiktok_urls.txt

# Språkbanken specific corpus
somali-orchestrate --pipeline sprakbanken --sprakbanken-corpus somali-cilmi
```

### Skip Specific Sources

```bash
# Run all except HuggingFace and TikTok
somali-orchestrate --pipeline all --skip-sources huggingface,tiktok

# Run only formal sources (Wikipedia + BBC + Språkbanken)
somali-orchestrate --pipeline all --skip-sources huggingface,tiktok
```

## Orchestration Concepts

### Refresh Cadences

Each data source has a configured refresh cadence based on its update frequency:

| Source | Default Cadence | Rationale |
|--------|----------------|-----------|
| BBC | 1 day | Daily news updates, high-frequency content |
| TikTok | 3 days | Active social media, frequent new comments |
| Wikipedia | 7 days | Weekly content changes, moderate update rate |
| Språkbanken | 30 days | Static academic corpora, rare updates |
| HuggingFace | 30 days | Static dataset snapshots, rare updates |

**Cadence Logic:**
- Sources only run when `time_since_last_run >= cadence_days`
- If cadence not met, pipeline is skipped with informative message
- Cadences are configurable via environment variables

### Initial Collection Phase

The **initial collection phase** is the first 6 days after project initialization. During this phase:

1. **All sources run daily** regardless of their configured cadence
2. **Purpose**: Quickly build a comprehensive baseline dataset
3. **Duration**: 6 days (configurable via `SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS`)
4. **Transition**: After 6 days, sources switch to their individual cadences

**Example Timeline:**

```
Day 1: BBC, Wikipedia, TikTok, Språkbanken, HuggingFace (all run)
Day 2: BBC, Wikipedia, TikTok, Språkbanken, HuggingFace (all run)
Day 3: BBC, Wikipedia, TikTok, Språkbanken, HuggingFace (all run)
Day 4: BBC, Wikipedia, TikTok, Språkbanken, HuggingFace (all run)
Day 5: BBC, Wikipedia, TikTok, Språkbanken, HuggingFace (all run)
Day 6: BBC, Wikipedia, TikTok, Språkbanken, HuggingFace (all run)
Day 7: BBC only (Wikipedia: 7-day cadence not met)
Day 8: BBC, Wikipedia (Wikipedia: 7 days elapsed)
Day 14: BBC (daily), TikTok (3 days not met)
Day 15: BBC, TikTok, Wikipedia (all cadences met)
```

**Check if in Initial Collection:**

```python
from somali_dialect_classifier.orchestration.flows import is_initial_collection_phase

if is_initial_collection_phase():
    print("In initial collection phase - all sources run daily")
else:
    print("In refresh phase - sources run per cadence")
```

### Incremental Processing

After initial collection, pipelines automatically use **incremental processing** to skip unchanged data:

**Wikipedia Incremental Processing:**
- Filters articles by timestamp
- Only processes articles modified since last run
- Achieves 99%+ efficiency on quarterly refreshes (50 new articles vs 9,960 total)

**Språkbanken Incremental Processing:**
- Filters corpora by resource ID
- Skips already-processed corpora
- Achieves 100% efficiency (static corpora don't change)

**Efficiency Gains:**

| Source | First Run | Quarterly Refresh | Efficiency Gain |
|--------|-----------|------------------|-----------------|
| Wikipedia | 9,960 articles (3 min) | 50 articles (10 sec) | 99.5% |
| Språkbanken | 66 corpora (2 min) | 0 corpora (0 sec) | 100% |
| BBC | Full RSS crawl | Incremental RSS | 90%+ |

See [Incremental Processing Guide](incremental-processing.md) for details.

### Three-Tier Deduplication

The orchestrator coordinates a three-tier deduplication strategy:

1. **Discovery-stage dedup** - Check if URL already processed in ledger (prevents redundant downloads)
2. **Processing-stage dedup** - Hash-based exact duplicate detection within run
3. **Cross-run dedup** - Near-duplicate detection across all runs (MinHash LSH)

**Deduplication Flow:**

```
URL discovered → Check ledger (Tier 1)
                ↓ If new
              Download → Extract → Clean
                ↓
              Compute hashes → Check within-run (Tier 2)
                ↓ If unique
              Write to silver → Cross-run MinHash (Tier 3)
                ↓ If unique
              Final silver dataset
```

See [Deduplication Guide](deduplication.md) for details.

## Configuration

### Environment Variables

Configure refresh cadences and orchestration behavior:

```bash
# .env file

# ============================================================================
# Orchestration Configuration
# ============================================================================

# Initial collection phase duration (days all sources run daily)
SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS=6

# Refresh cadences (days between runs)
SDC_ORCHESTRATION__BBC_CADENCE=1              # Daily news updates
SDC_ORCHESTRATION__WIKIPEDIA_CADENCE=7        # Weekly encyclopedia updates
SDC_ORCHESTRATION__TIKTOK_CADENCE=3           # Every 3 days for social media
SDC_ORCHESTRATION__SPRAKBANKEN_CADENCE=30     # Monthly for static corpora
SDC_ORCHESTRATION__HUGGINGFACE_CADENCE=30     # Monthly for static datasets

# Ledger backend (sqlite or postgres)
SDC_LEDGER_BACKEND=sqlite                      # or postgres for production
SDC_LEDGER_SQLITE_PATH=data/ledger/crawl_ledger.db

# PostgreSQL configuration (if using postgres backend)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=somali_nlp
POSTGRES_USER=somali
POSTGRES_PASSWORD="<secure_password_here>"

# Daily quotas per source (enforced in Phase C, 2025-11-13)
SDC_ORCHESTRATION__QUOTA_LIMITS__BBC=350
SDC_ORCHESTRATION__QUOTA_LIMITS__HUGGINGFACE=10000
SDC_ORCHESTRATION__QUOTA_LIMITS__SPRAKBANKEN=10
SDC_ORCHESTRATION__QUOTA_LIMITS__WIKIPEDIA=0          # Unlimited (file-based)
SDC_ORCHESTRATION__QUOTA_LIMITS__TIKTOK=0            # Manual scheduling
```

### Daily Quotas (New in Phase C)

The orchestrator enforces daily quotas to prevent excessive API usage and manage processing load:

| Source | Daily Limit | Enforcement | Rationale |
|--------|-------------|-------------|-----------|
| **BBC** | 350 articles | Hard stop at quota | Ethical web scraping, prevent server overload |
| **HuggingFace** | 10,000 records | Hard stop at quota | Manage processing time (100k+ dataset) |
| **Språkbanken** | 10 corpora | Hard stop at quota | Static collection, rare updates |
| **TikTok** | Manual scheduling | No automatic quota | Requires manual URL input, controlled externally |
| **Wikipedia** | Unlimited | No quota | File-based download, efficient processing |

**How Quotas Work:**

1. **Quota Check**: Before processing, orchestrator checks today's record count
2. **Hard Stop**: Processing stops immediately when quota is reached
3. **Daily Reset**: Quotas reset at midnight UTC
4. **Carry Forward**: Remaining items processed in next run (if within cadence)
5. **Metrics**: `quota_hit`, `quota_limit`, `quota_used`, and `items_remaining` tracked

**Example with Quota:**

```bash
# BBC quota example (350 articles/day)
somali-orchestrate --pipeline bbc

# Output:
# [INFO] BBC: Starting processing...
# [INFO] BBC: Discovered 500 articles
# [INFO] BBC: Processing articles...
# [INFO] BBC: Processed 350 articles (quota reached)
# [WARN] BBC: 150 articles remaining for next run
# [INFO] BBC: Quota metrics: {"quota_hit": true, "quota_limit": 350, "quota_used": 350, "items_remaining": 150}
```

**Quota Metrics Schema:**

```json
{
  "quota_hit": true,           // Whether quota was reached
  "quota_limit": 350,          // Configured daily limit
  "quota_used": 350,           // Records processed today
  "items_remaining": 150       // Records skipped due to quota
}
```

**Overriding Quotas:**

```bash
# Increase BBC quota to 500
export SDC_ORCHESTRATION__QUOTA_LIMITS__BBC=500

# Disable quota (set very high limit)
export SDC_ORCHESTRATION__QUOTA_LIMITS__BBC=999999

# Programmatic override
config.orchestration.quota_limits["bbc"] = 500
```

**Quota Best Practices:**

1. **Don't disable quotas** unless necessary (prevents runaway processing)
2. **Monitor quota hits** - if frequently hitting quota, consider increasing limit
3. **Align with cadences** - daily quotas should match source update frequency
4. **Review `items_remaining`** - large values indicate quota may be too low

**Special Cases:**

- **Wikipedia**: No quota (file-based, efficient download)
- **TikTok**: Manual scheduling only (no automatic daily runs)
- **Språkbanken**: Static collection (10 corpora/day more than sufficient)

### Programmatic Configuration

```python
from somali_dialect_classifier.config import get_config

config = get_config()

# Check configured cadences
print(f"BBC cadence: {config.orchestration.bbc_cadence} days")
print(f"Wikipedia cadence: {config.orchestration.wikipedia_cadence} days")
print(f"Initial collection: {config.orchestration.initial_collection_days} days")

# Get cadence for specific source
bbc_cadence = config.orchestration.get_cadence("bbc")
print(f"BBC runs every {bbc_cadence} day(s)")

# Check daily quotas (new in Phase C)
print(f"BBC daily quota: {config.orchestration.quota_limits.get('bbc', 0)} articles")
print(f"HuggingFace daily quota: {config.orchestration.quota_limits.get('huggingface', 0)} records")
print(f"Språkbanken daily quota: {config.orchestration.quota_limits.get('sprakbanken', 0)} corpora")

# Access OrchestrationConfig structure
print(f"Initial collection days: {config.orchestration.initial_collection_days}")
print(f"Default cadence: {config.orchestration.default_cadence_days} days")
print(f"Cadence days dict: {config.orchestration.cadence_days}")
print(f"Quota limits dict: {config.orchestration.quota_limits}")
```

## Common Commands

### Production Workflows

#### Daily Automated Run

```bash
# Add to cron: Run daily at 2 AM
# 0 2 * * * cd /path/to/project && somali-orchestrate --pipeline all

# This will automatically:
# - Check each source's cadence
# - Run sources that are due for refresh
# - Skip sources that were recently run
# - Log all activity to logs/orchestrator.log
```

#### Quarterly Refresh

```bash
# Quarterly refresh run (efficient incremental processing)
somali-orchestrate --pipeline all

# Expected behavior:
# - Wikipedia: ~50 new articles (99% skipped)
# - BBC: ~30-90 new articles (90% skipped)
# - TikTok: New comments only
# - Språkbanken: 0 corpora (100% skipped)
# - HuggingFace: Full refresh (static dataset)
```

#### Force Full Re-Processing

```bash
# Force all sources to re-process (ignores incremental filtering)
somali-orchestrate --pipeline all --force

# Use cases:
# - After schema changes
# - After cleaning/text processing updates
# - After deduplication logic changes
# - To recover from corrupted runs
```

### Testing Workflows

#### Smoke Test (Quick Validation)

```bash
# Test all pipelines with small limits
somali-orchestrate --pipeline all \
  --max-bbc-articles 10 \
  --max-hf-records 100

# Validates:
# - All pipelines can start
# - Credentials are configured
# - Ledger is accessible
# - Output directories writable
```

#### Source-Specific Testing

```bash
# Test BBC only
somali-orchestrate --pipeline bbc --max-bbc-articles 50

# Test Wikipedia only
somali-orchestrate --pipeline wikipedia

# Test TikTok only (requires Apify token)
export SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=your_token_here
somali-orchestrate --pipeline tiktok --tiktok-video-urls data/tiktok_urls.txt
```

## Advanced Workflows

### Quarterly Refresh Strategy

**Recommended quarterly workflow for production:**

```bash
#!/bin/bash
# quarterly_refresh.sh

# Step 1: Run orchestrator (incremental processing)
echo "Starting quarterly refresh..."
somali-orchestrate --pipeline all

# Step 2: Run cross-run deduplication
echo "Running cross-run deduplication..."
python scripts/deduplicate_silver.py --output-dir data/silver_deduped

# Step 3: Generate quality report
echo "Generating quality report..."
python scripts/generate_quality_report.py --output reports/quarterly_$(date +%Y%m%d).html

# Step 4: Backup ledger
echo "Backing up ledger..."
cp data/ledger/crawl_ledger.db .backups/ledger_$(date +%Y%m%d).db

echo "Quarterly refresh complete!"
```

**Schedule with cron:**

```bash
# Run quarterly on 1st day of January, April, July, October at 2 AM
0 2 1 1,4,7,10 * /path/to/quarterly_refresh.sh >> /path/to/logs/quarterly.log 2>&1
```

### CI/CD Integration

#### GitHub Actions Workflow

```yaml
# .github/workflows/quarterly-refresh.yml
name: Quarterly Data Refresh

on:
  schedule:
    - cron: '0 2 1 1,4,7,10 *'  # Quarterly on 1st at 2 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -e ".[config]"

      - name: Configure secrets
        env:
          APIFY_TOKEN: ${{ secrets.APIFY_API_TOKEN }}
        run: |
          echo "SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=$APIFY_TOKEN" >> .env

      - name: Run orchestrator
        run: |
          somali-orchestrate --pipeline all

      - name: Upload silver dataset
        uses: actions/upload-artifact@v3
        with:
          name: silver-dataset
          path: data/processed/silver/

      - name: Generate quality report
        run: |
          python scripts/generate_quality_report.py

      - name: Upload quality report
        uses: actions/upload-artifact@v3
        with:
          name: quality-report
          path: reports/*.html
```

#### Docker Orchestration

```yaml
# docker-compose.yml
version: '3.8'

services:
  orchestrator:
    build: .
    environment:
      - SDC_LEDGER_BACKEND=postgres
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=somali_nlp
      - SDC_ORCHESTRATION__BBC_CADENCE=1
      - SDC_ORCHESTRATION__WIKIPEDIA_CADENCE=7
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
    command: somali-orchestrate --pipeline all

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=somali_nlp
      - POSTGRES_USER=somali
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Run with Docker:**

```bash
# Start orchestrator
docker-compose up orchestrator

# Run specific pipeline
docker-compose run orchestrator somali-orchestrate --pipeline bbc --max-bbc-articles 100
```

### Custom Pipelines

**Create custom orchestration logic:**

```python
from somali_dialect_classifier.orchestration.flows import (
    run_wikipedia_task,
    run_bbc_task,
    should_run_source,
    is_initial_collection_phase
)

def custom_orchestration():
    """Custom orchestration logic."""
    # Check if sources should run
    bbc_should_run, bbc_reason = should_run_source("bbc")
    wiki_should_run, wiki_reason = should_run_source("wikipedia")

    print(f"BBC: {bbc_should_run} ({bbc_reason})")
    print(f"Wikipedia: {wiki_should_run} ({wiki_reason})")

    # Run only high-priority sources
    if bbc_should_run:
        result = run_bbc_task(force=False)
        print(f"BBC result: {result}")

    if wiki_should_run:
        result = run_wikipedia_task(force=False)
        print(f"Wikipedia result: {result}")

if __name__ == "__main__":
    custom_orchestration()
```

## Monitoring & Observability

### Metrics Collection

The orchestrator automatically collects metrics for all pipelines:

```json
{
  "source": "Wikipedia-Somali",
  "run_id": "20251111_143045",
  "status": "success",
  "duration_seconds": 180.5,
  "records_processed": 9960,
  "records_filtered": 9910,
  "records_written": 50,
  "efficiency_gain_percent": 99.5,
  "incremental_filtering": {
    "total": 9960,
    "new": 50,
    "skipped": 9910,
    "last_processing_time": "2025-11-10T12:00:00Z"
  },
  "deduplication": {
    "exact_duplicates": 0,
    "near_duplicates": 2,
    "unique_records": 48
  },
  "quality_filters": {
    "min_length_filter": {"passed": 50, "failed": 0},
    "langid_filter": {"passed": 50, "failed": 0},
    "topic_lexicon_enrichment_filter": {"passed": 50, "failed": 0}
  }
}
```

### Quality Reports

Generate unified quality report across all sources:

```bash
# Generate quality report
python scripts/generate_quality_report.py

# Output: reports/quality_report_20251111.html
# Contains:
# - Per-source metrics
# - Quality filter breakdown
# - Deduplication statistics
# - Efficiency gains
# - Processing times
```

### Ledger Tracking

Query ledger for orchestration status:

```python
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()

# Get last successful run for each source
sources = ["bbc", "wikipedia", "tiktok", "sprakbanken", "huggingface"]
for source in sources:
    last_run = ledger.get_last_successful_run(source)
    if last_run:
        print(f"{source}: Last run {last_run}")
    else:
        print(f"{source}: Never run")

# Get statistics for specific source
stats = ledger.get_statistics("Wikipedia-Somali")
print(f"Total URLs: {stats['total']}")
print(f"By state: {stats['by_state']}")
```

### Logging

All orchestration activity is logged to `logs/orchestrator.log`:

```bash
# View orchestrator logs
tail -f logs/orchestrator.log

# Search for specific source
grep "Wikipedia" logs/orchestrator.log

# Check for errors
grep "ERROR" logs/orchestrator.log

# View last 100 lines
tail -n 100 logs/orchestrator.log
```

## Troubleshooting

### Pipeline Skipped (Cadence Not Met)

**Symptom:**
```
[INFO] Skipping BBC: refresh_not_due (next in 0.5 days)
```

**Cause:** Source was recently run, cadence interval not elapsed.

**Solutions:**

1. **Wait for cadence to elapse** (recommended):
   ```bash
   # Check when source will run next
   python -c "
   from somali_dialect_classifier.orchestration.flows import should_run_source
   should_run, reason = should_run_source('bbc')
   print(f'BBC: {should_run} - {reason}')
   "
   ```

2. **Force run** (bypasses cadence check):
   ```bash
   somali-orchestrate --pipeline bbc --force
   ```

3. **Adjust cadence** (for testing):
   ```bash
   export SDC_ORCHESTRATION__BBC_CADENCE=0  # Run every time
   somali-orchestrate --pipeline bbc
   ```

### Duplicate Detection Issues

**Symptom:**
```
[WARNING] Duplicate URL detected: https://so.wikipedia.org/wiki/Example
[INFO] Skipping duplicate article
```

**Cause:** URL already processed in previous run (discovery-stage dedup working correctly).

**Solutions:**

1. **This is expected behavior** - duplicate detection prevents redundant processing
2. **Force re-processing** if needed:
   ```bash
   somali-orchestrate --pipeline wikipedia --force
   ```

3. **Clear ledger entry** (use with caution):
   ```python
   from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger
   ledger = get_ledger()
   # Manual SQL: DELETE FROM crawl_ledger WHERE url = 'specific_url'
   ```

### Out of Memory Errors

**Symptom:**
```
[ERROR] MemoryError: Unable to allocate array
```

**Cause:** Processing large datasets without batching.

**Solutions:**

1. **Use batching** (automatic in BasePipeline):
   ```python
   processor = WikipediaSomaliProcessor()
   processor.batch_size = 1000  # Process 1000 records at a time
   processor.run()
   ```

2. **Reduce concurrency**:
   ```bash
   # Process sources sequentially
   somali-orchestrate --pipeline wikipedia  # Run one at a time
   ```

3. **Increase system memory** or use machine with more RAM

4. **Process in smaller chunks**:
   ```bash
   # BBC: Process 100 articles at a time
   somali-orchestrate --pipeline bbc --max-bbc-articles 100

   # HuggingFace: Process 10k records at a time
   somali-orchestrate --pipeline huggingface --max-hf-records 10000
   ```

### Concurrent Run Detected

**Symptom:**
```
[WARNING] Wikipedia pipeline already running, skipping
[INFO] Status: skipped, Reason: concurrent_run_active
```

**Cause:** Distributed lock detected another orchestrator running the same source.

**Solutions:**

1. **Wait for current run to complete** (recommended):
   ```bash
   # Check if lock is still active
   python -c "
   from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger
   ledger = get_ledger()
   if ledger.is_source_locked('wikipedia'):
       print('Lock active')
   else:
       print('Lock released')
   "
   ```

2. **Force release lock** (if run crashed and lock is stale):
   ```python
   from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger
   ledger = get_ledger()
   ledger.release_source_lock("wikipedia")
   print("Lock released")
   ```

3. **Check for zombie processes**:
   ```bash
   ps aux | grep somali-orchestrate
   # Kill if necessary
   ```

## Best Practices

### 1. Monitor Initial Collection Phase

During the first 6 days, monitor to ensure all sources complete successfully:

```bash
# Check orchestrator logs daily
tail -n 100 logs/orchestrator.log | grep "status"

# Verify all sources have run
python -c "
from somali_dialect_classifier.orchestration.flows import is_initial_collection_phase
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()
sources = ['bbc', 'wikipedia', 'tiktok', 'sprakbanken', 'huggingface']

for source in sources:
    last_run = ledger.get_last_successful_run(source)
    print(f'{source}: {last_run}')

print(f'\\nIn initial collection: {is_initial_collection_phase()}')
"
```

### 2. Backup Ledger Regularly

The ledger tracks all processing history. Back it up regularly:

```bash
# Daily backup (add to cron)
cp data/ledger/crawl_ledger.db .backups/ledger_$(date +%Y%m%d).db

# Keep last 30 days
find .backups/ -name "ledger_*.db" -mtime +30 -delete
```

### 3. Use Force Sparingly

`--force` bypasses incremental filtering and re-processes all data. Only use when necessary:

- After schema changes
- After cleaning/text processing updates
- After deduplication logic changes
- To recover from corrupted runs

**Do not use for regular quarterly refreshes** (defeats incremental processing efficiency).

### 4. Set Appropriate Cadences

Configure cadences based on source update frequency:

- **High-frequency sources** (BBC, TikTok): 1-3 days
- **Medium-frequency sources** (Wikipedia): 7 days
- **Low-frequency sources** (Språkbanken, HuggingFace): 30 days

### 5. Monitor Quality Metrics

Review quality metrics after each run:

```bash
# Generate and review quality report
python scripts/generate_quality_report.py
open reports/quality_report_$(date +%Y%m%d).html
```

Look for:
- Unexpected drops in record counts
- High filter failure rates
- Duplicate detection anomalies

## References

### Related Documentation

- [Incremental Processing Guide](incremental-processing.md) - Efficient quarterly refreshes
- [Deduplication Guide](deduplication.md) - Three-tier deduplication strategy
- [Configuration Guide](configuration.md) - Environment variables and settings
- [Processing Pipelines Guide](processing-pipelines.md) - Individual pipeline documentation
- [PostgreSQL Deployment](../operations/postgres-deployment.md) - Production database setup
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions

### Source-Specific Guides

- [Wikipedia Integration](wikipedia-integration.md)
- [BBC Integration](bbc-integration.md)
- [HuggingFace Integration](huggingface-integration.md)
- [Språkbanken Integration](sprakbanken-integration.md)
- [TikTok Integration](tiktok-integration.md)

### API References

- [API Reference](../reference/api.md) - Complete API documentation
- [Metrics Schema](../reference/metrics-schema.md) - Metrics specification
- [Silver Schema](../reference/silver-schema.md) - Output dataset schema

---

**Version**: 1.0
**Last Updated**: 2025-11-11
**Maintainer**: DevOps Infrastructure Team
