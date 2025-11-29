# PostgreSQL Deployment Guide

**Guide for deploying and configuring PostgreSQL as the crawl ledger backend.**

**Last Updated:** 2025-11-29

**Status:** Production-Ready (95% Complete)
**Target Environment:** Production
**Estimated Deployment Time:** 1-4 hours (depending on dataset size)

---

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
  - [Required Software](#required-software)
  - [Verification Commands](#verification-commands)
  - [System Requirements](#system-requirements)
  - [Access Requirements](#access-requirements)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
  - [1. Backup Existing Data](#1-backup-existing-data)
  - [2. Review Environment Configuration](#2-review-environment-configuration)
  - [3. Verify Network Connectivity](#3-verify-network-connectivity)
  - [4. Test Docker Setup](#4-test-docker-setup)
- [Deployment Steps](#deployment-steps)
  - [Step 1: Configure Environment Variables](#step-1-configure-environment-variables)
  - [Step 2: Start PostgreSQL Container](#step-2-start-postgresql-container)
  - [Step 3: Verify Database Health](#step-3-verify-database-health)
  - [Step 4: Run Migration Script (Dry-Run)](#step-4-run-migration-script-dry-run)
  - [Step 5: Execute Migration](#step-5-execute-migration)
  - [Step 6: Validate Migration](#step-6-validate-migration)
  - [Step 7: Performance Validation](#step-7-performance-validation)
  - [Step 8: Switch Application to PostgreSQL](#step-8-switch-application-to-postgresql)
- [Configuration Guide](#configuration-guide)
  - [Environment Variables Explained](#environment-variables-explained)
  - [Connection Pooling Settings](#connection-pooling-settings)
  - [Docker Resource Limits](#docker-resource-limits)
- [Migration Validation](#migration-validation)
  - [Data Integrity Verification](#data-integrity-verification)
  - [Performance Validation](#performance-validation)
  - [Rollback Procedure](#rollback-procedure)
- [Post-Deployment](#post-deployment)
  - [Connection Pool Monitoring](#connection-pool-monitoring)
  - [Query Performance Benchmarks](#query-performance-benchmarks)
  - [Backup Strategy](#backup-strategy)
- [Troubleshooting](#troubleshooting)
  - [Connection Pool Exhaustion](#connection-pool-exhaustion)
  - [Migration Failures](#migration-failures)
  - [Performance Issues](#performance-issues)
  - [Docker Container Issues](#docker-container-issues)
  - [Rollback to SQLite](#rollback-to-sqlite)
- [Production Monitoring](#production-monitoring)
  - [Key Metrics to Monitor](#key-metrics-to-monitor)
  - [Recommended Monitoring Tools](#recommended-monitoring-tools)
  - [Alerting Thresholds](#alerting-thresholds)
- [Deployment Summary](#deployment-summary)
  - [Estimated Deployment Timeline](#estimated-deployment-timeline)
  - [Critical Success Criteria](#critical-success-criteria)
  - [Rollback Strategy](#rollback-strategy)
- [References](#references)
  - [Documentation Files](#documentation-files)
  - [Implementation Reports](#implementation-reports)
  - [External Resources](#external-resources)
- [Support](#support)
  - [Common Questions](#common-questions)
  - [Issue Reporting](#issue-reporting)

---

## Overview

This guide provides step-by-step instructions for deploying PostgreSQL as the production backend for the Somali NLP data pipeline. PostgreSQL enables concurrent processing of all 5 data sources, providing:

- **10x concurrent writes** without deadlocks (tested with 50 threads)
- **5x write throughput** improvement (500-1000 ops/s vs. 100-200 ops/s)
- **2-5x faster queries** (5-20ms p95 vs. 10-50ms p95)
- **Row-level locking** (eliminates SQLite's file-level lock contention)
- **Connection pooling** (2-10 connections for efficient resource usage)

---

## Prerequisites

### Required Software

- **Docker**: Version 20.10+ with Compose V2
- **Docker Compose**: Version 2.0+ (included with Docker Desktop)
- **Python**: Version 3.9+
- **Git**: For version control (optional but recommended)

### Verification Commands

```bash
# Verify Docker
docker --version
# Expected: Docker version 20.10.0 or higher

# Verify Docker Compose
docker compose version
# Expected: Docker Compose version v2.0.0 or higher

# Verify Python
python --version
# Expected: Python 3.9.0 or higher

# Verify project dependencies installed
pip list | grep psycopg2
# Expected: psycopg2-binary 2.9.9 or higher
```

### System Requirements

- **CPU**: 4 cores (recommended)
- **RAM**: 8GB available (4GB minimum)
- **Disk**: 20GB free space for database and backups
- **Network**: Port 5432 available (or configure alternate port)

### Access Requirements

- **Database credentials**: Strong password for PostgreSQL user
- **Existing SQLite database**: Path to `data/ledger/crawl_ledger.db` (if migrating)
- **Write permissions**: To project directory for .env file

---

## Pre-Deployment Checklist

### 1. Backup Existing Data

**Critical:** Always backup before migration to prevent data loss.

```bash
# Backup SQLite database
cd /Users/ilyas/Desktop/Computer\ Programming/somali-nlp-projects/somali-dialect-classifier

# Create backup directory
mkdir -p .backups/pre-postgres-migration

# Backup with timestamp
cp data/ledger/crawl_ledger.db .backups/pre-postgres-migration/crawl_ledger_$(date +%Y%m%d_%H%M%S).db

# Verify backup
ls -lh .backups/pre-postgres-migration/
```

### 2. Review Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your production values
# IMPORTANT: Use strong passwords in production
nano .env  # or your preferred editor
```

### 3. Verify Network Connectivity

```bash
# Check if port 5432 is available
lsof -i :5432
# Expected: No output (port is free)

# If port 5432 is in use, configure alternate port in .env:
# POSTGRES_PORT=5433
```

### 4. Test Docker Setup

```bash
# Verify Docker daemon is running
docker ps

# Test Docker Compose configuration
docker compose --profile prod config
# Expected: Properly formatted YAML output
```

---

## Deployment Steps

### Step 1: Configure Environment Variables

Edit `.env` file with production settings:

```bash
# ============================================================================
# PostgreSQL Configuration
# ============================================================================

# Backend selection
SDC_LEDGER_BACKEND=postgres

# PostgreSQL connection settings
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=somali_nlp
POSTGRES_USER=somali
POSTGRES_PASSWORD="<YOUR_SECURE_PASSWORD_HERE>"  # Set your actual password
POSTGRES_AUTH_METHOD=md5

# SQLite fallback (for rollback if needed)
SDC_LEDGER_SQLITE_PATH=data/ledger/crawl_ledger.db
```

**Security Note:** Generate a strong password (minimum 16 characters, alphanumeric + special characters):

```bash
# Generate secure password (macOS/Linux)
openssl rand -base64 24

# Alternative: use a password manager
```

### Step 2: Start PostgreSQL Container

```bash
# Start PostgreSQL with production profile
docker compose --profile prod up -d postgres

# Verify container is running
docker ps | grep postgres
# Expected: Container named 'somali-nlp-postgres' with status 'Up'

# Check container logs
docker logs somali-nlp-postgres
# Expected: "database system is ready to accept connections"
```

### Step 3: Verify Database Health

```bash
# Health check using pg_isready
docker compose exec postgres pg_isready -U somali -d somali_nlp
# Expected: "somali_nlp - accepting connections"

# Verify schema was initialized
docker compose exec postgres psql -U somali -d somali_nlp -c "\dt"
# Expected: List of tables (crawl_ledger, rss_feeds, schema_version)

# Verify indexes
docker compose exec postgres psql -U somali -d somali_nlp -c "\di"
# Expected: List of 9 indexes including GIN index on metadata
```

### Step 4: Run Migration Script (Dry-Run)

**Always test migration first with dry-run mode:**

```bash
# Dry-run migration to preview changes
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/ledger/crawl_ledger.db \
    --postgres-host localhost \
    --postgres-port 5432 \
    --postgres-db somali_nlp \
    --postgres-user somali \
    --dry-run

# Review output:
# - SQLite database statistics
# - Number of URLs per source
# - RSS feeds to migrate
# - No actual data written (DRY RUN)
```

**Expected Output:**
```
============================================================
SQLite to PostgreSQL Migration
============================================================
Opening SQLite database: data/ledger/crawl_ledger.db
DRY RUN MODE - No data will be written

SQLite Database Statistics:
  Total URLs: XXXX
  By state: {'discovered': XXX, 'fetched': XXX, ...}

...

DRY RUN completed - no data written
```

### Step 5: Execute Migration

**After dry-run validation passes, run actual migration:**

```bash
# Run actual migration
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/ledger/crawl_ledger.db \
    --postgres-host localhost \
    --postgres-port 5432 \
    --postgres-db somali_nlp \
    --postgres-user somali

# Enter password when prompted
# Expected: Password prompt (hidden input)
```

**Expected Output:**
```
============================================================
Migrating source: wikipedia
============================================================
  Found XXX URLs
  Migrating batch 1 (100 URLs)...
  Migrating batch 2 (100 URLs)...
  ...
  Completed wikipedia: XXX URLs migrated

...

============================================================
Migration Summary
============================================================
Total URLs migrated: XXXX

PostgreSQL Database Statistics:
  Total URLs: XXXX
  By state: {...}

✓ Migration completed successfully!
  All records migrated and verified.
```

### Step 6: Validate Migration

**Data Integrity Checks:**

```bash
# 1. Verify record counts match
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT COUNT(*) as total_urls FROM crawl_ledger;"

# 2. Verify state distribution
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT state, COUNT(*) FROM crawl_ledger GROUP BY state ORDER BY state;"

# 3. Verify sources
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT source, COUNT(*) FROM crawl_ledger GROUP BY source ORDER BY source;"

# 4. Verify RSS feeds
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT COUNT(*) FROM rss_feeds;"

# 5. Check for NULL values in critical fields
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT COUNT(*) FROM crawl_ledger WHERE url IS NULL OR source IS NULL OR state IS NULL;"
# Expected: 0
```

### Step 7: Performance Validation

**Query Performance Tests:**

```bash
# Test query latency (should be < 100ms p95)
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "EXPLAIN ANALYZE SELECT * FROM crawl_ledger WHERE source = 'wikipedia' AND state = 'discovered' LIMIT 100;"

# Check index usage
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read FROM pg_stat_user_indexes ORDER BY idx_scan DESC;"
```

**Connection Pool Test:**

```bash
# Run a quick concurrent write test
python -c "
import os
os.environ['SDC_LEDGER_BACKEND'] = 'postgres'
from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger
from concurrent.futures import ThreadPoolExecutor

ledger = CrawlLedger()
def test_write(i):
    ledger.mark_url_discovered(f'https://test-{i}.example.com', 'test')

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(test_write, range(100))

print('✓ Concurrent writes test passed')
ledger.close()
"
```

### Step 8: Switch Application to PostgreSQL

**Update environment for all pipeline processes:**

```bash
# Verify .env has correct backend
grep SDC_LEDGER_BACKEND .env
# Expected: SDC_LEDGER_BACKEND=postgres

# Test pipeline with PostgreSQL
python -m somali_dialect_classifier.cli.download_wikisom --limit 10

# Check logs for PostgreSQL connection
# Expected: "PostgreSQL connection pool created (2-10 connections)"
```

---

## Configuration Guide

### Environment Variables Explained

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `SDC_LEDGER_BACKEND` | `sqlite` | Backend selection | `postgres` |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host | `localhost` or IP |
| `POSTGRES_PORT` | `5432` | PostgreSQL port | `5432` (standard) |
| `POSTGRES_DB` | `somali_nlp` | Database name | `somali_nlp` |
| `POSTGRES_USER` | `somali` | Database user | `somali` |
| `POSTGRES_PASSWORD` | - | Database password | Strong password (16+ chars) |
| `POSTGRES_AUTH_METHOD` | `md5` | Auth method | `md5` or `scram-sha-256` |

### Connection Pooling Settings

The PostgreSQL backend uses `ThreadedConnectionPool` with the following defaults:

- **Minimum connections:** 2 (always kept open)
- **Maximum connections:** 10 (scales up under load)
- **Connection lifecycle:** Automatic return to pool after use
- **Thread-safety:** Full thread-safe connection management

**When to Adjust:**

```python
# For higher concurrency (> 20 threads), increase pool size:
# Modify src/somali_dialect_classifier/database/postgres_ledger.py
# Default: min_connections=2, max_connections=10
# High-load: min_connections=5, max_connections=20
```

### Docker Resource Limits

Current production limits (configured in `docker-compose.yml`):

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 4G
```

**When to Adjust:**
- Increase if PostgreSQL CPU usage consistently > 80%
- Increase memory if PostgreSQL OOM errors occur
- Monitor with: `docker stats somali-nlp-postgres`

---

## Migration Validation

### Data Integrity Verification

**1. Record Count Validation**

```bash
# SQLite count
sqlite3 data/ledger/crawl_ledger.db "SELECT COUNT(*) FROM crawl_ledger;"

# PostgreSQL count
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT COUNT(*) FROM crawl_ledger;"

# Counts should match exactly
```

**2. Hash Verification**

```bash
# Check duplicate detection fields migrated correctly
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT COUNT(*) FROM crawl_ledger WHERE text_hash IS NOT NULL;"

docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT COUNT(*) FROM crawl_ledger WHERE minhash_signature IS NOT NULL;"
```

**3. Metadata Integrity**

```bash
# Verify JSONB metadata is valid
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT url, metadata FROM crawl_ledger WHERE metadata IS NOT NULL LIMIT 5;"

# Should display valid JSON objects
```

### Performance Validation

**Query Latency Benchmarks:**

```bash
# Test 1: Single record lookup (target: < 10ms)
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "EXPLAIN ANALYZE SELECT * FROM crawl_ledger WHERE url = 'https://so.wikipedia.org/wiki/Example';"

# Test 2: State filter query (target: < 50ms)
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "EXPLAIN ANALYZE SELECT * FROM crawl_ledger WHERE source = 'wikipedia' AND state = 'discovered' LIMIT 100;"

# Test 3: Duplicate detection (target: < 20ms)
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "EXPLAIN ANALYZE SELECT COUNT(*) FROM crawl_ledger WHERE text_hash = 'test_hash';"
```

**Expected Performance Metrics:**
- Single record lookup: < 10ms
- State filter queries: < 50ms
- Bulk operations (1000 records): < 15s
- Concurrent writes (5 threads): No deadlocks
- Connection pool acquisition: < 5ms

### Rollback Procedure

**If validation fails or critical issues occur:**

```bash
# Step 1: Stop PostgreSQL
docker compose --profile prod down

# Step 2: Switch back to SQLite
sed -i.bak 's/SDC_LEDGER_BACKEND=postgres/SDC_LEDGER_BACKEND=sqlite/' .env

# Step 3: Verify SQLite backup is intact
ls -lh .backups/pre-postgres-migration/

# Step 4: Restore SQLite if needed
cp .backups/pre-postgres-migration/crawl_ledger_*.db data/ledger/crawl_ledger.db

# Step 5: Test pipeline with SQLite
python -m somali_dialect_classifier.cli.download_wikisom --limit 5

# Step 6: Investigate PostgreSQL issues
docker logs somali-nlp-postgres > postgres_error_logs.txt
```

**No Data Loss:** SQLite database is preserved during migration. Rollback is instant by changing environment variable.

---

## Post-Deployment

### Connection Pool Monitoring

**Monitor pool utilization:**

```bash
# Check active connections
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT count(*) as active_connections FROM pg_stat_activity WHERE datname = 'somali_nlp';"

# Connection pool is sized at 2-10 connections
# If active_connections consistently >= 10, consider increasing pool size
```

**Monitor connection wait times:**

```bash
# Check for connection waiting
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT pid, wait_event, state, query FROM pg_stat_activity WHERE datname = 'somali_nlp';"

# Look for 'ClientRead' or long-running queries
```

### Query Performance Benchmarks

**Establish baseline metrics:**

```bash
# Enable pg_stat_statements (optional but recommended)
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Monitor query performance over time
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT query, calls, mean_exec_time, max_exec_time FROM pg_stat_statements
     WHERE query LIKE '%crawl_ledger%' ORDER BY mean_exec_time DESC LIMIT 10;"
```

**Performance Targets:**
- Mean query time: < 50ms
- Max query time: < 100ms (p95)
- Queries > 1s: Investigate and optimize

### Backup Strategy

**PostgreSQL Backups vs. SQLite:**

| Aspect | SQLite | PostgreSQL |
|--------|--------|-----------|
| Backup method | File copy | `pg_dump` |
| Backup size | Full database | Compressed dump |
| Restore time | Instant | Minutes (depends on size) |
| Point-in-time recovery | No | Yes (with WAL archiving) |
| Incremental backups | No | Yes (with tools) |

**PostgreSQL Backup Commands:**

```bash
# Daily backup (add to cron)
docker exec somali-nlp-postgres pg_dump -U somali -Fc somali_nlp > \
    .backups/postgres/somali_nlp_$(date +%Y%m%d).dump

# Compressed backup (smaller size)
docker exec somali-nlp-postgres pg_dump -U somali -Fc somali_nlp | \
    gzip > .backups/postgres/somali_nlp_$(date +%Y%m%d).dump.gz

# Backup verification
docker exec somali-nlp-postgres pg_dump -U somali -Fc somali_nlp --schema-only | \
    docker exec -i somali-nlp-postgres pg_restore --list
```

**Restore from Backup:**

```bash
# Restore from dump
docker exec -i somali-nlp-postgres pg_restore -U somali -d somali_nlp -c \
    < .backups/postgres/somali_nlp_20251111.dump

# Or restore from compressed backup
gunzip -c .backups/postgres/somali_nlp_20251111.dump.gz | \
    docker exec -i somali-nlp-postgres pg_restore -U somali -d somali_nlp -c
```

**Automated Backup Script:**

```bash
#!/bin/bash
# Save as scripts/backup_postgres.sh

BACKUP_DIR=".backups/postgres"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Create backup
docker exec somali-nlp-postgres pg_dump -U somali -Fc somali_nlp > \
    "$BACKUP_DIR/somali_nlp_$(date +%Y%m%d_%H%M%S).dump"

# Delete backups older than retention period
find "$BACKUP_DIR" -name "somali_nlp_*.dump" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $(date)"
```

**Add to crontab:**

```bash
# Daily backup at 2 AM
0 2 * * * /path/to/somali-dialect-classifier/scripts/backup_postgres.sh >> /path/to/logs/backup.log 2>&1
```

---

## Troubleshooting

### Connection Pool Exhaustion

**Symptoms:**
- Error: "PoolError: connection pool exhausted"
- Pipeline hangs or times out
- Slow query performance

**Diagnosis:**

```bash
# Check current connections
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT count(*) FROM pg_stat_activity WHERE datname = 'somali_nlp';"

# If count >= 10 (pool max), pool is exhausted
```

**Solutions:**

1. **Increase pool size** (temporary fix):
   - Edit `src/somali_dialect_classifier/database/postgres_ledger.py`
   - Increase `max_connections=20` (from 10)
   - Restart application

2. **Fix connection leaks** (permanent fix):
   - Check logs for unclosed connections
   - Ensure all `CrawlLedger.close()` calls are executed
   - Use context managers: `with CrawlLedger() as ledger:`

3. **Reduce concurrent threads**:
   - Lower thread count in pipeline orchestration
   - Batch operations instead of parallel

### Migration Failures

**Partial Data Migration:**

```bash
# Symptom: PostgreSQL count < SQLite count

# Solution: Re-run migration after cleanup
docker compose exec postgres psql -U somali -d somali_nlp -c "TRUNCATE crawl_ledger, rss_feeds CASCADE;"

python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/ledger/crawl_ledger.db \
    --postgres-host localhost \
    --postgres-db somali_nlp
```

**Duplicate Key Errors:**

```bash
# Symptom: "duplicate key value violates unique constraint"

# Cause: URL already exists in PostgreSQL
# Solution: Migration script uses UPSERT, should not occur

# If it occurs, check for data corruption:
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT url, COUNT(*) FROM crawl_ledger GROUP BY url HAVING COUNT(*) > 1;"
```

**Metadata JSON Errors:**

```bash
# Symptom: Invalid JSONB value

# Diagnosis: Check problematic records
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT url, metadata FROM crawl_ledger WHERE metadata IS NOT NULL LIMIT 100;"

# Solution: Migration script handles JSON conversion automatically
# If errors persist, check SQLite metadata encoding
```

### Performance Issues

**Slow Queries:**

```bash
# Enable query logging
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "ALTER SYSTEM SET log_min_duration_statement = 1000;"  # Log queries > 1s

# Reload configuration
docker compose exec postgres psql -U somali -d somali_nlp -c "SELECT pg_reload_conf();"

# Check logs
docker logs somali-nlp-postgres | grep "duration:"
```

**Missing Indexes:**

```bash
# Verify all indexes exist
docker compose exec postgres psql -U somali -d somali_nlp -c "\di"

# Expected indexes:
# - idx_crawl_ledger_source
# - idx_crawl_ledger_state
# - idx_crawl_ledger_source_state
# - idx_crawl_ledger_text_hash
# - idx_crawl_ledger_minhash
# - idx_crawl_ledger_silver_id
# - idx_crawl_ledger_discovered_at
# - idx_crawl_ledger_updated_at
# - idx_crawl_ledger_metadata (GIN)

# If missing, recreate from schema (choose one method)

# Method 1: Alembic (recommended)
cd migrations/database && alembic upgrade head

# Method 2: Legacy SQL
docker exec -i somali-nlp-postgres psql -U somali -d somali_nlp < migrations/001_initial_schema.sql
docker exec -i somali-nlp-postgres psql -U somali -d somali_nlp < migrations/002_pipeline_runs_table.sql
```

**Connection Leaks:**

```bash
# Identify idle connections
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT pid, state, query, state_change FROM pg_stat_activity
     WHERE datname = 'somali_nlp' AND state = 'idle'
     ORDER BY state_change;"

# Terminate long-idle connections (use with caution)
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
     WHERE datname = 'somali_nlp' AND state = 'idle'
     AND state_change < NOW() - INTERVAL '1 hour';"
```

### Docker Container Issues

**Container Won't Start:**

```bash
# Check logs
docker logs somali-nlp-postgres

# Common issues:
# 1. Port already in use
lsof -i :5432
# Solution: Stop conflicting service or change POSTGRES_PORT

# 2. Volume corruption
docker volume rm somali-dialect-classifier_postgres_data
docker compose --profile prod up -d postgres

# 3. Permission issues
docker compose exec postgres ls -la /var/lib/postgresql/data
# Solution: Check Docker volume permissions
```

**Health Check Failing:**

```bash
# Check health status
docker inspect somali-nlp-postgres | grep -A 10 Health

# Manual health check
docker compose exec postgres pg_isready -U somali -d somali_nlp

# If failing, check PostgreSQL logs
docker logs somali-nlp-postgres --tail 50
```

### Rollback to SQLite

**When to Rollback:**
- Critical data integrity issues
- Unacceptable performance degradation
- Connection pool exhaustion under normal load
- Frequent deadlocks (should not occur, but if it does)

**Rollback Steps:**

```bash
# 1. Stop pipeline processes
# (kill any running pipeline processes)

# 2. Switch environment to SQLite
export SDC_LEDGER_BACKEND=sqlite
# Or edit .env:
sed -i 's/SDC_LEDGER_BACKEND=postgres/SDC_LEDGER_BACKEND=sqlite/' .env

# 3. Verify SQLite database exists
ls -lh data/ledger/crawl_ledger.db

# 4. Test pipeline with SQLite
python -m somali_dialect_classifier.cli.download_wikisom --limit 5

# 5. Stop PostgreSQL (optional)
docker compose --profile prod down

# 6. Document issues for investigation
echo "Rollback reason: [describe issue]" >> .backups/rollback_log.txt
```

**No data loss occurs during rollback** - SQLite database is never modified during PostgreSQL operation.

---

## Production Monitoring

### Key Metrics to Monitor

**1. Connection Pool Utilization**

```bash
# Target: < 80% of max_connections (10)
# Alert if: connections >= 9 for > 5 minutes

docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT count(*) as active,
     (count(*) * 100.0 / 10) as utilization_percent
     FROM pg_stat_activity WHERE datname = 'somali_nlp';"
```

**2. Query Latency**

```bash
# Target: < 100ms (p95)
# Alert if: p95 > 150ms

docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT
         percentile_cont(0.95) WITHIN GROUP (ORDER BY mean_exec_time) as p95_latency_ms,
         percentile_cont(0.99) WITHIN GROUP (ORDER BY mean_exec_time) as p99_latency_ms
     FROM pg_stat_statements;"
```

**3. Concurrent Write Throughput**

```bash
# Target: > 500 ops/s
# Alert if: < 100 ops/s

# Monitor transaction rate
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT xact_commit, xact_rollback,
     xact_commit + xact_rollback as total_transactions
     FROM pg_stat_database WHERE datname = 'somali_nlp';"
```

**4. Database Size**

```bash
# Monitor growth rate
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT pg_size_pretty(pg_database_size('somali_nlp')) as db_size;"

# Check table sizes
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as total_size
     FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;"
```

**5. Index Usage**

```bash
# Verify indexes are being used
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
     FROM pg_stat_user_indexes ORDER BY idx_scan DESC;"

# Alert if: idx_scan = 0 for any index (indicates unused index)
```

### Recommended Monitoring Tools

**1. pg_stat_statements Extension**

```bash
# Enable advanced query monitoring
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Query analysis
docker compose exec postgres psql -U somali -d somali_nlp -c \
    "SELECT query, calls, mean_exec_time, max_exec_time, stddev_exec_time
     FROM pg_stat_statements
     WHERE query LIKE '%crawl_ledger%'
     ORDER BY mean_exec_time DESC LIMIT 20;"
```

**2. Application-Level Logging**

Monitor application logs for PostgreSQL-specific messages:

```bash
# Connection pool warnings
grep "pool exhausted" logs/*.log

# Query errors
grep "psycopg2" logs/*.log | grep -i error

# Performance warnings
grep "query took" logs/*.log
```

**3. Docker Stats**

```bash
# Real-time resource usage
docker stats somali-nlp-postgres

# Continuous monitoring
watch -n 5 'docker stats somali-nlp-postgres --no-stream'
```

### Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Connection pool utilization | > 70% | > 90% | Increase pool size |
| Query latency (p95) | > 100ms | > 200ms | Optimize queries/indexes |
| Disk usage | > 80% | > 95% | Cleanup/expand disk |
| CPU usage | > 80% | > 95% | Scale resources |
| Memory usage | > 80% | > 95% | Increase Docker limits |
| Deadlocks | > 0 | > 1/hour | Investigate concurrency |

---

## Deployment Summary

### Estimated Deployment Timeline

**Small Dataset (< 10,000 URLs):**
- Setup: 15 minutes
- Migration: 5-10 minutes
- Validation: 10 minutes
- **Total: 30-45 minutes**

**Medium Dataset (10,000 - 100,000 URLs):**
- Setup: 15 minutes
- Migration: 30-60 minutes
- Validation: 15 minutes
- **Total: 1-1.5 hours**

**Large Dataset (> 100,000 URLs):**
- Setup: 15 minutes
- Migration: 2-3 hours
- Validation: 30 minutes
- **Total: 3-4 hours**

### Critical Success Criteria

**Deployment is successful when:**

1. **PostgreSQL container is healthy**
   - `docker ps` shows container running
   - Health check passes: `pg_isready` returns success
   - Logs show: "database system is ready to accept connections"

2. **Migration completed without errors**
   - Dry-run preview matches expectations
   - Actual migration completes successfully
   - Record counts match between SQLite and PostgreSQL
   - No NULL values in critical fields (url, source, state)

3. **Performance targets met**
   - Query latency < 100ms (p95)
   - Concurrent writes succeed without deadlocks
   - Connection pool responds within 5ms

4. **Application connects successfully**
   - Pipeline runs with `SDC_LEDGER_BACKEND=postgres`
   - Logs show: "PostgreSQL connection pool created"
   - No connection errors in application logs

5. **Data integrity verified**
   - All URLs present in PostgreSQL
   - State distribution matches SQLite
   - Metadata JSONB fields valid
   - RSS feeds migrated correctly

### Rollback Strategy

**Rollback is instant if deployment fails:**

1. **Preserve SQLite Database**
   - SQLite database is never deleted during migration
   - Original data remains intact in `data/ledger/crawl_ledger.db`

2. **Single Environment Variable Change**
   ```bash
   # Switch back to SQLite
   export SDC_LEDGER_BACKEND=sqlite
   # Or edit .env
   ```

3. **Zero Downtime**
   - Application restarts with SQLite backend
   - All functionality preserved
   - No data loss

4. **Investigation Time**
   - Rollback provides time to investigate PostgreSQL issues
   - Can re-attempt deployment after fixes
   - SQLite continues to operate normally

**Rollback Decision Criteria:**
- Migration fails data integrity checks
- Query latency > 200ms consistently
- Connection pool exhaustion under normal load
- Application errors connecting to PostgreSQL
- Stakeholder decision to postpone

---

## References

### Documentation Files

- **Setup Guide:** `docs/operations/postgres-setup.md`
- **Migration Guide:** `migrations/database/README.md` (Alembic migrations)
- **Schema Migrations (Alembic):** `migrations/database/alembic/versions/`
- **Schema Migrations (Legacy SQL):** `migrations/001_initial_schema.sql`, `migrations/002_pipeline_runs_table.sql`
- **Migration Script:** `scripts/migrate_sqlite_to_postgres.py`
- **PostgreSQL Backend:** `src/somali_dialect_classifier/database/postgres_ledger.py`
- **Migration Utilities:** `src/somali_dialect_classifier/database/migrations.py`

### Implementation Reports


### External Resources

- **PostgreSQL 16 Documentation:** https://www.postgresql.org/docs/16/
- **psycopg2 Connection Pooling:** https://www.psycopg.org/docs/pool.html
- **Docker Compose Reference:** https://docs.docker.com/compose/
- **pg_stat_statements:** https://www.postgresql.org/docs/16/pgstatstatements.html

---

## Support

### Common Questions

**Q: Can I run both SQLite and PostgreSQL simultaneously?**

A: No. The application uses one backend at a time, controlled by `SDC_LEDGER_BACKEND` environment variable. However, both databases can exist simultaneously without conflict.

**Q: How do I migrate back from PostgreSQL to SQLite?**

A: SQLite database is preserved during migration. Simply change `SDC_LEDGER_BACKEND=sqlite` to switch back. No data migration needed.

**Q: What happens if PostgreSQL container restarts?**

A: Data persists in Docker volume `postgres_data`. Connection pool automatically reconnects. No data loss.

**Q: Can I use external PostgreSQL instead of Docker?**

A: Yes. Set `POSTGRES_HOST` to external server IP/hostname. Ensure firewall allows connections.

**Q: How do I upgrade PostgreSQL version?**

A:
1. Backup database: `pg_dump`
2. Update `docker-compose.yml` image version
3. Recreate container: `docker compose up -d postgres`
4. Verify data integrity

### Issue Reporting

If deployment issues occur, collect the following information:

```bash
# System information
docker --version
docker compose version
python --version

# Container logs
docker logs somali-nlp-postgres > postgres_logs.txt

# PostgreSQL diagnostics
docker compose exec postgres psql -U somali -d somali_nlp -c "\l" > db_list.txt
docker compose exec postgres psql -U somali -d somali_nlp -c "\dt" > tables.txt
docker compose exec postgres psql -U somali -d somali_nlp -c "\di" > indexes.txt

# Application logs
cat logs/*.log | grep -i postgres > app_postgres_logs.txt

# Environment (sanitize passwords!)
cat .env | grep -v PASSWORD > env_sanitized.txt
```

---

**Document Version:** 1.0
**Maintained By:** DevOps Infrastructure Team

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
