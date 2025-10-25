# Data Visualization Implementation Quickstart

**Project:** Somali NLP Dialect Classifier
**Phase:** Data Ingestion Visualization
**Status:** Ready for Implementation

---

## TL;DR - What to Build

You need **5 visualizations** to communicate your data ingestion pipeline's performance:

1. **Source Contribution Bar Chart** - Shows Wikipedia dominates (70% of corpus)
2. **Pipeline Funnel** - Visualizes data flow and drop-off rates
3. **Quality Metrics Radar** - Multi-dimensional source comparison
4. **Processing Timeline** - Cumulative growth over time
5. **Performance KPI Cards** - At-a-glance health metrics

**Current Status:** 13,735 records from 4 sources with 82.7% success rate

---

## Prerequisites

### Already Have ✅
- Chart.js 4.4.0 infrastructure (`chart-config-enhanced.js`, `enhanced-charts.js`)
- Colorblind-safe palette (Paul Tol's bright scheme)
- Accessibility features (keyboard nav, screen reader support)
- Mobile optimization framework

### Need to Create 📝
- Data transformation script (`transform_dashboard_data.py`)
- Individual visualization implementations
- Dashboard integration HTML

---

## Step 1: Transform Your Data (30 minutes)

Create `/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/scripts/transform_dashboard_data.py`:

```python
#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime

def create_dashboard_data():
    """Quick transformer for MVP"""

    # Source contribution (from actual data)
    source_contribution = [
        {"source": "Wikipedia-Somali", "records": 9623, "percentage": 70.1},
        {"source": "BBC-Somali", "records": 49, "percentage": 0.4},
        {"source": "HuggingFace-MC4", "records": 48, "percentage": 0.3},
        {"source": "Språkbanken", "records": 4015, "percentage": 29.2}
    ]

    # Pipeline funnel
    pipeline_funnel = {
        "stages": [
            {"name": "Items Discovered", "count": 10687, "conversionToNext": 100},
            {"name": "Items Processed", "count": 10687, "conversionToNext": 100},
            {"name": "Records Written", "count": 13735, "conversionToNext": None}
        ]
    }

    # Quality metrics (normalized 0-100)
    quality_metrics = [
        {
            "source": "Wikipedia-Somali",
            "successRate": 100,
            "textQuality": 66,
            "throughput": 95,
            "coverage": 70,
            "consistency": 100
        },
        {
            "source": "BBC-Somali",
            "successRate": 98,
            "textQuality": 74,
            "throughput": 3,
            "coverage": 0.4,
            "consistency": 100
        },
        {
            "source": "HuggingFace-MC4",
            "successRate": 96,
            "textQuality": 90,
            "throughput": 52,
            "coverage": 0.3,
            "consistency": 100
        },
        {
            "source": "Språkbanken",
            "successRate": 100,
            "textQuality": 20,
            "throughput": 100,
            "coverage": 29,
            "consistency": 100
        }
    ]

    # Performance metrics
    performance_metrics = {
        "totalRecords": {
            "value": 13735,
            "status": "good",
            "change": "+42%",
            "trend": [9623, 9672, 9720, 13687, 13735]
        },
        "successRate": {
            "value": 82.7,
            "status": "warning",
            "change": "-15.6%",
            "trend": [98, 96, 100, 98, 82.7]
        },
        "avgTextLength": {
            "value": 2979,
            "status": "warning",
            "change": "-33%",
            "trend": [4416, 4933, 5980, 132, 2979]
        }
    }

    dashboard_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "version": "1.0",
        "sourceContribution": source_contribution,
        "pipelineFunnel": pipeline_funnel,
        "qualityMetrics": quality_metrics,
        "performanceMetrics": performance_metrics
    }

    # Write to file
    output_file = Path("_site/data/dashboard_data.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"✅ Dashboard data created: {output_file}")
    print(f"   Total records: {sum(s['records'] for s in source_contribution)}")

if __name__ == '__main__':
    create_dashboard_data()
```

**Run it:**
```bash
python scripts/transform_dashboard_data.py
```

---

## Step 2: Create Visualization 1 - Source Contribution (15 minutes)

Create `/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/dashboard/visualizations/source-contribution.js`:

```javascript
/**
 * Source Contribution Horizontal Bar Chart
 */
function createSourceContributionChart(canvasId, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Sort by records (ascending for horizontal bar)
    const sorted = data.sort((a, b) => a.records - b.records);

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(s => s.source),
            datasets: [{
                label: 'Total Records',
                data: sorted.map(s => s.records),
                backgroundColor: sorted.map(s =>
                    getColorWithAlpha(SourceColors[s.source], 0.85)
                ),
                borderColor: sorted.map(s => SourceColors[s.source]),
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal bars
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                title: {
                    display: true,
                    text: 'Data Source Contribution',
                    font: { size: 18, weight: 600 }
                },

                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const item = sorted[context.dataIndex];
                            return [
                                `Records: ${formatNumber(item.records)}`,
                                `Percentage: ${item.percentage}%`
                            ];
                        }
                    }
                },

                legend: { display: false }
            },

            scales: {
                x: {
                    title: { display: true, text: 'Number of Records' },
                    ticks: { callback: (v) => formatNumber(v) }
                }
            }
        }
    });
}
```

---

## Step 3: Create Dashboard HTML (20 minutes)

Create `/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/dashboard/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Ingestion Dashboard | Somali Dialect Classifier</title>

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

    <!-- Enhanced Config -->
    <script src="chart-config-enhanced.js"></script>
    <script src="enhanced-charts.js"></script>

    <!-- Visualizations -->
    <script src="visualizations/source-contribution.js"></script>

    <link rel="stylesheet" href="enhanced-charts.css">

    <style>
        body {
            font-family: 'Inter', sans-serif;
            background: #F9FAFB;
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 24px;
        }

        .dashboard-header {
            background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
            color: white;
            padding: 48px 24px;
            text-align: center;
            margin-bottom: 40px;
        }

        .dashboard-header h1 {
            margin: 0 0 16px 0;
            font-size: 2.5rem;
        }

        .stats-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 40px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #2563EB;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #111827;
        }

        .stat-label {
            font-size: 0.875rem;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .chart-section {
            background: white;
            padding: 32px;
            border-radius: 12px;
            margin-bottom: 32px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .chart-section h2 {
            margin: 0 0 24px 0;
            font-size: 1.5rem;
            color: #111827;
        }

        .chart-canvas {
            position: relative;
            height: 400px;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="dashboard-header">
        <h1>Data Ingestion Dashboard</h1>
        <p>Somali NLP Dialect Classifier Project</p>
    </div>

    <!-- Main Container -->
    <div class="container">

        <!-- Summary Stats -->
        <div class="stats-summary">
            <div class="stat-card">
                <div class="stat-label">Total Records</div>
                <div class="stat-value" id="stat-total">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Data Sources</div>
                <div class="stat-value">4</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value" id="stat-success">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pipeline Runs</div>
                <div class="stat-value">12</div>
            </div>
        </div>

        <!-- Visualization 1: Source Contribution -->
        <section class="chart-section">
            <h2>Source Contribution Analysis</h2>
            <div class="chart-canvas">
                <canvas id="sourceContributionChart"></canvas>
            </div>
        </section>

        <!-- Visualization 2: Quality Metrics -->
        <section class="chart-section">
            <h2>Quality Metrics Comparison</h2>
            <div class="chart-canvas">
                <canvas id="qualityMetricsChart"></canvas>
            </div>
        </section>

        <!-- Add more visualizations as needed -->

    </div>

    <!-- Load and Render -->
    <script>
        async function loadDashboard() {
            try {
                // Fetch dashboard data
                const response = await fetch('_site/data/dashboard_data.json');
                const data = await response.json();

                // Update summary stats
                const totalRecords = data.sourceContribution.reduce((sum, s) => sum + s.records, 0);
                document.getElementById('stat-total').textContent = formatNumber(totalRecords);
                document.getElementById('stat-success').textContent =
                    data.performanceMetrics.successRate.value + '%';

                // Create charts
                createSourceContributionChart('sourceContributionChart', data.sourceContribution);

                // Create quality radar
                createEnhancedRadarChart(
                    document.getElementById('qualityMetricsChart'),
                    data.qualityMetrics.map(m => ({
                        source: m.source,
                        records_written: 0,
                        successRate: m.successRate,
                        avgTextLength: m.textQuality,
                        throughput: m.throughput,
                        coverage: m.coverage
                    })),
                    { title: 'Source Quality Comparison' }
                );

                console.log('✅ Dashboard loaded successfully');

            } catch (error) {
                console.error('❌ Error loading dashboard:', error);
            }
        }

        // Load on DOM ready
        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
```

---

## Step 4: Test It (10 minutes)

```bash
# 1. Generate data
python scripts/transform_dashboard_data.py

# 2. Start local server
cd dashboard
python -m http.server 8000

# 3. Open browser
open http://localhost:8000/index.html
```

**What to check:**
- ✅ Charts render without errors
- ✅ Source contribution shows Wikipedia at 70%
- ✅ Tooltips display on hover
- ✅ Colors are colorblind-safe
- ✅ Works on mobile (resize browser)

---

## Step 5: Implement Remaining Visualizations (2-3 hours)

**Priority Order:**

1. ✅ Source Contribution (DONE in Step 2)
2. **Quality Metrics Radar** (use existing `createEnhancedRadarChart`)
3. **Performance KPI Cards** (custom implementation)
4. **Pipeline Funnel** (use stacked bar chart)
5. **Processing Timeline** (use time-series line chart)

**For each visualization:**
1. Copy configuration from `VISUALIZATION_SPECIFICATIONS.md`
2. Create function in `dashboard/visualizations/{name}.js`
3. Add canvas element to `index.html`
4. Call creation function in `loadDashboard()`

---

## Common Issues & Solutions

### Issue: "SourceColors is not defined"
**Solution:** Import `chart-config-enhanced.js` before other scripts

### Issue: Charts not rendering
**Solution:** Check browser console; ensure data structure matches expected format

### Issue: Mobile layout broken
**Solution:** Add viewport meta tag and test with Chrome DevTools device emulation

### Issue: Tooltips not showing
**Solution:** Verify `tooltip.enabled: true` in chart options

---

## Next Steps After MVP

1. **Add Interactivity**
   - Connect filter events between charts
   - Add CSV export buttons
   - Implement zoom/pan on timeline

2. **Enhance Accessibility**
   - Run axe DevTools audit
   - Test with screen reader (NVDA/VoiceOver)
   - Verify keyboard navigation

3. **Optimize Performance**
   - Implement lazy loading for charts
   - Debounce zoom/pan events
   - Add loading spinners

4. **Integrate with Main Dashboard**
   - Embed into existing Flask app
   - Add auto-refresh on new data
   - Set up analytics tracking

---

## Resources

- **Full Specifications:** `/dashboard/VISUALIZATION_SPECIFICATIONS.md`
- **Chart.js Docs:** https://www.chartjs.org/docs/latest/
- **Color Palette Reference:** Paul Tol's schemes (https://personal.sron.nl/~pault/)
- **Accessibility Testing:** axe DevTools browser extension
- **Example Implementation:** `/dashboard/example-integration.html`

---

## Estimated Timeline

| Task | Time | Status |
|------|------|--------|
| Data transformation script | 30 min | ⏳ To Do |
| Source contribution chart | 15 min | ⏳ To Do |
| Quality radar chart | 20 min | ⏳ To Do |
| Performance KPI cards | 45 min | ⏳ To Do |
| Pipeline funnel | 30 min | ⏳ To Do |
| Processing timeline | 40 min | ⏳ To Do |
| Dashboard HTML integration | 30 min | ⏳ To Do |
| Testing & debugging | 1 hour | ⏳ To Do |
| **TOTAL** | **~4 hours** | |

---

## Quick Reference: Data Structure

```javascript
// What your dashboard_data.json should look like
{
  "sourceContribution": [
    { "source": "Wikipedia-Somali", "records": 9623, "percentage": 70.1 }
  ],

  "qualityMetrics": [
    {
      "source": "Wikipedia-Somali",
      "successRate": 100,
      "textQuality": 66,
      "throughput": 95,
      "coverage": 70,
      "consistency": 100
    }
  ],

  "performanceMetrics": {
    "totalRecords": { "value": 13735, "status": "good", "trend": [...] }
  }
}
```

---

**Questions?** Refer to the full specification document for detailed configurations, rationale, and advanced features.

**Ready to Start?** Begin with Step 1 - transform your data!
