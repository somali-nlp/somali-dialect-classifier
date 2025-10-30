# Data Quality Report

**Run ID:** 20251029_165927_sprakbanken-somali_ed7d70d2
**Source:** Sprakbanken-Somali
**Timestamp:** 2025-10-29T16:59:38.145673+00:00
**Duration:** 10s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 79.3%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 4,009
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 1 |
| Files Processed | 1 |
| Records Extracted | 5,053 |
| Records Written | 4,009 |

---

## Performance Metrics

### Extraction Performance

- **Mean:** 7066 ms
- **Median:** 7066 ms
- **P95:** 7066 ms
- **P99:** 7066 ms

### Throughput

- **Records/minute:** 22628.3
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 133 chars
- **Median:** 86 chars
- **Min:** 6 chars
- **Max:** 925 chars
- **Total:** 130.3 KB

---

## Filter Statistics

**Total Filtered:** 1,044 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| langid_filter | 747 | 71.6% |
| min_length_filter | 233 | 22.3% |
| empty_after_cleaning | 64 | 6.1% |

---

## Recommendations

✅ All metrics within acceptable ranges.

---
