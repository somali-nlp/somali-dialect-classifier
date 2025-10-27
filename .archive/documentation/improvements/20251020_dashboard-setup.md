# Dashboard Setup Guide

Step-by-step guide to get your data pipeline dashboard live on GitHub Pages.

## 📋 Prerequisites

- GitHub account
- Your repo pushed to GitHub
- At least one pipeline run completed (to have metrics data)

## 🚀 Quick Setup (5 minutes)

### Step 1: Enable GitHub Pages

1. Go to your repo on GitHub: `https://github.com/somali-nlp/somali-dialect-classifier`
2. Click **Settings** tab
3. Scroll down to **Pages** in the left sidebar
4. Under **Source**, select:
   - Source: `GitHub Actions`
5. Click **Save**

That's it! GitHub Actions is now enabled to deploy your dashboard.

### Step 2: Add Your Metrics to Git

Your `.gitignore` is now configured to track metrics and reports:

```bash
# Make sure you have some metrics generated
# (Run a pipeline if you haven't already)
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

### Step 3: Update URLs in Files

Replace `somali-nlp` with your GitHub username in these files:

1. **README.md** (line 9 and 13):
   ```markdown
   https://somali-nlp.github.io/somali-dialect-classifier/
   ```

2. **dashboard/README.md** (line 5):
   ```markdown
   https://somali-nlp.github.io/somali-dialect-classifier/
   ```

3. **dashboard/app.py** (line 464):
   ```python
   - **GitHub Repository**: [somali-dialect-classifier](https://github.com/somali-nlp/somali-dialect-classifier)
   ```

Quick replace all:
```bash
# On macOS/Linux:
sed -i '' 's/somali-nlp/your-actual-username/g' README.md
sed -i '' 's/somali-nlp/your-actual-username/g' dashboard/README.md
sed -i '' 's/somali-nlp/your-actual-username/g' dashboard/app.py

# Or manually edit these 3 files
```

### Step 4: Commit and Push

```bash
git add README.md dashboard/README.md dashboard/app.py
git commit -m "Configure dashboard URLs"
git push origin main
```

### Step 5: Watch the Magic Happen ✨

1. Go to **Actions** tab in your GitHub repo
2. You should see "Deploy Dashboard to GitHub Pages" workflow running
3. Wait ~2-3 minutes for it to complete
4. Visit: `https://somali-nlp.github.io/somali-dialect-classifier/`

🎉 **Your dashboard is live!**

---

## 🖥️ Local Development

Run the interactive dashboard on your machine:

```bash
# Install dashboard dependencies
pip install -r dashboard/requirements.txt

# Run Streamlit dashboard
streamlit run dashboard/app.py
```

Opens at: `http://localhost:8501`

**Features only available locally:**
- Real-time filtering
- Interactive charts (zoom, pan, select)
- Full quality report viewer
- Date range filters
- Source comparisons

---

## 🔄 Workflow

### Your Development Loop

```bash
# 1. Run pipeline locally
python -m somali_dialect_classifier.cli.download_bbcsom

# 2. Generated files:
#    - logs/*.log              (LOCAL ONLY - not committed)
#    - data/metrics/*.json     (COMMITTED - used by dashboard)
#    - data/reports/*.md       (COMMITTED - shown on dashboard)

# 3. Test dashboard locally
streamlit run dashboard/app.py

# 4. Commit and push when satisfied
git add data/metrics/ data/reports/
git commit -m "Add BBC Somali pipeline run"
git push origin main

# 5. GitHub Actions automatically updates the live dashboard
#    (Check Actions tab to see deployment)
```

### What Gets Committed vs Ignored

| File/Directory | Committed? | Reason |
|----------------|------------|--------|
| `logs/*.log` | ❌ | Large, local-only runtime logs |
| `data/metrics/*.json` | ✅ | Small, valuable for dashboard |
| `data/reports/*.md` | ✅ | Human-readable quality reports |
| `data/silver/*.jsonl` | ❌ | Large processed data files |
| `data/bronze/*` | ❌ | Raw downloaded data |
| `dashboard/` code | ✅ | Dashboard source code |

---

## 📊 Customizing Your Dashboard

### Add a New Metric

1. **Update your pipeline** to export the metric in `MetricsCollector`:

```python
# In src/somali_dialect_classifier/utils/metrics.py
# Add to MetricSnapshot dataclass
custom_metric: int = 0

# Record during pipeline
collector.increment("custom_metric", value)
```

2. **Update dashboard** to display it:

```python
# In dashboard/app.py, load_metrics()
row["custom_metric"] = snapshot.get("custom_metric", 0)

# Add a chart
fig = px.line(filtered_df, x="timestamp", y="custom_metric", color="source")
st.plotly_chart(fig)
```

3. **Test, commit, push** - dashboard auto-updates!

### Change Dashboard Colors

Edit `dashboard/app.py` chart configurations:

```python
# Change color scheme
fig = px.line(
    df, x="timestamp", y="metric",
    color_discrete_sequence=px.colors.qualitative.Set2  # Your palette
)
```

### Add Custom KPIs

```python
# In dashboard/app.py, add new metric card:
with col6:
    your_metric = filtered_df["your_column"].sum()
    st.metric("Your Metric", f"{your_metric:,}")
```

---

## 🐛 Troubleshooting

### Dashboard Not Deploying?

1. **Check GitHub Actions**:
   - Go to **Actions** tab
   - Look for failed workflows
   - Click on workflow to see error logs

2. **Common Issues**:
   - **No metrics found**: Run a pipeline first to generate `data/metrics/*.json`
   - **Permission denied**: Ensure GitHub Pages is enabled in Settings
   - **404 on dashboard URL**: Wait a few minutes after first deploy

### Dashboard Shows "No data"?

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
```

### Local Dashboard Not Loading?

```bash
# Reinstall dependencies
pip install -r dashboard/requirements.txt --upgrade

# Run with verbose output
streamlit run dashboard/app.py --logger.level=debug
```

---

## 🎯 Portfolio Tips

### Screenshot Your Dashboard

Take screenshots for your portfolio/resume:

1. Visit live dashboard
2. Screenshot key metrics section
3. Screenshot interesting charts
4. Add to portfolio with description

### Share Your Dashboard

Add to your:
- Resume (under Projects section)
- LinkedIn (post about it!)
- Portfolio website
- GitHub profile README

Example:
> **Somali NLP Pipeline Dashboard** - Built automated data quality monitoring with
> real-time metrics visualization using Python, Streamlit, and GitHub Actions.
> [Live Demo](https://your-username.github.io/somali-dialect-classifier/)

### Highlight in Interviews

Talk about:
- "Built CI/CD pipeline that automatically deploys dashboards on commit"
- "Implemented structured logging and metrics collection in production pipeline"
- "Created interactive visualizations to monitor 130K+ records across 4 data sources"
- "Used GitHub Pages for zero-cost hosting with automated deployments"

---

## 📚 Next Steps

1. ✅ Set up GitHub Pages
2. ✅ Push metrics to repo
3. ✅ Update URLs
4. ✅ Deploy dashboard
5. ⬜ Add custom metrics
6. ⬜ Screenshot for portfolio
7. ⬜ Share on LinkedIn
8. ⬜ Add to resume

---

## 💡 Advanced Features (Optional)

### Add Historical Trends

Store metrics over time to show pipeline improvements:

```python
# Keep all historical metrics in git
# Dashboard will automatically show trends
```

### Set Up Alerts

Add monitoring alerts in GitHub Actions:

```yaml
- name: Check Success Rate
  run: |
    python scripts/check_pipeline_health.py
    # Fails if success rate < 80%
```

### Export to Other Platforms

- **Notion**: Use Notion API to sync dashboard data
- **Google Sheets**: Export metrics for sharing
- **Slack**: Post pipeline summaries via webhook

---

## 🤝 Need Help?

- **GitHub Issues**: Report dashboard bugs
- **Streamlit Docs**: https://docs.streamlit.io
- **GitHub Pages Docs**: https://docs.github.com/pages

Happy dashboarding! 📊
