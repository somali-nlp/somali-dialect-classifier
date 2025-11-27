# Filter Analytics with Historical Data

**Analyzing filter performance and trends using historical metrics data.**

**Last Updated:** 2025-11-21

## Overview

Filter metrics are exported to Parquet format for historical analysis and trend tracking. This enables data-driven filter optimization, longitudinal studies, and integration with data warehouses.

**Key capabilities:**
- Track filter effectiveness over time
- Identify data quality trends across sources
- Optimize filter thresholds based on historical patterns
- Export to business intelligence tools (Tableau, Looker, Power BI)
- Run SQL queries on filter history with DuckDB

## Quick Start

```bash
# 1. Export filter metrics to Parquet
python scripts/export_filters_to_parquet.py

# 2. Run pre-built analytical queries
python scripts/query_filter_history.py

# 3. Open Jupyter notebook for visualizations
jupyter notebook notebooks/filter_analytics.ipynb
```

## Data Location

**Parquet files:** `data/warehouse/filter_history.parquet/`

**Partition structure:**
```
data/warehouse/filter_history.parquet/
├── source=Wikipedia-Somali/
│   └── month=2025-11/
│       └── part-0.parquet
├── source=TikTok-Somali/
│   └── month=2025-11/
│       └── part-0.parquet
└── ... (5 sources total)
```

**Partitioning strategy:**
- Physical: By `source` (5 directories)
- Logical: By `month` (YYYY-MM subdirectories)
- Benefits: Fast queries when filtering by source or time range

## Exporting Metrics

### Basic Export

```bash
# Export all metrics from data/metrics/*.json
python scripts/export_filters_to_parquet.py

# Expected output:
# ✅ Export complete
#    Total records: 45
#    Unique sources: 5
#    Unique filters: 8
#    Date range: 2025-10-29 to 2025-11-02
#    Output: data/warehouse/filter_history.parquet
```

### Advanced Options

```bash
# Export from custom directory
python scripts/export_filters_to_parquet.py \
  --metrics-dir /custom/path/metrics \
  --output-dir /custom/path/warehouse

# Single file (no partitioning)
python scripts/export_filters_to_parquet.py --no-partitioning

# Verbose logging
python scripts/export_filters_to_parquet.py --verbose
```

### Incremental Mode

The export script automatically skips existing run IDs:

```bash
# First export: Writes 45 records
python scripts/export_filters_to_parquet.py

# Run pipeline to generate new metrics
somali-orchestrate --pipeline all

# Second export: Only adds new records (e.g., 5 new records)
python scripts/export_filters_to_parquet.py
# Output: "Skipped 45 existing run_ids, exported 5 new records"
```

### Automation

Add to your pipeline orchestration:

```python
# In orchestration/flows.py or post-pipeline script
import subprocess

def post_pipeline_export():
    """Export filter metrics to Parquet after pipeline run."""
    subprocess.run([
        "python", "scripts/export_filters_to_parquet.py"
    ], check=True)
```

Or use a cron job:

```bash
# Export daily at 2 AM
0 2 * * * cd /path/to/project && python scripts/export_filters_to_parquet.py
```

## Data Schema

### Parquet Table Schema

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime | Pipeline run timestamp (UTC) |
| `source` | string | Data source (e.g., "Wikipedia-Somali", "TikTok-Somali") |
| `run_id` | string | Unique run identifier (YYYYMMDD_HHMMSS_source_hash) |
| `filter_key` | string | Filter identifier (e.g., "min_length_filter") |
| `filter_label` | string | Human-readable label (e.g., "Minimum length (50 chars)") |
| `filter_category` | string | Category (length, language, content_quality, etc.) |
| `records_filtered` | int | Records filtered by THIS filter |
| `total_records_filtered` | int | Total records filtered (all filters combined) |
| `records_written` | int | Final record count (passed all filters) |
| `quality_pass_rate` | float | Overall quality pass rate (0.0-1.0) |

### Example Record

```json
{
  "timestamp": "2025-11-02T07:11:04+00:00",
  "source": "TikTok-Somali",
  "run_id": "20251102_071104_tiktok-somali_d400941e",
  "filter_key": "emoji_only_comment",
  "filter_label": "Emoji-only comment",
  "filter_category": "content_quality",
  "records_filtered": 250,
  "total_records_filtered": 400,
  "records_written": 800,
  "quality_pass_rate": 0.667
}
```

## Querying Data

### Option 1: DuckDB (SQL)

**Fast, in-process SQL queries on Parquet files:**

```python
import duckdb

con = duckdb.connect()

# Top filters by volume (last 90 days)
query = """
SELECT
    filter_label,
    filter_category,
    COUNT(DISTINCT run_id) AS occurrences,
    SUM(records_filtered) AS total_filtered,
    AVG(records_filtered) AS avg_per_run,
    AVG(records_filtered::FLOAT / NULLIF(total_records_filtered, 0)) AS avg_percentage
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY filter_label, filter_category
ORDER BY total_filtered DESC
"""

df = con.execute(query).df()
print(df)
```

### Option 2: Pandas

**Load into memory for interactive analysis:**

```python
import pandas as pd

# Load all data
df = pd.read_parquet('data/warehouse/filter_history.parquet')

# Filter trends over time
trends = df.groupby([pd.Grouper(key='timestamp', freq='W'), 'filter_label'])['records_filtered'].sum()

# Source comparison
source_stats = df.groupby('source').agg({
    'quality_pass_rate': 'mean',
    'records_written': 'sum',
    'total_records_filtered': 'sum'
})
```

### Option 3: Pre-built Queries

**Run common analytical queries:**

```bash
python scripts/query_filter_history.py

# Outputs:
# 📊 Top Filters (Last 90 Days)
# 🔝 Source Quality Comparison (Last 90 Days)
# 📈 Filter Trends (Last 30 Days)
# 📚 Wikipedia Namespace Filter Trend
```

## Common Analytical Queries

### 1. Filter Effectiveness Over Time

**Which filters remove the most content?**

```sql
SELECT
    filter_label,
    filter_category,
    SUM(records_filtered) AS total_filtered,
    AVG(records_filtered::FLOAT / NULLIF(total_records_filtered, 0)) AS avg_percentage,
    COUNT(DISTINCT run_id) AS pipeline_runs
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY filter_label, filter_category
ORDER BY total_filtered DESC
LIMIT 10
```

### 2. Source Quality Comparison

**Which sources have the highest quality pass rates?**

```sql
SELECT
    source,
    COUNT(DISTINCT run_id) AS total_runs,
    AVG(quality_pass_rate) AS avg_quality_rate,
    AVG(total_records_filtered::FLOAT / NULLIF(records_written + total_records_filtered, 0)) AS avg_rejection_rate,
    SUM(records_written) AS total_records_written,
    SUM(total_records_filtered) AS total_records_filtered
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY source
ORDER BY total_records_written DESC
```

### 3. Filter Trends (Weekly)

**How has filter usage changed over time?**

```sql
SELECT
    DATE_TRUNC('week', timestamp) AS week,
    source,
    filter_key,
    filter_label,
    AVG(records_filtered) AS avg_filtered,
    SUM(records_filtered) AS total_filtered
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY week, source, filter_key, filter_label
ORDER BY week DESC, total_filtered DESC
LIMIT 20
```

### 4. Wikipedia Namespace Filter Analysis

**Track Wikipedia namespace filter over time:**

```sql
SELECT
    DATE_TRUNC('day', timestamp) AS date,
    records_filtered,
    total_records_filtered,
    records_filtered::FLOAT / NULLIF(total_records_filtered, 0) AS percentage
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE source = 'Wikipedia-Somali'
  AND filter_key = 'namespace_filter'
ORDER BY date DESC
LIMIT 30
```

### 5. TikTok Emoji Filter Impact

**Analyze TikTok emoji-only comment filtering:**

```sql
SELECT
    DATE_TRUNC('week', timestamp) AS week,
    AVG(records_filtered::FLOAT / NULLIF(total_records_filtered, 0)) * 100 AS emoji_percentage,
    AVG(records_filtered) AS avg_emoji_filtered,
    AVG(records_written) AS avg_linguistic_comments
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
WHERE source = 'TikTok-Somali'
  AND filter_key = 'emoji_only_comment'
GROUP BY week
ORDER BY week DESC
```

## Jupyter Notebook

### Opening the Notebook

```bash
# Start Jupyter
jupyter notebook notebooks/filter_analytics.ipynb
```

### Notebook Contents

The included notebook provides:

1. **Setup** - Import libraries and load data
2. **Filter trends** - Line charts showing filter activity over time
3. **Category breakdown** - Bar charts by filter category
4. **Source comparison** - Quality rates and rejection rates by source
5. **Heatmaps** - Filter activity patterns across sources and time
6. **Export insights** - Key statistics and findings

### Example Visualization Code

```python
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
con = duckdb.connect()
df = con.execute(
    "SELECT * FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')"
).df()

# Filter trends over time
plt.figure(figsize=(14, 6))
for filter_label in df['filter_label'].unique()[:5]:  # Top 5 filters
    subset = df[df['filter_label'] == filter_label]
    weekly = subset.groupby(pd.Grouper(key='timestamp', freq='W'))['records_filtered'].sum()
    plt.plot(weekly.index, weekly.values, label=filter_label, marker='o')

plt.xlabel('Week')
plt.ylabel('Records Filtered')
plt.title('Filter Trends Over Time (Top 5 Filters)')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

## Data Warehouse Integration

### Export to BigQuery

```python
import pandas_gbq

df = pd.read_parquet('data/warehouse/filter_history.parquet')
pandas_gbq.to_gbq(
    df,
    'somali_nlp.filter_metrics',
    project_id='my-project',
    if_exists='append'
)
```

### Export to Snowflake

```python
from snowflake.connector.pandas_tools import write_pandas

df = pd.read_parquet('data/warehouse/filter_history.parquet')
write_pandas(
    conn=snowflake_conn,
    df=df,
    table_name='FILTER_METRICS',
    database='SOMALI_NLP',
    schema='PUBLIC'
)
```

### Export to PostgreSQL

```python
from sqlalchemy import create_engine

df = pd.read_parquet('data/warehouse/filter_history.parquet')
engine = create_engine('postgresql://user:pass@localhost/somali_nlp')
df.to_sql('filter_metrics', engine, if_exists='append', index=False)
```

## Storage and Performance

### Storage Efficiency

**Compression:** Parquet uses Snappy compression by default (80-90% reduction vs. JSON)

**Example:**
- 45 records × 10 fields × ~50 bytes/field = ~22 KB raw
- Compressed Parquet: ~4 KB (82% reduction)
- Over 1 year (365 runs): ~1.5 MB

**Retention policy:** Indefinite storage recommended (data is valuable, storage is cheap)

### Query Performance

**Typical query times (1 year of data, ~1,800 records):**
- Simple aggregation: <100ms
- Complex joins: <500ms
- Full table scan: <1s

**Optimization tips:**
1. Filter by `source` or `timestamp` (partitioned columns)
2. Use `DATE_TRUNC` for time-based aggregations
3. Limit results with `LIMIT` clause
4. Use DuckDB for faster queries than Pandas

## Troubleshooting

### Issue: No Parquet files generated

**Cause:** No metrics JSON files found in `data/metrics/`

**Solution:**
```bash
# Check metrics directory
ls -lh data/metrics/*_processing.json

# If empty, run pipelines first
somali-orchestrate --pipeline all
```

### Issue: "Module not found: pyarrow"

**Cause:** PyArrow not installed

**Solution:**
```bash
pip install pyarrow pandas duckdb
```

### Issue: Duplicate records in Parquet

**Cause:** Running export script multiple times without incremental mode

**Solution:**
```bash
# Delete and rebuild
rm -rf data/warehouse/filter_history.parquet/
python scripts/export_filters_to_parquet.py
```

### Issue: Query returns empty results

**Cause:** Time filter too restrictive or wrong partition

**Solution:**
```sql
-- Check date range first
SELECT MIN(timestamp), MAX(timestamp)
FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet');

-- Remove date filter
SELECT * FROM read_parquet('data/warehouse/filter_history.parquet/**/*.parquet')
LIMIT 10;
```

## Best Practices

1. **Export regularly** - Run export script after each pipeline run (or daily via cron)
2. **Partition by time** - Keep monthly partitions for fast queries
3. **Monitor storage** - Archive old partitions if storage becomes an issue (>10GB)
4. **Version catalog exports** - Export `filter_catalog.json` alongside Parquet for metadata traceability
5. **Document insights** - Save Jupyter notebooks with findings for future reference
6. **Share queries** - Create a SQL cookbook for common analytical questions

## Related Documentation

- **[Processing Pipelines Guide](processing-pipelines.md#filter-telemetry)** - Filter telemetry overview
- **[Metrics Schema Reference](../reference/metrics-schema.md#filter-telemetry)** - `filter_breakdown` field specification
- **[API Reference](../reference/api.md#export_filter_catalog)** - Export function documentation
- **[CI Monitoring Guide](ci-metrics-anomaly-detection.md)** - Automated anomaly detection

---

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Data Location](#data-location)
- [Exporting Metrics](#exporting-metrics)
  - [Basic Export](#basic-export)
  - [Advanced Options](#advanced-options)
  - [Incremental Mode](#incremental-mode)
  - [Automation](#automation)
- [Data Schema](#data-schema)
  - [Parquet Table Schema](#parquet-table-schema)
  - [Example Record](#example-record)
- [Querying Data](#querying-data)
  - [Option 1: DuckDB (SQL)](#option-1-duckdb-sql)
  - [Option 2: Pandas](#option-2-pandas)
  - [Option 3: Pre-built Queries](#option-3-pre-built-queries)
- [Common Analytical Queries](#common-analytical-queries)
  - [1. Filter Effectiveness Over Time](#1-filter-effectiveness-over-time)
  - [2. Source Quality Comparison](#2-source-quality-comparison)
  - [3. Filter Trends (Weekly)](#3-filter-trends-weekly)
  - [4. Wikipedia Namespace Filter Analysis](#4-wikipedia-namespace-filter-analysis)
  - [5. TikTok Emoji Filter Impact](#5-tiktok-emoji-filter-impact)
- [Jupyter Notebook](#jupyter-notebook)
  - [Opening the Notebook](#opening-the-notebook)
  - [Notebook Contents](#notebook-contents)
  - [Example Visualization Code](#example-visualization-code)
- [Data Warehouse Integration](#data-warehouse-integration)
  - [Export to BigQuery](#export-to-bigquery)
  - [Export to Snowflake](#export-to-snowflake)
  - [Export to PostgreSQL](#export-to-postgresql)
- [Storage and Performance](#storage-and-performance)
  - [Storage Efficiency](#storage-efficiency)
  - [Query Performance](#query-performance)
- [Troubleshooting](#troubleshooting)
  - [Issue: No Parquet files generated](#issue-no-parquet-files-generated)
  - [Issue: "Module not found: pyarrow"](#issue-module-not-found-pyarrow)
  - [Issue: Duplicate records in Parquet](#issue-duplicate-records-in-parquet)
  - [Issue: Query returns empty results](#issue-query-returns-empty-results)
- [Best Practices](#best-practices)

---

**Maintainers:** Somali NLP Contributors
**Maintainers**: Somali NLP Contributors
