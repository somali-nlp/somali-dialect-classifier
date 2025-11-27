# Metrics Schema Specification

**Schema specification for metrics files in the Somali NLP data pipeline ensuring data integrity and reliable dashboard aggregation.**

**Last Updated:** 2025-11-21

This document defines the schema specification for metrics files in the Somali NLP data pipeline. All metrics files must conform to this schema to ensure data integrity and reliable dashboard aggregation.

## Schema Version: 3.0

Last Updated: 2025-10-27

## Overview

The metrics schema provides a standardized format for tracking pipeline execution metrics across all data sources. It uses **layered metrics** that separate concerns by operational phase:

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
- `bytes_downloaded` (int, ≥0): Total bytes downloaded (see policy below)
- `total_chars` (int, ≥0): Total characters in all records

**bytes_downloaded Policy** (Clarified in Phase B, 2025-11-13):

The `bytes_downloaded` metric has different meanings depending on the source type:

| Source | Value | Meaning |
|--------|-------|---------|
| **Wikipedia** | Actual bytes | Tracks file download size (accurate) |
| **BBC** | 0 | Not tracked (web scraping, no meaningful byte count) |
| **HuggingFace** | 0 | Not tracked (streaming dataset, no file download) |
| **Språkbanken** | 0 | Not tracked (API-based access, no file download) |
| **TikTok** | 0 | Not tracked (API-based comments, no file download) |

**Why 0 for non-file sources?**
- `0` explicitly means "not tracked", not "zero bytes downloaded"
- File-based sources (Wikipedia) can accurately measure bytes
- Web scraping and API sources have no meaningful byte metric (HTML overhead, API responses, etc.)
- Recommendation: Future enhancement could use `null` instead of `0` for clarity

**Example**:
```json
{
  "source": "BBC-Somali",
  "volume": {
    "records_written": 100,
    "bytes_downloaded": 0,       // Not tracked (web scraping)
    "total_chars": 125000
  }
}

{
  "source": "Wikipedia-Somali",
  "volume": {
    "records_written": 5000,
    "bytes_downloaded": 125000000,  // Actual file size (125 MB)
    "total_chars": 3500000
  }
}
```

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

## Migration Guide

### Upgrading from Version 2.0

Version 2.0 metrics are supported via `legacy_metrics` wrapper. To migrate:

1. Keep existing `snapshot` and `statistics` sections
2. Add new `layered_metrics` section
3. Set `_schema_version` to "3.0"
4. Run validation to ensure compliance

### Example Migration

**Before (Version 2.0)**:
```json
{
  "_schema_version": "2.0",
  "_pipeline_type": "web_scraping",
  "snapshot": {
    "records_written": 100,
    "http_requests_successful": 95
  },
  "statistics": {
    "http_request_success_rate": 0.95
  }
}
```

**After (Version 3.0)**:
```json
{
  "_schema_version": "3.0",
  "_pipeline_type": "web_scraping",
  "layered_metrics": {
    "connectivity": {
      "connection_attempted": true,
      "connection_successful": true,
      "connection_duration_ms": 1200.5,
      "connection_error": null
    },
    "extraction": {
      "http_requests_attempted": 100,
      "http_requests_successful": 95,
      "http_status_distribution": {"200": 95, "404": 5}
    },
    "quality": {
      "records_received": 95,
      "records_passed_filters": 90,
      "filter_breakdown": {"min_length_filter": 5}
    },
    "volume": {
      "records_written": 90,
      "bytes_downloaded": 500000,
      "total_chars": 45000
    }
  },
  "legacy_metrics": {
    "snapshot": {
      "records_written": 100,
      "http_requests_successful": 95
    },
    "statistics": {
      "http_request_success_rate": 0.95
    }
  }
}
```

## Deprecated Metrics

The following metrics are deprecated and should not be used in new implementations:

- `success_rate` → Use `http_request_success_rate`
- `fetch_success_rate` → Use `http_request_success_rate`
- `dedup_rate` → Use `deduplication_rate`

These fields may still appear in legacy_metrics sections for backward compatibility but should not be used as primary metrics.

## Best Practices

1. **Always validate before committing**: Run `validate_metrics_schema.py` before committing metrics files
2. **Include filter breakdown**: Essential for quality monitoring and debugging filter issues
3. **Use null for missing values**: Don't use 0 or empty strings for genuinely missing data
4. **Preserve run_id uniqueness**: Ensures metrics can be accurately tracked and prevents duplicate data
5. **Include source in all records**: Enables proper aggregation and source-specific analysis
6. **Set accurate timestamps**: Use ISO 8601 format with timezone information
7. **Document custom filters**: Add new filters to filter_breakdown when they're added to the pipeline

## Schema Field Reference

### Metadata Fields (Required)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `_schema_version` | string | Schema version number | `"3.0"` |
| `_pipeline_type` | string | Type of pipeline | `"web_scraping"`, `"file_processing"`, `"stream_processing"` |
| `_timestamp` | string (ISO 8601) | When the pipeline ran | `"2025-10-26T16:23:45.383125+00:00"` |
| `_run_id` | string | Unique identifier for this run | `"20251026_155342_bbc-somali_6ca368f7"` |
| `_source` | string | Data source name | `"BBC-Somali"`, `"Wikipedia-Somali"` |

### Connectivity Layer Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `connection_attempted` | boolean | required | Whether connection was attempted |
| `connection_successful` | boolean | required | Whether connection succeeded |
| `connection_duration_ms` | float | ≥ 0 | Connection establishment time in milliseconds |
| `connection_error` | string or null | optional | Error message if connection failed |

### Extraction Layer Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `http_requests_attempted` | integer | ≥ 0 | Total HTTP requests attempted |
| `http_requests_successful` | integer | ≥ 0, ≤ attempted | Successful HTTP requests (2xx status) |
| `http_status_distribution` | object | keys: status codes | Count of each HTTP status code |
| `pages_parsed` | integer | ≥ 0 | Pages successfully parsed |
| `content_extracted` | integer | ≥ 0 | Records with content extracted |

### Quality Layer Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `records_received` | integer | ≥ 0 | Records entering quality filters |
| `records_passed_filters` | integer | ≥ 0, ≤ received | Records passing all filters |
| `filter_breakdown` | object | keys: filter names | Count of records dropped by each filter |

### Volume Layer Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `records_written` | integer | ≥ 0 | Records written to silver dataset |
| `bytes_downloaded` | integer | ≥ 0 | Total bytes downloaded |
| `total_chars` | integer | ≥ 0 | Total characters in all records |

## Examples

### Complete Example: Web Scraping Pipeline

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
      "http_requests_attempted": 150,
      "http_requests_successful": 145,
      "http_status_distribution": {
        "200": 145,
        "404": 3,
        "500": 2
      },
      "pages_parsed": 145,
      "content_extracted": 142
    },
    "quality": {
      "records_received": 142,
      "records_passed_filters": 125,
      "filter_breakdown": {
        "min_length_filter": 12,
        "langid_filter": 5
      }
    },
    "volume": {
      "records_written": 125,
      "bytes_downloaded": 2500000,
      "total_chars": 312500
    }
  },

  "legacy_metrics": {
    "snapshot": {
      "records_written": 125,
      "http_requests_attempted": 150,
      "http_requests_successful": 145
    },
    "statistics": {
      "http_request_success_rate": 0.9667,
      "content_extraction_success_rate": 0.9793,
      "quality_pass_rate": 0.8803,
      "deduplication_rate": 0.0,
      "throughput": {
        "urls_per_second": 0.025,
        "bytes_per_second": 416.67,
        "records_per_minute": 1.25
      },
      "text_length_stats": {
        "min": 50,
        "max": 5000,
        "mean": 2500,
        "median": 2400,
        "p95": 4500,
        "p99": 4800
      }
    }
  }
}
```

### Example: File Processing Pipeline

```json
{
  "_schema_version": "3.0",
  "_pipeline_type": "file_processing",
  "_timestamp": "2025-10-26T18:30:00.000000+00:00",
  "_run_id": "20251026_183000_wikipedia-somali_abc123",
  "_source": "Wikipedia-Somali",

  "layered_metrics": {
    "connectivity": {
      "connection_attempted": true,
      "connection_successful": true,
      "connection_duration_ms": 850.25,
      "connection_error": null
    },
    "extraction": {
      "http_requests_attempted": 1,
      "http_requests_successful": 1,
      "http_status_distribution": {"200": 1},
      "pages_parsed": 5432,
      "content_extracted": 5400
    },
    "quality": {
      "records_received": 5400,
      "records_passed_filters": 4850,
      "filter_breakdown": {
        "min_length_filter": 450,
        "langid_filter": 75,
        "namespace_filter": 25
      }
    },
    "volume": {
      "records_written": 4850,
      "bytes_downloaded": 125000000,
      "total_chars": 15500000
    }
  }
}
```


---

---

## Table of Contents

- [Schema Version: 3.0](#schema-version-30)
- [Overview](#overview)
- [File Types](#file-types)
  - [1. Processing Files (`*_processing.json`)](#1-processing-files-processingjson)
  - [2. Consolidated Metrics (`all_metrics.json`)](#2-consolidated-metrics-allmetricsjson)
  - [3. Dashboard Summary (`summary.json`)](#3-dashboard-summary-summaryjson)
- [Layered Metrics Details](#layered-metrics-details)
  - [Connectivity Layer](#connectivity-layer)
  - [Extraction Layer](#extraction-layer)
  - [Quality Layer](#quality-layer)
  - [Volume Layer](#volume-layer)
- [Statistics Section](#statistics-section)
  - [Success Rates (0.0 - 1.0)](#success-rates-00-10)
  - [Throughput Metrics (≥0)](#throughput-metrics-0)
  - [Statistical Distributions (optional)](#statistical-distributions-optional)
- [Validation](#validation)
  - [Automatic Validation](#automatic-validation)
  - [Schema Enforcement](#schema-enforcement)
  - [CI Integration](#ci-integration)
- [Migration Guide](#migration-guide)
  - [Upgrading from Version 2.0](#upgrading-from-version-20)
  - [Example Migration](#example-migration)
- [Deprecated Metrics](#deprecated-metrics)
- [Best Practices](#best-practices)
- [Schema Field Reference](#schema-field-reference)
  - [Metadata Fields (Required)](#metadata-fields-required)
  - [Connectivity Layer Fields](#connectivity-layer-fields)
  - [Extraction Layer Fields](#extraction-layer-fields)
  - [Quality Layer Fields](#quality-layer-fields)
  - [Volume Layer Fields](#volume-layer-fields)
- [Examples](#examples)
  - [Complete Example: Web Scraping Pipeline](#complete-example-web-scraping-pipeline)
  - [Example: File Processing Pipeline](#example-file-processing-pipeline)
- [Filter Telemetry](#filter-telemetry)
  - [Overview](#overview)
  - [Field Specification](#field-specification)
  - [Filter Keys and Labels](#filter-keys-and-labels)
  - [Validation Rules](#validation-rules)
  - [Examples by Source](#examples-by-source)
    - [Web Scraping (BBC-Somali)](#web-scraping-bbc-somali)
    - [Encyclopedia (Wikipedia-Somali)](#encyclopedia-wikipedia-somali)
    - [Social Media (TikTok-Somali)](#social-media-tiktok-somali)
    - [Streaming Dataset (HuggingFace MC4)](#streaming-dataset-huggingface-mc4)
  - [Complete Example with Context](#complete-example-with-context)
  - [Interpretation Guide](#interpretation-guide)
  - [Dashboard Integration](#dashboard-integration)
  - [Adding New Filters](#adding-new-filters)
  - [Catalog Versioning (New in v2.0)](#catalog-versioning-new-in-v20)
  - [Historical Export to Parquet (New in v2.0)](#historical-export-to-parquet-new-in-v20)
  - [Cross-References](#cross-references)
- [Support](#support)
- [Support](#support)
- [Version History](#version-history)

---

## Filter Telemetry

### Overview

The `filter_breakdown` field within the Quality layer tracks how many records were rejected by each filter. This enables precise diagnosis of which quality checks are removing data.

### Field Specification

**Location:** `layered_metrics.quality.filter_breakdown`

**Type:** Object (map of filter_name → count)

**Required:** No (optional, may be absent if no filters applied)

**Example:**
```json
{
  "min_length_filter": 45,
  "langid_filter": 15,
  "topic_lexicon_enrichment_filter": 10,
  "emoji_only_comment": 8,
  "empty_after_cleaning": 3
}
```

**IMPORTANT:** The filter_breakdown field must accurately represent filter rejections:
- **Must be present** when filters are applied and records are rejected
- **May be empty** `{}` only when no filters applied OR all records pass filters
- **Never omit** filter keys that rejected records (causes inaccurate metrics)

**Common Errors:**
- ❌ Missing filter_breakdown when filters ran
- ❌ Incomplete filter_breakdown (missing filters that rejected records)
- ❌ Using `null` instead of `{}` for empty breakdown
- ✅ Complete filter_breakdown with all active filter keys

### Filter Keys and Labels

All filter keys are defined in the central filter catalog: `src/somali_dialect_classifier/pipeline/filters/catalog.py`

The catalog maps filter keys to human-readable labels:

| Filter Key | Label | Category | Description |
|------------|-------|----------|-------------|
| `min_length_filter` | Minimum length (50 chars) | length | Text must be at least 50 characters |
| `langid_filter` | Language ID (non-Somali) | language | Content must be primarily Somali |
| `empty_after_cleaning` | Empty after cleaning | content | Text must contain non-whitespace after cleanup |
| `emoji_only_comment` | Emoji-only comment | content | Removes comments with only emojis (TikTok) |
| `text_too_short_after_cleanup` | Very short text (<3 chars) | length | Removes very short text (TikTok) |
| `topic_lexicon_enrichment_filter` | Topic lexicon enrichment | enrichment | Enriches with topic markers (not filtering, see Phase B) |
| `namespace_filter` | Wikipedia namespace exclusion | content | Skips non-article pages (Wikipedia) |

**Note on topic_lexicon_enrichment_filter:**
- Previously named `dialect_heuristic_filter` (renamed in Phase B, 2025-11-13)
- Performs **topic classification**, not dialect detection
- Typically used with `enrich_only=True` (does not reject records)
- May appear in filter_breakdown with count=0 if no rejections occurred

See [Filter Catalog Reference](filters.md) for the complete list.

### Validation Rules

**Constraints:**
- All counts must be integers >= 0
- Sum of all filter_breakdown counts ≤ `records_received`
- Each filter_breakdown entry represents records rejected, not passed

**Validation:**
```python
# All counts are non-negative
assert all(count >= 0 for count in filter_breakdown.values())

# Total rejected <= received
total_rejected = sum(filter_breakdown.values())
assert total_rejected <= records_received

# Consistency check
assert records_passed_filters == records_received - total_rejected
```

### Examples by Source

#### Web Scraping (BBC-Somali)

```json
"filter_breakdown": {
  "min_length_filter": 45,
  "langid_filter": 15,
  "topic_lexicon_enrichment_filter": 10
}
```

#### Encyclopedia (Wikipedia-Somali)

```json
"filter_breakdown": {
  "min_length_filter": 450,
  "langid_filter": 75,
  "namespace_filter": 25
}
```

#### Social Media (TikTok-Somali)

```json
"filter_breakdown": {
  "emoji_only_comment": 250,
  "text_too_short_after_cleanup": 85,
  "min_length_filter": 45,
  "langid_filter": 12,
  "empty_after_cleaning": 8
}
```

#### Streaming Dataset (HuggingFace MC4)

```json
"filter_breakdown": {
  "min_length_filter": 5000,
  "langid_filter": 1200
}
```

### Complete Example with Context

```json
{
  "_schema_version": "3.0",
  "_source": "TikTok-Somali",
  "_run_id": "20251101_132706_tiktok-somali_8fa6c534",
  "_timestamp": "2025-11-01T13:27:06.123456+00:00",
  "_pipeline_type": "stream_processing",

  "layered_metrics": {
    "connectivity": {
      "connection_attempted": true,
      "connection_successful": true,
      "connection_duration_ms": 2150.5,
      "connection_error": null
    },
    "extraction": {
      "http_requests_attempted": 5,
      "http_requests_successful": 5,
      "http_status_distribution": {"200": 5},
      "pages_parsed": 5,
      "content_extracted": 1200
    },
    "quality": {
      "records_received": 1200,
      "records_passed_filters": 726,
      "filter_breakdown": {
        "emoji_only_comment": 250,
        "text_too_short_after_cleanup": 85,
        "min_length_filter": 45,
        "langid_filter": 12,
        "empty_after_cleaning": 8
      }
    },
    "volume": {
      "records_written": 726,
      "bytes_downloaded": 0,
      "total_chars": 145000
    }
  }
}
```

### Interpretation Guide

**High filter counts indicate:**
- **min_length_filter**: Source has naturally short content (TikTok, tweets) or aggressive curation needed
- **langid_filter**: Source may have code-switching, transliteration issues, or language detection problems
- **emoji_only_comment**: Social media source with strong emoji culture (TikTok, Twitter) - expect 20-30%
- **empty_after_cleaning**: Text normalization is removing all content - may indicate preprocessing issue

**Zero filter counts indicate:**
- Source content naturally meets all quality thresholds
- Filters may be too lenient for the source
- Data quality is consistently high (Wikipedia, professional news)

### Dashboard Integration

The filter_breakdown is used by the dashboard to display:
- **Filter Footprint chart** - Stacked bar showing rejected vs. passed records
- **Filter Breakdown table** - Detailed view of each filter's rejection count
- **Quality Insights narrative** - Human-readable summary of filtering impact

See [Dashboard Architecture](../reference/dashboard-architecture.md) for how filter_breakdown is visualized.

### Adding New Filters

When adding a new filter to the pipeline:

1. **Define in catalog** → `src/somali_dialect_classifier/pipeline/filters/catalog.py`
2. **Implement filter logic** → Call `metrics.record_filter_reason("new_filter_key")`
3. **Update dashboard labels** → `dashboard/js/core/aggregates.js`
4. **Document in schema** → This file (add to table above)

Example:
```python
# Step 1: Add to catalog
FILTER_CATALOG["sentiment_filter"] = (
    "Negative sentiment",
    "Removes comments with negative sentiment",
    "semantic"
)

# Step 2: Use in processor
if detect_negative_sentiment(text):
    self.metrics.record_filter_reason("sentiment_filter")
    return None
```

### Catalog Versioning (New in v2.0)

The filter catalog is versioned and exported to JSON for dashboard consumption:

**Catalog location:** `src/somali_dialect_classifier/pipeline/filters/catalog.py`

**Export location:** `dashboard/data/filter_catalog.json`

**Schema:**
```json
{
  "filters": {
    "filter_key": {
      "label": "Human-readable label",
      "description": "Detailed description",
      "category": "length|language|content_quality|..."
    }
  },
  "categories": {
    "length": ["min_length_filter", "text_too_short_after_cleanup"],
    "language": ["langid_filter"],
    "content_quality": ["emoji_only_comment", "empty_after_cleaning"]
  },
  "version": "1.13.0",
  "last_updated": "2025-11-02T12:00:00Z"
}
```

**Generating catalog export:**
```bash
python scripts/export_filter_catalog.py
# Output: dashboard/data/filter_catalog.json
```

**Usage:** The dashboard dynamically loads this file to display filter labels, eliminating manual synchronization.

### Historical Export to Parquet (New in v2.0)

Filter breakdown data can be exported to Parquet for historical analysis:

**Export location:** `data/warehouse/filter_history.parquet/`

**Partition structure:** `source=<SOURCE>/month=<YYYY-MM>/part-0.parquet`

**Schema:**
```python
{
    "timestamp": datetime,           # ISO 8601 with timezone
    "source": str,                   # "Wikipedia-Somali", "TikTok-Somali", etc.
    "run_id": str,                   # Unique run identifier
    "filter_key": str,               # "min_length_filter", etc.
    "filter_label": str,             # "Minimum length (50 chars)"
    "filter_category": str,          # "length", "content_quality", etc.
    "records_filtered": int,         # Count for this filter
    "total_records_filtered": int,   # Total across all filters
    "records_written": int,          # Final record count
    "quality_pass_rate": float       # Overall quality rate (0.0-1.0)
}
```

**Exporting:**
```bash
python scripts/export_filters_to_parquet.py
```

**Querying with DuckDB:**
```python
import duckdb

con = duckdb.connect()
df = con.execute("""
    SELECT filter_label, SUM(records_filtered) AS total
    FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY filter_label
    ORDER BY total DESC
""").df()
```

See [Filter Analytics Guide](../howto/filter-analytics.md) for complete documentation.

### Cross-References

- **[Filter Catalog Reference](filters.md)** - Complete filter definitions and categories
- **[Processing Pipelines Guide](../howto/processing-pipelines.md#filter-telemetry)** - How-to for adding new filters
- **[TikTok Integration Guide](../howto/tiktok-integration.md#filter-telemetry)** - TikTok-specific filter stages
- **[Quality Layer Specification](#quality-layer)** - Field constraints and validation

## Support
## Support

For questions or issues with the schema:
- Open an issue on GitHub with the `metrics` label
- Check `src/somali_dialect_classifier/utils/metrics_schema.py` for the definitive schema implementation
- Run `pytest tests/test_metrics_consolidation.py` to verify your implementation against test cases
- See [Metrics Reference](metrics.md) for usage examples

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2025-10-27 | Added layered metrics architecture, filter breakdown tracking |
| 2.0 | 2025-10-21 | Added statistics section, computed metrics |
| 1.0 | 2025-10-01 | Initial snapshot-only schema |

## Related Documentation

- [Metrics Reference](metrics.md) - Pipeline metrics collection and interpretation
- [API Reference](api.md) - Pipeline API documentation
- [CI/CD Dashboard](../operations/cicd-dashboard.md) - Dashboard automation and deployment

---

**Maintainers**: Somali NLP Contributors
