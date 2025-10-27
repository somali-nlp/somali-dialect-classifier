# Metrics Phase 2 & 3 Migration Guide

**Date:** 2025-10-26
**Schema Version:** 3.0
**Backward Compatible:** Yes (100%)

## Table of Contents

1. [Overview](#overview)
2. [What's New](#whats-new)
3. [Layered Metrics Architecture (Phase 2)](#layered-metrics-architecture-phase-2)
4. [Type Safety & Validation (Phase 3)](#type-safety--validation-phase-3)
5. [Prometheus Export (Phase 3)](#prometheus-export-phase-3)
6. [Migration Guide](#migration-guide)
7. [Backward Compatibility](#backward-compatibility)
8. [Examples](#examples)
9. [FAQ](#faq)

## Overview

Phase 2 and Phase 3 of the metrics refactoring introduce a **layered metrics architecture** with clear separation of concerns, **type-safe validation**, and **production-ready Prometheus export**. These changes are fully backward compatible with Phase 1.

### Key Benefits

- **Clearer Mental Model**: Metrics organized into 4 logical layers
- **Better Debugging**: Validation catches data inconsistencies before export
- **Production Observability**: Native Prometheus export for monitoring
- **Type Safety**: Factory functions prevent mixing metric types across pipelines
- **Schema Versioning**: Track metric format changes over time

## What's New

### Phase 2: Layered Metrics Architecture

Metrics are now organized into 4 hierarchical layers:

1. **Layer 1: Connectivity** - Can we reach the source?
2. **Layer 2: Extraction** - Can we retrieve data? (pipeline-specific)
3. **Layer 3: Quality** - Does data meet standards?
4. **Layer 4: Volume** - How much data?

### Phase 3: Type Safety & Validation

- **Validation Methods**: Each metric class validates its own consistency
- **Factory Functions**: `create_extraction_metrics()` ensures correct metric types
- **Cross-Layer Validation**: Checks logical consistency across layers
- **Schema Versioning**: JSON exports include `_schema_version: "3.0"`
- **Prometheus Export**: Production-ready Prometheus text format

## Layered Metrics Architecture (Phase 2)

### Layer 1: Connectivity Metrics

Tracks connection establishment to data sources.

```python
from src.somali_dialect_classifier.utils.metrics import ConnectivityMetrics

connectivity = ConnectivityMetrics(
    connection_attempted=True,
    connection_successful=True,
    connection_duration_ms=150.0,
    connection_error=None  # or error message if failed
)
```

**Fields:**
- `connection_attempted`: Whether connection was attempted
- `connection_successful`: Whether connection succeeded
- `connection_duration_ms`: Time to establish connection
- `connection_error`: Error message if connection failed

### Layer 2: Extraction Metrics (Pipeline-Specific)

#### Web Scraping Extraction

For HTTP-based web scrapers (BBC pipeline):

```python
from src.somali_dialect_classifier.utils.metrics import WebScrapingExtractionMetrics

extraction = WebScrapingExtractionMetrics(
    http_requests_attempted=100,
    http_requests_successful=95,
    http_status_distribution={200: 95, 404: 3, 500: 2},
    pages_parsed=95,
    content_extracted=90
)

# Computed properties
extraction.http_success_rate  # 0.95 (95%)
extraction.content_extraction_rate  # 0.95 (90/95)
```

#### File Processing Extraction

For file-based processors (Wikipedia, Språkbanken):

```python
from src.somali_dialect_classifier.utils.metrics import FileProcessingExtractionMetrics

extraction = FileProcessingExtractionMetrics(
    files_discovered=10,
    files_processed=8,
    files_failed=2,
    records_extracted=1000,
    extraction_errors={"corrupted_file": 2}
)

# Computed properties
extraction.file_extraction_rate  # 0.8 (8/10)
extraction.extraction_efficiency  # 125.0 (1000/8 records per file)
```

#### Stream Processing Extraction

For API streaming (HuggingFace):

```python
from src.somali_dialect_classifier.utils.metrics import StreamProcessingExtractionMetrics

extraction = StreamProcessingExtractionMetrics(
    stream_opened=True,
    total_records_available=1000000,  # If known
    batches_attempted=100,
    batches_completed=98,
    batches_failed=2,
    records_fetched=5000
)

# Computed properties
extraction.stream_reliability  # 0.98 (98/100)
extraction.dataset_coverage_rate  # 0.005 (5000/1000000)
extraction.stream_completion_rate  # 0.98 (98/100)
```

### Layer 3: Quality Metrics (Common to All Pipelines)

Tracks quality filtering and validation:

```python
from src.somali_dialect_classifier.utils.metrics import QualityMetrics

quality = QualityMetrics(
    records_received=1000,
    records_passed_filters=800,
    filter_breakdown={
        "too_short": 150,
        "invalid_language": 30,
        "low_quality": 20
    }
)

# Computed properties
quality.quality_pass_rate  # 0.8 (800/1000)
quality.total_filtered  # 200
```

### Layer 4: Volume Metrics (Common to All Pipelines)

Tracks data volume:

```python
from src.somali_dialect_classifier.utils.metrics import VolumeMetrics

volume = VolumeMetrics(
    records_written=800,
    bytes_downloaded=4000000,  # 4 MB
    total_chars=2000000
)

# Computed properties
volume.avg_record_size_bytes  # 5000.0 (4MB / 800)
volume.avg_record_length_chars  # 2500.0 (2M / 800)
```

### Using Layered Metrics

The `MetricsCollector` automatically builds layered metrics:

```python
from src.somali_dialect_classifier.utils.metrics import MetricsCollector, PipelineType

collector = MetricsCollector(
    run_id="my_run",
    source="BBC-Somali",
    pipeline_type=PipelineType.WEB_SCRAPING
)

# Collect metrics as usual
collector.increment("urls_fetched", 100)
collector.increment("records_written", 80)

# Get layered metrics
layered = collector.get_layered_metrics()

# Access layers
print(f"Connection successful: {layered['connectivity']['connection_successful']}")
print(f"HTTP success rate: {layered['extraction']['http_requests_successful']} / {layered['extraction']['http_requests_attempted']}")
print(f"Quality pass rate: {layered['quality']['records_passed_filters']} / {layered['quality']['records_received']}")
print(f"Records written: {layered['volume']['records_written']}")
```

## Type Safety & Validation (Phase 3)

### Validation Methods

Each metric class has a `validate()` method that checks logical consistency:

```python
from src.somali_dialect_classifier.utils.metrics import WebScrapingExtractionMetrics

extraction = WebScrapingExtractionMetrics(
    http_requests_attempted=100,
    http_requests_successful=105  # ERROR: successful > attempted!
)

is_valid, error = extraction.validate()
print(f"Valid: {is_valid}")  # False
print(f"Error: {error}")  # "Successful requests (105) exceed attempted (100)"
```

**Validation catches:**
- Successful operations > attempted operations
- Negative durations or counts
- Rates outside [0, 1] bounds
- Cross-field inconsistencies

### Factory Functions

Use `create_extraction_metrics()` to ensure type safety:

```python
from src.somali_dialect_classifier.utils.metrics import (
    create_extraction_metrics,
    PipelineType,
    WebScrapingExtractionMetrics
)

# Type-safe creation
extraction = create_extraction_metrics(
    PipelineType.WEB_SCRAPING,
    http_requests_attempted=100,
    http_requests_successful=95
)

assert isinstance(extraction, WebScrapingExtractionMetrics)  # True

# Prevents mixing types
try:
    extraction = create_extraction_metrics(
        "invalid_type",
        http_requests_attempted=100
    )
except ValueError as e:
    print(f"Caught error: {e}")  # "Unknown pipeline type: invalid_type"
```

### Cross-Layer Validation

Validate all layers together:

```python
from src.somali_dialect_classifier.utils.metrics import validate_layered_metrics

is_valid, errors = validate_layered_metrics(
    connectivity=connectivity,
    extraction=extraction,
    quality=quality,
    volume=volume
)

if not is_valid:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

**Cross-layer checks:**
- Volume records ≤ quality passed records
- If connectivity failed, extraction metrics should be zero
- Filter breakdown sum ≤ total filtered

### Schema Versioning

JSON exports now include schema version:

```python
collector.export_json("metrics.json")
```

**Output structure:**
```json
{
  "_schema_version": "3.0",
  "_pipeline_type": "web_scraping",
  "_timestamp": "2025-10-26T10:30:00Z",
  "_run_id": "my_run",
  "_source": "BBC-Somali",
  "layered_metrics": {
    "connectivity": {...},
    "extraction": {...},
    "quality": {...},
    "volume": {...}
  },
  "legacy_metrics": {
    "snapshot": {...},
    "statistics": {...}
  },
  "_validation_warnings": []  // If validation found issues
}
```

## Prometheus Export (Phase 3)

Export metrics in Prometheus text format for production monitoring:

```python
collector.export_prometheus("metrics.prom")
```

**Output format:**
```prometheus
# HELP pipeline_connection_successful Whether connection to data source succeeded
# TYPE pipeline_connection_successful gauge
pipeline_connection_successful{source="BBC-Somali",pipeline_type="web_scraping",run_id="my_run"} 1

# HELP pipeline_http_requests_attempted Total HTTP requests attempted
# TYPE pipeline_http_requests_attempted counter
pipeline_http_requests_attempted{source="BBC-Somali",pipeline_type="web_scraping",run_id="my_run"} 100

# HELP pipeline_quality_pass_rate Quality filter pass rate (0-1)
# TYPE pipeline_quality_pass_rate gauge
pipeline_quality_pass_rate{source="BBC-Somali",pipeline_type="web_scraping",run_id="my_run"} 0.8

# ... more metrics
```

### Prometheus Scrape Configuration

Example Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'somali-nlp-pipeline'
    static_configs:
      - targets: ['localhost:9090']
    file_sd_configs:
      - files:
        - '/path/to/metrics/*.prom'
        refresh_interval: 30s
```

### Available Prometheus Metrics

**Connectivity (Layer 1):**
- `pipeline_connection_attempted` (gauge)
- `pipeline_connection_successful` (gauge)
- `pipeline_connection_duration_ms` (gauge)

**Web Scraping Extraction (Layer 2):**
- `pipeline_http_requests_attempted` (counter)
- `pipeline_http_requests_successful` (counter)
- `pipeline_http_success_rate` (gauge)
- `pipeline_pages_parsed` (counter)
- `pipeline_content_extracted` (counter)
- `pipeline_http_status_total` (counter with `status_code` label)

**File Processing Extraction (Layer 2):**
- `pipeline_files_discovered` (counter)
- `pipeline_files_processed` (counter)
- `pipeline_files_failed` (counter)
- `pipeline_file_extraction_rate` (gauge)
- `pipeline_records_extracted` (counter)
- `pipeline_extraction_efficiency` (gauge)

**Stream Processing Extraction (Layer 2):**
- `pipeline_stream_opened` (gauge)
- `pipeline_batches_attempted` (counter)
- `pipeline_batches_completed` (counter)
- `pipeline_batches_failed` (counter)
- `pipeline_stream_reliability` (gauge)
- `pipeline_records_fetched` (counter)
- `pipeline_dataset_coverage_rate` (gauge, if known)

**Quality (Layer 3):**
- `pipeline_records_received` (counter)
- `pipeline_records_passed_filters` (counter)
- `pipeline_quality_pass_rate` (gauge)
- `pipeline_records_filtered` (counter)
- `pipeline_filter_reason_total` (counter with `reason` label)

**Volume (Layer 4):**
- `pipeline_records_written_total` (counter)
- `pipeline_bytes_downloaded_total` (counter)
- `pipeline_total_chars_total` (counter)
- `pipeline_avg_record_size_bytes` (gauge)
- `pipeline_avg_record_length_chars` (gauge)

**Performance:**
- `pipeline_deduplication_rate` (gauge)
- `pipeline_fetch_duration_ms_mean` (gauge)
- `pipeline_fetch_duration_ms_p95` (gauge)
- `pipeline_records_per_minute` (gauge)
- `pipeline_bytes_per_second` (gauge)

## Migration Guide

### For New Code (Recommended)

Use layered metrics from the start:

```python
from src.somali_dialect_classifier.utils.metrics import (
    MetricsCollector,
    PipelineType
)

# 1. Create collector with pipeline type
collector = MetricsCollector(
    run_id="my_run",
    source="BBC-Somali",
    pipeline_type=PipelineType.WEB_SCRAPING
)

# 2. Collect metrics as usual
collector.increment("urls_fetched", 100)
collector.record_http_status(200)

# 3. Export with layered metrics (default)
collector.export_json("metrics.json")  # Includes layered + legacy
collector.export_prometheus("metrics.prom")  # New!
```

### For Existing Code (Gradual Migration)

**Option 1: No Changes Required**

Existing code continues to work:

```python
# Phase 1 code (still works!)
collector = MetricsCollector("run_id", "BBC")
collector.increment("urls_fetched", 100)
snapshot = collector.get_snapshot()
stats = snapshot.calculate_statistics()

# All Phase 1 metrics still available
assert "http_request_success_rate" in stats
```

**Option 2: Add Layered Metrics Gradually**

Add layered metrics alongside existing code:

```python
# Existing Phase 1 code
collector = MetricsCollector("run_id", "BBC", PipelineType.WEB_SCRAPING)
collector.increment("urls_fetched", 100)

# NEW: Access layered metrics
layered = collector.get_layered_metrics()

# Use both
legacy_stats = collector.get_snapshot().calculate_statistics()
print(f"Legacy HTTP success: {legacy_stats['http_request_success_rate']:.1%}")
print(f"Layered HTTP success: {layered['extraction']['http_requests_successful']} / {layered['extraction']['http_requests_attempted']}")
```

**Option 3: Export Legacy Format Only**

Disable layered metrics in export if needed:

```python
collector.export_json("metrics.json", include_layered=False)
# Only legacy metrics exported (no layered_metrics field)
```

### Updating Tests

Phase 1 tests continue to pass. Add Phase 2/3 tests for new features:

```python
def test_layered_metrics():
    """Test new layered metrics."""
    collector = MetricsCollector("test", "BBC", PipelineType.WEB_SCRAPING)
    collector.increment("urls_fetched", 10)

    layered = collector.get_layered_metrics()

    assert "connectivity" in layered
    assert "extraction" in layered
    assert layered["connectivity"]["connection_successful"] is True
```

## Backward Compatibility

### 100% Backward Compatible

All Phase 1 code continues to work without modification:

| Phase 1 Feature | Still Works? | Notes |
|----------------|--------------|-------|
| `MetricsCollector` API | ✅ Yes | All methods unchanged |
| Phase 1 metrics | ✅ Yes | Still in `legacy_metrics.statistics` |
| `get_snapshot()` | ✅ Yes | Returns same `MetricSnapshot` |
| `calculate_statistics()` | ✅ Yes | Returns same stats dict |
| JSON export | ✅ Yes | Legacy format in `legacy_metrics` |
| Metric semantics | ✅ Yes | Still in `_metric_semantics` |
| Deprecation warnings | ✅ Yes | Still in `_deprecation_warnings` |

### What's Added (Not Breaking)

- `get_layered_metrics()` - NEW method
- `export_prometheus()` - NEW method
- `export_json(..., include_layered=True)` - NEW parameter (default True)
- Schema versioning fields in JSON exports
- Validation warnings in JSON exports

### Deprecation Plan

**Nothing deprecated in Phase 2/3.**

Phase 1 deprecations remain:
- `fetch_success_rate` (deprecated in Phase 1, aliased to pipeline-specific metrics)
- Will be removed in next major version

## Examples

### Example 1: Web Scraping with Validation

```python
from src.somali_dialect_classifier.utils.metrics import (
    MetricsCollector,
    PipelineType,
    validate_layered_metrics,
    create_extraction_metrics,
    ConnectivityMetrics,
    QualityMetrics,
    VolumeMetrics
)

# Collect metrics
collector = MetricsCollector("bbc_run", "BBC-Somali", PipelineType.WEB_SCRAPING)

for url in urls:
    try:
        response = fetch(url)
        collector.record_http_status(response.status_code)
        collector.increment("urls_fetched")

        content = extract_content(response)
        if content:
            collector.increment("urls_processed")

            if is_high_quality(content):
                collector.increment("records_written")
            else:
                collector.record_filter_reason("low_quality")
    except Exception as e:
        collector.increment("urls_failed")
        collector.record_error(type(e).__name__)

# Export and validate
layered = collector.get_layered_metrics()

connectivity = ConnectivityMetrics(**layered["connectivity"])
extraction = create_extraction_metrics(PipelineType.WEB_SCRAPING, **layered["extraction"])
quality = QualityMetrics(**layered["quality"])
volume = VolumeMetrics(**layered["volume"])

is_valid, errors = validate_layered_metrics(connectivity, extraction, quality, volume)

if not is_valid:
    print("⚠️ Metric validation warnings:")
    for error in errors:
        print(f"  - {error}")

# Export both formats
collector.export_json("metrics.json")  # JSON with layered + legacy
collector.export_prometheus("metrics.prom")  # Prometheus format
```

### Example 2: File Processing with Efficiency Tracking

```python
from src.somali_dialect_classifier.utils.metrics import (
    MetricsCollector,
    PipelineType
)

collector = MetricsCollector("wiki_run", "Wikipedia", PipelineType.FILE_PROCESSING)

dump_files = discover_dump_files()
collector.increment("files_discovered", len(dump_files))

for dump_file in dump_files:
    try:
        records = extract_records(dump_file)
        collector.increment("files_processed")
        collector.increment("records_extracted", len(records))

        for record in records:
            if passes_quality(record):
                write_record(record)
                collector.increment("records_written")
            else:
                collector.record_filter_reason("quality_check_failed")
    except Exception as e:
        collector.record_error(type(e).__name__)

# Check extraction efficiency
layered = collector.get_layered_metrics()
extraction = layered["extraction"]
efficiency = extraction["records_extracted"] / max(extraction["files_processed"], 1)

print(f"Extraction efficiency: {efficiency:.1f} records per file")

if efficiency < 100:
    print("⚠️ Low extraction efficiency - investigate dump file issues")
```

### Example 3: Stream Processing with Coverage Tracking

```python
from src.somali_dialect_classifier.utils.metrics import (
    MetricsCollector,
    PipelineType
)

collector = MetricsCollector("hf_run", "HuggingFace-C4", PipelineType.STREAM_PROCESSING)

# Open stream
try:
    dataset = load_dataset("c4", "so", streaming=True)
    collector.increment("datasets_opened")

    # Process in batches
    for batch in dataset.iter(batch_size=100):
        try:
            collector.increment("batches_completed")
            collector.increment("records_fetched", len(batch))

            for record in batch:
                if is_somali(record):
                    collector.increment("records_processed")
                    collector.increment("records_written")
                else:
                    collector.record_filter_reason("wrong_language")
        except Exception as e:
            collector.increment("batches_failed")

except Exception as e:
    print(f"Stream connection failed: {e}")
    # Metrics will show stream_opened=False

# Check coverage
layered = collector.get_layered_metrics()
extraction = layered["extraction"]

if extraction["stream_opened"]:
    reliability = extraction["batches_completed"] / max(extraction["batches_attempted"], 1)
    print(f"Stream reliability: {reliability:.1%}")
else:
    print("❌ Stream connection failed")
```

## FAQ

### Q: Do I need to update my existing code?

**A:** No. Phase 2/3 is 100% backward compatible. All existing code continues to work.

### Q: Should I use layered metrics or legacy metrics?

**A:** For new code, use layered metrics (`get_layered_metrics()`). They provide better structure and validation. For existing code, no changes needed unless you want the new features.

### Q: What's the difference between schema versions?

**A:**
- Schema 1.0: Original flat metrics (before Phase 1)
- Schema 2.0: Phase 1 - semantic metrics per pipeline type
- Schema 3.0: Phase 2/3 - layered metrics with validation

### Q: Can I disable layered metrics?

**A:** Yes, use `export_json(path, include_layered=False)` to export only legacy format.

### Q: How do I know if my metrics are valid?

**A:** Check the JSON export for `_validation_warnings`. If present, fix the issues. Or manually validate:

```python
from src.somali_dialect_classifier.utils.metrics import validate_layered_metrics

layered = collector.get_layered_metrics()
# ... reconstruct metric objects
is_valid, errors = validate_layered_metrics(conn, extr, qual, vol)
```

### Q: Can I mix web scraping and file processing metrics?

**A:** No. The factory function `create_extraction_metrics()` prevents this:

```python
# This raises ValueError
extraction = create_extraction_metrics(
    PipelineType.WEB_SCRAPING,
    files_discovered=10  # Wrong! These are file processing fields
)
```

### Q: How do I set up Prometheus scraping?

**A:** Export metrics to `.prom` files and configure Prometheus file service discovery:

```yaml
scrape_configs:
  - job_name: 'somali-nlp'
    file_sd_configs:
      - files: ['/metrics/*.prom']
```

### Q: What happens to old JSON exports?

**A:** They remain valid. New exports include both layered and legacy metrics. Old consumers can continue reading `legacy_metrics.statistics`.

### Q: When will deprecated metrics be removed?

**A:** Phase 1 deprecated `fetch_success_rate` will be removed in the next major version. Phase 2/3 introduced no new deprecations.

### Q: Can I contribute new metrics?

**A:** Yes! Add to the appropriate layer:
- Connectivity issues → `ConnectivityMetrics`
- Pipeline-specific extraction → Extend extraction metric classes
- Cross-pipeline quality → `QualityMetrics`
- Volume tracking → `VolumeMetrics`

---

**Questions or issues?** Open an issue on GitHub or contact the maintainers.
