# Codebase Tour

**A comprehensive walkthrough of the Somali Dialect Classifier project structure, key components, and development workflow.**

**Last Updated:** 2025-11-21

## Quick Navigation

### If you want to...

#### Work on data ingestion
- **Location:** `src/somali_dialect_classifier/ingestion/`
- **Entry point:** `ingestion/base_pipeline.py`
- **Source processors:** `ingestion/processors/*.py`
- **Key files:**
  - `base_pipeline.py` - Abstract pipeline orchestrator
  - `crawl_ledger.py` - URL tracking, quotas, state management
  - `dedup.py` - URL-based deduplication engine
  - `processors/` - Source-specific implementations (Wikipedia, BBC, HuggingFace, Språkbanken, TikTok)
- **Tests:** `tests/preprocessing/`, `tests/test_base_pipeline_contract.py`
- **Docs:** `docs/howto/processing-pipelines.md`, `docs/howto/adding-sources.md`

#### Work on filters and data quality
- **Location:** `src/somali_dialect_classifier/quality/`
- **Key files:**
  - `filters.py` - Filter implementations (min_length, langid, topic_lexicon, etc.)
  - `filter_engine.py` - Filter orchestration and pipeline
  - `filters/catalog.py` - Dynamic filter registry
  - `record_builder.py` - Schema enforcement and validation
  - `silver_writer.py` - Silver dataset Parquet writer
  - `text_cleaners.py` - Text cleaning pipelines (HTML, Wiki markup)
  - `schema_mappers.py` - Schema version mapping
- **Tests:** `tests/test_filters.py`, `tests/quality/`
- **Docs:** `docs/reference/filters.md`, `docs/howto/custom-filters.md`

#### Work on metrics and observability
- **Location:** `src/somali_dialect_classifier/infra/`
- **Key files:**
  - `metrics.py`, `metrics_schema.py` - Metrics collection and schema
  - `metrics_aggregation.py` - Consolidation utilities
  - `config.py` - Configuration management (Pydantic)
  - `data_manager.py` - Data path management
  - `logging_utils.py` - Structured logging
  - `tracking.py` - MLFlow experiment tracking (context-aware)
  - `filter_analysis.py` - Filter analytics
- **CLI:** `somali-tools metrics`
- **Tests:** `tests/infra/`, `tests/utils/test_metrics_aggregation.py`
- **Docs:** `docs/guides/metrics.md`, `docs/guides/mlflow.md`, `docs/reference/metrics-schema.md`

#### Work on dashboards
- **Location:** `dashboard/`
- **Key files:**
  - `dashboard/js/` - ES6 modules (core, data, ui, viz)
  - `dashboard/index.html` - Main entry point
  - `_site/` - Built artifacts (generated, not source)
- **Build:** `somali-tools dashboard build` (CLI) or `src/dashboard/build-site.sh` (shell)
- **Tests:** `tests/dashboard/`
- **Docs:** `dashboard/README.md`, `docs/guides/dashboard.md`

#### Work on CLI tools
- **Location:** `src/somali_dialect_classifier/tools/`
- **Key files:**
  - `cli.py` - Main CLI framework (Click-based)
  - `metrics_commands.py` - Metrics logic (testable library code)
  - `ledger_commands.py` - Ledger operations
  - `data_commands.py` - Data validation
  - `dashboard_commands.py` - Dashboard build/deploy
- **Entry point:** `somali-tools` command
- **Tests:** `tests/tools/`
- **Docs:** `docs/reference/cli-reference.md`

#### Work on orchestration flows
- **Location:** `src/somali_dialect_classifier/orchestration/`
- **Key files:**
  - `flows.py` - Prefect flows for multi-source pipelines
- **CLI:** `somali-orchestrate` command
- **Tests:** `tests/orchestration/`
- **Docs:** `docs/howto/orchestration.md`

#### Work on ML models (Stage 3 - Future)
- **Location:** `src/somali_dialect_classifier/ml/` (scaffolded)
- **Status:** Awaiting gold datasets from Stage 2
- **Planned components:**
  - `datasets.py` - Data loaders for gold datasets
  - `models.py` - Baseline and transformer model definitions
  - `train.py` - Training loops with MLflow/W&B tracking
  - `evaluation.py` - Comprehensive evaluation suite
  - `preprocessing.py` - ML-specific preprocessing
- **Docs:** See `ml/README.md` for Stage 3 implementation plan

---

---

## Table of Contents

- [Quick Navigation](#quick-navigation)
  - [If you want to...](#if-you-want-to)
    - [Work on data ingestion](#work-on-data-ingestion)
    - [Work on filters and data quality](#work-on-filters-and-data-quality)
    - [Work on metrics and observability](#work-on-metrics-and-observability)
    - [Work on dashboards](#work-on-dashboards)
    - [Work on CLI tools](#work-on-cli-tools)
    - [Work on orchestration flows](#work-on-orchestration-flows)
    - [Work on ML models (Stage 3 - Future)](#work-on-ml-models-stage-3-future)
- [Package Organization](#package-organization)
  - [Core Architecture (4 Packages)](#core-architecture-4-packages)
    - [1. `ingestion/` - Data Collection Layer](#1-ingestion-data-collection-layer)
    - [2. `quality/` - Data Quality Layer](#2-quality-data-quality-layer)
    - [3. `infra/` - Infrastructure Layer](#3-infra-infrastructure-layer)
    - [4. `ml/` - Machine Learning Layer (Scaffolded)](#4-ml-machine-learning-layer-scaffolded)
- [Complete Package Tree](#complete-package-tree)
- [Testing](#testing)
  - [Test Structure](#test-structure)
  - [Running Tests](#running-tests)
- [Scripts vs. CLI](#scripts-vs-cli)
  - [Current State (Stage 1.2)](#current-state-stage-12)
  - [CLI Command Groups](#cli-command-groups)
  - [Script Stubs (Deprecated)](#script-stubs-deprecated)
- [Data Flow](#data-flow)
  - [Complete Data Pipeline](#complete-data-pipeline)
- [Configuration](#configuration)
  - [Configuration Management](#configuration-management)
  - [Configuration Hierarchy](#configuration-hierarchy)
- [Common Workflows](#common-workflows)
  - [Adding a New Data Source](#adding-a-new-data-source)
  - [Adding a Custom Filter](#adding-a-custom-filter)
  - [Adding a CLI Command](#adding-a-cli-command)
- [Development Setup](#development-setup)
  - [Quick Start](#quick-start)
  - [Code Quality Checks](#code-quality-checks)
- [Migration Guide](#migration-guide)
  - [Import Path Changes (Stage 1.1)](#import-path-changes-stage-11)
- [Getting Help](#getting-help)

---

## Package Organization

### Core Architecture (4 Packages)

The codebase is organized into **four logical packages** following clean architecture principles:

```
src/somali_dialect_classifier/
├── ingestion/          # Data collection layer
├── quality/            # Data quality layer
├── infra/              # Infrastructure layer
├── ml/                 # Machine learning layer (scaffolded)
```

#### 1. `ingestion/` - Data Collection Layer

**Responsibility:** Acquire raw data from external sources and track ingestion state.

**Contains:**
- Pipeline orchestration (`base_pipeline.py`)
- Source-specific processors (`processors/*.py`)
- Crawl state tracking (`crawl_ledger.py`)
- Deduplication engine (`dedup.py`)
- Raw data models (`raw_record.py`)

**Does NOT contain:**
- Quality filtering (→ `quality/`)
- Schema validation (→ `quality/`)
- Configuration (→ `infra/`)

**Entry Points:**
```python
from somali_dialect_classifier.ingestion import (
    BasePipeline,
    CrawlLedger,
    DedupEngine,
)
from somali_dialect_classifier.ingestion.processors import (
    WikipediaSomaliProcessor,
    BBCSomaliProcessor,
    HuggingFaceSomaliProcessor,
    SprakbankenSomaliProcessor,
    TikTokSomaliProcessor,
)
```

#### 2. `quality/` - Data Quality Layer

**Responsibility:** Enforce data quality standards and transform to silver format.

**Contains:**
- Filter implementations (`filters.py`)
- Filter orchestration (`filter_engine.py`)
- Filter catalog (`filters/catalog.py`)
- Record building (`record_builder.py`)
- Schema enforcement (`record_utils.py`)
- Silver dataset writing (`silver_writer.py`)
- Text cleaning (`text_cleaners.py`)

**Does NOT contain:**
- Ingestion logic (→ `ingestion/`)
- Configuration (→ `infra/`)

**Entry Points:**
```python
from somali_dialect_classifier.quality import (
    FilterEngine,
    RecordBuilder,
    SilverDatasetWriter,
    TextCleaningPipeline,
    min_length_filter,
    langid_filter,
)
```

#### 3. `infra/` - Infrastructure Layer

**Responsibility:** Provide cross-cutting infrastructure services.

**Contains:**
- Configuration management (`config.py`)
- Data path management (`data_manager.py`)
- Metrics collection (`metrics*.py`)
- Manifest generation (`manifest_writer.py`)
- HTTP utilities (`http.py`)
- Logging utilities (`logging_utils.py`)
- MLFlow experiment tracking (`tracking.py`)
- Rate limiting (`rate_limiter.py`)
- Security utilities (`security.py`)

**Does NOT contain:**
- Business logic (→ `ingestion/` or `quality/`)
- ML models (→ `ml/`)

**Entry Points:**
```python
from somali_dialect_classifier.infra import (
    get_config,
    DataManager,
    MetricsCollector,
    HTTPClient,
    get_logger,
)
```

#### 4. `ml/` - Machine Learning Layer (Scaffolded)

**Responsibility:** ML models, training, evaluation (Stage 3 implementation).

**Status:** Scaffolded with README, empty for Stage 3

**Planned Components:**
- Data loaders (`datasets.py`)
- Model definitions (`models.py`)
- Training pipelines (`train.py`)
- Evaluation utilities (`evaluation.py`)

**Entry Points (future):**
```python
from somali_dialect_classifier.ml import (
    DialectDataset,
    DialectClassifier,
    train,
    evaluate,
)
```

---

## Complete Package Tree

```
src/somali_dialect_classifier/
│
├── ingestion/                          # Data collection layer
│   ├── __init__.py                    # Exports: BasePipeline, CrawlLedger, DedupEngine
│   ├── base_pipeline.py               # Abstract pipeline orchestrator (~500 LOC)
│   ├── crawl_ledger.py                # SQLite ledger for state tracking (~1422 LOC)
│   ├── dedup.py                       # URL-based deduplication (~400 LOC)
│   ├── data_processor.py              # Abstract processor interface (~150 LOC)
│   ├── pipeline_setup.py              # Pipeline utilities (~200 LOC)
│   ├── raw_record.py                  # Raw data model (~100 LOC)
│   ├── apify_tiktok_client.py         # TikTok API client (~300 LOC)
│   └── processors/                    # Source-specific processors
│       ├── __init__.py
│       ├── bbc_somali_processor.py           (~800 LOC)
│       ├── wikipedia_somali_processor.py     (~600 LOC)
│       ├── huggingface_somali_processor.py   (~700 LOC)
│       ├── sprakbanken_somali_processor.py   (~750 LOC)
│       └── tiktok_somali_processor.py        (~600 LOC)
│
├── quality/                            # Data quality layer
│   ├── __init__.py                    # Exports: FilterEngine, RecordBuilder, SilverDatasetWriter
│   ├── filters.py                     # Filter implementations (~800 LOC)
│   ├── filter_engine.py               # Filter orchestration (~600 LOC)
│   ├── record_builder.py              # Schema enforcement (~400 LOC)
│   ├── record_utils.py                # Record utilities (~200 LOC)
│   ├── silver_writer.py               # Silver dataset output (~500 LOC)
│   ├── text_cleaners.py               # Text cleaning pipelines (~300 LOC)
│   ├── schema_mappers.py              # Schema version mappers (~250 LOC)
│   └── filters/                       # Filter catalog
│       ├── __init__.py
│       └── catalog.py                 # Dynamic filter registry (~500 LOC)
│
├── infra/                              # Infrastructure layer
│   ├── __init__.py                    # Exports: get_config, DataManager, MetricsCollector
│   ├── config.py                      # Configuration management (~600 LOC)
│   ├── data_manager.py                # Data path management (~400 LOC)
│   ├── http.py                        # HTTP utilities (~200 LOC)
│   ├── logging_utils.py               # Logging utilities (~250 LOC)
│   ├── metrics.py                     # Core metrics collection (~600 LOC)
│   ├── metrics_schema.py              # Metrics schema definitions (~800 LOC)
│   ├── metrics_aggregation.py         # Metrics aggregation logic (~500 LOC)
│   ├── metrics_comparison.py          # Metrics comparison (~400 LOC)
│   ├── metrics_filters.py             # Metrics filtering (~300 LOC)
│   ├── rate_limiter.py                # Rate limiting (~150 LOC)
│   ├── security.py                    # Security utilities (~200 LOC)
│   ├── manifest_writer.py             # Manifest generation (~400 LOC)
│   ├── aggregation.py                 # General aggregation (~300 LOC)
│   ├── filter_analysis.py             # Filter analytics (~350 LOC)
│   ├── tracking.py                    # MLFlow tracking (~200 LOC)
│   └── visualization_aggregator.py    # Viz aggregation (~300 LOC)
│
├── ml/                                 # Machine learning layer (scaffolded)
│   ├── __init__.py                    # Empty (Stage 3)
│   └── README.md                      # Implementation roadmap
│
├── cli/                                # CLI entry points (unchanged)
│   ├── download_wikisom.py
│   ├── download_bbcsom.py
│   ├── download_hfsom.py
│   ├── download_spraksom.py
│   ├── download_tiktoksom.py
│   └── lock_status.py
│
├── tools/                              # Unified CLI (new in Stage 1.2)
│   ├── __init__.py
│   └── cli.py                         # Click-based CLI framework (~700 LOC)
│
├── orchestration/                      # Orchestration flows (unchanged)
│   └── flows.py                       # Prefect flows
│
├── database/                           # Database backends (unchanged)
│   ├── ledger_backend.py
│   └── postgres_backend.py
│
├── deployment/                         # Deployment utilities (unchanged)
│   └── deploy.py
│
├── schema/                             # Schema management (unchanged)
│   └── validation_service.py
│
└── DEPRECATED (backward-compat only):
    ├── preprocessing/                  # Re-exports to ingestion + quality
    │   └── __init__.py                # DeprecationWarning
    ├── pipeline/                       # Re-exports to quality
    │   └── __init__.py                # DeprecationWarning
    └── utils/                          # Re-exports to infra
        └── __init__.py                # DeprecationWarning
```

---

## Testing

### Test Structure

Tests mirror the source structure:

```
tests/
├── ingestion/                 # Ingestion tests
│   ├── test_base_pipeline.py
│   ├── test_crawl_ledger.py
│   └── processors/
│       ├── test_wikipedia.py
│       └── test_bbc.py
│
├── quality/                   # Quality tests
│   ├── test_filters.py
│   ├── test_filter_engine.py
│   └── test_silver_writer.py
│
├── infra/                     # Infrastructure tests
│   ├── test_config.py
│   ├── test_metrics_aggregation.py
│   └── test_data_manager.py
│
├── tools/                     # CLI tests
│   ├── test_cli.py
│   └── test_metrics_commands.py
│
├── dashboard/                 # Dashboard tests
│   └── test_dashboard.py
│
├── fixtures/                  # Test data
│   ├── mini_wiki_dump.xml
│   ├── bbc_articles.json
│   └── test_metrics.json
│
├── test_base_pipeline_contract.py  # Contract tests for all processors
├── test_wikipedia_integration.py   # Wikipedia end-to-end tests
├── test_bbc_integration.py         # BBC end-to-end tests
└── conftest.py                      # Shared fixtures
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific package tests
pytest tests/ingestion/
pytest tests/quality/
pytest tests/infra/

# Run specific test file
pytest tests/test_filters.py -v

# Run with coverage
pytest tests/ --cov=src/somali_dialect_classifier --cov-report=term-missing
```

---

## Scripts vs. CLI

### Current State (Stage 1.2)

- **Prefer CLI:** `somali-tools <command>`
- **Scripts (`scripts/`):** Backward-compat stubs (deprecated)
- **Migration:** Ongoing from scripts → CLI

### CLI Command Groups

```bash
somali-tools metrics consolidate    # Generate consolidated metrics
somali-tools metrics validate        # Validate metrics schema
somali-tools ledger status           # Show ledger database status
somali-tools ledger migrate          # Run database migrations
somali-tools data validate-silver    # Validate silver datasets
somali-tools dashboard build         # Build dashboard site
```

See `docs/reference/cli-reference.md` for complete command reference.

### Script Stubs (Deprecated)

Old scripts remain as compatibility stubs:

```bash
# OLD (deprecated, but still works)
python scripts/generate_consolidated_metrics.py

# NEW (preferred)
somali-tools metrics consolidate
```

---

## Data Flow

### Complete Data Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│ 1. INGESTION: Source-specific data collection               │
│    ingestion/processors/*.py                                 │
│    → download() → extract() → RawRecord iterator             │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. TEXT CLEANING: Markup removal and normalization          │
│    quality/text_cleaners.py                                  │
│    → TextCleaningPipeline.clean()                            │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. QUALITY FILTERING: Validation and enrichment             │
│    quality/filters.py + filter_engine.py                     │
│    → min_length, langid, topic_lexicon filters               │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. RECORD BUILDING: Schema enforcement                      │
│    quality/record_builder.py                                 │
│    → build_silver_record()                                   │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. SILVER WRITING: Parquet output                           │
│    quality/silver_writer.py                                  │
│    → SilverDatasetWriter.write()                             │
└──────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Configuration Management

All configuration managed by `infra/config.py`:

```python
from somali_dialect_classifier.infra import get_config

config = get_config()
print(config.data.raw_dir)
print(config.scraping.bbc.max_articles)
```

### Configuration Hierarchy

1. Default values (in code)
2. `.env` file (if exists)
3. Environment variables (highest priority)

See `docs/howto/configuration.md` for details.

---

## Common Workflows

### Adding a New Data Source

1. Create processor in `ingestion/processors/your_source_processor.py`
2. Extend `BasePipeline` and implement hooks
3. Register filters in `_register_filters()`
4. Create CLI entry point in `cli/download_yoursourcesom.py`
5. Add tests in `tests/ingestion/processors/test_your_source.py`
6. Update `docs/howto/your-source-integration.md`

See `docs/howto/processing-pipelines.md` for complete guide.

### Adding a Custom Filter

1. Define filter function in `quality/filters.py`
2. Follow filter signature: `(text, **kwargs) -> Tuple[bool, Dict]`
3. Register in processor's `_register_filters()` method
4. Add tests in `tests/quality/test_filters.py`
5. Document in `docs/reference/filters.md`

See `docs/howto/custom-filters.md` for complete guide.

### Adding a CLI Command

1. Add command to `tools/cli.py` (or create new group)
2. Extract logic to `tools/*_commands.py` (testable library code)
3. Wire command to library function
4. Add tests in `tests/tools/test_*_commands.py`
5. Document in `docs/reference/cli-reference.md`

See `docs/reference/cli-reference.md` for patterns.

---

## Development Setup

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/somali-dialect-classifier.git
cd somali-dialect-classifier

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
pytest --version
ruff --version
somali-tools --help
```

### Code Quality Checks

```bash
# Lint and format
ruff check --fix src/ tests/
ruff format src/ tests/

# Type check
mypy src/

# Run tests
pytest tests/
```

See `CONTRIBUTING.md` for complete development guide.

---

## Migration Guide

### Import Path Changes (Stage 1.1)

If you have code using old imports:

**OLD (deprecated):**
```python
from somali_dialect_classifier.preprocessing import BasePipeline
from somali_dialect_classifier.pipeline import FilterEngine
from somali_dialect_classifier.utils import get_logger
from somali_dialect_classifier.config import get_config
```

**NEW (current):**
```python
from somali_dialect_classifier.ingestion import BasePipeline
from somali_dialect_classifier.quality import FilterEngine
from somali_dialect_classifier.infra import get_logger, get_config
```

**Backward Compatibility:** Old imports still work with deprecation warnings.

See `docs/guides/module-restructuring.md` for complete migration guide.

---

## Getting Help

- **Documentation Index:** `docs/index.md`
- **Architecture Overview:** `docs/overview/architecture.md`
- **API Reference:** `docs/reference/api.md`
- **Contributing Guide:** `CONTRIBUTING.md`
- **Code Examples:** Look at existing processors (Wikipedia, BBC)
- **Issues:** Search existing issues on GitHub
- **Discussions:** Use GitHub Discussions for questions

---

**Maintainers:** Somali NLP Contributors

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
