# Testing Patterns and Dependency Injection

**Comprehensive guide to testing patterns, dependency injection, and test isolation strategies in the Somali Dialect Classifier.**

**Last Updated:** 2025-12-30

---

## Table of Contents

- [Overview](#overview)
- [Dependency Injection](#dependency-injection)
  - [What is Dependency Injection?](#what-is-dependency-injection)
  - [Why Dependency Injection Matters](#why-dependency-injection-matters)
  - [Injected Dependencies in BasePipeline](#injected-dependencies-in-basepipeline)
  - [Backward Compatibility](#backward-compatibility)
- [Using Dependency Injection](#using-dependency-injection)
  - [Mocking the Ledger](#mocking-the-ledger)
  - [Mocking Metrics Factory](#mocking-metrics-factory)
  - [Mocking HTTP Session](#mocking-http-session)
  - [Combined Example](#combined-example)
- [Test Patterns](#test-patterns)
  - [Unit Test Isolation](#unit-test-isolation)
  - [Integration Test Strategies](#integration-test-strategies)
  - [Fixture Patterns](#fixture-patterns)
  - [Contract Test Examples](#contract-test-examples)
- [Best Practices](#best-practices)
  - [When to Use Mocks vs Real Dependencies](#when-to-use-mocks-vs-real-dependencies)
  - [Test Organization Strategies](#test-organization-strategies)
  - [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
- [Testing Scenarios](#testing-scenarios)
  - [Testing Crash Recovery](#testing-crash-recovery)
  - [Testing Memory-Bounded Deduplication](#testing-memory-bounded-deduplication)
  - [Testing Contract Validation](#testing-contract-validation)
- [References](#references)

---

## Overview

The Somali Dialect Classifier uses **dependency injection** to enable isolated, fast, and reliable testing. This guide explains how to write effective tests using the project's testing patterns.

### Key Benefits

- **Isolation**: Test components without external dependencies
- **Speed**: Fast unit tests without database/network I/O
- **Reliability**: Consistent test results regardless of environment
- **Flexibility**: Easy to test edge cases and error conditions

---

## Dependency Injection

### What is Dependency Injection?

Dependency Injection (DI) is a design pattern where dependencies are provided to a class from the outside, rather than created internally. This makes testing easier by allowing mock objects to be substituted.

**Without DI:**
```python
class MyProcessor:
    def __init__(self):
        self.ledger = CrawlLedger()  # Hard-coded dependency
        self.metrics = MetricsCollector()
```

**With DI:**
```python
class MyProcessor:
    def __init__(self, ledger=None, metrics_factory=None):
        self.ledger = ledger or CrawlLedger()  # Injected or default
        self.metrics_factory = metrics_factory or self._default_metrics
```

### Why Dependency Injection Matters

1. **Testability**: Replace real dependencies with mocks
2. **Flexibility**: Swap implementations without changing code
3. **Decoupling**: Reduce tight coupling between components
4. **Maintainability**: Easier to refactor and extend

### Injected Dependencies in BasePipeline

The `BasePipeline` class accepts three optional dependencies:

| Dependency | Type | Purpose | Default |
|------------|------|---------|---------|
| `ledger` | `CrawlLedger` | URL state tracking and quotas | Auto-created SQLite ledger |
| `metrics_factory` | `Callable` | Metrics collection factory | Auto-creates `MetricsCollector` |
| `http_session` | `requests.Session` | HTTP client for downloads | Auto-creates `requests.Session` |

### Backward Compatibility

All dependencies are **optional** - existing code works without changes:

```python
# Old code (still works)
processor = WikipediaSomaliProcessor()

# New code (with dependency injection)
processor = WikipediaSomaliProcessor(
    ledger=mock_ledger,
    metrics_factory=mock_metrics_factory
)
```

---

## Using Dependency Injection

### Mocking the Ledger

**Why Mock the Ledger?**
- Avoid database I/O in unit tests
- Test different ledger states easily
- Isolate processor logic from ledger implementation

**Basic Mock:**
```python
from unittest.mock import Mock, MagicMock
from somali_dialect_classifier.ingestion.processors import WikipediaSomaliProcessor

# Create mock ledger
mock_ledger = Mock()
mock_ledger.should_fetch_url.return_value = True
mock_ledger.get_processed_urls.return_value = []
mock_ledger.mark_fetched.return_value = None
mock_ledger.mark_processed.return_value = None

# Inject into processor
processor = WikipediaSomaliProcessor(ledger=mock_ledger)

# Test processor logic without database
processor.process()

# Verify ledger interactions
mock_ledger.should_fetch_url.assert_called()
mock_ledger.mark_processed.assert_called()
```

**Testing Different Ledger States:**
```python
# Test with already-processed URLs
mock_ledger = Mock()
mock_ledger.should_fetch_url.return_value = False  # Skip fetching
mock_ledger.get_processed_urls.return_value = [
    {'url': 'https://example.com/article1', 'state': 'processed'}
]

processor = WikipediaSomaliProcessor(ledger=mock_ledger)
result = processor.process()

# Verify processor skipped already-processed URLs
assert result.records_written == 0
```

**Testing Ledger Errors:**
```python
from somali_dialect_classifier.ingestion.crawl_ledger import LedgerError

# Mock ledger failure
mock_ledger = Mock()
mock_ledger.mark_processed.side_effect = LedgerError("Database locked")

processor = WikipediaSomaliProcessor(ledger=mock_ledger)

# Verify processor handles ledger errors gracefully
with pytest.raises(LedgerError):
    processor.process()
```

### Mocking Metrics Factory

**Why Mock Metrics?**
- Avoid file I/O during testing
- Verify metrics are collected correctly
- Test metrics aggregation logic

**Basic Mock:**
```python
from unittest.mock import Mock

# Create mock metrics collector
mock_metrics = Mock()
mock_metrics.increment.return_value = None
mock_metrics.record_fetch_duration.return_value = None
mock_metrics.export_json.return_value = None

# Create metrics factory
def mock_metrics_factory(run_id, source):
    return mock_metrics

# Inject into processor
processor = BBCSomaliProcessor(metrics_factory=mock_metrics_factory)
processor.process()

# Verify metrics were collected
mock_metrics.increment.assert_any_call('urls_discovered')
mock_metrics.record_fetch_duration.assert_called()
```

**Testing Metrics Calculation:**
```python
# Mock metrics with real behavior
class MockMetrics:
    def __init__(self, run_id, source):
        self.data = {}

    def increment(self, key, count=1):
        self.data[key] = self.data.get(key, 0) + count

    def get(self, key):
        return self.data.get(key, 0)

def metrics_factory(run_id, source):
    return MockMetrics(run_id, source)

processor = WikipediaSomaliProcessor(metrics_factory=metrics_factory)
processor.process()

# Verify specific metric values
assert processor.metrics.get('records_processed') > 0
assert processor.metrics.get('records_written') > 0
```

### Mocking HTTP Session

**Why Mock HTTP?**
- Avoid network I/O in unit tests
- Test HTTP error handling
- Control response data exactly

**Basic Mock:**
```python
from unittest.mock import Mock

# Create mock session
mock_session = Mock()
mock_response = Mock()
mock_response.status_code = 200
mock_response.content = b"<xml>...</xml>"
mock_response.headers = {'Content-Type': 'application/xml'}
mock_session.get.return_value = mock_response

# Inject into processor
processor = SprakbankenSomaliProcessor(
    corpus_id="somali-cilmi",
    http_session=mock_session
)

# Test without network
processor.download()

# Verify HTTP calls
mock_session.get.assert_called_once()
```

**Testing HTTP Errors:**
```python
import requests

# Mock HTTP 404 error
mock_session = Mock()
mock_session.get.side_effect = requests.HTTPError("404 Not Found")

processor = SprakbankenSomaliProcessor(
    corpus_id="somali-invalid",
    http_session=mock_session
)

# Verify error handling
with pytest.raises(requests.HTTPError):
    processor.download()
```

**Using VCR.py for Real Responses:**
```python
import vcr

# Record HTTP interactions once, replay in tests
@vcr.use_cassette('tests/vcr_cassettes/wikipedia_dump.yaml')
def test_wikipedia_download():
    processor = WikipediaSomaliProcessor()
    result = processor.download()

    assert result is not None
    # First run records, subsequent runs replay
```

### Combined Example

**Full Test with All Dependencies Mocked:**
```python
from unittest.mock import Mock
import pytest

def test_processor_with_all_mocks():
    # Mock ledger
    mock_ledger = Mock()
    mock_ledger.should_fetch_url.return_value = True
    mock_ledger.get_processed_urls.return_value = []

    # Mock metrics
    mock_metrics = Mock()
    def metrics_factory(run_id, source):
        return mock_metrics

    # Mock HTTP session
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"Test content"
    mock_session.get.return_value = mock_response

    # Create processor with all mocks
    processor = BBCSomaliProcessor(
        ledger=mock_ledger,
        metrics_factory=metrics_factory,
        http_session=mock_session
    )

    # Test processor logic
    result = processor.process()

    # Verify interactions
    mock_ledger.should_fetch_url.assert_called()
    mock_metrics.increment.assert_called()
    mock_session.get.assert_called()

    assert result is not None
```

---

## Test Patterns

### Unit Test Isolation

**Goal**: Test single components in isolation

**Pattern: Pure Function Testing**
```python
from somali_dialect_classifier.quality.filters import min_length_filter

def test_min_length_filter():
    # Test passing case
    passes, metadata = min_length_filter("This is long enough text", threshold=10)
    assert passes is True
    assert metadata == {}

    # Test failing case
    passes, metadata = min_length_filter("Short", threshold=10)
    assert passes is False
    assert metadata == {}
```

**Pattern: Mocked Dependencies**
```python
from unittest.mock import Mock, patch

def test_processor_extraction():
    # Mock only what's needed
    with patch('somali_dialect_classifier.ingestion.processors.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"<article>Test</article>"

        processor = BBCSomaliProcessor()
        records = list(processor._extract_records())

        assert len(records) > 0
```

### Integration Test Strategies

**Goal**: Test component interactions with real dependencies

**Pattern: Minimal Integration**
```python
import pytest
from pathlib import Path

@pytest.mark.integration
def test_wikipedia_end_to_end(tmp_path):
    # Use real ledger in temp directory
    ledger_path = tmp_path / "test_ledger.db"

    processor = WikipediaSomaliProcessor(
        ledger=CrawlLedger(ledger_path)
    )

    # Test with real fixture data
    result = processor.process()

    assert result.records_written > 0
    assert ledger_path.exists()
```

**Pattern: Docker Integration Tests**
```python
@pytest.mark.docker
def test_postgres_ledger_integration():
    # Requires Docker Compose up
    ledger = PostgresLedger(
        host='localhost',
        port=5432,
        database='test_ledger'
    )

    processor = BBCSomaliProcessor(ledger=ledger)
    result = processor.process()

    assert result is not None
```

### Fixture Patterns

**Pattern: Shared Test Data**
```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_wiki_xml():
    """Provide sample Wikipedia XML for testing."""
    fixture_path = Path(__file__).parent / "fixtures" / "mini_wiki_dump.xml"
    return fixture_path

@pytest.fixture
def mock_ledger():
    """Provide configured mock ledger."""
    ledger = Mock()
    ledger.should_fetch_url.return_value = True
    ledger.get_processed_urls.return_value = []
    return ledger

def test_with_fixtures(sample_wiki_xml, mock_ledger):
    processor = WikipediaSomaliProcessor(ledger=mock_ledger)
    # Use fixtures in test
    assert sample_wiki_xml.exists()
```

**Pattern: Factory Fixtures**
```python
@pytest.fixture
def processor_factory(mock_ledger, tmp_path):
    """Factory to create processors with test configuration."""
    def _create_processor(processor_class, **kwargs):
        return processor_class(
            ledger=mock_ledger,
            data_dir=tmp_path,
            **kwargs
        )
    return _create_processor

def test_multiple_processors(processor_factory):
    wiki = processor_factory(WikipediaSomaliProcessor)
    bbc = processor_factory(BBCSomaliProcessor, max_articles=10)

    assert wiki is not None
    assert bbc is not None
```

### Contract Test Examples

**Goal**: Verify all processors implement the contract

**Pattern: Abstract Test Class**
```python
import pytest
from abc import ABC

class BaseProcessorContractTests(ABC):
    """Base contract tests for all processors."""

    @pytest.fixture
    def processor(self):
        """Override in subclass to provide processor instance."""
        raise NotImplementedError

    def test_has_extract_records(self, processor):
        assert hasattr(processor, '_extract_records')
        assert callable(processor._extract_records)

    def test_has_register_filters(self, processor):
        assert hasattr(processor, '_register_filters')
        assert callable(processor._register_filters)

    def test_process_returns_result(self, processor):
        result = processor.process()
        assert result is not None
        assert hasattr(result, 'records_written')

# Concrete test class
class TestWikipediaContract(BaseProcessorContractTests):
    @pytest.fixture
    def processor(self, mock_ledger):
        return WikipediaSomaliProcessor(ledger=mock_ledger)

class TestBBCContract(BaseProcessorContractTests):
    @pytest.fixture
    def processor(self, mock_ledger):
        return BBCSomaliProcessor(ledger=mock_ledger)
```

---

## Best Practices

### When to Use Mocks vs Real Dependencies

**Use Mocks:**
- Unit tests (test single component)
- Testing error conditions (network failures, database errors)
- Fast feedback (< 1 second per test)
- CI/CD pipelines (no external services)

**Use Real Dependencies:**
- Integration tests (test component interactions)
- End-to-end tests (verify full pipeline)
- Performance testing (measure real I/O)
- Contract testing (verify external API behavior)

**Decision Matrix:**

| Scenario | Mock | Real | Rationale |
|----------|------|------|-----------|
| Filter function logic | Mock | - | Pure function, no dependencies |
| HTTP request handling | Mock | Real (VCR) | Test error cases with mock, record real responses |
| Database queries | Mock | Real (test DB) | Fast unit tests with mock, integration tests with real DB |
| Text cleaning pipeline | - | Real | Deterministic, no side effects |
| Full processor pipeline | Mock | Real | Unit tests mock, integration tests use real |

### Test Organization Strategies

**Directory Structure:**
```
tests/
├── unit/                      # Fast, isolated tests
│   ├── test_filters.py
│   ├── test_cleaners.py
│   └── test_dedup.py
├── integration/               # Component interaction tests
│   ├── test_wikipedia_integration.py
│   ├── test_bbc_integration.py
│   └── test_contract_integration.py
├── fixtures/                  # Shared test data
│   ├── mini_wiki_dump.xml
│   ├── bbc_articles.json
│   └── sample_silver.parquet
├── vcr_cassettes/            # Recorded HTTP responses
│   ├── wikipedia_dump.yaml
│   └── bbc_homepage.yaml
└── conftest.py               # Shared fixtures and configuration
```

**Test Naming Convention:**
```python
# Unit tests
def test_filter_rejects_short_text():
    pass

def test_cleaner_removes_html_tags():
    pass

# Integration tests
def test_processor_writes_to_silver_dataset():
    pass

def test_ledger_tracks_processed_urls():
    pass

# Contract tests
def test_all_processors_implement_extract_records():
    pass
```

**Markers for Test Categories:**
```python
import pytest

@pytest.mark.unit
def test_fast_unit_test():
    pass

@pytest.mark.integration
def test_component_interaction():
    pass

@pytest.mark.slow
def test_full_pipeline():
    pass

@pytest.mark.requires_network
def test_real_http_request():
    pass
```

**Running Specific Tests:**
```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_filters.py -v
```

### Common Pitfalls and Solutions

**Pitfall 1: Shared Mutable State**

**Problem:**
```python
# Bad: Shared mock across tests
mock_ledger = Mock()

def test_one():
    processor = WikipediaSomaliProcessor(ledger=mock_ledger)
    processor.process()

def test_two():
    # mock_ledger carries state from test_one!
    processor = BBCSomaliProcessor(ledger=mock_ledger)
    processor.process()
```

**Solution:**
```python
# Good: Fresh mock per test
@pytest.fixture
def mock_ledger():
    return Mock()

def test_one(mock_ledger):
    processor = WikipediaSomaliProcessor(ledger=mock_ledger)
    processor.process()

def test_two(mock_ledger):
    # Clean mock for each test
    processor = BBCSomaliProcessor(ledger=mock_ledger)
    processor.process()
```

**Pitfall 2: Over-Mocking**

**Problem:**
```python
# Bad: Mocking everything, testing nothing
mock_processor = Mock()
mock_processor.process.return_value = Mock(records_written=100)

result = mock_processor.process()
assert result.records_written == 100  # Meaningless test
```

**Solution:**
```python
# Good: Mock dependencies, test real logic
mock_ledger = Mock()
mock_ledger.should_fetch_url.return_value = True

processor = WikipediaSomaliProcessor(ledger=mock_ledger)
result = processor.process()  # Real processor logic

assert result.records_written > 0  # Tests actual processing
```

**Pitfall 3: Brittle Assertions**

**Problem:**
```python
# Bad: Over-specifying mock calls
mock_ledger.should_fetch_url.assert_called_with(
    'https://exact.url/article',
    force=False,
    timeout=30,
    retry=True
)  # Breaks if parameter order changes
```

**Solution:**
```python
# Good: Verify essential behavior only
mock_ledger.should_fetch_url.assert_called()
# Or use argument matchers
from unittest.mock import ANY
mock_ledger.should_fetch_url.assert_called_with(ANY, force=False)
```

**Pitfall 4: Missing Test Isolation**

**Problem:**
```python
# Bad: Tests depend on execution order
def test_create_file():
    Path('test.txt').write_text('data')

def test_read_file():
    content = Path('test.txt').read_text()  # Fails if test_create_file skipped
    assert content == 'data'
```

**Solution:**
```python
# Good: Each test is independent
@pytest.fixture
def test_file(tmp_path):
    file_path = tmp_path / 'test.txt'
    file_path.write_text('data')
    return file_path

def test_read_file(test_file):
    content = test_file.read_text()
    assert content == 'data'
```

---

## Testing Scenarios

### Testing Crash Recovery

**Scenario**: Verify checkpoint recovery works correctly

```python
from somali_dialect_classifier.ingestion.processors import WikipediaSomaliProcessor

def test_checkpoint_recovery(tmp_path, mock_ledger):
    # Create processor with checkpoint directory
    processor = WikipediaSomaliProcessor(
        ledger=mock_ledger,
        checkpoint_dir=tmp_path / "checkpoints"
    )

    # Simulate crash after 1000 records
    processor.batch_size = 1000

    # First run (processes 1000 records, then stops)
    with patch.object(processor, '_extract_records') as mock_extract:
        mock_extract.return_value = iter([Mock()] * 2000)

        # Simulate crash
        with pytest.raises(KeyboardInterrupt):
            for i, record in enumerate(processor._extract_records()):
                processor._process_record(record)
                if i == 999:
                    raise KeyboardInterrupt("Simulated crash")

    # Verify checkpoint saved
    checkpoints = list((tmp_path / "checkpoints").glob("*.json"))
    assert len(checkpoints) == 1

    # Second run (resumes from checkpoint)
    processor2 = WikipediaSomaliProcessor(
        ledger=mock_ledger,
        checkpoint_dir=tmp_path / "checkpoints"
    )

    # Verify processor resumes from offset 1000
    assert processor2.resume_offset == 1000
```

### Testing Memory-Bounded Deduplication

**Scenario**: Verify LRU eviction works correctly

```python
from somali_dialect_classifier.ingestion.dedup import DedupEngine, DedupConfig

def test_memory_bounded_dedup():
    # Configure small cache for testing
    config = DedupConfig(
        cache_size=10,  # Only 10 entries
        enable_minhash=False
    )

    dedup = DedupEngine(config)

    # Add 15 documents (exceeds cache size)
    for i in range(15):
        text_hash = f"hash_{i}"
        dedup.add_document(text_hash, None)

    # Verify cache size is bounded
    assert len(dedup.hash_cache) == 10

    # Verify oldest entries evicted (LRU)
    assert not dedup.is_exact_duplicate("hash_0")  # Evicted
    assert dedup.is_exact_duplicate("hash_14")  # Recent, still in cache
```

### Testing Contract Validation

**Scenario**: Verify silver output matches contract

```python
from somali_dialect_classifier.contracts.ingestion_output import validate_ingestion_output
import pyarrow.parquet as pq

def test_silver_output_contract(tmp_path):
    # Process sample data
    processor = WikipediaSomaliProcessor(
        ledger=Mock(),
        silver_dir=tmp_path / "silver"
    )

    result = processor.process()

    # Read silver output
    silver_path = tmp_path / "silver" / f"source=Wikipedia-Somali"
    table = pq.read_table(silver_path)

    # Validate against contract
    errors = validate_ingestion_output(table)

    # Verify no contract violations
    assert len(errors) == 0, f"Contract violations: {errors}"

    # Verify required fields present
    assert 'id' in table.column_names
    assert 'text' in table.column_names
    assert 'run_id' in table.column_names
    assert 'schema_version' in table.column_names
```

---

## References

- [Contract Validation Guide](contract-validation.md) - Ingestion output contracts
- [Crash Recovery Guide](crash-recovery.md) - Checkpoint-based recovery
- [Memory Optimization Guide](memory-optimization.md) - Memory-bounded deduplication
- [Architecture Documentation](../overview/architecture.md) - System design patterns
- [pytest Documentation](https://docs.pytest.org/) - Testing framework reference

---

**Maintainers**: Somali NLP Contributors
