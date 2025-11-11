# Data Quality Report

**Run ID:** 20251111_065906_wikipedia-somali_b1a064bd
**Source:** Wikipedia-Somali
**Timestamp:** 2025-11-11T06:59:11.565298+00:00
**Duration:** 5s

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
| Records Extracted | 1,507 |
| Records Written | 0 |

---

## Performance Metrics

### Extraction Performance

- **Mean:** 2429 ms
- **Median:** 2429 ms
- **P95:** 2429 ms
- **P99:** 2429 ms

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

- **Mean:** 5,464 chars
- **Median:** 3,512 chars
- **Min:** 3 chars
- **Max:** 122,020 chars
- **Total:** 5.2 MB

---

## Filter Statistics

**Total Filtered:** 15,507 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| schema_validation_failed | 9,960 | 64.2% |
| min_length_filter | 4,138 | 26.7% |
| langid_filter | 1,208 | 7.8% |
| empty_after_cleaning | 201 | 1.3% |

---

## Recommendations

⚠️ **Low quality filter pass rate.** Many records are being filtered out. Review filter configurations or consider adjusting quality thresholds.

---
