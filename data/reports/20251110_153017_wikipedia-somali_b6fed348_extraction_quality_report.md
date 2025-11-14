# Data Quality Report

**Run ID:** 20251110_153017_wikipedia-somali_b6fed348
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-10T15:30:34.186744+00:00
**Duration:** 17s

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

- **Mean:** 13343 ms
- **Median:** 13343 ms
- **P95:** 13343 ms
- **P99:** 13343 ms
- **Min:** 13343 ms
- **Max:** 13343 ms

### Extraction Performance

- **Mean:** 3678 ms
- **Median:** 3678 ms
- **P95:** 3678 ms
- **P99:** 3678 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 849.4 KB/s

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
