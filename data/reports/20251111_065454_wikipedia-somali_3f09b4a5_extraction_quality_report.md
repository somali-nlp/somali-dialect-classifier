# Data Quality Report

**Run ID:** 20251111_065454_wikipedia-somali_3f09b4a5
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-11T06:55:17.411059+00:00
**Duration:** 22s

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

- **Mean:** 20537 ms
- **Median:** 20537 ms
- **P95:** 20537 ms
- **P99:** 20537 ms
- **Min:** 20537 ms
- **Max:** 20537 ms

### Extraction Performance

- **Mean:** 2405 ms
- **Median:** 2405 ms
- **P95:** 2405 ms
- **P99:** 2405 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 630.2 KB/s

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
