# Data Quality Report

**Run ID:** 20251026_155342_bbc-somali_6ca368f7
**Source:** BBC-Somali
**Timestamp:** 2025-10-26T16:23:45.356104+00:00
**Duration:** 30m 2s

---

## Executive Summary

**Pipeline Status:** ✅ **HEALTHY**
**Pipeline Type:** web_scraping

- **HTTP Request Success Rate:** 96.6%
- **Content Extraction Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 0.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 0
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| URLs Discovered | 189 | 100.0% |
| URLs Fetched | 28 | 14.8% |
| URLs Processed | 0 | 0.0% |
| URLs Failed | 1 | 0.5% |
| URLs Skipped | 0 | 0.0% |
| URLs Deduplicated | 0 | 0.0% |

---

## Performance Metrics

### Fetch Performance

- **Mean:** 1357 ms
- **Median:** 1126 ms
- **P95:** 3305 ms
- **P99:** 4421 ms
- **Min:** 599 ms
- **Max:** 4421 ms

### Throughput

- **URLs/second:** 0.00
- **Records/minute:** 0.0
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 4,875 chars
- **Median:** 4,438 chars
- **Min:** 337 chars
- **Max:** 10,598 chars
- **Total:** 133.3 KB

---

## HTTP Status Distribution

| Status Class | Count | Details |
|--------------|-------|---------|
| 2xx | 28 | 200:28 |

---

## Error Analysis

**Total Errors:** 1

| Error Type | Count | Percentage |
|------------|-------|------------|
| scrape_failed | 1 | 100.0% |

---

## Recommendations

⚠️ **Low quality filter pass rate.** Many records are being filtered out. Review filter configurations or consider adjusting quality thresholds.

---
