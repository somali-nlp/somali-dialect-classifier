# Data Quality Report

**Run ID:** 20251110_155041_huggingface-somali_c4-so_54df892d
**Source:** HuggingFace-Somali_c4-so
**Timestamp:** 2025-11-10T15:52:24.267352+00:00
**Duration:** 1m 43s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** stream_processing

- **Stream Connection Success:** 100.0%
- **Record Retrieval Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 100.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 191
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Datasets Opened | 1 |
| Records Fetched | 200 |
| Records Processed | 191 |
| Batches Completed | 0 |
| Records Written | 191 |

---

## Performance Metrics

### Download Performance

- **Mean:** 6 ms
- **Median:** 3 ms
- **P95:** 16 ms
- **P99:** 70 ms
- **Min:** 0 ms
- **Max:** 103 ms

### Throughput

- **Records/minute:** 111.0
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 5,148 chars
- **Median:** 1,818 chars
- **Min:** 107 chars
- **Max:** 93,463 chars
- **Total:** 1015.5 KB

---

## Filter Statistics

**Total Filtered:** 19 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| langid_filter | 17 | 89.5% |
| min_length_filter | 2 | 10.5% |

---

## Recommendations

✅ All metrics within acceptable ranges.

---
