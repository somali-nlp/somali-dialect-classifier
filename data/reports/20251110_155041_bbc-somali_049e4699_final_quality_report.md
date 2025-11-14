# Data Quality Report

**Run ID:** 20251110_155041_bbc-somali_049e4699
**Source:** BBC-Somali
**Timestamp:** 2025-11-10T15:55:42.111201+00:00
**Duration:** 5m 1s

---

## Executive Summary

**Pipeline Status:** ⚠️ **DEGRADED**
**Pipeline Type:** web_scraping

- **HTTP Request Success Rate:** 80.0%
- **Content Extraction Success Rate:** 100.0%
- **Quality Filter Pass Rate:** 100.0%
- **Deduplication Rate:** 0.0%
- **Total Records Processed:** 4
- **Data Downloaded:** 0.0 B

---

## Processing Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| URLs Discovered | 168 | 100.0% |
| URLs Fetched | 4 | 2.4% |
| URLs Processed | 4 | 2.4% |
| URLs Failed | 1 | 0.6% |
| URLs Skipped | 0 | 0.0% |
| URLs Deduplicated | 0 | 0.0% |

---

## Performance Metrics

### Fetch Performance

- **Mean:** 941 ms
- **Median:** 631 ms
- **P95:** 2050 ms
- **P99:** 2050 ms
- **Min:** 553 ms
- **Max:** 2050 ms

### Throughput

- **URLs/second:** 0.01
- **Records/minute:** 0.8
- **Bytes/second:** 0.0 B/s

---

## Data Quality Metrics

### Deduplication

- **Unique Documents:** 0
- **Exact Duplicates:** 0
- **Near Duplicates:** 0

### Text Length Distribution

- **Mean:** 3,838 chars
- **Median:** 4,320 chars
- **Min:** 475 chars
- **Max:** 6,235 chars
- **Total:** 15.0 KB

---

## HTTP Status Distribution

| Status Class | Count | Details |
|--------------|-------|---------|
| 2xx | 4 | 200:4 |

---

## Error Analysis

**Total Errors:** 1

| Error Type | Count | Percentage |
|------------|-------|------------|
| scrape_failed | 1 | 100.0% |

---

## Recommendations

❌ **High error rate detected.** Review error types and consider implementing circuit breakers or exponential backoff.

---
