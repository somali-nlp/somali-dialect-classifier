# Docker Guide

**Complete guide for using Docker with the Somali Dialect Classifier project.**

**Last Updated:** 2025-11-21

## Overview

The project uses Docker for consistent development and deployment environments. The Docker setup uses a multi-stage build process that installs dependencies from `pyproject.toml`, ensuring the container environment matches local development exactly.

## Prerequisites

- Docker 20.10 or higher
- Docker Compose 1.29 or higher (optional, for multi-container setups)

## Quick Start

### Building the Image

```bash
# Build Docker image
docker build -t somali-dialect-classifier .

# Build with specific tag
docker build -t somali-dialect-classifier:v1.0 .
```

### Running Commands

```bash
# Show CLI help
docker run --rm somali-dialect-classifier somali-tools --help

# Run specific command
docker run --rm somali-dialect-classifier somali-tools metrics consolidate

# With data volumes
docker run --rm -v $(pwd)/data:/app/data somali-dialect-classifier somali-tools ledger status
```

## Dockerfile Architecture

### Multi-Stage Build

The Dockerfile uses a two-stage build process for efficiency:

#### Stage 1: Builder

Installs all dependencies from `pyproject.toml`:

```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install with all extras
RUN pip install --no-cache-dir .[all]
```

#### Stage 2: Runtime

Creates minimal production image:

```dockerfile
FROM python:3.11-slim

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/

WORKDIR /app

# Set environment
ENV PYTHONPATH=/app
ENV PATH=/app:$PATH

# Default command
CMD ["somali-tools", "--help"]
```

### Benefits

- **Single source of truth:** Dependencies from `pyproject.toml` only
- **No dependency drift:** Container matches development environment
- **Smaller final image:** Multi-stage build excludes build artifacts
- **Consistent reproduction:** Exact package versions

## Usage Examples

### Running Data Pipelines

```bash
# Run Wikipedia pipeline
docker run --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier wikisom-download

# Run BBC pipeline with limits
docker run --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier bbcsom-download --max-articles 100

# Run all pipelines
docker run --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier somali-orchestrate --pipeline all
```

### Running CLI Commands

```bash
# Metrics consolidation
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/_site:/app/_site \
  somali-dialect-classifier somali-tools metrics consolidate

# Ledger status
docker run --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier somali-tools ledger status --verbose

# Data validation
docker run --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier somali-tools data validate-silver
```

### Interactive Shell

```bash
# Start interactive Python shell
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier python

# Start bash shell
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier bash
```

## Volume Mounts

### Common Mount Points

```bash
# Data directory (required for most operations)
-v $(pwd)/data:/app/data

# Dashboard output
-v $(pwd)/_site:/app/_site

# Configuration files
-v $(pwd)/.env:/app/.env:ro

# Custom config
-v $(pwd)/config:/app/config:ro
```

### Full Mount Example

```bash
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/_site:/app/_site \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/config:/app/config:ro \
  somali-dialect-classifier somali-tools metrics consolidate
```

## Environment Variables

Pass environment variables to configure behavior:

```bash
# Set custom data directory
docker run --rm \
  -e SDC_DATA__RAW_DIR=/custom/path \
  somali-dialect-classifier somali-tools ledger status

# Set log level
docker run --rm \
  -e SDC_LOGGING__LEVEL=DEBUG \
  somali-dialect-classifier wikisom-download

# Multiple environment variables
docker run --rm \
  -e SDC_DATA__RAW_DIR=/data/raw \
  -e SDC_DATA__SILVER_DIR=/data/silver \
  -e SDC_LOGGING__LEVEL=INFO \
  somali-dialect-classifier somali-tools metrics consolidate
```

## Docker Compose

### Basic Compose File

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    image: somali-dialect-classifier:latest
    volumes:
      - ./data:/app/data
      - ./_site:/app/_site
      - ./.env:/app/.env:ro
    environment:
      - SDC_LOGGING__LEVEL=INFO
    command: somali-tools --help

  pipeline:
    build: .
    image: somali-dialect-classifier:latest
    volumes:
      - ./data:/app/data
    command: somali-orchestrate --pipeline all

  dashboard:
    build: .
    image: somali-dialect-classifier:latest
    volumes:
      - ./data:/app/data
      - ./_site:/app/_site
    command: somali-tools dashboard build
```

### Running with Compose

```bash
# Build services
docker-compose build

# Run services
docker-compose up

# Run specific service
docker-compose run app somali-tools metrics consolidate

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Development with Docker

### Hot Reload Development

Mount source code for live changes:

```bash
docker run -it --rm \
  -v $(pwd)/src:/app/src:ro \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier bash

# Inside container
python -c "from somali_dialect_classifier.ingestion import BasePipeline; print('OK')"
```

### Running Tests

```bash
# Run full test suite
docker run --rm \
  -v $(pwd)/tests:/app/tests:ro \
  -v $(pwd)/src:/app/src:ro \
  somali-dialect-classifier pytest tests/

# Run specific test file
docker run --rm \
  -v $(pwd)/tests:/app/tests:ro \
  -v $(pwd)/src:/app/src:ro \
  somali-dialect-classifier pytest tests/test_filters.py -v

# With coverage
docker run --rm \
  -v $(pwd)/tests:/app/tests:ro \
  -v $(pwd)/src:/app/src:ro \
  somali-dialect-classifier pytest tests/ --cov --cov-report=term-missing
```

### Code Quality Checks

```bash
# Lint with ruff
docker run --rm \
  -v $(pwd)/src:/app/src:ro \
  somali-dialect-classifier ruff check src/

# Format check
docker run --rm \
  -v $(pwd)/src:/app/src:ro \
  somali-dialect-classifier ruff format --check src/

# Type check with mypy
docker run --rm \
  -v $(pwd)/src:/app/src:ro \
  somali-dialect-classifier mypy src/
```

## Production Deployment

### Building for Production

```bash
# Build optimized image
docker build \
  --tag somali-dialect-classifier:prod \
  --build-arg PYTHON_VERSION=3.11 \
  .

# Push to registry
docker tag somali-dialect-classifier:prod registry.example.com/somali-dialect-classifier:latest
docker push registry.example.com/somali-dialect-classifier:latest
```

### Running in Production

```bash
# Run with resource limits
docker run --rm \
  --memory=2g \
  --cpus=1.5 \
  -v /data:/app/data \
  -v /logs:/app/logs \
  somali-dialect-classifier somali-orchestrate --pipeline all

# Run as daemon
docker run -d \
  --name somali-pipeline \
  --restart unless-stopped \
  -v /data:/app/data \
  somali-dialect-classifier somali-orchestrate --pipeline wikipedia

# View logs
docker logs -f somali-pipeline

# Stop container
docker stop somali-pipeline
```

## Troubleshooting

### Build Errors

**Problem:** `ERROR: failed to solve: failed to compute cache key`

**Solution:**
```bash
# Clear Docker build cache
docker builder prune -a

# Rebuild without cache
docker build --no-cache -t somali-dialect-classifier .
```

### Permission Issues

**Problem:** `PermissionError: [Errno 13] Permission denied: '/app/data'`

**Solution:**
```bash
# Set correct permissions on host
chmod -R 755 data/

# Or run container with user ID
docker run --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier somali-tools metrics consolidate
```

### Volume Not Found

**Problem:** `Error: Directory 'data/' does not exist`

**Solution:**
```bash
# Create directory before running
mkdir -p data/_site

# Verify mount
docker run --rm \
  -v $(pwd)/data:/app/data \
  somali-dialect-classifier ls -la /app/data
```

### Dependency Conflicts

**Problem:** `ModuleNotFoundError: No module named 'pydantic'`

**Solution:**
```bash
# Verify pyproject.toml includes all dependencies
cat pyproject.toml | grep pydantic

# Rebuild image
docker build --no-cache -t somali-dialect-classifier .

# Test installation
docker run --rm somali-dialect-classifier pip list
```

## Optimization Tips

### Image Size Optimization

```bash
# Use specific Python version
FROM python:3.11-slim  # ~150MB vs python:3.11 (~900MB)

# Clean up after pip install
RUN pip install --no-cache-dir .[all]

# Remove unnecessary files
RUN rm -rf /tmp/* /var/tmp/*
```

### Build Speed Optimization

```bash
# Use BuildKit
DOCKER_BUILDKIT=1 docker build -t somali-dialect-classifier .

# Cache dependencies separately
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .[all]
COPY src/ src/  # Changes here don't invalidate dependency cache
```

### Layer Caching

```dockerfile
# COPY in order of change frequency (least to most)
COPY pyproject.toml README.md ./  # Rarely changes
COPY src/ src/                     # Changes more often
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/docker.yml
name: Docker

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t somali-dialect-classifier .

      - name: Run tests in container
        run: docker run --rm somali-dialect-classifier pytest tests/

      - name: Run CLI validation
        run: docker run --rm somali-dialect-classifier somali-tools --version
```

## Comparison: Local vs. Docker

| Aspect | Local Development | Docker |
|--------|-------------------|--------|
| **Setup Time** | 5-10 minutes | 10-15 minutes (first build) |
| **Consistency** | Depends on Python version | Guaranteed identical |
| **Isolation** | Global Python environment | Isolated container |
| **Performance** | Native speed | ~5% overhead |
| **Storage** | Packages in site-packages | Image ~500MB |
| **Updates** | `pip install -U` | `docker build` |

**Recommendation:** Use Docker for CI/CD and production, local development for iteration speed.

## Additional Resources

- **Dockerfile:** See project root for current Dockerfile
- **Docker Compose:** See `docker-compose.yml` for multi-container setup
- **Configuration:** `docs/howto/configuration.md` - Environment variable reference
- **CLI Reference:** `docs/reference/cli-reference.md` - All commands
- **Troubleshooting:** `docs/howto/troubleshooting.md` - Common issues

---

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Building the Image](#building-the-image)
  - [Running Commands](#running-commands)
- [Dockerfile Architecture](#dockerfile-architecture)
  - [Multi-Stage Build](#multi-stage-build)
    - [Stage 1: Builder](#stage-1-builder)
    - [Stage 2: Runtime](#stage-2-runtime)
  - [Benefits](#benefits)
- [Usage Examples](#usage-examples)
  - [Running Data Pipelines](#running-data-pipelines)
  - [Running CLI Commands](#running-cli-commands)
  - [Interactive Shell](#interactive-shell)
- [Volume Mounts](#volume-mounts)
  - [Common Mount Points](#common-mount-points)
  - [Full Mount Example](#full-mount-example)
- [Environment Variables](#environment-variables)
- [Docker Compose](#docker-compose)
  - [Basic Compose File](#basic-compose-file)
  - [Running with Compose](#running-with-compose)
- [Development with Docker](#development-with-docker)
  - [Hot Reload Development](#hot-reload-development)
  - [Running Tests](#running-tests)
  - [Code Quality Checks](#code-quality-checks)
- [Production Deployment](#production-deployment)
  - [Building for Production](#building-for-production)
  - [Running in Production](#running-in-production)
- [Troubleshooting](#troubleshooting)
  - [Build Errors](#build-errors)
  - [Permission Issues](#permission-issues)
  - [Volume Not Found](#volume-not-found)
  - [Dependency Conflicts](#dependency-conflicts)
- [Optimization Tips](#optimization-tips)
  - [Image Size Optimization](#image-size-optimization)
  - [Build Speed Optimization](#build-speed-optimization)
  - [Layer Caching](#layer-caching)
- [CI/CD Integration](#cicd-integration)
  - [GitHub Actions Example](#github-actions-example)
- [Comparison: Local vs. Docker](#comparison-local-vs-docker)
- [Additional Resources](#additional-resources)

---

**Related Documentation:**
- [Configuration Guide](../howto/configuration.md) - Environment variable reference
- [CLI Reference](../reference/cli-reference.md) - All commands
- [Troubleshooting](../howto/troubleshooting.md) - Common issues
- [Local vs Docker Development](../howto/local-vs-docker-development.md) - Comparison guide

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
