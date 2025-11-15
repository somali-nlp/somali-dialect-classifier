# Data Quality Report

**Run ID:** 20251115_045737_wikipedia-somali_93854c9d
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-15T04:57:40.904614+00:00
**Duration:** 3s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 0.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 0
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 0 |
| Files Processed | 0 |
| Records Extracted | 5,547 |
| Records Written | 0 |

---

## Performance Metrics

### Extraction Performance

- **Mean:** 57 ms
- **Median:** 57 ms
- **P95:** 57 ms
- **P99:** 57 ms

### Throughput

- **Records/minute:** 0.0
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 1,251 chars
- **Median:** 34 chars
- **Min:** 3 chars
- **Max:** 55,956 chars
- **Total:** 1.2 MB

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

⚠️ **Low quality filter pass rate.** Many records are being filtered out. Review filter configurations or consider adjusting quality thresholds.

---
