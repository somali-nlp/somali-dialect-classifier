# Database Migrations

This directory contains PostgreSQL database schema migrations for the Somali NLP project.

## Structure

```
database/
├── README.md                    # This file
├── alembic.ini                  # Alembic configuration
├── alembic/                     # Alembic migrations
│   ├── env.py                   # Alembic environment
│   ├── script.py.mako          # Migration template
│   └── versions/               # Migration versions
│       ├── 001_initial_schema.py
│       └── 002_pipeline_runs_table.py
├── 001_initial_schema.sql      # Legacy SQL (backward compatibility)
└── 002_pipeline_runs_table.sql # Legacy SQL (backward compatibility)
```

## Schema Management Philosophy

**Single Source of Truth:** Database schema is defined ONLY in migration files, not in Python code.

### What's in migrations:
- ✅ `CREATE TABLE` statements
- ✅ `CREATE INDEX` statements
- ✅ Schema evolution (ALTER TABLE, etc.)

### What's in Python code:
- ❌ NO `CREATE TABLE` statements
- ✅ Table existence checks
- ✅ Query operations (INSERT, SELECT, UPDATE, DELETE)

## Migration Systems

### 1. Alembic (Recommended for Production)

**Advantages:**
- Version control for schema changes
- Up/down migrations (rollback support)
- Automatic dependency tracking
- Ideal for production deployments

**Usage:**

```bash
# Install alembic
pip install alembic psycopg2-binary

# Run all migrations
cd migrations/database
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### 2. Docker Init (Auto-initialization)

**Advantages:**
- Zero setup for new developers
- Runs automatically on first `docker-compose up`
- Uses simple SQL files

**How it works:**
1. Docker mounts `./migrations` to `/docker-entrypoint-initdb.d`
2. PostgreSQL automatically runs `*.sql` files on first start
3. Files run in alphabetical order: `001_*.sql`, `002_*.sql`, etc.

**Usage:**

```bash
# Start fresh (destroys existing data)
docker-compose down -v
docker-compose up -d postgres

# Check if migrations ran
docker-compose logs postgres | grep "initial"
```

### 3. Legacy SQL Files (Backward Compatibility)

The `*.sql` files in this directory are kept for backward compatibility with:
- Docker init scripts
- Manual migrations
- CI/CD pipelines that haven't migrated to Alembic

**IMPORTANT:** When adding new migrations:
1. Create Alembic migration: `alembic revision -m "description"`
2. Also create corresponding SQL file for Docker init
3. Keep both in sync

## Current Schema Versions

| Version | Migration | Description |
|---------|-----------|-------------|
| 001 | `001_initial_schema.py` | Initial schema (crawl_ledger, rss_feeds, schema_version) |
| 002 | `002_pipeline_runs_table.py` | Pipeline runs tracking table |

## Creating New Migrations

### Option 1: Alembic (Recommended)

```bash
cd migrations/database

# Create new migration
alembic revision -m "add_new_table"

# Edit the generated file in alembic/versions/
# Add upgrade() and downgrade() logic

# Test migration
alembic upgrade head

# Test rollback
alembic downgrade -1
```

### Option 2: SQL File (for Docker init)

```bash
# Create new SQL file
touch migrations/003_add_new_table.sql

# Write SQL
cat > migrations/003_add_new_table.sql << 'EOF'
-- Description
CREATE TABLE IF NOT EXISTS new_table (
    id SERIAL PRIMARY KEY,
    ...
);

CREATE INDEX IF NOT EXISTS idx_new_table_foo ON new_table(foo);

INSERT INTO schema_version (version) VALUES (3)
ON CONFLICT DO NOTHING;
EOF
```

## Python Code Integration

### ✅ CORRECT: Check table existence

```python
from somali_dialect_classifier.database.migrations import verify_schema_initialized

# In your code
conn = get_connection()
all_exist, missing = verify_schema_initialized(conn)
if not all_exist:
    raise RuntimeError(f"Missing tables: {missing}")
```

### ❌ WRONG: Create tables in Python

```python
# DON'T DO THIS!
conn.execute("""
    CREATE TABLE IF NOT EXISTS my_table (
        ...
    )
""")
```

## Troubleshooting

### Tables don't exist

```bash
# Check if migrations ran
docker-compose exec postgres psql -U somali -d somali_nlp -c "\dt"

# If empty, run migrations
docker-compose down -v
docker-compose up -d postgres

# Or use Alembic
cd migrations/database && alembic upgrade head
```

### Schema drift detected

```bash
# Check current schema version
docker-compose exec postgres psql -U somali -d somali_nlp -c "SELECT * FROM schema_version;"

# Compare with migration files
alembic current
```

### Migration failed halfway

```bash
# Check Alembic version
alembic current

# Rollback to known good state
alembic downgrade 001

# Re-run migration
alembic upgrade head
```

## Best Practices

1. **Never skip versions:** Migrations must run in order (001 → 002 → 003)
2. **Always test rollback:** Every migration should have a working `downgrade()`
3. **Keep SQL and Alembic in sync:** Update both when schema changes
4. **Document breaking changes:** Add notes in migration docstrings
5. **Use transactions:** Wrap migrations in BEGIN/COMMIT for atomicity

## Environment Variables

Alembic reads database connection from:

```bash
# Default (development)
DATABASE_URL=postgresql://somali:somali_dev_password@localhost:5432/somali_nlp

# Override via environment
export DATABASE_URL=postgresql://user:pass@host:port/db
```

## CI/CD Integration

```yaml
# Example GitHub Actions
- name: Run migrations
  run: |
    cd migrations/database
    alembic upgrade head
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Init Scripts](https://hub.docker.com/_/postgres) (see "Initialization scripts")
- Project docs: `docs/operations/postgres-setup.md`
