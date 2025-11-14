# Local vs Docker Development Guide

Complete guide for choosing between local and Docker development workflows.

## Quick Decision Guide

**Use Local Development when:**
- Debugging code and need fast iteration
- Testing small changes
- Running individual pipelines
- Exploring the codebase
- Development phase (data ingestion)

**Use Docker when:**
- Testing production configuration
- Running long pipelines overnight
- Integration testing with PostgreSQL
- Sharing work with team members
- Deploying to production
- CI/CD pipelines

---

## Local Development Setup

### Prerequisites

1. Python 3.9+ installed
2. All dependencies installed: `pip install -e ".[all]"`
3. `.env.local` file configured (auto-created)

### Running Pipelines Locally

```bash
# Recommended: Use Makefile commands (clean and discoverable)
make dev PIPELINE=wikipedia
make dev PIPELINE=bbc ARGS='--max-bbc-articles 100'
make dev-all  # Run all pipelines

# Alternative: Use the run-local.sh script directly
bash scripts/run-local.sh python -m somali_dialect_classifier.orchestration.flows --pipeline wikipedia

# Or set environment variables manually
export SDC_LEDGER_BACKEND=sqlite
export SDC_LEDGER_SQLITE_PATH=data/ledger/crawl_ledger.db
python -m somali_dialect_classifier.orchestration.flows --pipeline bbc
```

### Local Development Benefits

**Pros:**
- **Fast iteration**: No Docker build/start overhead
- **Easy debugging**: Direct access to Python debugger
- **Simple**: No container complexity
- **Resource efficient**: Lower memory usage

**Cons:**
- Different environment than production (SQLite vs PostgreSQL)
- Manual dependency management
- Potential environment conflicts

### Configuration

Local development uses `.env.local`:

```bash
# Local Development Environment
SDC_LEDGER_BACKEND=sqlite
SDC_LEDGER_SQLITE_PATH=data/ledger/crawl_ledger.db
ENV=development
LOG_LEVEL=DEBUG
```

---

## Docker Development Setup

### Prerequisites

1. Docker Desktop installed
2. Project cloned
3. `.env` file configured for production

### Running Pipelines with Docker

```bash
# Start PostgreSQL only
docker compose --profile prod up -d postgres

# Run a pipeline in container
docker compose run --rm somali-nlp-prod \
  python -m somali_dialect_classifier.orchestration.flows --pipeline wikipedia

# Or start full production stack
docker compose --profile prod up -d
```

### Docker Development Benefits

**Pros:**
- **Production parity**: Same environment as deployment
- **PostgreSQL**: Production database (10x concurrent operations)
- **Isolation**: No dependency conflicts
- **Reproducible**: Same environment everywhere

**Cons:**
- **Slower iteration**: Build/start overhead
- **More complex**: Container management
- **Resource intensive**: Docker Desktop uses memory
- **Debugging harder**: Additional layer of abstraction

### Configuration

Docker uses `.env`:

```bash
# Production Environment
SDC_LEDGER_BACKEND=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=somali_nlp
POSTGRES_USER=somali
POSTGRES_PASSWORD="<somali_secure_2025>"
ENV=production
LOG_LEVEL=INFO
```

---

## Hybrid Workflow (Recommended)

The best approach is to use both strategically:

### Day-to-Day Development
```bash
# Local: Fast iteration during development
./run-local.sh python -m somali_dialect_classifier.orchestration.flows --pipeline wikipedia
```

### Integration Testing
```bash
# Docker: Test with production database before committing
docker compose --profile prod up -d postgres
docker compose run --rm somali-nlp-prod \
  python -m somali_dialect_classifier.orchestration.flows --pipeline all
```

### Production Deployment
```bash
# Docker: Run in production
docker compose --profile prod up -d
```

---

## Common Commands

### Local Development

```bash
# Run Wikipedia pipeline locally
make dev PIPELINE=wikipedia

# Run with limits for testing
make dev PIPELINE=bbc ARGS='--max-bbc-articles 10'

# Run all pipelines
make dev-all

# Run tests locally
make test

# Check SQLite database
sqlite3 data/ledger/crawl_ledger.db "SELECT COUNT(*) FROM crawl_ledger;"
```

### Docker Development

```bash
# Build Docker image
make docker-build

# Start production stack (PostgreSQL + app)
make docker-up

# Run pipeline in container (for testing)
make docker-test

# View logs
make docker-logs

# Stop services
make docker-down

# Check PostgreSQL database
docker exec somali-nlp-postgres \
  psql -U somali -d somali_nlp -c "SELECT COUNT(*) FROM crawl_ledger;"

# Interactive shell in container
make docker-shell
```

---

## Switching Between Environments

### From Local to Docker

1. Commit your code changes
2. Build new Docker image: `docker compose build`
3. Run tests in Docker: `docker compose run --rm somali-nlp-prod pytest tests/`
4. Deploy: `docker compose --profile prod up -d`

### From Docker to Local

1. Stop Docker services: `docker compose --profile prod down`
2. Switch to local: `./run-local.sh python -m ...`

---

## Database Differences

### SQLite (Local)

- **Use case**: Local development, testing
- **Performance**: Great for single-threaded operations
- **Concurrency**: Limited (file-based locking)
- **Setup**: Zero configuration
- **Location**: `data/ledger/crawl_ledger.db`

```bash
# Check SQLite data
sqlite3 data/ledger/crawl_ledger.db ".tables"
sqlite3 data/ledger/crawl_ledger.db "SELECT * FROM crawl_ledger LIMIT 5;"
```

### PostgreSQL (Docker)

- **Use case**: Production, integration testing
- **Performance**: Optimized for concurrent operations
- **Concurrency**: 10x better than SQLite
- **Setup**: Requires Docker
- **Location**: Docker volume `postgres_data`

```bash
# Check PostgreSQL data
docker exec -it somali-nlp-postgres psql -U somali -d somali_nlp
# In psql shell:
# \dt                    -- List tables
# SELECT * FROM crawl_ledger LIMIT 5;
```

---

## Troubleshooting

### Local Development Issues

**Problem**: Import errors or missing modules
```bash
# Solution: Reinstall in editable mode
pip install -e ".[all]"
```

**Problem**: Can't find data files
```bash
# Solution: Check you're in project root
pwd  # Should be .../somali-dialect-classifier
ls data/  # Should show raw/, processed/, etc.
```

### Docker Issues

**Problem**: Container won't start
```bash
# Solution: Check logs
docker compose logs postgres
# Rebuild if needed
docker compose build --no-cache
```

**Problem**: Can't connect to PostgreSQL
```bash
# Solution: Check if running
docker compose ps
# Restart if needed
docker compose restart postgres
```

---

## Best Practices

### For Data Ingestion Phase (Current)

1. **Default to local**: Faster development
2. **Test in Docker weekly**: Ensure production parity
3. **Use SQLite locally**: Simpler, no Docker needed
4. **Switch to Docker for**: Long-running jobs, overnight scraping

### For Model Training Phase (Future)

1. **Use Docker**: GPU support, consistent ML environment
2. **Docker volumes**: Persist models and artifacts
3. **PostgreSQL**: Track experiments, model versions

### For Production Deployment

1. **Always Docker**: Consistency and reproducibility
2. **PostgreSQL**: Production database
3. **Resource limits**: Set in docker-compose.yml
4. **Monitoring**: Use health checks and logs

---

## Summary

| Aspect | Local | Docker |
|--------|-------|--------|
| **Speed** | ⚡ Fast | 🐢 Slower |
| **Setup** | ✅ Simple | ⚙️ Complex |
| **Debugging** | 🔍 Easy | 🔎 Harder |
| **Production Parity** | ❌ No | ✅ Yes |
| **Database** | SQLite | PostgreSQL |
| **Best For** | Development | Testing/Production |

**Recommendation**: Start local, test with Docker, deploy with Docker.

---

## Next Steps

- [Docker Deployment Guide](../operations/docker-deployment.md) - Full Docker deployment instructions
- [Configuration Guide](configuration.md) - Environment variable reference
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
