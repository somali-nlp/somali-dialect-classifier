# Data Quality Report

**Run ID:** 20251102_081139_huggingface-somali_c4-so_8a88e83f
**Source:** HuggingFace-Somali_c4-so
**Timestamp:** 2025-11-02T08:13:51.988489+00:00
**Duration:** 2m 12s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** stream_processing

- **Stream Connection Success:** 100.0%
- **Record Retrieval Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 100.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 190
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Datasets Opened | 1 |
| Records Fetched | 200 |
| Records Processed | 190 |
| Batches Completed | 0 |
| Records Written | 190 |

---

## Performance Metrics

### Download Performance

- **Mean:** 5 ms
- **Median:** 2 ms
- **P95:** 14 ms
- **P99:** 46 ms
- **Min:** 0 ms
- **Max:** 111 ms

### Throughput

- **Records/minute:** 86.0
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 4,614 chars
- **Median:** 1,881 chars
- **Min:** 102 chars
- **Max:** 107,236 chars
- **Total:** 901.2 KB

---

## Filter Statistics

**Total Filtered:** 10 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| langid_filter | 8 | 80.0% |
| min_length_filter | 2 | 20.0% |

---

## Recommendations

✅ All metrics within acceptable ranges.

---
