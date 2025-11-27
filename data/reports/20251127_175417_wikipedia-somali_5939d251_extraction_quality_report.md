# Data Quality Report

**Run ID:** 20251127_175417_wikipedia-somali_5939d251
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-27T17:55:00.215206+00:00
**Duration:** 41s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 0.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 0
- **Data Downloaded:** 14.5 MB

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 15,747 |
| Records Written | 0 |

---

## Performance Metrics

### Download Performance

- **Mean:** 38517 ms
- **Median:** 38517 ms
- **P95:** 38517 ms
- **P99:** 38517 ms
- **Min:** 38517 ms
- **Max:** 38517 ms

### Extraction Performance

- **Mean:** 1087 ms
- **Median:** 1087 ms
- **P95:** 1087 ms
- **P99:** 1087 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 353.0 KB/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 4,744 chars
- **Median:** 2,962 chars
- **Min:** 16 chars
- **Max:** 392,270 chars
- **Total:** 4.5 MB

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
