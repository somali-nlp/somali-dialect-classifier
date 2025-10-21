# Enhanced Charts - Quick Reference Guide

## One-Page Cheat Sheet for Implementation

---

## 📦 Installation (1 minute)

```html
<!-- Add to your HTML <head> -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<script src="dashboard/chart-config-enhanced.js"></script>
<script src="dashboard/enhanced-charts.js"></script>
<link rel="stylesheet" href="dashboard/enhanced-charts.css">
```

---

## 🎨 Color Palette

### Source Colors (Colorblind-Safe)
```javascript
'Wikipedia-Somali'  → '#4477AA' (Blue)
'BBC-Somali'        → '#EE6677' (Red)
'HuggingFace-MC4'   → '#228833' (Green)
'Sprakbanken'       → '#CCBB44' (Yellow)
```

### Access Palettes
```javascript
ColorPalettes.bright         // 7 colors
ColorPalettes.vibrant        // 7 colors
ColorPalettes.highContrast   // 3 colors
ColorPalettes.sequential.blue // Gradient
```

---

## 📊 Chart Types - Copy & Paste Ready

### 1. Time Series (Line Chart)
```javascript
const chart = createEnhancedTimeSeriesChart(canvas, metrics, {
    title: 'Records Over Time',
    fillArea: true
});
```

### 2. Bar Chart (Source Comparison)
```javascript
const chart = createEnhancedSourceComparisonChart(canvas, metrics, {
    title: 'Source Contribution'
});
```

### 3. Funnel Chart (Pipeline Stages)
```javascript
const chart = createEnhancedFunnelChart(canvas, metrics, {
    title: 'Pipeline Funnel'
});
```

### 4. Radar Chart (Performance)
```javascript
const chart = createEnhancedRadarChart(canvas, metrics, {
    title: 'Performance Comparison'
});
```

### 5. Histogram (Distribution)
```javascript
const chart = createEnhancedHistogramChart(canvas, metrics, {
    title: 'Length Distribution',
    logScale: false
});
```

### 6. Heatmap (Quality Metrics)
```javascript
const chart = createEnhancedHeatmapChart(canvas, metrics, {
    title: 'Quality by Source'
});
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Move to next chart |
| `→` / `↑` | Next data point |
| `←` / `↓` | Previous data point |
| `Home` | First data point |
| `End` | Last data point |
| `R` | Reset zoom |
| `Escape` | Clear tooltip |

---

## 🎯 Essential Features

### Add Zoom Reset
```javascript
setupZoomReset(chart, canvas);
```

### Add CSV Export
```javascript
setupDataExport(chart, canvas, 'filename');
```

### Add Keyboard Navigation
```javascript
setupKeyboardNavigation(chart, canvas);
```

### Add Data Table
```javascript
generateDataTable(chart, 'containerId');
```

### Enable Lazy Loading
```javascript
setupLazyLoading(canvas, () => {
    const chart = createEnhancedTimeSeriesChart(canvas, metrics);
});
```

---

## 📱 Responsive Breakpoints

```javascript
Mobile:     < 768px  → 300px height, 11px font
Tablet:     768-1024px → 350px height, 12px font
Desktop:    > 1024px → 400px height, 13px font
```

---

## ♿ Accessibility Checklist

- [ ] Canvas has `aria-label`
- [ ] Container has `role="region"`
- [ ] Keyboard navigation enabled
- [ ] Focus indicators visible
- [ ] Screen reader announcements work
- [ ] Data table alternative provided
- [ ] Colors meet WCAG AA contrast

### HTML Template
```html
<div class="chart-container" role="region" aria-labelledby="chart-title">
    <h3 id="chart-title">Chart Title</h3>
    <div class="chart-canvas">
        <canvas id="myChart" aria-label="Chart description"></canvas>
    </div>
</div>
```

---

## 🚀 Performance Tips

### Large Datasets (>1000 points)
```javascript
options: {
    plugins: {
        decimation: {
            enabled: true,
            algorithm: 'lttb',
            samples: 500
        }
    }
}
```

### Update Without Animation
```javascript
chart.update('none'); // Fast update
chart.update();       // Animated update
```

### Clean Up on Unmount
```javascript
if (chart) {
    chart.destroy();
    chart = null;
}
```

---

## 🎨 Customization Examples

### Change Tooltip Style
```javascript
tooltip: {
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    titleFont: { size: 14, weight: 600 },
    bodyFont: { size: 13 },
    padding: 12
}
```

### Custom Color Function
```javascript
function getColorWithAlpha(color, alpha = 1.0) {
    // Converts hex to rgba
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
```

### Override Chart Defaults
```javascript
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#374151';
Chart.defaults.borderColor = '#E5E7EB';
```

---

## 📊 Data Format

### Required Metrics Structure
```javascript
{
    timestamp: '2025-10-21T10:00:00Z',
    source: 'Wikipedia-Somali',
    records_written: 1000,
    success_rate: 0.95,
    deduplication_rate: 0.15,
    avg_text_length: 1500,
    urls_discovered: 500,
    urls_fetched: 450,
    urls_processed: 400,
    records_per_minute: 50,
    urls_per_second: 5
}
```

---

## 🔧 Troubleshooting Quick Fixes

### Chart Not Showing
```javascript
// Ensure canvas has height
.chart-canvas { height: 400px; }

// Check if Chart.js loaded
console.log(typeof Chart); // Should be 'function'
```

### Zoom Not Working
```javascript
// Register zoom plugin
Chart.register(ChartZoom);

// Add zoom config
options: { plugins: { zoom: ZoomConfig } }
```

### Touch Not Working on Mobile
```javascript
// Increase hit radius
elements: {
    point: { hitRadius: 20 }
}
```

---

## 📱 Mobile-Specific Code

```javascript
const isMobile = window.innerWidth < 768;

options: {
    plugins: {
        legend: {
            display: !isMobile // Hide on mobile
        }
    },
    elements: {
        point: {
            radius: isMobile ? 6 : 4,
            hitRadius: isMobile ? 20 : 10
        }
    }
}
```

---

## 🎯 Click Event Handler

```javascript
onClick: (event, activeElements) => {
    if (activeElements.length > 0) {
        const index = activeElements[0].index;
        const value = chart.data.datasets[0].data[index];

        // Dispatch custom event
        canvas.dispatchEvent(new CustomEvent('chartFilter', {
            detail: { index, value }
        }));
    }
}
```

---

## 💡 Pro Tips

1. **Always test with keyboard** - Tab through all charts
2. **Use Color Oracle** - Verify colorblind accessibility
3. **Test on real mobile devices** - Not just browser emulation
4. **Profile performance** - Use Chrome DevTools Performance tab
5. **Provide data tables** - Essential for screen reader users

---

## 📚 Documentation Links

- Full Documentation: `CHART_ENHANCEMENTS.md`
- Example Integration: `example-integration.html`
- Config Module: `chart-config-enhanced.js`
- Chart Implementations: `enhanced-charts.js`
- Styles: `enhanced-charts.css`

---

## 🆘 Quick Support

**Common Issues:**
1. Chart blank → Check canvas height
2. Zoom broken → Register ChartZoom plugin
3. Colors wrong → Use SourceColors mapping
4. Mobile laggy → Enable decimation
5. Not accessible → Check ARIA labels

**Testing Tools:**
- Lighthouse (accessibility audit)
- axe DevTools (automated checks)
- Color Oracle (colorblind simulation)
- Screen reader (NVDA/JAWS/VoiceOver)

---

## ✨ Complete Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Dashboard</title>

    <!-- Dependencies -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>

    <!-- Enhanced Charts -->
    <script src="chart-config-enhanced.js"></script>
    <script src="enhanced-charts.js"></script>
    <link rel="stylesheet" href="enhanced-charts.css">
</head>
<body>
    <div class="chart-container" role="region" aria-labelledby="chart-title">
        <h3 id="chart-title">Records Over Time</h3>
        <div class="chart-canvas">
            <canvas id="myChart" aria-label="Line chart showing records over time"></canvas>
        </div>
    </div>

    <script>
        // Sample data
        const metrics = [
            {
                timestamp: '2025-10-20T10:00:00Z',
                source: 'Wikipedia-Somali',
                records_written: 1000,
                success_rate: 0.95
            }
            // ... more data
        ];

        // Register plugins
        Chart.register(CrosshairPlugin);

        // Create chart
        const canvas = document.getElementById('myChart');
        const chart = createEnhancedTimeSeriesChart(canvas, metrics, {
            title: 'Records Over Time'
        });
    </script>
</body>
</html>
```

---

**Version:** 2.0 | **Last Updated:** 2025-10-21 | **License:** MIT
