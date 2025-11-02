# Data Quality Report

**Run ID:** 20251102_071104_tiktok-somali_d400941e
**Source:** TikTok-Somali
**Timestamp:** 2025-11-02T07:13:10.327134+00:00
**Duration:** 2m 6s

---

## Executive Summary

**Pipeline Status:** ❌ **UNHEALTHY**
**Pipeline Type:** stream_processing

- **Stream Connection Success:** 0.0%
- **Record Retrieval Success Rate:** 0.0%
- **Quality Filter Pass Rate:** 0.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 0
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count |
|--------|-------|
| Datasets Opened | 0 |
| Records Fetched | 0 |
| Records Processed | 0 |
| Batches Completed | 0 |
| Records Written | 0 |

---

## Performance Metrics

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

- **Mean:** 35 chars
- **Median:** 23 chars
- **Min:** 3 chars
- **Max:** 1,614 chars
- **Total:** 13.2 KB

---

## Filter Statistics

**Total Filtered:** 804 records

| Filter Reason | Count | Percentage |
|---------------|-------|------------|
| emoji_only_comment | 801 | 99.6% |
| text_too_short_after_cleanup | 3 | 0.4% |

---

## Recommendations

❌ **Stream connection failed.** Check API credentials, network connectivity, and rate limits.
⚠️ **Low quality filter pass rate.** Many records are being filtered out. Review filter configurations or consider adjusting quality thresholds.

---
