# Dashboard Technical Reference

Interactive Streamlit dashboard for monitoring data pipeline metrics and quality.

**For complete documentation, setup instructions, and usage guide, see**: [Dashboard Guide](../docs/guides/dashboard.md)

---

## Quick Reference

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run app.py
```

Opens at `http://localhost:8501`

### Live Dashboard

**GitHub Pages**: `https://somali-nlp.github.io/somali-dialect-classifier/`
*Status*: Deployment pending - workflow needs to be triggered

---

## Technical Specifications

### Dependencies

- **streamlit** (>=1.28.0) - Web application framework
- **plotly** (>=5.17.0) - Interactive visualizations
- **pandas** (>=2.0.0) - Data manipulation
- **pyarrow** (>=13.0.0) - Parquet file reading

### Data Sources

The dashboard reads from:
- `../data/metrics/*.json` - Pipeline metrics (auto-generated)
- `../data/reports/*.md` - Quality reports (auto-generated)

### File Structure

```
dashboard/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── data/              # Cached dashboard data (local only)
```

### Key Metrics Displayed

1. **Aggregate Metrics**
   - Total records processed
   - Average success rate
   - Data volume (MB)
   - URLs processed
   - Deduplication statistics

2. **Time Series Visualizations**
   - Records over time by source
   - Success rate trends
   - Deduplication rates
   - Throughput (URLs/sec, records/min)
   - Performance (P95 latency)

3. **Source Comparisons**
   - Side-by-side metrics
   - Performance benchmarks
   - Quality indicators

### Auto-Deployment

GitHub Actions workflow automatically deploys the dashboard to GitHub Pages on every push to `main` branch.

See: [`.github/workflows/deploy-dashboard.yml`](../.github/workflows/deploy-dashboard.yml)

---

## Customization

### Adding Metrics

1. Update `MetricsCollector` in `src/somali_dialect_classifier/utils/metrics.py`
2. Add metric to `load_metrics()` function in `app.py`
3. Create visualization for the new metric
4. Test locally, then commit and push

### Modifying Visualizations

All charts use Plotly Express. Example:

```python
import plotly.express as px

fig = px.line(
    df,
    x="timestamp",
    y="your_metric",
    color="source",
    title="Your Metric Over Time"
)
st.plotly_chart(fig, use_container_width=True)
```

### Styling

Streamlit uses its own theming system. Customize in `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

---

## API Reference

### Main Components

#### `load_metrics() -> pd.DataFrame`

Loads all metrics from `data/metrics/*.json` and returns a pandas DataFrame.

**Returns**:
- DataFrame with columns: `timestamp`, `source`, `records`, `success_rate`, etc.

#### `load_quality_reports() -> List[Dict]`

Loads all quality reports from `data/reports/*.md`.

**Returns**:
- List of dictionaries with keys: `source`, `timestamp`, `content`

#### `render_metric_card(title: str, value: str, delta: str = None)`

Renders a metric card using Streamlit's `st.metric()`.

**Parameters**:
- `title`: Metric display name
- `value`: Current value (formatted string)
- `delta`: Optional change indicator

#### `render_time_series_chart(df: pd.DataFrame, y_column: str, title: str)`

Renders an interactive line chart with Plotly.

**Parameters**:
- `df`: DataFrame with `timestamp`, `source`, and metric columns
- `y_column`: Column name for y-axis
- `title`: Chart title

---

## Development

### Local Testing

```bash
# Run with auto-reload on file changes
streamlit run app.py

# Run with debug logging
streamlit run app.py --logger.level=debug

# Run on custom port
streamlit run app.py --server.port=8502
```

### Performance Optimization

```python
# Use caching for expensive operations
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_metrics():
    # ... loading code ...

# Limit data volume
df = df.tail(1000)  # Only last 1000 records

# Use efficient pandas operations
df = df[df["timestamp"] > cutoff_date]  # Filter early
```

### Debugging

```python
# Add debug output
st.write("Debug info:", df.shape)

# Show raw data
with st.expander("Raw Data"):
    st.dataframe(df)

# Log to console
import logging
logging.debug(f"Loaded {len(df)} records")
```

---

## Deployment

### GitHub Pages (Automated)

Dashboard automatically deploys via GitHub Actions on push to `main`.

**Workflow**: `.github/workflows/deploy-dashboard.yml`

**Steps**:
1. Checkout repository
2. Set up Python
3. Install dependencies
4. Generate static dashboard
5. Deploy to GitHub Pages

### Manual Deployment

```bash
# Export static dashboard data
python scripts/export_dashboard_data.py

# Deploy static files to hosting service
# (S3, Netlify, Vercel, etc.)
```

### Environment Variables

Optional environment variables for configuration:

- `SDC_DATA_DIR`: Override data directory location
- `SDC_METRICS_DIR`: Override metrics directory location
- `SDC_REPORTS_DIR`: Override reports directory location

---

## Troubleshooting

### Common Issues

**Dashboard not loading data**:
```bash
# Check metrics exist
ls ../data/metrics/

# Verify JSON format
python -m json.tool ../data/metrics/latest_metrics.json
```

**Plotly charts not rendering**:
```bash
# Update Plotly
pip install plotly --upgrade

# Clear Streamlit cache
rm -rf ~/.streamlit/cache/
```

**Port already in use**:
```bash
# Kill existing process
lsof -i :8501
kill -9 <PID>

# Or use different port
streamlit run app.py --server.port=8502
```

---

## Resources

- **Complete Guide**: [Dashboard Guide](../docs/guides/dashboard.md)
- **Streamlit Docs**: https://docs.streamlit.io
- **Plotly Docs**: https://plotly.com/python/
- **GitHub Actions**: https://docs.github.com/actions

---

**Version**: 1.0.0
**Last Updated**: 2025-10-20
**License**: MIT License
