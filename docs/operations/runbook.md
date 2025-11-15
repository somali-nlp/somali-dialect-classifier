# Operational Runbook - Somali NLP Data Pipeline

**Version:** 1.0
**Last Updated:** 2025-11-15
**Status:** Production Ready

## Table of Contents

- [Overview](#overview)
- [Recovery Procedures](#recovery-procedures)
- [Source-Specific Operations](#source-specific-operations)
- [Common Error Scenarios](#common-error-scenarios)
- [Escalation](#escalation)

---

## Overview

This runbook provides operational procedures for the Somali NLP data ingestion pipeline. The system runs on a 7-day initial collection phase, followed by source-specific refresh cadences.

### System Architecture

- **Ledger Backend:** SQLite (data/ledger/crawl_ledger.db)
- **Data Layers:** Raw → Staging → Silver (Parquet)
- **Orchestration:** Cadence-based with quota enforcement
- **Monitoring:** Metrics + Dashboard

### Key Metrics

- **Current Ledger:** ~10MB, 15,508 URLs (9,961 processed)
- **Test Pass Rate:** 73.9% (487/671 tests)
- **Sources:** Wikipedia, BBC Somali, HuggingFace, Språkbanken, TikTok

---

## Recovery Procedures

### Scenario 1: Pipeline Failed Mid-Execution

**Symptoms:**
- Run appears stuck or incomplete
- Logs show errors mid-processing
- Partial data in staging but not in silver

**Recovery Steps:**

1. **Check logs for error details:**
   ```bash
   tail -100 logs/pipeline.log
   # or
   ls -lt logs/ | head -10  # Find most recent log
   cat logs/<latest_log_file>
   ```

2. **Identify failure point:**
   - Download failure: Check network/API errors
   - Processing failure: Check filter/transformation errors
   - Silver write failure: Check disk space/permissions

3. **Rerun with --force flag:**
   ```bash
   python -m somali_dialect_classifier.pipeline.run \
       --source <source_name> \
       --force
   ```

4. **If staging data exists, skip download:**
   ```bash
   python -m somali_dialect_classifier.pipeline.run \
       --source <source_name> \
       --skip-download \
       --force
   ```

5. **Verify success:**
   ```bash
   # Check silver output
   ls -lh data/processed/silver/source=<Source>/

   # Check metrics
   ls -lt data/metrics/ | head -5
   ```

**Implications:**
- Deduplication still applies (won't create duplicates)
- Ledger tracks new pipeline run
- Previous partial run remains in ledger for audit

---

### Scenario 2: Pipeline Stuck (Locks Not Cleared)

**Symptoms:**
- Pipeline won't start for a source
- Error: "Cannot acquire lock"
- Lock files exist in `.locks/` directory

**Recovery Steps:**

1. **Check for stuck locks:**
   ```bash
   ls -lh .locks/
   ```

2. **Verify no pipeline actually running:**
   ```bash
   ps aux | grep "somali_dialect_classifier"
   # Check for any running Python processes
   ```

3. **Clear locks manually (ONLY if pipeline definitely not running):**
   ```bash
   rm .locks/<source>.lock
   # Example: rm .locks/wikipedia.lock
   ```

4. **Or use ledger cleanup:**
   ```bash
   python3 << 'EOF'
   from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger
   from pathlib import Path

   ledger = CrawlLedger(db_path=Path('data/ledger/crawl_ledger.db'))
   ledger.cleanup_stale_locks(max_age_hours=1)
   print("Stale locks cleaned")
   EOF
   ```

5. **Retry pipeline:**
   ```bash
   python -m somali_dialect_classifier.pipeline.run --source <source>
   ```

**Warning:** Never delete locks if a pipeline is actually running!

---

### Scenario 3: Quota Exceeded

**Symptoms:**
- Pipeline stops early
- Metrics show quota_hit=true
- Logs mention quota limit reached

**Diagnosis:**

```bash
# Check today's quota usage
python3 << 'EOF'
from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger
from pathlib import Path

ledger = CrawlLedger(db_path=Path('data/ledger/crawl_ledger.db'))
for source in ['bbc-somali', 'huggingface', 'sprakbanken']:
    usage = ledger.get_daily_quota_usage(source)
    print(f"{source}: {usage}")
EOF
```

**Resolution:**

**Option A:** Wait for quota reset (midnight UTC)

**Option B:** Adjust quota limits (if justified):
```bash
# Edit .env
SDC_ORCHESTRATION__QUOTA_LIMITS__BBC=500  # Increase from 350

# Restart pipeline
python -m somali_dialect_classifier.pipeline.run --source bbc-somali
```

**Option C:** Force run without quota (emergency only):
```bash
# WARNING: This bypasses quota enforcement
# Use only for urgent catchup
python -m somali_dialect_classifier.pipeline.run \
    --source bbc-somali \
    --ignore-quota \
    --force
```

---

### Scenario 4: Deduplication Issues

**Symptoms:**
- Same content appearing multiple times
- Unexpectedly low deduplication rate
- Duplicate text_hash values

**Diagnosis:**

```bash
# Check deduplication stats
sqlite3 data/ledger/crawl_ledger.db << 'EOF'
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT text_hash) as unique_hashes,
    COUNT(*) - COUNT(DISTINCT text_hash) as duplicates
FROM crawl_ledger
WHERE state='processed' AND text_hash IS NOT NULL;
EOF
```

**Resolution:**

1. **If low dedup rate (<1%):** Normal for diverse sources
2. **If high dedup rate (>50%):** Possible configuration issue
3. **If duplicate text_hashes in silver:** Bug - needs investigation

```bash
# Force reprocessing with fresh hash computation
python -m somali_dialect_classifier.pipeline.run \
    --source <source> \
    --recompute-hashes \
    --force
```

---

## Source-Specific Operations

### Wikipedia

**Cadence:** 7 days
**Type:** File-based (dump download)
**Quota:** Unlimited

**Rerun:**
```bash
python -m somali_dialect_classifier.pipeline.run \
    --source wikipedia \
    --force
```

**Common Issues:**
- **Dump download timeout:** Increase timeout in config
- **Parsing errors:** Check Wikipedia dump format changes
- **Low yield:** Normal - many articles are redirects/stubs

**Expected Output:**
- ~9,960 articles per full dump
- Deduplication rate: ~0.6%
- License: CC-BY-SA-3.0

---

### BBC Somali

**Cadence:** 7 days
**Type:** Web scraping (RSS + HTML)
**Quota:** 350 articles/day

**Rerun:**
```bash
python -m somali_dialect_classifier.pipeline.run \
    --source bbc-somali \
    --force
```

**Common Issues:**
- **Rate limiting:** Respect 3-6 second delays (configured)
- **Quota hit:** Expected after 350 articles
- **HTML changes:** May require processor updates

**Expected Output:**
- ~350 articles/day (quota-limited)
- Deduplication rate: <5%
- License: Custom (research use only)

**Ethical Considerations:**
- Always respect robots.txt
- Never exceed 350 articles/day
- Monitor for IP blocking

---

### HuggingFace (MC4 Somali)

**Cadence:** 30 days
**Type:** Dataset streaming
**Quota:** 10,000 records/day

**Rerun:**
```bash
python -m somali_dialect_classifier.pipeline.run \
    --source huggingface \
    --force
```

**Common Issues:**
- **API rate limits:** Built-in backoff handles this
- **Dataset version changes:** Pin revision in config
- **Large dataset:** Will take hours for full run

**Expected Output:**
- 10,000 records/day (quota-limited)
- Variable quality (filters applied)
- License: Per-dataset (check HF page)

---

### Språkbanken

**Cadence:** 90 days
**Type:** Corpus download
**Quota:** 10 corpora/day

**Rerun:**
```bash
python -m somali_dialect_classifier.pipeline.run \
    --source sprakbanken \
    --force
```

**Common Issues:**
- **Slow downloads:** Normal for academic corpus
- **Format variations:** 23 different corpora types

**Expected Output:**
- 10 corpora/day (quota-limited)
- License: CC-BY-4.0 (verify per corpus)

---

### TikTok (Apify)

**Cadence:** 7 days
**Type:** Apify actor (manual)
**Quota:** Manual cost gating

**Rerun:**
```bash
# Requires APIFY_API_TOKEN in .env
python -m somali_dialect_classifier.pipeline.run \
    --source tiktok \
    --force
```

**Common Issues:**
- **Cost overruns:** Monitor Apify dashboard
- **API token expired:** Rotate token
- **Actor changes:** May require processor updates

**Cost Considerations:**
- ~$2-5 per 1000 comments
- Target: 30,000 comments total
- Manual approval required for runs

---

## Common Error Scenarios

### Error: "No module named 'somali_dialect_classifier'"

**Cause:** Virtual environment not activated or package not installed

**Solution:**
```bash
source venv/bin/activate  # Activate venv
pip install -e .  # Install package in editable mode
```

---

### Error: "Database locked"

**Cause:** Multiple processes accessing SQLite simultaneously

**Solution:**
- Only one pipeline per source at a time
- FileLock should prevent this
- If it occurs, check for stale locks (see Scenario 2)

---

### Error: "Schema validation failed"

**Cause:** Silver record doesn't match expected schema

**Solution:**
1. Check silver schema: `docs/reference/silver-schema.md`
2. Review processor output for missing/invalid fields
3. Check schema version compatibility

```bash
# Validate metrics against schema
python scripts/validate_metrics_phase3.py data/metrics/<file>.json
```

---

### Error: "Permission denied" (file write)

**Cause:** Insufficient permissions on data directory

**Solution:**
```bash
# Fix permissions
chmod -R u+w data/

# Or run with appropriate user
sudo -u <user> python -m somali_dialect_classifier.pipeline.run ...
```

---

### Error: "Disk space full"

**Cause:** Insufficient disk space for data

**Diagnosis:**
```bash
df -h  # Check disk usage
du -sh data/*  # Check data directory sizes
```

**Solution:**
1. Clean up old raw files:
   ```bash
   find data/raw -type f -mtime +30 -delete  # Delete >30 days old
   ```

2. Archive to external storage:
   ```bash
   tar -czf backup-$(date +%Y%m%d).tar.gz data/silver/
   mv backup-*.tar.gz /external/storage/
   ```

3. Adjust retention policy in config

---

## Maintenance Operations

### Clean Ledger (Remove Old Failed Entries)

```bash
python3 << 'EOF'
from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger
from pathlib import Path

ledger = CrawlLedger(db_path=Path('data/ledger/crawl_ledger.db'))
removed = ledger.cleanup(days=30)
print(f"Removed {removed} old failed entries")
EOF
```

### Backup System

```bash
# Full system backup
tar -czf backup-full-$(date +%Y%m%d).tar.gz \
    data/ledger/ \
    data/processed/silver/ \
    data/metrics/ \
    .env

# Restore from backup
tar -xzf backup-full-YYYYMMDD.tar.gz
```

### View Ledger Statistics

```bash
sqlite3 data/ledger/crawl_ledger.db << 'EOF'
.mode column
.headers on

-- URLs by source and state
SELECT source, state, COUNT(*) as count
FROM crawl_ledger
GROUP BY source, state
ORDER BY source, state;

-- Recent pipeline runs
SELECT run_id, source, status, records_processed, datetime(start_time)
FROM pipeline_runs
ORDER BY start_time DESC
LIMIT 10;

-- Daily quota usage
SELECT date, source, records_ingested, quota_limit
FROM daily_quotas
ORDER BY date DESC, source
LIMIT 20;
EOF
```

---

## Escalation

### Technical Issues

- **GitHub Issues:** Report bugs/feature requests
- **Contact:** (define technical contact)
- **Emergency:** (define emergency contact)

### Data Quality Issues

- **PII Detected:** Immediately halt source, review, implement redaction
- **License Violations:** Remove affected data, document incident
- **Extreme Bias:** Flag for review, adjust filters if needed

### Production Outages

1. **Check system status:**
   - Ledger accessible?
   - Disk space available?
   - Network connectivity?

2. **Review recent changes:**
   - Recent code deployments?
   - Configuration changes?
   - Infrastructure changes?

3. **Implement workaround:**
   - Switch to backup source if available
   - Reduce quotas to conserve resources
   - Disable problematic source temporarily

4. **Document incident:**
   - Time of incident
   - Root cause
   - Resolution steps
   - Prevention measures

---

## Appendix: Quick Reference

### Essential Commands

```bash
# Run all sources (respects cadences)
python -m somali_dialect_classifier.orchestration.main

# Run single source
python -m somali_dialect_classifier.orchestration.main --source wikipedia

# Force run (ignore cadence)
python -m somali_dialect_classifier.orchestration.main --source wikipedia --force

# Check ledger stats
sqlite3 data/ledger/crawl_ledger.db "SELECT source, COUNT(*) FROM crawl_ledger GROUP BY source;"

# Check quota usage
sqlite3 data/ledger/crawl_ledger.db "SELECT * FROM daily_quotas ORDER BY date DESC LIMIT 10;"

# View recent runs
sqlite3 data/ledger/crawl_ledger.db "SELECT * FROM pipeline_runs ORDER BY start_time DESC LIMIT 5;"
```

### Configuration Files

- **Main Config:** `.env`
- **Schema:** `docs/reference/silver-schema.md`
- **Filters:** `docs/architecture/filter-alignment.md`

### Log Locations

- **Pipeline Logs:** `logs/`
- **Metrics:** `data/metrics/`
- **Ledger:** `data/ledger/crawl_ledger.db`

---

**End of Runbook**
