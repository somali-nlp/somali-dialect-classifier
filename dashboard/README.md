# Dashboard Technical Reference

Modern ES6 modular dashboard for monitoring data pipeline metrics and quality.

**For complete documentation, setup instructions, and usage guide, see**: [Dashboard Guide](../docs/guides/dashboard.md)

---

## Quick Reference

### Running Locally

**Requirements**: HTTP server (ES6 modules require HTTP protocol)

```bash
# 1. Build the site (aggregates metrics and copies files)
./build-site.sh

# 2. Start HTTP server in _site directory
cd _site && python3 -m http.server 8000

# 3. Open browser
# Navigate to: http://localhost:8000
```

**Important**: Do NOT open `index.html` directly with `file://` protocol. ES6 modules require HTTP server.

### Live Dashboard

**GitHub Pages**: `https://somali-nlp.github.io/somali-dialect-classifier/`
*Deployment*: Automatic via GitHub Actions on push to main branch

---

## Technical Specifications

### Architecture

**ES6 Modular Design** (Code Quality: 9.0/10)

- Modern JavaScript with ES6 modules
- No runtime dependencies (Chart.js loaded via CDN)
- Structured logging with environment-aware verbosity
- Configuration management with override capability
- Data normalization layer for schema compatibility

### Browser Requirements

- **Chrome**: 61+ (ES6 modules support)
- **Firefox**: 60+
- **Safari**: 11+
- **Edge**: 79+ (Chromium-based)

### Data Sources

The dashboard reads from:
- `../data/metrics/*.json` - Pipeline metrics (auto-generated)
- `../data/reports/*.md` - Quality reports (auto-generated)
- `_site/data/all_metrics.json` - Aggregated metrics (build output)

### File Structure

```
dashboard/
├── index.html                # Main dashboard HTML
├── css/                      # Stylesheets
│   ├── dashboard.css        # Core dashboard styles
│   └── dark-mode.css        # Dark mode overrides
├── js/                       # ES6 modular JavaScript
│   ├── config.js            # Configuration management
│   ├── main.js              # Entry point & initialization
│   ├── core/                # Core functionality
│   │   ├── data-service.js # Data loading & normalization
│   │   ├── stats.js        # Statistics calculation
│   │   ├── charts.js       # Chart rendering
│   │   ├── ui-renderer.js  # UI component rendering
│   │   └── tabs.js         # Tab navigation
│   ├── features/            # Advanced features
│   │   ├── export-manager.js    # Export functionality
│   │   ├── advanced-charts.js   # Sankey, Ridge plots
│   │   └── comparison.js        # Run comparison
│   └── utils/               # Utilities
│       ├── logger.js        # Structured logging
│       └── formatters.js    # Data formatting
├── build-site.sh            # Build script for deployment
└── README.md               # This file
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
2. Add metric to export script `scripts/export_dashboard_data.py`
3. Create chart function in `dashboard/js/core/charts.js`
4. Add canvas element to `dashboard/index.html`
5. Initialize chart in `dashboard/js/main.js`
6. Test locally, then commit and push

Example:

```javascript
// In dashboard/js/core/charts.js
export function renderMyNewChart(metricsData) {
    const ctx = document.getElementById('myNewChart')?.getContext('2d');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: metricsData.metrics.map(m => m.source),
            datasets: [{
                label: 'My New Metric',
                data: metricsData.metrics.map(m => m.my_new_metric || 0),
                backgroundColor: '#0176D3'
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true } }
        }
    });
}
```

### Modifying Visualizations

All charts use Chart.js 4.4.0. Key patterns:

```javascript
// Get canvas context with null check
const ctx = document.getElementById('chartId')?.getContext('2d');
if (!ctx) {
    Logger.warn('Chart canvas not found');
    return;
}

// Create chart with defensive data mapping
new Chart(ctx, {
    type: 'line',
    data: {
        datasets: [{
            label: 'My Data',
            data: metricsData.metrics.map(m => ({
                x: m.timestamp,
                y: m.value || 0  // Always provide fallback
            })),
            borderColor: Config.CHART_COLORS.primary
        }]
    },
    options: {
        responsive: true,
        scales: {
            x: { type: 'time' },
            y: { beginAtZero: true }
        }
    }
});

Logger.debug('Chart rendered successfully');
```

### Styling

Dashboard uses CSS custom properties for theming:

```css
/* In dashboard/css/dashboard.css */
:root {
    --primary-color: #0176D3;
    --bg-primary: #FFFFFF;
    --text-primary: #080707;
}

[data-theme="dark"] {
    --primary-color: #60a5fa;
    --bg-primary: #1a1a1a;
    --text-primary: #f5f5f5;
}
```

Toggle dark mode programmatically:

```javascript
// Set theme
document.documentElement.setAttribute('data-theme', 'dark');

// Toggle theme
const currentTheme = document.documentElement.getAttribute('data-theme');
const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
document.documentElement.setAttribute('data-theme', newTheme);
```

---

## API Reference

### Core Modules

#### `config.js`

Configuration management with override support.

```javascript
import { Config } from './js/config.js';

// Access configuration
Config.DATA_PATHS        // Array of data file paths
Config.FETCH_TIMEOUT     // Network timeout (ms)
Config.CHART_COLORS      // Color scheme

// Override configuration
Config.DATA_PATHS = ['custom/path/metrics.json'];
```

#### `data-service.js`

Data loading and normalization.

```javascript
import { loadMetrics, refreshMetrics } from './js/core/data-service.js';

// Load metrics (cached)
const data = await loadMetrics();

// Force refresh
const freshData = await refreshMetrics();
```

#### `logger.js`

Structured logging with level control.

```javascript
import { Logger, LogLevel } from './js/utils/logger.js';

// Set log level
Logger.level = LogLevel.DEBUG;  // DEBUG, INFO, WARN, ERROR, OFF

// Log messages
Logger.debug('Debug message', { context: 'value' });
Logger.info('Info message');
Logger.warn('Warning message', error);
Logger.error('Error message', error);

// Performance timing
Logger.time('operation-name');
// ... perform operation ...
Logger.timeEnd('operation-name');
```

#### `charts.js`

Chart rendering functions.

```javascript
import { initCharts, renderRecordsChart } from './js/core/charts.js';

// Initialize all charts
initCharts(metricsData);

// Render specific chart
renderRecordsChart(metricsData);
```

---

## Development

### Local Testing

```bash
# 1. Build dashboard
./build-site.sh

# 2. Start HTTP server
cd _site && python3 -m http.server 8000

# 3. Open browser to http://localhost:8000
# Open DevTools (F12) to see console logs
```

### Development Workflow

```bash
# 1. Make changes to JavaScript/CSS/HTML in dashboard/
vim dashboard/js/core/charts.js

# 2. Rebuild
./build-site.sh

# 3. Refresh browser (server doesn't need restart)
# Hard refresh: Ctrl+Shift+R (Chrome/Firefox) or Cmd+Shift+R (Safari)
```

### Debugging

**Enable Debug Logging** (in browser console):

```javascript
// Set debug level
Logger.level = LogLevel.DEBUG;

// Refresh to see debug output
location.reload();

// Check loaded data
console.log('Data:', await loadMetrics());

// Test specific function
import { renderRecordsChart } from './js/core/charts.js';
renderRecordsChart(metricsData);
```

**Check Data Loading**:

```javascript
// In browser console
fetch('data/all_metrics.json')
    .then(r => r.json())
    .then(data => console.log('Data loaded:', data))
    .catch(error => console.error('Load failed:', error));
```

**Monitor Performance**:

```javascript
// Wrap operations with timing
Logger.time('chart-render');
initCharts(metricsData);
Logger.timeEnd('chart-render');
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

**Dashboard shows blank page or "Failed to fetch"**:

Most common cause: Opening `index.html` with `file://` protocol

```bash
# ❌ WRONG: Opening file directly
open _site/index.html  # This will NOT work

# ✅ CORRECT: Using HTTP server
cd _site && python3 -m http.server 8000
# Then open http://localhost:8000
```

**Dashboard not loading data**:
```bash
# 1. Check if data file exists
ls _site/data/all_metrics.json

# 2. Verify JSON format
python3 -m json.tool _site/data/all_metrics.json | head -50

# 3. Check browser console (F12) for errors
# Look for: fetch errors, CORS errors, module loading failures

# 4. Rebuild if data is missing
./build-site.sh
```

**Charts not rendering**:

```javascript
// In browser console, check:
// 1. Is Chart.js loaded?
typeof Chart  // Should return "function"

// 2. Are there JavaScript errors?
// Check Console tab in DevTools

// 3. Is data loaded?
Logger.level = LogLevel.DEBUG;
location.reload();
// Watch console for data loading messages
```

**Port already in use**:
```bash
# Kill existing process
lsof -i :8000
kill -9 <PID>

# Or use different port
python3 -m http.server 8001
```

**Build script fails**:
```bash
# Check permissions
chmod +x build-site.sh

# Run with verbose output
bash -x build-site.sh

# Verify Python script works
python3 ../scripts/export_dashboard_data.py
```

---

## Resources

- **Complete Guide**: [Dashboard Guide](../docs/guides/dashboard.md)
- **Architecture Reference**: [Dashboard Architecture](../docs/reference/dashboard-architecture.md)
- **Chart.js Docs**: https://www.chartjs.org/docs/latest/
- **ES6 Modules**: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules
- **GitHub Actions**: https://docs.github.com/actions

---

**Architecture**: ES6 Modular
**Code Quality**: 9.0/10
**Version**: 3.2.0
**Last Updated**: 2025-10-28
**License**: MIT License
