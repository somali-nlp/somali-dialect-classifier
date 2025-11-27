# Multi-stage Dockerfile for Somali Dialect Classifier
# Builds dependencies from pyproject.toml for consistency with development environment
# Optimized for production deployment with minimal image size

# ============================================================================
# Stage 1: Builder - Install dependencies from pyproject.toml
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies required for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata and dependencies
COPY pyproject.toml README.md ./

# Copy source code (required for editable install)
COPY src/ src/

# Upgrade pip and install build tools, then install package with all extras
# Using pip install .[config] to include production dependencies + config management
# See pyproject.toml [project.optional-dependencies] for available extras:
#   - [dev] for development (pytest, mypy, ruff)
#   - [config] for config management (pydantic, python-dotenv)
#   - [mlops] for MLOps tools (mlflow, prefect, great-expectations)
#   - [ml] for ML libraries (torch, transformers)
#   - [all] for everything
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir ".[config]"

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime system dependencies
# - libgomp1: OpenMP library required for NumPy/Pandas parallel operations
# - curl: For health checks and debugging (can be removed for smaller image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python site-packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy Python executables from builder (CLI entry points)
COPY --from=builder /usr/local/bin /usr/local/bin

# Create application directories for data and logs
RUN mkdir -p /app/data/ledger /app/data/raw /app/data/staging /app/data/processed /app/data/metrics /app/data/reports /app/logs

# Copy application source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN useradd -m -u 1000 somali && \
    chown -R somali:somali /app

# Switch to non-root user
USER somali

# Set Python environment variables
ENV PYTHONPATH=/app/src:/app/scripts:/app
ENV PYTHONUNBUFFERED=1
ENV PATH=/app:$PATH

# Health check - verify Python and application environment are functional
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; from pathlib import Path; sys.exit(0 if Path('/app/src').exists() else 1)" || exit 1

# Default command - show help for somali-tools CLI
# Override with specific command or python module invocation
CMD ["somali-tools", "--help"]
