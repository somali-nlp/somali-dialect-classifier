# Docker Deployment Guide

Complete guide for deploying the Somali NLP data pipeline using Docker containers.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Configuration Management](#configuration-management)
- [Health Checks](#health-checks)
- [Rollback Procedure](#rollback-procedure)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Docker** (version 20.10+)
   ```bash
   # Install Docker Desktop (macOS/Windows)
   # https://www.docker.com/products/docker-desktop

   # Or install Docker Engine (Linux)
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Verify installation
   docker --version
   docker-compose --version
   ```

2. **Git** (for version control)
   ```bash
   git --version
   ```

### Required Files

1. Environment configuration (`.env`)
   ```bash
   # Copy template and configure
   cp .env.example .env

   # Edit .env with your values
   nano .env
   ```

2. TikTok video URLs (optional, only if using TikTok scraping)
   ```bash
   # Create file with one URL per line
   nano data/tiktok_urls.txt
   ```

## Quick Start

Get up and running in 5 minutes:

```bash
# 1. Clone repository (if not already)
git clone <repository-url>
cd somali-dialect-classifier

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Build Docker image
docker-compose build

# 4. Run in development mode
docker-compose --profile dev up

# 5. Or run in production mode
docker-compose --profile prod up -d
```

## Development Deployment

Development mode provides an interactive environment with hot reload for code changes.

### Build Image

```bash
# Build the Docker image
docker-compose build

# Verify image was created
docker images | grep somali-nlp
```

Expected output:
```
somali-nlp    latest    abc123def456    2 minutes ago    850MB
```

### Run Development Container

```bash
# Start development container with interactive shell
docker-compose --profile dev up

# This will:
# - Mount source code for hot reload
# - Mount data directories for persistence
# - Provide interactive bash shell
```

### Working in Development Mode

Once inside the container:

```bash
# Run specific pipeline
python -m somali_dialect_classifier.orchestration.flows --pipeline wikipedia

# Run all pipelines
python -m somali_dialect_classifier.orchestration.flows --pipeline all

# Run tests
pytest tests/

# Check data
ls -lah data/processed/
ls -lah data/ledger/

# Exit container
exit
```

### Stop Development Container

```bash
# Stop and remove container
docker-compose --profile dev down

# Stop and remove container + volumes (CAREFUL: deletes data)
docker-compose --profile dev down -v
```

## Production Deployment

Production mode runs the pipeline as a daemon with resource limits and automatic restarts.

### Initial Production Deployment

```bash
# 1. Configure environment for production
cp .env.example .env
nano .env  # Set production values

# 2. Build production image
docker-compose --profile prod build

# 3. Start production container in background
docker-compose --profile prod up -d

# 4. Verify container is running
docker-compose ps

# 5. Monitor logs
docker-compose --profile prod logs -f
```

### Production Container Management

```bash
# View running containers
docker-compose ps

# Check container health
docker ps --filter name=somali-dialect-pipeline-prod

# View logs (real-time)
docker-compose --profile prod logs -f

# View logs (last 100 lines)
docker-compose --profile prod logs --tail 100

# Restart container
docker-compose --profile prod restart

# Stop container
docker-compose --profile prod stop

# Start stopped container
docker-compose --profile prod start

# Stop and remove container
docker-compose --profile prod down
```

### Resource Monitoring

```bash
# Monitor resource usage
docker stats somali-dialect-pipeline-prod

# View detailed container info
docker inspect somali-dialect-pipeline-prod
```

### Updating Production Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild image
docker-compose --profile prod build

# 3. Stop old container
docker-compose --profile prod down

# 4. Start new container
docker-compose --profile prod up -d

# 5. Verify health
docker-compose ps
docker-compose --profile prod logs --tail 50
```

## Configuration Management

### Environment Variables

Required environment variables in `.env`:

```bash
# TikTok Apify Configuration
SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=your_token_here

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: Data paths (uses defaults if not set)
SDC_DATA_DIR=data
SDC_LOGS_DIR=logs
```

### Secrets Management

**For production deployments:**

1. **Never commit `.env` to git**
   - `.env` is gitignored by default
   - Use `.env.example` as template

2. **For GitHub Actions:**
   ```bash
   # Add secrets in GitHub repository settings:
   # Settings > Secrets and variables > Actions > New repository secret

   # Example secrets:
   # - SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN
   ```

3. **For Docker Compose:**
   ```bash
   # Option 1: Use .env file (recommended for local)
   docker-compose --profile prod up -d

   # Option 2: Pass environment variables directly
   SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=xxx \
   docker-compose --profile prod up -d
   ```

### Configuration Validation

```bash
# Verify environment variables are loaded
docker exec somali-dialect-pipeline-prod \
  python -c "from somali_dialect_classifier.config import get_config; print(get_config())"

# Check configuration file syntax
docker exec somali-dialect-pipeline-prod \
  python -m somali_dialect_classifier.config
```

## Health Checks

### Container Health Status

```bash
# Check container health
docker ps | grep somali-dialect-pipeline-prod

# Output columns:
# - STATUS shows health: "Up X minutes (healthy)" or "Up X minutes (unhealthy)"
```

### Application Health Checks

```bash
# 1. Check Python environment
docker exec somali-dialect-pipeline-prod \
  python -c "import sys; print(f'Python {sys.version}')"

# 2. Check data directories
docker exec somali-dialect-pipeline-prod \
  ls -lah /app/data

# 3. Check ledger database (PostgreSQL in production)
docker exec somali-nlp-postgres \
  psql -U somali -d somali_nlp -c "SELECT COUNT(*), state FROM crawl_ledger GROUP BY state;"

# For SQLite (development mode only):
# docker exec somali-dialect-pipeline-prod \
#   sqlite3 /app/data/ledger/crawl_ledger.db "SELECT COUNT(*) FROM urls;"

# 4. Check logs
docker exec somali-dialect-pipeline-prod \
  tail -n 20 /app/logs/orchestrator.log
```

### Smoke Tests

Run quick tests to verify deployment:

```bash
# Run smoke tests (if available)
docker exec somali-dialect-pipeline-prod \
  pytest tests/smoke/ -v

# Or run simple validation
docker exec somali-dialect-pipeline-prod \
  python -m somali_dialect_classifier.orchestration.flows --help
```

## Rollback Procedure

If a deployment fails or causes issues, rollback to previous state.

### Step 1: Stop Current Container

```bash
docker-compose --profile prod down
```

### Step 2: Restore Data from Backup

```bash
# List available backups
python scripts/restore_system.py --list

# Restore from specific backup
python scripts/restore_system.py --backup 2025-11-10_14-30-00

# Verify restoration
ls -lah data/ledger/
ls -lah data/processed/
```

### Step 3: Rollback to Previous Image

```bash
# Option 1: Rebuild from previous git commit
git checkout <previous-commit-hash>
docker-compose --profile prod build
docker-compose --profile prod up -d

# Option 2: Use specific image tag
docker tag somali-nlp:latest somali-nlp:backup
docker pull somali-nlp:previous-version
docker-compose --profile prod up -d

# Option 3: Use local image backup
docker images | grep somali-nlp
docker tag <image-id> somali-nlp:latest
docker-compose --profile prod up -d
```

### Step 4: Verify Rollback

```bash
# Check container status
docker-compose ps

# Check logs for errors
docker-compose --profile prod logs --tail 100

# Verify data integrity
docker exec somali-dialect-pipeline-prod \
  ls -lah /app/data/processed/
```

### Emergency Rollback (One Command)

```bash
# Stop container, restore backup, restart
docker-compose --profile prod down && \
python scripts/restore_system.py --backup <backup-name> && \
docker-compose --profile prod up -d
```

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs for errors
docker-compose --profile prod logs

# Common causes:
# - Missing environment variables
# - Port conflicts
# - Insufficient resources
```

**Solution:**
```bash
# Verify .env file exists and has required values
cat .env

# Check for port conflicts
docker ps -a

# Increase Docker resource limits (Docker Desktop settings)
```

#### 2. Out of Memory

```bash
# Symptoms:
# - Container killed unexpectedly
# - "Killed" in logs

# Check resource limits
docker stats somali-dialect-pipeline-prod
```

**Solution:**
```bash
# Edit docker-compose.yml to adjust memory limits
# Under deploy.resources.limits.memory: 8G -> 16G

# Rebuild and restart
docker-compose --profile prod up -d
```

#### 3. Permission Denied Errors

```bash
# Symptoms:
# - Can't write to /app/data
# - Permission denied on log files
```

**Solution:**
```bash
# Ensure mounted volumes have correct permissions
sudo chown -R 1000:1000 data/ logs/ backups/

# Restart container
docker-compose --profile prod restart
```

#### 4. Image Build Fails

```bash
# Symptoms:
# - Dependency installation fails
# - Network timeouts
```

**Solution:**
```bash
# Clear Docker build cache
docker builder prune -a

# Rebuild with no cache
docker-compose build --no-cache

# Check internet connection and Docker Hub access
docker pull python:3.11-slim
```

#### 5. Data Not Persisting

```bash
# Symptoms:
# - Data lost after container restart
# - Empty data directories
```

**Solution:**
```bash
# Verify volume mounts in docker-compose.yml
docker-compose config | grep volumes

# Check volume exists
docker volume ls | grep somali-nlp

# Inspect volume
docker volume inspect somali-nlp_data-volume
```

### Debug Commands

```bash
# Enter running container for debugging
docker exec -it somali-dialect-pipeline-prod /bin/bash

# View full container logs
docker logs somali-dialect-pipeline-prod

# Check container resource usage
docker stats somali-dialect-pipeline-prod

# Inspect container configuration
docker inspect somali-dialect-pipeline-prod | jq .

# Test network connectivity from container
docker exec somali-dialect-pipeline-prod \
  curl -I https://so.wikipedia.org
```

### Getting Help

If issues persist:

1. **Check logs:**
   ```bash
   docker-compose --profile prod logs > deployment-logs.txt
   ```

2. **Gather system info:**
   ```bash
   docker version > system-info.txt
   docker-compose version >> system-info.txt
   docker info >> system-info.txt
   ```

3. **Create GitHub issue** with:
   - Error messages from logs
   - System info
   - Steps to reproduce

## Advanced Topics

### Custom Commands

Run custom commands in production container:

```bash
# Run specific pipeline
docker exec somali-dialect-pipeline-prod \
  python -m somali_dialect_classifier.orchestration.flows --pipeline bbc

# Run with custom arguments
docker exec somali-dialect-pipeline-prod \
  python -m somali_dialect_classifier.orchestration.flows \
  --pipeline all --max-bbc-articles 100

# Export metrics
docker exec somali-dialect-pipeline-prod \
  python scripts/export_dashboard_data.py
```

### Multi-Container Deployment

For future scaling with multiple services:

```bash
# Run pipeline and backup service together
docker-compose --profile prod --profile backup up -d

# Run backup separately
docker-compose --profile backup run --rm somali-nlp-backup
```

### CI/CD Integration

See `.github/workflows/` for automated deployment examples.

## Security Best Practices

1. **Non-root user:** Container runs as user `somali` (UID 1000)
2. **No secrets in image:** Use `.env` for sensitive data
3. **Read-only volumes:** Use `:ro` suffix for read-only mounts
4. **Resource limits:** Prevent DoS with CPU/memory limits
5. **Network isolation:** Use Docker networks for service communication

## Performance Optimization

1. **Build cache:** Use multi-stage builds for faster rebuilds
2. **Volume mounts:** Keep data outside container for persistence
3. **Resource limits:** Set appropriate CPU/memory limits
4. **Logging:** Configure log rotation to prevent disk fill

## Next Steps

- [Backup and Restore Guide](./backup-restore.md)
- [General Deployment Guide](./deployment.md)
- [Monitoring and Observability](deployment.md#monitoring-and-alerting)
