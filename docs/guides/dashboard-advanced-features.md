# Dashboard Advanced Features Guide

**Comprehensive guide to advanced dashboard functionality and features.**

**Last Updated**: 2025-10-27
**Audience**: Power users, data analysts, ML engineers

---

## Table of Contents

- [Overview](#overview)
- [Advanced Visualizations](#advanced-visualizations)
  - [Sankey Diagrams](#sankey-diagrams)
  - [Ridge Plots](#ridge-plots)
  - [Bullet Charts](#bullet-charts)
- [Interactive Features](#interactive-features)
  - [Dark Mode](#dark-mode)
  - [Chart Export](#chart-export)
  - [Date Range Filtering](#date-range-filtering)
  - [Advanced Filters](#advanced-filters)
  - [Comparison Mode](#comparison-mode)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

The Somali Dialect Classifier dashboard includes advanced features designed for power users who need deeper insights, custom visualizations, and flexible data exploration capabilities.

### Feature Matrix

| Feature | Purpose | User Level | Status |
|---------|---------|------------|--------|
| **Sankey Diagrams** | Visualize data flow through pipeline | Advanced | Implemented |
| **Ridge Plots** | Compare distributions across sources | Advanced | Implemented |
| **Bullet Charts** | Performance against targets | Intermediate | Implemented |
| **Dark Mode** | Theme switching for accessibility | All | Planned |
| **Chart Export** | Export visualizations (PNG/PDF/CSV) | All | PNG Implemented |
| **Date Filtering** | Time-based data filtering | Intermediate | Planned |
| **Advanced Filters** | Multi-dimensional filtering | Advanced | Planned |
| **Comparison Mode** | Compare pipeline runs | Advanced | Planned |

---

## Advanced Visualizations

### Sankey Diagrams

**Purpose**: Visualize how data flows through the pipeline from initial discovery through quality filtering to final storage.

#### When to Use

- **Pipeline Optimization**: Identify where most data is lost
- **Quality Analysis**: Understand filter impact visually
- **Stakeholder Communication**: Explain pipeline flow non-technically
- **Bottleneck Detection**: Find stages that need improvement

#### Reading a Sankey Diagram

```
[Discovered] ━━━━━━━━━━━━━━━━━━━━━━━━┓
                                        ┃
                                        ┃ 15,136 records
                                        ▼
                                  [Extracted] ━━━━━━━━┳━━━━━━━━┓
                                                      ┃        ┃
                                      9,623 pass ┃        ┃ 5,513 filtered
                                                      ┃        ┃
                                                      ▼        ▼
                                            [Passed Filters]  [Rejected]
                                                      ┃
                                                      ┃ 9,623 written
                                                      ▼
                                                  [Storage]
```

**Flow Width**: Proportional to record count
**Node Height**: Total throughput at that stage
**Colors**: Different sources or filter types

#### Example Analysis

```javascript
// Wikipedia Sankey interpretation

Discovered: 136 files
    ↓ (100% extraction success)
Extracted: 15,136 records
    ↓ (63.6% quality pass rate)
Passed Filters: 9,623 records
    ├─ min_length_filter: 4,128 rejected (74.9% of rejections)
    ├─ langid_filter: 1,185 rejected (21.5% of rejections)
    └─ empty_after_cleaning: 200 rejected (3.6% of rejections)
    ↓ (0% duplicates)
Stored: 9,623 records

Insights:
→ Primary quality issue: Short articles (stubs)
→ Language detection filtering 21.5% (check confidence threshold)
→ Very few empty pages (good source quality)
→ No duplicates (first run or well-maintained source)
```

#### Configuration

Customize Sankey appearance:

```javascript
const sankeyConfig = {
    nodeWidth: 15,          // Width of boxes
    nodePadding: 10,        // Space between nodes
    iterations: 32,         // Layout optimization passes
    colorScheme: 'tableau', // Color palette
    showValues: true,       // Display counts on flows
    showPercentages: true   // Display % on flows
};
```

#### Troubleshooting

**Issue**: Sankey diagram not rendering

**Solutions**:
1. Check browser console for errors
2. Verify data has required fields: `nodes` and `links`
3. Ensure D3.js library is loaded
4. Check that container element exists

**Issue**: Flow widths seem incorrect

**Solutions**:
1. Verify all link values are positive
2. Check for data type mismatches (string vs number)
3. Ensure conservation of flow (input = output at each node)

---

### Ridge Plots

**Purpose**: Compare distributions of metrics (text length, processing time, quality scores) across different data sources.

#### When to Use

- **Distribution Comparison**: See how metrics vary between sources
- **Outlier Detection**: Identify unusual patterns in one source
- **Quality Assessment**: Compare text length distributions
- **Performance Analysis**: Visualize processing time distributions

#### Reading a Ridge Plot

```
Source A  ┌─────╱╲─────┐
          │    ╱  ╲    │  Mean: 2,500 chars
          └───╱────╲───┘

Source B      ┌──╱╲──┐
              │ ╱  ╲ │      Mean: 1,800 chars
              └╱────╲┘

Source C  ┌───────╱╲───────┐
          │      ╱  ╲      │  Mean: 3,200 chars
          └─────╱────╲─────┘
         ┬─────┬─────┬─────┬
         0    1k    2k    3k   (characters)
```

**Interpretation**:
- **Peak Position**: Most common value (mode)
- **Peak Height**: Density/frequency
- **Width**: Range and variance
- **Shape**: Distribution skew

#### Example Analysis

**Text Length Distribution**:

```
Wikipedia:
  Distribution: Right-skewed (long tail)
  Peak: 800 characters
  Range: 50 - 50,000 characters
  Interpretation: Many short articles (stubs), few long ones

BBC:
  Distribution: Normal (bell curve)
  Peak: 2,500 characters
  Range: 500 - 8,000 characters
  Interpretation: Consistent news article lengths

HuggingFace:
  Distribution: Bimodal (two peaks)
  Peaks: 1,200 and 4,500 characters
  Range: 100 - 20,000 characters
  Interpretation: Mix of short posts and long articles

Språkbanken:
  Distribution: Uniform
  Peak: No clear peak
  Range: 1,000 - 10,000 characters
  Interpretation: Diverse content types
```

#### Configuration

```python
# Backend: Generate ridge plot data
from somali_dialect_classifier.visualization import create_ridge_plot_data

ridge_data = create_ridge_plot_data(
    metrics_data=all_metrics,
    metric_name='text_lengths',
    bins=50,              # Histogram bins
    smoothing='kde',      # Kernel density estimation
    normalize=True        # Scale to same height
)
```

```javascript
// Frontend: Customize appearance
const ridgeConfig = {
    overlap: 0.7,           // How much layers overlap (0-1)
    fillOpacity: 0.6,       // Transparency
    strokeWidth: 2,         // Outline thickness
    colorScheme: 'sources', // Color by source
    showMean: true,         // Mark mean with vertical line
    showMedian: true        // Mark median with dashed line
};
```

#### Use Cases

**1. Quality Control**: Detect if source content quality degraded
```
Before: Normal distribution centered at 2,000 chars
After: Left-skewed distribution centered at 500 chars
→ Source now contains more short/low-quality content
```

**2. Filter Tuning**: Understand impact of length filters
```
Current min_length: 500 chars
Distribution shows: 30% of content between 300-500 chars
Action: Lower threshold to 300 to capture more data
```

---

### Bullet Charts

**Purpose**: Compare actual performance against targets and thresholds in a compact, easy-to-scan format.

#### When to Use

- **KPI Tracking**: Monitor if metrics meet targets
- **Performance Dashboards**: Executive summaries
- **Multi-Source Comparison**: Quick source ranking
- **Goal Setting**: Define acceptable/excellent ranges

#### Reading a Bullet Chart

```
Wikipedia Quality Pass Rate

Poor      Acceptable    Excellent
[████░░░░░░░░░░░░░░░░░░░░░░]  63.6%
  ↑         ↑             ↑
  0        50%           80%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Legend:
● Dark Bar (━━━): Actual performance (63.6%)
○ Light Gray (░): Target performance (70%)
□ Background Zones:
  - Red [0-50%]: Poor
  - Yellow [50-80%]: Acceptable
  - Green [80-100%]: Excellent
```

**Interpretation**:
- **In Green Zone**: Exceeding expectations
- **In Yellow Zone**: Meeting minimum requirements
- **In Red Zone**: Needs immediate attention
- **Below Target**: Gap to close
- **Above Target**: Celebrate success!

#### Example: Multi-Source Performance

```
Quality Pass Rate Comparison

Wikipedia    [████████████░░░░░░░] 63.6% ← Target: 70%
             Poor    OK    Excellent
             Analysis: Slightly below target (yellow zone)
             Action: Review filter thresholds

BBC          [████████████████████] 85.3% ← Target: 80%
             Poor    OK    Excellent
             Analysis: Exceeds target (green zone)
             Action: Maintain current settings

HuggingFace  [██████████████░░░░░░] 72.4% ← Target: 75%
             Poor    OK    Excellent
             Analysis: Near target (yellow zone)
             Action: Minor optimization needed

Språkbanken  [███████████████████░] 91.8% ← Target: 85%
             Poor    OK    Excellent
             Analysis: Excellent performance (green zone)
             Action: Model for other sources
```

#### Configuration

**Define Thresholds**:

```javascript
const bulletConfig = {
    sources: ['Wikipedia', 'BBC', 'HuggingFace', 'Språkbanken'],

    // Define zones (% values)
    ranges: {
        poor: [0, 50],
        acceptable: [50, 80],
        excellent: [80, 100]
    },

    // Set targets per source
    targets: {
        'Wikipedia': 70,
        'BBC': 80,
        'HuggingFace': 75,
        'Språkbanken': 85
    },

    // Customize appearance
    colors: {
        poor: '#f4cccc',
        acceptable: '#fff4cc',
        excellent: '#d1f4d1',
        actual: '#0176D3',
        target: '#888888'
    }
};
```

#### Advanced: Multiple Metrics

Track multiple KPIs per source:

```
Wikipedia Performance Dashboard

Quality Pass Rate   [████████████░░] 63.6% / 70%
Success Rate        [█████████████████] 95.2% / 90%
Deduplication Eff.  [████████████████████] 100% / 95%
Processing Speed    [███████████░░░░] 58.3% / 80%

Overall Score: 79.3% (Acceptable)
```

---

## Interactive Features

### Dark Mode

**Purpose**: Reduce eye strain in low-light environments and provide user preference options.

#### Activation Methods

**Method 1: UI Toggle**
1. Click moon icon in top-right corner
2. Theme switches immediately
3. Preference saved in browser

**Method 2: Keyboard Shortcut**
```
Press: Ctrl + Shift + D
```

**Method 3: System Preference**
- Dashboard respects OS dark mode setting
- Auto-switch based on time of day (if enabled in browser)

#### Dark Mode Features

**Chart Adjustments**:
- Lighter colors for better contrast
- Grid lines optimized for dark backgrounds
- Text colors inverted but high contrast maintained
- Tooltips styled for readability

**Color Palette Changes**:

| Element | Light Mode | Dark Mode |
|---------|-----------|-----------|
| Background | `#FFFFFF` | `#1a1a1a` |
| Text | `#080707` | `#f5f5f5` |
| Cards | `#F4F4F4` | `#252525` |
| Borders | `#EBEBEB` | `#404040` |
| Wikipedia | `#3b82f6` | `#60a5fa` (lighter) |
| BBC | `#ef4444` | `#f87171` (lighter) |

**Accessibility**:
- WCAG AAA contrast compliance
- Colorblind-safe palette
- No information conveyed by color alone
- Focus indicators visible in both modes

#### Troubleshooting

**Issue**: Dark mode not persisting

**Solution**: Enable localStorage in browser settings

**Issue**: Charts still showing light colors

**Solution**: Hard refresh (Ctrl + Shift + R) to reload Chart.js instances

**Issue**: Some text unreadable in dark mode

**Solution**: Report bug with screenshot - CSS custom properties may need adjustment

---

### Chart Export

**Purpose**: Save visualizations for reports, presentations, or offline analysis.

#### Supported Formats

**PNG Export** (Implemented):
- High resolution (2x pixel density)
- Transparent background option
- Includes title and legend
- Instant download

**PDF Export** (Planned):
- Vector graphics (scalable)
- Multiple charts per page
- Embedded metadata
- Professional quality

**CSV Export** (Planned):
- Raw chart data
- Headers and labels
- Import into Excel/Sheets
- Data analysis ready

#### How to Export

**Individual Chart**:
```
1. Hover over chart
2. Click "Export PNG" button
3. Image downloads as: chartId_2025-10-27T14-30-00.png
4. Use in your presentation/report
```

**Bulk Export** (Planned):
```
1. Click "Export All Charts" in navigation
2. Select format: PNG, PDF, or ZIP
3. Choose resolution: Standard, High, Print
4. Download archive with all charts
```

**Custom Export**:
```javascript
// Export specific chart programmatically
const exporter = new ChartExporter();

exporter.exportChart('recordsChart', 'png', {
    resolution: 3.0,      // 3x for print quality
    background: 'white',  // Override transparent
    watermark: false      // Remove branding
});
```

#### Export Settings

**Resolution Options**:
- **Standard (1x)**: 72 DPI, web use
- **High (2x)**: 144 DPI, presentations (default)
- **Print (3x)**: 216 DPI, professional printing

**Background Options**:
- **Transparent**: For overlays (default)
- **White**: For documents
- **Match Theme**: Use current light/dark background

**Include Options**:
- Chart title
- Legend
- Axis labels
- Timestamp
- Source attribution

#### Use Cases

**1. Weekly Reports**:
```
Export: Records Over Time (PNG, 2x)
Usage: Embed in stakeholder email
Benefit: Visual progress update
```

**2. Presentations**:
```
Export: All charts (PDF, 3x)
Usage: Slide deck
Benefit: Professional quality, scalable
```

**3. Data Analysis**:
```
Export: Comparison table (CSV)
Usage: Excel pivot tables
Benefit: Further statistical analysis
```

**4. Documentation**:
```
Export: Architecture diagram (PNG, 2x, white background)
Usage: README.md or docs
Benefit: Explain pipeline visually
```

---

### Date Range Filtering

**Purpose**: Focus dashboard on specific time periods for trend analysis or incident investigation.

#### Preset Ranges

**Quick Select**:
```
○ Last 7 Days     - Recent activity monitoring
○ Last 30 Days    - Monthly overview (default)
○ Last 90 Days    - Quarterly trends
○ Year to Date    - Annual progress
○ All Time        - Complete history
● Custom Range    - Specific dates
```

#### Custom Range Selection

**Step-by-Step**:
```
1. Click "Date Range" dropdown
2. Select "Custom Range"
3. Start Date Picker:
   - Click calendar icon
   - Navigate to month
   - Select start date
4. End Date Picker:
   - Select end date (must be after start)
5. Click "Apply"
6. All charts update with filtered data
```

**Date Input Formats**:
```
Valid:
  2025-10-01        (ISO format)
  10/01/2025        (US format)
  01-10-2025        (EU format)
  October 1, 2025   (Natural language)

Invalid:
  10/1/25           (Two-digit year ambiguous)
  2025/31/10        (Invalid day)
```

#### Use Cases

**1. Incident Investigation**:
```
Scenario: Quality drop reported on Oct 15
Action: Set range Oct 10-20
Analysis: Identify exact run that caused drop
Result: Found filter config change on Oct 14
```

**2. Before/After Comparison**:
```
Scenario: New filter deployed Oct 1
Before: Set range Sep 1-30
After: Set range Oct 1-30
Analysis: Compare quality pass rates
Result: +12% improvement confirmed
```

**3. Monthly Reporting**:
```
Scenario: Generate October report
Action: Set range Oct 1-31
Export: All charts with October data only
Result: Clean monthly summary
```

**4. Trend Analysis**:
```
Scenario: Long-term quality trends
Action: Set range Jan 1 - Oct 27 (YTD)
Analysis: Plot quality rates over months
Result: Identify seasonal patterns
```

#### Advanced Filtering

**Combine with Other Filters**:
```
Date Range: Last 30 days
     AND
Source: BBC, HuggingFace
     AND
Pipeline Type: web_scraping

Result: Web scraping performance last month for news sources
```

#### Performance Considerations

- Filtering happens client-side (instant)
- Large date ranges may slow chart rendering
- Recommendation: Use < 90 days for best performance
- All-time view cached for faster subsequent loads

---

### Advanced Filters

**Purpose**: Drill down into specific subsets of pipeline data using multiple filter dimensions.

#### Available Filters

**1. Source Filter**:
```
□ Wikipedia (Somali)
□ BBC Somali
□ HuggingFace (mC4-so)
□ Språkbanken

Behavior: Show only selected sources (OR logic)
```

**2. Pipeline Type Filter**:
```
□ File Processing
□ Web Scraping
□ Stream Processing

Behavior: Show only selected types (OR logic)
```

**3. Success Rate Range**:
```
Minimum: [____] % (0-100)
Maximum: [____] % (0-100)

Behavior: Inclusive range filter
Example: 80-100 shows only high-success runs
```

**4. Quality Threshold**:
```
Minimum Quality Pass Rate: [____] %

Behavior: Exclude runs below threshold
Example: 70% shows only acceptable+ quality
```

**5. Record Volume Range**:
```
Minimum Records: [______]
Maximum Records: [______]

Behavior: Filter by run size
Example: 1000-10000 excludes small test runs
```

**6. Date Range** (see previous section)

#### Filter Combinations

**Scenario 1: Identify Problematic Web Scraping Runs**:
```
Filters Applied:
  ✓ Pipeline Type: Web Scraping
  ✓ Success Rate Range: 0-70%
  ✓ Date Range: Last 30 days

Results: 3 runs found
  - BBC (Oct 5): 45% success - HTTP 404 errors
  - BBC (Oct 12): 58% success - Rate limiting
  - BBC (Oct 19): 67% success - Partial outage

Action: Review error logs, implement retry logic
```

**Scenario 2: Find High-Quality File Processing**:
```
Filters Applied:
  ✓ Pipeline Type: File Processing
  ✓ Quality Threshold: 80%
  ✓ Source: Wikipedia, Språkbanken

Results: All Språkbanken runs (91.8% avg quality)
Analysis: Use as benchmark for Wikipedia optimization
```

**Scenario 3: Large Dataset Runs**:
```
Filters Applied:
  ✓ Record Volume: 10,000+
  ✓ Date Range: All Time

Results: 8 runs (all HuggingFace stream processing)
Insight: Only HF provides large batches
Recommendation: Increase batch sizes for other sources
```

#### Filter UI

**Sidebar Panel**:
```
┌─────────────────────────────┐
│ FILTERS                     │
├─────────────────────────────┤
│ Sources                     │
│  ☑ Wikipedia               │
│  ☑ BBC                     │
│  ☐ HuggingFace             │
│  ☑ Språkbanken             │
├─────────────────────────────┤
│ Pipeline Type               │
│  ☑ File Processing         │
│  ☑ Web Scraping            │
│  ☐ Stream Processing       │
├─────────────────────────────┤
│ Success Rate                │
│  Min: [80] Max: [100]      │
├─────────────────────────────┤
│ [Apply Filters] [Reset]    │
└─────────────────────────────┘
```

**Filter State Indicator**:
```
Active Filters (3):
  📊 Sources: Wikipedia, BBC, Språkbanken
  📈 Success Rate: 80-100%
  📅 Date: Last 30 Days

[Clear All Filters]
```

#### Performance Tips

- **Client-Side Filtering**: Instant updates
- **Progressive Loading**: Filters applied incrementally
- **Cached Results**: Re-applying same filter is instant
- **Reset Button**: Quickly remove all filters

---

### Comparison Mode

**Purpose**: Compare metrics between different pipeline runs to track improvements, investigate regressions, or analyze A/B tests.

#### Activation

**Method 1: UI Button**:
```
1. Click "Compare Runs" in navigation
2. Comparison panel appears
3. Select runs to compare
```

**Method 2: Keyboard Shortcut**:
```
Press: Ctrl + Shift + C
```

#### Selecting Runs to Compare

**Run Selector**:
```
Select Pipeline Runs (2-4 recommended):

□ 20251027_143000_wikipedia ● Oct 27, 14:30 | 9,623 records | 63.6% quality
□ 20251020_091500_wikipedia   Oct 20, 09:15 | 9,000 records | 58.2% quality
□ 20251015_162000_wikipedia   Oct 15, 16:20 | 8,750 records | 55.8% quality
□ 20251010_103000_wikipedia   Oct 10, 10:30 | 8,500 records | 52.4% quality

[Compare Selected] [Cancel]
```

**Selection Strategies**:
```
Time Series:
  Select runs at regular intervals
  Example: Oct 1, Oct 10, Oct 20, Oct 27
  Use Case: Track gradual improvements

Before/After:
  Select runs before and after a change
  Example: Before filter update, After filter update
  Use Case: Measure impact of changes

A/B Testing:
  Select runs with different configurations
  Example: min_length=50 vs min_length=100
  Use Case: Optimize parameters
```

#### Comparison Views

**Side-by-Side Table**:
```
Metric               Run 1 (Oct 27)   Run 2 (Oct 20)   Delta      % Change
──────────────────────────────────────────────────────────────────────────
Records Collected    9,623            9,000            +623       +6.9%
Quality Pass Rate    63.6%            58.2%            +5.4pp     +9.3%
Success Rate         95.2%            94.1%            +1.1pp     +1.2%
Dedup Rate           0.0%             2.5%             -2.5pp     -100.0%
Duration             36.5s            42.8s            -6.3s      -14.7%
Throughput           263 rec/s        210 rec/s        +53 rec/s  +25.2%

Legend:
  ↑ Green: Improvement
  ↓ Red: Regression
  ─ Gray: No significant change (< 5%)
```

**Delta Visualization**:
```
Quality Pass Rate Trend

60% ├─────○─────────────●───┤
    │     │             │   │
55% ├─────┼─────○───────┼───┤
    │     │     │       │   │
50% ├─────┼─────┼───○───┼───┤
    │     │     │   │   │   │
    Oct 10   Oct 15  Oct 20  Oct 27

Improvement: +11.2 percentage points over 17 days
Rate of Change: +0.66 pp/day
Projection: 70% target reached by Nov 5
```

**Improvement/Regression Summary**:
```
Improvements Detected (4):
  ✓ Quality Pass Rate: +5.4pp (+9.3%)
  ✓ Records Collected: +623 (+6.9%)
  ✓ Throughput: +53 rec/s (+25.2%)
  ✓ Duration: -6.3s (-14.7% faster)

Regressions Detected (1):
  ✗ Deduplication Rate: -2.5pp (-100%)
    Note: Expected for first run vs incremental run

Stable Metrics (2):
  ─ Success Rate: 95.2% → 95.2% (±0%)
  ─ HTTP Request Success: 100% → 100% (±0%)
```

#### Use Cases

**1. Track Filter Optimization**:
```
Context: Lowered min_length threshold from 500 → 300 chars

Comparison:
  Before (min_length=500): 58.2% quality, 9,000 records
  After (min_length=300): 63.6% quality, 9,623 records

Analysis:
  Quality: +5.4pp improvement
  Volume: +623 records (+6.9%)
  Conclusion: Threshold change successful

Action: Keep new threshold
```

**2. Investigate Regression**:
```
Context: Quality dropped suddenly

Comparison:
  Oct 15 (baseline): 58% quality, 15 min duration
  Oct 20 (problem): 45% quality, 18 min duration

Analysis:
  Quality: -13pp regression
  Duration: +3 min slower
  Filter breakdown: langid_filter rejecting 35% (was 20%)

Root Cause: langid model updated, higher confidence threshold
Action: Revert langid model or adjust confidence
```

**3. A/B Testing**:
```
Context: Test two deduplication strategies

Run A (hash-based): 92% quality, 8,500 records, 30s
Run B (fuzzy matching): 95% quality, 8,200 records, 180s

Analysis:
  Quality: +3pp with fuzzy matching
  Volume: -300 records (-3.5%)
  Speed: 6x slower

Trade-off: Better quality vs performance
Decision: Use hash-based for batch, fuzzy for critical data
```

---

## Configuration Options

See [Dashboard Configuration Guide](dashboard-configuration.md) for detailed customization options.

**Quick Reference**:
- Chart colors and themes
- Filter defaults
- Export settings
- Date range presets
- Performance thresholds
- Comparison baselines

---

## Troubleshooting

### Common Issues

**Q: Advanced features not appearing**

**A**: Possible causes:
1. Browser cache outdated → Hard refresh (Ctrl+Shift+R)
2. JavaScript disabled → Enable in browser settings
3. Old dashboard version → Check for updates
4. Feature flag disabled → Contact administrator

**Q: Sankey diagram shows incorrect flow**

**A**: Debug steps:
1. Open browser console (F12)
2. Check for errors related to D3.js
3. Verify metrics data has `layered_metrics` structure
4. Ensure conservation of flow: sum(inputs) = sum(outputs)

**Q: Comparison mode shows "No runs found"**

**A**: Ensure:
1. Multiple runs exist for the selected source
2. Runs have complete metrics data
3. Date range includes the runs
4. No filters excluding all runs

**Q: Export PNG is blurry**

**A**: Increase resolution:
1. Edit export settings
2. Set resolution to 3x (print quality)
3. Re-export chart

### Performance Issues

**Q: Dashboard loads slowly**

**A**: Optimization tips:
1. Use date range filter to limit data
2. Clear browser cache
3. Limit comparison to 2-3 runs
4. Disable ridge plots temporarily (resource-intensive)

**Q: Filters lag when applied**

**A**: Reduce data volume:
1. Set date range to last 30 days
2. Select specific sources only
3. Increase quality threshold to filter out low-quality runs

---

## Best Practices

### 1. Regular Monitoring

**Daily Check**:
- Review hero metrics
- Check source health indicators
- Scan bullet charts for red zones
- Note any comparison mode alerts

**Weekly Deep Dive**:
- Compare last week's runs
- Review Sankey diagrams for bottlenecks
- Analyze ridge plots for distribution changes
- Export charts for weekly report

### 2. Data Analysis Workflow

**Step 1: Overview** (5 min)
```
1. Check all-time metrics
2. Review source comparison table
3. Identify outliers
```

**Step 2: Drill Down** (15 min)
```
1. Apply filters to focus on issues
2. Use comparison mode to understand changes
3. Review Sankey diagrams for problem areas
```

**Step 3: Root Cause** (30 min)
```
1. Examine ridge plots for distribution shifts
2. Review quality reports for details
3. Check error logs
4. Formulate hypothesis
```

**Step 4: Action** (varies)
```
1. Adjust filter thresholds
2. Fix pipeline bugs
3. Update documentation
4. Schedule follow-up comparison
```

### 3. Sharing Insights

**For Stakeholders**:
```
Export: Bullet charts (PNG)
Why: Clear KPI status
How: High-res with white background
```

**For Engineers**:
```
Export: Sankey diagrams + Comparison tables (PDF)
Why: Technical details
How: Include timestamps and metadata
```

**For Analysts**:
```
Export: Ridge plots + raw data (CSV)
Why: Further statistical analysis
How: Include distribution stats
```

### 4. Comparison Guidelines

**Don't Compare**:
- Runs from different sources
- Test runs with production runs
- Partial runs with complete runs
- Pre-v3.0 metrics with post-v3.0 metrics

**Do Compare**:
- Same source, different dates
- Before/after configuration changes
- Similar-sized runs
- Runs with same pipeline type

### 5. Filter Best Practices

**Progressive Filtering**:
```
Start broad → Narrow down
1. Date range: Last 90 days
2. Check trends
3. Add source filter
4. Add quality threshold
5. Analyze subset
```

**Save Common Filters**:
```
Bookmark URLs with filter parameters:
https://...dashboard.html?source=bbc&dateRange=30d&quality=80

Create dashboard presets:
- "High Quality Runs"
- "Problematic Runs"
- "Large Datasets"
```

### 6. Export Organization

**File Naming Convention**:
```
{chart_type}_{source}_{date_range}_{timestamp}.{ext}

Examples:
  sankey_wikipedia_2025-10-27_143022.png
  comparison_all-sources_last-30d_143022.pdf
  ridgeplot_text-length_all-time_143022.csv
```

**Archive Strategy**:
```
Monthly:
  Create folder: exports/2025-10/
  Export all charts
  Include README with context

Quarterly:
  Comparison reports
  Trend analysis
  Stakeholder summaries
```

---

## Related Documentation

- [Dashboard User Guide](dashboard-user-guide.md) - Basic usage and interpretation
- [Dashboard Technical Guide](dashboard-technical.md) - Architecture and implementation
- [Dashboard Configuration Guide](dashboard-configuration.md) - Customization options
- [Dashboard Performance Guide](dashboard-performance.md) - Optimization tips
- [Dashboard Accessibility Guide](dashboard-accessibility.md) - WCAG compliance

---

**Last Updated**: 2025-10-27
**Version**: 3.1.0
**Maintainers**: Somali NLP Contributors
