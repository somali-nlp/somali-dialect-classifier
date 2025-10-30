# Data Quality Report

**Run ID:** 20251029_165927_wikipedia-somali_11636b96
**Source:** Wikipedia-Somali
**Timestamp:** 2025-10-29T16:59:41.558212+00:00
**Duration:** 14s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 0.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 0
- **Data Downloaded:** 13.6 MB

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 136 |
| Records Written | 0 |

---

## Performance Metrics

### Download Performance

- **Mean:** 10725 ms
- **Median:** 10725 ms
- **P95:** 10725 ms
- **P99:** 10725 ms
- **Min:** 10725 ms
- **Max:** 10725 ms

### Extraction Performance

- **Mean:** 3298 ms
- **Median:** 3298 ms
- **P95:** 3298 ms
- **P99:** 3298 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 994.1 KB/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 4,416 chars
- **Median:** 1,917 chars
- **Min:** 10 chars
- **Max:** 122,020 chars
- **Total:** 4.2 MB

---

## HTTP Status Distribution

| Status Class | Count | Details |
|--------------|-------|---------|
| 2xx | 1 | 200:1 |

---

## Recommendations

⚠️ **Low quality filter pass rate.** Many records are being filtered out. Review filter configurations or consider adjusting quality thresholds.
🐢 **Slow fetch times detected.** Consider implementing connection pooling, adjusting timeouts, or using concurrent requests.

---
