# Migration Guide: Integrating Enhanced Charts
## Somali Dialect Classifier Dashboard

**Estimated Time:** 30-45 minutes
**Difficulty:** Intermediate
**Prerequisites:** Basic HTML/JavaScript knowledge

---

## Overview

This guide walks you through integrating the enhanced Chart.js visualizations into your existing GitHub Pages dashboard deployment.

**What You'll Update:**
- `.github/workflows/deploy-dashboard.yml` - Add new JavaScript/CSS files
- Chart initialization code - Switch to enhanced functions
- HTML structure - Add accessibility features

---

## Step-by-Step Migration

### Step 1: Add Enhanced Chart Files to Deployment

**Location:** `.github/workflows/deploy-dashboard.yml`

**Find this section** (around line 1462 in the current file):
```yaml
cat > _site/index.html << 'EOF'
```

**Before the closing `EOF`, add these script tags** after the existing Chart.js imports:

```html
<!-- AFTER existing Chart.js imports, ADD: -->

<!-- Zoom Plugin for Interactive Charts -->
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>

<!-- Enhanced Chart Configuration (Colorblind-Safe, Accessibility) -->
<script>
// ============================================================================
// PASTE CONTENTS OF: dashboard/chart-config-enhanced.js
// ============================================================================

// (Copy the entire content from chart-config-enhanced.js and paste here)

</script>

<!-- Enhanced Chart Implementations -->
<script>
// ============================================================================
// PASTE CONTENTS OF: dashboard/enhanced-charts.js
// ============================================================================

// (Copy the entire content from enhanced-charts.js and paste here)

</script>
```

**For the CSS**, add to the `<style>` section (around line 68):

```html
<style>
    /* ========== Existing styles ========== */
    /* ... keep all existing styles ... */

    /* ========== Enhanced Charts CSS ========== */
    /* PASTE CONTENTS OF: dashboard/enhanced-charts.css */

</style>
```

---

### Step 2: Update Chart Initialization Code

**Location:** Same file, JavaScript section (starting around line 1075)

#### Replace Time Series Chart

**Find this code** (around line 1095):
```javascript
function renderRecordsOverTimeChart(metrics) {
    const ctx = document.getElementById('recordsOverTimeChart');
    if (!ctx) return;

    // ... existing code ...

    if (recordsChart) recordsChart.destroy();
    recordsChart = new Chart(ctx, config);
}
```

**Replace with:**
```javascript
function renderRecordsOverTimeChart(metrics) {
    const ctx = document.getElementById('recordsOverTimeChart');
    if (!ctx) return;

    // Destroy existing chart
    if (recordsChart) recordsChart.destroy();

    // Create enhanced chart
    recordsChart = createEnhancedTimeSeriesChart(ctx, metrics, {
        title: 'Data Collection Progress Over Time',
        fillArea: true
    });

    console.log('✅ Enhanced time series chart created');
}
```

#### Replace Source Comparison Chart

**Find this code** (around line 1186):
```javascript
function renderSourceComparisonChart(metrics) {
    const ctx = document.getElementById('sourceComparisonChart');
    if (!ctx) return;

    // ... existing code ...

    if (sourceChart) sourceChart.destroy();
    sourceChart = new Chart(ctx, config);
}
```

**Replace with:**
```javascript
function renderSourceComparisonChart(metrics) {
    const ctx = document.getElementById('sourceComparisonChart');
    if (!ctx) return;

    // Destroy existing chart
    if (sourceChart) sourceChart.destroy();

    // Create enhanced chart
    sourceChart = createEnhancedSourceComparisonChart(ctx, metrics, {
        title: 'Source Contribution to Dataset'
    });

    console.log('✅ Enhanced source comparison chart created');
}
```

#### Replace Success Rate Chart

**Find this code** (around line 1247):
```javascript
function renderSuccessRateChart(metrics) {
    const ctx = document.getElementById('successRateChart');
    if (!ctx) return;

    // ... existing code ...

    if (successChart) successChart.destroy();
    successChart = new Chart(ctx, config);
}
```

**Replace with:**
```javascript
function renderSuccessRateChart(metrics) {
    const ctx = document.getElementById('successRateChart');
    if (!ctx) return;

    // Destroy existing chart
    if (successChart) successChart.destroy();

    // Create enhanced chart (using time series function)
    successChart = createEnhancedTimeSeriesChart(ctx, metrics, {
        title: 'Success Rate Trends',
        fillArea: false
    });

    console.log('✅ Enhanced success rate chart created');
}
```

#### Replace Quality Metrics Chart

**Find this code** (around line 1338):
```javascript
function renderDataQualityChart(metrics) {
    const ctx = document.getElementById('dataQualityChart');
    if (!ctx) return;

    // ... existing code ...

    if (qualityChart) qualityChart.destroy();
    qualityChart = new Chart(ctx, config);
}
```

**Replace with:**
```javascript
function renderDataQualityChart(metrics) {
    const ctx = document.getElementById('dataQualityChart');
    if (!ctx) return;

    // Destroy existing chart
    if (qualityChart) qualityChart.destroy();

    // Create enhanced chart
    qualityChart = createEnhancedHeatmapChart(ctx, metrics, {
        title: 'Data Quality Metrics'
    });

    console.log('✅ Enhanced quality metrics chart created');
}
```

---

### Step 3: Update HTML Structure for Accessibility

**Find chart containers** (around lines 820-851) and update them:

**Before:**
```html
<div class="chart-canvas" role="img" aria-label="Line chart showing records processed over time by data source">
    <canvas id="recordsOverTimeChart"></canvas>
</div>
```

**After:**
```html
<div class="chart-canvas">
    <canvas id="recordsOverTimeChart"
            role="img"
            tabindex="0"
            aria-label="Line chart showing records processed over time by data source. Use arrow keys to navigate data points, R to reset zoom."></canvas>
</div>
<div class="chart-keyboard-hint" style="margin-top: 8px; padding: 8px 12px; background: #EFF6FF; border-radius: 4px; font-size: 12px; color: #1E40AF; display: none;">
    💡 <strong>Keyboard shortcuts:</strong> Arrow keys to navigate, R to reset zoom, Escape to clear tooltip
</div>
```

**Repeat for all chart canvases.**

---

### Step 4: Register Plugins

**Add this code** after Chart.js is loaded, before any charts are created (around line 1455):

```javascript
// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Register enhanced chart plugins
    if (typeof CrosshairPlugin !== 'undefined') {
        Chart.register(CrosshairPlugin);
        console.log('✅ Crosshair plugin registered');
    }

    if (typeof ChartZoom !== 'undefined') {
        Chart.register(ChartZoom);
        console.log('✅ Zoom plugin registered');
    }

    // Load metrics and render charts
    loadMetrics();
    loadReports();
});
```

---

### Step 5: Add Keyboard Hint Visibility

**Add this CSS** to show keyboard hints when chart is focused:

```css
/* Show keyboard hint when chart is focused */
canvas:focus + .chart-keyboard-hint {
    display: block !important;
}

/* Enhanced focus indicator for charts */
canvas:focus {
    outline: 3px solid #2563EB;
    outline-offset: 3px;
    box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.1);
}
```

---

### Step 6: Optional - Add Pipeline Funnel Chart

If you want to add the funnel chart (currently not in the deployment):

**Add to HTML** (insert in appropriate section):
```html
<div class="charts-section">
    <div class="chart-container">
        <div class="chart-title">Pipeline Processing Funnel</div>
        <div class="chart-canvas" role="img" aria-label="Funnel chart showing conversion through pipeline stages">
            <canvas id="pipelineFunnelChart"></canvas>
        </div>
    </div>
</div>
```

**Add to JavaScript**:
```javascript
function renderPipelineFunnelChart(metrics) {
    const ctx = document.getElementById('pipelineFunnelChart');
    if (!ctx) return;

    if (funnelChart) funnelChart.destroy();

    funnelChart = createEnhancedFunnelChart(ctx, metrics, {
        title: 'Pipeline Processing Funnel'
    });

    console.log('✅ Enhanced funnel chart created');
}

// Call in renderCharts function
function renderCharts(metrics) {
    // ... existing charts ...
    renderPipelineFunnelChart(metrics);
}
```

---

### Step 7: Test Locally (Optional but Recommended)

Before deploying, test the changes locally:

1. **Copy the generated HTML** from the workflow file
2. **Save as** `test-dashboard.html`
3. **Open in browser** and test:
   - ✅ All charts render
   - ✅ Keyboard navigation works (Tab, Arrow keys, R)
   - ✅ Zoom works on time series (mouse wheel)
   - ✅ Export buttons appear and work
   - ✅ Mobile responsive (test with DevTools)
   - ✅ Screen reader announcements (test with NVDA/JAWS/VoiceOver)

---

### Step 8: Deploy to GitHub Pages

1. **Commit changes** to `.github/workflows/deploy-dashboard.yml`
2. **Push to GitHub**
3. **Wait for GitHub Actions** to complete
4. **Visit** `https://somali-nlp.github.io/somali-dialect-classifier/`
5. **Verify** all enhancements work

---

## Verification Checklist

After deployment, verify the following:

### Visual Checks
- [ ] All charts use colorblind-safe palette
- [ ] Colors match: Wikipedia=Blue, BBC=Red, HuggingFace=Green, Sprakbanken=Yellow
- [ ] Charts are responsive on mobile
- [ ] Focus indicators are visible
- [ ] Tooltips are styled correctly

### Functionality Checks
- [ ] Time series chart zooms with mouse wheel
- [ ] Reset button appears when zoomed
- [ ] Keyboard shortcuts work (R to reset, arrows to navigate)
- [ ] Export buttons download CSV files
- [ ] Click events on bar chart work

### Accessibility Checks
- [ ] Tab key moves between charts
- [ ] Arrow keys navigate data points
- [ ] Screen reader announces chart titles
- [ ] All canvases have aria-label
- [ ] Focus indicators have 3px outline

### Performance Checks
- [ ] Charts render in <500ms
- [ ] No JavaScript errors in console
- [ ] Mobile touch interactions work
- [ ] Page load time is acceptable

---

## Troubleshooting

### Issue: Charts not rendering

**Symptoms:** Blank canvases

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify all scripts are loaded (check Network tab)
3. Ensure Chart.js version is 4.4.0+
4. Check if `createEnhanced*` functions are defined:
   ```javascript
   console.log(typeof createEnhancedTimeSeriesChart); // Should be 'function'
   ```

---

### Issue: Colors are wrong

**Symptoms:** Charts not using colorblind-safe palette

**Solutions:**
1. Verify `SourceColors` is defined:
   ```javascript
   console.log(SourceColors);
   ```
2. Check if source names match exactly (case-sensitive)
3. Ensure `chart-config-enhanced.js` is loaded before `enhanced-charts.js`

---

### Issue: Zoom not working

**Symptoms:** Mouse wheel doesn't zoom

**Solutions:**
1. Verify zoom plugin is loaded:
   ```javascript
   console.log(typeof ChartZoom); // Should be 'object'
   ```
2. Check if plugin is registered:
   ```javascript
   Chart.register(ChartZoom);
   ```
3. Ensure only time series chart has zoom (by design)

---

### Issue: Keyboard navigation not working

**Symptoms:** Arrow keys don't navigate

**Solutions:**
1. Click on chart to focus first
2. Check if `setupKeyboardNavigation` was called
3. Verify canvas has `tabindex="0"`
4. Check browser console for errors

---

### Issue: Mobile touch not responsive

**Symptoms:** Small touch targets, gestures don't work

**Solutions:**
1. Verify responsive config is applied:
   ```javascript
   console.log(chart.options.elements.point.hitRadius); // Should be 20 on mobile
   ```
2. Test on actual device (not just browser emulation)
3. Check viewport meta tag is present

---

### Issue: Export not working

**Symptoms:** Export button doesn't appear or doesn't download

**Solutions:**
1. Verify `setupDataExport` function is called
2. Check if button is visible (might be outside viewport)
3. Test browser allows downloads
4. Check browser console for errors

---

## Rollback Plan

If issues occur in production:

### Option 1: Quick Rollback

Revert the commit in GitHub:
```bash
git revert <commit-hash>
git push
```

### Option 2: Disable Enhanced Features

Comment out the enhanced chart calls and use original Chart.js:
```javascript
// Temporarily disable enhanced charts
// recordsChart = createEnhancedTimeSeriesChart(ctx, metrics);

// Use original Chart.js
recordsChart = new Chart(ctx, {
    type: 'line',
    data: data,
    options: options
});
```

---

## Performance Optimization

If you experience slow performance:

### Enable Decimation for Large Datasets

Add to chart options:
```javascript
options: {
    plugins: {
        decimation: {
            enabled: true,
            algorithm: 'lttb',
            samples: 500,
            threshold: 1000
        }
    }
}
```

### Enable Lazy Loading

Wrap chart creation:
```javascript
setupLazyLoading(canvas, () => {
    createEnhancedTimeSeriesChart(canvas, metrics);
});
```

---

## Additional Enhancements (Optional)

### Add Dark Mode Support

Already included in CSS, activate with:
```javascript
// Detect system preference
if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.body.classList.add('dark-mode');
}
```

### Add Data Table Alternatives

For each chart:
```javascript
generateDataTable(chart, 'chart-container-id');
```

### Add Annotation Lines

For reference lines (requires annotation plugin):
```javascript
options: {
    plugins: {
        annotation: {
            annotations: {
                line1: {
                    type: 'line',
                    yMin: 1000,
                    yMax: 1000,
                    borderColor: 'rgb(255, 99, 132)',
                    borderWidth: 2,
                }
            }
        }
    }
}
```

---

## FAQ

**Q: Will this break the current dashboard?**
A: No, if migration is done correctly. The enhanced functions are drop-in replacements.

**Q: Do I need to update the data format?**
A: No, enhanced charts use the same data format as before.

**Q: Will bundle size increase significantly?**
A: Yes, by ~50KB uncompressed (~15KB gzipped). This is acceptable for the features gained.

**Q: Can I use only some enhanced features?**
A: Yes, you can selectively enhance charts. Just use enhanced functions for specific charts.

**Q: Is this compatible with existing Chart.js code?**
A: Yes, 100% compatible. Enhanced functions build on top of Chart.js, not replace it.

**Q: What Chart.js version is required?**
A: Chart.js 4.4.0 or higher. The current deployment uses 4.4.0, so no upgrade needed.

---

## Next Steps After Migration

1. **Monitor Analytics** - Track user engagement with new features
2. **Collect Feedback** - Ask users about accessibility improvements
3. **Accessibility Audit** - Run Lighthouse and axe DevTools
4. **Performance Monitoring** - Check real-world performance metrics
5. **User Testing** - Test with actual screen reader users
6. **Documentation** - Update project README with new features

---

## Support

If you encounter issues during migration:

1. **Check Documentation:**
   - `CHART_ENHANCEMENTS.md` - Full guide
   - `QUICK_REFERENCE.md` - Quick solutions
   - `example-integration.html` - Working example

2. **Review Example:**
   Open `example-integration.html` to see working implementation

3. **Test Locally:**
   Before deploying, test changes in a local HTML file

4. **Incremental Migration:**
   Migrate one chart at a time to isolate issues

---

## Completion Checklist

- [ ] Step 1: Added enhanced chart files to deployment
- [ ] Step 2: Updated chart initialization code
- [ ] Step 3: Updated HTML structure for accessibility
- [ ] Step 4: Registered plugins
- [ ] Step 5: Added keyboard hint visibility
- [ ] Step 6: (Optional) Added funnel chart
- [ ] Step 7: Tested locally
- [ ] Step 8: Deployed to GitHub Pages
- [ ] Verified all features work in production
- [ ] Ran accessibility audit (Lighthouse 100/100)
- [ ] Tested on mobile devices
- [ ] Updated project documentation

---

**Migration Status:** Ready for Implementation
**Estimated Time:** 30-45 minutes
**Risk Level:** Low (changes are additive, not breaking)
**Rollback Time:** <5 minutes

**Good luck with the migration! 🚀**
