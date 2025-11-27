# Dashboard Architecture Reference

**Technical reference for the Somali Dialect Classifier dashboard architecture, metrics pipeline, and data flow.**

**Last Updated:** 2025-11-21

**Last Updated**: 2025-10-28
**Audience**: Software engineers, DevOps engineers, system architects, contributors

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Metrics Pipeline](#metrics-pipeline)
- [Data Flow Diagram](#data-flow-diagram)
- [Schema Documentation](#schema-documentation)
- [Adding New Metrics](#adding-new-metrics)
- [Debugging Zero/Missing Metrics](#debugging-zeromissing-metrics)
- [Performance Considerations](#performance-considerations)

---

## Architecture Overview

### System Components

The dashboard system consists of four main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                     PIPELINE EXECUTION                           │
│  (BasePipeline + Source-Specific Processors)                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Collects metrics via MetricsCollector
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    METRICS STORAGE                               │
│  data/metrics/*.json (Schema v3.0)                              │
│  - Discovery metrics                                            │
│  - Extraction metrics                                           │
│  - Processing metrics                                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Aggregated and transformed
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DASHBOARD GENERATION                            │
│  - export_dashboard_data.py: Aggregates metrics                 │
│  - build-site.sh: Builds static HTML                           │
│  - GitHub Actions: Deploys to GitHub Pages                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Served to users
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LIVE DASHBOARD                                │
│  GitHub Pages (Static HTML + JavaScript + Chart.js)            │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Metrics Collection** | Python (dataclasses, json) | Runtime metric tracking |
| **Storage** | JSON files (v3.0 schema) | Persistent metric storage |
| **Aggregation** | Python scripts | Combine metrics across runs |
| **Visualization** | Chart.js 4.4.0 | Interactive charts |
| **Frontend** | ES6 Modules + HTML5 + CSS3 | Modular dashboard UI |
| **Configuration** | config.js | Externalized settings |
| **Logging** | logger.js | Structured client-side logging |
| **Data Service** | data-service.js | Data loading & normalization |
| **Deployment** | GitHub Actions + Pages | Zero-cost hosting |
| **Monitoring** | Quality reports (Markdown) | Automated insights |

---

## Metrics Pipeline

### Phase 1: Collection (Runtime)

#### MetricsCollector Class

Located: `src/somali_dialect_classifier/utils/metrics.py`

**Initialization**:
```python
from somali_dialect_classifier.utils.metrics import MetricsCollector, PipelineType

collector = MetricsCollector(
    run_id="20251027_120000_wikipedia",
    source="Wikipedia-Somali",
    pipeline_type=PipelineType.FILE_PROCESSING
)
```

**Recording Metrics**:
```python
# Increment counters
collector.increment("files_discovered", 1)
collector.increment("records_extracted", 136)

# Record timing
collector.record_fetch_duration(2895.3)  # milliseconds

# Record text statistics
collector.record_text_length(4416)

# Record filter rejections
collector.record_filter_reason("min_length_filter")

# Record HTTP status (web scraping only)
collector.record_http_status(200)

# Record errors
collector.record_error("TimeoutError")
```

**Export Metrics**:
```python
from pathlib import Path

# Export to JSON with layered metrics
collector.export_json(
    Path("data/metrics/20251027_120000_wikipedia_processing.json"),
    include_layered=True
)

# Export to Prometheus format (optional)
collector.export_prometheus(
    Path("data/metrics/20251027_120000_wikipedia.prom")
)
```

### Phase 2: Layered Metrics Architecture

The v3.0 schema introduces a layered architecture that separates concerns:

```
Layer 1: Connectivity
  └─ Can we reach the source?
      ├─ connection_attempted
      ├─ connection_successful
      └─ connection_duration_ms

Layer 2: Extraction (Pipeline-Specific)
  └─ Can we retrieve data?
      ├─ Web Scraping: HTTP requests, content extraction
      ├─ File Processing: File reading, record parsing
      └─ Stream Processing: Stream connection, batch retrieval

Layer 3: Quality
  └─ Does data meet standards?
      ├─ records_received
      ├─ records_passed_filters
      └─ filter_breakdown

Layer 4: Volume
  └─ How much data?
      ├─ records_written
      ├─ bytes_downloaded
      └─ total_chars
```

**Benefits**:
- Clear separation of concerns
- Pipeline-specific metrics
- Easier debugging (layer isolation)
- Consistent quality measurement

### Phase 3: Storage (JSON Files)

#### Schema v3.0 Structure

```json
{
  "_schema_version": "3.0",
  "_pipeline_type": "file_processing",
  "_timestamp": "2025-10-27T12:00:00Z",
  "_run_id": "20251027_120000_wikipedia",
  "_source": "Wikipedia-Somali",

  "layered_metrics": {
    "connectivity": {
      "connection_attempted": true,
      "connection_successful": true,
      "connection_duration_ms": 100.5,
      "connection_error": null
    },
    "extraction": {
      "files_discovered": 1,
      "files_processed": 1,
      "files_failed": 0,
      "records_extracted": 136,
      "extraction_errors": {}
    },
    "quality": {
      "records_received": 15136,
      "records_passed_filters": 9623,
      "filter_breakdown": {
        "min_length_filter": 4128,
        "langid_filter": 1185,
        "empty_after_cleaning": 200
      }
    },
    "volume": {
      "records_written": 9623,
      "bytes_downloaded": 14254080,
      "total_chars": 42500000
    }
  },

  "legacy_metrics": {
    "snapshot": {
      "timestamp": "2025-10-27T12:00:00Z",
      "run_id": "20251027_120000_wikipedia",
      "source": "Wikipedia-Somali",
      "duration_seconds": 36.5,
      "pipeline_type": "file_processing",
      "files_discovered": 1,
      "files_processed": 1,
      "records_extracted": 136,
      "bytes_downloaded": 14254080,
      "records_written": 9623,
      "records_filtered": 5513,
      "filter_reasons": {
        "min_length_filter": 4128,
        "langid_filter": 1185,
        "empty_after_cleaning": 200
      },
      "fetch_durations_ms": [28953.2],
      "process_durations_ms": [3647.1],
      "text_lengths": [/* last 1000 samples */],
      "unique_hashes": 0,
      "duplicate_hashes": 0,
      "near_duplicates": 0
    },
    "statistics": {
      "file_extraction_success_rate": 1.0,
      "record_parsing_success_rate": 1.0,
      "quality_pass_rate": 0.636,
      "deduplication_rate": 0.0,
      "fetch_duration_stats": {
        "min": 28953.2,
        "max": 28953.2,
        "mean": 28953.2,
        "median": 28953.2,
        "p95": 28953.2,
        "p99": 28953.2
      },
      "throughput": {
        "urls_per_second": 0.027,
        "bytes_per_second": 390589.0,
        "records_per_minute": 15834.2
      },
      "_metric_semantics": {
        "file_extraction_success_rate": "File-level extraction success (local file I/O, not HTTP)",
        "quality_pass_rate": "Records passing quality filters (after deduplication)"
      }
    }
  }
}
```

#### File Naming Convention

```
{timestamp}_{source}_{run_id_hash}_{phase}.json

Examples:
  20251027_120000_wikipedia-somali_c2915cab_discovery.json
  20251027_120000_wikipedia-somali_c2915cab_extraction.json
  20251027_120000_wikipedia-somali_c2915cab_processing.json
```

**Phases**:
- `discovery`: Source discovery phase metrics (URLs found, files discovered)
- `extraction`: Data extraction phase metrics (downloads, parsing)
- `processing`: Final processing metrics (filtering, deduplication, writing)

### Phase 4: Aggregation

#### export_dashboard_data.py

Located: `scripts/export_dashboard_data.py`

**Purpose**: Aggregate individual metric files into dashboard-ready format

**Input**: `data/metrics/*_processing.json`

**Output**:
- `_site/data/summary.json`: High-level summary statistics
- `_site/data/all_metrics.json`: All metrics combined
- `_site/data/reports.json`: List of quality reports

**Algorithm**:

```python
def load_all_metrics() -> List[Dict[str, Any]]:
    """
    Load all metrics JSON files from data/metrics/.

    Returns list of metric entries, deduplicated by run_id.
    """
    metrics_dir = Path("data/metrics")
    all_metrics = []
    seen_runs = set()

    for metrics_file in metrics_dir.glob("*_processing.json"):
        with open(metrics_file) as f:
            data = json.load(f)

        # Extract from v3.0 schema
        snapshot = data.get("legacy_metrics", {}).get("snapshot", {})
        stats = data.get("legacy_metrics", {}).get("statistics", {})

        run_id = snapshot.get("run_id", "")

        # Deduplicate by run_id
        if run_id not in seen_runs:
            seen_runs.add(run_id)
            all_metrics.append({
                "run_id": run_id,
                "source": snapshot.get("source", ""),
                "timestamp": snapshot.get("timestamp", ""),
                "records_written": snapshot.get("records_written", 0),
                "success_rate": stats.get("quality_pass_rate", 0),
                # ... more fields
            })

    return all_metrics
```

**Summary Generation**:

```python
def generate_summary(metrics: List[Dict]) -> Dict:
    """
    Generate summary statistics for dashboard.

    Returns:
        - total_records: Sum of all records_written
        - avg_success_rate: Mean of all quality_pass_rates
        - sources: List of unique sources
        - total_runs: Count of pipeline runs
        - source_breakdown: Per-source statistics
    """
    return {
        "total_records": sum(m["records_written"] for m in metrics),
        "total_urls_processed": sum(m["urls_processed"] for m in metrics),
        "avg_success_rate": sum(m["success_rate"] for m in metrics) / len(metrics),
        "sources": sorted(list(set(m["source"] for m in metrics))),
        "last_update": sorted_metrics[-1]["timestamp"],
        "total_runs": len(metrics),
        "source_breakdown": {
            source: {
                "records": sum(m["records_written"] for m in source_metrics),
                "runs": len(source_metrics),
                "avg_success_rate": sum(m["success_rate"] for m in source_metrics) / len(source_metrics),
                "last_run": max(m["timestamp"] for m in source_metrics)
            }
            for source in summary["sources"]
        }
    }
```

### Phase 5: Visualization (Dashboard)

#### Frontend Architecture

Located: `dashboard/index.html` with `dashboard/js/` modules

**Architecture**: ES6 Modular Design

**Module Structure**:
```
dashboard/js/
├── config.js                  # Configuration management
├── main.js                    # Entry point & initialization
├── core/                      # Core functionality
│   ├── data-service.js       # Data loading & normalization
│   ├── stats.js              # Statistics calculation
│   ├── charts.js             # Chart rendering (Chart.js)
│   ├── ui-renderer.js        # UI component rendering
│   └── tabs.js               # Tab navigation
├── features/                  # Advanced features
│   ├── export-manager.js     # Export functionality
│   ├── advanced-charts.js    # Sankey, Ridge plots
│   └── comparison.js         # Run comparison
└── utils/                     # Utilities
    ├── logger.js             # Structured logging
    └── formatters.js         # Data formatting
```

**Technologies**:
- **ES6 Modules**: Native browser modules for modular code organization
- **Chart.js 4.4.0**: Interactive charts
- **Structured Logging**: Client-side logger with level control
- **Configuration Management**: Externalized config with override support
- **Data Normalization**: Automatic flattening of nested data structures
- **Responsive CSS**: Mobile-first design with dark mode support

**Data Loading** (data-service.js):

```javascript
// New ES6 modular approach with data normalization
import { Config } from '../config.js';
import { Logger } from '../utils/logger.js';

let metricsData = null;

export async function loadMetrics() {
    if (metricsData) {
        Logger.debug('Using cached metrics data');
        return metricsData;
    }

    Logger.info('Starting metrics data load...');

    try {
        // Try each configured path with fallback
        const data = await fetchWithFallback(Config.DATA_PATHS);

        // Normalize nested structures to flat format
        metricsData = normalizeMetrics(data);

        Logger.info(`Metrics loaded successfully: ${metricsData.metrics.length} records`);
        return metricsData;
    } catch (error) {
        Logger.error('Failed to load metrics', error);
        throw error;
    }
}

function normalizeMetrics(rawData) {
    if (!rawData || !Array.isArray(rawData.metrics)) {
        throw new DataValidationError('Invalid data format');
    }

    return {
        ...rawData,
        metrics: rawData.metrics.map(normalizeMetricRecord)
    };
}

function normalizeMetricRecord(metric) {
    // Flatten nested structures (Bug fixes #2-5)
    return {
        ...metric,
        quality_pass_rate: metric.quality_pass_rate ||
                          metric.pipeline_metrics?.quality_pass_rate || 0,
        records_per_minute: metric.records_per_minute ||
                           metric.performance?.records_per_minute || 0,
        text_length_stats: metric.text_length_stats ||
                          metric.quality ||
                          { min: 0, max: 0, mean: 0 }
    };
}
```

**Chart Rendering** (charts.js):

```javascript
// Modular chart rendering with error handling
import { Logger } from '../utils/logger.js';

export function initCharts(metricsData) {
    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        Logger.warn('No metrics data available for charts');
        return;
    }

    try {
        renderRecordsOverTime(metricsData);
        renderQualityRateChart(metricsData);
        renderSourceDistribution(metricsData);
        // ... more charts
    } catch (error) {
        Logger.error('Failed to initialize charts', error);
    }
}

function renderRecordsOverTime(metricsData) {
    const ctx = document.getElementById('recordsChart')?.getContext('2d');
    if (!ctx) {
        Logger.warn('Records chart canvas not found');
        return;
    }

    // Group by source with defensive checks
    const bySource = {};
    metricsData.metrics.forEach(m => {
        const source = m.source || 'Unknown';
        if (!bySource[source]) bySource[source] = [];
        bySource[source].push({
            x: m.timestamp,
            y: m.records_written || 0
        });
    });

    // Create datasets with color mapping
    const datasets = Object.keys(bySource).map(source => ({
        label: source,
        data: bySource[source],
        borderColor: Config.CHART_COLORS[source] || '#666666',
        backgroundColor: `${Config.CHART_COLORS[source] || '#666666'}20`,
        tension: 0.4
    }));

    new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'day' },
                    title: { display: true, text: 'Date' }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Records Collected' }
                }
            },
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            }
        }
    });

    Logger.debug('Records chart rendered successfully');
}
```

**Key Improvements in ES6 Architecture**:
1. **Modular Design**: Each concern (data, stats, charts, UI) in separate module
2. **Data Normalization**: Automatic flattening of nested structures
3. **Error Handling**: Graceful degradation with user-friendly messaging
4. **Structured Logging**: Environment-aware logging (verbose in dev, quiet in prod)
5. **Configuration Management**: Externalized paths and settings
6. **Code Quality**: 9.0/10 score with comprehensive documentation

---

## Data Flow Diagram

### Complete Pipeline Flow

```
┌───────────────────────────────────────────────────────────────────┐
│ 1. PIPELINE EXECUTION                                             │
│                                                                   │
│  User Trigger:                                                   │
│    python -m somali_dialect_classifier.cli.download_wikisom     │
│                                                                   │
│  Pipeline Phases:                                               │
│    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐│
│    │  Discovery   │ ───▶ │  Extraction  │ ───▶ │  Processing  ││
│    └──────────────┘      └──────────────┘      └──────────────┘│
│         │                      │                      │         │
│         │ MetricsCollector     │ MetricsCollector     │ MetricsCollector
│         ▼                      ▼                      ▼         │
│    discovery.json        extraction.json        processing.json│
└───────────────────────────────────────────────────────────────────┘
                               │
                               │ Files written to data/metrics/
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│ 2. QUALITY REPORT GENERATION                                      │
│                                                                   │
│  QualityReporter reads processing.json                          │
│    └─▶ Generates Markdown report                                │
│        └─▶ data/reports/*_quality_report.md                     │
└───────────────────────────────────────────────────────────────────┘
                               │
                               │ Optional: Auto-deploy
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│ 3. GIT COMMIT (via DashboardDeployer)                            │
│                                                                   │
│  DashboardDeployer:                                              │
│    1. Validates metrics files                                    │
│    2. Generates commit message                                   │
│    3. git add data/metrics/*_processing.json                     │
│    4. git commit -m "chore(metrics): update metrics for ..."     │
│    5. git push origin main                                       │
└───────────────────────────────────────────────────────────────────┘
                               │
                               │ Triggers GitHub Actions
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│ 4. GITHUB ACTIONS WORKFLOW                                        │
│    (.github/workflows/deploy-dashboard-v2.yml)                   │
│                                                                   │
│  Steps:                                                          │
│    1. Checkout repository                                        │
│    2. Set up Python 3.11                                         │
│    3. Install dependencies                                       │
│    4. Run export_dashboard_data.py                               │
│       └─▶ Generates _site/data/all_metrics.json                 │
│    5. Run build-site.sh                                          │
│       └─▶ Copies index.html to _site/                           │
│    6. Deploy to GitHub Pages                                     │
│       └─▶ Publishes _site/ directory                            │
└───────────────────────────────────────────────────────────────────┘
                               │
                               │ 2-3 minutes
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│ 5. LIVE DASHBOARD                                                 │
│    https://USERNAME.github.io/somali-dialect-classifier/         │
│                                                                   │
│  User visits dashboard                                           │
│    └─▶ Browser loads index.html                                 │
│        └─▶ JavaScript fetches all_metrics.json                  │
│            └─▶ Chart.js renders visualizations                  │
└───────────────────────────────────────────────────────────────────┘
```

### Metric File Lifecycle

```
Creation:
  BasePipeline._finalize_phase()
    └─▶ collector.export_json(metrics_path)
        └─▶ data/metrics/{timestamp}_{source}_{hash}_{phase}.json

Validation:
  MetricsValidator.validate_metrics_file()
    └─▶ Check required fields
    └─▶ Validate timestamp format
    └─▶ Verify logical consistency

Aggregation:
  export_dashboard_data.py
    └─▶ Load all *_processing.json files
    └─▶ Deduplicate by run_id
    └─▶ Generate summary statistics
    └─▶ Export to _site/data/

Deployment:
  GitHub Actions
    └─▶ Copy to Pages branch
    └─▶ Serve to users
```

---

## Schema Documentation

### Pydantic Models

All metrics use dataclasses with validation:

#### ConnectivityMetrics

```python
@dataclass
class ConnectivityMetrics:
    """Layer 1: Source connectivity metrics."""
    connection_attempted: bool = False
    connection_successful: bool = False
    connection_duration_ms: float = 0.0
    connection_error: Optional[str] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate logical consistency."""
        if self.connection_successful and not self.connection_attempted:
            return False, "Connection marked successful but not attempted"
        if self.connection_duration_ms < 0:
            return False, "Connection duration cannot be negative"
        return True, None
```

#### WebScrapingExtractionMetrics

```python
@dataclass
class WebScrapingExtractionMetrics(ExtractionMetrics):
    """Layer 2: Web scraping extraction metrics."""
    http_requests_attempted: int = 0
    http_requests_successful: int = 0
    http_status_distribution: Dict[int, int] = field(default_factory=dict)
    pages_parsed: int = 0
    content_extracted: int = 0

    @property
    def http_success_rate(self) -> float:
        if self.http_requests_attempted == 0:
            return 0.0
        return self.http_requests_successful / self.http_requests_attempted
```

#### QualityMetrics

```python
@dataclass
class QualityMetrics:
    """Layer 3: Data quality metrics."""
    records_received: int = 0
    records_passed_filters: int = 0
    filter_breakdown: Dict[str, int] = field(default_factory=dict)

    @property
    def quality_pass_rate(self) -> float:
        if self.records_received == 0:
            return 0.0
        return self.records_passed_filters / self.records_received
```

### Schema Evolution

**v1.0 → v2.0**: Added pipeline_type field
**v2.0 → v3.0**: Introduced layered metrics architecture

**Backward Compatibility**:
- v3.0 files include `legacy_metrics` wrapper
- Old tools can still read `legacy_metrics.snapshot`
- New tools prefer `layered_metrics` when available

---

## Adding New Metrics

### Step 1: Update MetricsCollector

Add counter or tracking method:

```python
# In src/somali_dialect_classifier/utils/metrics.py

class MetricsCollector:
    def __init__(self, ...):
        # Add to counters
        self.counters["my_new_metric"] = 0

    def record_my_new_metric(self, value: int):
        """Track custom metric."""
        self.counters["my_new_metric"] += value
```

### Step 2: Update MetricSnapshot

Add field to dataclass:

```python
@dataclass
class MetricSnapshot:
    # ... existing fields ...
    my_new_metric: int = 0
```

### Step 3: Update get_snapshot()

Include new metric in snapshot:

```python
def get_snapshot(self) -> MetricSnapshot:
    return MetricSnapshot(
        # ... existing fields ...
        my_new_metric=self.counters["my_new_metric"]
    )
```

### Step 4: Update Dashboard Export

Modify `export_dashboard_data.py`:

```python
metric_entry = {
    # ... existing fields ...
    "my_new_metric": snapshot.get("my_new_metric", 0)
}
```

### Step 5: Update Dashboard Visualization

Add chart in `index.html`:

```javascript
function renderMyNewMetric(data) {
    const ctx = document.getElementById('myNewChart').getContext('2d');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.metrics.map(m => m.source),
            datasets: [{
                label: 'My New Metric',
                data: data.metrics.map(m => m.my_new_metric),
                backgroundColor: '#0176D3'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}
```

### Step 6: Update Documentation

Document the new metric:

```markdown
## My New Metric

**Definition**: Description of what this metric measures

**Formula**: `my_new_metric = ...`

**Good Value**: > 90%

**Use Cases**:
- Use case 1
- Use case 2
```

---

## Debugging Zero/Missing Metrics

### Common Causes

#### 1. Metric Not Being Recorded

**Symptom**: Metric shows 0 in dashboard

**Check**:
```python
# Add logging to pipeline
logger.info(f"Recording my_metric: {value}")
collector.increment("my_metric", value)
```

**Verify**:
```bash
# Check if metric appears in JSON
cat data/metrics/latest_processing.json | jq '.legacy_metrics.snapshot.my_metric'
```

#### 2. Metric Not Exported

**Symptom**: Metric exists in collector but not in JSON

**Check**:
```python
# Verify get_snapshot() includes field
snapshot = collector.get_snapshot()
print(snapshot.my_metric)  # Should not raise AttributeError
```

#### 3. Aggregation Issue

**Symptom**: Metric in JSON but not in dashboard data

**Check**:
```python
# Test export script locally
python scripts/export_dashboard_data.py
cat _site/data/all_metrics.json | jq '.[0].my_metric'
```

#### 4. Dashboard Not Rendering

**Symptom**: Metric in data file but chart empty

**Check**:
1. Browser console for JavaScript errors
2. Network tab for failed data loads
3. Chart.js data mapping:
   ```javascript
   console.log("Data:", data.metrics.map(m => m.my_metric));
   ```

### Debugging Workflow

```bash
# 1. Verify metric recorded during pipeline run
python -m somali_dialect_classifier.cli.download_wikisom --max-articles 10
grep "my_metric" logs/*.log

# 2. Check metric in JSON file
latest_file=$(ls -t data/metrics/*_processing.json | head -1)
jq '.legacy_metrics.snapshot.my_metric' "$latest_file"

# 3. Test aggregation
python scripts/export_dashboard_data.py
jq '.[0].my_metric' _site/data/all_metrics.json

# 4. Build dashboard locally
cd dashboard
bash build-site.sh
python -m http.server 8000
# Visit http://localhost:8000/_site/
```

---

## Performance Considerations

### Metrics Collection Overhead

**Guideline**: Metrics should add < 5% overhead to pipeline execution

**Optimization Strategies**:

1. **Batch Statistics**:
   ```python
   # Bad: O(n) for each sample
   for text in texts:
       collector.record_text_length(len(text))

   # Good: O(n) once
   lengths = [len(t) for t in texts]
   collector.text_lengths.extend(lengths)
   ```

2. **Sampling**:
   ```python
   # Only keep last 1000 samples
   collector.text_lengths = collector.text_lengths[-1000:]
   ```

3. **Lazy Computation**:
   ```python
   # Don't compute percentiles until export
   @property
   def p95(self):
       return self._percentile(self.fetch_durations_ms, 95)
   ```

### Dashboard Load Performance

**Metrics**:
- Initial load: < 2 seconds
- Chart render: < 500ms
- Data fetch: < 200ms

**Optimization**:

1. **Use Consolidated Metrics**:
   ```javascript
   // Prefer single large file over multiple small files
   const data = await fetch('all_metrics.json');
   ```

2. **Lazy Load Charts**:
   ```javascript
   // Render above-the-fold charts first
   window.addEventListener('DOMContentLoaded', () => {
       renderHeroMetrics();
       renderRecordsChart();
   });

   // Defer below-the-fold charts
   window.addEventListener('load', () => {
       renderPerformanceCharts();
       renderFilterBreakdown();
   });
   ```

3. **Limit Data Points**:
   ```javascript
   // Only show last 30 days
   const cutoffDate = new Date();
   cutoffDate.setDate(cutoffDate.getDate() - 30);
   const recentData = data.metrics.filter(m =>
       new Date(m.timestamp) > cutoffDate
   );
   ```

### Storage Efficiency

**Current Usage**:
- Per-run metrics: 3-5 KB
- 100 runs: 300-500 KB
- Yearly projection: 3-5 MB

**Strategies**:

1. **Prune Old Metrics**:
   ```bash
   # Keep only last 90 days
   find data/metrics -name "*.json" -mtime +90 -delete
   ```

2. **Compress Archives**:
   ```bash
   # Monthly archival
   tar -czf metrics-2025-01.tar.gz data/metrics/202501*.json
   ```

3. **Limit Sample Retention**:
   ```python
   # Keep only last 1000 samples of distributions
   snapshot.fetch_durations_ms = snapshot.fetch_durations_ms[-1000:]
   ```

---

## Advanced Visualization Components

### Sankey Diagram Architecture

**Purpose**: Visualize data flow through the pipeline from discovery through quality filtering to final storage.

**Data Structure**:

```javascript
const sankeyData = {
    nodes: [
        { id: 'discovered', label: 'Records Discovered' },
        { id: 'extracted', label: 'Extracted' },
        { id: 'passed_filters', label: 'Passed Filters' },
        { id: 'duplicates', label: 'Duplicates' },
        { id: 'written', label: 'Written to Storage' }
    ],
    links: [
        { source: 'discovered', target: 'extracted', value: 15136 },
        { source: 'extracted', target: 'passed_filters', value: 9623 },
        { source: 'extracted', target: 'duplicates', value: 0 },
        { source: 'passed_filters', target: 'written', value: 9623 }
    ]
};
```

**Implementation**:

```javascript
function renderSankeyDiagram(data) {
    // Convert metrics to Sankey format
    const nodes = buildNodes(data);
    const links = buildLinks(data);

    // Use D3-sankey or Chart.js Sankey plugin
    const sankey = d3.sankey()
        .nodeWidth(15)
        .nodePadding(10)
        .extent([[1, 1], [width - 1, height - 6]]);

    const graph = sankey({
        nodes: nodes,
        links: links
    });

    // Render SVG
    renderSankeyNodes(graph.nodes);
    renderSankeyLinks(graph.links);
}

function buildNodes(metricsData) {
    const totalDiscovered = metricsData.files_discovered || metricsData.urls_discovered;
    const totalExtracted = metricsData.records_extracted;
    const totalPassedFilters = metricsData.records_passed_filters;
    const totalDuplicates = metricsData.duplicate_records;
    const totalWritten = metricsData.records_written;

    return [
        { id: 0, name: `Discovered\n${totalDiscovered.toLocaleString()}` },
        { id: 1, name: `Extracted\n${totalExtracted.toLocaleString()}` },
        { id: 2, name: `Quality Check\n${totalPassedFilters.toLocaleString()}` },
        { id: 3, name: `Duplicates\n${totalDuplicates.toLocaleString()}` },
        { id: 4, name: `Stored\n${totalWritten.toLocaleString()}` }
    ];
}
```

**Use Cases**:
- Identify bottlenecks in the pipeline
- Visualize filter impact
- Understand deduplication efficiency
- Communicate pipeline flow to stakeholders

### Ridge Plot Implementation

**Purpose**: Show distribution of text lengths, processing times, or quality scores across different sources.

**Binning Algorithm**:

```python
def create_ridge_plot_data(metrics_data, metric_name='text_lengths'):
    """
    Create ridge plot data with proper binning.

    Args:
        metrics_data: List of metric dictionaries
        metric_name: Name of the metric to plot

    Returns:
        Dictionary with source names and their distributions
    """
    ridge_data = {}

    for source in get_unique_sources(metrics_data):
        source_metrics = filter_by_source(metrics_data, source)
        values = []

        for metric in source_metrics:
            values.extend(metric.get(metric_name, []))

        if not values:
            continue

        # Create histogram bins
        hist, bin_edges = np.histogram(values, bins=50, density=True)

        # Smooth using kernel density estimation
        kde = gaussian_kde(values)
        x_range = np.linspace(min(values), max(values), 200)
        density = kde(x_range)

        ridge_data[source] = {
            'x': x_range.tolist(),
            'y': density.tolist(),
            'mean': np.mean(values),
            'median': np.median(values),
            'std': np.std(values)
        }

    return ridge_data
```

**JavaScript Rendering**:

```javascript
function renderRidgePlot(ridgeData, containerId) {
    const sources = Object.keys(ridgeData);
    const container = document.getElementById(containerId);

    // Create layered ridge plot
    sources.forEach((source, index) => {
        const layer = document.createElement('div');
        layer.className = 'ridge-plot-layer';
        layer.style.marginTop = `${index * -20}px`; // Overlap layers

        // Create mini area chart for this source
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ridgeData[source].x,
                datasets: [{
                    label: source,
                    data: ridgeData[source].y,
                    fill: true,
                    backgroundColor: `${SOURCE_COLORS[source]}40`,
                    borderColor: SOURCE_COLORS[source],
                    borderWidth: 2,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { display: index === sources.length - 1 }, // Only show x-axis on bottom layer
                    y: { display: false }
                },
                plugins: {
                    legend: { display: true, position: 'left' }
                }
            }
        });

        container.appendChild(layer);
    });
}
```

### Bullet Chart Technical Details

**Data Format**:

```javascript
const bulletChartData = {
    sources: ['Wikipedia', 'BBC', 'HuggingFace', 'Språkbanken'],
    data: [
        {
            source: 'Wikipedia',
            actual: 63.6,        // Quality pass rate
            target: 70.0,        // Target quality
            ranges: [50, 80, 100] // Poor, Acceptable, Excellent
        },
        {
            source: 'BBC',
            actual: 85.3,
            target: 80.0,
            ranges: [50, 80, 100]
        }
    ]
};
```

**Implementation Using Chart.js**:

```javascript
function renderBulletChart(bulletData, canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Transform bullet data into horizontal bar chart with background ranges
    const datasets = [
        {
            label: 'Excellent',
            data: bulletData.data.map(d => d.ranges[2]),
            backgroundColor: '#d1f4d1',
            barPercentage: 1.0,
            categoryPercentage: 1.0
        },
        {
            label: 'Good',
            data: bulletData.data.map(d => d.ranges[1]),
            backgroundColor: '#fff4cc',
            barPercentage: 1.0,
            categoryPercentage: 1.0
        },
        {
            label: 'Poor',
            data: bulletData.data.map(d => d.ranges[0]),
            backgroundColor: '#f4cccc',
            barPercentage: 1.0,
            categoryPercentage: 1.0
        },
        {
            label: 'Performance Score',
            data: bulletData.data.map(d => d.actual),
            backgroundColor: '#0176D3',
            barThickness: 20,
            order: 0 // Render on top
        }
    ];

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bulletData.sources,
            datasets: datasets
        },
        options: {
            indexAxis: 'y', // Horizontal
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    filter: (item) => ['Performance Score', 'Excellent', 'Good'].includes(item.text)
                }
            },
            scales: {
                x: {
                    stacked: true,
                    max: 100
                },
                y: {
                    stacked: false
                }
            }
        }
    });
}
```

### Dark Mode CSS Architecture

**CSS Custom Properties Strategy**:

```css
:root {
    /* Light mode (default) */
    --bg-primary: #FFFFFF;
    --bg-secondary: #F4F4F4;
    --text-primary: #080707;
    --text-secondary: #333333;
    --border-color: #EBEBEB;
    --card-bg: #FFFFFF;
    --chart-grid: #E5E7EB;
}

[data-theme="dark"] {
    /* Dark mode overrides */
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #f5f5f5;
    --text-secondary: #d4d4d4;
    --border-color: #404040;
    --card-bg: #252525;
    --chart-grid: #404040;

    /* Chart colors adjusted for dark backgrounds */
    --wikipedia: #60a5fa;
    --bbc: #f87171;
    --huggingface: #34d399;
    --sprakbanken: #fbbf24;
}
```

**JavaScript Theme Toggle**:

```javascript
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('dashboard-theme') || 'light';
        this.applyTheme();
        this.setupToggle();
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        this.updateChartColors();
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('dashboard-theme', this.theme);
        this.applyTheme();
    }

    updateChartColors() {
        // Update all Chart.js instances with new colors
        Chart.defaults.color = getComputedStyle(document.documentElement)
            .getPropertyValue('--text-primary');
        Chart.defaults.borderColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--chart-grid');

        // Redraw all charts
        Chart.instances.forEach(chart => chart.update());
    }

    setupToggle() {
        const toggle = document.getElementById('theme-toggle');
        toggle.addEventListener('click', () => this.toggleTheme());

        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'D') {
                this.toggleTheme();
            }
        });
    }
}

// Initialize on page load
const themeManager = new ThemeManager();
```

### Export Functionality Architecture

**Export Formats Support**:

```javascript
class ChartExporter {
    constructor() {
        this.supportedFormats = ['png', 'pdf', 'svg', 'csv'];
    }

    exportChart(chartId, format = 'png') {
        const chart = Chart.getChart(chartId);

        switch (format) {
            case 'png':
                return this.exportPNG(chart);
            case 'pdf':
                return this.exportPDF(chart);
            case 'csv':
                return this.exportCSV(chart);
            default:
                throw new Error(`Unsupported format: ${format}`);
        }
    }

    exportPNG(chart) {
        // Get high-resolution image
        const url = chart.toBase64Image('image/png', 2.0); // 2x resolution

        // Create download link
        const link = document.createElement('a');
        link.download = `${chart.canvas.id}_${new Date().toISOString()}.png`;
        link.href = url;
        link.click();
    }

    exportPDF(chart) {
        // Use jsPDF library
        const pdf = new jsPDF('landscape');
        const imgData = chart.toBase64Image();

        pdf.addImage(imgData, 'PNG', 10, 10, 280, 150);
        pdf.save(`${chart.canvas.id}_${new Date().toISOString()}.pdf`);
    }

    exportCSV(chart) {
        // Extract data from chart
        const labels = chart.data.labels;
        const datasets = chart.data.datasets;

        // Build CSV
        let csv = 'Label,' + datasets.map(ds => ds.label).join(',') + '\n';

        labels.forEach((label, index) => {
            const row = [label];
            datasets.forEach(ds => {
                row.push(ds.data[index]);
            });
            csv += row.join(',') + '\n';
        });

        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.download = `${chart.canvas.id}_data.csv`;
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);
    }
}

const exporter = new ChartExporter();

// Add export buttons to all charts
function addExportButtons() {
    document.querySelectorAll('canvas').forEach(canvas => {
        const container = canvas.parentElement;
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'chart-export-buttons';

        ['PNG', 'PDF', 'CSV'].forEach(format => {
            const button = document.createElement('button');
            button.textContent = `Export ${format}`;
            button.onclick = () => exporter.exportChart(canvas.id, format.toLowerCase());
            buttonGroup.appendChild(button);
        });

        container.insertBefore(buttonGroup, canvas);
    });
}
```

### Filter State Management

**State Management Pattern**:

```javascript
class DashboardFilterState {
    constructor() {
        this.filters = {
            sources: [],
            pipelineTypes: [],
            dateRange: { start: null, end: null },
            successRateRange: { min: 0, max: 100 },
            qualityThreshold: 0,
            recordVolumeRange: { min: 0, max: Infinity }
        };

        this.listeners = [];
    }

    updateFilter(filterName, value) {
        this.filters[filterName] = value;
        this.notifyListeners();
    }

    applyFilters(data) {
        let filtered = data;

        // Apply source filter
        if (this.filters.sources.length > 0) {
            filtered = filtered.filter(m =>
                this.filters.sources.includes(m.source)
            );
        }

        // Apply pipeline type filter
        if (this.filters.pipelineTypes.length > 0) {
            filtered = filtered.filter(m =>
                this.filters.pipelineTypes.includes(m.pipeline_type)
            );
        }

        // Apply date range filter
        if (this.filters.dateRange.start && this.filters.dateRange.end) {
            filtered = filtered.filter(m => {
                const timestamp = new Date(m.timestamp);
                return timestamp >= this.filters.dateRange.start &&
                       timestamp <= this.filters.dateRange.end;
            });
        }

        // Apply success rate filter
        filtered = filtered.filter(m => {
            const rate = m.success_rate * 100;
            return rate >= this.filters.successRateRange.min &&
                   rate <= this.filters.successRateRange.max;
        });

        // Apply quality threshold
        filtered = filtered.filter(m =>
            m.quality_pass_rate * 100 >= this.filters.qualityThreshold
        );

        // Apply record volume filter
        filtered = filtered.filter(m =>
            m.records_written >= this.filters.recordVolumeRange.min &&
            m.records_written <= this.filters.recordVolumeRange.max
        );

        return filtered;
    }

    subscribe(callback) {
        this.listeners.push(callback);
    }

    notifyListeners() {
        this.listeners.forEach(callback => callback(this.filters));
    }

    reset() {
        this.filters = {
            sources: [],
            pipelineTypes: [],
            dateRange: { start: null, end: null },
            successRateRange: { min: 0, max: 100 },
            qualityThreshold: 0,
            recordVolumeRange: { min: 0, max: Infinity }
        };
        this.notifyListeners();
    }
}

// Usage
const filterState = new DashboardFilterState();

filterState.subscribe((filters) => {
    // Reload dashboard with filtered data
    const filteredData = filterState.applyFilters(allMetricsData);
    updateAllCharts(filteredData);
});
```

### Comparison Mode Implementation

**Comparison Engine**:

```javascript
class RunComparator {
    constructor(metricsData) {
        this.allRuns = metricsData.metrics;
    }

    compareRuns(runIds) {
        const runs = runIds.map(id =>
            this.allRuns.find(r => r.run_id === id)
        );

        return {
            runs: runs,
            deltas: this.calculateDeltas(runs),
            summary: this.generateSummary(runs)
        };
    }

    calculateDeltas(runs) {
        if (runs.length < 2) return null;

        const baseline = runs[0];
        const deltas = [];

        for (let i = 1; i < runs.length; i++) {
            const current = runs[i];

            deltas.push({
                run_id: current.run_id,
                records_delta: {
                    absolute: current.records_written - baseline.records_written,
                    percentage: ((current.records_written - baseline.records_written) / baseline.records_written * 100)
                },
                success_rate_delta: {
                    absolute: current.success_rate - baseline.success_rate,
                    percentage: ((current.success_rate - baseline.success_rate) / baseline.success_rate * 100)
                },
                quality_delta: {
                    absolute: current.quality_pass_rate - baseline.quality_pass_rate,
                    percentage: ((current.quality_pass_rate - baseline.quality_pass_rate) / baseline.quality_pass_rate * 100)
                }
            });
        }

        return deltas;
    }

    generateSummary(runs) {
        return {
            totalRuns: runs.length,
            dateRange: {
                start: new Date(Math.min(...runs.map(r => new Date(r.timestamp)))),
                end: new Date(Math.max(...runs.map(r => new Date(r.timestamp))))
            },
            improvements: this.identifyImprovements(runs),
            degradations: this.identifyDegradations(runs)
        };
    }

    identifyImprovements(runs) {
        const deltas = this.calculateDeltas(runs);
        return deltas?.filter(d =>
            d.quality_delta.absolute > 0 ||
            d.success_rate_delta.absolute > 0
        ) || [];
    }

    identifyDegradations(runs) {
        const deltas = this.calculateDeltas(runs);
        return deltas?.filter(d =>
            d.quality_delta.absolute < 0 ||
            d.success_rate_delta.absolute < 0
        ) || [];
    }
}
```

---

## Related Documentation

- [Dashboard User Guide](../guides/dashboard-user-guide.md) - Interpreting dashboard metrics
- [Dashboard Advanced Features](../guides/dashboard-advanced-features.md) - Detailed feature documentation
- [Dashboard Configuration Guide](../guides/dashboard-configuration.md) - Customization options
- [Metrics Reference](metrics.md) - Complete metrics API
- [Filter Reference](filters.md) - Understanding quality filters
- [Deployment Guide](../operations/deployment.md) - Deployment procedures

---

**Maintainers**: Somali NLP Contributors
