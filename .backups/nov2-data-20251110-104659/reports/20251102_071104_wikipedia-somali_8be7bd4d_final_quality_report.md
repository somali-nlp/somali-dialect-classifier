# Data Quality Report

**Run ID:** 20251102_071104_wikipedia-somali_8be7bd4d
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-02T07:11:22.261588+00:00
**Duration:** 18s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 64.2%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 9,960
- **Data Downloaded:** 14.1 MB

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 1,507 |
| Records Written | 9,960 |

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

- **Records/minute:** 33184.7
- **Bytes/second:** 803.2 KB/s

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

## Filter Statistics

**Total Filtered:** 5,547 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| min_length_filter | 4,138 | 74.6% |
| langid_filter | 1,208 | 21.8% |
| empty_after_cleaning | 201 | 3.6% |

---

## Recommendations

🐢 **Slow fetch times detected.** Consider implementing connection pooling, adjusting timeouts, or using concurrent requests.

---
