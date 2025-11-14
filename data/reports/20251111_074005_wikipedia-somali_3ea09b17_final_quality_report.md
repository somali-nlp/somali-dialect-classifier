# Data Quality Report

**Run ID:** 20251111_074005_wikipedia-somali_3ea09b17
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-11T07:40:11.735101+00:00
**Duration:** 5s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 64.2%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 9,960
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 0 |
| Files Processed | 0 |
| Records Extracted | 1,507 |
| Records Written | 9,960 |

---

## Performance Metrics

### Extraction Performance

- **Mean:** 2502 ms
- **Median:** 2502 ms
- **P95:** 2502 ms
- **P99:** 2502 ms

### Throughput

- **Records/minute:** 102042.2
- **Bytes/second:** 0.0 B/s

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

## Filter Statistics

**Total Filtered:** 5,547 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| min_length_filter | 4,138 | 74.6% |
| langid_filter | 1,208 | 21.8% |
| empty_after_cleaning | 201 | 3.6% |

---

## Recommendations

✅ All metrics within acceptable ranges.

---
