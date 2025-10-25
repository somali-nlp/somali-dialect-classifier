# Data Visualization Quick Reference Card

**Print this page and keep it handy during implementation**

---

## Color Palette (Paul Tol's Bright Scheme)

```javascript
const SourceColors = {
  'Wikipedia-Somali':   '#4477AA',  // Blue
  'BBC-Somali':         '#EE6677',  // Red
  'HuggingFace-MC4':    '#228833',  // Green
  'Språkbanken':        '#CCBB44',  // Yellow
  'default':            '#BBBBBB'   // Grey
};
```

---

## Data Structure (dashboard_data.json)

```json
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

  "pipelineFunnel": {
    "stages": [
      { "name": "Discovered", "count": 10687, "conversionToNext": 100 }
    ]
  },

  "performanceMetrics": {
    "totalRecords": { "value": 13735, "status": "good", "trend": [...] }
  }
}
```

---

## Chart Template

```javascript
function createMyChart(canvasId, data) {
  const ctx = document.getElementById(canvasId).getContext('2d');

  return new Chart(ctx, {
    type: 'bar',  // or 'line', 'radar', etc.
    data: {
      labels: [...],
      datasets: [{
        label: 'Dataset Label',
        data: [...],
        backgroundColor: getColorWithAlpha(color, 0.85),
        borderColor: color,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,

      plugins: {
        title: {
          display: true,
          text: 'Chart Title',
          font: { size: 18, weight: 600 }
        },
        tooltip: { enabled: true },
        legend: { display: true, position: 'top' }
      },

      scales: {
        x: { title: { display: true, text: 'X Axis' } },
        y: { title: { display: true, text: 'Y Axis' } }
      }
    }
  });
}
```

---

## Utility Functions

```javascript
// Number formatting
function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
}

// Color with opacity
function getColorWithAlpha(color, alpha = 1.0) {
  const hex = color.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Screen reader announcement
function announceToScreenReader(message) {
  const region = document.getElementById('sr-live-region');
  if (region) {
    region.textContent = message;
    setTimeout(() => region.textContent = '', 1000);
  }
}
```

---

## Current Data Stats

```
Total Records:       13,735
Sources:             4
Success Rate:        82.7%
Pipeline Runs:       12
Collection Period:   October 2025

Source Breakdown:
  Wikipedia-Somali:  9,623 (70.1%)
  Språkbanken:       4,015 (29.2%)
  BBC-Somali:           49 (0.4%)
  HuggingFace-MC4:      48 (0.3%)
```

---

## HTML Canvas Elements

```html
<!-- Source Contribution -->
<canvas id="sourceContributionChart"></canvas>

<!-- Quality Radar -->
<canvas id="qualityMetricsChart"></canvas>

<!-- Pipeline Funnel -->
<canvas id="pipelineFunnelChart"></canvas>

<!-- Processing Timeline -->
<canvas id="processingTimelineChart"></canvas>

<!-- Screen Reader Live Region -->
<div id="sr-live-region" class="sr-only" aria-live="polite"></div>
```

---

## CSS Essentials

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

.chart-canvas {
  position: relative;
  height: 400px;  /* Desktop */
}

@media (max-width: 768px) {
  .chart-canvas { height: 300px; }  /* Mobile */
}

.chart-section {
  background: white;
  padding: 32px;
  border-radius: 12px;
  margin-bottom: 32px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
```

---

## Chart.js CDN Links

```html
<!-- Chart.js Core -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<!-- Date Adapter (for timeline) -->
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>

<!-- Zoom Plugin (for timeline) -->
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
```

---

## Accessibility Checklist

- [ ] ARIA label on canvas
- [ ] Keyboard focus indicators (3px outline)
- [ ] Screen reader announcements
- [ ] Color contrast ≥ 4.5:1
- [ ] Tooltip on hover AND keyboard
- [ ] Alternative text provided
- [ ] No info by color alone

---

## Common Chart Options

```javascript
// Horizontal bars
indexAxis: 'y'

// Remove legend
legend: { display: false }

// Stacked bars/areas
scales: {
  x: { stacked: true },
  y: { stacked: true }
}

// Time-series axis
scales: {
  x: {
    type: 'time',
    time: { unit: 'minute' }
  }
}

// Rounded bars
borderRadius: 8,
borderSkipped: false

// Area fill (line chart)
fill: true,
tension: 0.3
```

---

## Status Colors

```javascript
const StatusColors = {
  good:     '#10B981',  // Green
  warning:  '#F59E0B',  // Orange
  critical: '#EF4444'   // Red
};

function getStatus(value, target) {
  const percent = (value / target) * 100;
  if (percent >= 90) return 'good';
  if (percent >= 50) return 'warning';
  return 'critical';
}
```

---

## Typography Scale

```
Chart Titles:     18px, weight: 600
Axis Labels:      13px, weight: 500
Axis Ticks:       11px, weight: 400
Tooltips:         14px (header), 13px (body)
Data Labels:      12px, weight: 600
Legend:           12px, weight: 400
```

---

## Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 767px) {
  --chart-height: 280px;
  --font-size: 12px;
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  --chart-height: 350px;
  --font-size: 14px;
}

/* Desktop */
@media (min-width: 1024px) {
  --chart-height: 400px;
  --font-size: 16px;
}
```

---

## Data Loading Pattern

```javascript
async function loadDashboard() {
  try {
    const response = await fetch('_site/data/dashboard_data.json');
    const data = await response.json();

    // Create charts
    createSourceChart('chart1', data.sourceContribution);
    createRadarChart('chart2', data.qualityMetrics);
    // ... etc

    console.log('✅ Dashboard loaded');
  } catch (error) {
    console.error('❌ Error:', error);
    // Show error message to user
  }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
```

---

## Testing Commands

```bash
# Generate data
python scripts/transform_dashboard_data.py

# Start local server
cd dashboard
python -m http.server 8000

# Open browser
open http://localhost:8000/index.html

# Check for errors
# Open DevTools Console (F12)
```

---

## File Paths Reference

```
Configuration:
  /dashboard/chart-config-enhanced.js
  /dashboard/enhanced-charts.js
  /dashboard/enhanced-charts.css

Data:
  /data/metrics/*_processing.json        (input)
  /_site/data/dashboard_data.json        (output)

Scripts:
  /scripts/transform_dashboard_data.py

Documentation:
  /dashboard/VISUALIZATION_SPECIFICATIONS.md  (full specs)
  /dashboard/IMPLEMENTATION_QUICKSTART.md     (fast start)
  /dashboard/VISUAL_MOCKUPS.md                (design ref)
  /dashboard/README_VISUALIZATIONS.md         (overview)
  /dashboard/QUICK_REFERENCE.md               (this file)
```

---

## Keyboard Shortcuts (for charts)

```
Tab           - Focus next chart
Shift+Tab     - Focus previous chart
Arrow Keys    - Navigate data points
Enter         - Select/activate
Escape        - Close tooltip
R             - Reset zoom (timeline)
Ctrl+Scroll   - Zoom in/out (timeline)
```

---

## Debugging Checklist

Chart not rendering?
1. [ ] Check console for errors
2. [ ] Verify canvas ID matches JavaScript
3. [ ] Ensure Chart.js loaded
4. [ ] Check data structure

Wrong colors?
1. [ ] Verify SourceColors mapping
2. [ ] Check getColorWithAlpha() exists
3. [ ] Inspect computed styles

Mobile broken?
1. [ ] Add viewport meta tag
2. [ ] Check CSS media queries
3. [ ] Test with DevTools emulation

Accessibility issues?
1. [ ] Run axe DevTools
2. [ ] Test keyboard navigation
3. [ ] Test screen reader
4. [ ] Check ARIA labels

---

## Key Metrics Targets

```
Total Records:     15,000  (current: 13,735 = 91.6%)
Success Rate:      95%     (current: 82.7% = 87.1%)
Avg Text Length:   4,000   (current: 2,979 = 74.5%)
Throughput:        500/s   (current: 259   = 51.8%)
Dedup Rate:        < 5%    (current: 0%    = 100%)
```

---

## Chart Type Decision Matrix

| Data Type | Best Chart | Alternative |
|-----------|------------|-------------|
| Comparison (few items) | Bar | Lollipop |
| Comparison (many items) | Horizontal Bar | Dot Plot |
| Part-to-whole | Bar + % | Treemap |
| Distribution | Histogram | Violin Plot |
| Correlation | Scatter | Line |
| Time-series | Line/Area | Column |
| Multi-dimensional | Radar | Parallel Coords |
| Flow/Process | Funnel/Sankey | Stacked Bar |

---

## Performance Tips

```javascript
// Lazy load charts
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      createChart(entry.target);
      observer.unobserve(entry.target);
    }
  });
});

// Debounce resize
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    charts.forEach(chart => chart.resize());
  }, 250);
});

// Decimation for large datasets
datasets: [{
  parsing: false,
  normalized: true,
  data: largeDataArray,
  // ... other options
}]
```

---

## Quick Links

- **Chart.js Docs:** https://www.chartjs.org/docs/latest/
- **Color Oracle:** https://colororacle.org/
- **WCAG Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **DataViz Project:** https://datavizproject.com/
- **axe DevTools:** https://www.deque.com/axe/devtools/

---

**Print this page and keep it next to your keyboard during implementation!**

Last Updated: October 25, 2025
