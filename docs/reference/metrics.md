# Metrics Reference

**Comprehensive reference for pipeline metrics collection, reporting, and interpretation.**

**Last Updated:** 2025-11-21

Comprehensive reference for pipeline metrics collection, reporting, and interpretation.

## Overview

All data pipelines collect detailed metrics during execution to track performance, data quality, and pipeline health. Metrics are automatically exported to JSON files and used to generate quality reports.

## MLflow Headline Metrics

A subset of high-level metrics is logged directly to MLflow for dashboarding and health monitoring. These are available immediately after a run completes:

| Metric | Description |
|--------|-------------|
| `quality_pass_rate` | Percentage of records passing all quality filters |
| `records_processed` | Total records processed in this run |
| `records_written` | Records successfully written to silver dataset |
| `records_filtered` | Records dropped due to quality filters |

## Pipeline-Specific Metrics

Different pipeline types collect semantically accurate metrics that reflect their specific operational characteristics.

### Web Scraping Pipelines (BBC)

**Pipeline Type**: `web_scraping`

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `http_request_success_rate` | float | 0.0-1.0 | Network-level HTTP success (2xx responses / attempted requests) |
| `http_request_failure_rate` | float | 0.0-1.0 | HTTP request failures / attempted |
| `content_extraction_success_rate` | float | 0.0-1.0 | Content successfully extracted from HTTP 200 responses |
| `quality_pass_rate` | float | 0.0-1.0 | Records passing quality filters |
| `deduplication_rate` | float | 0.0-1.0 | Records filtered as duplicates |

**Example**:
```json
{
  "statistics": {
    "http_request_success_rate": 0.947,
    "content_extraction_success_rate": 1.0,
    "quality_pass_rate": 0.847,
    "deduplication_rate": 0.053
  }
}
```

### File Processing Pipelines (Wikipedia, Språkbanken)

**Pipeline Type**: `file_processing`

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `file_extraction_success_rate` | float | 0.0-1.0 | Files successfully extracted / discovered |
| `file_extraction_failure_rate` | float | 0.0-1.0 | Files failed extraction / discovered |
| `record_parsing_success_rate` | float | 0.0-1.0 | Records successfully parsed / extracted |
| `quality_pass_rate` | float | 0.0-1.0 | Records passing quality filters |
| `deduplication_rate` | float | 0.0-1.0 | Records filtered as duplicates |

**Example**:
```json
{
  "statistics": {
    "file_extraction_success_rate": 1.0,
    "record_parsing_success_rate": 1.0,
    "quality_pass_rate": 0.95,
    "deduplication_rate": 0.125
  }
}
```

### Stream Processing Pipelines (HuggingFace)

**Pipeline Type**: `stream_processing`

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `stream_connection_success_rate` | float | 0.0 or 1.0 | Stream connection established (boolean) |
| `record_retrieval_success_rate` | float | 0.0-1.0 | Records retrieved / requested |
| `dataset_coverage_rate` | float or null | 0.0-1.0 | Records consumed / total dataset size (if known) |
| `quality_pass_rate` | float | 0.0-1.0 | Records passing quality filters |
| `deduplication_rate` | float | 0.0-1.0 | Records filtered as duplicates |

**Example**:
```json
{
  "statistics": {
    "stream_connection_success_rate": 1.0,
    "record_retrieval_success_rate": 1.0,
    "dataset_coverage_rate": 0.002,
    "quality_pass_rate": 0.85,
    "deduplication_rate": 0.03
  }
}
```

## Common Metrics

These metrics are collected across all pipeline types:

### Quality Filtering

- **quality_pass_rate**: Percentage of records passing all quality filters
- **deduplication_rate**: Percentage of records removed as duplicates

### Text Statistics

- **text_length_stats**: Statistics about text lengths
  - `min`: Minimum text length (characters)
  - `max`: Maximum text length (characters)
  - `mean`: Average text length
  - `median`: Median text length
  - `total_chars`: Total characters processed

**Example**:
```json
{
  "text_length_stats": {
    "min": 52,
    "max": 15234,
    "mean": 342.5,
    "median": 298,
    "total_chars": 17125000
  }
}
```

## Metric Semantics

All metrics include a `_metric_semantics` field that provides human-readable descriptions:

```json
{
  "statistics": {
    "http_request_success_rate": 0.947,
    "_metric_semantics": {
      "http_request_success_rate": "Network-level HTTP success (2xx responses / attempted requests)"
    }
  }
}
```

## Accessing Metrics

### Programmatic Access

```python
from somali_dialect_classifier.utils.metrics import MetricsCollector

# Create collector
metrics = MetricsCollector(run_id, source)

# Collect metrics during pipeline execution
metrics.increment('urls_discovered')
metrics.record_fetch_duration(234.5)

# Get snapshot and calculate statistics
snapshot = metrics.get_snapshot()
stats = snapshot.calculate_statistics()

# Access specific metrics
http_success = stats["http_request_success_rate"]
quality_pass = stats["quality_pass_rate"]

# Check semantic meaning
semantics = stats["_metric_semantics"]
print(semantics["http_request_success_rate"])
```

### Exported JSON Files

Metrics are automatically exported to `data/metrics/`:

```bash
data/metrics/
├── 20251020_143045_wikipedia_somali_discovery.json
├── 20251020_143045_wikipedia_somali_extraction.json
└── 20251020_143045_wikipedia_somali_processing.json
```

Each file contains:
```json
{
  "run_id": "20251020_143045",
  "source": "Wikipedia-Somali",
  "phase": "processing",
  "timestamp": "2025-10-20T14:35:30Z",
  "statistics": {
    "file_extraction_success_rate": 1.0,
    "record_parsing_success_rate": 1.0,
    "quality_pass_rate": 0.95
  },
  "_metric_semantics": { ... }
}
```

## Quality Reports

Metrics are used to generate automated quality reports in `data/reports/`:

### Report Structure

```markdown
# Quality Report: Wikipedia-Somali

**Run ID**: 20251020_143045
**Pipeline Type**: file_processing
**Status**: ✅ HEALTHY

## Executive Summary

- **File Extraction Success Rate**: 100.0%
- **Record Parsing Success Rate**: 100.0%
- **Quality Filter Pass Rate**: 95.0%
- **Deduplication Rate**: 12.5%

## Health Indicators

✅ File extraction: 100.0% (Target: >90%)
✅ Record parsing: 100.0% (Target: >90%)
✅ Quality filtering: 95.0% (Target: >70%)
```

### Health Status Thresholds

- **✅ HEALTHY**: Success rate > 90%
- **⚠️ WARNING**: Success rate 70-90%
- **❌ CRITICAL**: Success rate < 70%

## Using Metrics for Debugging

### Identifying Issues

**Low HTTP Success Rate**:
```json
{
  "http_request_success_rate": 0.45
}
```
→ Check network connectivity, verify URLs are valid, review rate limiting

**Low Content Extraction Rate**:
```json
{
  "content_extraction_success_rate": 0.30
}
```
→ Website HTML structure may have changed, update scraping selectors

**Low Quality Pass Rate**:
```json
{
  "quality_pass_rate": 0.25
}
```
→ Review filter thresholds, check data quality at source

**High Deduplication Rate**:
```json
{
  "deduplication_rate": 0.80
}
```
→ Expected for incremental runs, or indicates source has stale content

## Best Practices

### 1. Monitor Trends Over Time

Track metrics across multiple runs to detect degradation:

```python
import pandas as pd
import glob

# Load all processing metrics
metrics_files = glob.glob("data/metrics/*_processing.json")
df = pd.DataFrame([json.load(open(f)) for f in metrics_files])

# Plot quality pass rate over time
df.plot(x='timestamp', y='quality_pass_rate')
```

### 2. Set Up Alerts

Configure alerts for critical thresholds:

```python
if stats["http_request_success_rate"] < 0.7:
    send_alert("HTTP success rate below 70%")
```

### 3. Compare Across Sources

```python
# Compare quality across different sources
sources = ["Wikipedia-Somali", "BBC-Somali", "HuggingFace-MC4"]
for source in sources:
    metrics = load_latest_metrics(source)
    print(f"{source}: {metrics['quality_pass_rate']:.1%}")
```

## Metric Calculation Details

### Success Rates

Success rates are calculated as:
```
success_rate = successful_items / total_attempted_items
```

**Important**: The denominator is *attempted* items, not *discovered* items. This ensures test limits don't artificially lower success rates.

### Deduplication Rate

```
deduplication_rate = duplicate_records / total_records_received
```

### Quality Pass Rate

```
quality_pass_rate = records_passing_filters / (total_records - duplicates)
```

Quality filtering happens *after* deduplication.

## Related Documentation

- [Data Pipeline Guide](../guides/data-pipeline.md) - Understanding the data flow
- [API Reference](api.md) - MetricsCollector and QualityReporter APIs
- [Dashboard Guide](../guides/dashboard.md) - Visualizing metrics

---

---

## Table of Contents

- [Overview](#overview)
- [Pipeline-Specific Metrics](#pipeline-specific-metrics)
  - [Web Scraping Pipelines (BBC)](#web-scraping-pipelines-bbc)
  - [File Processing Pipelines (Wikipedia, Språkbanken)](#file-processing-pipelines-wikipedia-språkbanken)
  - [Stream Processing Pipelines (HuggingFace)](#stream-processing-pipelines-huggingface)
- [Common Metrics](#common-metrics)
  - [Quality Filtering](#quality-filtering)
  - [Text Statistics](#text-statistics)
- [Metric Semantics](#metric-semantics)
- [Accessing Metrics](#accessing-metrics)
  - [Programmatic Access](#programmatic-access)
  - [Exported JSON Files](#exported-json-files)
- [Quality Reports](#quality-reports)
  - [Report Structure](#report-structure)
- [Executive Summary](#executive-summary)
- [Health Indicators](#health-indicators)
  - [Health Status Thresholds](#health-status-thresholds)
- [Using Metrics for Debugging](#using-metrics-for-debugging)
  - [Identifying Issues](#identifying-issues)
- [Best Practices](#best-practices)
  - [1. Monitor Trends Over Time](#1-monitor-trends-over-time)
  - [2. Set Up Alerts](#2-set-up-alerts)
  - [3. Compare Across Sources](#3-compare-across-sources)
- [Metric Calculation Details](#metric-calculation-details)
  - [Success Rates](#success-rates)
  - [Deduplication Rate](#deduplication-rate)
  - [Quality Pass Rate](#quality-pass-rate)

---

**Maintainers**: Somali NLP Contributors
