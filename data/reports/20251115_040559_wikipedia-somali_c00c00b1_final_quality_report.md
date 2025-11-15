# Data Quality Report

**Run ID:** 20251115_040559_wikipedia-somali_c00c00b1
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-15T04:06:17.522603+00:00
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
| Records Extracted | 15,507 |
| Records Written | 9,960 |

---

## Performance Metrics

### Download Performance

- **Mean:** 11307 ms
- **Median:** 11307 ms
- **P95:** 11307 ms
- **P99:** 11307 ms
- **Min:** 11307 ms
- **Max:** 11307 ms

### Extraction Performance

- **Mean:** 1141 ms
- **Median:** 1141 ms
- **P95:** 1141 ms
- **P99:** 1141 ms

### Throughput

- **Records/minute:** 32976.0
- **Bytes/second:** 798.1 KB/s

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
