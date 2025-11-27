# Data Quality Report

**Run ID:** 20251127_175417_sprakbanken-somali_5939d251
**Source:** sprakbanken-somali
**Timestamp:** 2025-11-27T18:01:06.225380+00:00
**Duration:** 6m 47s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** file_processing

- **File Extraction Success Rate:** 100.0%
- **Record Parsing Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 81.9%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 13,134
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Files Discovered | 66 |
| Files Processed | 66 |
| Records Extracted | 16,039 |
| Records Written | 13,134 |

---

## Performance Metrics

### Extraction Performance

- **Mean:** 3838 ms
- **Median:** 562 ms
- **P95:** 21114 ms
- **P99:** 21114 ms

### Throughput

- **Records/minute:** 1931.6
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 73 chars
- **Median:** 58 chars
- **Min:** 7 chars
- **Max:** 310 chars
- **Total:** 71.7 KB

---

## Filter Statistics

**Total Filtered:** 2,905 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| langid_filter | 2,044 | 70.4% |
| min_length_filter | 747 | 25.7% |
| empty_after_cleaning | 114 | 3.9% |

---

## Recommendations

✅ All metrics within acceptable ranges.

---
