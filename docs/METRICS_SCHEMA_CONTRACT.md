# Metrics Schema Contract (Phase 3)

This document defines the schema contract for metrics files in the Somali NLP data pipeline. All metrics files must conform to this schema to ensure data integrity and reliable dashboard aggregation.

## Schema Version: 3.0

Last Updated: 2025-10-27

## Overview

The Phase 3 schema introduces **layered metrics** that separate concerns by operational phase:
- **Connectivity**: Network connection and initial handshake
- **Extraction**: HTTP requests and content parsing
- **Quality**: Filter application and quality control
- **Volume**: Final output metrics

This separation enables:
- Precise fault isolation (network vs. parsing vs. quality issues)
- Granular performance monitoring
- Better error attribution

## File Types

### 1. Processing Files (`*_processing.json`)

**Location**: `data/metrics/*_processing.json`

**Purpose**: Individual run metrics from each pipeline execution

**Schema**: `Phase3MetricsSchema`

**Required Fields**:
```json
{
  "_schema_version": "3.0",
  "_pipeline_type": "web_scraping",
  "_timestamp": "2025-10-26T16:23:45.383125+00:00",
  "_run_id": "20251026_155342_bbc-somali_6ca368f7",
  "_source": "BBC-Somali",

  "layered_metrics": {
    "connectivity": {
      "connection_attempted": true,
      "connection_successful": true,
      "connection_duration_ms": 4420.66,
      "connection_error": null
    },
    "extraction": {
      "http_requests_attempted": 29,
      "http_requests_successful": 28,
      "http_status_distribution": {"200": 28},
      "pages_parsed": 28,
      "content_extracted": 28
    },
    "quality": {
      "records_received": 28,
      "records_passed_filters": 28,
      "filter_breakdown": {
        "min_length_filter": 2,
        "langid_filter": 1
      }
    },
    "volume": {
      "records_written": 28,
      "bytes_downloaded": 0,
      "total_chars": 136510
    }
  },

  "legacy_metrics": {
    "snapshot": { /* ... */ },
    "statistics": {
      "http_request_success_rate": 0.9655,
      "content_extraction_success_rate": 1.0,
      "quality_pass_rate": 0.93,
      "deduplication_rate": 0.0,
      "throughput": {
        "urls_per_second": 0.0155,
        "bytes_per_second": 0.0,
        "records_per_minute": 0.932
      }
    }
  }
}
```

### 2. Consolidated Metrics (`all_metrics.json`)

**Location**: `_site/data/all_metrics.json`

**Purpose**: Aggregated metrics from all runs for dashboard consumption

**Schema**: `ConsolidatedMetricsOutput`

**Structure**:
```json
{
  "count": 10,
  "records": 5000,
  "sources": ["BBC-Somali", "Wikipedia-Somali"],
  "metrics": [
    {
      "run_id": "...",
      "source": "...",
      "timestamp": "...",
      "records_written": 500,
      "total_chars": 50000,
      "http_request_success_rate": 0.95,
      "quality_pass_rate": 0.90,
      "filter_breakdown": {...}
    }
  ]
}
```

### 3. Dashboard Summary (`summary.json`)

**Location**: `_site/data/summary.json`

**Purpose**: High-level statistics for dashboard header

**Schema**: `DashboardSummary`

**Structure**:
```json
{
  "total_records": 5000,
  "total_urls_processed": 1000,
  "avg_success_rate": 0.95,
  "total_data_downloaded_bytes": 10000000,
  "sources": ["BBC-Somali", "Wikipedia-Somali"],
  "last_update": "2025-10-26T16:23:45.383125+00:00",
  "total_runs": 10,
  "source_breakdown": {
    "BBC-Somali": {
      "records": 2500,
      "runs": 5,
      "avg_success_rate": 0.96,
      "avg_quality_pass_rate": 0.91
    }
  }
}
```

## Layered Metrics Details

### Connectivity Layer

Tracks initial connection establishment:

- `connection_attempted` (bool): Whether connection was attempted
- `connection_successful` (bool): Whether connection succeeded
- `connection_duration_ms` (float, ≥0): Time to establish connection
- `connection_error` (string | null): Error message if connection failed

### Extraction Layer

Tracks HTTP requests and content parsing:

- `http_requests_attempted` (int, ≥0): Total HTTP requests attempted
- `http_requests_successful` (int, ≥0): Successful HTTP requests (2xx)
- `http_status_distribution` (object): Count of each status code
- `pages_parsed` (int, ≥0): Pages successfully parsed
- `content_extracted` (int, ≥0): Records with content extracted

**Invariant**: `http_requests_successful ≤ http_requests_attempted`

### Quality Layer

Tracks filter application and quality control:

- `records_received` (int, ≥0): Records entering quality filters
- `records_passed_filters` (int, ≥0): Records passing all filters
- `filter_breakdown` (object): Count of records dropped by each filter

**Invariant**: `records_passed_filters ≤ records_received`

**Example filter_breakdown**:
```json
{
  "min_length_filter": 150,
  "langid_filter": 42,
  "empty_after_cleaning": 8
}
```

### Volume Layer

Tracks final output metrics:

- `records_written` (int, ≥0): Records written to silver dataset
- `bytes_downloaded` (int, ≥0): Total bytes downloaded
- `total_chars` (int, ≥0): Total characters in all records

## Statistics Section

Computed metrics for dashboard visualization:

### Success Rates (0.0 - 1.0)

- `http_request_success_rate`: HTTP success (2xx / attempted)
- `content_extraction_success_rate`: Content extracted / HTTP success
- `quality_pass_rate`: Passed filters / records received
- `deduplication_rate`: Duplicates / total records

### Throughput Metrics (≥0)

- `urls_per_second`: URL processing rate
- `bytes_per_second`: Data download rate
- `records_per_minute`: Record processing rate

### Statistical Distributions (optional)

- `text_length_stats`: min, max, mean, median, p95, p99
- `fetch_duration_stats`: min, max, mean, median, p95, p99

## Validation

### Automatic Validation

All metrics files are automatically validated against the schema:

```bash
# Validate all metrics files
python scripts/validate_metrics_schema.py

# Strict mode (fail on warnings)
python scripts/validate_metrics_schema.py --strict
```

### Schema Enforcement

- **Type checking**: Pydantic models enforce field types
- **Range validation**: Numeric fields validated (≥0, rates in [0,1])
- **Invariant checking**: Relationships validated (success ≤ attempted)
- **Null guards**: Required fields cannot be null/missing

### CI Integration

Add to `.github/workflows/metrics-validation.yml`:

```yaml
- name: Validate Metrics Schema
  run: |
    python scripts/validate_metrics_schema.py --strict
```

## Migration from Phase 2

Phase 2 metrics are supported via `legacy_metrics` wrapper. To migrate:

1. Keep existing `snapshot` and `statistics` sections
2. Add new `layered_metrics` section
3. Set `_schema_version` to "3.0"
4. Run validation to ensure compliance

## Deprecated Metrics

The following metrics are deprecated and should not be used:

- `success_rate` → Use `http_request_success_rate`
- `fetch_success_rate` → Use `http_request_success_rate`
- `dedup_rate` → Use `deduplication_rate`

## Best Practices

1. **Always validate before committing**: Run `validate_metrics_schema.py`
2. **Include filter breakdown**: Essential for quality monitoring
3. **Use null for missing values**: Don't use 0 or empty strings
4. **Preserve run_id uniqueness**: Prevents duplicate data
5. **Include source in all records**: Enables proper aggregation

## Examples

See `tests/test_metrics_consolidation.py` for comprehensive examples.

## Support

For questions or issues with the schema:
- Open an issue on GitHub
- Check `src/somali_dialect_classifier/utils/metrics_schema.py` for definitive schema
- Run `pytest tests/test_metrics_consolidation.py` to verify implementation

## Version History

- **3.0** (2025-10-27): Added layered metrics, filter breakdown
- **2.0** (2025-10-21): Added statistics section
- **1.0** (2025-10-01): Initial snapshot-only schema
