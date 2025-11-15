# API Changelog

**Last Updated**: 2025-11-11

This document tracks all API changes, additions, deprecations, and breaking changes across project versions. Use this guide to understand what changed between versions and how to migrate your code.

---

## Version 1.1.0 (2025-11-11) - Production Scale Infrastructure

**Release Highlights:**
- PostgreSQL backend for 10x concurrent scale
- Service-oriented architecture (God Object refactoring)
- Incremental processing for 90%+ efficiency
- DataManager for centralized file I/O
- Enhanced orchestration with distributed locking

### Added

#### Database Backend

**PostgresLedger** - Production-ready PostgreSQL backend
- **Location**: `src/somali_dialect_classifier/database/postgres_ledger.py`
- **Purpose**: Replace SQLite for concurrent write operations
- **Features**:
  - Connection pooling (2-10 connections, ThreadedConnectionPool)
  - Row-level locking (vs SQLite's file-level locking)
  - JSONB metadata support with GIN indexes
  - Transaction rollback support
  - Automatic schema initialization
  - < 100ms query latency (p95)
  - 10x concurrent writes without deadlocks

**Usage:**
```python
from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger

# Auto-selects backend from environment
ledger = CrawlLedger()  # Uses SDC_LEDGER_BACKEND env var

# Explicit PostgreSQL
ledger = CrawlLedger(
    backend_type='postgres',
    host='localhost',
    port=5432,
    database='somali_nlp',
    user='somali',
    password='secure_password'
)
```

**Migration:**
```bash
# Migrate SQLite to PostgreSQL
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/ledger/crawl_ledger.db \
    --postgres-host localhost \
    --postgres-db somali_nlp
```

#### Service Classes (P3.1 Refactoring)

**DataManager** - Centralized file I/O operations
- **Location**: `src/somali_dialect_classifier/data/data_manager.py`
- **Purpose**: Manage all file operations (read/write/list/delete)
- **Features**:
  - Timestamped filenames for lineage tracking
  - Partitioned directory structure (source=*/date_accessed=*)
  - Atomic writes with temp files
  - Cleanup utilities for old files
  - Security validation (path traversal prevention)

**Usage:**
```python
from somali_dialect_classifier.data.data_manager import DataManager

manager = DataManager(source="BBC-Somali", run_id="20251111_143045")

# Write data
manager.write_staging(data, stage="extracted", format="jsonl")
# Output: data/staging/source=BBC-Somali/date_accessed=2025-11-11/
#         bbc-somali_20251111_143045_staging_extracted.jsonl

# Read data
records = manager.read_staging(stage="extracted", format="jsonl")

# List files
files = manager.list_staging_files(stage="extracted")

# Cleanup old files (keep last 5 runs)
manager.cleanup_old_staging_files(stage="extracted", keep=5)
```

**FilterEngine** - Filter execution and statistics
- **Location**: `src/somali_dialect_classifier/pipeline/filter_engine.py`
- **Purpose**: Execute quality filters and track statistics
- **Features**:
  - Register multiple filters
  - Execute filters in order
  - Track pass/fail statistics per filter
  - Human-readable filter labels
  - Exception handling with graceful degradation

**Usage:**
```python
from somali_dialect_classifier.pipeline.filter_engine import FilterEngine
from somali_dialect_classifier.preprocessing.quality_filters import (
    min_length_filter,
    langid_filter
)

engine = FilterEngine()
engine.register_filter(min_length_filter, {"min_chars": 50})
engine.register_filter(langid_filter)

# Apply filters
passed, failed_filter, metadata = engine.apply_filters(
    cleaned_text="Example text",
    record_title="Example title"
)

if passed:
    print("Passed all filters")
else:
    print(f"Failed filter: {failed_filter}")

# Get statistics
stats = engine.get_filter_stats()
# {'min_length_filter': 100, 'langid_filter': 95}

# Get human-readable statistics
readable_stats = engine.get_human_readable_stats()
# {'min_length_filter': ('Minimum Length Filter', 100), ...}
```

**RecordBuilder** - Silver record construction
- **Location**: `src/somali_dialect_classifier/preprocessing/record_builder.py`
- **Purpose**: Build standardized silver dataset records
- **Features**:
  - Consistent record structure across sources
  - Metadata merging from multiple sources
  - Schema versioning fields
  - UUID generation
  - Token counting

**Usage:**
```python
from somali_dialect_classifier.preprocessing.record_builder import RecordBuilder
from somali_dialect_classifier.preprocessing.raw_record import RawRecord

builder = RecordBuilder(source="BBC-Somali")

raw = RawRecord(
    title="Example Article",
    text="Article text...",
    url="https://example.com/article",
    timestamp="2025-11-11T10:00:00Z",
    metadata={"author": "John Doe"}
)

record = builder.build_silver_record(
    raw_record=raw,
    cleaned_text="Cleaned article text...",
    filter_metadata={"detected_lang": "so", "lang_confidence": 0.95},
    source_type="news",
    license_str="BBC Terms of Use",
    domain="news",
    register="formal"
)

# Output: Fully-formed silver record with all required fields
# {
#   "id": "uuid-v4",
#   "text": "Cleaned article text...",
#   "title": "Example Article",
#   "source": "BBC-Somali",
#   "source_type": "news",
#   "language": "so",
#   "license": "BBC Terms of Use",
#   "tokens": 123,
#   "source_metadata": {...}
# }
```

**ValidationService** - Schema validation
- **Location**: `src/somali_dialect_classifier/schema/validation_service.py`
- **Purpose**: Validate records against silver schema
- **Features**:
  - Required field validation
  - Type checking
  - Value constraints
  - Detailed error messages
  - Failure counting

**Usage:**
```python
from somali_dialect_classifier.schema.validation_service import ValidationService

validator = ValidationService()

record = {
    "id": "uuid-v4",
    "text": "Example text",
    "title": "Example",
    "source": "Wikipedia-Somali",
    # ... other fields
}

is_valid, errors = validator.validate_record(record, source="Wikipedia-Somali")

if not is_valid:
    print(f"Validation failed: {errors}")
    # ['Missing required field: language', 'Invalid type for tokens']

# Get total failures
failures = validator.get_failure_count()
print(f"Total validation failures: {failures}")
```

#### HTTP Utilities

**HTTPSessionFactory** - Session management for web scraping
- **Location**: `src/somali_dialect_classifier/utils/http.py`
- **Purpose**: Create configured HTTP sessions with retries and rate limiting
- **Features**:
  - Retry logic with exponential backoff
  - Custom user agent
  - Timeout configuration
  - Rate limiting support
  - Connection pooling

**Usage:**
```python
from somali_dialect_classifier.utils.http import HTTPSessionFactory

# Create session with default settings
session = HTTPSessionFactory.create_session()

# Create session with custom settings
session = HTTPSessionFactory.create_session(
    max_retries=5,
    backoff_factor=1.0,
    timeout=30,
    user_agent="CustomBot/1.0"
)

# Use session
response = session.get("https://example.com")
```

#### Orchestration Enhancements

**Distributed Locking** - Prevent concurrent pipeline runs
- **Added to**: `src/somali_dialect_classifier/preprocessing/crawl_ledger.py`
- **Purpose**: Prevent data corruption from concurrent runs
- **Features**:
  - Acquire/release source locks
  - Lock timeout with automatic release
  - Check if source is locked
  - Lock status tracking in ledger

**Usage:**
```python
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()

# Check if locked
if ledger.is_source_locked("wikipedia"):
    print("Wikipedia pipeline already running")
    exit(1)

# Acquire lock
try:
    lock = ledger.acquire_source_lock("wikipedia", timeout=3600)
    # Run pipeline...
finally:
    ledger.release_source_lock("wikipedia")
```

**Refresh Cadence Logic** - Smart orchestration scheduling
- **Added to**: `src/somali_dialect_classifier/orchestration/flows.py`
- **Purpose**: Run sources based on configured refresh intervals
- **Features**:
  - Per-source cadence configuration
  - Initial collection phase (6 days all sources)
  - Automatic cadence checking
  - Skip sources when cadence not met

**Usage:**
```python
from somali_dialect_classifier.orchestration.flows import (
    should_run_source,
    is_initial_collection_phase
)

# Check if source should run
should_run, reason = should_run_source("bbc")
print(f"BBC should run: {should_run} ({reason})")
# Output: False (refresh_not_due - next in 0.5 days)

# Check if in initial collection phase
if is_initial_collection_phase():
    print("All sources run daily during initial collection")
else:
    print("Sources run per configured cadence")
```

#### Incremental Processing

**Timestamp-based Filtering** - Skip unchanged data (Wikipedia)
- **Added to**: `src/somali_dialect_classifier/preprocessing/wikipedia_somali_processor.py`
- **Purpose**: Only process articles modified since last run
- **Features**:
  - Query ledger for last processing time
  - Filter articles by timestamp
  - 99%+ efficiency on quarterly refreshes
  - Automatic fallback to full processing

**Resource ID Filtering** - Skip processed corpora (Språkbanken)
- **Added to**: `src/somali_dialect_classifier/preprocessing/sprakbanken_somali_processor.py`
- **Purpose**: Only download new corpora
- **Features**:
  - Track processed corpus IDs in ledger
  - Filter requested corpora against processed set
  - 100% efficiency (static corpora)

### Changed

#### BasePipeline Refactoring (P3.1)

**Reduced from 615 lines to 298 lines (52% reduction)**
- **Location**: `src/somali_dialect_classifier/preprocessing/base_pipeline.py`
- **Changes**:
  - Extracted FilterEngine service (filter execution logic)
  - Extracted RecordBuilder service (record construction logic)
  - Extracted ValidationService service (schema validation logic)
  - Delegated file I/O to DataManager (P2.2)
  - Condensed docstrings (moved detailed docs to service classes)
  - Simplified process() method (227 → ~100 lines)
  - Added dependency injection for services

**Migration:**

**Before (v1.0):**
```python
class MyProcessor(BasePipeline):
    def __init__(self):
        super().__init__(source="MySource")
        # Direct access to internal methods
```

**After (v1.1):**
```python
class MyProcessor(BasePipeline):
    def __init__(self):
        super().__init__(source="MySource")
        # Services injected automatically (no changes required)
        # Optional: inject custom services for testing
        # super().__init__(
        #     source="MySource",
        #     filter_engine=custom_filter_engine,
        #     record_builder=custom_record_builder
        # )
```

**Backward Compatibility:** All existing processors work without changes. Services are injected automatically with sensible defaults.

#### Metrics Export Centralization

**Moved from scattered export calls to centralized manager**
- **Changed in**: All processor classes
- **Before**: Each processor exported metrics manually
- **After**: DataManager.export_metrics() centralizes export logic

**Migration:**

**Before (v1.0):**
```python
# Manual metrics export
metrics_path = self.data_manager.get_metrics_path()
with open(metrics_path, 'w') as f:
    json.dump(self.metrics_collector.get_summary(), f, indent=2)
```

**After (v1.1):**
```python
# Centralized export
self.data_manager.export_metrics(self.metrics_collector)
```

#### Configuration Schema Updates

**Added orchestration configuration section**
- **Changed in**: `src/somali_dialect_classifier/config.py`
- **Added fields**:
  - `orchestration.initial_collection_days` (default: 6)
  - `orchestration.bbc_cadence` (default: 1)
  - `orchestration.wikipedia_cadence` (default: 7)
  - `orchestration.tiktok_cadence` (default: 3)
  - `orchestration.sprakbanken_cadence` (default: 30)
  - `orchestration.huggingface_cadence` (default: 30)

**Migration:**

Add to `.env`:
```bash
SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS=6
SDC_ORCHESTRATION__BBC_CADENCE=1
SDC_ORCHESTRATION__WIKIPEDIA_CADENCE=7
# ... etc
```

### Deprecated

#### Direct File I/O in Processors

**Deprecated**: Manual file operations in processor classes
**Replacement**: Use DataManager service

**Migration:**

**Deprecated (v1.0):**
```python
# Direct file I/O
output_path = Path(f"data/staging/source={self.source}/file.jsonl")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    for record in records:
        f.write(json.dumps(record) + '\n')
```

**Recommended (v1.1):**
```python
# Use DataManager
self.data_manager.write_staging(records, stage="extracted", format="jsonl")
```

**Status**: Old code still works but generates deprecation warnings. Will be removed in v2.0.

#### Manual Metrics Export

**Deprecated**: Manual metrics export in process() method
**Replacement**: Use DataManager.export_metrics()

**Migration:**

**Deprecated (v1.0):**
```python
# Manual export
metrics_path = Path(f"data/metrics/{self.source}_metrics.json")
with open(metrics_path, 'w') as f:
    json.dump(self.metrics_collector.get_summary(), f)
```

**Recommended (v1.1):**
```python
# Centralized export
self.data_manager.export_metrics(self.metrics_collector)
```

**Status**: Old code still works. Will be removed in v2.0.

### Removed

None. All v1.0 APIs remain functional in v1.1 (backward compatible).

---

## Version 1.0.0 (2025-11-02) - Initial Production Release

**Release Highlights:**
- Five data source processors (Wikipedia, BBC, HuggingFace, Språkbanken, TikTok)
- Three-tier deduplication (discovery, processing, cross-run)
- Medallion architecture (raw → staging → silver)
- Comprehensive metrics collection
- Pluggable filter framework
- Schema versioning

### Added

#### Core Pipeline Architecture

**BasePipeline** - Abstract base class for all processors
- **Location**: `src/somali_dialect_classifier/preprocessing/base_pipeline.py`
- **Features**:
  - Three-phase processing (download → extract → process)
  - Integrated metrics collection
  - Crawl ledger state tracking
  - Quality filter execution
  - Silver dataset writing
  - Deduplication integration

**DataProcessor Protocol** - Interface for all processors
- **Location**: `src/somali_dialect_classifier/preprocessing/data_processor.py`
- **Purpose**: Define contract for processor implementations

#### Data Source Processors

1. **WikipediaSomaliProcessor** - Wikipedia dump processing
   - Location: `src/somali_dialect_classifier/preprocessing/wikipedia_somali_processor.py`
   - Features: XML parsing, namespace filtering, redirect handling

2. **BBCSomaliProcessor** - BBC Somali news scraping
   - Location: `src/somali_dialect_classifier/preprocessing/bbc_somali_processor.py`
   - Features: RSS feed parsing, ethical rate limiting, topic enrichment

3. **HuggingFaceSomaliProcessor** - HuggingFace dataset streaming
   - Location: `src/somali_dialect_classifier/preprocessing/huggingface_somali_processor.py`
   - Features: Streaming datasets, continuous streaming, JSONL batching

4. **SprakbankenSomaliProcessor** - Språkbanken corpus download
   - Location: `src/somali_dialect_classifier/preprocessing/sprakbanken_somali_processor.py`
   - Features: 66 corpora support, XML token extraction, domain mapping

5. **TikTokSomaliProcessor** - TikTok comment scraping via Apify
   - Location: `src/somali_dialect_classifier/preprocessing/tiktok_somali_processor.py`
   - Features: Apify API integration, comment extraction, video metadata

#### Deduplication System

**Three-Tier Deduplication:**

1. **Discovery-stage dedup** - CrawlLedger URL tracking
   - Prevents redundant downloads
   - Checks if URL already processed

2. **Processing-stage dedup** - Hash-based exact duplicate detection
   - SHA256 text hashing
   - Within-run duplicate detection

3. **Cross-run dedup** - MinHash LSH near-duplicate detection
   - 80% similarity threshold
   - Jaccard similarity computation
   - Scales to millions of documents

**Classes:**
- `TextHasher` - SHA256 hashing utilities
- `MinHashDeduplicator` - LSH-based near-duplicate detection

#### Filter Framework

**Quality Filters:**

1. **min_length_filter** - Reject short texts (< 50 chars)
2. **langid_filter** - Heuristic Somali language detection
3. **topic_lexicon_enrichment_filter** - Topic marker enrichment (renamed from dialect_heuristic_filter)
4. **namespace_filter** - Wikipedia namespace validation (articles only)

**Filter Registration:**
```python
from somali_dialect_classifier.preprocessing.quality_filters import (
    min_length_filter,
    langid_filter
)

processor.register_filter(min_length_filter, min_chars=50)
processor.register_filter(langid_filter)
```

#### Metrics Collection

**MetricsCollector** - Comprehensive metrics tracking
- **Location**: `src/somali_dialect_classifier/metrics/metrics_collector.py`
- **Metrics**:
  - Records processed/filtered/written
  - Processing time and throughput
  - Quality filter statistics (per-filter breakdown)
  - Deduplication statistics
  - Error counts and types
  - Source-specific metrics

**Export:**
```python
collector = MetricsCollector(source="Wikipedia-Somali")
collector.increment_records_processed(100)
collector.increment_records_filtered(10, "min_length_filter")

summary = collector.get_summary()
# Exported to: data/metrics/source=Wikipedia-Somali/metrics.json
```

#### Schema System

**Silver Dataset Schema** - Standardized output format
- **Location**: `src/somali_dialect_classifier/schema/silver_schema.py`
- **Fields**:
  - `id` (UUID v4)
  - `text` (cleaned text)
  - `title` (article/document title)
  - `source` (data source identifier)
  - `source_type` (wiki, news, web, corpus)
  - `language` (so)
  - `license` (data license)
  - `tokens` (token count)
  - `source_metadata` (quality metrics, dialect markers)

**Schema Versioning:**
- Version: 1.0.0
- Tracking: `schema_version` field in all records
- Validation: Automatic validation before writing

#### Crawl Ledger

**SQLiteLedger** - Persistent state tracking
- **Location**: `src/somali_dialect_classifier/preprocessing/crawl_ledger.py`
- **Features**:
  - URL state tracking (discovered → fetched → processed)
  - RSS feed tracking (last_crawled timestamps)
  - Retry logic (backoff for failed URLs)
  - Statistics and reporting
  - Duplicate detection integration (text_hash, minhash_signature)

**States:**
- `discovered` - URL found but not downloaded
- `fetched` - Downloaded but not processed
- `processed` - Fully processed and written to silver
- `failed` - Processing failed (with retry logic)
- `duplicate` - Duplicate detected (skipped)

#### Configuration Management

**Settings** - Pydantic-based configuration
- **Location**: `src/somali_dialect_classifier/config.py`
- **Sections**:
  - `data` - Data directory paths
  - `scraping` - Per-source scraping settings
  - `logging` - Logging configuration
  - `deduplication` - Deduplication thresholds
  - `quality` - Quality filter settings

**Usage:**
```python
from somali_dialect_classifier.config import get_config

config = get_config()
print(config.data.raw_dir)
print(config.scraping.bbc.max_articles)
```

---

## Migration Guides

### Migrating from v1.0 to v1.1

#### 1. PostgreSQL Migration (Optional but Recommended)

**Why**: 10x concurrent scale, row-level locking, production-ready

**Steps:**

1. Install dependencies:
   ```bash
   pip install psycopg2-binary sqlalchemy filelock
   ```

2. Start PostgreSQL:
   ```bash
   docker-compose --profile prod up -d postgres
   ```

3. Configure environment:
   ```bash
   export SDC_LEDGER_BACKEND=postgres
   export POSTGRES_HOST=localhost
   export POSTGRES_DB=somali_nlp
   export POSTGRES_USER=somali
   export POSTGRES_PASSWORD="<secure_password>"
   ```

4. Migrate data:
   ```bash
   python scripts/migrate_sqlite_to_postgres.py \
       --sqlite data/ledger/crawl_ledger.db \
       --postgres-host localhost \
       --postgres-db somali_nlp
   ```

5. Test:
   ```bash
   wikisom-download --limit 10
   ```

**Rollback**: Change `SDC_LEDGER_BACKEND=sqlite` (instant rollback, no data loss)

#### 2. Service-Based Architecture (Automatic)

**No code changes required**. Services are injected automatically:

- FilterEngine
- RecordBuilder
- ValidationService
- DataManager

**For testing** (optional): Inject mock services:

```python
from unittest.mock import Mock
from somali_dialect_classifier.pipeline.filter_engine import FilterEngine

mock_engine = Mock(spec=FilterEngine)
processor = BBCSomaliProcessor(filter_engine=mock_engine)
```

#### 3. Orchestration Configuration (Required for Smart Scheduling)

Add to `.env`:

```bash
SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS=6
SDC_ORCHESTRATION__BBC_CADENCE=1
SDC_ORCHESTRATION__WIKIPEDIA_CADENCE=7
SDC_ORCHESTRATION__TIKTOK_CADENCE=3
SDC_ORCHESTRATION__SPRAKBANKEN_CADENCE=30
SDC_ORCHESTRATION__HUGGINGFACE_CADENCE=30
```

**Default values** apply if not configured.

#### 4. Update File I/O (Recommended)

Replace direct file operations with DataManager:

**Before:**
```python
output_path = Path("data/staging/file.jsonl")
with open(output_path, 'w') as f:
    json.dump(data, f)
```

**After:**
```python
self.data_manager.write_staging(data, stage="extracted", format="jsonl")
```

**Status**: Old code still works with deprecation warnings.

---

## Breaking Changes

### v1.1.0

**None**. All v1.0 APIs remain functional. New features are additive.

### v1.0.0

**Initial release** - no breaking changes.

---

## Deprecation Timeline

| Feature | Deprecated In | Removed In | Replacement |
|---------|--------------|------------|-------------|
| Direct file I/O in processors | v1.1.0 | v2.0.0 | DataManager |
| Manual metrics export | v1.1.0 | v2.0.0 | DataManager.export_metrics() |

---

## Version Support Policy

- **Current version**: v1.1.0 (fully supported)
- **Previous version**: v1.0.0 (security fixes only)
- **Deprecation period**: 6 months minimum
- **Breaking changes**: Major version only (v2.0.0+)

---

## API Stability Guarantees

- **Public APIs** (documented in API Reference): Stable within major version
- **Internal APIs** (prefixed with `_`): No stability guarantees
- **Experimental features**: Marked explicitly, subject to change

---

## References

- [API Reference](api.md) - Complete API documentation
- [PostgreSQL Deployment](../operations/postgres-deployment.md) - PostgreSQL setup guide
- [Orchestration Guide](../howto/orchestration.md) - Pipeline orchestration
- [Incremental Processing](../howto/incremental-processing.md) - Efficiency features

---

**Version**: 1.0
**Last Updated**: 2025-11-11
**Maintainer**: API Documentation Team
