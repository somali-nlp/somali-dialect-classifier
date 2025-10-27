# Dashboard User Guide

**Complete guide for interpreting and using the Somali Dialect Classifier data pipeline dashboard.**

**Last Updated**: 2025-10-27
**Audience**: Data scientists, ML engineers, project managers, and stakeholders

---

## Table of Contents

- [Overview](#overview)
- [Dashboard Modes](#dashboard-modes)
  - [Story Mode](#story-mode-executive-view)
  - [Analyst Mode](#analyst-mode-deep-dive)
- [Understanding Visualizations](#understanding-visualizations)
- [Interpreting Metrics](#interpreting-metrics)
- [Glossary of Terms](#glossary-of-terms)
- [Common Workflows](#common-workflows)
- [FAQ](#faq)

---

## Overview

The Somali Dialect Classifier Dashboard provides real-time insights into the data collection pipeline. It visualizes metrics from four major data sources:

- **Wikipedia (Somali)**: Encyclopedia articles
- **BBC Somali**: News content
- **HuggingFace (mC4-so)**: Web-crawled corpus
- **Språkbanken**: Linguistic resources

### Dashboard Purpose

The dashboard serves three primary audiences:

1. **Project Managers**: Track progress and verify pipeline health
2. **Data Scientists**: Analyze data quality and source characteristics
3. **Developers**: Debug pipeline issues and optimize performance

### Accessing the Dashboard

- **Live Dashboard**: [https://YOUR-USERNAME.github.io/somali-dialect-classifier/](https://YOUR-USERNAME.github.io/somali-dialect-classifier/)
- **Update Frequency**: Automatically updates on every push to `main` branch
- **Data Freshness**: Metrics are generated in real-time during pipeline runs

---

## Dashboard Modes

The dashboard conceptually operates in two modes, tailored to different user needs:

### Story Mode (Executive View)

**Purpose**: Quick overview of pipeline status and progress

**Best For**:
- Daily check-ins
- Stakeholder updates
- High-level health monitoring
- Progress reporting

**Key Sections**:

#### 1. Hero Metrics (Top of Dashboard)

```
Total Records Collected: 130,000+
Success Rate: 95.2%
Data Volume: 142 MB
Active Sources: 4/4
```

**What to Look For**:
- Total records should increase after each run
- Success rate > 90% indicates healthy pipeline
- All sources should show recent activity

#### 2. Source Health Cards

Each source has a status card showing:

- **Status Indicator**:
  - 🟢 Green: Healthy (success rate > 90%)
  - 🟡 Yellow: Degraded (success rate 70-90%)
  - 🔴 Red: Critical (success rate < 70%)

- **Quick Stats**:
  - Records collected
  - Last update timestamp
  - Quality pass rate

**Example Interpretation**:
```
Wikipedia (Somali) 🟢
  9,623 records | 63.6% quality rate
  Last run: 2 hours ago
```
- Status is healthy (green)
- Collected nearly 10K records
- 63.6% passed quality filters (see filter breakdown for details)
- Recently updated

#### 3. Timeline View

Visual timeline showing when each source was last processed.

**Use Case**: Quickly identify stale sources that need attention.

---

### Analyst Mode (Deep Dive)

**Purpose**: Detailed analysis of data quality, performance, and trends

**Best For**:
- Debugging pipeline issues
- Optimizing filter thresholds
- Understanding quality patterns
- Performance tuning

**Key Sections**:

#### 1. Quality Metrics Breakdown

**Quality Pass Rate**: Percentage of records passing all quality filters

**Formula**:
```
quality_pass_rate = records_written / (records_written + records_filtered)
```

**Why It Matters**:
- Wikipedia showing 63.6% is expected due to strict filters
- Lower rates may indicate:
  - Source content degradation
  - Overly aggressive filters
  - Language contamination

**Breakdown by Filter**:
```
Wikipedia Filtering:
  - min_length_filter: 4,128 rejected (74.9%)
  - langid_filter: 1,185 rejected (21.5%)
  - empty_after_cleaning: 200 rejected (3.6%)
```

**Interpretation**:
- Most rejections due to short articles (stubs)
- Some language detection failures
- Few empty pages after cleaning

#### 2. Source-Specific Success Rates

Each pipeline type has different success metrics:

**Web Scraping (BBC)**:
- **HTTP Request Success Rate**: Network-level HTTP success (2xx responses)
- **Content Extraction Success Rate**: Successfully parsed content from pages

**File Processing (Wikipedia, Språkbanken)**:
- **File Extraction Success Rate**: Files successfully read and parsed
- **Record Parsing Success Rate**: Individual records extracted from files

**Stream Processing (HuggingFace)**:
- **Stream Connection Success Rate**: API connection established
- **Record Retrieval Success Rate**: Records successfully fetched
- **Dataset Coverage Rate**: Portion of total dataset consumed

**Example**:
```
BBC Somali (Web Scraping):
  HTTP Request Success: 94.7%
  Content Extraction: 100%

  → Network requests mostly successful
  → All fetched pages successfully parsed
```

#### 3. Performance Metrics

**Throughput**:
- **Records/minute**: How fast data is processed
- **Bytes/second**: Download speed

**Latency**:
- **Mean**: Average request time
- **P95**: 95th percentile (95% of requests faster than this)
- **P99**: 99th percentile

**Interpretation Guide**:
```
Good Performance:
  - Wikipedia: 15,000+ records/min
  - BBC: 50+ records/min
  - HuggingFace: 5,000+ records/min

Slow Performance Indicators:
  - P95 latency > 5 seconds
  - Throughput 50% below baseline
```

#### 4. Deduplication Statistics

**Deduplication Rate**: Percentage of records removed as duplicates

**Formula**:
```
deduplication_rate = duplicate_records / total_records_received
```

**Expected Rates**:
- **First run**: 0-5% (mostly fresh data)
- **Incremental runs**: 20-80% (depends on source update frequency)
- **High rates (>80%)**: Source may have stale content or limited new data

**Example**:
```
Wikipedia: 0.0% deduplication
  → First run or source updated significantly

BBC: 45.2% deduplication
  → Incremental run with some duplicate articles
```

---

## Understanding Visualizations

### 1. Records Over Time (Line Chart)

**What It Shows**: Cumulative records collected per source over time

**How to Read**:
- **Y-axis**: Total records
- **X-axis**: Date/time
- **Colors**: Each source has a distinct color

**Patterns to Look For**:
- **Steep slopes**: High collection rate
- **Flat lines**: No recent activity (source may be paused)
- **Steps**: Individual pipeline runs
- **Divergence**: Some sources collecting faster than others

**Example Analysis**:
```
If Wikipedia line is flat while BBC is climbing:
  → BBC pipeline running frequently
  → Wikipedia pipeline needs to be triggered
```

### 2. Success Rate Trends (Area Chart)

**What It Shows**: Quality metrics over time

**How to Read**:
- **Y-axis**: Success rate (0-100%)
- **X-axis**: Date/time
- **Bands**: Healthy (green), warning (yellow), critical (red) zones

**Patterns to Watch**:
- **Declining trend**: Investigate source changes or filter issues
- **Sudden drops**: Check error logs for pipeline failures
- **Oscillations**: Inconsistent data quality (normal for some sources)

### 3. Filter Impact Visualization (Stacked Bar)

**What It Shows**: How many records each filter removes

**How to Read**:
- **Height**: Total records filtered
- **Segments**: Breakdown by filter type
- **Colors**: Different filters

**Use Case**:
```
If langid_filter segment is large:
  → Source may have language contamination
  → Consider adjusting confidence threshold

If min_length_filter dominates:
  → Source has many short texts (e.g., Wikipedia stubs)
  → Expected behavior, not an issue
```

### 4. Data Volume by Source (Pie Chart)

**What It Shows**: Distribution of collected data across sources

**How to Read**:
- **Segments**: Proportional to data volume
- **Labels**: Source name and percentage

**Insights**:
```
Balanced Distribution (all sources ~25%):
  → Good diversity

One source dominating (e.g., 70%):
  → May introduce bias
  → Consider balancing collection efforts
```

---

## Interpreting Metrics

### Metric Semantics by Pipeline Type

Different pipelines measure success differently. Understanding these differences is crucial for accurate interpretation.

#### Web Scraping Pipelines (BBC)

| Metric | Meaning | Good Value |
|--------|---------|------------|
| HTTP Request Success Rate | Network-level success (2xx responses) | > 90% |
| Content Extraction Success Rate | Successfully parsed HTML content | > 95% |
| Quality Pass Rate | Records passing quality filters | > 70% |

**Common Issues**:
- Low HTTP success: Network problems, invalid URLs, rate limiting
- Low extraction success: Website HTML changed, scraper needs updating
- Low quality rate: Content quality degradation or strict filters

#### File Processing Pipelines (Wikipedia, Språkbanken)

| Metric | Meaning | Good Value |
|--------|---------|------------|
| File Extraction Success Rate | Files successfully opened and read | > 95% |
| Record Parsing Success Rate | Individual records extracted from files | > 90% |
| Quality Pass Rate | Records passing quality filters | > 50% |

**Common Issues**:
- Low extraction rate: Corrupted files, format changes, missing dependencies
- Low parsing rate: Schema changes, encoding issues
- Low quality rate: Expected for Wikipedia (many stubs), investigate for others

#### Stream Processing Pipelines (HuggingFace)

| Metric | Meaning | Good Value |
|--------|---------|------------|
| Stream Connection Success Rate | API connection established | 100% |
| Record Retrieval Success Rate | Records successfully fetched | > 95% |
| Dataset Coverage Rate | Portion of dataset consumed | Varies |

**Common Issues**:
- Connection failure: API credentials, network connectivity, rate limits
- Low retrieval rate: Timeouts, API errors, corrupt records
- Low coverage: Expected for partial runs (testing), investigate for full runs

### Health Status Indicators

The dashboard uses color-coded status indicators:

```
🟢 HEALTHY: Success rate > 90%
  → Pipeline operating normally
  → No action needed

🟡 DEGRADED: Success rate 70-90%
  → Pipeline experiencing issues
  → Monitor closely, investigate if persistent

🔴 CRITICAL: Success rate < 70%
  → Significant pipeline problems
  → Immediate investigation required
  → Check error logs and quality reports
```

---

## Glossary of Terms

### Pipeline Terms

| Term | Definition | Example |
|------|------------|---------|
| **Run ID** | Unique identifier for a pipeline execution | `20251026_155342_wikipedia-somali_c2915cab` |
| **Source** | Data origin (Wikipedia, BBC, HuggingFace, Språkbanken) | `Wikipedia-Somali` |
| **Pipeline Type** | Processing method (web_scraping, file_processing, stream_processing) | `file_processing` |

### Quality Metrics

| Metric | Formula | Range | Meaning |
|--------|---------|-------|---------|
| **Success Rate** | `successful_items / total_attempted` | 0-100% | Pipeline reliability |
| **Quality Pass Rate** | `records_passing_filters / total_non_duplicate_records` | 0-100% | Data quality level |
| **Deduplication Rate** | `duplicate_records / total_records` | 0-100% | Content redundancy |

### Filter Types

| Filter | Purpose | Typical Rejection Rate |
|--------|---------|----------------------|
| **min_length_filter** | Remove very short texts | 30-70% (Wikipedia), 5-15% (news) |
| **langid_filter** | Detect and remove non-Somali text | 10-25% |
| **empty_after_cleaning** | Remove texts that are empty after HTML removal | 1-5% |
| **namespace_filter** | Remove non-article Wikipedia pages | 20-40% (Wikipedia only) |

### Performance Metrics

| Metric | Unit | Typical Value | Meaning |
|--------|------|---------------|---------|
| **Throughput (records/min)** | records/min | 1,000-20,000 | Processing speed |
| **Latency (P95)** | milliseconds | 500-3000 | Request response time |
| **Bytes Downloaded** | MB | 10-200 per run | Data volume |

---

## Common Workflows

### 1. Daily Health Check

**Goal**: Verify pipeline is operating normally

**Steps**:
1. Check hero metrics at top
2. Verify all sources show green status
3. Confirm recent activity (last run < 24 hours)
4. Review success rate trend (should be stable)

**Time**: 2 minutes

### 2. Investigating Low Quality Rate

**Goal**: Understand why quality pass rate dropped

**Steps**:
1. Navigate to source-specific metrics
2. Check filter breakdown to identify dominant filter
3. Review sample rejected records in quality report
4. Compare with historical baselines

**Example**:
```
Wikipedia quality dropped from 70% → 63%:

1. Check filter breakdown:
   - min_length_filter: 74.9% of rejections

2. Hypothesis: More Wikipedia stubs being created

3. Action: Expected behavior, no changes needed
```

### 3. Debugging Pipeline Failure

**Goal**: Diagnose and resolve pipeline errors

**Steps**:
1. Check dashboard for red status indicators
2. Review error types in quality report
3. Examine HTTP status distribution (web scraping)
4. Check logs for detailed error messages
5. Review recent code changes

**Example**:
```
BBC showing 45% HTTP success rate:

1. Check HTTP status distribution:
   - 404 errors: 40%
   - 500 errors: 15%

2. Hypothesis: BBC changed URL structure

3. Action: Update URL patterns in scraper
```

### 4. Optimizing Filters

**Goal**: Balance data quality vs. volume

**Steps**:
1. Review current quality pass rates
2. Analyze filter breakdown by source
3. Examine sample rejected records
4. Adjust filter thresholds iteratively
5. Monitor impact on downstream tasks

**Example**:
```
Goal: Increase Wikipedia records without sacrificing quality

Current: 63.6% quality rate
  - min_length threshold: 50 chars

Test: Lower threshold to 30 chars

Results:
  - Quality rate: 75.2% (+11.6%)
  - Total records: 12,450 (+29%)
  - Spot-check: Quality acceptable

Decision: Adopt new threshold
```

### 5. Monthly Trend Analysis

**Goal**: Identify long-term patterns and anomalies

**Steps**:
1. Export metrics data for past 30 days
2. Calculate average success rates by source
3. Identify any degradation trends
4. Compare source productivity
5. Generate stakeholder report

**Metrics to Track**:
- Total records collected
- Average success rate by source
- Data volume trends
- Filter rejection patterns
- Performance degradation

---

## FAQ

### General Questions

**Q: How often is the dashboard updated?**
A: Automatically on every push to `main` branch. GitHub Actions rebuilds the dashboard within 2-3 minutes.

**Q: Can I access historical data?**
A: Yes, all historical metrics are stored in `data/metrics/`. Load them locally or query via the API.

**Q: Why does Wikipedia have a lower quality rate than other sources?**
A: Wikipedia contains many stub articles (very short pages) that fail the `min_length_filter`. This is expected and not a quality issue.

### Metrics Interpretation

**Q: What's a "good" quality pass rate?**
A: It varies by source:
- News sources (BBC): 70-90%
- Wikipedia: 50-70% (due to stubs)
- Corpus data (HuggingFace): 60-80%
- Språkbanken: 80-95% (curated source)

**Q: Why is the deduplication rate so high?**
A: High deduplication (>50%) on incremental runs is normal. Sources often don't publish much new content between runs.

**Q: What does "P95 latency" mean?**
A: 95% of requests completed faster than this time. It's a better indicator than average because it shows worst-case performance.

### Troubleshooting

**Q: Dashboard shows "No data available"**
A: Possible causes:
1. No pipeline runs yet (run a pipeline first)
2. Metrics files not committed to git
3. GitHub Actions workflow hasn't completed
4. Browser cache issue (hard refresh: Ctrl+Shift+R)

**Q: A source is showing red status**
A: Check the quality report for that source:
1. Navigate to `data/reports/`
2. Find the latest report for that source
3. Review "Recommendations" section
4. Check error logs for details

**Q: Success rate suddenly dropped**
A: Common causes:
1. Source website changed (web scraping)
2. API rate limits hit (streaming)
3. Network issues
4. Filter thresholds changed
5. Source content quality degraded

**Q: Charts not rendering**
A: Try:
1. Hard refresh browser (Ctrl+Shift+R)
2. Clear browser cache
3. Check browser console for JavaScript errors
4. Verify metrics data files exist

### Pipeline Operations

**Q: How do I trigger a pipeline run?**
A: Use the CLI commands:
```bash
# Single source
python -m somali_dialect_classifier.cli.download_wikisom

# All sources
somali-orchestrate --pipeline all
```

**Q: Can I adjust filter thresholds?**
A: Yes, filters are configurable in each processor's `_register_filters()` method. See [Custom Filters Guide](../howto/custom-filters.md).

**Q: How do I export dashboard data?**
A: Use the export script:
```bash
python scripts/export_dashboard_data.py
```
Data is saved to `_site/data/all_metrics.json`.

---

## Related Documentation

- [Dashboard Technical Guide](dashboard-technical.md) - Architecture and implementation details
- [Filter Breakdown Explanation](filter-breakdown.md) - Deep dive into quality filters
- [Metrics Reference](../reference/metrics.md) - Complete metrics API documentation
- [Troubleshooting Guide](../howto/troubleshooting.md) - Debugging common issues

---

**Questions or Feedback?**
Open an issue on [GitHub](https://github.com/somali-nlp/somali-dialect-classifier/issues) with the `dashboard` label.
