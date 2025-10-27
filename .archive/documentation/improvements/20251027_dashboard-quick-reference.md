# Dashboard Quick Reference

**One-page reference for common dashboard tasks and features.**

**Version**: 3.1.0 | **Last Updated**: 2025-10-27

---

## Quick Access

| Resource | URL |
|----------|-----|
| **Live Dashboard** | `https://YOUR-USERNAME.github.io/somali-dialect-classifier/` |
| **Local Dev** | `http://localhost:8000/_site/` |
| **Metrics Data** | `data/metrics/*.json` |
| **Quality Reports** | `data/reports/*.md` |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+E` | Export current view |
| `Ctrl+F` | Open filters panel |
| `Ctrl+R` | Refresh dashboard data |
| `Ctrl+Shift+D` | Toggle dark mode |
| `Ctrl+Shift+C` | Open comparison mode |
| `Alt+1` to `Alt+6` | Jump to main sections |
| `?` | Show all shortcuts |
| `Esc` | Close modals/cancel |

---

## Common Tasks

### Daily Health Check (2 min)
```
1. Check hero metrics (top of page)
2. Verify all sources show green status
3. Confirm recent activity (< 24 hours)
4. Review success rate trend
```

### Investigate Low Quality (15 min)
```
1. Navigate to source-specific metrics
2. Check filter breakdown
3. Review quality report
4. Compare with historical baseline
5. Identify dominant filter
6. Examine sample rejected records
```

### Export Charts for Report (5 min)
```
1. Hover over chart
2. Click "Export PNG"
3. Image downloads automatically
4. Rename: [chart_type]_[date].png
5. Insert into report/presentation
```

### Compare Pipeline Runs (10 min)
```
1. Click "Compare Runs" button
2. Select 2-4 runs from list
3. Review side-by-side metrics
4. Analyze delta (absolute & percentage)
5. Identify improvements/regressions
6. Export comparison table
```

### Apply Filters (3 min)
```
1. Click "Filters" in sidebar
2. Select criteria:
   - Sources
   - Pipeline types
   - Date range
   - Quality threshold
3. Click "Apply Filters"
4. View filtered results
5. Click "Reset" to clear
```

---

## Metric Cheat Sheet

### Quality Metrics

| Metric | Formula | Good Value | Meaning |
|--------|---------|------------|---------|
| **Success Rate** | `successful / attempted` | > 90% | Pipeline reliability |
| **Quality Pass Rate** | `passed_filters / total_records` | 50-90%* | Data quality |
| **Deduplication Rate** | `duplicates / total` | 20-80%** | Content redundancy |
| **Throughput** | `records / minute` | 1000+ | Processing speed |

*Varies by source | **Higher on incremental runs

### Pipeline Type Semantics

| Type | Success Metric | Description |
|------|---------------|-------------|
| **Web Scraping** | HTTP Request Success | Network-level (2xx responses) |
| **File Processing** | File Extraction Success | File I/O success rate |
| **Stream Processing** | Stream Connection Success | API connectivity |

---

## Status Indicators

### Health Colors

| Color | Status | Success Rate | Action |
|-------|--------|--------------|--------|
| 🟢 **Green** | Healthy | > 90% | None needed |
| 🟡 **Yellow** | Degraded | 70-90% | Monitor closely |
| 🔴 **Red** | Critical | < 70% | Investigate immediately |

### Filter Rejection Rates

| Filter | Typical Rate | High Rate Indicates |
|--------|--------------|---------------------|
| `min_length_filter` | 30-70% | Many short texts (stubs) |
| `langid_filter` | 10-25% | Language contamination |
| `empty_after_cleaning` | 1-5% | Low source quality |
| `namespace_filter` | 20-40% | Wikipedia-specific |

---

## Chart Types

### Records Over Time (Line Chart)
- **What**: Cumulative records collected
- **Use**: Track growth trends
- **Look For**: Flat lines (stale sources), steep slopes (high activity)

### Success Rate Trends (Area Chart)
- **What**: Quality metrics over time
- **Use**: Monitor pipeline health
- **Look For**: Declining trends, sudden drops

### Filter Impact (Stacked Bar)
- **What**: Records removed by each filter
- **Use**: Understand quality bottlenecks
- **Look For**: Dominant filters, unusual patterns

### Source Comparison (Horizontal Bar)
- **What**: Side-by-side source metrics
- **Use**: Rank sources, identify outliers
- **Look For**: Imbalanced data collection

### Performance Bullet (Bullet Chart)
- **What**: Actual vs target performance
- **Use**: KPI tracking, quick assessment
- **Look For**: Red zones, targets missed

### Data Flow (Sankey Diagram)
- **What**: Pipeline flow visualization
- **Use**: Identify bottlenecks
- **Look For**: Wide rejection flows

### Distribution (Ridge Plot)
- **What**: Metric distributions across sources
- **Use**: Compare patterns, detect outliers
- **Look For**: Shifted peaks, unusual shapes

---

## Troubleshooting

### Dashboard Not Loading
```
1. Check URL is correct
2. Hard refresh: Ctrl+Shift+R
3. Clear browser cache
4. Check browser console (F12) for errors
5. Verify GitHub Actions workflow passed
```

### Charts Not Rendering
```
1. Verify data files exist: _site/data/all_metrics.json
2. Check browser console for JS errors
3. Ensure Chart.js loaded (check Network tab)
4. Try different browser
```

### Source Showing Red Status
```
1. Navigate to data/reports/
2. Find latest report for that source
3. Review "Recommendations" section
4. Check error logs in logs/
5. Review recent code changes
```

### Success Rate Dropped
```
Common Causes:
  - Source website changed (web scraping)
  - API rate limits hit (streaming)
  - Network issues
  - Filter thresholds changed
  - Source content quality degraded

Action:
  1. Check quality report for details
  2. Review error distribution
  3. Compare with previous runs
  4. Check pipeline logs
```

### No Data Available
```
Possible Causes:
  1. No pipeline runs yet → Run a pipeline
  2. Metrics not committed → Check git status
  3. GitHub Actions not completed → Check workflow
  4. Browser cache issue → Hard refresh
```

---

## Data Source Characteristics

| Source | Volume | Quality Pass Rate | Update Frequency | Characteristics |
|--------|--------|-------------------|------------------|-----------------|
| **Wikipedia** | 9,600+ | 50-70% | Weekly | Many stubs, encyclopedic |
| **BBC** | 4,250+ | 70-90% | Daily | News articles, consistent length |
| **HuggingFace** | 50,000+ | 60-80% | One-time | Web corpus, varied quality |
| **Språkbanken** | 1,450+ | 80-95% | Quarterly | Curated, high quality |

---

## Export Formats

| Format | Status | Use Case | Quality |
|--------|--------|----------|---------|
| **PNG** | ✅ Implemented | Presentations, emails | 2x resolution |
| **PDF** | 🚧 Planned | Reports, printing | Vector (scalable) |
| **CSV** | 🚧 Planned | Data analysis | Raw numbers |
| **SVG** | 🚧 Planned | Web, graphics | Vector |

---

## Filter Combinations (Examples)

### Find Problematic Runs
```
Filters:
  ✓ Success Rate: 0-70%
  ✓ Date Range: Last 30 days

Use: Identify runs needing investigation
```

### High-Quality Datasets
```
Filters:
  ✓ Quality Threshold: 80%
  ✓ Record Volume: 1000+

Use: Find best training data
```

### Web Scraping Performance
```
Filters:
  ✓ Pipeline Type: web_scraping
  ✓ Source: BBC
  ✓ Date Range: Last 90 days

Use: Analyze scraping trends
```

---

## CLI Commands

### Generate Dashboard
```bash
# Aggregate metrics
python scripts/export_dashboard_data.py

# Build static site
cd dashboard && bash build-site.sh

# Serve locally
python -m http.server 8000 --directory _site
```

### Run Pipeline
```bash
# Single source
python -m somali_dialect_classifier.cli.download_wikisom --max-articles 100

# All sources
somali-orchestrate --pipeline all
```

### Deploy Dashboard
```bash
# Manual deployment
somali-deploy-dashboard --source wikipedia --auto-push

# Or commit metrics and let GitHub Actions deploy
git add data/metrics/*.json
git commit -m "chore(metrics): update metrics for wikipedia"
git push origin main
```

---

## URLs & Paths

### Local Development
```
Dashboard:     _site/index.html
Metrics:       data/metrics/*.json
Reports:       data/reports/*.md
Logs:          logs/*.log
Config:        configs/*.yaml
```

### Production
```
Dashboard:     https://YOUR-USERNAME.github.io/somali-dialect-classifier/
GitHub Repo:   https://github.com/YOUR-USERNAME/somali-dialect-classifier
Actions:       https://github.com/YOUR-USERNAME/somali-dialect-classifier/actions
```

---

## Contact & Support

### Documentation
- **User Guide**: [docs/guides/dashboard-user-guide.md](guides/dashboard-user-guide.md)
- **Technical Guide**: [docs/guides/dashboard-technical.md](guides/dashboard-technical.md)
- **Advanced Features**: [docs/guides/dashboard-advanced-features.md](guides/dashboard-advanced-features.md)
- **Developer Onboarding**: [docs/guides/dashboard-developer-onboarding.md](guides/dashboard-developer-onboarding.md)

### Getting Help
- **Questions**: Open GitHub Discussion
- **Bugs**: Open issue with `dashboard` label
- **Features**: Open issue with `enhancement` label

---

## Version History

| Version | Date | Major Changes |
|---------|------|---------------|
| **3.1.0** | 2025-10-27 | Advanced features (Sankey, Ridge, Bullet, Comparison) |
| **3.0.0** | 2025-10-27 | Tableau redesign, dark mode, layered metrics |
| **2.1.0** | 2025-10-26 | Pipeline-specific metrics, semantic accuracy |
| **2.0.0** | 2025-10-20 | Automated deployment, CI/CD integration |
| **1.0.0** | 2025-10-15 | Initial release |

---

**Print this page for easy reference at your desk!**
