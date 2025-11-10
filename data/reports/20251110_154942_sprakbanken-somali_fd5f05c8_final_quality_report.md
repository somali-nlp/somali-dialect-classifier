# Data Quality Report

**Run ID:** 20251110_154942_sprakbanken-somali_fd5f05c8
**Source:** Sprakbanken-Somali
**Timestamp:** 2025-11-10T15:49:49.373986+00:00
**Duration:** 6s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 83.7%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 2,527
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 2 |
| Files Processed | 2 |
| Records Extracted | 3,018 |
| Records Written | 2,527 |

---

## Performance Metrics

### Extraction Performance

- **Mean:** 2371 ms
- **Median:** 3030 ms
- **P95:** 3559 ms
- **P99:** 3559 ms

### Throughput

- **Records/minute:** 23351.2
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 93 chars
- **Median:** 69 chars
- **Min:** 8 chars
- **Max:** 564 chars
- **Total:** 90.9 KB

---

## Filter Statistics

**Total Filtered:** 491 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| langid_filter | 367 | 74.7% |
| min_length_filter | 113 | 23.0% |
| empty_after_cleaning | 11 | 2.2% |

---

## Recommendations

✅ All metrics within acceptable ranges.

---
