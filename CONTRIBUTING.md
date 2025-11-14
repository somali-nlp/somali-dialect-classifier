# Contributing to Somali Dialect Classifier

Thank you for your interest in contributing! This document provides guidelines and instructions for contributors.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Adding New Data Sources](#adding-new-data-sources)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic knowledge of NLP and data pipelines

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/somali-dialect-classifier.git
   cd somali-dialect-classifier
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the package with development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

   Or install all optional dependencies:
   ```bash
   pip install -e ".[all]"
   ```

4. **Verify installation**
   ```bash
   pytest --version
   ruff --version
   mypy --version
   ```

## Running Tests

### Quick Start

Run all tests:
```bash
pytest
```

### Test Options

```bash
# Run with coverage report
pytest --cov=src/somali_dialect_classifier --cov-report=html

# Run specific test file
pytest tests/test_wikipedia_integration.py

# Run specific test
pytest tests/test_wikipedia_integration.py::test_process_creates_silver_dataset

# Stop at first failure
pytest --maxfail=1

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"

# Verbose output
pytest -v

# Show local variables on failure
pytest -l
```

### Test Structure

```
tests/
├── fixtures/              # Test data (mini_wiki_dump.xml, bbc_articles.json)
├── test_base_pipeline_contract.py   # Contract tests for all processors
├── test_wikipedia_integration.py    # Wikipedia end-to-end tests
├── test_bbc_integration.py          # BBC end-to-end tests
├── test_cli_e2e.py                  # CLI command tests
└── conftest.py                       # Shared fixtures
```

### Writing Tests

- Place test files in `tests/` with `test_` prefix
- Use descriptive test names: `test_wikipedia_extracts_all_pages_from_dump`
- Use fixtures for setup/teardown (see `conftest.py`)
- Add docstrings explaining what each test validates
- For new processors, add them to `PROCESSOR_CLASSES` in `test_base_pipeline_contract.py`

Example:
```python
def test_new_processor_creates_silver_dataset(temp_data_dir, monkeypatch):
    """Test that NewProcessor creates valid silver parquet files."""
    processor = NewProcessor()
    # ... test logic
```

## Code Quality

### Linting and Formatting

We use **Ruff** for linting and formatting:

```bash
# Check code
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Type check the codebase
mypy src/

# Type check specific file
mypy src/somali_dialect_classifier/preprocessing/base_pipeline.py
```

### Pre-commit Checks

Before committing, run:

```bash
# Run all checks
ruff check --fix src/ tests/
ruff format src/ tests/
mypy src/
pytest
```

### Secret Scanning

We use **Gitleaks** to prevent accidental secret commits (API keys, passwords, tokens).

**One-time setup** (installs automatic pre-commit hook):

```bash
make secrets-install
```

**Manual checks** (optional, the hook runs automatically):

```bash
# Check staged files (fast)
make secrets-check

# Full repository scan (slower, use occasionally)
make secrets-scan
```

Once installed, the hook automatically scans before every commit:
- Scans only staged files (completes in milliseconds)
- Blocks commit if secrets are detected
- Provides guidance on how to fix issues

See [Secret Scanning Guide](docs/howto/secret-scanning.md) for detailed setup, troubleshooting, and configuration.

## Adding New Data Sources

The project currently has **4 production data sources**: Wikipedia, BBC Somali, HuggingFace (MC4), and Språkbanken (23 corpora). When adding a fifth source:

### 1. Create Processor Class

Create `src/somali_dialect_classifier/preprocessing/your_source_somali_processor.py`:

**Note**: Follow the naming convention `<source>_somali_processor.py`

```python
from .base_pipeline import BasePipeline, RawRecord
from typing import Iterator
from ..config import get_config

class YourSourceSomaliProcessor(BasePipeline):
    def __init__(self, force: bool = False):
        # Load config BEFORE super().__init__() if using in _register_filters()
        config = get_config()
        self.source_config = config.scraping.yoursource  # Add to config.yaml

        super().__init__(source="YourSource-Somali", force=force)

        # Set file paths
        self.staging_file = self.staging_dir / "yoursource_articles.json"
        self.processed_file = self.processed_dir / "yoursource.txt"

    def download(self) -> Path:
        """Download raw data."""
        # Implementation
        pass

    def extract(self) -> Path:
        """Extract to staging format."""
        # Implementation
        pass

    def _extract_records(self) -> Iterator[RawRecord]:
        """Yield records from staging file."""
        # Implementation
        yield RawRecord(title="...", text="...", url="...", metadata={})

    def _create_cleaner(self):
        """Create text cleaner."""
        from .text_cleaners import create_html_cleaner
        return create_html_cleaner()

    def _register_filters(self):
        """Register quality filters."""
        from .filters import min_length_filter, langid_filter

        self.record_filters.append((min_length_filter, {
            "threshold": self.source_config.min_length_threshold
        }))
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": self.source_config.langid_confidence
        }))

    def _get_source_type(self) -> str:
        return "news"  # or "wiki", "social", "corpus", "web"

    def _get_license(self) -> str:
        return "CC-BY-4.0"  # or appropriate license

    def _get_language(self) -> str:
        return "so"

    def _get_source_metadata(self) -> dict:
        return {"custom_field": "value"}

    def _get_domain(self) -> str:
        """Return content domain."""
        return "news"  # or "encyclopedia", "social_media", "literature", etc.
```

### 2. Integrate with Phase 0 Infrastructure

**Phase 0 provides production-ready MLOps infrastructure**. Integrate your processor:

```python
from somali_dialect_classifier.utils.logging_utils import (
    StructuredLogger, set_run_context, get_run_id
)
from somali_dialect_classifier.utils.metrics import MetricsCollector, QualityReporter
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger
from somali_dialect_classifier.preprocessing.dedup import DedupEngine

class YourSourceSomaliProcessor(BasePipeline):
    def __init__(self, force: bool = False):
        config = get_config(env="production")  # or "development"

        # Structured logging
        self.logger = StructuredLogger("YourSource-Somali", config)

        # Crawl ledger for state tracking
        self.ledger = get_ledger()  # SQLite by default

        # Deduplication engine
        self.dedup = DedupEngine(config, self.ledger)

        super().__init__(source="YourSource-Somali", force=force)

    def download(self):
        run_id = get_run_id("YourSource-Somali")
        set_run_context(run_id=run_id, source="YourSource-Somali", phase="discovery")

        # Initialize metrics
        self.metrics = MetricsCollector(run_id, "YourSource-Somali")

        self.logger.info("discovery_started", strategy="api")

        # Discover URLs and mark in ledger
        for url in discovered_urls:
            self.ledger.mark_discovered(url, "yoursource", metadata={"type": "article"})
            self.metrics.increment('urls_discovered')

        return manifest_path

    def extract(self):
        set_run_context(run_id=self.metrics.run_id, source="YourSource-Somali", phase="fetch")

        # Get pending URLs from ledger
        pending = self.ledger.get_pending("yoursource", limit=1000)

        for entry in pending:
            # Check for duplicates via hash
            text_hash = self._compute_text_hash(article_text, url)
            if self.ledger.is_duplicate(text_hash):
                self.ledger.mark_duplicate(url, text_hash, duplicate_url)
                self.metrics.increment('urls_deduplicated')
                continue

            # Fetch and mark in ledger
            self.ledger.mark_fetched(url, 200, text_hash, etag="...", content_length=len(text))
            self.metrics.increment('urls_fetched')

        # Export metrics and generate report
        self.metrics.export_json()
        QualityReporter(self.metrics).generate_markdown_report()

        return staging_path
```

**See**: [Phase 0 Implementation Guide](docs/operations/PHASE_0_IMPLEMENTATION_GUIDE.md)

### 3. Create CLI Entry Point

Create `src/somali_dialect_classifier/cli/download_yoursourcesom.py`:

**Note**: Follow the naming convention `download_<source>som.py`

```python
def main() -> None:
    processor = YourSourceSomaliProcessor()
    processor.run()  # Runs download → extract → process
```

Add to `pyproject.toml`:
```toml
[project.scripts]
yoursourcesom-download = "somali_dialect_classifier.cli.download_yoursourcesom:main"
```

### 4. Add Configuration

Add to `src/somali_dialect_classifier/config/production.yaml`:

```yaml
yoursource:
  timeout: 30
  max_requests_per_hour: 100
  min_length_threshold: 50
  langid_confidence_threshold: 0.3
```

### 5. Add Tests

1. Add test fixtures to `tests/fixtures/yoursource_sample.json`
2. Create `tests/test_yoursource_integration.py`
3. Create `tests/test_yoursource_processor.py`
4. Add processor to `PROCESSOR_CLASSES` in `tests/test_base_pipeline_contract.py`
5. Add Phase 0 integration tests (ledger, metrics, logging)

### 6. Update Documentation

- Add usage example to `README.md`
- Create `docs/howto/yoursource-integration.md` (follow template from other sources)
- Update `docs/index.md` to include new source
- Add to `docs/reference/api.md`
- Document ethical scraping policies if web scraping

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/add-voa-somali-processor
# or
git checkout -b fix/deduplicate-silver-records
```

### 2. Make Your Changes

- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation
- Keep commits atomic and well-described

### 3. Run Quality Checks

```bash
# Format and lint
ruff format src/ tests/
ruff check --fix src/ tests/

# Type check
mypy src/

# Test
pytest

# Check coverage
pytest --cov=src/somali_dialect_classifier --cov-report=term-missing
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add VOA Somali news processor

- Implements BasePipeline interface
- Adds CLI command voa-download
- Includes integration tests with fixtures
- Updates README with usage instructions"
```

### 5. Push and Create PR

```bash
git push origin feature/add-voa-somali-processor
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what was added/fixed
- Link to related issues
- Screenshots/logs if applicable

### PR Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`ruff format`)
- [ ] No linting errors (`ruff check`)
- [ ] Type checks pass (`mypy src/`)
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] PR description is clear

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Reproduction Steps**: Minimal steps to reproduce
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**:
   - Python version (`python --version`)
   - Package version
   - Operating system
6. **Logs**: Relevant error messages or stack traces

### Feature Requests

For feature requests, include:

1. **Use Case**: What problem does this solve?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other solutions you've considered
4. **Additional Context**: Any other relevant information

## Development Tips

### Debugging

```bash
# Run with verbose output
pytest -vv -s

# Drop into debugger on failure
pytest --pdb

# Use ipdb for interactive debugging
import ipdb; ipdb.set_trace()
```

### Data Pipeline Development

```bash
# Test with small dataset
wikisom-download  # Uses test fixtures automatically in tests

# Check silver dataset
python -c "import pyarrow.parquet as pq; print(pq.read_table('data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-01-01').to_pandas())"
```

### Performance Profiling

```bash
# Profile tests
pytest --profile

# Profile specific function
python -m cProfile -o output.prof your_script.py
python -m pstats output.prof
```

## Getting Help

- **Documentation**: Check `README.md` and docstrings
- **Issues**: Search existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Code Examples**: Look at existing processors (Wikipedia, BBC)

## Code of Conduct

Please note that this project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms.

---

**Thank you for contributing to Somali Dialect Classifier!**

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
