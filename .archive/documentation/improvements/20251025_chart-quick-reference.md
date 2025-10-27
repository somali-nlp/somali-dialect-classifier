# Pipeline Performance Charts - Quick Reference

## Four Charts, Four Questions

### 1. 📊 Performance Bullet Graph
**"How close are we to optimal performance?"**

```javascript
createPerformanceBulletChart(canvas, metrics, {
    title: 'Performance Efficiency Score by Source'
});
```

**Shows:**
- Composite score (60% speed + 40% quality)
- Target line at 80%
- Color zones (poor/satisfactory/good/excellent)

**Use When:** You need to compare performance against targets

---

### 2. 🎯 Quality vs Speed Scatter
**"Which sources are fast AND reliable?"**

```javascript
createQualityVsSpeedScatterChart(canvas, metrics, {
    title: 'Quality vs. Speed Trade-off Analysis'
});
```

**Shows:**
- X: Processing speed (log scale)
- Y: Success rate (%)
- Bubble size: Data volume
- Quadrants: Optimal, Fast-but-unreliable, etc.

**Use When:** You need to identify trade-offs and optimization opportunities

---

### 3. ⏱️ Resource Gauge Cluster
**"Are we using resources efficiently?"**

```javascript
createResourceGaugeCluster(canvas, metrics, {
    title: 'System Resource Efficiency'
});
```

**Shows:**
- 4 gauges: Speed, Success, Health, Quality
- Color coding: Green/Yellow/Red
- Instant health status

**Use When:** You need at-a-glance system health monitoring

---

### 4. 📈 Throughput Stream Graph
**"How did collection evolve over time?"**

```javascript
createPipelineThroughputStreamChart(canvas, metrics, {
    title: 'Cumulative Data Collection Timeline'
});
```

**Shows:**
- Cumulative records over time
- Contribution by source (stacked areas)
- Collection phases and patterns

**Use When:** You need to understand temporal patterns

---

## Data Format Required

```json
{
  "metrics": [
    {
      "source": "Wikipedia-Somali",
      "timestamp": "2025-10-21T11:36:30Z",
      "duration_seconds": 17.09,
      "records_written": 9623,
      "success_rate": 1.0,
      "deduplication_rate": 0.0,
      "performance": {
        "urls_per_second": 562.96,
        "records_per_minute": 33777.83
      },
      "quality": {
        "min": 10,
        "max": 122020,
        "mean": 4415.74,
        "median": 1917.0
      }
    }
  ]
}
```

---

## Quick Integration

### Step 1: Include Scripts
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1"></script>
<script src="chart-config-enhanced.js"></script>
<script src="pipeline-performance-charts.js"></script>
```

### Step 2: Create Canvas
```html
<div class="chart-container" style="height: 400px;">
    <canvas id="myChart"></canvas>
</div>
```

### Step 3: Initialize Chart
```javascript
fetch('data/all_metrics.json')
    .then(res => res.json())
    .then(data => {
        const canvas = document.getElementById('myChart');
        createPerformanceBulletChart(canvas, data.metrics);
    });
```

---

## Customization Options

### All Charts Support

```javascript
createChartFunction(canvas, metrics, {
    title: 'Custom Title',
    subtitle: 'Optional subtitle',
    showLegend: true,
    height: 500
});
```

### Chart-Specific Options

**Bullet Graph:**
```javascript
{
    targetValue: 80,           // Custom target %
    showRanges: true,          // Show color zones
    rangeColors: [...],        // Custom colors
}
```

**Scatter Plot:**
```javascript
{
    logScale: true,            // Logarithmic X-axis
    showQuadrants: true,       // Median dividing lines
    bubbleSizeMultiplier: 8    // Adjust bubble sizes
}
```

**Gauge Cluster:**
```javascript
{
    thresholds: {
        excellent: 80,
        acceptable: 60,
        poor: 0
    },
    colors: {
        excellent: '#34D399',
        acceptable: '#FBBF24',
        poor: '#EF4444'
    }
}
```

**Stream Graph:**
```javascript
{
    stacked: false,            // Cumulative vs stacked
    smoothing: 0.4,            // Curve tension
    showPoints: false,         // Show data points
    enableZoom: true           // Zoom/pan
}
```

---

## Color Palette Reference

### Source Colors (Consistent)
```javascript
const SourceColors = {
    'Wikipedia-Somali': '#4477AA',      // Blue
    'BBC-Somali': '#EE6677',            // Red
    'HuggingFace-MC4': '#228833',       // Green
    'Sprakbanken': '#CCBB44'            // Yellow
};
```

### Performance Colors
```javascript
const PerformanceColors = {
    excellent: '#34D399',  // Green (80-100%)
    good: '#FBBF24',       // Yellow (60-80%)
    poor: '#EF4444'        // Red (<60%)
};
```

---

## Troubleshooting

### Chart Not Rendering?

1. **Check console** for errors
2. **Verify data format** matches expected structure
3. **Ensure canvas exists** in DOM before initialization
4. **Check dependencies** are loaded in correct order

### Performance Issues?

1. **Reduce data points** if >1000 items
2. **Disable animations** for large datasets
3. **Use decimation** plugin
4. **Lazy load** off-screen charts

### Accessibility Warnings?

1. **Add aria-label** to canvas
2. **Ensure color contrast** meets WCAG AA
3. **Test with keyboard** navigation
4. **Verify screen reader** announcements

---

## Examples

### Minimal Example
```javascript
// Simplest possible usage
const canvas = document.getElementById('chart');
const metrics = await fetch('data.json').then(r => r.json());
createPerformanceBulletChart(canvas, metrics.metrics);
```

### Full Example
```javascript
// With all bells and whistles
const canvas = document.getElementById('chart');
const metrics = await loadMetrics();

const chart = createPerformanceBulletChart(canvas, metrics, {
    title: 'Q4 2025 Performance Review',
    subtitle: 'All sources compared against 80% target',
    showLegend: true,
    targetValue: 80,
    colors: {
        excellent: '#10B981',
        good: '#F59E0B',
        poor: '#DC2626'
    }
});

// Add event listeners
canvas.addEventListener('click', (e) => {
    const elements = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, false);
    if (elements.length) {
        const source = chart.data.labels[elements[0].index];
        console.log('Clicked:', source);
    }
});

// Export functionality
document.getElementById('exportBtn').addEventListener('click', () => {
    const url = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = 'performance-chart.png';
    link.href = url;
    link.click();
});
```

---

## Best Practices

### DO ✅
- Load real data from `all_metrics.json`
- Use consistent colors across dashboard
- Enable keyboard navigation
- Provide tooltips with context
- Test with screen readers
- Optimize for mobile

### DON'T ❌
- Hardcode data in JavaScript
- Mix chart types without purpose
- Ignore accessibility features
- Use red/green only (colorblind)
- Forget to handle empty data
- Block rendering with synchronous operations

---

## Common Patterns

### Pattern 1: Dashboard Grid
```html
<div class="dashboard-grid">
    <div class="chart-card"><canvas id="chart1"></canvas></div>
    <div class="chart-card"><canvas id="chart2"></canvas></div>
    <div class="chart-card full-width"><canvas id="chart3"></canvas></div>
</div>

<style>
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
    gap: 32px;
}
.full-width { grid-column: 1 / -1; }
</style>
```

### Pattern 2: Lazy Loading
```javascript
// Only load charts when visible
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const canvas = entry.target;
            createChart(canvas, metrics);
            observer.unobserve(canvas);
        }
    });
});

document.querySelectorAll('canvas').forEach(canvas => {
    observer.observe(canvas);
});
```

### Pattern 3: Responsive Resizing
```javascript
// Charts auto-resize on window resize
window.addEventListener('resize', debounce(() => {
    Chart.instances.forEach(chart => {
        chart.resize();
    });
}, 250));
```

---

## API Reference

### createPerformanceBulletChart(canvas, metrics, options)
Returns: `Chart` instance

### createQualityVsSpeedScatterChart(canvas, metrics, options)
Returns: `Chart` instance

### createResourceGaugeCluster(canvas, metrics, options)
Returns: `Chart` instance (for primary gauge)

### createPipelineThroughputStreamChart(canvas, metrics, options)
Returns: `Chart` instance

### All Functions Accept:
- `canvas` (HTMLCanvasElement): Target canvas element
- `metrics` (Array): Metrics data from all_metrics.json
- `options` (Object): Optional configuration overrides

---

## Need Help?

1. **Check the demo:** Open `pipeline-performance-demo.html`
2. **Read the spec:** See `PIPELINE_PERFORMANCE_REDESIGN.md`
3. **Inspect code:** Comments in `pipeline-performance-charts.js`
4. **Test accessibility:** Use axe DevTools browser extension

---

**Last Updated:** October 2025
**Version:** 2.0
**License:** MIT
