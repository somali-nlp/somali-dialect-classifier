# Metrics Refactoring Migration Guide - Phase 1

**Date:** 2025-10-26
**Version:** Phase 1 Implementation
**Breaking Changes:** None (backward compatible)

---

## Overview

This guide documents the Phase 1 refactoring of the metrics system, which introduces **semantically accurate metric names** for different pipeline types while maintaining backward compatibility.

### Problem Addressed

The previous system used a single metric name (`fetch_success_rate`) for fundamentally different operations:
- **BBC (web scraping):** HTTP request success rate
- **Wikipedia (file processing):** File extraction success rate
- **HuggingFace (streaming):** Stream connection success (boolean)

This semantic overloading made metrics difficult to interpret and prevented meaningful aggregation across sources.

---

## What Changed

### New Metric Names by Pipeline Type

#### Web Scraping Pipelines (BBC)

| Old Metric | New Metric | Description |
|------------|------------|-------------|
| `fetch_success_rate` | `http_request_success_rate` | Network-level HTTP success (2xx responses / attempted requests) |
| N/A (new) | `content_extraction_success_rate` | Content successfully extracted from HTTP responses |
| `fetch_failure_rate` | `http_request_failure_rate` | HTTP request failures |
| `quality_pass_rate` | `quality_pass_rate` | ✅ **No change** - Records passing quality filters |
| `deduplication_rate` | `deduplication_rate` | ✅ **No change** - Records filtered as duplicates |

#### File Processing Pipelines (Wikipedia, Språkbanken)

| Old Metric | New Metric | Description |
|------------|------------|-------------|
| `fetch_success_rate` | `file_extraction_success_rate` | File-level extraction success (local file I/O, not HTTP) |
| N/A (new) | `record_parsing_success_rate` | Record-level parsing success from extracted files |
| `fetch_failure_rate` | `file_extraction_failure_rate` | File extraction failures |
| `quality_pass_rate` | `quality_pass_rate` | ✅ **No change** - Records passing quality filters |
| `deduplication_rate` | `deduplication_rate` | ✅ **No change** - Records filtered as duplicates |

#### Stream Processing Pipelines (HuggingFace)

| Old Metric | New Metric | Description |
|------------|------------|-------------|
| `fetch_success_rate` | `stream_connection_success_rate` | Stream connection established (boolean: 1.0 or 0.0) |
| N/A (new) | `record_retrieval_success_rate` | Records successfully retrieved from stream |
| N/A (new) | `dataset_coverage_rate` | Fraction of total dataset consumed (if known, else `null`) |
| `fetch_failure_rate` | N/A (removed) | Replaced by inverse of `stream_connection_success_rate` |
| `quality_pass_rate` | `quality_pass_rate` | ✅ **No change** - Records passing quality filters |
| `deduplication_rate` | `deduplication_rate` | ✅ **No change** - Records filtered as duplicates |

---

## Bug Fixes

### BBC Test Limit Calculation Fix

**Problem:** The BBC web scraper was calculating success rates using `urls_discovered` as the denominator, which included URLs that were never attempted due to test limits.

**Before (incorrect):**
```python
total_attempts = self.urls_discovered  # e.g., 1000
success_rate = urls_fetched / total_attempts  # e.g., 20/1000 = 2%
```

**After (correct):**
```python
total_attempted = self.urls_fetched + self.urls_failed  # e.g., 20
success_rate = urls_fetched / total_attempted  # e.g., 18/20 = 90%
```

**Impact:** Success rates are now accurate and not artificially lowered by test limits.

---

## Backward Compatibility

### Deprecated Metrics (Available for 1 Version)

The following metrics are **deprecated but still available** for backward compatibility:

- `fetch_success_rate` - Aliased to pipeline-specific primary metric
- `fetch_failure_rate` - Aliased to pipeline-specific failure metric

**Deprecation Warnings:** When metrics are accessed, the `_deprecation_warnings` field in the statistics output will contain migration guidance.

### Timeline

- **Phase 1 (Current):** Old metrics available alongside new metrics
- **Phase 2 (Future):** Old metrics removed, only new metrics available
- **Recommended Action:** Migrate to new metric names as soon as possible

---

## New Features

### Metric Semantics Metadata

All statistics now include a `_metric_semantics` field that clarifies what each metric measures:

```json
{
  "statistics": {
    "http_request_success_rate": 0.947,
    "content_extraction_success_rate": 1.0,
    "quality_pass_rate": 0.847,
    "_metric_semantics": {
      "http_request_success_rate": "Network-level HTTP success (2xx responses / attempted requests)",
      "content_extraction_success_rate": "Content successfully extracted from HTTP responses",
      "quality_pass_rate": "Records passing quality filters (after deduplication)"
    },
    "_deprecation_warnings": [
      "fetch_success_rate is deprecated for web scraping. Use http_request_success_rate for HTTP success and content_extraction_success_rate for content extraction success."
    ]
  }
}
```

---

## Migration Examples

### Example 1: Web Scraping (BBC)

**Before:**
```python
metrics = collector.get_snapshot()
stats = metrics.calculate_statistics()

# Old metric (still works, but deprecated)
http_success = stats["fetch_success_rate"]  # e.g., 0.947
```

**After:**
```python
metrics = collector.get_snapshot()
stats = metrics.calculate_statistics()

# New metrics (recommended)
http_success = stats["http_request_success_rate"]  # Network-level HTTP success
extraction_success = stats["content_extraction_success_rate"]  # Content extraction
quality_pass = stats["quality_pass_rate"]  # Quality filtering

# Check semantic meaning
print(stats["_metric_semantics"]["http_request_success_rate"])
# Output: "Network-level HTTP success (2xx responses / attempted requests)"
```

### Example 2: File Processing (Wikipedia)

**Before:**
```python
stats = metrics.calculate_statistics()
extraction_rate = stats["fetch_success_rate"]  # Confusing name for file extraction
```

**After:**
```python
stats = metrics.calculate_statistics()
extraction_rate = stats["file_extraction_success_rate"]  # Clear semantic meaning
parsing_rate = stats["record_parsing_success_rate"]  # New granular metric
```

### Example 3: Stream Processing (HuggingFace)

**Before:**
```python
stats = metrics.calculate_statistics()
connected = stats["fetch_success_rate"]  # 1.0 if stream connected, but what about coverage?
```

**After:**
```python
stats = metrics.calculate_statistics()
connected = stats["stream_connection_success_rate"]  # Boolean: connected or not
retrieval_success = stats["record_retrieval_success_rate"]  # How many records retrieved
coverage = stats["dataset_coverage_rate"]  # What % of dataset consumed (if known)

# Handle unknown coverage
if coverage is not None:
    print(f"Dataset coverage: {coverage * 100:.3f}%")
else:
    print("Dataset coverage unknown (dataset size not tracked)")
```

---

## Dashboard and Reporting Changes

### Quality Reports

Quality reports now show **pipeline-specific metrics** in the Executive Summary:

**Web Scraping Report:**
```markdown
## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** web_scraping

- **HTTP Request Success Rate:** 94.7%
- **Content Extraction Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 84.7%
- **Deduplication Rate:** 5.3%
```

**File Processing Report:**
```markdown
## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 100.0%
- **Deduplication Rate:** 12.5%
```

**Stream Processing Report:**
```markdown
## Executive Summary

**Pipeline Status:** ⚠️ **DEGRADED**
**Pipeline Type:** stream_processing

- **Stream Connection Success:** 100.0%
- **Record Retrieval Success Rate:** 100.0%
- **Dataset Coverage:** 0.002%
- **Quality Filter Pass Rate:** 0.0%
```

### Recommendations

Recommendations are now **pipeline-aware**:

- Web scraping: Checks `http_request_success_rate` and suggests network troubleshooting
- File processing: Checks `file_extraction_success_rate` and suggests file corruption checks
- Stream processing: Checks `stream_connection_success_rate` and `dataset_coverage_rate`

---

## Testing Changes

No changes required to existing code that **only reads metrics**. The old metric names are still present as aliases.

### Recommended Test Updates

Update tests to use new metric names for clarity:

**Before:**
```python
def test_bbc_metrics():
    stats = collector.get_snapshot().calculate_statistics()
    assert stats["fetch_success_rate"] > 0.8  # What does "fetch" mean here?
```

**After:**
```python
def test_bbc_metrics():
    stats = collector.get_snapshot().calculate_statistics()
    assert stats["http_request_success_rate"] > 0.8  # Clear: HTTP network success
    assert stats["content_extraction_success_rate"] > 0.9  # Clear: content extraction
    assert stats["quality_pass_rate"] > 0.7  # Clear: quality filtering
```

---

## Code Changes Required

### If You're Using Metrics in Custom Code

1. **Read-only usage (no changes needed):**
   ```python
   # This still works (deprecated but compatible)
   success_rate = stats["fetch_success_rate"]
   ```

2. **Recommended migration:**
   ```python
   # Update to pipeline-specific metrics
   if pipeline_type == PipelineType.WEB_SCRAPING:
       success_rate = stats["http_request_success_rate"]
   elif pipeline_type == PipelineType.FILE_PROCESSING:
       success_rate = stats["file_extraction_success_rate"]
   elif pipeline_type == PipelineType.STREAM_PROCESSING:
       success_rate = stats["stream_connection_success_rate"]
   ```

3. **Using semantic metadata (new feature):**
   ```python
   # Get automatic metric descriptions
   semantics = stats["_metric_semantics"]
   for metric_name, metric_value in stats.items():
       if metric_name in semantics:
           print(f"{metric_name}: {metric_value} - {semantics[metric_name]}")
   ```

---

## Next Steps (Future Phases)

### Phase 2: Hierarchical Metrics (Planned)

Implement layered metrics structure:
```python
{
  "connectivity": {
    "connection_attempted": true,
    "connection_successful": true,
    "connection_duration_ms": 150.0
  },
  "extraction": {
    "http_requests_attempted": 187,
    "http_requests_successful": 177,
    "http_success_rate": 0.947
  },
  "quality": {
    "records_received": 177,
    "records_passed_filters": 150,
    "quality_pass_rate": 0.847
  }
}
```

### Phase 3: Domain-Specific Classes (Planned)

Implement type-safe metric classes:
```python
class WebScrapingMetrics(BaseMetrics):
    http_requests_attempted: int
    http_requests_successful: int

    @property
    def http_success_rate(self) -> float:
        return self.http_requests_successful / self.http_requests_attempted
```

---

## FAQs

**Q: Will my existing code break?**
A: No. Old metric names are aliased to new names for backward compatibility.

**Q: When will old metrics be removed?**
A: Not before the next major version. You'll receive deprecation warnings in the meantime.

**Q: How do I know which metrics to use?**
A: Check the `_metric_semantics` field in the statistics output for descriptions.

**Q: Why the rename?**
A: "Fetch" meant different things for different pipelines (HTTP vs file I/O vs streaming). New names are semantically accurate and prevent confusion.

**Q: What if I'm averaging metrics across sources?**
A: Don't average incompatible metrics (e.g., HTTP success vs file extraction). Only average semantically identical metrics like `quality_pass_rate`.

**Q: How do I update my dashboard?**
A: Quality reports are automatically updated. If you have custom dashboard code, migrate to new metric names at your convenience.

---

## Support

For questions or issues:
1. Check the `_metric_semantics` field for metric descriptions
2. Review the `_deprecation_warnings` field for migration guidance
3. See `METRICS_ARCHITECTURE_ASSESSMENT.md` for technical details
4. See `METRICS_ASSESSMENT_SUMMARY.md` for executive summary

---

## Appendix: Complete Metric Reference

### Web Scraping Metrics

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `http_request_success_rate` | float | 0.0-1.0 | Network-level HTTP success (2xx / attempted) |
| `http_request_failure_rate` | float | 0.0-1.0 | HTTP request failures / attempted |
| `content_extraction_success_rate` | float | 0.0-1.0 | Content extracted / HTTP 200 responses |
| `quality_pass_rate` | float | 0.0-1.0 | Records passing quality filters |
| `deduplication_rate` | float | 0.0-1.0 | Records filtered as duplicates |

### File Processing Metrics

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `file_extraction_success_rate` | float | 0.0-1.0 | Files successfully extracted / discovered |
| `file_extraction_failure_rate` | float | 0.0-1.0 | Files failed extraction / discovered |
| `record_parsing_success_rate` | float | 0.0-1.0 | Records successfully parsed / extracted |
| `quality_pass_rate` | float | 0.0-1.0 | Records passing quality filters |
| `deduplication_rate` | float | 0.0-1.0 | Records filtered as duplicates |

### Stream Processing Metrics

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `stream_connection_success_rate` | float | 0.0 or 1.0 | Stream connection established (boolean) |
| `record_retrieval_success_rate` | float | 0.0-1.0 | Records retrieved / requested |
| `dataset_coverage_rate` | float or null | 0.0-1.0 | Records consumed / total dataset size (if known) |
| `quality_pass_rate` | float | 0.0-1.0 | Records passing quality filters |
| `deduplication_rate` | float | 0.0-1.0 | Records filtered as duplicates |

---

**End of Migration Guide**
