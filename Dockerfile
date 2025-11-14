# Multi-stage Dockerfile for Somali NLP Data Pipeline
# Optimized for production deployment with minimal image size

# ============================================================================
# Stage 1: Build dependencies
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specification
COPY pyproject.toml ./

# Extract dependencies from pyproject.toml
# Install dependencies to a virtual environment for easy copying
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir \
        requests>=2.31 \
        tqdm>=4.65 \
        pyarrow>=14 \
        beautifulsoup4>=4.12 \
        lxml>=4.9 \
        feedparser>=6.0 \
        datasketch>=1.6 \
        apify-client==1.7.1 \
        pydantic>=2.5 \
        pydantic-settings>=2.1 \
        python-dotenv>=1.0 \
        psycopg2-binary>=2.9.9 \
        sqlalchemy>=2.0.23 \
        filelock>=3.13.1 \
        aiohttp>=3.9 \
        aiodns>=3.1 \
        pandas>=2.0

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for numpy/pandas operations
    libgomp1 \
    # Useful for debugging (optional, can be removed for smaller image)
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create application directories
RUN mkdir -p /app/data/ledger /app/data/raw /app/data/staging /app/data/processed /app/data/metrics /app/data/reports /app/logs

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create .env.example as template (actual .env should be mounted or passed via env vars)
COPY .env.example .env.example

# Create non-root user for security
RUN useradd -m -u 1000 somali && \
    chown -R somali:somali /app

# Switch to non-root user
USER somali

# Health check - verify Python environment is working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; from pathlib import Path; sys.exit(0 if Path('/app/src').exists() else 1)"

# Set Python path
ENV PYTHONPATH=/app/src:/app/scripts:/app

# Default command - run orchestrator with all pipelines
# Override with docker run command or docker-compose
CMD ["python", "-m", "somali_dialect_classifier.orchestration.flows"]
