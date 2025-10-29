# Dashboard Guide

**Complete guide to deploying, using, and mastering the Somali Dialect Classifier data pipeline dashboard.**

**Last Updated**: 2025-10-28
**Version**: 3.2.0

---

## Overview

The Somali Dialect Classifier includes a professional data quality monitoring dashboard with zero hosting costs. This comprehensive guide covers everything from initial deployment to advanced analytics and customization.

**What You Get**:
- Live static ES6 modular dashboard on GitHub Pages with zero hosting costs
- Real-time metrics visualization and quality reports
- Automated deployments via GitHub Actions
- Advanced filtering, comparison, and export capabilities
- Interactive charts with dark mode support

**Data Sources Monitored**:
- **Wikipedia (Somali)**: Encyclopedia articles
- **BBC Somali**: News content
- **HuggingFace (mC4-so)**: Web-crawled corpus
- **Språkbanken**: Linguistic resources

**Who This Guide Is For**:
- **Project Managers**: Track progress and verify pipeline health
- **Data Scientists**: Analyze data quality and source characteristics
- **ML Engineers**: Optimize pipeline performance and filters
- **Developers**: Debug issues and customize dashboards
- **Stakeholders**: Monitor project metrics and ROI

---

## Table of Contents

- [Quick Start (5 Minutes)](#quick-start-5-minutes)
- [Automated Deployment](#automated-deployment)
- [Manual Deployment](#manual-deployment)
- [Dashboard Features](#dashboard-features)
- [Understanding Visualizations](#understanding-visualizations)
- [Interpreting Metrics](#interpreting-metrics)
- [Dashboard Modes](#dashboard-modes)
- [Common Workflows](#common-workflows)
- [Local Development](#local-development)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Glossary](#glossary)
- [Advanced Features](#advanced-features)
  - [Interactive Data Exploration](#interactive-data-exploration)
  - [Sankey Diagrams](#sankey-diagrams)
  - [Ridge Plots](#ridge-plots)
  - [Bullet Charts](#bullet-charts)
  - [Chart Export (PNG)](#chart-export-png)
  - [Date Range Filtering](#date-range-filtering)
  - [Dark Mode](#dark-mode)
  - [Pipeline Run Comparison](#pipeline-run-comparison)
  - [Advanced Filters](#advanced-filters)
  - [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Quick Start (5 Minutes)

Get your dashboard live on GitHub Pages in 5 minutes.

### Prerequisites

- GitHub account
- Repository pushed to GitHub
- At least one pipeline run completed (to generate metrics data)

### Step 1: Enable GitHub Pages (30 seconds)

1. Go to your repository settings: `https://github.com/YOUR-USERNAME/somali-dialect-classifier/settings/pages`
2. Under **Source**, select: **GitHub Actions**
3. Click **Save**

### Step 2: Add Metrics to Git (1 minute)

Your `.gitignore` is configured to track metrics and reports:

```bash
# Run a pipeline if you haven't already
python -m somali_dialect_classifier.cli.download_wikisom

# Check what will be committed
git status

# You should see files like:
# - data/metrics/*_metrics.json
# - data/reports/*_quality_report.md

# Add them to git
git add data/metrics/ data/reports/
git commit -m "chore(metrics): add pipeline metrics and quality reports"
git push origin main
```

### Step 3: Update URLs (30 seconds)

Replace `somali-nlp` with your actual GitHub username in these files:

1. **README.md** (badge and link sections)
2. **dashboard/README.md** (live dashboard link)
3. **dashboard/index.html** (if needed for absolute paths)

Quick replacement command:
```bash
# macOS/Linux
sed -i '' 's/somali-nlp/YOUR-GITHUB-USERNAME/g' README.md dashboard/README.md dashboard/index.html

# Or manually edit the files
```

### Step 4: Deploy (1 minute)

```bash
# Stage all changes
git add README.md dashboard/README.md dashboard/index.html

# Commit
git commit -m "chore(config): configure dashboard URLs for deployment"

# Push to trigger deployment
git push origin main
```

### Step 5: Watch Deployment (2 minutes)

1. Go to **Actions** tab in your GitHub repository
2. Watch "Deploy Dashboard to GitHub Pages" workflow
3. Wait for green checkmark (typically 2-3 minutes)
4. Visit: `https://YOUR-USERNAME.github.io/somali-dialect-classifier/`

**Your dashboard is now live!**

---

## Automated Deployment

The project includes automated deployment tools to streamline the process of updating the dashboard after pipeline runs.

### Installation

The deployment tools are included in the package:

```bash
pip install -e .
```

Verify commands are available:

```bash
somali-deploy-dashboard --help
somali-orchestrate --help
```

### Common Commands

#### 1. Automated Deployment (Recommended)

Run pipelines and deploy automatically:

```bash
somali-orchestrate --pipeline all --auto-deploy
```

This automatically:
- Collects data from all sources
- Validates metrics files
- Commits to git
- Pushes to GitHub
- Triggers dashboard rebuild

#### 2. Manual Deployment

Deploy existing metrics:

```bash
somali-deploy-dashboard
```

#### 3. Preview Before Deploying

Check what will be deployed:

```bash
somali-deploy-dashboard --dry-run
```

#### 4. Verbose Mode

Debug deployment issues:

```bash
somali-deploy-dashboard --verbose
```

### Typical Workflows

**Daily Data Collection:**

```bash
# Morning: collect data with auto-deploy
somali-orchestrate --pipeline all --auto-deploy

# Verify deployment
# Visit: https://YOUR-USERNAME.github.io/somali-dialect-classifier/
```

**Development Testing:**

```bash
# Test pipeline without deploying
somali-orchestrate --pipeline wikipedia --max-articles 10

# Preview deployment
somali-deploy-dashboard --dry-run

# Deploy if satisfied
somali-deploy-dashboard
```

**Batch Collection:**

```bash
# Run pipelines individually
somali-orchestrate --pipeline wikipedia
somali-orchestrate --pipeline bbc
somali-orchestrate --pipeline huggingface
somali-orchestrate --pipeline sprakbanken

# Deploy all at once
somali-deploy-dashboard --min-sources 4
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Preview without deploying | False |
| `--no-push` | Commit locally only | Push enabled |
| `--no-validate` | Skip validation | Validation on |
| `--no-batch` | Deploy immediately | Batch mode on |
| `--min-sources N` | Min sources for batch | 1 |
| `--verbose` | Detailed logging | Normal logging |
| `--log-file FILE` | Save logs to file | Console only |

---

## Manual Deployment

### Dashboard Architecture

The project includes a modern ES6 modular dashboard:

#### Static Dashboard (GitHub Pages)

**URL**: `https://YOUR-USERNAME.github.io/somali-dialect-classifier/`

**Architecture**: ES6 modular JavaScript with Chart.js visualizations

**Features**:
- Key metrics overview with interactive charts
- Source comparison tables and performance analytics
- Quality reports viewer
- Zero cost hosting
- Automatic updates on push to `main`
- Dark mode support
- Advanced filtering and export capabilities

**Requirements**: Must be served over HTTP (not file:// protocol)

**Local Development**: Run an HTTP server in the `_site/` directory:
```bash
cd _site && python3 -m http.server 8000
# Opens at: http://localhost:8000
```

**Best For**: Public metrics sharing, stakeholder visibility, production dashboard

### Data Flow

#### Local Development Workflow

```
┌─────────────────────────────────────────────────┐
│ 1. Run Pipeline                                 │
│    python -m somali_dialect_classifier.cli...   │
└─────────────┬───────────────────────────────────┘
              │
              ├─► logs/*.log                   (LOCAL ONLY - not committed)
              ├─► data/metrics/*.json          (COMMITTED - used by dashboard)
              └─► data/reports/*.md            (COMMITTED - shown on dashboard)

┌─────────────────────────────────────────────────┐
│ 2. Test Dashboard Locally                       │
│    cd _site && python3 -m http.server 8000     │
└─────────────┬───────────────────────────────────┘
              │
              └─► http://localhost:8000 (ES6 Dashboard)

┌─────────────────────────────────────────────────┐
│ 3. Commit & Push                                │
│    git add data/metrics/ data/reports/          │
│    git push origin main                         │
└─────────────────────────────────────────────────┘
```

#### GitHub Actions Workflow (Automatic)

```
┌─────────────────────────────────────────────────┐
│ Push to main branch                             │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│ GitHub Actions Workflow                         │
│ (.github/workflows/deploy-dashboard.yml)        │
└─────────────┬───────────────────────────────────┘
              │
              ├─► Aggregates metrics
              ├─► Generates static dashboard
              └─► Deploys to GitHub Pages

┌─────────────────────────────────────────────────┐
│ Live Dashboard Updated                          │
│ https://YOUR-USERNAME.github.io/...             │
└─────────────────────────────────────────────────┘
```

### Files Structure

```
├── dashboard/
│   ├── index.html                # Main dashboard HTML
│   ├── css/                      # Stylesheets
│   ├── js/                       # ES6 modular JavaScript
│   │   ├── config.js             # Configuration management
│   │   ├── main.js               # Entry point
│   │   ├── core/                 # Core functionality
│   │   │   ├── data-service.js   # Data loading with normalization
│   │   │   ├── stats.js          # Statistics calculation
│   │   │   ├── charts.js         # Chart rendering
│   │   │   ├── ui-renderer.js    # UI component rendering
│   │   │   └── tabs.js           # Tab navigation
│   │   ├── features/             # Advanced features
│   │   └── utils/                # Utility functions
│   │       ├── logger.js         # Structured logging
│   │       └── formatters.js     # Data formatting utilities
│   ├── build-site.sh             # Build script for deployment
│   └── README.md                 # Technical reference
├── scripts/
│   └── export_dashboard_data.py  # Aggregates metrics for static site
├── .github/workflows/
│   └── deploy-dashboard.yml      # Auto-deploys to GitHub Pages
└── data/
    ├── metrics/                  # JSON metrics (committed)
    └── reports/                  # Quality reports (committed)
```

### What Gets Committed

| File/Directory | Committed? | Reason |
|----------------|------------|--------|
| `logs/*.log` | No | Large, local-only runtime logs |
| `data/metrics/*.json` | Yes | Small, valuable for dashboard |
| `data/reports/*.md` | Yes | Human-readable quality reports |
| `data/silver/*.parquet` | No | Large processed data files |
| `data/bronze/*` | No | Raw downloaded data |
| `dashboard/` code | Yes | Dashboard source code |

---

## Dashboard Features

### Key Metrics Overview

The dashboard displays comprehensive pipeline metrics:

**Aggregate Metrics**:
- Total records processed across all sources
- Average success rate with standard deviation
- Data volume downloaded (MB)
- URLs processed
- Deduplication statistics

**Per-Source Metrics**:
- Records extracted per pipeline run
- Success rates over time
- Throughput (URLs/sec, records/min)
- Performance (P95 fetch latency)
- Deduplication rates

### Hero Metrics (Top of Dashboard)

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

### Source Health Cards

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

### Visualizations

#### 1. Records Over Time
Track pipeline output across all runs, color-coded by source.

**Use Cases**:
- Monitor data collection progress
- Compare source productivity
- Identify anomalies or drops

#### 2. Success Rate Trends
Monitor data quality over time with trend lines.

**Use Cases**:
- Detect quality degradation
- Validate pipeline improvements
- Compare reliability across sources

#### 3. Deduplication Rates
Identify data redundancy patterns across sources.

**Use Cases**:
- Measure dataset uniqueness
- Optimize source selection
- Track duplicate patterns

#### 4. Throughput Analysis
Visualize processing speed (URLs/second, records/minute).

**Use Cases**:
- Performance benchmarking
- Bottleneck identification
- Capacity planning

#### 5. Performance Metrics
P95 fetch latency by source for detailed performance analysis.

**Use Cases**:
- API/scraping performance monitoring
- Identify slow sources
- Optimize rate limiting

#### 6. Source Comparison
Side-by-side comparison of all data sources.

**Use Cases**:
- Select best sources for training
- Evaluate source ROI
- Make data acquisition decisions

### Quality Reports

The dashboard provides access to detailed quality reports generated by each pipeline run:

**Report Contents**:
- Extraction summary
- Filter statistics
- Data quality metrics
- Performance benchmarks
- Error analysis
- Recommendations

**Features**:
- Interactive viewer with markdown rendering
- Filterable by source and date range
- Direct links from metrics to reports
- Mobile-friendly formatting

### Interactive Features (Local Only)

Features available in the local Streamlit dashboard:

**Filters**:
- Date range selector
- Source multi-select
- Metric threshold filters

**Interactions**:
- Zoom and pan on charts
- Hover for detailed tooltips
- Click to drill down
- Export filtered data

**Real-time**:
- Auto-refresh on data changes
- Live metric updates
- Instant filter application

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

### Quality Pass Rate

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

### Performance Metrics

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

### Deduplication Statistics

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

## Dashboard Modes

The dashboard conceptually operates in two modes, tailored to different user needs:

### Executive Mode (Narrative View)

**Purpose**: Quick overview of pipeline status and progress

**Best For**:
- Daily check-ins
- Stakeholder updates
- High-level health monitoring
- Progress reporting

**Key Sections**:

#### 1. Hero Metrics (Top of Dashboard)

See [Dashboard Features → Hero Metrics](#hero-metrics-top-of-dashboard) for details.

#### 2. Source Health Cards

See [Dashboard Features → Source Health Cards](#source-health-cards) for details.

#### 3. Timeline View

Visual timeline showing when each source was last processed.

**Use Case**: Quickly identify stale sources that need attention.

### Analyst Mode (Deep Dive)

**Purpose**: Detailed analysis of data quality, performance, and trends

**Best For**:
- Debugging pipeline issues
- Optimizing filter thresholds
- Understanding quality patterns
- Performance tuning

**Key Sections**:

All detailed metrics described in [Interpreting Metrics](#interpreting-metrics) section, including:
- Quality metrics breakdown
- Source-specific success rates
- Performance metrics
- Deduplication statistics

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

## Local Development

### Requirements

The dashboard is built with ES6 modules and requires:
- Modern web browser (Chrome 61+, Firefox 60+, Safari 11+, Edge 79+)
- HTTP server (ES6 modules cannot load from `file://` protocol)
- No Python dependencies for the dashboard itself

### Running the Dashboard Locally

```bash
# 1. Build the site (aggregates metrics)
./dashboard/build-site.sh

# 2. Start HTTP server in the _site directory
cd _site && python3 -m http.server 8000

# 3. Open browser
# Navigate to: http://localhost:8000
```

**Alternative HTTP servers**:
```bash
# Node.js http-server
npx http-server _site -p 8000

# PHP built-in server
php -S localhost:8000 -t _site

# Ruby WEBrick
ruby -run -e httpd _site -p 8000
```

### Development Loop

```bash
# 1. Run pipeline locally
python -m somali_dialect_classifier.cli.download_bbcsom --max-articles 100

# 2. Rebuild dashboard with new data
./dashboard/build-site.sh

# 3. Refresh browser (no need to restart server)
# The dashboard will load the updated data automatically

# 4. Commit and push when satisfied
git add data/metrics/ data/reports/
git commit -m "chore(metrics): add BBC Somali pipeline run"
git push origin main

# 5. GitHub Actions automatically updates the live dashboard
#    (Check Actions tab to see deployment)
```

### Advanced Development

**Enable Debug Logging** (in browser console):
```javascript
// Set log level to DEBUG
Logger.level = LogLevel.DEBUG;

// Refresh dashboard to see debug output
location.reload();
```

**Test with Different Data Files**:
```javascript
// Override data path in browser console
Config.DATA_PATHS = ['test-data/all_metrics.json'];

// Reload data
location.reload();
```

**Monitor Performance**:
```javascript
// Use Logger's timing utility
Logger.time('data-load');
// ... perform operation ...
Logger.timeEnd('data-load');
```

---

## Customization

### Adding Custom Metrics

#### Step 1: Update Pipeline to Export Metric

```python
# In src/somali_dialect_classifier/utils/metrics.py
# Add to MetricSnapshot dataclass
@dataclass
class MetricSnapshot:
    # ... existing fields ...
    custom_metric: int = 0

# Record during pipeline
collector.increment("custom_metric", value)
```

#### Step 2: Update Export Script

```python
# In scripts/export_dashboard_data.py
# Add to metric entry dictionary
metric_entry = {
    # ... existing fields ...
    "custom_metric": snapshot.get("custom_metric", 0)
}
```

#### Step 3: Update Dashboard JavaScript

```javascript
// In dashboard/js/core/charts.js or create new module
function renderCustomMetricChart(metricsData) {
    const ctx = document.getElementById('customMetricChart').getContext('2d');

    const data = metricsData.metrics.map(m => ({
        x: m.timestamp,
        y: m.custom_metric
    }));

    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Custom Metric',
                data: data,
                borderColor: '#0176D3',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: { type: 'time', title: { display: true, text: 'Date' } },
                y: { beginAtZero: true, title: { display: true, text: 'Value' } }
            }
        }
    });
}

// In dashboard/js/main.js, add to initialization
initCustomMetricChart();
```

#### Step 4: Add HTML Container

```html
<!-- In dashboard/index.html -->
<div class="chart-container">
    <h3>Custom Metric Analysis</h3>
    <canvas id="customMetricChart"></canvas>
</div>
```

#### Step 5: Deploy

```bash
# Test locally
./dashboard/build-site.sh
cd _site && python3 -m http.server 8000
# Open http://localhost:8000 and verify chart appears

# Commit and push
git add dashboard/js/ dashboard/index.html src/somali_dialect_classifier/utils/metrics.py
git commit -m "feat(dashboard): add custom metric visualization"
git push origin main
```

### Customizing Visualizations

#### Change Color Schemes

```python
# In dashboard/app.py
fig = px.line(
    df,
    x="timestamp",
    y="metric",
    color_discrete_sequence=px.colors.qualitative.Set2  # Your palette
)

# Available color palettes:
# - px.colors.qualitative.Plotly
# - px.colors.qualitative.Dark24
# - px.colors.qualitative.Light24
# - px.colors.sequential.Viridis
```

#### Add Custom KPI Cards

```python
# In dashboard/app.py, add metric card:
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Records", f"{total_records:,}")

with col2:
    st.metric("Avg Success Rate", f"{avg_success:.1%}")

with col3:
    your_metric = filtered_df["your_column"].sum()
    st.metric("Your Metric", f"{your_metric:,}")
```

#### Create Custom Charts

```python
import plotly.express as px
import plotly.graph_objects as go

# Line chart with multiple y-axes
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["metric1"], name="Metric 1"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["metric2"], name="Metric 2", yaxis="y2"))
fig.update_layout(yaxis2=dict(overlaying="y", side="right"))
st.plotly_chart(fig, use_container_width=True)

# Bar chart with custom colors
fig = px.bar(
    df,
    x="source",
    y="records",
    color="source",
    title="Records by Source"
)
st.plotly_chart(fig, use_container_width=True)
```

### Dashboard Layout

Modify the dashboard layout in `dashboard/app.py`:

```python
# Create tabs
tab1, tab2, tab3 = st.tabs(["Overview", "Detailed Analysis", "Reports"])

with tab1:
    # Overview content
    st.header("Pipeline Overview")
    # ... metrics and charts ...

with tab2:
    # Detailed analysis
    st.header("Detailed Analysis")
    # ... advanced visualizations ...

with tab3:
    # Quality reports
    st.header("Quality Reports")
    # ... report viewer ...
```

### Responsive Design

The dashboard is already mobile-friendly, but you can customize breakpoints:

```python
# In dashboard/app.py
# Use responsive columns
col1, col2 = st.columns([2, 1])  # 2:1 ratio

# Add mobile-specific styling
st.markdown("""
<style>
@media (max-width: 768px) {
    .metric-card {
        font-size: 14px;
    }
}
</style>
""", unsafe_allow_html=True)
```

---

## Troubleshooting

### Dashboard Not Deploying

**Symptom**: GitHub Actions workflow fails or doesn't run.

**Solutions**:

1. **Check GitHub Pages is enabled**:
   - Go to Settings > Pages
   - Ensure "Source" is set to "GitHub Actions"

2. **Check workflow permissions**:
   - Go to Settings > Actions > General
   - Ensure "Read and write permissions" is enabled

3. **Review workflow logs**:
   - Go to Actions tab
   - Click on failed workflow
   - Review error messages in logs

4. **Common errors**:
   - `No metrics found`: Run a pipeline to generate `data/metrics/*.json`
   - `Permission denied`: Check GitHub Pages settings
   - `404 on dashboard URL`: Wait 3-5 minutes after first deploy

### Dashboard Shows "No Data"

**Symptom**: Dashboard loads but shows empty charts or "No data available".

**Solutions**:

```bash
# Check if metrics exist locally
ls data/metrics/

# Should show files like: 20251020_*_metrics.json

# Verify they're tracked by git
git ls-files data/metrics/

# If not tracked, add them:
git add data/metrics/
git commit -m "chore(metrics): add metrics data"
git push

# Wait 2-3 minutes for GitHub Actions to deploy
```

### Local Dashboard Not Loading

**Symptom**: Dashboard shows "Failed to fetch" errors or blank page.

**Common Cause**: Attempting to open `index.html` directly using `file://` protocol.

**Solution**: Must use HTTP server (ES6 modules require HTTP protocol)

```bash
# 1. Navigate to _site directory
cd _site

# 2. Start HTTP server
python3 -m http.server 8000

# 3. Open browser to http://localhost:8000
# DO NOT open file:///path/to/_site/index.html
```

**Additional Troubleshooting**:

```bash
# Check if data file exists
ls _site/data/all_metrics.json

# Verify data format
python3 -c "import json; print(json.load(open('_site/data/all_metrics.json'))['metrics'][0])"

# Check browser console for errors
# Open DevTools (F12) → Console tab
# Look for CORS errors or module loading failures

# Clear browser cache and reload
# Chrome/Edge: Ctrl+Shift+R
# Firefox: Ctrl+F5
# Safari: Cmd+Shift+R
```

### Broken Visualizations

**Symptom**: Charts not rendering or showing incorrectly.

**Solutions**:

1. **Verify Chart.js loaded**: Check browser console for Chart.js errors

2. **Clear browser cache**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

3. **Check data format**:
   ```bash
   # Verify data structure
   cat _site/data/all_metrics.json | python3 -m json.tool | head -50
   ```

4. **Enable debug logging** (in browser console):
   ```javascript
   Logger.level = LogLevel.DEBUG;
   location.reload();
   ```

5. **Check data normalization**: Dashboard expects flat structure:
   ```json
   {
     "metrics": [{
       "quality_pass_rate": 1.0,
       "records_per_minute": 0.9319,
       "text_length_stats": { "mean": 4875 }
     }]
   }
   ```

### Performance Issues

**Symptom**: Dashboard loads slowly or times out.

**Solutions**:

```python
# In dashboard/app.py, add caching:
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_metrics():
    # ... metric loading code ...

# Limit data loaded
df = df.tail(1000)  # Only show last 1000 records

# Use efficient filtering
df = df[df["timestamp"] > cutoff_date]  # Filter before rendering
```

### Automated Deployment Issues

**"No valid metrics files found":**

```bash
# Run pipelines first
somali-orchestrate --pipeline all
```

**"Failed to push changes":**

```bash
# Check authentication
git push origin main

# If fails, setup SSH key or token
```

**"Not in a git repository":**

```bash
# Navigate to project root
cd /path/to/somali-dialect-classifier
```

**Dashboard not updating:**

1. Check GitHub Actions: https://github.com/YOUR-USERNAME/somali-dialect-classifier/actions
2. Wait 2-3 minutes for build
3. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

### When Things Go Wrong

```bash
# 1. Check git status
git status

# 2. Check metrics exist
ls -lh data/metrics/*.json

# 3. Validate deployment environment
somali-deploy-dashboard --dry-run --verbose

# 4. Check GitHub Actions
# Visit: https://github.com/YOUR-USERNAME/somali-dialect-classifier/actions

# 5. Manual deployment
git add data/metrics/*_processing.json
git commit -m "chore(metrics): manual metrics update"
git push origin main
```

---

## Glossary

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

## Advanced Features

The Somali Dialect Classifier dashboard includes advanced features designed for power users who need deeper insights, custom visualizations, and flexible data exploration capabilities.

### Interactive Data Exploration

#### Source Comparison Table

The dashboard includes an interactive comparison table that provides detailed side-by-side metrics for all data sources.

**Features**:
- Sortable columns (click header to sort)
- Color-coded success rates
- At-a-glance quality metrics
- Pipeline type indicators

**How to Use**:
1. Scroll to "Source Comparison Table" section
2. Click column headers to sort by that metric
3. Hover over rows for highlighting
4. Compare metrics across sources

**Interpretation**:
```
Source    Records  Success Rate  Quality Pass  Dedup Rate
Wiki      9,623    95.2%        63.6%         0.0%
BBC       4,250    94.7%        85.3%         45.2%
HF        50,000   98.1%        72.4%         12.5%
Språk     1,450    99.2%        91.8%         5.3%

→ Wikipedia: High volume, lower quality rate (many stubs)
→ BBC: Moderate volume, high quality, high dedup (frequent updates)
→ HuggingFace: Highest volume, good quality
→ Språkbanken: Lowest volume, highest quality (curated)
```

---

### Sankey Diagrams

**Purpose**: Visualize how data flows through the pipeline from initial discovery through quality filtering to final storage.

#### When to Use

- **Pipeline Optimization**: Identify where most data is lost
- **Quality Analysis**: Understand filter impact visually
- **Stakeholder Communication**: Explain pipeline flow non-technically
- **Bottleneck Detection**: Find stages that need improvement

#### Reading a Sankey Diagram

```
[Discovered] ━━━━━━━━━━━━━━━━━━━━━━━━┓
                                        ┃
                                        ┃ 15,136 records
                                        ▼
                                  [Extracted] ━━━━━━━━┳━━━━━━━━┓
                                                      ┃        ┃
                                      9,623 pass ┃        ┃ 5,513 filtered
                                                      ┃        ┃
                                                      ▼        ▼
                                            [Passed Filters]  [Rejected]
                                                      ┃
                                                      ┃ 9,623 written
                                                      ▼
                                                  [Storage]
```

**Flow Width**: Proportional to record count
**Node Height**: Total throughput at that stage
**Colors**: Different sources or filter types

#### Example Analysis

```javascript
// Wikipedia Sankey interpretation

Discovered: 136 files
    ↓ (100% extraction success)
Extracted: 15,136 records
    ↓ (63.6% quality pass rate)
Passed Filters: 9,623 records
    ├─ min_length_filter: 4,128 rejected (74.9% of rejections)
    ├─ langid_filter: 1,185 rejected (21.5% of rejections)
    └─ empty_after_cleaning: 200 rejected (3.6% of rejections)
    ↓ (0% duplicates)
Stored: 9,623 records

Insights:
→ Primary quality issue: Short articles (stubs)
→ Language detection filtering 21.5% (check confidence threshold)
→ Very few empty pages (good source quality)
→ No duplicates (first run or well-maintained source)
```

#### Configuration

Customize Sankey appearance:

```javascript
const sankeyConfig = {
    nodeWidth: 15,          // Width of boxes
    nodePadding: 10,        // Space between nodes
    iterations: 32,         // Layout optimization passes
    colorScheme: 'tableau', // Color palette
    showValues: true,       // Display counts on flows
    showPercentages: true   // Display % on flows
};
```

#### Troubleshooting

**Issue**: Sankey diagram not rendering

**Solutions**:
1. Check browser console for errors
2. Verify data has required fields: `nodes` and `links`
3. Ensure D3.js library is loaded
4. Check that container element exists

**Issue**: Flow widths seem incorrect

**Solutions**:
1. Verify all link values are positive
2. Check for data type mismatches (string vs number)
3. Ensure conservation of flow (input = output at each node)

---

### Ridge Plots

**Purpose**: Compare distributions of metrics (text length, processing time, quality scores) across different data sources.

#### When to Use

- **Distribution Comparison**: See how metrics vary between sources
- **Outlier Detection**: Identify unusual patterns in one source
- **Quality Assessment**: Compare text length distributions
- **Performance Analysis**: Visualize processing time distributions

#### Reading a Ridge Plot

```
Source A  ┌─────╱╲─────┐
          │    ╱  ╲    │  Mean: 2,500 chars
          └───╱────╲───┘

Source B      ┌──╱╲──┐
              │ ╱  ╲ │      Mean: 1,800 chars
              └╱────╲┘

Source C  ┌───────╱╲───────┐
          │      ╱  ╲      │  Mean: 3,200 chars
          └─────╱────╲─────┘
         ┬─────┬─────┬─────┬
         0    1k    2k    3k   (characters)
```

**Interpretation**:
- **Peak Position**: Most common value (mode)
- **Peak Height**: Density/frequency
- **Width**: Range and variance
- **Shape**: Distribution skew

#### Example Analysis

**Text Length Distribution**:

```
Wikipedia:
  Distribution: Right-skewed (long tail)
  Peak: 800 characters
  Range: 50 - 50,000 characters
  Interpretation: Many short articles (stubs), few long ones

BBC:
  Distribution: Normal (bell curve)
  Peak: 2,500 characters
  Range: 500 - 8,000 characters
  Interpretation: Consistent news article lengths

HuggingFace:
  Distribution: Bimodal (two peaks)
  Peaks: 1,200 and 4,500 characters
  Range: 100 - 20,000 characters
  Interpretation: Mix of short posts and long articles

Språkbanken:
  Distribution: Uniform
  Peak: No clear peak
  Range: 1,000 - 10,000 characters
  Interpretation: Diverse content types
```

#### Configuration

```python
# Backend: Generate ridge plot data
from somali_dialect_classifier.visualization import create_ridge_plot_data

ridge_data = create_ridge_plot_data(
    metrics_data=all_metrics,
    metric_name='text_lengths',
    bins=50,              # Histogram bins
    smoothing='kde',      # Kernel density estimation
    normalize=True        # Scale to same height
)
```

```javascript
// Frontend: Customize appearance
const ridgeConfig = {
    overlap: 0.7,           // How much layers overlap (0-1)
    fillOpacity: 0.6,       // Transparency
    strokeWidth: 2,         // Outline thickness
    colorScheme: 'sources', // Color by source
    showMean: true,         // Mark mean with vertical line
    showMedian: true        // Mark median with dashed line
};
```

#### Use Cases

**1. Quality Control**: Detect if source content quality degraded
```
Before: Normal distribution centered at 2,000 chars
After: Left-skewed distribution centered at 500 chars
→ Source now contains more short/low-quality content
```

**2. Filter Tuning**: Understand impact of length filters
```
Current min_length: 500 chars
Distribution shows: 30% of content between 300-500 chars
Action: Lower threshold to 300 to capture more data
```

---

### Bullet Charts

**Purpose**: Compare actual performance against targets and thresholds in a compact, easy-to-scan format.

#### When to Use

- **KPI Tracking**: Monitor if metrics meet targets
- **Performance Dashboards**: Executive summaries
- **Multi-Source Comparison**: Quick source ranking
- **Goal Setting**: Define acceptable/excellent ranges

#### Reading a Bullet Chart

```
Wikipedia Quality Pass Rate

Poor      Acceptable    Excellent
[████░░░░░░░░░░░░░░░░░░░░░░]  63.6%
  ↑         ↑             ↑
  0        50%           80%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Legend:
● Dark Bar (━━━): Actual performance (63.6%)
○ Light Gray (░): Target performance (70%)
□ Background Zones:
  - Red [0-50%]: Poor
  - Yellow [50-80%]: Acceptable
  - Green [80-100%]: Excellent
```

**Interpretation**:
- **In Green Zone**: Exceeding expectations
- **In Yellow Zone**: Meeting minimum requirements
- **In Red Zone**: Needs immediate attention
- **Below Target**: Gap to close
- **Above Target**: Celebrate success!

#### Example: Multi-Source Performance

```
Quality Pass Rate Comparison

Wikipedia    [████████████░░░░░░░] 63.6% ← Target: 70%
             Poor    OK    Excellent
             Analysis: Slightly below target (yellow zone)
             Action: Review filter thresholds

BBC          [████████████████████] 85.3% ← Target: 80%
             Poor    OK    Excellent
             Analysis: Exceeds target (green zone)
             Action: Maintain current settings

HuggingFace  [██████████████░░░░░░] 72.4% ← Target: 75%
             Poor    OK    Excellent
             Analysis: Near target (yellow zone)
             Action: Minor optimization needed

Språkbanken  [███████████████████░] 91.8% ← Target: 85%
             Poor    OK    Excellent
             Analysis: Excellent performance (green zone)
             Action: Model for other sources
```

#### Configuration

**Define Thresholds**:

```javascript
const bulletConfig = {
    sources: ['Wikipedia', 'BBC', 'HuggingFace', 'Språkbanken'],

    // Define zones (% values)
    ranges: {
        poor: [0, 50],
        acceptable: [50, 80],
        excellent: [80, 100]
    },

    // Set targets per source
    targets: {
        'Wikipedia': 70,
        'BBC': 80,
        'HuggingFace': 75,
        'Språkbanken': 85
    },

    // Customize appearance
    colors: {
        poor: '#f4cccc',
        acceptable: '#fff4cc',
        excellent: '#d1f4d1',
        actual: '#0176D3',
        target: '#888888'
    }
};
```

#### Advanced: Multiple Metrics

Track multiple KPIs per source:

```
Wikipedia Performance Dashboard

Quality Pass Rate   [████████████░░] 63.6% / 70%
Success Rate        [█████████████████] 95.2% / 90%
Deduplication Eff.  [████████████████████] 100% / 95%
Processing Speed    [███████████░░░░] 58.3% / 80%

Overall Score: 79.3% (Acceptable)
```

---

### Chart Export (PNG)

**Purpose**: Save visualizations as high-resolution images for reports, presentations, or offline analysis.

#### PNG Export Features

The dashboard supports exporting charts as PNG images with the following capabilities:

- High resolution (2x pixel density for crisp images)
- Transparent background option
- Includes title and legend
- Instant download

#### How to Export

**Individual Chart**:
```
1. Hover over the chart you want to export
2. Click the "Export PNG" button that appears
3. Image downloads automatically as: chartId_2025-10-27T14-30-00.png
4. Use the exported image in your presentation or report
```

**Programmatic Export**:
```javascript
// Export specific chart programmatically
const exporter = new ChartExporter();

exporter.exportChart('recordsChart', 'png', {
    resolution: 3.0,      // 3x for print quality
    background: 'white',  // Override transparent default
    watermark: false      // Remove branding
});
```

#### Export Settings

**Resolution Options**:
- **Standard (1x)**: 72 DPI, web use
- **High (2x)**: 144 DPI, presentations (default)
- **Print (3x)**: 216 DPI, professional printing

**Background Options**:
- **Transparent**: For overlays (default)
- **White**: For documents

**Include Options**:
- Chart title
- Legend
- Axis labels
- Timestamp
- Source attribution

#### Use Cases

**1. Weekly Reports**:
```
Export: Records Over Time (PNG, 2x)
Usage: Embed in stakeholder email
Benefit: Visual progress update
```

**2. Presentations**:
```
Export: Key charts (PNG, 3x)
Usage: Slide deck
Benefit: High-quality, professional images
```

**3. Documentation**:
```
Export: Architecture diagram (PNG, 2x, white background)
Usage: README.md or docs
Benefit: Explain pipeline visually
```

---

### Date Range Filtering

Filter dashboard data by time period to focus on specific intervals.

**Available Presets**:
- Last 7 days
- Last 30 days
- Last 90 days
- Year to date
- All time
- Custom range

**How to Use**:
1. Click "Date Range" dropdown in top navigation
2. Select preset or choose "Custom Range"
3. For custom: select start and end dates
4. Click "Apply"
5. Dashboard updates all visualizations

**Use Cases**:
```
Last 7 Days:
  → Monitor recent pipeline activity
  → Quick health check
  → Detect immediate issues

Last 90 Days:
  → Identify trends
  → Compare source performance
  → Monthly reporting

Custom Range:
  → Investigate specific incident
  → Compare before/after changes
  → Quarter/year-end reports
```

---

### Dark Mode

Switch between light and dark themes for comfortable viewing in any environment.

**How to Toggle**:
- Click moon/sun icon in top-right navigation
- Or press `Ctrl+Shift+D` (keyboard shortcut)

**Dark Mode Features**:
- Reduces eye strain in low-light environments
- Optimized chart colors for dark backgrounds
- Preserves data readability
- Saves preference in browser

**Accessibility**:
- Meets WCAG AA contrast requirements
- Color schemes tested for colorblind users
- Automatic adjustment based on system preference

---

### Pipeline Run Comparison

Compare metrics between different pipeline runs to track improvements or investigate degradations.

**How to Use**:
1. Click "Compare Runs" button
2. Select two or more runs from the list
3. View side-by-side metrics
4. Toggle between absolute and percentage difference views

**Comparison Metrics**:
- Records collected (delta)
- Success rate change
- Quality pass rate change
- Performance improvements
- Filter efficiency changes

**Example Analysis**:
```
Comparing Wikipedia Runs:
  Run 1 (Oct 20): 9,000 records, 58% quality
  Run 2 (Oct 27): 9,623 records, 63.6% quality

Delta Analysis:
  ↑ +623 records (+6.9%)
  ↑ +5.6% quality pass rate
  → Filter threshold adjusted successfully
```

---

### Advanced Filters

Apply multiple filters to drill down into specific data subsets.

**Available Filters**:
- **Source**: Filter by data source (Wikipedia, BBC, etc.)
- **Pipeline Type**: web_scraping, file_processing, stream_processing
- **Success Rate Range**: Only show runs within success rate bounds
- **Date Range**: Time-based filtering
- **Quality Threshold**: Minimum quality pass rate
- **Record Volume**: Minimum/maximum record counts

**How to Use**:
1. Click "Filters" panel in sidebar
2. Select filter criteria
3. Combine multiple filters
4. Click "Apply Filters"
5. Click "Reset" to clear all filters

**Filter Combinations**:
```
Example 1: Identify Low-Quality Runs
  - Success Rate Range: 0-70%
  - Date Range: Last 30 days
  → Shows problematic runs requiring investigation

Example 2: Compare Scraping Performance
  - Pipeline Type: web_scraping
  - Source: BBC
  - Date Range: Last 90 days
  → Analyze web scraping trends
```

---

### Keyboard Shortcuts

Navigate the dashboard efficiently using keyboard shortcuts.

**Navigation**:
- `Alt+1` through `Alt+6`: Jump to main sections
- `Tab`: Navigate between interactive elements
- `Enter/Space`: Activate buttons and toggles
- `/`: Focus search box (if available)
- `Esc`: Close modals or cancel operations

**Data Operations**:
- `Ctrl+E`: Export current view
- `Ctrl+F`: Open filters panel
- `Ctrl+R`: Refresh data
- `Ctrl+Shift+D`: Toggle dark mode
- `Ctrl+Shift+C`: Open comparison mode

**Accessibility**:
- All features accessible via keyboard
- Skip links for screen readers
- Focus indicators visible
- Logical tab order

---

### Best Practices

#### 1. Regular Monitoring

**Daily Check**:
- Review hero metrics on main dashboard
- Check source health indicators
- Scan bullet charts for red zones (below target performance)

**Weekly Deep Dive**:
- Review Sankey diagrams to identify bottlenecks
- Analyze ridge plots for distribution changes
- Export key charts for weekly reports

#### 2. Data Analysis Workflow

**Step 1: Overview** (5 min)
```
1. Check current metrics
2. Review source comparison table
3. Identify outliers or anomalies
```

**Step 2: Investigate** (15 min)
```
1. Review Sankey diagrams for pipeline flow issues
2. Check ridge plots for unusual distributions
3. Examine bullet charts for performance gaps
```

**Step 3: Root Cause** (30 min)
```
1. Examine ridge plots for distribution shifts
2. Review detailed quality reports
3. Check error logs
4. Formulate hypothesis
```

**Step 4: Action** (varies)
```
1. Adjust filter thresholds if needed
2. Fix pipeline bugs
3. Update documentation
4. Monitor results
```

#### 3. Sharing Insights

**For Stakeholders**:
```
Export: Bullet charts (PNG, high-res, white background)
Why: Clear KPI status at a glance
Format: 2x or 3x resolution for presentations
```

**For Engineers**:
```
Export: Sankey diagrams (PNG)
Why: Technical pipeline analysis
Format: Include timestamps and metadata
```

**For Analysts**:
```
Export: Ridge plots (PNG)
Why: Distribution analysis
Format: High resolution for detailed examination
```

#### 4. Visualization Best Practices

**Sankey Diagrams**:
- Use to identify the biggest sources of data loss
- Focus on stages with large drop-offs
- Compare flow patterns across different sources

**Ridge Plots**:
- Best for comparing 3-5 sources
- Look for distribution shape changes over time
- Identify outliers and unusual patterns

**Bullet Charts**:
- Set realistic targets based on historical data
- Use color zones to quickly assess status
- Update targets quarterly as performance improves

#### 5. Export Organization

**File Naming Convention**:
```
{chart_type}_{source}_{date}_{timestamp}.png

Examples:
  sankey_wikipedia_2025-10-27_143022.png
  ridgeplot_text-length_all-sources_2025-10-27_143022.png
  bullet_quality-metrics_all-sources_2025-10-27_143022.png
```

**Archive Strategy**:
```
Monthly:
  Create folder: exports/2025-10/
  Export key charts
  Include README with context and observations

Quarterly:
  Comprehensive visualization review
  Trend analysis
  Stakeholder summaries
```

---

### Historical Trend Analysis

Store metrics over time to show pipeline improvements:

```python
# Keep all historical metrics in git
# Dashboard automatically shows trends

# Compare current vs. previous runs
current_run = df[df["run_id"] == latest_run]
previous_run = df[df["run_id"] == previous_run]

delta = current_run["metric"].mean() - previous_run["metric"].mean()
st.metric("Success Rate", f"{current_run['metric'].mean():.1%}", delta=f"{delta:.1%}")
```

---

### Monitoring Alerts

Add health checks in GitHub Actions:

```yaml
# In .github/workflows/deploy-dashboard.yml
- name: Check Pipeline Health
  run: |
    python scripts/check_pipeline_health.py
    # Fails workflow if success rate < 80%
```

```python
# scripts/check_pipeline_health.py
import json
import sys
from pathlib import Path

metrics_dir = Path("data/metrics")
latest_metrics = sorted(metrics_dir.glob("*_metrics.json"))[-1]

with open(latest_metrics) as f:
    data = json.load(f)
    success_rate = data["final"]["success_rate"]

    if success_rate < 0.8:
        print(f"ALERT: Success rate {success_rate:.1%} below threshold")
        sys.exit(1)
```

---

### Integration with Other Platforms

#### Export to Google Sheets

```python
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Authenticate
scope = ["https://spreadsheets.google.com/feeds"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Export metrics
sheet = client.open("Pipeline Metrics").sheet1
df_for_export = df[["timestamp", "source", "records", "success_rate"]]
sheet.update([df_for_export.columns.tolist()] + df_for_export.values.tolist())
```

#### Send to Slack

```python
import requests

def send_slack_summary(metrics):
    webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    message = {
        "text": f"Pipeline Run Complete: {metrics['records']} records, {metrics['success_rate']:.1%} success rate"
    }
    requests.post(webhook_url, json=message)
```

#### Sync to Notion

```python
import requests

def update_notion_database(metrics):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Date": {"date": {"start": metrics["timestamp"]}},
            "Records": {"number": metrics["records"]},
            "Success Rate": {"number": metrics["success_rate"]}
        }
    }
    requests.post(url, headers=headers, json=data)
```

---

### FAQ

#### General Questions

**Q: How often is the dashboard updated?**
A: Automatically on every push to `main` branch. GitHub Actions rebuilds the dashboard within 2-3 minutes.

**Q: Can I access historical data?**
A: Yes, all historical metrics are stored in `data/metrics/`. Load them locally or query via the API.

**Q: Why does Wikipedia have a lower quality rate than other sources?**
A: Wikipedia contains many stub articles (very short pages) that fail the `min_length_filter`. This is expected and not a quality issue.

#### Metrics Interpretation

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

#### Troubleshooting

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

#### Pipeline Operations

**Q: How do I trigger a pipeline run?**
A: Use the CLI commands:
```bash
# Single source
python -m somali_dialect_classifier.cli.download_wikisom

# All sources
somali-orchestrate --pipeline all
```

**Q: Can I adjust filter thresholds?**
A: Yes, filters are configurable in each processor's `_register_filters()` method. See the custom filters documentation.

**Q: How do I export dashboard data?**
A: Yes, multiple ways:
1. **Individual charts**: Click "Export PNG" button on any chart
2. **Raw data**: Use the export script:
   ```bash
   python scripts/export_dashboard_data.py
   ```
   Data is saved to `_site/data/all_metrics.json`
3. **CSV export**: Click "Export CSV" in the data table (planned)

#### Advanced Features FAQ

**Q: How do I use dark mode?**
A: Click the moon/sun icon in the top-right navigation, or press `Ctrl+Shift+D`. Your preference is automatically saved.

**Q: Can I compare different pipeline runs?**
A: Yes, click the "Compare Runs" button to select multiple runs and view side-by-side metrics with delta calculations.

**Q: How do date range filters work?**
A: Click "Date Range" in the navigation to select a preset (Last 7/30/90 days) or choose a custom range. All charts update automatically.

**Q: What keyboard shortcuts are available?**
A: Press `?` to view all shortcuts, or see the "Keyboard Shortcuts" section in this guide. Common ones:
- `Ctrl+E`: Export current view
- `Ctrl+F`: Open filters
- `Ctrl+R`: Refresh data
- `Ctrl+Shift+D`: Toggle dark mode

**Q: How do I filter the dashboard data?**
A: Click "Filters" in the sidebar to apply filters by source, pipeline type, success rate, date range, or record volume. Multiple filters can be combined.

**Q: Can I export charts for presentations?**
A: Yes, hover over any chart and click "Export PNG". Charts are exported at high resolution (2x) with transparent backgrounds for easy insertion into slides.

**Q: What are bullet charts and how do I read them?**
A: Bullet charts show performance against targets. The dark bar is actual performance, and color zones indicate Poor (red), Acceptable (yellow), and Excellent (green) ranges. See the "Bullet Charts" section for details.

**Q: What are Sankey diagrams used for?**
A: Sankey diagrams visualize data flow through the pipeline, showing where records are lost at each stage. They're excellent for identifying bottlenecks and understanding filter impact.

**Q: How do ridge plots help with data analysis?**
A: Ridge plots compare metric distributions across sources, making it easy to spot quality issues, outliers, and distribution changes. They're particularly useful for text length analysis and filter tuning.

---

## Related Documentation

### Core Documentation
- [Dashboard Developer Onboarding](dashboard-developer-onboarding.md) - For developers extending the dashboard

### Operations & Maintenance
- [Dashboard Maintenance](../operations/dashboard-maintenance.md) - Operational procedures and troubleshooting
- [Deployment Guide](../operations/deployment.md) - General deployment procedures

### Reference & Architecture
- [Dashboard Architecture](../reference/dashboard-architecture.md) - Technical architecture details
- [Metrics Reference](../reference/metrics.md) - Complete metrics API documentation
- [API Reference](../reference/api.md) - General API documentation

### Development Guides
- [Architecture Overview](../overview/architecture.md) - Project architecture
- [Data Pipeline Guide](data-pipeline.md) - Pipeline implementation details

### External Resources
- [Streamlit Documentation](https://docs.streamlit.io)
- [Plotly Python Documentation](https://plotly.com/python/)
- [GitHub Pages Documentation](https://docs.github.com/pages)
- [GitHub Actions Documentation](https://docs.github.com/actions)

---

## Support

### Getting Help

- **Dashboard Issues**: Open GitHub issue with `dashboard` label
- **Deployment Problems**: Check [Troubleshooting](#troubleshooting) section
- **Feature Requests**: Use GitHub Discussions
- **Questions**: Tag `@maintainers` in issues

### Contributing

Contributions to improve the dashboard are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

**Last Updated**: 2025-10-28
**Maintainers**: Somali NLP Contributors
