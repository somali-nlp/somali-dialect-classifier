# Quick Reference: Dashboard Visualization Guide
**One-page cheat sheet for choosing and using dashboards**

---

## At a Glance

| Use Case | Choose | URL |
|----------|--------|-----|
| Quick status check | Chart.js | `/index.html` |
| Debugging pipeline issue | D3.js | `/advanced.html` |
| Weekly stakeholder meeting | Chart.js | `/index.html` |
| Technical deep dive | D3.js | `/advanced.html` |
| Mobile viewing | Chart.js | `/index.html` |
| Finding correlations | D3.js | `/advanced.html` |
| Exporting screenshots | Chart.js | `/index.html` |
| Exploratory analysis | D3.js | `/advanced.html` |

---

## Chart Selection Guide

### When to Use Each Chart Type

#### Chart.js Options
```
Line Chart
  Use for: Trends over time
  Example: "Records processed increasing weekly"
  Data: Time-series with 2-3 dimensions

Bar Chart
  Use for: Comparing categories
  Example: "Wikipedia has 2× more records than BBC"
  Data: Categorical comparison

Doughnut Chart
  Use for: Part-to-whole relationships
  Example: "BBC contributes 35% of total records"
  Data: Percentages that sum to 100%
```

#### D3.js Options
```
Bubble Timeline
  Use for: Multi-dimensional time-series
  Example: "Which source had anomalies when?"
  Data: Events with 5+ attributes

Radial Comparison
  Use for: Compact multi-metric comparison
  Example: "How do all 4 sources compare across 3 metrics?"
  Data: 4-8 categories × 3-4 metrics

Horizon Charts
  Use for: Dense time-series comparison
  Example: "Show 7 days of success rates for 4 sources"
  Data: Multiple aligned time-series

Hexbin Heatmap
  Use for: Correlation analysis
  Example: "Does high dedup reduce success rate?"
  Data: Two continuous variables + frequency

Streamgraph
  Use for: Volume distribution over time
  Example: "How has each source's contribution changed?"
  Data: Stacked area with centered baseline

Health Matrix
  Use for: System status monitoring
  Example: "Which source has latency issues?"
  Data: Grid of sources × metrics
```

---

## Keyboard Shortcuts

### Chart.js Dashboard
```
Tab              Focus next chart element
Shift+Tab        Focus previous element
Ctrl+Scroll      Zoom in/out (on charts with zoom enabled)
Ctrl+Drag        Pan chart
```

### D3.js Dashboard
```
Tab              Focus next interactive element
Shift+Tab        Focus previous element
Enter/Space      Activate focused element (show tooltip)
Arrow Keys       Navigate within chart (e.g., health matrix cells)
Esc              Close tooltip
```

---

## Common Tasks

### Task: Export Chart Data
**Chart.js**:
```javascript
// Open browser console (F12), run:
const chart = Chart.getChart('recordsOverTimeChart');
const data = chart.data.datasets;
console.table(data);
// Then copy from console
```

**D3.js**:
```javascript
// Open browser console (F12), run:
const metrics = window.metrics; // Global variable
const csv = metrics.map(m => Object.values(m).join(',')).join('\n');
console.log(csv);
// Or add export button (see INTEGRATION_GUIDE.md)
```

### Task: Filter by Date Range
**Chart.js**: Use zoom to focus on specific time period
**D3.js**: Add date range filter (see INTEGRATION_GUIDE.md Week 2)

### Task: Compare Two Time Periods
**Chart.js**: Visually compare by zooming
**D3.js**: Horizon charts show aligned comparison automatically

### Task: Identify Anomalies
**Chart.js**: Manual visual inspection
**D3.js**: Bubble timeline shows ⚠️ markers automatically

### Task: Find Correlations
**Chart.js**: Not possible (must manually compare separate charts)
**D3.js**: Use hexbin heatmap

---

## Troubleshooting

### Chart.js Issues

**Problem**: Chart not rendering
```bash
Solution:
1. Open browser console (F12)
2. Check for errors
3. Verify data/all_metrics.json exists:
   curl https://[username].github.io/somali-dialect-classifier/data/all_metrics.json
4. Check Chart.js version:
   console.log(Chart.version); // Should be 4.4.0
```

**Problem**: Zoom not working
```bash
Solution:
1. Check if chartjs-plugin-zoom is loaded:
   console.log(typeof Chart.Zoom); // Should not be undefined
2. Use Ctrl+Scroll (not just scroll)
3. Try Ctrl+Drag to pan
```

**Problem**: Mobile touch not working
```bash
Solution:
1. Use two-finger pinch for zoom
2. Single tap for tooltips
3. Swipe to pan
```

### D3.js Issues

**Problem**: Charts are blank
```bash
Solution:
1. Check console for errors
2. Verify data loaded:
   console.log(window.metrics); // Should be array
3. Check if D3 loaded:
   console.log(d3.version); // Should be "7.x.x"
4. Fallback to sample data:
   // Refresh page, should auto-fallback
```

**Problem**: Tooltips not showing
```bash
Solution:
1. Hover over elements (don't click)
2. For keyboard: Tab to element, press Enter
3. For touch: Tap and hold briefly
4. Check console for tooltip errors
```

**Problem**: Performance is slow
```bash
Solution:
1. Check data size:
   console.log(metrics.length); // >500 points may be slow
2. Enable performance monitoring:
   console.log('Render time:', performance.measure(...));
3. Consider data sampling for initial view
```

---

## Data Structure Reference

### Minimum Required Fields
```json
{
  "timestamp": "2025-10-21T12:26:44Z",
  "source": "BBC-Somali",
  "records_written": 49,
  "success_rate": 0.9795918367346939
}
```

### Full Feature Set
```json
{
  "timestamp": "2025-10-21T12:26:44Z",
  "run_id": "20251021_113641_bbc_somali_efac82d1",
  "source": "BBC-Somali",
  "records_written": 49,
  "success_rate": 0.9795918367346939,
  "deduplication_rate": 0.0,
  "quality_score": 85.2,
  "uptime": 99.5,
  "latency_ms": 650.5,
  "error_rate": 2.04,
  "urls_discovered": 118,
  "urls_fetched": 49,
  "urls_processed": 49,
  "urls_failed": 1
}
```

### Field Calculations
```python
# In workflow Python script:
quality_score = 100 - (error_rate * 100)
uptime = (urls_fetched / (urls_fetched + urls_failed)) * 100
error_rate = fetch_failure_rate * 100
latency_ms = fetch_duration_stats['mean']
```

---

## Color Coding Reference

### Chart.js Palette (Wong's Colorblind-Safe)
```
Wikipedia:   #0173B2 (Blue)
BBC:         #DE8F05 (Orange)
HuggingFace: #029E73 (Green)
Sprakbanken: #CC78BC (Pink)
```

### D3.js Palette (Paul Tol's Colorblind-Safe)
```
Wikipedia:   #4477AA (Blue)
BBC:         #EE6677 (Red)
HuggingFace: #228833 (Green)
Sprakbanken: #CCBB44 (Yellow)
```

### Success Rate Colors
```
High (>90%):    #228833 (Green)
Medium (70-90%): #CCBB44 (Yellow)
Low (<70%):     #EE6677 (Red)
```

### Health Status Colors
```
Excellent (95-100%): #10B981 (Green)
Good (85-95%):       #3B82F6 (Blue)
Warning (70-85%):    #F59E0B (Orange)
Critical (<70%):     #EF4444 (Red)
```

---

## Accessibility Quick Tips

### For Chart.js
- Tab to navigate between chart elements
- Focus indicators are visible (blue outline)
- Screen readers announce chart title and data
- Color contrast meets WCAG AA (4.5:1 minimum)

### For D3.js
- Tab through all interactive elements
- Enter/Space activates focused element
- Arrow keys navigate within charts (health matrix)
- 44×44px minimum touch targets (WCAG)
- Tooltips announced via aria-live regions

### Testing Tools
```bash
# Contrast checker
https://webaim.org/resources/contrastchecker/

# Screen reader testing
- macOS: VoiceOver (Cmd+F5)
- Windows: NVDA (free)
- Chrome: ChromeVox extension

# Colorblind simulation
- Chrome DevTools > Rendering > Emulate vision deficiencies
```

---

## Performance Targets

### Chart.js
```
Initial page load:     <1.5s (3G network)
Chart render:          <200ms
Tooltip show:          <16ms (60fps)
Zoom/pan:              <16ms (60fps)
Memory usage:          <15MB
```

### D3.js
```
Initial page load:     <2s (3G network)
Chart render:          <500ms
Tooltip show:          <33ms (30fps)
Zoom/pan:              <33ms (30fps)
Memory usage:          <25MB
```

**Monitoring**:
```javascript
// Check render time
const start = performance.now();
// ... render charts ...
const end = performance.now();
console.log(`Render time: ${(end - start).toFixed(0)}ms`);
```

---

## Integration Checklist

### Pre-Deployment
- [ ] Test locally with `python3 -m http.server 8000`
- [ ] Verify all 6 D3.js charts render
- [ ] Check console for errors
- [ ] Test navigation links
- [ ] Test on mobile (Chrome DevTools)

### Post-Deployment
- [ ] Visit production URL
- [ ] Verify data loads from `data/all_metrics.json`
- [ ] Test tooltips and interactions
- [ ] Check browser console for errors
- [ ] Test on real mobile device
- [ ] Share with 2-3 team members for feedback

### Week 1 Monitoring
- [ ] Check analytics (views, time on page)
- [ ] Gather user feedback
- [ ] Monitor for errors (console logs)
- [ ] Verify performance (render times)
- [ ] Decide on Option C migration

---

## Useful Links

### Documentation
- Chart.js: https://www.chartjs.org/docs/
- D3.js: https://d3js.org/
- Observable D3: https://observablehq.com/@d3/gallery

### Community
- Chart.js GitHub: https://github.com/chartjs/Chart.js
- D3.js GitHub: https://github.com/d3/d3
- Stack Overflow: [chartjs] or [d3.js] tags

### Design Resources
- Color Oracle (colorblind simulator): https://colororacle.org/
- Paul Tol's palettes: https://personal.sron.nl/~pault/
- WCAG guidelines: https://www.w3.org/WAI/WCAG21/quickref/

### Testing
- WebAIM WAVE: https://wave.webaim.org/
- Lighthouse (Chrome DevTools)
- axe DevTools: https://www.deque.com/axe/devtools/

---

## Contact for Help

**Chart.js Issues**:
- GitHub: https://github.com/chartjs/Chart.js/issues
- Stack Overflow: [chartjs] tag
- Discord: https://discord.gg/chartjs

**D3.js Issues**:
- GitHub: https://github.com/d3/d3/issues
- Stack Overflow: [d3.js] tag
- Observable Forums: https://talk.observablehq.com/

**Project-Specific**:
- Create GitHub issue in your repo
- Tag with `dashboard` or `visualization`
- Include browser, data sample, console errors

---

## Quick Commands

```bash
# Test locally
cd _site && python3 -m http.server 8000
# Open: http://localhost:8000/advanced.html

# Check data
curl https://[username].github.io/somali-dialect-classifier/data/all_metrics.json | jq

# Deploy
git add . && git commit -m "feat: update dashboard" && git push

# View workflow logs
gh run list --workflow=deploy-dashboard.yml
gh run view [run-id] --log

# Check production
curl -I https://[username].github.io/somali-dialect-classifier/advanced.html
```

---

**Print this page for quick reference while developing!**
