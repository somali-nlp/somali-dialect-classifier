# Data Quality Report

**Run ID:** 20251021_113613_wikipedia_somali_36fc6f34
**Source:** Wikipedia-Somali
**Timestamp:** 2025-10-21T11:36:30.234488+00:00
**Duration:** 17s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**

- **Success Rate:** 100.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 9,623
- **Data Downloaded:** 13.6 MB

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 136 |
| Records Written | 9,623 |

---

## Performance Metrics

### Download Performance

- **Mean:** 10036 ms
- **Median:** 10036 ms
- **P95:** 10036 ms
- **P99:** 10036 ms
- **Min:** 10036 ms
- **Max:** 10036 ms

### Extraction Performance

- **Mean:** 3726 ms
- **Median:** 3726 ms
- **P95:** 3726 ms
- **P99:** 3726 ms

### Throughput

- **Records/minute:** 33775.9
- **Bytes/second:** 815.8 KB/s

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

🐢 **Slow fetch times detected.** Consider implementing connection pooling, adjusting timeouts, or using concurrent requests.

---
