# Somali NLP Pipeline Dashboard

Interactive dashboard for monitoring data collection, quality metrics, and pipeline performance.

## 🌐 Live Dashboard

**GitHub Pages (Static)**: https://somali-nlp.github.io/somali-dialect-classifier/

The static version shows key metrics and links to quality reports.

## 🚀 Run Interactive Dashboard Locally

The full interactive dashboard with charts, filters, and real-time analysis:

```bash
# Install dependencies
pip install -r dashboard/requirements.txt

# Run dashboard
streamlit run dashboard/app.py
```

The dashboard will open at `http://localhost:8501`

## 📊 Features

### Key Metrics
- Total records processed across all sources
- Average success rate and standard deviation
- Data volume downloaded
- URLs processed
- Deduplication statistics

### Visualizations
- **Records Over Time**: Track pipeline output per run
- **Success Rate Trends**: Monitor data quality over time
- **Deduplication Rates**: Identify data redundancy patterns
- **Throughput Analysis**: URLs/second and records/minute
- **Performance Metrics**: P95 fetch latency by source
- **Source Comparison**: Compare performance across data sources

### Quality Reports
- Interactive viewer for detailed quality reports
- Markdown rendering of full reports
- Filterable by source and date range

## 📁 Data Sources

The dashboard reads from:
- `data/metrics/*.json` - Pipeline metrics (auto-generated)
- `data/reports/*.md` - Quality reports (auto-generated)

## 🔄 Auto-Deployment

The dashboard automatically deploys to GitHub Pages when:
- New metrics are committed to `data/metrics/`
- New reports are committed to `data/reports/`
- Dashboard code is updated

See [`.github/workflows/deploy-dashboard.yml`](../.github/workflows/deploy-dashboard.yml)

## 🛠️ Customization

### Add New Metrics

Modify the data loading in `app.py`:

```python
# Add new metric to row dictionary
row["your_metric"] = snapshot.get("your_metric", 0)
```

### Add New Charts

Use Plotly Express for quick charts:

```python
import plotly.express as px

fig = px.line(
    filtered_df,
    x="timestamp",
    y="your_metric",
    color="source",
    title="Your Metric Over Time"
)
st.plotly_chart(fig, use_container_width=True)
```

## 📱 Responsive Design

The dashboard is mobile-friendly and adapts to different screen sizes.

## 🎯 Portfolio Value

This dashboard showcases:
- **Data Engineering**: Automated pipeline with quality monitoring
- **Visualization**: Interactive charts and KPIs
- **CI/CD**: Automated deployment with GitHub Actions
- **DevOps**: Production-ready logging and metrics
- **Best Practices**: Structured data, caching, error handling

## 📄 License

Same as parent project - see [LICENSE](../LICENSE)
