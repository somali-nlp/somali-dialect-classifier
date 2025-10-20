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

## Adding New Data Sources

To add a new data source (e.g., VOA Somali, HuggingFace datasets):

### 1. Create Processor Class

Create `src/somali_dialect_classifier/preprocessing/your_source_processor.py`:

```python
from .base_pipeline import BasePipeline, RawRecord
from typing import Iterator

class YourSourceProcessor(BasePipeline):
    def __init__(self):
        super().__init__(source="YourSource-Somali")
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

    def _get_source_type(self) -> str:
        return "news"  # or "wiki", "social", etc.

    def _get_license(self) -> str:
        return "CC-BY-4.0"  # or appropriate license

    def _get_language(self) -> str:
        return "so"

    def _get_source_metadata(self) -> dict:
        return {"custom_field": "value"}
```

### 2. Create CLI Entry Point

Create `src/somali_dialect_classifier/cli/download_yoursource.py`:

```python
def main() -> None:
    processor = YourSourceProcessor()
    processor.download()
    processor.extract()
    processor.process()
```

Add to `pyproject.toml`:
```toml
[project.scripts]
yoursource-download = "somali_dialect_classifier.cli.download_yoursource:main"
```

### 3. Add Tests

1. Add test fixtures to `tests/fixtures/yoursource_sample.json`
2. Create `tests/test_yoursource_integration.py`
3. Add processor to `PROCESSOR_CLASSES` in `tests/test_base_pipeline_contract.py`

### 4. Update Documentation

- Add usage example to `README.md`
- Document data source in docstrings
- Update architecture diagrams if needed

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

**Thank you for contributing to Somali Dialect Classifier!** 🎉
