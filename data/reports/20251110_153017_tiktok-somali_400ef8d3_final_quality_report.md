# Data Quality Report

**Run ID:** 20251110_153017_tiktok-somali_400ef8d3
**Source:** TikTok-Somali
**Timestamp:** 2025-11-10T15:32:53.499487+00:00
**Duration:** 2m 36s

---

## Executive Summary

**Pipeline Status:** ❌ **UNHEALTHY**
**Pipeline Type:** stream_processing

- **Stream Connection Success:** 0.0%
- **Record Retrieval Success Rate:** 0.0%
- **Quality Filter Pass Rate:** 79.2%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 262
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Datasets Opened | 0 |
| Records Fetched | 0 |
| Records Processed | 0 |
| Batches Completed | 0 |
| Records Written | 262 |

---

## Performance Metrics

### Throughput

- **Records/minute:** 100.5
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 35 chars
- **Median:** 21 chars
- **Min:** 3 chars
- **Max:** 1,617 chars
- **Total:** 11.3 KB

---

## Filter Statistics

**Total Filtered:** 700 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| emoji_only_comment | 628 | 89.7% |
| empty_after_cleaning | 69 | 9.9% |
| text_too_short_after_cleanup | 3 | 0.4% |

---

## Recommendations

❌ **Stream connection failed.** Check API credentials, network connectivity, and rate limits.

---
