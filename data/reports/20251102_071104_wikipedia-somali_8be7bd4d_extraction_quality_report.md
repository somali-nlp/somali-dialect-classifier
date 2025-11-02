# Data Quality Report

**Run ID:** 20251102_071104_wikipedia-somali_8be7bd4d
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-02T07:11:18.917352+00:00
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
- **Data Downloaded:** 14.1 MB

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 1,507 |
| Records Written | 0 |

---

## Performance Metrics

### Download Performance

- **Mean:** 11293 ms
- **Median:** 11293 ms
- **P95:** 11293 ms
- **P99:** 11293 ms
- **Min:** 11293 ms
- **Max:** 11293 ms

### Extraction Performance

- **Mean:** 3367 ms
- **Median:** 3367 ms
- **P95:** 3367 ms
- **P99:** 3367 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 986.3 KB/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 5,464 chars
- **Median:** 3,512 chars
- **Min:** 3 chars
- **Max:** 122,020 chars
- **Total:** 5.2 MB

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
