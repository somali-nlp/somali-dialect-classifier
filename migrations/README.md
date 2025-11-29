# Migrations Directory

This directory contains database schema migrations for the Somali NLP project.

## Quick Start

### For Development (Docker)

```bash
# Migrations run automatically on first start
docker-compose up -d postgres
```

### For Production (Alembic)

```bash
cd database
alembic upgrade head
```

## Structure

```
migrations/
├── README.md                 # This file
├── database/                 # PostgreSQL database migrations
│   ├── README.md            # Detailed migration guide
│   ├── alembic.ini          # Alembic configuration
│   ├── alembic/             # Alembic migrations (NEW)
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       └── 002_pipeline_runs_table.py
│   ├── 001_initial_schema.sql      # Legacy SQL files
│   └── 002_pipeline_runs_table.sql # (for Docker init)
```

## Migration Systems

This project supports two migration systems:

### 1. Alembic (Production)
- Full version control
- Up/down migrations
- Dependency tracking
- **Location:** `database/alembic/versions/`
- **Usage:** `cd database && alembic upgrade head`

### 2. Docker Init (Development)
- Auto-runs on first `docker-compose up`
- Simple SQL files
- **Location:** `database/*.sql`
- **Usage:** Automatic

## Important Changes (2025-11-29)

**Schema duplication eliminated:**
- ❌ **REMOVED:** CREATE TABLE statements from Python code
- ✅ **NEW:** Single source of truth in migration files
- ✅ **NEW:** Alembic support for production migrations
- ✅ **NEW:** Table existence verification in Python code

**What this means for you:**
- Existing Docker setups continue to work (backward compatible)
- Python code now verifies tables exist instead of creating them
- New Alembic migrations for production-grade schema evolution

## For More Details

See `database/README.md` for comprehensive migration documentation including:
- How to create new migrations
- Troubleshooting guide
- Best practices
- CI/CD integration

## Schema Versions

| Version | Date | Description |
|---------|------|-------------|
| 001 | 2025-11-11 | Initial schema (crawl_ledger, rss_feeds) |
| 002 | 2025-11-15 | Pipeline runs tracking |
