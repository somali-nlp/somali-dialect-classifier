# PostgreSQL Setup Guide

**Setting up PostgreSQL database for production crawl ledger.**

**Last Updated:** 2025-11-29


---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
  - [Development (SQLite - Default)](#development-sqlite-default)
  - [Production (PostgreSQL)](#production-postgresql)
- [Architecture](#architecture)
  - [SQLite (Development)](#sqlite-development)
  - [PostgreSQL (Production)](#postgresql-production)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Docker Compose](#docker-compose)
- [Migration](#migration)
  - [Migrate from SQLite to PostgreSQL](#migrate-from-sqlite-to-postgresql)
- [Performance](#performance)
  - [Benchmarks](#benchmarks)
  - [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)
  - [PostgreSQL container won't start](#postgresql-container-wont-start)
  - [Connection refused](#connection-refused)
  - [Schema not initialized](#schema-not-initialized)
  - [Slow query performance](#slow-query-performance)
- [Best Practices](#best-practices)
  - [Development](#development)
  - [Production](#production)
  - [Quarterly Refresh](#quarterly-refresh)
- [Schema](#schema)
  - [Tables](#tables)
  - [Indexes](#indexes)
- [Security](#security)
  - [Credentials](#credentials)
  - [Network](#network)
  - [Backups](#backups)
- [References](#references)

---
## Overview

This guide covers PostgreSQL setup for the Somali NLP data pipeline. PostgreSQL provides production-scale performance with row-level locking for concurrent writes.

## Quick Start

### Development (SQLite - Default)

No setup needed. SQLite is the default backend:

```bash
# Uses SQLite automatically
python -m somali_dialect_classifier.cli.download_wikisom
```

### Production (PostgreSQL)

1. **Start PostgreSQL container:**

```bash
docker-compose --profile prod up -d postgres
```

2. **Set environment variables:**

```bash
export SDC_LEDGER_BACKEND=postgres
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=somali_nlp
export POSTGRES_USER=somali
export POSTGRES_PASSWORD="<your_secure_password>"
```

3. **Run pipeline:**

```bash
python -m somali_dialect_classifier.cli.download_wikisom
```

## Architecture

### SQLite (Development)
- **Use case:** Single developer, local testing
- **Concurrency:** Limited (file-level locking)
- **Location:** `data/ledger/crawl_ledger.db`
- **Pros:** Zero setup, portable, simple
- **Cons:** Write contention at scale

### PostgreSQL (Production)
- **Use case:** Production, concurrent sources, quarterly refresh
- **Concurrency:** Unlimited (row-level locking)
- **Location:** Docker container or cloud database
- **Pros:** Scales to 10x+, concurrent writes, ACID transactions
- **Cons:** Requires setup, external dependency

## Configuration

### Environment Variables

```bash
# Backend selection
SDC_LEDGER_BACKEND=postgres         # or 'sqlite'

# PostgreSQL connection (if backend=postgres)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=somali_nlp
POSTGRES_USER=somali
POSTGRES_PASSWORD="<secure_password>"
POSTGRES_AUTH_METHOD=md5

# SQLite fallback (if backend=sqlite)
SDC_LEDGER_SQLITE_PATH=data/ledger/crawl_ledger.db
```

### Docker Compose

The PostgreSQL service is defined in `docker-compose.yml`:

```yaml
postgres:
  image: postgres:16-alpine
  container_name: somali-nlp-postgres
  profiles:
    - prod
  environment:
    POSTGRES_DB: ${POSTGRES_DB:-somali_nlp}
    POSTGRES_USER: ${POSTGRES_USER:-somali}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-somali_dev_password}
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./migrations:/docker-entrypoint-initdb.d
```

## Migration

### Migrate from SQLite to PostgreSQL

Use the migration script to transfer existing data:

```bash
# Dry run (preview)
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/ledger/crawl_ledger.db \
    --postgres-host localhost \
    --postgres-db somali_nlp \
    --dry-run

# Actual migration
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/ledger/crawl_ledger.db \
    --postgres-host localhost \
    --postgres-db somali_nlp
```

The script will:
1. Connect to both databases
2. Export all URL records from SQLite
3. Import to PostgreSQL with proper state tracking
4. Verify counts match
5. Report statistics

## Performance

### Benchmarks

| Metric | SQLite | PostgreSQL |
|--------|--------|-----------|
| Single writes | 100-200 ops/s | 500-1000 ops/s |
| Concurrent writes (5 threads) | Deadlocks | No deadlocks |
| Query latency (p95) | 10-50ms | 5-20ms |
| Connection pooling | No | Yes (2-10 connections) |
| Max concurrent sources | 1-2 | 10+ |

### Scaling

- **Current:** 5 sources, sequential runs
- **Target:** 5 sources, concurrent runs (quarterly refresh)
- **10x scale:** 50 concurrent threads (stress tested)

## Connection Pool Management

Connection pool leaks are prevented through proper resource cleanup.

### Configuration

```bash
# Connection pool settings
SDC_DB__POOL_SIZE=5              # Base pool size
SDC_DB__MAX_OVERFLOW=10          # Additional connections under load
SDC_DB__POOL_RECYCLE=3600        # Recycle connections after 1 hour
SDC_DB__POOL_PRE_PING=true       # Verify connection before use
```

### Monitoring

Check active connections:

```bash
# Total connections
psql -h localhost -U somali -d somali_nlp -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='somali_nlp';"

# Idle connections
psql -h localhost -U somali -d somali_nlp -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state='idle';"
```

### Troubleshooting Pool Exhaustion

**Symptoms**: `QueuePool limit reached` errors

**Solutions**:

1. Increase pool size (temporary):
   ```bash
   export SDC_DB__POOL_SIZE=10
   export SDC_DB__MAX_OVERFLOW=20
   ```

2. Check for connection leaks:
   ```python
   # All connections should be properly closed
   # Check logs for unclosed connection warnings
   grep "unclosed connection" logs/*.log
   ```

3. Restart pooler:
   ```bash
   docker-compose restart postgres
   ```

### Best Practices

- **Development**: pool_size=2, max_overflow=5 (sufficient)
- **Production**: pool_size=5, max_overflow=10 (handles concurrent pipelines)
- **Quarterly Refresh**: pool_size=10, max_overflow=20 (all 5 sources concurrent)

---

## Query Timeout Configuration

Prevent runaway queries with timeout limits:

```bash
# Global query timeout
SDC_DB__QUERY_TIMEOUT=30  # seconds

# Per-statement timeout (PostgreSQL config)
ALTER DATABASE somali_nlp SET statement_timeout = '30s';
```

### Timeout Scenarios

| Query Type | Typical Duration | Recommended Timeout |
|------------|------------------|---------------------|
| URL lookup | 5-10ms | 30s (default) |
| State update | 10-20ms | 30s (default) |
| Batch insert | 100-500ms | 60s |
| Analytics query | 1-5s | 120s |

### Handling Timeouts

If queries consistently timeout:

1. **Add indexes**:
   ```sql
   CREATE INDEX idx_custom ON crawl_ledger(your_column);
   ```

2. **Analyze tables**:
   ```sql
   ANALYZE crawl_ledger;
   ```

3. **Check slow queries**:
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY total_time DESC
   LIMIT 10;
   ```

## Troubleshooting

### PostgreSQL container won't start

```bash
# Check logs
docker logs somali-nlp-postgres

# Verify port is available
lsof -i :5432

# Reset container
docker-compose --profile prod down
docker volume rm somali-dialect-classifier_postgres_data
docker-compose --profile prod up -d postgres
```

### Connection refused

1. Verify container is running: `docker ps | grep postgres`
2. Check environment variables are set
3. Test connection: `psql -h localhost -U somali -d somali_nlp`

### Schema not initialized

Schema is auto-initialized via migrations when using Docker. If issues occur:

```bash
# Option 1: Fresh restart (recommended for Docker)
docker-compose down -v
docker-compose up -d postgres

# Option 2: Alembic migrations (production)
cd migrations/database
alembic upgrade head

# Option 3: Legacy SQL (backward compatibility)
docker exec -i somali-nlp-postgres psql -U somali -d somali_nlp < migrations/001_initial_schema.sql
docker exec -i somali-nlp-postgres psql -U somali -d somali_nlp < migrations/002_pipeline_runs_table.sql
```

**Note:** As of 2025-11-29, the project uses Alembic for production-grade migrations. See [`migrations/database/README.md`](../../migrations/database/README.md) for details.

### Slow query performance

1. Check indexes: `\d+ crawl_ledger` in psql
2. Analyze tables: `ANALYZE crawl_ledger;`
3. Check connection pool: Look for "pool exhausted" warnings in logs

## Best Practices

### Development
- Use SQLite (default) for local development
- Commit `.env.example` but never `.env`
- Test with small datasets

### Production
- Always use PostgreSQL for production
- Set strong `POSTGRES_PASSWORD` (min 16 chars)
- Monitor connection pool usage
- Run migrations in dry-run mode first
- Backup database before migrations

### Quarterly Refresh
- Use PostgreSQL backend
- All 5 sources can run concurrently
- Monitor for connection pool exhaustion
- Check logs for deadlock warnings (should be none)

## Schema Management

As of 2025-11-29, database schema is managed via **Alembic migrations** (single source of truth):

### Migration Systems

**1. Alembic (Production - Recommended)**
- Full version control with rollback support
- Location: `migrations/database/alembic/versions/`
- Usage: `cd migrations/database && alembic upgrade head`

**2. Docker Init (Development - Auto-runs)**
- SQL files auto-execute on first `docker-compose up`
- Location: `migrations/*.sql`
- Backward compatible with existing setups

**3. Legacy SQL (Deprecated)**
- Direct SQL execution (no rollback support)
- Still supported for backward compatibility
- Use Alembic for new deployments

### Current Schema Version

- **Version 1:** Initial schema (crawl_ledger, rss_feeds)
- **Version 2:** Pipeline runs tracking table

### Managing Migrations

```bash
# Check current version
cd migrations/database
alembic current

# Apply latest migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

For complete migration documentation, see [`migrations/database/README.md`](../../migrations/database/README.md).

## Schema

### Tables

**crawl_ledger**
- Tracks all discovered URLs and their processing state
- Indexed on: source, state, text_hash, discovered_at
- JSONB metadata field for flexible storage

**rss_feeds**
- Tracks RSS feed fetch times for ethical scraping
- Prevents excessive polling (BBC Somali)

**pipeline_runs**
- Tracks each pipeline execution for scheduling
- Links to metrics and logs via run_id

**schema_version**
- Migration version tracking
- Current version: 2

### Indexes

All indexes are created automatically on schema initialization:
- `idx_crawl_ledger_source_state` - Fast state queries
- `idx_crawl_ledger_text_hash` - Duplicate detection
- `idx_crawl_ledger_metadata` - JSONB queries (GIN index)

## Security

### Credentials

**CRITICAL**: PostgreSQL password validation is enforced.

**Password Requirements**:
- Minimum length: 8 characters (16+ recommended for production)
- Must be set via `SDC_DB_PASSWORD` or `POSTGRES_PASSWORD` environment variable
- NEVER hardcode passwords in code
- NEVER commit `.env` files to version control

**Setting Passwords**:

```bash
# Development (.env file)
SDC_DB_PASSWORD="dev_password_123"

# Production (environment variable)
export SDC_DB_PASSWORD="$(openssl rand -base64 32)"

# Docker Compose
echo "SDC_DB_PASSWORD=$(openssl rand -base64 32)" >> .env
docker-compose up -d postgres
```

**Password Validation Errors**:

If you see:

```
ValueError: PostgreSQL password is required. Set SDC_DB_PASSWORD or POSTGRES_PASSWORD environment variable.
```

Solution:

```bash
# Check password is set
echo $SDC_DB_PASSWORD

# If empty, set it
export SDC_DB_PASSWORD="your_secure_password"
```

**Password Rotation**:

```bash
# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update PostgreSQL
psql -h localhost -U somali -d somali_nlp -c \
  "ALTER USER somali WITH PASSWORD '$NEW_PASSWORD';"

# Update environment
export SDC_DB_PASSWORD="$NEW_PASSWORD"

# Update .env (for Docker)
sed -i "s/SDC_DB_PASSWORD=.*/SDC_DB_PASSWORD=$NEW_PASSWORD/" .env
docker-compose restart postgres
```

**See Also**:
- [Configuration Guide - Security](../howto/configuration.md#security-best-practices)
- `.env.example` - Password configuration template

### Network
- PostgreSQL port (5432) exposed only on localhost
- Use Docker network for container-to-container communication
- Consider VPN for remote access

### Backups
- Docker volume: `postgres_data`
- Backup command: `docker exec somali-nlp-postgres pg_dump -U somali somali_nlp > backup.sql`
- Restore command: `docker exec -i somali-nlp-postgres psql -U somali somali_nlp < backup.sql`

## References

- PostgreSQL Documentation: https://www.postgresql.org/docs/16/
- Connection pooling: https://www.psycopg.org/docs/pool.html
- Docker Compose: https://docs.docker.com/compose/

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
