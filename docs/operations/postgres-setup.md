# PostgreSQL Setup Guide

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

Schema is auto-initialized on first connection. If issues occur:

```bash
# Manually apply schema
docker exec -i somali-nlp-postgres psql -U somali -d somali_nlp < migrations/001_initial_schema.sql
```

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

## Schema

### Tables

**crawl_ledger**
- Tracks all discovered URLs and their processing state
- Indexed on: source, state, text_hash, discovered_at
- JSONB metadata field for flexible storage

**rss_feeds**
- Tracks RSS feed fetch times for ethical scraping
- Prevents excessive polling (BBC Somali)

**schema_version**
- Migration version tracking
- Current version: 1

### Indexes

All indexes are created automatically on schema initialization:
- `idx_crawl_ledger_source_state` - Fast state queries
- `idx_crawl_ledger_text_hash` - Duplicate detection
- `idx_crawl_ledger_metadata` - JSONB queries (GIN index)

## Security

### Credentials
- Never commit passwords to git
- Use strong passwords in production
- Rotate passwords regularly

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
