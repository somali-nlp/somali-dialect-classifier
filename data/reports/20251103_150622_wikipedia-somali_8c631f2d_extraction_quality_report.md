# Data Quality Report

**Run ID:** 20251103_150622_wikipedia-somali_8c631f2d
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-03T15:06:37.582690+00:00
**Duration:** 15s

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

- **Mean:** 12717 ms
- **Median:** 12717 ms
- **P95:** 12717 ms
- **P99:** 12717 ms
- **Min:** 12717 ms
- **Max:** 12717 ms

### Extraction Performance

- **Mean:** 2501 ms
- **Median:** 2501 ms
- **P95:** 2501 ms
- **P99:** 2501 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 950.0 KB/s

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
