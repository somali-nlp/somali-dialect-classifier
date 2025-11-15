# Somali Dialect Classifier

A production-ready data pipeline for collecting, processing, and preparing high-quality Somali language text from multiple sources. Built for dialect classification and NLP research with MLOps best practices including structured logging, automated quality metrics, deduplication, and ethical web scraping.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-165%2B%20passing-success)](tests/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dashboard](https://img.shields.io/badge/Dashboard-Live-blue)](https://somali-nlp.github.io/somali-dialect-classifier/)

## What's New (v2.0)

**Enhanced Filter Observability & Analytics** - Four major enhancements transform the project from operational to enterprise-grade:

1. **Dynamic Filter Catalog Loading** - Dashboard automatically loads filter labels from Python catalog (zero manual sync)
2. **CI Metrics Anomaly Alerts** - Automated GitHub Issues for metrics calculation bugs (prevents production incidents)
3. **Filter Coverage Regression Tests** - Automated tests prevent filter telemetry regressions (100% detection coverage)
4. **Historical Filter Export** - Export filter metrics to Parquet for trend analysis and data warehouse integration

See [Filter Analytics Guide](docs/howto/filter-analytics.md) and [CI Monitoring Guide](docs/howto/ci-metrics-anomaly-detection.md) for details.

## Key Features

- **Multi-source data collection** - Wikipedia (~50k articles), BBC Somali news, HuggingFace MC4 (~100k-200k web docs), Språkbanken (66 academic corpora), TikTok comments (social media)
- **Production-grade MLOps** - Structured logging, automated metrics, quality reports, crawl ledger for resume capability
- **Quality-first architecture** - Two-tier deduplication (exact + near-duplicate), pluggable quality filters, unified silver dataset schema
- **Advanced filter telemetry** - Per-filter breakdown tracking, historical analytics, regression prevention, automated anomaly detection
- **Ethical web scraping** - Rate limiting, robots.txt compliance, conditional requests, configurable scraping policies
- **Reproducible pipelines** - Timestamped artifacts, manifest versioning, Parquet storage with metadata sidecars
- **Comprehensive testing** - 165+ tests with CI/CD on Ubuntu and macOS (Python 3.9-3.11)

## Live Dashboard

**[View Interactive Dashboard →](https://somali-nlp.github.io/somali-dialect-classifier/)**

Real-time metrics, quality reports, and pipeline performance monitoring.

### Local Development

**Important:** The dashboard uses ES6 modules and must be run on an HTTP server.

#### Quick Start

```bash
# Python 3
cd _site
python -m http.server 8000

# Node.js
npx serve _site -p 8000

# PHP
cd _site
php -S localhost:8000
```

Then open: http://localhost:8000

#### Why HTTP Server Required?

ES6 modules (`import`/`export`) are subject to CORS policy and will not load from `file://` protocol. This is a browser security feature, not a bug.

#### VS Code Users

Install "Live Server" extension and right-click `index.html` → "Open with Live Server"

## Quick Start

```bash
# Clone and install
git clone https://github.com/yourusername/somali-dialect-classifier.git
cd somali-dialect-classifier
pip install -e ".[config]"

# Run individual pipelines
wikisom-download                          # Wikipedia Somali
bbcsom-download --max-articles 100       # BBC Somali News
hfsom-download mc4 --max-records 10000   # HuggingFace MC4
spraksom-download --corpus all           # Språkbanken corpora
tiktoksom-download --video-urls data/tiktok_urls.txt  # TikTok comments (requires Apify account)

# Or orchestrate all pipelines together (TikTok auto-includes if data/tiktok_urls.txt exists)
somali-orchestrate --pipeline all
```

**Output:** Unified silver dataset written to `data/processed/silver/` as Parquet files.

## Installation

### Requirements

- Python 3.9 or higher
- pip or conda package manager

### Installation Options

```bash
# Basic installation
pip install -e .

# With configuration support (recommended)
pip install -e ".[config]"

# Development tools (pytest, ruff, mypy)
pip install -e ".[dev]"

# MLOps tools (MLflow, W&B, Prefect)
pip install -e ".[mlops]"

# ML libraries (PyTorch, Transformers)
pip install -e ".[ml]"

# Everything
pip install -e ".[all]"
```

## Usage

### Orchestrated Execution (Recommended)

Run all pipelines with unified logging and parallel execution:

```bash
# Run all pipelines
somali-orchestrate --pipeline all

# Run specific pipeline with limits
somali-orchestrate --pipeline bbc --max-bbc-articles 500
somali-orchestrate --pipeline all --max-hf-records 10000

# Skip specific sources
somali-orchestrate --pipeline all --skip-sources bbc huggingface

# Choose specific Språkbanken corpus
somali-orchestrate --pipeline all --sprakbanken-corpus cilmi

# Auto-deploy dashboard after successful run
somali-orchestrate --pipeline all --auto-deploy

# Testing with limits
somali-orchestrate --pipeline all --max-bbc-articles 100 --max-hf-records 1000
```

### Individual Pipelines

**Wikipedia Somali** (~50,000 articles)
```bash
wikisom-download
```

**BBC Somali** (News articles)
```bash
bbcsom-download --max-articles 500
```

**HuggingFace MC4** (~100k-200k documents)
```bash
hfsom-download mc4 --max-records 10000
```

**Språkbanken** (66 academic corpora)
```bash
# List available corpora
spraksom-download --list

# Download specific corpus (use full corpus ID with "somali-" prefix)
spraksom-download --corpus somali-cilmi

# Download all corpora
spraksom-download --corpus all

# Use with orchestrator
somali-orchestrate --pipeline sprakbanken --sprakbanken-corpus somali-ogaden
```

**TikTok Comments** (Social media, colloquial Somali)
```bash
# Requires Apify account and API token
# See docs/howto/tiktok-integration.md for setup

# Use the pre-configured URLs file (contains 5 verified URLs)
tiktoksom-download --video-urls data/tiktok_urls.txt

# Or add your own URLs to data/tiktok_urls.txt
# Format: one URL per line, https://www.tiktok.com/@user/video/ID

# With limits
tiktoksom-download --video-urls data/tiktok_urls.txt --max-comments 10000

# Use with orchestrator (uses data/tiktok_urls.txt by default)
somali-orchestrate --pipeline tiktok

# Or specify custom URL file
somali-orchestrate --pipeline tiktok --tiktok-video-urls /custom/path.txt
```

**Note:** TikTok scraping costs $1 per 1,000 comments via Apify. See [Cost Analysis](docs/cost-analysis/tiktok-apify-costs.md) for budget planning.

### Accessing the Silver Dataset

```python
import pyarrow.parquet as pq

# Read unified silver dataset
table = pq.read_table("data/processed/silver/")

# Filter by source
wiki_records = table.filter(table.column("source") == "Wikipedia-Somali")
bbc_records = table.filter(table.column("source") == "BBC-Somali")

# Filter by quality
high_quality = table.filter(table.column("tokens") > 500)
```

**Schema:**
- `id` - UUID v4 identifier
- `text` - Cleaned text content
- `title` - Article/document title
- `source` - Data source (Wikipedia-Somali, BBC-Somali, etc.)
- `source_type` - Type (wiki, news, web, corpus)
- `language` - Language code (so)
- `license` - Data license
- `tokens` - Token count
- `source_metadata` - Quality metrics (detected_lang, lang_confidence, topic_markers)

See [Silver Schema Reference](docs/reference/silver-schema.md) for complete specification.

### Force Reprocessing

Pipelines skip existing files by default. To rebuild:

```bash
wikisom-download --force
bbcsom-download --force
hfsom-download mc4 --force
```

## Configuration

Configure via environment variables or `.env` files:

```bash
# Create .env file
cat > .env << EOF
SDC_DATA__RAW_DIR=/custom/path/raw
SDC_SCRAPING__BBC__MAX_ARTICLES=500
SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=200
SDC_LOGGING__LEVEL=DEBUG
EOF
```

Or programmatically:

```python
from somali_dialect_classifier.config import get_config

config = get_config()
print(config.data.raw_dir)
print(config.scraping.bbc.max_articles)
```

See [Configuration Guide](docs/howto/configuration.md) for all options.

## Data Quality

### Quality Filters

All pipelines include pluggable quality filters:

- **min_length_filter** - Reject records below character threshold (default: 50 chars)
- **langid_filter** - Heuristic Somali language detection
- **topic_lexicon_enrichment_filter** - Topic marker enrichment (sports, politics, etc.)
- **namespace_filter** - Wikipedia namespace validation

See [Filters Reference](docs/reference/filters.md) and [Custom Filters Guide](docs/howto/custom-filters.md).

### Deduplication

Remove exact and near-duplicate records using SHA256 hashing and MinHash LSH:

```bash
# Analyze duplicates (dry run)
python scripts/deduplicate_silver.py --dry-run

# Deduplicate and write to new directory
python scripts/deduplicate_silver.py --output-dir data/silver_deduped
```

## Documentation

**Complete Documentation:** [docs/index.md](docs/index.md)

### Essential Guides

- [Data Pipeline Guide](docs/guides/data-pipeline.md) - Complete guide to data collection and processing
- [Dashboard Guide](docs/guides/dashboard.md) - Interactive metrics dashboard deployment and usage
- [Portfolio Guide](docs/guides/portfolio.md) - Showcasing this project in your portfolio

### Quick Links by Task

**Getting Started:**
- **Get started:** [Processing Pipelines](docs/howto/processing-pipelines.md)
- **Add new data source:** [Architecture Overview](docs/overview/architecture.md)
- **Add custom filter:** [Custom Filters Guide](docs/howto/custom-filters.md)
- **Configure pipelines:** [Configuration Guide](docs/howto/configuration.md)

**New Features (v2.0):**
- **Filter analytics:** [Filter Analytics Guide](docs/howto/filter-analytics.md) - Historical analysis and trends
- **CI monitoring:** [CI Anomaly Detection](docs/howto/ci-metrics-anomaly-detection.md) - Automated quality gates
- **Dashboard usage:** [Dashboard Guide](docs/guides/dashboard.md) - Interactive metrics visualization
- **Regression testing:** [CONTRIBUTING.md](CONTRIBUTING.md#regression-tests) - Running filter coverage tests

**Operations:**
- **Deploy to production:** [Deployment Guide](docs/operations/deployment.md)
- **Troubleshooting:** [Troubleshooting Guide](docs/howto/troubleshooting.md)

### API Reference

- [API Reference](docs/reference/api.md) - Complete API documentation with examples
- [Silver Schema](docs/reference/silver-schema.md) - Silver dataset schema specification
- [Filters Reference](docs/reference/filters.md) - Built-in filter documentation

## Project Status

**Current Phase:** Data Curation (Phase 1) - **COMPLETE**

- ✅ Production data pipelines for multiple sources (Wikipedia, BBC, HuggingFace, Språkbanken, TikTok)
- ✅ Integrated MLOps infrastructure (logging, metrics, deduplication)
- ✅ Unified silver dataset schema across all sources
- ✅ 130,000-300,000 deduplicated Somali text records
- **Next:** Data labeling and annotation (Phase 2)

See [Project Roadmap](docs/roadmap/lifecycle.md) for detailed milestones.

## Data Directory Structure

```
data/
├── raw/                    # Original downloads
│   └── source=*/date_accessed=YYYY-MM-DD/
├── staging/                # Intermediate processing
│   └── source=*/date_accessed=YYYY-MM-DD/
├── processed/              # Cleaned data
│   └── source=*/date_accessed=YYYY-MM-DD/
└── processed/silver/       # Final unified dataset (Parquet)
    └── source=*/date_accessed=YYYY-MM-DD/
        ├── *_silver_part-0000.parquet
        └── *_silver_metadata.json
```

All filenames include run IDs (timestamp) for complete lineage tracking.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=term-missing

# Run specific test file
pytest tests/test_bbc_integration.py
```

### Code Quality

```bash
# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

### CI/CD

GitHub Actions automatically runs tests, linting, and type checking on all PRs. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Setting up your development environment
- Running tests and code quality checks
- Adding new data sources
- Submitting pull requests

All contributors must follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use this project in your research, please cite:

```bibtex
@software{somali_dialect_classifier,
  title = {Somali Dialect Classifier: Production Data Pipeline},
  author = {Somali NLP Contributors},
  year = {2025},
  url = {https://github.com/yourusername/somali-dialect-classifier}
}
```

## Tech Stack

- **Language:** Python 3.9+
- **Data Processing:** PyArrow, Pandas
- **Web Scraping:** Requests, BeautifulSoup, FeedParser
- **Quality:** Ruff, MyPy, Pytest (165+ tests)
- **Storage:** Parquet (columnar storage)
- **Configuration:** Pydantic Settings

## Acknowledgments

- **Data Sources:** Wikimedia Foundation, BBC Somali, HuggingFace, Språkbanken (University of Gothenburg), Apify (TikTok scraping)
- **Licenses:** CC-BY-SA-3.0 (Wikipedia), ODC-BY-1.0 (MC4), CC BY 4.0 (Språkbanken), TikTok Terms of Service

---

**Last Updated:** 2025-10-31
