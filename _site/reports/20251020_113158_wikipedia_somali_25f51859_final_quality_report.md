# Data Quality Report

**Run ID:** 20251020_113158_wikipedia_somali_25f51859
**Source:** Wikipedia-Somali
**Timestamp:** 2025-10-20T11:32:13.784478+00:00
**Duration:** 15s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**

- **Success Rate:** 100.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 9,329
- **Data Downloaded:** 12.7 MB

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 728 |
| Records Written | 9,329 |

---

## Performance Metrics

### Download Performance

- **Mean:** 9447 ms
- **Median:** 9447 ms
- **P95:** 9447 ms
- **P99:** 9447 ms
- **Min:** 9447 ms
- **Max:** 9447 ms

### Extraction Performance

- **Mean:** 3598 ms
- **Median:** 3598 ms
- **P95:** 3598 ms
- **P99:** 3598 ms

### Throughput

- **Records/minute:** 36757.7
- **Bytes/second:** 857.3 KB/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 2,521 chars
- **Median:** 580 chars
- **Min:** 11 chars
- **Max:** 122,020 chars
- **Total:** 2.4 MB

---

## HTTP Status Distribution

| Status Class | Count | Details |
|--------------|-------|---------|
| 2xx | 1 | 200:1 |

---

## Recommendations

🐢 **Slow fetch times detected.** Consider implementing connection pooling, adjusting timeouts, or using concurrent requests.

---
