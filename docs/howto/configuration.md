# Configuration Management Guide

**Comprehensive guide to configuring the Somali Dialect Classifier using environment variables, .env files, and programmatic configuration.**

**Last Updated:** 2025-11-21

## Table of Contents

1. [Overview](#overview)
2. [Configuration Hierarchy](#configuration-hierarchy)
3. [Environment Variables Reference](#environment-variables-reference)
4. [Configuration Sections](#configuration-sections)
   - [PerformanceConfig](#performanceconfig-new-in-v020)
   - [Performance Tuning Quick Start](#performance-tuning-quick-start)
5. [Programmatic Access](#programmatic-access)
   - [Configuration Startup Logging](#configuration-startup-logging)
6. [Environment-Specific Configs](#environment-specific-configs)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The project uses **pydantic-settings** for declarative, type-safe configuration management with automatic environment variable binding. Configuration follows the **12-factor app** methodology.

### Key Features

- **Environment variable override**: All settings configurable via `SDC_*` env vars
- **Type validation**: Pydantic ensures type safety and validation
- **Hierarchical structure**: Organized into logical sections (data, scraping, logging)
- **Defaults provided**: Works out-of-the-box with sensible defaults
- **`.env` file support**: Load configuration from `.env` file in project root
- **Graceful fallback**: If pydantic not installed, falls back to dataclass-based config

### Configuration Philosophy

```
┌─────────────────┐
│ Defaults        │  ← Hardcoded in config.py (lowest priority)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ .env file       │  ← Project-level configuration
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Environment     │  ← Runtime overrides (highest priority)
│ variables       │
└─────────────────┘
```

## Configuration Hierarchy

Configuration is loaded in the following order (later sources override earlier ones):

1. **Default values** (defined in `config.py`)
2. **`.env` file** (project root)
3. **Environment variables** (runtime overrides)

### Example

```python
# config.py default
raw_dir: Path = Path('data/raw')

# .env file override
SDC_DATA__RAW_DIR=/custom/data/raw

# Environment variable override (highest priority)
export SDC_DATA__RAW_DIR=/prod/data/raw
```

## Environment Variables Reference

All environment variables use the `SDC_` prefix (Somali Dialect Classifier) and double underscores `__` for nested configuration.

### Naming Convention

```
SDC_{SECTION}__{SUBSECTION}__{FIELD}
```

Examples:
- `SDC_DATA__RAW_DIR` → `Config.data.raw_dir`
- `SDC_SCRAPING__BBC__MAX_ARTICLES` → `Config.scraping.bbc.max_articles`
- `SDC_LOGGING__LEVEL` → `Config.logging.level`

### Complete Reference

| Environment Variable | Type | Default | Description |
|---------------------|------|---------|-------------|
| **Data Paths** |
| `SDC_DATA__RAW_DIR` | Path | `data/raw` | Directory for raw scraped data (Bronze layer) |
| `SDC_DATA__SILVER_DIR` | Path | `data/processed/silver` | Directory for cleaned Parquet datasets (Silver layer) |
| `SDC_DATA__STAGING_DIR` | Path | `data/staging` | Directory for intermediate staging files |
| `SDC_DATA__PROCESSED_DIR` | Path | `data/processed` | Directory for processed text files |
| **BBC Scraping** |
| `SDC_SCRAPING__BBC__MAX_ARTICLES` | int | `None` | Maximum articles to scrape (None = unlimited) |
| `SDC_SCRAPING__BBC__MIN_DELAY` | float | `1.0` | Minimum delay between requests (seconds) |
| `SDC_SCRAPING__BBC__MAX_DELAY` | float | `3.0` | Maximum delay between requests (seconds) |
| `SDC_SCRAPING__BBC__TIMEOUT` | int | `30` | Request timeout (seconds) |
| `SDC_SCRAPING__BBC__USER_AGENT` | str | `Mozilla/5.0...` | User agent string for requests |
| **Wikipedia Scraping** |
| `SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE` | int | `100` | Number of articles to fetch per batch |
| `SDC_SCRAPING__WIKIPEDIA__MAX_ARTICLES` | int | `None` | Maximum articles to fetch (None = unlimited) |
| `SDC_SCRAPING__WIKIPEDIA__TIMEOUT` | int | `30` | Request timeout (seconds) |
| **Logging** |
| `SDC_LOGGING__LEVEL` | str | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SDC_LOGGING__LOG_DIR` | Path | `logs` | Directory for log files |
| `SDC_LOGGING__FORMAT` | str | `%(asctime)s...` | Log message format |

## Configuration Sections

### DataConfig

Controls data directory paths for the medallion architecture (Bronze → Silver → Gold).

**Fields**:

```python
class DataConfig(BaseSettings):
    raw_dir: Path = Path('data/raw')              # Bronze layer
    silver_dir: Path = Path('data/processed/silver')  # Silver layer
    staging_dir: Path = Path('data/staging')      # Intermediate
    processed_dir: Path = Path('data/processed')  # Text outputs
```

**Environment Variables**:
```bash
SDC_DATA__RAW_DIR=/data/bronze
SDC_DATA__SILVER_DIR=/data/silver
SDC_DATA__STAGING_DIR=/data/staging
SDC_DATA__PROCESSED_DIR=/data/processed
```

**Use Cases**:
- **Development**: Use local `data/` directory (default)
- **Production**: Use absolute paths to persistent storage
- **Docker**: Map to mounted volumes
- **Cloud**: Use cloud storage paths (e.g., `/mnt/s3/data/raw`)

### BBCScrapingConfig

Controls BBC Somali news scraping behavior with ethical rate limiting.

**Fields**:

```python
class BBCScrapingConfig(BaseSettings):
    max_articles: Optional[int] = None     # None = unlimited
    min_delay: float = 1.0                 # Min seconds between requests
    max_delay: float = 3.0                 # Max seconds between requests
    timeout: int = 30                      # Request timeout
    user_agent: str = 'Mozilla/5.0...'    # User agent string
```

**Environment Variables**:
```bash
# Limit to 100 articles for testing
SDC_SCRAPING__BBC__MAX_ARTICLES=100

# Increase delays for more ethical scraping
SDC_SCRAPING__BBC__MIN_DELAY=2.0
SDC_SCRAPING__BBC__MAX_DELAY=5.0

# Custom user agent
SDC_SCRAPING__BBC__USER_AGENT="MyBot/1.0 (+https://example.com)"
```

**Rate Limiting Behavior**:
- Delay = `random.uniform(min_delay, max_delay)`
- Automatic retry with exponential backoff on 429, 5xx errors
- Respects robots.txt

### WikipediaScrapingConfig

Controls Wikipedia dump download and processing.

**Fields**:

```python
class WikipediaScrapingConfig(BaseSettings):
    batch_size: int = 100                  # Articles per batch
    max_articles: Optional[int] = None     # None = unlimited
    timeout: int = 30                      # Request timeout
```

**Environment Variables**:
```bash
# Process in smaller batches for memory efficiency
SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=50

# Limit for testing
SDC_SCRAPING__WIKIPEDIA__MAX_ARTICLES=1000
```

### LoggingConfig

Controls logging behavior and output destinations.

**Fields**:

```python
class LoggingConfig(BaseSettings):
    level: str = 'INFO'                    # DEBUG, INFO, WARNING, ERROR
    log_dir: Path = Path('logs')           # Log file directory
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

**Environment Variables**:
```bash
# Enable debug logging
SDC_LOGGING__LEVEL=DEBUG

# Custom log directory
SDC_LOGGING__LOG_DIR=/var/log/somali-dialect-classifier

# Custom format (timestamps only)
SDC_LOGGING__FORMAT="%(asctime)s - %(message)s"
```

### Deduplication Configuration

Configure deduplication behavior with centralized settings:

```bash
# Similarity threshold for near-duplicate detection (0.0-1.0)
SDC_DEDUP__SIMILARITY_THRESHOLD=0.85

# Maximum cache size for hash storage (default: 100,000)
SDC_DEDUP__CACHE_SIZE=100000

# Enable MinHash for near-duplicate detection
SDC_DEDUP__ENABLE_MINHASH=true

# Number of MinHash shards for parallel processing
SDC_DEDUP__NUM_SHARDS=10
```

**Memory Management:**
- `DEDUP_CACHE_SIZE`: Controls memory usage (legacy, prefer SDC_DEDUP__CACHE_SIZE)
- Default 100k entries ≈ 14MB memory
- Increase for large runs, decrease for memory-constrained environments

**Performance Impact:**
- 1M documents: 200MB → 14MB (93% reduction with bounded cache)
- May miss duplicates after cache eviction (acceptable tradeoff)
- No false positives guaranteed

See [Memory Optimization Guide](memory-optimization.md) for details.

### Språkbanken Configuration

```bash
# XML parsing timeout in seconds (default: 300)
SDC_SCRAPING__SPRAKBANKEN__XML_PARSE_TIMEOUT=300
```

**Performance Notes:**
- Streaming XML parser uses O(1) memory regardless of file size
- Timeout prevents hanging on malformed/large XML files
- Adjust timeout for very large corpus files (>1GB)

**Memory Optimization:**
- Språkbanken processor uses streaming XML parser
- Memory usage: O(1) bounded (~4MB) vs O(n) unbounded
- Before: 500MB for large files → After: 4MB (99% reduction)

### OrchestrationConfig (New in Phase B)

Controls pipeline orchestration behavior including refresh cadences and daily quotas.

**Fields**:

```python
class OrchestrationConfig(BaseSettings):
    initial_collection_days: int = 7          # Days all sources run daily
    default_cadence_days: int = 7             # Default refresh interval
    cadence_days: Dict[str, int] = {          # Per-source cadences
        "wikipedia": 7,
        "bbc": 1,
        "huggingface": 30,
        "sprakbanken": 90,
        "tiktok": 7
    }
    quota_limits: Dict[str, int] = {          # Per-source daily quotas
        "bbc": 350,
        "huggingface": 10000,
        "sprakbanken": 10,
        "wikipedia": 0,  # Unlimited
        "tiktok": 0      # Manual scheduling
    }
```

**Field Descriptions**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `initial_collection_days` | `int` | `7` | Duration of initial collection phase (all sources run daily) |
| `default_cadence_days` | `int` | `7` | Default refresh interval if source not in `cadence_days` |
| `cadence_days` | `Dict[str, int]` | See above | Per-source refresh intervals (days) |
| `quota_limits` | `Dict[str, int]` | See above | Per-source daily processing quotas (0 = unlimited) |

**Validation Rules**:

- `initial_collection_days`: Must be between 1-30 days
- `cadence_days` values: Must be between 1-365 days
- `quota_limits` values: Must be >= 0 (0 means unlimited)

**Environment Variables**:

```bash
# Initial collection phase
SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS=7

# Default cadence
SDC_ORCHESTRATION__DEFAULT_CADENCE_DAYS=7

# Per-source cadences
SDC_ORCHESTRATION__CADENCE_DAYS__WIKIPEDIA=7
SDC_ORCHESTRATION__CADENCE_DAYS__BBC=1
SDC_ORCHESTRATION__CADENCE_DAYS__HUGGINGFACE=30
SDC_ORCHESTRATION__CADENCE_DAYS__SPRAKBANKEN=90
SDC_ORCHESTRATION__CADENCE_DAYS__TIKTOK=7

# Per-source quotas (Phase C feature)
SDC_ORCHESTRATION__QUOTA_LIMITS__BBC=350
SDC_ORCHESTRATION__QUOTA_LIMITS__HUGGINGFACE=10000
SDC_ORCHESTRATION__QUOTA_LIMITS__SPRAKBANKEN=10
SDC_ORCHESTRATION__QUOTA_LIMITS__WIKIPEDIA=0
SDC_ORCHESTRATION__QUOTA_LIMITS__TIKTOK=0
```

**Cadence Guidelines**:

| Source | Recommended Cadence | Rationale |
|--------|---------------------|-----------|
| BBC | 1 day | Daily news updates |
| Wikipedia | 7 days | Weekly content changes |
| TikTok | 3 days | Active social media |
| HuggingFace | 30 days | Static dataset snapshots |
| Språkbanken | 90 days | Static academic corpora |

**Quota Guidelines**:

| Source | Recommended Quota | Rationale |
|--------|------------------|-----------|
| BBC | 350 articles | Ethical web scraping |
| HuggingFace | 10,000 records | Manage processing time |
| Språkbanken | 10 corpora | Static collection |
| Wikipedia | 0 (unlimited) | File-based, efficient |
| TikTok | 0 (manual) | Controlled externally |

**Usage Example**:

```python
from somali_dialect_classifier.config import get_config

config = get_config()

# Access cadences
print(f"BBC cadence: {config.orchestration.cadence_days['bbc']} days")
print(f"Wikipedia cadence: {config.orchestration.cadence_days['wikipedia']} days")

# Access quotas
print(f"BBC daily quota: {config.orchestration.quota_limits['bbc']} articles")
print(f"HuggingFace daily quota: {config.orchestration.quota_limits['huggingface']} records")

# Get cadence for specific source (with fallback to default)
def get_cadence(source: str) -> int:
    return config.orchestration.cadence_days.get(
        source,
        config.orchestration.default_cadence_days
    )

print(f"BBC runs every {get_cadence('bbc')} day(s)")
```

**Override Example** (.env file):

```bash
# Increase BBC daily quota
SDC_ORCHESTRATION__QUOTA_LIMITS__BBC=500

# Run Wikipedia more frequently
SDC_ORCHESTRATION__CADENCE_DAYS__WIKIPEDIA=3

# Extend initial collection phase
SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS=14
```

**See Also**:
- [Orchestration Guide](orchestration.md) - Full orchestration documentation
- [Daily Quotas Documentation](orchestration.md#daily-quotas-new-in-phase-c) - Quota enforcement details

### PerformanceConfig (New in v0.2.0)

Controls timeout, buffer sizes, and resource limits for production reliability.

**Fields**:

```python
class PerformanceConfig(BaseSettings):
    request_timeout: int = 30           # HTTP request timeout (seconds)
    query_timeout: int = 30             # Database query timeout (seconds)
    buffer_size_mb: int = 10            # XML/HTML parsing buffer (MB)
    min_free_disk_gb: int = 10          # Minimum disk space (GB)
    connection_pool_size: int = 5       # Database connection pool size
    max_pool_overflow: int = 10         # Max additional connections
```

**Environment Variables**:

```bash
# HTTP timeout (applies to BBC, Wikipedia, HuggingFace)
SDC_HTTP__REQUEST_TIMEOUT=30

# Database timeout (prevents runaway queries)
SDC_DB__QUERY_TIMEOUT=30

# Parsing buffer (memory vs. performance tradeoff)
SDC_PARSING__BUFFER_SIZE_MB=10

# Disk space safety check
SDC_DISK__MIN_FREE_SPACE_GB=10

# Connection pool (concurrent pipeline support)
SDC_DB__POOL_SIZE=5
SDC_DB__MAX_OVERFLOW=10
```

**Usage Example**:

```python
from somali_dialect_classifier.config import get_config

config = get_config()

# Check timeout settings
print(f"HTTP timeout: {config.performance.request_timeout}s")
print(f"DB query timeout: {config.performance.query_timeout}s")

# Adjust for slow network
import os
os.environ['SDC_HTTP__REQUEST_TIMEOUT'] = '60'
config = get_config(reload=True)
```

**Tuning Guidelines**:

| Setting | Low Resources | Standard | High Performance |
|---------|--------------|----------|------------------|
| `request_timeout` | 60s | 30s | 15s |
| `query_timeout` | 60s | 30s | 15s |
| `buffer_size_mb` | 5MB | 10MB | 20MB |
| `min_free_disk_gb` | 5GB | 10GB | 20GB |
| `pool_size` | 2 | 5 | 10 |

**Disk Space Pre-Flight Checks**:

All pipelines check available disk space before processing (v0.2.0). If free space is below `min_free_disk_gb`, the pipeline aborts with:

```
DiskSpaceError: Insufficient disk space: 8GB available, 10GB required
```

**Override for testing**:

```bash
# Warning: May cause disk full errors
SDC_DISK__MIN_FREE_SPACE_GB=1
```

### Performance Tuning Quick Start

**New in v0.2.0**: Comprehensive performance tuning across multiple subsystems.

Performance optimization is covered across several specialized guides. Use this decision tree to navigate to the right documentation:

**Decision Tree: What's Slow?**

```
Is the pipeline slow?
├─ YES: Network requests timing out?
│   ├─ YES → Increase timeouts (see below: HTTP Timeout Tuning)
│   └─ NO → Database queries slow?
│       ├─ YES → Tune database (see: Database Performance Tuning)
│       └─ NO → High memory usage?
│           ├─ YES → Reduce memory (see: Memory Tuning)
│           └─ NO → CPU-bound processing?
│               └─ YES → Increase buffer sizes (see: Buffer Size Tuning)
└─ NO: Out of memory errors?
    └─ YES → See Memory Tuning below
```

**HTTP Timeout Tuning**:

| Problem | Symptom | Solution | Guide |
|---------|---------|----------|-------|
| Network slow | `TimeoutError: Connection timed out` | Increase `SDC_HTTP__REQUEST_TIMEOUT` | [Troubleshooting](troubleshooting.md#http-requests-timing-out) |
| Large responses | `ReadTimeout: Read timed out` | Increase timeout + buffer size | This section + [Memory Optimization](memory-optimization.md#buffer-size-tuning) |

**Quick fix**:
```bash
export SDC_HTTP__REQUEST_TIMEOUT=60  # Increase from default 30s
```

**Database Performance Tuning**:

| Problem | Symptom | Solution | Guide |
|---------|---------|----------|-------|
| Query timeout | `OperationalError: query timeout` | Increase `SDC_DB__QUERY_TIMEOUT` | [PostgreSQL Setup](../operations/postgres-setup.md#query-timeout-configuration) |
| Connection pool exhausted | `PoolError: Connection pool is full` | Increase pool size | [PostgreSQL Setup](../operations/postgres-setup.md#connection-pool-management) |
| Slow queries | General slowness | Add indexes, optimize queries | [PostgreSQL Setup](../operations/postgres-setup.md#performance-optimization) |

**Quick fix**:
```bash
export SDC_DB__QUERY_TIMEOUT=60     # Increase from default 30s
export SDC_DB__POOL_SIZE=10         # Increase from default 5
```

**Memory Tuning**:

| Problem | Symptom | Solution | Guide |
|---------|---------|----------|-------|
| Out of memory | `MemoryError` | Reduce buffer/batch sizes, enable LRU | [Memory Optimization](memory-optimization.md) |
| Dedup cache too large | Memory grows unbounded | Configure LRU cache size | [Memory Optimization](memory-optimization.md#memory-bounded-deduplication-lruhashset) |
| XML parsing memory spike | High memory during parsing | Reduce buffer size | [Memory Optimization](memory-optimization.md#buffer-size-tuning) |

**Quick fix**:
```bash
export SDC_PARSING__BUFFER_SIZE_MB=5           # Reduce from default 10 MB
export DEDUP_CACHE_SIZE=10000                  # Reduce from default 100K
export SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=50  # Reduce from default 100
```

**Buffer Size Tuning**:

| Problem | Symptom | Solution | Guide |
|---------|---------|----------|-------|
| Slow parsing | Low throughput (< 1000 articles/sec) | Increase buffer size | [Memory Optimization](memory-optimization.md#buffer-size-tuning) |
| High memory but slow | Memory high but still slow | Balance buffer with batch size | [Memory Optimization](memory-optimization.md#buffer-size-tuning) |

**Quick fix**:
```bash
export SDC_PARSING__BUFFER_SIZE_MB=20  # Increase from default 10 MB (requires sufficient RAM)
```

**Comprehensive Tuning Checklist**:

For production deployment, tune all performance settings together:

```bash
# High-performance configuration (16+ GB RAM)
export SDC_HTTP__REQUEST_TIMEOUT=30
export SDC_DB__QUERY_TIMEOUT=30
export SDC_DB__POOL_SIZE=10
export SDC_DB__MAX_OVERFLOW=20
export SDC_PARSING__BUFFER_SIZE_MB=20
export SDC_DISK__MIN_FREE_SPACE_GB=20
export DEDUP_CACHE_SIZE=500000
export SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=200
export SDC_SCRAPING__WIKIPEDIA__BUFFER_LIMIT_MB=20

# Low-resource configuration (< 4 GB RAM)
export SDC_HTTP__REQUEST_TIMEOUT=60
export SDC_DB__QUERY_TIMEOUT=60
export SDC_DB__POOL_SIZE=2
export SDC_DB__MAX_OVERFLOW=5
export SDC_PARSING__BUFFER_SIZE_MB=5
export SDC_DISK__MIN_FREE_SPACE_GB=5
export DEDUP_CACHE_SIZE=10000
export SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=50
export SDC_SCRAPING__WIKIPEDIA__BUFFER_LIMIT_MB=5
```

**Performance Monitoring**:

Monitor these metrics during pipeline runs:

```bash
# Memory usage
watch -n 1 'ps aux | grep python | grep somali'

# Disk I/O
iostat -x 1

# Network throughput
iftop

# Database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='somali_nlp';"
```

**Specialized Guides**:

For deep dives into specific subsystems:

| Subsystem | Guide | Topics Covered |
|-----------|-------|----------------|
| **Memory** | [Memory Optimization](memory-optimization.md) | LRU cache, streaming parsing, buffer tuning, batch sizes |
| **Database** | [PostgreSQL Setup](../operations/postgres-setup.md) | Connection pools, query timeouts, indexes, VACUUM |
| **Network** | [Troubleshooting](troubleshooting.md) | HTTP timeouts, retry logic, rate limiting |
| **Debugging** | [Troubleshooting](troubleshooting.md) | General performance issues, profiling |

**See Also**:
- [PerformanceConfig](#performanceconfig-new-in-v020) - Full configuration reference
- [Memory Optimization Guide](memory-optimization.md) - Memory tuning deep dive
- [PostgreSQL Setup](../operations/postgres-setup.md) - Database performance tuning
- [Troubleshooting Guide](troubleshooting.md) - Performance debugging

## Programmatic Access

### Basic Usage

```python
from somali_dialect_classifier.config import get_config

# Load configuration (reads .env + environment variables)
config = get_config()

# Access nested configuration
print(config.data.raw_dir)              # Path('data/raw')
print(config.scraping.bbc.max_articles)  # None
print(config.logging.level)             # 'INFO'
```

### Reload Configuration

```python
# Initial load
config = get_config()

# Change environment variable at runtime
import os
os.environ['SDC_LOGGING__LEVEL'] = 'DEBUG'

# Reload to pick up changes
config = get_config(reload=True)
print(config.logging.level)  # 'DEBUG'
```

### Reset to Defaults (Testing)

```python
from somali_dialect_classifier.config import reset_config

# Reset global config state
reset_config()

# Next get_config() call will reload from defaults + env
config = get_config()
```

### Access Specific Sections

```python
from somali_dialect_classifier.config import get_config

config = get_config()

# Data paths
raw_dir = config.data.raw_dir
silver_dir = config.data.silver_dir

# Scraping config
bbc_config = config.scraping.bbc
max_articles = bbc_config.max_articles
delay_range = (bbc_config.min_delay, bbc_config.max_delay)

# Logging
log_level = config.logging.level
```

### Type Safety

```python
# Pydantic validates types automatically
config.scraping.bbc.max_articles = "invalid"  # ValidationError!
config.scraping.bbc.max_articles = 100        # OK
config.scraping.bbc.max_articles = None       # OK (Optional[int])
```

### Configuration Startup Logging

**New in v0.2.0**: All pipelines log configuration summaries at startup for debugging and audit trails.

**What Gets Logged**:

At pipeline initialization, the following configuration sections are logged:

```
INFO [2026-01-06 10:30:45] Configuration loaded:
  Data paths:
    raw_dir: data/raw
    silver_dir: data/processed/silver
    staging_dir: data/staging

  Scraping (BBC):
    max_articles: 100
    delay_range: (3, 6)
    timeout: 30

  Performance:
    request_timeout: 30
    query_timeout: 30
    buffer_size_mb: 10
    min_free_disk_gb: 10

  Database:
    host: localhost
    port: 5432
    database: somali_nlp
    password: [REDACTED]  # Sensitive values masked
```

**Why Configuration is Logged**:

1. **Debugging**: Quickly verify which settings are active (especially in production)
2. **Audit Trail**: Record which configuration was used for each pipeline run
3. **Reproducibility**: Enable exact replication of pipeline runs from logs
4. **Validation**: Confirm environment variables were loaded correctly

**Security - Automatic Redaction**:

Sensitive configuration values are **automatically redacted** before logging:

| Field Pattern | Redaction | Example |
|--------------|-----------|---------|
| `*password*` | `[REDACTED]` | `password: [REDACTED]` |
| `*api_key*` | `[REDACTED]` | `apify_api_token: [REDACTED]` |
| `*token*` | `[REDACTED]` | `github_token: [REDACTED]` |
| `*secret*` | `[REDACTED]` | `jwt_secret: [REDACTED]` |

Redaction logic is implemented in `src/somali_dialect_classifier/infra/logging_utils.py`. For full details, see [Security Hardening Guide](security-hardening.md#log-redaction).

**Disabling Startup Logging**:

If startup logs are too verbose or not needed:

```bash
# Disable configuration logging
export SDC_LOGGING__LOG_CONFIG_ON_STARTUP=false

# Or in .env file
SDC_LOGGING__LOG_CONFIG_ON_STARTUP=false
```

**Default**: Startup logging is **enabled** by default (`true`).

**Error Handling**:

If configuration logging fails (e.g., due to serialization errors), the pipeline **continues execution** to prevent logging issues from blocking data processing.

```python
# Implementation detail (for reference)
try:
    logger.info(f"Configuration loaded: {sanitize_config(config)}")
except Exception as e:
    # Log warning but don't fail pipeline startup
    logger.warning(f"Failed to log configuration: {e}")
```

**Where Startup Logs Appear**:

| Output | Location | Format |
|--------|----------|--------|
| **Console (stdout)** | Terminal output | Human-readable text |
| **Log file** | `logs/somali_nlp_{timestamp}.log` | Structured JSON (if configured) |
| **Metrics file** | `data/metrics/{run_id}_processing.json` | Not included (only runtime metrics) |

**Troubleshooting with Startup Logs**:

**Problem**: Pipeline uses wrong data directory

**Solution**: Check startup logs to verify `data.raw_dir` value:

```bash
# Run pipeline with verbose logging
SDC_LOGGING__LEVEL=DEBUG wikisom-download 2>&1 | grep "Configuration loaded" -A 20

# Expected output:
# INFO [2026-01-06 10:30:45] Configuration loaded:
#   Data paths:
#     raw_dir: /custom/path/raw  # Verify this matches expectation
```

**Problem**: HTTP timeouts despite increasing `SDC_HTTP__REQUEST_TIMEOUT`

**Solution**: Confirm environment variable was loaded:

```bash
export SDC_HTTP__REQUEST_TIMEOUT=60
wikisom-download 2>&1 | grep "request_timeout"

# Expected output:
#   Performance:
#     request_timeout: 60  # Should match exported value
```

**Example Startup Log Output**:

```
INFO [2026-01-06 10:30:45] Starting Wikipedia Somali processor
INFO [2026-01-06 10:30:45] Configuration loaded:
  Data paths:
    raw_dir: data/raw
    silver_dir: data/processed/silver
    staging_dir: data/staging
    processed_dir: data/processed
    metrics_dir: data/metrics

  Scraping (Wikipedia):
    batch_size: 100
    max_articles: None
    buffer_limit_mb: 10

  Performance:
    request_timeout: 30
    query_timeout: 30
    buffer_size_mb: 10
    min_free_disk_gb: 10
    connection_pool_size: 5
    max_pool_overflow: 10

  Database:
    host: localhost
    port: 5432
    database: somali_nlp
    user: somali_user
    password: [REDACTED]
    pool_size: 5
    max_overflow: 10
    query_timeout: 30

  Logging:
    level: INFO
    format: structured
    log_config_on_startup: true

INFO [2026-01-06 10:30:46] Pre-flight disk space check: 45GB available (required: 10GB)
INFO [2026-01-06 10:30:46] Initializing crawl ledger (SQLite)
INFO [2026-01-06 10:30:46] Starting extraction phase...
```

**See Also**:
- [Security Hardening Guide](security-hardening.md#log-redaction) - Full redaction implementation details
- [Troubleshooting Guide](troubleshooting.md) - Using logs for debugging
- [Operations Runbook](../operations/runbook.md) - Production startup checklist

## Environment-Specific Configs

### Development Environment

Create `.env` in project root:

```bash
# .env (development)
SDC_LOGGING__LEVEL=DEBUG
SDC_SCRAPING__BBC__MAX_ARTICLES=10
SDC_SCRAPING__BBC__MIN_DELAY=1.0
SDC_SCRAPING__BBC__MAX_DELAY=2.0
SDC_DATA__RAW_DIR=data/raw
SDC_DATA__SILVER_DIR=data/processed/silver
```

**Run**:
```bash
# .env is automatically loaded
python -m somali_dialect_classifier.cli.download_bbcsom
```

### Production Environment

Use environment variables (do NOT commit production `.env` to git):

```bash
# Export in shell or set in systemd/k8s/etc
export SDC_LOGGING__LEVEL=INFO
export SDC_LOGGING__LOG_DIR=/var/log/somali-nlp
export SDC_DATA__RAW_DIR=/mnt/storage/bronze
export SDC_DATA__SILVER_DIR=/mnt/storage/silver
export SDC_SCRAPING__BBC__MIN_DELAY=2.0
export SDC_SCRAPING__BBC__MAX_DELAY=5.0
export SDC_SCRAPING__BBC__USER_AGENT="SomaliNLP/1.0 (+https://example.com)"

# Run pipeline
bbcsom-download --max-articles 1000
```

### Docker Environment

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app
RUN pip install -e .

# Default environment (can be overridden)
ENV SDC_DATA__RAW_DIR=/data/raw
ENV SDC_DATA__SILVER_DIR=/data/silver
ENV SDC_LOGGING__LOG_DIR=/logs

CMD ["bbcsom-download"]
```

**docker-compose.yml**:
```yaml
version: '3.8'
services:
  scraper:
    build: .
    environment:
      - SDC_LOGGING__LEVEL=INFO
      - SDC_SCRAPING__BBC__MAX_ARTICLES=1000
      - SDC_DATA__RAW_DIR=/data/raw
      - SDC_DATA__SILVER_DIR=/data/silver
    volumes:
      - ./data:/data
      - ./logs:/logs
```

**Run**:
```bash
docker-compose up
```

### Cloud Deployment (AWS)

**EC2 User Data Script**:
```bash
#!/bin/bash
# /etc/profile.d/somali-nlp-config.sh

export SDC_DATA__RAW_DIR=/mnt/efs/bronze
export SDC_DATA__SILVER_DIR=/mnt/efs/silver
export SDC_LOGGING__LOG_DIR=/var/log/somali-nlp
export SDC_LOGGING__LEVEL=INFO
export SDC_SCRAPING__BBC__MIN_DELAY=2.0
export SDC_SCRAPING__BBC__MAX_DELAY=5.0
```

**AWS Systems Manager Parameter Store**:
```bash
# Store sensitive config in SSM
aws ssm put-parameter \
  --name /somali-nlp/scraping/user-agent \
  --value "SomaliNLP/1.0 (+https://example.com)" \
  --type String

# Retrieve in application
aws ssm get-parameter --name /somali-nlp/scraping/user-agent --query Parameter.Value
```

## Security Best Practices

### 1. Never Commit Secrets

**Bad**:
```bash
# .env (DO NOT COMMIT)
SDC_SCRAPING__API_KEY=sk-1234567890abcdef
```

**Good**:
```bash
# .env.example (commit this template)
SDC_SCRAPING__API_KEY=your-api-key-here

# .gitignore (commit this)
.env
.env.local
.env.*.local
```

### 2. Use Secret Management Tools

**Development**:
```bash
# Use direnv for project-specific env vars
# .envrc (gitignored)
export SDC_SCRAPING__API_KEY=$(pass show somali-nlp/api-key)
```

**Production**:
- **AWS**: Use AWS Secrets Manager or SSM Parameter Store
- **GCP**: Use Secret Manager
- **Azure**: Use Key Vault
- **Kubernetes**: Use Secrets with RBAC

### 3. Validate Configuration at Startup

```python
from somali_dialect_classifier.config import get_config

config = get_config()

# Ensure critical paths exist
config.data.raw_dir.mkdir(parents=True, exist_ok=True)
config.data.silver_dir.mkdir(parents=True, exist_ok=True)
config.logging.log_dir.mkdir(parents=True, exist_ok=True)

# Validate required secrets (if any)
if not config.scraping.bbc.user_agent:
    raise ValueError("SDC_SCRAPING__BBC__USER_AGENT is required in production")
```

### 4. Principle of Least Privilege

```bash
# Read-only access to raw data
chmod 444 data/raw/source=*/date_accessed=*/*

# Write access only to silver and logs
chmod 755 data/processed/silver
chmod 755 logs
```

### 5. Audit Configuration Changes

```python
import logging
from somali_dialect_classifier.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Log configuration on startup (redact secrets)
logger.info(f"Configuration loaded:")
logger.info(f"  raw_dir: {config.data.raw_dir}")
logger.info(f"  silver_dir: {config.data.silver_dir}")
logger.info(f"  log_level: {config.logging.level}")
logger.info(f"  max_articles: {config.scraping.bbc.max_articles}")
# DO NOT log: user_agent, API keys, passwords
```

## Troubleshooting

### Configuration Not Loading

**Problem**: Environment variables not being read

**Solution**:
```bash
# Verify environment variables are set
env | grep SDC_

# Check .env file exists and is readable
ls -la .env
cat .env

# Test configuration loading
python -c "from somali_dialect_classifier.config import get_config; print(get_config().data.raw_dir)"
```

### Pydantic Validation Errors

**Problem**: `ValidationError: 1 validation error for DataConfig`

**Solution**:
```python
# Check types match expectations
export SDC_SCRAPING__BBC__MAX_ARTICLES=100  # int, not "100"
export SDC_SCRAPING__BBC__MIN_DELAY=1.5     # float, not "1.5"

# Use reload to pick up fixes
from somali_dialect_classifier.config import get_config, reset_config
reset_config()
config = get_config()
```

### Path Resolution Issues

**Problem**: Relative paths not working in Docker/production

**Solution**:
```bash
# Use absolute paths in production
export SDC_DATA__RAW_DIR=/data/raw           # Absolute
# NOT: SDC_DATA__RAW_DIR=data/raw            # Relative

# Verify paths are absolute
python -c "from somali_dialect_classifier.config import get_config; print(get_config().data.raw_dir.absolute())"
```

### Pydantic Not Installed

**Problem**: ImportError: No module named 'pydantic'

**Solution**:
```bash
# Install config dependencies
pip install "somali-dialect-classifier[config]"

# Or install manually
pip install pydantic pydantic-settings python-dotenv

# Fallback: If pydantic unavailable, config.py uses dataclass
# (loses validation and .env loading)
```

### Configuration Overrides Not Working

**Problem**: `.env` file changes not reflected

**Solution**:
```python
# Ensure reload=True when testing config changes
from somali_dialect_classifier.config import get_config
config = get_config(reload=True)

# Check configuration loading order
import os
print(f"ENV: {os.environ.get('SDC_LOGGING__LEVEL')}")
print(f"CONFIG: {config.logging.level}")

# Environment variables always win over .env
# .env < Environment Variables
```

### Testing Configuration

**Problem**: Tests interfere with global configuration

**Solution**:
```python
import pytest
from somali_dialect_classifier.config import reset_config, get_config

@pytest.fixture(autouse=True)
def reset_test_config():
    """Reset configuration before each test."""
    reset_config()
    yield
    reset_config()

def test_custom_config():
    import os
    os.environ['SDC_LOGGING__LEVEL'] = 'DEBUG'
    config = get_config(reload=True)
    assert config.logging.level == 'DEBUG'
```

## Related Documentation

- [Architecture Documentation](ARCHITECTURE.md) - System design and patterns
- [API Reference](API_REFERENCE.md) - Programmatic APIs
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Data Pipeline](DATA_PIPELINE.md) - Pipeline architecture

---

**Maintainers**: Somali NLP Contributors
