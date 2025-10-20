# Somali Dialect Classifier

**A production-ready data pipeline for collecting, processing, and preparing Somali language text from multiple sources for dialect classification and NLP research.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-165%2B%20passing-success)](tests/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dashboard](https://img.shields.io/badge/📊_Dashboard-Live-blue)](https://somali-nlp.github.io/somali-dialect-classifier/)

## 📊 Live Dashboard

**[View Interactive Dashboard →](https://somali-nlp.github.io/somali-dialect-classifier/)**

Real-time metrics, quality reports, and pipeline performance monitoring. See data engineering in action!

## Project Status

**Phase 0 (Foundation):** ✅ Complete - Production-ready MLOps infrastructure INTEGRATED into all processors
**Phase 1 (Data Curation):** ✅ Complete - 4 data sources with Phase 0 integration
**Current Phase:** Data labeling and annotation (Phase 2) preparation
**Dataset Size:** 130,000-300,000 deduplicated Somali text records

## Features

### Four Production Data Sources

All sources integrated with Phase 0 MLOps infrastructure:

1. **Wikipedia-Somali** - ~50,000 encyclopedic articles
2. **BBC-Somali** - News articles with ethical web scraping
3. **HuggingFace MC4** - ~100,000-200,000 web documents
4. **Språkbanken** - 23 academic corpora from University of Gothenburg

### Integrated MLOps Infrastructure

**All processors include:**

- **Structured Logging** - JSON logs with automatic context (run_id, source, phase, hostname)
- **Metrics Collection** - Discovery, fetch, processing metrics with automated quality reports
- **Crawl Ledger** - Persistent URL state tracking with conditional requests
- **Deduplication** - Exact SHA256 hashing + MinHash LSH for near-duplicates
- **Configuration** - YAML-based config with ethical scraping policies
- **Quality Reports** - Automated health assessments with recommendations

[See complete Phase 0 features →](docs/overview/phase-0-architecture.md)

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd somali-dialect-classifier

# Install in editable mode for development
pip install -e .

# Install with development tools (recommended for contributors)
pip install -e ".[dev]"

# Install with configuration management (includes Phase 0 features)
pip install -e ".[config]"

# Install with MLOps tools (MLflow, W&B, Prefect)
pip install -e ".[mlops]"

# Install with ML libraries (PyTorch, Transformers)
pip install -e ".[ml]"

# Install everything
pip install -e ".[all]"
```

## Usage

### Orchestrated Execution (Recommended)

Run all pipelines together with parallel execution:

```bash
# Run all pipelines
somali-orchestrate --pipeline all

# Run specific pipeline
somali-orchestrate --pipeline wikipedia
somali-orchestrate --pipeline bbc --max-bbc-articles 500

# With limits
somali-orchestrate --pipeline all --max-bbc-articles 500 --max-hf-records 10000
```

### Individual Pipelines

#### Wikipedia

```bash
wikisom-download
# or: python -m somali_dialect_classifier.cli.download_wikisom
```

#### BBC Somali News

```bash
bbcsom-download --max-articles 500
# or: python -m somali_dialect_classifier.cli.download_bbcsom
```

**Features**: RSS feeds (primary), web scraping (fallback), adaptive rate limiting, conditional requests, respects robots.txt

#### HuggingFace Datasets

```bash
# Process MC4 (Multilingual C4) dataset
hfsom-download mc4 --max-records 10000

# Process full MC4 dataset (no limit)
hfsom-download mc4

# Force reprocessing
hfsom-download mc4 --force

# Custom HuggingFace dataset (advanced)
hfsom-download custom --dataset-name allenai/gdelt --config so
```

**Supported Datasets**:
- **mc4**: Multilingual C4 (~100k-200k Somali records, web crawl, ODC-BY-1.0) ✅ **ACTIVE**
- **custom**: Any HuggingFace dataset with field mapping

**Note**: OSCAR and MADLAD-400 have been excluded from this project. See [ADR-001](docs/decisions/001-oscar-exclusion.md) and [ADR-003](docs/decisions/003-madlad-400-exclusion.md) for details.

**Features**:
- Streaming mode for large datasets (no memory limits)
- JSONL batching with resume capability (5k records/batch)
- Manifest-based versioning for reproducibility
- Quality filters applied automatically

See [HuggingFace Datasets Guide](docs/howto/huggingface-integration.md) for complete documentation.

### Download and Process Språkbanken Corpora

```bash
# List all available corpora
python -m somali_dialect_classifier.cli.download_sprakbankensom --list

# Show info about specific corpus
python -m somali_dialect_classifier.cli.download_sprakbankensom --info ogaden

# Download and process specific corpus
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus cilmi

# Download and process ALL 23 corpora
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all

# Force reprocessing
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all --force
```

**Available Corpora (23 total)**:
- **News**: as-2001, as-2016, ah-2010-19, cb variants (6 corpora)
- **Literature**: sheekooyin, suugaan variants (4 corpora)
- **Science**: cilmi, saynis-1980-89 (2 corpora)
- **Health**: caafimaad-1972-79 (1 corpus)
- **Children**: sheekooyin-carruureed (1 corpus)
- **Radio**: radioden2014, radioswe2014 (2 corpora)
- **Regional**: ogaden (Ogaden region news) (1 corpus)
- **Translation**: turjuman variants (2 corpora)
- **Historical**: 1971-79, 1993-94, 2001, mk-1972-79 (4 corpora)
- **QA**: kqa (question-answer) (1 corpus)

**Features**:
- 23 domain-diverse Somali corpora from University of Gothenburg
- Rich metadata (dates, authors, publishers, genres, regions)
- All licensed under CC BY 4.0
- Domain-specific content (news, literature, science, health, radio, etc.)
- Automatic domain classification and tagging
- **Easy corpus querying**: All records use source="Sprakbanken-Somali" with corpus_id in source_id field

**Querying Språkbanken Records**:

```python
import pyarrow.parquet as pq

# Read silver dataset
table = pq.read_table("data/processed/silver/source=Sprakbanken-Somali/")

# Filter by specific corpus
cilmi_records = table.filter(
    (table.column("source") == "Sprakbanken-Somali") &
    (table.column("source_id") == "cilmi")
)

# Filter by domain
news_records = table.filter(table.column("domain") == "news")

# Combine filters: science corpus with high token count
science_long = table.filter(
    (table.column("source_id") == "cilmi") &
    (table.column("tokens") > 500)
)
```

See [Språkbanken Integration Guide](docs/howto/sprakbanken-integration.md) for complete documentation.

### Force Reprocessing

By default, pipelines skip existing files to avoid redundant work. To force rebuild:

```bash
# Force Wikipedia reprocessing
wikisom-download --force

# Force BBC reprocessing
bbcsom-download --force

# Force HuggingFace reprocessing
hfsom-download mc4 --force

# Or programmatically
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor
processor = WikipediaSomaliProcessor(force=True)
processor.process()
```

### Data Directory Structure

After running the pipelines, data will be organized with **timestamped filenames** for full traceability:

```
data/
├── raw/
│   ├── source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/
│   │   └── sowiki-latest-pages-articles.xml.bz2
│   └── source=BBC-Somali/date_accessed=YYYY-MM-DD/
│       ├── bbc-somali_20251020_150230_raw_article-links.json
│       └── bbc-somali_20251020_150230_raw_article-0001.json
├── staging/
│   ├── source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/
│   │   └── wikipedia-somali_20251020_143045_staging_extracted.txt
│   └── source=BBC-Somali/date_accessed=YYYY-MM-DD/
│       └── bbc-somali_20251020_150230_staging_articles.jsonl
├── processed/
│   ├── source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/
│   │   └── wikipedia-somali_20251020_143045_processed_cleaned.txt
│   └── source=BBC-Somali/date_accessed=YYYY-MM-DD/
│       └── bbc-somali_20251020_150230_processed_cleaned.txt
└── processed/silver/
    ├── source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/
    │   ├── wikipedia-somali_20251020_143045_silver_part-0000.parquet
    │   └── wikipedia-somali_20251020_143045_silver_metadata.json
    └── source=BBC-Somali/date_accessed=YYYY-MM-DD/
        ├── bbc-somali_20251020_150230_silver_part-0000.parquet
        └── bbc-somali_20251020_150230_silver_metadata.json
```

**File Naming Pattern**: `{source-slug}_{run_id}_{layer}_{descriptive-name}[_{partition}].{ext}`
- `source-slug`: Lowercase hyphenated (e.g., `wikipedia-somali`, `bbc-somali`, `hf-mc4-so`)
- `run_id`: Timestamp format `YYYYMMDD_HHMMSS` (e.g., `20251020_143045`)
- `layer`: `raw`, `staging`, `processed`, `silver`
- `descriptive-name`: Purpose-specific (e.g., `manifest`, `extracted`, `articles`, `cleaned`, `part-0000`)

**Key Features**:
- ✅ **Run ID Traceability**: Every file includes timestamp for complete lineage tracking
- ✅ **No Overwrites**: Multiple runs on same day never collide
- ✅ **Partition Consistency**: All layers use `date_accessed` (no more `date_processed` inconsistency)
- ✅ **Schema Enforcement**: Same silver dataset schema across all sources
- ✅ **Metadata Sidecars**: Silver layer includes JSON metadata with checksums and statistics
- ✅ **MLOps Ready**: Compatible with data catalogs, DVC, and automated pipelines

### Logs

Pipeline logs are stored with automatic rotation (5MB max, 3 backups):
- Wikipedia: `logs/download_wikisom.log`
- BBC: `logs/download_bbcsom.log`

## Development

### Project Structure

```
src/somali_dialect_classifier/
├── cli/                             # CLI entry points
│   ├── download_wikisom.py         # wikisom-download
│   └── download_bbcsom.py          # bbcsom-download
└── preprocessing/                   # Data processing pipeline
    ├── base_pipeline.py            # Base orchestration (shared logic)
    ├── filters.py                  # Quality filters (length, language, dialect)
    ├── wikipedia_somali_processor.py  # Wikipedia implementation
    ├── bbc_somali_processor.py        # BBC implementation
    │
    ├── text_cleaners.py            # Shared: WikiMarkup, HTML, Whitespace cleaners
    ├── record_utils.py             # Shared: Hashing, ID generation, record building
    └── silver_writer.py            # Shared: Parquet schema + I/O
```

**Key Design Principles:**
- ✅ **Reusable utilities** - Text cleaners, record utils, silver writer shared across all sources
- ✅ **Quality filters** - Pluggable filter framework with hook interface for extensibility
- ✅ **Schema enforcement** - `SilverDatasetWriter` prevents drift with explicit PyArrow schema
- ✅ **Consistent partitioning** - All sources use `source=X/date_accessed=Y` structure
- ✅ **Testable** - Pure functions with no side effects (137+ unit tests)

### Adding New Data Sources

To add a new data source (e.g., BBC Somali):

1. Create a new processor in `src/somali_dialect_classifier/preprocessing/`
2. Inherit from `DataProcessor` base class
3. Follow the naming convention: `<source>_somali_processor.py`
4. Use consistent directory structure with `source=<SourceName>` partitioning

## Data Management (MLOps Best Practices)

### What's in Git:
- ✅ Source code (`src/`)
- ✅ Configuration (`pyproject.toml`, `.gitignore`)
- ✅ Documentation (`README.md`)
- ✅ Empty directories (`data/.gitkeep`, `logs/.gitkeep`)

### What's NOT in Git (gitignored):
- ❌ Data files (`data/*`) - Too large, regenerate via pipelines
- ❌ Log files (`logs/*`) - Runtime artifacts
- ❌ Models (`*.pt`, `*.bin`) - Use DVC, MLflow, or cloud storage
- ❌ Environment files (`.env`)

### Data Reproducibility:

Data is **not committed** to Git. Instead:

1. **For development**: Run `wikisom-download` or `bbcsom-download` to regenerate data locally
2. **For production**: Store data in cloud storage (S3, GCS, Azure Blob)
3. **For versioning**: Use DVC (Data Version Control) or MLflow for data lineage

Example with DVC (optional):
```bash
pip install dvc
dvc init
dvc add data/processed/silver/
git add data/.dvc .dvc/
```

## Configuration

The project supports flexible configuration via environment variables or `.env` files using pydantic-settings:

```bash
# Create a .env file in project root
cat > .env << EOF
SDC_DATA__RAW_DIR=/custom/path/raw
SDC_SCRAPING__BBC__MAX_ARTICLES=500
SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=200
SDC_LOGGING__LEVEL=DEBUG
EOF
```

Configuration can also be accessed programmatically:

```python
from somali_dialect_classifier.config import get_config

config = get_config()
print(config.data.raw_dir)
print(config.scraping.bbc.max_articles)
```

See [src/somali_dialect_classifier/config.py](src/somali_dialect_classifier/config.py) for all available configuration options.

## Data Quality

### Quality Filters

The preprocessing pipeline includes a pluggable filter framework for quality control:

```python
from somali_dialect_classifier.preprocessing.filters import (
    min_length_filter,
    langid_filter,
    dialect_heuristic_filter
)

# Filters are automatically applied during processing
# Each processor configures its own filters via _register_filters()
```

**Available Filters:**

- **min_length_filter**: Reject records below character threshold (default: 50 chars)
- **langid_filter**: Heuristic Somali language detection (120+ word vocabulary, 0.3 confidence)
- **dialect_heuristic_filter**: Topic/dialect marker enrichment without rejection
- **namespace_filter**: Wikipedia namespace validation (e.g., reject Talk:, User:)
- **custom_filter**: Arbitrary predicate functions for domain-specific rules

**Filter Statistics:**

Pipelines automatically log rejection counts per filter:

```
INFO - Processing 1000 records...
INFO - Filter statistics:
INFO -   filtered_by_min_length_filter: 23 records
INFO -   filtered_by_langid_filter: 45 records
INFO - Processed 932 records
```

**Extending Filters:**

To add custom filters to a processor:

```python
from somali_dialect_classifier.preprocessing.base_pipeline import BasePipeline

class MyCustomProcessor(BasePipeline):
    def _register_filters(self):
        from .filters import min_length_filter, custom_filter

        # Minimum length check
        self.record_filters.append((min_length_filter, {"threshold": 100}))

        # Custom business logic
        def is_news_article(text):
            return any(word in text.lower() for word in ["wararka", "xog"])

        self.record_filters.append((custom_filter, {
            "predicate": is_news_article,
            "metadata_key": "is_news"
        }))
```

### Deduplication

Remove duplicate articles from the silver dataset:

```bash
# Analyze duplicates without modifying data
python scripts/deduplicate_silver.py --dry-run

# Deduplicate and write to new directory
python scripts/deduplicate_silver.py --output-dir data/silver_deduped

# Custom silver directory
python scripts/deduplicate_silver.py --silver-dir data/silver --output-dir data/silver_clean
```

The deduplication script:
- Identifies duplicates by `text_hash`
- Keeps the earliest record (by `date_accessed`)
- Records provenance of removed duplicates
- Generates statistics by source, source_type, and topic

## Development Tools

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov --cov-report=term-missing

# Run specific test file
pytest tests/test_bbc_integration.py

# Stop on first failure
pytest --maxfail=1

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Lint code with ruff
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Type check with mypy
mypy src/
```

### CI/CD

GitHub Actions automatically runs linting, type checking, and tests on all pull requests. See [.github/workflows/ci.yml](.github/workflows/ci.yml) for details.

The CI pipeline:
- Runs on Ubuntu and macOS
- Tests Python 3.9, 3.10, and 3.11
- Generates coverage reports
- Uploads coverage to Codecov

## Documentation

**📘 [Complete Data Pipeline Guide](docs/guides/data-pipeline.md)** - Everything you need to know about data collection and processing

**Quick links:**
- [Documentation Index](docs/index.md) - Central navigation hub
- [Data Pipeline Guide](docs/guides/data-pipeline.md) - Comprehensive guide (architecture, sources, usage, troubleshooting)
- [Architecture Overview](docs/overview/architecture.md) - System design patterns
- [API Reference](docs/reference/api.md) - Complete API documentation
- [Deployment Guide](docs/operations/deployment.md) - Production deployment
- [Project Roadmap](docs/roadmap/lifecycle.md) - Project phases and milestones

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up your development environment
- Running tests and code quality checks
- Adding new data sources (4 existing sources as references)
- Integrating with Phase 0 infrastructure (crawl ledger, metrics, logging)
- Submitting pull requests

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
