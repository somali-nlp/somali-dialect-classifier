# Dashboard Guide

**Complete guide to deploying and using the Somali Dialect Classifier data pipeline dashboard.**

**Last Updated**: 2025-10-20

---

## Overview

The Somali Dialect Classifier includes a professional data quality monitoring dashboard with zero hosting costs. This guide covers everything from quick setup to advanced customization.

**What You Get**:
- Live static dashboard on GitHub Pages (public portfolio piece)
- Interactive local dashboard with Streamlit (deep analysis)
- Automated deployments via GitHub Actions
- Real-time metrics visualization
- Quality reports and trend analysis

---

## Table of Contents

- [Quick Start (5 Minutes)](#quick-start-5-minutes)
- [Dashboard Architecture](#dashboard-architecture)
- [Local Development](#local-development)
- [Dashboard Features](#dashboard-features)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Portfolio & Career Impact](#portfolio--career-impact)

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
git commit -m "Add pipeline metrics and quality reports"
git push origin main
```

### Step 3: Update URLs (30 seconds)

Replace `somali-nlp` with your actual GitHub username in these files:

1. **README.md** (badge and link sections)
2. **dashboard/README.md** (live dashboard link)
3. **dashboard/app.py** (footer GitHub link)

Quick replacement command:
```bash
# macOS/Linux
sed -i '' 's/somali-nlp/YOUR-GITHUB-USERNAME/g' README.md dashboard/README.md dashboard/app.py

# Or manually edit the 3 files
```

### Step 4: Deploy (1 minute)

```bash
# Stage all changes
git add README.md dashboard/README.md dashboard/app.py

# Commit
git commit -m "Configure dashboard URLs for deployment"

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

## Dashboard Architecture

### Two Dashboard Versions

#### 1. Static Dashboard (GitHub Pages)

**URL**: `https://YOUR-USERNAME.github.io/somali-dialect-classifier/`

**Features**:
- Key metrics overview
- Links to quality reports
- Source comparison tables
- Zero cost hosting
- Public portfolio piece

**Auto-updates**: On every push to `main` branch

**Best For**: Sharing with employers, portfolio showcase, public metrics

#### 2. Interactive Dashboard (Local/Streamlit)

**Run**: `streamlit run dashboard/app.py`

**Features**:
- Real-time filtering by source and date
- Interactive charts (zoom, pan, select)
- Live data refresh
- Full quality report viewer
- Advanced analytics
- Export capabilities

**Best For**: Deep analysis, debugging, exploration

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
│    streamlit run dashboard/app.py               │
└─────────────┬───────────────────────────────────┘
              │
              └─► http://localhost:8501 (Interactive)

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
│   ├── app.py                    # Interactive Streamlit dashboard
│   ├── requirements.txt          # Dashboard dependencies
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

## Local Development

### Installation

```bash
# Install dashboard dependencies
pip install -r dashboard/requirements.txt
```

Dependencies include:
- `streamlit` - Interactive web dashboard framework
- `plotly` - Interactive charts and visualizations
- `pandas` - Data manipulation
- `pyarrow` - Parquet file reading

### Running the Dashboard

```bash
# Run interactive dashboard
streamlit run dashboard/app.py

# Opens at: http://localhost:8501
```

### Development Loop

```bash
# 1. Run pipeline locally
python -m somali_dialect_classifier.cli.download_bbcsom --max-articles 100

# 2. Test dashboard locally
streamlit run dashboard/app.py

# 3. Commit and push when satisfied
git add data/metrics/ data/reports/
git commit -m "Add BBC Somali pipeline run"
git push origin main

# 4. GitHub Actions automatically updates the live dashboard
#    (Check Actions tab to see deployment)
```

### Advanced Development

```bash
# Run with debug logging
streamlit run dashboard/app.py --logger.level=debug

# Run on custom port
streamlit run dashboard/app.py --server.port=8502

# Disable file watcher (for performance)
streamlit run dashboard/app.py --server.fileWatcherType=none
```

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

#### Step 2: Update Dashboard to Display Metric

```python
# In dashboard/app.py, load_metrics() function
row["custom_metric"] = snapshot.get("custom_metric", 0)

# Add visualization
st.subheader("Custom Metric Analysis")
fig = px.line(
    filtered_df,
    x="timestamp",
    y="custom_metric",
    color="source",
    title="Custom Metric Over Time"
)
st.plotly_chart(fig, use_container_width=True)
```

#### Step 3: Deploy

```bash
# Test locally
streamlit run dashboard/app.py

# Commit and push
git add dashboard/app.py src/somali_dialect_classifier/utils/metrics.py
git commit -m "Add custom metric to dashboard"
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
git commit -m "Add metrics data"
git push

# Wait 2-3 minutes for GitHub Actions to deploy
```

### Local Dashboard Not Loading

**Symptom**: `streamlit run dashboard/app.py` fails or shows errors.

**Solutions**:

```bash
# Reinstall dependencies
pip install -r dashboard/requirements.txt --upgrade

# Check Python version (requires 3.8+)
python --version

# Run with debug logging
streamlit run dashboard/app.py --logger.level=debug

# Clear Streamlit cache
rm -rf ~/.streamlit/cache/

# Check port availability
lsof -i :8501  # Kill conflicting process if needed
```

### Broken Visualizations

**Symptom**: Charts not rendering or showing incorrectly.

**Solutions**:

1. **Update Plotly**:
   ```bash
   pip install plotly --upgrade
   ```

2. **Clear browser cache**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

3. **Check data format**: Ensure metrics JSON has correct structure

4. **Verify Pandas version**:
   ```bash
   pip install pandas>=1.3.0
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

### GitHub Actions Timeout

**Symptom**: Deployment workflow exceeds time limit.

**Solutions**:

1. **Optimize export script**: Reduce data processing in `export_dashboard_data.py`
2. **Use shallow clone**: Modify workflow to use `fetch-depth: 1`
3. **Split workflows**: Separate metric aggregation from deployment

---

## Advanced Features

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

## Next Steps

### Checklist

- [ ] Set up GitHub Pages
- [ ] Push metrics to repository
- [ ] Update URLs in dashboard files
- [ ] Deploy dashboard
- [ ] Test local interactive dashboard
- [ ] Add custom metrics (optional)
- [ ] Screenshot for portfolio
- [ ] Share on LinkedIn
- [ ] Add to resume
- [ ] Create case study blog post

### Further Enhancements

1. **Add more data sources**: Extend pipeline to include additional sources
2. **Implement A/B testing**: Compare different preprocessing strategies
3. **Add model metrics**: Track model performance as you train classifiers
4. **Create API**: Build REST API for programmatic metric access
5. **Add authentication**: Protect dashboard with login for private deployments

---

## Resources

### Documentation

- [Streamlit Documentation](https://docs.streamlit.io)
- [Plotly Python Documentation](https://plotly.com/python/)
- [GitHub Pages Documentation](https://docs.github.com/pages)
- [GitHub Actions Documentation](https://docs.github.com/actions)

### Related Project Documentation

- [Architecture Overview](../overview/architecture.md)
- [Data Pipeline Guide](data-pipeline.md)
- [Deployment Guide](../operations/deployment.md)
- [API Reference](../reference/api.md)

### External Resources

- [Streamlit Gallery](https://streamlit.io/gallery) - Dashboard inspiration
- [Plotly Community](https://community.plotly.com) - Visualization help
- [GitHub Actions Marketplace](https://github.com/marketplace) - Workflow actions

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

**Dashboard Version**: 1.0.0
**Last Updated**: 2025-10-20
**Maintained By**: Somali NLP Team
**License**: MIT License
