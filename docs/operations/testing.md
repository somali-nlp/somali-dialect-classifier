# Testing Documentation

Comprehensive guide to the test strategy, test suite architecture, and testing best practices for the Somali Dialect Classifier.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Suite Overview](#test-suite-overview)
3. [Test Categories](#test-categories)
4. [Running Tests](#running-tests)
5. [Writing Tests](#writing-tests)
6. [Test Fixtures](#test-fixtures)
7. [Coverage](#coverage)
8. [CI/CD Integration](#cicd-integration)

## Testing Philosophy

### Principles

1. **Test behavior, not implementation**: Focus on public APIs and contracts
2. **Fast feedback**: Unit tests run in <1 second, full suite in <30 seconds
3. **Deterministic**: No flaky tests, reproducible results
4. **Isolated**: Tests don't depend on external services (network, filesystem)
5. **Readable**: Tests serve as documentation of expected behavior

### Test Pyramid

```
      ┌──────────┐
      │   E2E    │  5% - CLI end-to-end workflows
      │  (8 tests)│
      ├──────────┤
      │Integration│  20% - Multi-component interactions
      │ (24 tests)│
      ├──────────┤
      │   Unit   │  75% - Individual functions/classes
      │(105 tests)│
      └──────────┘
```

**Current Distribution**:
- **Unit tests**: 105 tests (76.6%)
- **Integration tests**: 24 tests (17.5%)
- **E2E tests**: 8 tests (5.8%)
- **Total**: 137 tests

## Test Suite Overview

### Test Files

```
tests/
├── fixtures/                              # Test data
│   ├── bbc_articles.json                 # Sample BBC articles (5 articles)
│   ├── wikipedia_sample.xml              # Sample Wikipedia dump (10 pages)
│   └── conftest.py                       # Shared pytest fixtures
│
├── test_base_pipeline_contract.py        # 24 tests - BasePipeline interface
├── test_bbc_integration.py               # 8 tests - BBC end-to-end
├── test_cli_e2e.py                       # 18 tests - CLI commands
├── test_filters.py                       # 35 tests - Quality filters
├── test_force_reprocessing.py            # 8 tests - Force flag behavior
├── test_record_utils.py                  # 11 tests - Utility functions
├── test_silver_writer.py                 # 5 tests - Parquet I/O
├── test_text_cleaners.py                 # 23 tests - Text transformation
└── test_wikipedia_integration.py         # 5 tests - Wikipedia end-to-end
```

### Test Coverage Matrix

| Component | Unit Tests | Integration Tests | E2E Tests | Total |
|-----------|-----------|------------------|-----------|-------|
| **BasePipeline** | 16 | 8 | 2 | 26 |
| **Filters** | 35 | 0 | 0 | 35 |
| **TextCleaners** | 23 | 0 | 0 | 23 |
| **RecordUtils** | 11 | 0 | 0 | 11 |
| **SilverWriter** | 5 | 0 | 0 | 5 |
| **Wikipedia** | 0 | 5 | 9 | 14 |
| **BBC** | 0 | 8 | 9 | 17 |
| **CLI** | 0 | 0 | 6 | 6 |
| **Total** | **90** | **21** | **26** | **137** |

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual functions and classes in isolation

**Characteristics**:
- ✅ Fast (< 10ms per test)
- ✅ No I/O (mocked or in-memory)
- ✅ Single responsibility
- ✅ High coverage (>90%)

**Examples**:

**Filters** (`test_filters.py`):
```python
def test_min_length_filter_passes_long_text():
    """Test that text >= threshold passes."""
    text = "a" * 100
    passes, metadata = min_length_filter(text, threshold=50)

    assert passes is True
    assert metadata == {}

def test_min_length_filter_rejects_short_text():
    """Test that text < threshold is rejected."""
    text = "a" * 30
    passes, metadata = min_length_filter(text, threshold=50)

    assert passes is False
    assert metadata == {}
```

**Text Cleaners** (`test_text_cleaners.py`):
```python
def test_wiki_markup_cleaner_removes_links():
    """Test [[link]] removal."""
    cleaner = WikiMarkupCleaner()
    text = "[[Soomaaliya]] waa waddan."

    result = cleaner.clean(text)

    assert result == "Soomaaliya waa waddan."
    assert "[[" not in result
```

**Record Utils** (`test_record_utils.py`):
```python
def test_text_hash_deterministic():
    """Test hash is deterministic."""
    text = "Muqdisho waa magaalada caasimadda ah."

    hash1 = text_hash(text)
    hash2 = text_hash(text)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest
```

### 2. Integration Tests

**Purpose**: Test interactions between components

**Characteristics**:
- ⚠️ Moderate speed (100-500ms per test)
- ⚠️ Uses temporary filesystem
- ✅ Tests realistic workflows
- ✅ Verifies component contracts

**Examples**:

**BBC Integration** (`test_bbc_integration.py`):
```python
@pytest.fixture
def mock_bbc_staging(temp_work_dir):
    """Create mock BBC staging data."""
    staging_dir = temp_work_dir / "staging" / "source=BBC-Somali" / f"date_accessed={date.today()}"
    staging_dir.mkdir(parents=True)

    articles = [
        {
            "title": "Wararka Maanta",
            "text": "<p>Muqdisho waa magaalada caasimadda ah...</p>",
            "url": "https://bbc.com/somali/1"
        }
    ]

    staging_file = staging_dir / "bbcsom_articles.json"
    with open(staging_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False)

    return staging_file

def test_bbc_process_from_fixture(mock_bbc_staging, temp_work_dir):
    """Test BBC processor creates silver dataset."""
    processor = BBCSomaliProcessor()

    silver_path = processor.process()

    assert silver_path.exists()
    assert silver_path.suffix == ".parquet"

    # Verify content
    df = pd.read_parquet(silver_path)
    assert len(df) >= 1
    assert all(col in df.columns for col in ["id", "text", "source"])
```

**Wikipedia Integration** (`test_wikipedia_integration.py`):
```python
def test_wikipedia_process_creates_silver_dataset(mock_wikipedia_staging):
    """Test Wikipedia processor creates Parquet output."""
    processor = WikipediaSomaliProcessor()

    silver_path = processor.process()

    assert silver_path.exists()
    df = pd.read_parquet(silver_path)
    assert df["source"].iloc[0] == "Wikipedia-Somali"
    assert df["source_type"].iloc[0] == "encyclopedia"
    assert df["license"].iloc[0] == "CC-BY-SA-3.0"
```

### 3. Contract Tests

**Purpose**: Verify processors implement BasePipeline interface correctly

**Characteristics**:
- ✅ Parameterized across all processors
- ✅ Validates interface compliance
- ✅ Catches breaking changes early

**Examples**:

**Base Pipeline Contract** (`test_base_pipeline_contract.py`):
```python
PROCESSORS = [WikipediaSomaliProcessor, BBCSomaliProcessor]

@pytest.mark.parametrize("processor_class", PROCESSORS)
def test_processor_implements_required_methods(processor_class):
    """Test processor has all required methods."""
    processor = processor_class()

    # Required abstract methods
    assert hasattr(processor, '_extract_records')
    assert callable(processor._extract_records)

    # Required concrete methods
    assert hasattr(processor, 'process')
    assert hasattr(processor, 'download')
    assert hasattr(processor, '_register_filters')

@pytest.mark.parametrize("processor_class", PROCESSORS)
def test_processor_has_required_attributes(processor_class):
    """Test processor has required attributes."""
    processor = processor_class()

    assert hasattr(processor, 'source')
    assert isinstance(processor.source, str)
    assert hasattr(processor, 'text_cleaner')
    assert hasattr(processor, 'record_filters')
    assert isinstance(processor.record_filters, list)
```

### 4. End-to-End Tests

**Purpose**: Test complete workflows from CLI to output

**Characteristics**:
- ❌ Slow (1-5 seconds per test)
- ⚠️ Uses subprocess for CLI
- ✅ Tests user-facing behavior
- ✅ Catches integration issues

**Examples**:

**CLI E2E** (`test_cli_e2e.py`):
```python
def test_wikipedia_cli_full_pipeline_with_fixture(temp_work_dir):
    """Test wikisom-download CLI with fixture data."""
    # Setup fixture
    create_wikipedia_fixture(temp_work_dir)

    # Run CLI
    result = subprocess.run(
        ["wikisom-download"],
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0
    assert "Successfully processed" in result.stdout

    # Verify output
    silver_dir = temp_work_dir / "processed" / "silver" / f"source=Wikipedia-Somali"
    assert silver_dir.exists()

    parquet_files = list(silver_dir.rglob("*.parquet"))
    assert len(parquet_files) == 1

def test_bbc_cli_help_output():
    """Test bbcsom-download --help."""
    result = subprocess.run(
        ["bbcsom-download", "--help"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "BBC Somali" in result.stdout
    assert "--max-articles" in result.stdout
```

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_filters.py

# Run specific test
pytest tests/test_filters.py::test_min_length_filter_passes_long_text

# Run tests matching pattern
pytest -k "langid"

# Stop on first failure
pytest -x

# Run with verbose output
pytest -v

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### With Coverage

```bash
# Run with coverage report
pytest --cov=src/somali_dialect_classifier --cov-report=term-missing

# Generate HTML report
pytest --cov=src/somali_dialect_classifier --cov-report=html
open htmlcov/index.html

# Fail if coverage < 80%
pytest --cov=src/somali_dialect_classifier --cov-fail-under=80
```

### Test Selection

```bash
# Run only unit tests (fast)
pytest tests/test_filters.py tests/test_text_cleaners.py tests/test_record_utils.py

# Run only integration tests
pytest tests/test_bbc_integration.py tests/test_wikipedia_integration.py

# Run only E2E tests (slow)
pytest tests/test_cli_e2e.py

# Skip slow tests
pytest -m "not slow"

# Run specific test class
pytest tests/test_filters.py::TestMinLengthFilter
```

### Debug Mode

```bash
# Show print statements
pytest -s

# Enter debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Verbose output with full tracebacks
pytest -vv --tb=long
```

## Writing Tests

### Test Structure (AAA Pattern)

```python
def test_function_name():
    """Test description in plain English.

    Explains what behavior is being tested and why.
    """
    # ARRANGE - Setup test data and conditions
    text = "Muqdisho waa magaalada caasimadda ah."
    threshold = 50

    # ACT - Execute the code under test
    passes, metadata = min_length_filter(text, threshold=threshold)

    # ASSERT - Verify expected outcomes
    assert passes is True
    assert metadata == {}
```

### Naming Conventions

**Test Files**: `test_<module_name>.py`
```
src/somali_dialect_classifier/preprocessing/filters.py
→ tests/test_filters.py
```

**Test Functions**: `test_<function>_<condition>_<expected_result>`
```python
test_min_length_filter_passes_long_text()
test_min_length_filter_rejects_short_text()
test_langid_filter_detects_somali_text()
test_langid_filter_rejects_english_text()
```

**Test Classes**: `Test<ClassName>`
```python
class TestMinLengthFilter:
    def test_passes_long_text(self):
        ...

    def test_rejects_short_text(self):
        ...
```

### Parametrized Tests

**Multiple Inputs**:
```python
@pytest.mark.parametrize("text,expected", [
    ("a" * 100, True),   # Long text passes
    ("a" * 50, True),    # Exactly at threshold passes
    ("a" * 49, False),   # One below threshold fails
    ("", False),         # Empty string fails
])
def test_min_length_filter(text, expected):
    """Test min_length_filter with various inputs."""
    passes, _ = min_length_filter(text, threshold=50)
    assert passes is expected
```

**Multiple Processors**:
```python
@pytest.mark.parametrize("processor_class", [
    WikipediaSomaliProcessor,
    BBCSomaliProcessor,
])
def test_processor_has_force_parameter(processor_class):
    """Test all processors accept force parameter."""
    processor = processor_class(force=True)
    assert processor.force is True
```

### Fixtures

**Shared Setup**:
```python
# tests/conftest.py
@pytest.fixture
def temp_work_dir(tmp_path, monkeypatch):
    """Create temporary working directory for tests."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Override config to use temp directory
    monkeypatch.setenv("SDC_DATA__RAW_DIR", str(work_dir / "raw"))
    monkeypatch.setenv("SDC_DATA__SILVER_DIR", str(work_dir / "processed" / "silver"))

    return work_dir

# tests/test_bbc_integration.py
def test_bbc_processor(temp_work_dir):
    """Test uses temp_work_dir fixture."""
    processor = BBCSomaliProcessor()
    # ... test code ...
```

**Fixture Scope**:
```python
@pytest.fixture(scope="function")  # Default: new for each test
def temp_dir(tmp_path):
    return tmp_path

@pytest.fixture(scope="class")     # Shared within test class
def shared_data():
    return load_data()

@pytest.fixture(scope="module")    # Shared within test file
def database_connection():
    conn = connect()
    yield conn
    conn.close()

@pytest.fixture(scope="session")   # Shared across entire test run
def test_config():
    return load_config()
```

### Mocking

**Mock External Dependencies**:
```python
from unittest.mock import patch, MagicMock

def test_bbc_scraper_handles_network_error():
    """Test graceful handling of network failures."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        scraper = BBCScraper()
        result = scraper.scrape_article("https://bbc.com/somali/1")

        assert result is None
        # Verify retry logic was called
        assert mock_get.call_count == 3  # 3 retries
```

**Mock Filesystem**:
```python
def test_process_skips_existing_file(temp_work_dir):
    """Test processor skips existing silver file."""
    # Create existing file
    silver_dir = temp_work_dir / "processed" / "silver" / f"source=BBC-Somali"
    silver_dir.mkdir(parents=True)
    (silver_dir / "part-0000.parquet").touch()

    processor = BBCSomaliProcessor()
    result = processor.process()

    # Should return existing file without reprocessing
    assert result == silver_dir / "part-0000.parquet"
```

## Test Fixtures

### Wikipedia Fixture

**File**: `tests/fixtures/wikipedia_sample.xml`

**Content**: 10 sample articles
```xml
<mediawiki>
  <page>
    <title>Muqdisho</title>
    <ns>0</ns>
    <revision>
      <text>Muqdisho waa magaalada caasimadda ah...</text>
    </revision>
  </page>
  <!-- 9 more articles -->
</mediawiki>
```

**Usage**:
```python
@pytest.fixture
def mock_wikipedia_staging(temp_work_dir):
    staging_dir = temp_work_dir / "staging" / f"source=Wikipedia-Somali"
    staging_dir.mkdir(parents=True)
    shutil.copy("tests/fixtures/wikipedia_sample.xml", staging_dir / "sample.xml")
    return staging_dir
```

### BBC Fixture

**File**: `tests/fixtures/bbc_articles.json`

**Content**: 5 sample news articles
```json
[
  {
    "title": "Wararka Maanta",
    "text": "<p>Muqdisho waa magaalada caasimadda ah ee Soomaaliya...</p>",
    "url": "https://www.bbc.com/somali/articles/1",
    "published_date": "2025-01-15"
  }
]
```

**Usage**:
```python
@pytest.fixture
def mock_bbc_articles():
    with open("tests/fixtures/bbc_articles.json") as f:
        return json.load(f)
```

## Coverage

### Current Coverage

**Overall**: 92% coverage (target: 90%+)

| Module | Coverage | Lines | Missing |
|--------|----------|-------|---------|
| **filters.py** | 98% | 371 | 7 |
| **text_cleaners.py** | 95% | 245 | 12 |
| **record_utils.py** | 100% | 87 | 0 |
| **silver_writer.py** | 88% | 156 | 19 |
| **base_pipeline.py** | 91% | 298 | 27 |
| **wikipedia_processor.py** | 89% | 187 | 21 |
| **bbc_processor.py** | 87% | 234 | 30 |

### Uncovered Lines

**Common Patterns**:

1. **Error handling** (hard to test without real failures):
   ```python
   except Exception as e:
       logger.error(f"Unexpected error: {e}")  # Uncovered
   ```

2. **Optional dependencies**:
   ```python
   try:
       from pydantic import Field
   except ImportError:
       # Fallback to dataclass  # Uncovered (pydantic always installed in tests)
   ```

3. **Edge cases** (low priority):
   ```python
   if sys.getsizeof(buffer) > 100_000_000:  # Uncovered (requires 100MB fixture)
       logger.warning("Buffer exceeds 100MB")
   ```

### Coverage Reports

**Generate Report**:
```bash
# Terminal report
pytest --cov=src/somali_dialect_classifier --cov-report=term-missing

# HTML report (interactive)
pytest --cov=src/somali_dialect_classifier --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest --cov=src/somali_dialect_classifier --cov-report=xml
```

**Example Output**:
```
Name                                               Stmts   Miss  Cover   Missing
--------------------------------------------------------------------------------
src/somali_dialect_classifier/config.py               45      3    93%   78-80
src/somali_dialect_classifier/preprocessing/
    filters.py                                        371      7    98%   234, 289-292
    text_cleaners.py                                  245     12    95%   134-137, 201-205
    record_utils.py                                    87      0   100%
--------------------------------------------------------------------------------
TOTAL                                                1234    112    92%
```

## CI/CD Integration

### GitHub Actions

**File**: `.github/workflows/ci.yml`

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.9", "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest --cov=src/somali_dialect_classifier --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hooks

**File**: `.pre-commit-config.yaml` (optional)

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: Run fast tests
        entry: pytest -k "not slow" --maxfail=1
        language: system
        pass_filenames: false
        always_run: true
```

### Test Quality Gates

**Pull Request Requirements**:
- ✅ All tests pass (137/137)
- ✅ Coverage ≥ 90%
- ✅ No linting errors (ruff)
- ✅ Type checking passes (mypy)

**Enforcement**:
```bash
# Run all quality checks
pytest --cov=src/somali_dialect_classifier --cov-fail-under=90
ruff check src/ tests/
mypy src/
```

## Best Practices

### 1. Test Independence

❌ **Bad** (tests depend on order):
```python
shared_state = []

def test_a():
    shared_state.append("a")
    assert len(shared_state) == 1

def test_b():
    # Fails if test_a didn't run first!
    assert "a" in shared_state
```

✅ **Good** (each test is independent):
```python
def test_a():
    state = []
    state.append("a")
    assert len(state) == 1

def test_b(temp_state):
    # Uses fixture
    assert "a" in temp_state
```

### 2. Descriptive Assertions

❌ **Bad**:
```python
assert processor.process()
```

✅ **Good**:
```python
result = processor.process()
assert result is not None, "Processor should return Path object"
assert result.exists(), f"Silver file should exist at {result}"
assert result.suffix == ".parquet", "Output should be Parquet format"
```

### 3. Test One Thing

❌ **Bad** (testing multiple behaviors):
```python
def test_bbc_processor():
    processor = BBCSomaliProcessor()
    processor.download()  # Test download
    result = processor.process()  # Test process
    df = pd.read_parquet(result)  # Test I/O
    assert len(df) > 0  # Test filtering
    assert "text" in df.columns  # Test schema
```

✅ **Good** (separate tests):
```python
def test_bbc_download_creates_raw_file():
    processor = BBCSomaliProcessor()
    result = processor.download()
    assert result.exists()

def test_bbc_process_creates_silver_dataset():
    processor = BBCSomaliProcessor()
    result = processor.process()
    assert result.suffix == ".parquet"

def test_bbc_silver_has_required_columns():
    df = load_bbc_fixture()
    assert all(col in df.columns for col in ["id", "text", "source"])
```

### 4. Use Factories for Complex Objects

```python
# tests/factories.py
def create_raw_record(
    text: str = "Default Somali text for testing",
    metadata: Optional[Dict] = None
) -> RawRecord:
    """Factory for creating RawRecord test fixtures."""
    return RawRecord(
        text=text,
        metadata=metadata or {"title": "Test Article"}
    )

# tests/test_pipeline.py
def test_process_with_short_text():
    record = create_raw_record(text="Short")  # Easy to customize
    # ... test code ...
```

### 5. Don't Test External Libraries

❌ **Bad** (testing pandas, not our code):
```python
def test_pandas_can_read_parquet():
    df = pd.read_parquet("file.parquet")
    assert isinstance(df, pd.DataFrame)  # Testing pandas!
```

✅ **Good** (testing our logic):
```python
def test_silver_writer_creates_valid_parquet():
    writer = SilverDatasetWriter()
    path = writer.write(records, "TestSource", datetime.now())

    # Test our code: file exists, has correct schema
    df = pd.read_parquet(path)
    assert df["source"].iloc[0] == "TestSource"
```

## Troubleshooting Tests

### Common Issues

**Issue: Tests fail on CI but pass locally**
```
AssertionError: File not found: /tmp/pytest-...
```
**Solution**: Check environment variables, ensure `temp_work_dir` fixture used

**Issue: Flaky test (sometimes passes, sometimes fails)**
```
AssertionError: Expected 10, got 9
```
**Solution**: Remove non-determinism (time.sleep, random, network calls)

**Issue: Test takes too long**
```
test_wikipedia_process_full_dump ... PASSED (142.3s)
```
**Solution**: Use smaller fixture, mark as slow (`@pytest.mark.slow`)

**Issue: Import error in tests**
```
ModuleNotFoundError: No module named 'somali_dialect_classifier'
```
**Solution**: Install in editable mode: `pip install -e .`

### Debug Test Failures

**Print debug info**:
```python
def test_filter():
    text = "Test text"
    passes, metadata = langid_filter(text)

    print(f"DEBUG: text={text!r}")
    print(f"DEBUG: passes={passes}, metadata={metadata}")

    assert passes is True
```

**Use pytest -s to see prints**:
```bash
pytest tests/test_filters.py::test_filter -s
```

**Drop into debugger**:
```python
def test_filter():
    text = "Test text"
    passes, metadata = langid_filter(text)

    import pdb; pdb.set_trace()  # Debugger starts here

    assert passes is True
```

## Future Enhancements

### Planned Improvements

1. **Property-based testing** with Hypothesis:
   ```python
   from hypothesis import given, strategies as st

   @given(text=st.text(min_size=100))
   def test_min_length_filter_handles_any_long_text(text):
       passes, _ = min_length_filter(text, threshold=50)
       assert passes is True
   ```

2. **Mutation testing** with mutmut:
   ```bash
   mutmut run
   # Verifies tests catch bugs by introducing mutations
   ```

3. **Performance benchmarking**:
   ```python
   def test_filter_performance(benchmark):
       text = "a" * 10000
       benchmark(langid_filter, text)
       # Ensures filter runs in < 10ms
   ```

4. **Contract testing** for APIs:
   ```python
   # Verify processor outputs match schema
   from pydantic import ValidationError

   def test_silver_record_schema_valid():
       record = build_silver_record(...)
       SilverRecord(**record)  # Validates via Pydantic
   ```

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
