# Dashboard Visualization Recommendations

Based on the analysis of 13,395 records from 4 data sources, here are the recommended dashboard improvements.

---

## Current Data Overview

```
Total Records: 13,395
Total Sources: 4 (Wikipedia, Sprakbanken, HuggingFace, BBC)
Total Characters: ~2.97 million
Success Rate: 100%
Active Issues: 6 (4 critical, 2 warnings)
```

---

## Recommended Dashboard Layout

### Section 1: Overview Cards (Top Row)

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  Total Records  │  Active Sources │  Success Rate   │  Data Volume    │
│                 │                 │                 │                 │
│     13,395      │      4/4        │      100%       │    2.97 MB      │
│   ↑ +1,234      │      ✅         │       ✅        │   ↑ +0.3 MB     │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

**Implementation:**
- Use large, bold numbers
- Show trend indicators (up/down arrows with delta)
- Color-code status: Green ≥95%, Yellow 80-95%, Red <80%

### Section 2: Source Distribution (Left Column)

#### Visualization 1: Source Contribution Bar Chart

```
Wikipedia-Somali     █████████████████████████████████████ 69.6% (9,329)
Sprakbanken-Somali   ███████████████ 30.0% (4,015)
HuggingFace-Somali   ▌ 0.4% (48)
BBC-Somali           ▌ 0.0% (3)
                     0%    25%    50%    75%    100%
```

**Features:**
- Interactive: click to filter other charts
- Hover: show exact counts and percentages
- Color-coded by source
- Sort option: by count or alphabetically

**Priority:** ⭐⭐⭐ Essential

#### Visualization 2: Source Status Table

```
┌────────────────────┬──────────┬─────────────────────┬────────┐
│ Source             │ Records  │ Last Run            │ Status │
├────────────────────┼──────────┼─────────────────────┼────────┤
│ Wikipedia-Somali   │  9,329   │ 2025-10-20 11:13:42 │   ✅   │
│ Sprakbanken-Somali │  4,015   │ 2025-10-20 11:15:50 │   ✅   │
│ HuggingFace-Somali │    48    │ 2025-10-20 11:20:15 │   ✅   │
│ BBC-Somali         │     3    │ 2025-10-20 11:16:46 │   ⚠️   │
└────────────────────┴──────────┴─────────────────────┴────────┘
```

**Priority:** ⭐⭐⭐ Essential

### Section 3: Document Length Analysis (Center)

#### Visualization 3: Length Distribution Histogram (Log Scale)

```
    │
500 │ ┌──┐
400 │ │██│
300 │ │██│  ┌──┐
200 │ │██│  │██│  ┌──┐
100 │ │██│  │██│  │██│  ┌──┐        ┌──┐
  0 │ └──┴──┴──┴──┴──┴──┴──┴────────┴──┴────────────────
      10   100  1K   10K  100K
            Characters (log scale)

Legend: █ Wikipedia  █ Sprakbanken  █ HuggingFace  █ BBC
```

**Features:**
- Log scale X-axis (handles 1 to 122,020 char range)
- Stacked or overlaid bars by source
- Hover: show bin range and count
- Toggle: linear vs log scale

**Priority:** ⭐⭐⭐ Essential

#### Visualization 4: Box Plot by Source

```
Wikipedia     ├────[======█======]──────────────────────┤
              10   580  2521                       122020

Sprakbanken   ├─[█]┤
              1  85 132  925

HuggingFace   ├──────────────[======█======]──────────┤
              500          6229               15000

BBC           ├──────────[███]────┤
              100       4844    10000
              │         │         │
            100        1K        10K       100K
                  Characters (log scale)

Legend: [====] = IQR, █ = median, ├─┤ = whiskers
```

**Features:**
- Shows median, quartiles, outliers
- Clearly displays variance differences
- Interactive: hover for exact values

**Priority:** ⭐⭐ Important

### Section 4: Data Quality (Right Column)

#### Visualization 5: Quality Scorecard

```
┌─────────────────────────────────────────────────────┐
│              DATA QUALITY SCORECARD                 │
├─────────────────┬──────────┬────────────────────────┤
│ Metric          │ Value    │ Status                 │
├─────────────────┼──────────┼────────────────────────┤
│ Success Rate    │  100.0%  │ ✅ Excellent           │
│ Dedup Rate      │   0.0%   │ ❌ Not Functioning     │
│ Avg Length      │  1,445   │ ⚠️  High Variance      │
│ Filter Rate     │   8.6%   │ ✅ Acceptable          │
│ Min Length      │      1   │ ❌ Too Short           │
│ Max Length      │ 122,020  │ ⚠️  Very Long          │
└─────────────────┴──────────┴────────────────────────┘
```

**Priority:** ⭐⭐⭐ Essential

#### Visualization 6: Issues Summary

```
┌─────────────────────────────────────────────────────┐
│            ACTIVE QUALITY ISSUES (6)                │
├──────────┬──────────────────────────────────────────┤
│ CRITICAL │ Deduplication not functioning (4 sources)│
│ WARNING  │ Ultra-short documents (22 docs < 10 chr) │
│ WARNING  │ High filter rate (22.3% in Sprakbanken) │
└──────────┴──────────────────────────────────────────┘

[View Details] [Resolve All]
```

**Priority:** ⭐⭐⭐ Essential

### Section 5: Processing Performance (Bottom)

#### Visualization 7: Throughput Comparison

```
                Records per Minute
Sprakbanken   ████████████████████████ 63,015
Wikipedia     ████████████████ 40,495
HuggingFace   ██████ 15,000
BBC           ████ 10,000
              0     20K    40K    60K
```

**Priority:** ⭐ Nice to have

#### Visualization 8: Pipeline Funnel

```
Wikipedia Pipeline:
Discovered → Fetched → Extracted → Filtered → Written
    1         1          728        728       9,329
    │         │           │          │          │
    └─────────┴───────────┴──────────┴──────────┘
                      +1181% expansion

Sprakbanken Pipeline:
Discovered → Fetched → Extracted → Filtered → Written
    1         1         5,165       3,015      4,015
    │         │           │          │          │
    └─────────┴───────────┴──────────┴──────────┘
                      -22.3% filtering
```

**Priority:** ⭐⭐ Important

### Section 6: Advanced Analytics (Collapsible)

#### Visualization 9: Length Distribution Table

```
┌────────────────┬───────┬─────────┬─────────┬────────┐
│ Length Range   │ Count │ Percent │ Avg Len │ Source │
├────────────────┼───────┼─────────┼─────────┼────────┤
│ Very Short     │    70 │   3.4%  │      8  │  Mixed │
│ (<20 chars)    │       │         │         │        │
├────────────────┼───────┼─────────┼─────────┼────────┤
│ Short          │   833 │  40.6%  │     52  │  Sprak │
│ (20-100)       │       │         │         │        │
├────────────────┼───────┼─────────┼─────────┼────────┤
│ Medium         │   700 │  34.1%  │    385  │  Wiki  │
│ (100-1000)     │       │         │         │        │
├────────────────┼───────┼─────────┼─────────┼────────┤
│ Long           │   394 │  19.2%  │  3,245  │  Wiki  │
│ (1K-10K)       │       │         │         │        │
├────────────────┼───────┼─────────┼─────────┼────────┤
│ Very Long      │    56 │   2.7%  │ 28,450  │  Wiki  │
│ (10K+)         │       │         │         │        │
└────────────────┴───────┴─────────┴─────────┴────────┘
```

**Priority:** ⭐ Nice to have

#### Visualization 10: Time Series (Cumulative)

```
    │
14K │                                              ●
12K │                                         ●
10K │                                    ●
 8K │                               ●
 6K │                          ●
 4K │                     ●
 2K │                ●
  0 │───────────────────────────────────────────────
    11:13      11:15      11:16      11:20
           Run timestamps (2025-10-20)

● Wikipedia  ● Sprakbanken  ● BBC  ● HuggingFace
```

**Priority:** ⭐ Nice to have

---

## Interactive Features

### Filters
- [ ] Source selector (multi-select)
- [ ] Date range picker
- [ ] Length range slider
- [ ] Status filter (complete/incomplete/error)

### Export Options
- [ ] Export current view as PNG
- [ ] Download data as CSV
- [ ] Generate PDF report
- [ ] Copy metrics to clipboard

### Real-Time Updates
- [ ] Auto-refresh every 5 minutes
- [ ] WebSocket updates on new data
- [ ] Progress bar for active pipelines
- [ ] Notification on pipeline completion

---

## New Metrics to Display

### Priority 1 (Add Immediately)

1. **Filter Reasons Breakdown**
   ```json
   {
     "too_short": 50,
     "non_somali": 30,
     "duplicate": 20,
     "encoding_error": 10
   }
   ```

2. **Language Distribution**
   ```json
   {
     "somali": 12500,
     "english": 200,
     "mixed": 100,
     "other": 50
   }
   ```

3. **Deduplication Details**
   ```json
   {
     "unique": 12000,
     "exact_duplicates": 800,
     "near_duplicates": 200,
     "rate": 0.074
   }
   ```

### Priority 2 (Add Next Month)

4. **Vocabulary Statistics**
   ```json
   {
     "unique_words": 15000,
     "total_words": 400000,
     "type_token_ratio": 0.0375,
     "avg_word_length": 6.2
   }
   ```

5. **Content Type Distribution**
   ```json
   {
     "article": 728,
     "paragraph": 8601,
     "sentence": 4015,
     "fragment": 51
   }
   ```

6. **Dialect Indicators** (Project-Specific)
   ```json
   {
     "northern": 8000,
     "southern": 3000,
     "unknown": 2395
   }
   ```

---

## Dashboard Technology Recommendations

### Frontend Framework
**Recommended:** React + Recharts or D3.js
- Recharts: Simple, responsive, good for standard charts
- D3.js: Full control, custom visualizations
- Alternative: Plotly.js (if Python backend)

### Data Refresh Strategy
1. **Static Mode:** Generate dashboard from JSON exports (current)
2. **Polling Mode:** Auto-refresh every N minutes
3. **Live Mode:** WebSocket updates from pipeline

**Recommended:** Start with Static (Phase 1), add Polling (Phase 2), consider Live (Phase 3)

### Responsive Design
```
Desktop (>1200px):  3-column layout
Tablet (768-1200):  2-column layout
Mobile (<768px):    1-column, stacked cards
```

---

## Implementation Priority

### Phase 1: Core Dashboard (Week 1)
1. ✅ Overview cards (total records, sources, success rate)
2. ✅ Source contribution bar chart
3. ✅ Quality scorecard
4. ✅ Issues summary

### Phase 2: Analytics (Week 2)
5. ⭐ Length distribution histogram
6. ⭐ Box plot by source
7. ⭐ Source status table
8. ⭐ Pipeline funnel

### Phase 3: Advanced (Week 3-4)
9. 🔧 Throughput comparison
10. 🔧 Time series
11. 🔧 Length distribution table
12. 🔧 Interactive filters

---

## Sample Code Snippets

### Visualization 1: Source Contribution (Recharts)

```javascript
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const data = [
  { source: 'Wikipedia', records: 9329, percentage: 69.6 },
  { source: 'Sprakbanken', records: 4015, percentage: 30.0 },
  { source: 'HuggingFace', records: 48, percentage: 0.4 },
  { source: 'BBC', records: 3, percentage: 0.0 }
];

<BarChart data={data}>
  <XAxis dataKey="source" />
  <YAxis />
  <Tooltip />
  <Bar dataKey="records" fill="#8884d8" />
</BarChart>
```

### Visualization 3: Length Distribution (D3.js concept)

```javascript
// Bin data into logarithmic buckets
const bins = [10, 100, 1000, 10000, 100000];
const histogram = d3.histogram()
  .domain([1, 122020])
  .thresholds(bins);

// Create grouped histogram by source
const histData = sources.map(source => ({
  source: source.name,
  bins: histogram(source.text_lengths)
}));
```

### Visualization 5: Quality Scorecard (React)

```javascript
const QualityCard = ({ metric, value, threshold, status }) => (
  <div className={`metric-card ${status}`}>
    <div className="metric-name">{metric}</div>
    <div className="metric-value">{value}</div>
    <div className="metric-status">{status === 'good' ? '✅' : '❌'}</div>
  </div>
);
```

---

## Data File Structure

The dashboard should read from:

```
/data/analysis/
  ├── metrics_analysis_latest.json      # Auto-generated, always current
  ├── metrics_analysis_YYYYMMDD.json    # Historical snapshots
  └── dashboard_cache.json              # Optimized for dashboard

/data/metrics/
  ├── RUNID_source_phase.json           # Individual run metrics
  └── ...
```

**Recommendation:** Create a `dashboard_cache.json` that pre-aggregates common queries for faster loading.

---

## Testing Checklist

Dashboard should be tested for:
- [ ] Loads within 2 seconds
- [ ] Responsive on mobile devices
- [ ] All charts render correctly
- [ ] Interactive filters work
- [ ] Export functions work
- [ ] Auto-refresh doesn't freeze UI
- [ ] Handles empty/missing data gracefully
- [ ] Works offline (static mode)
- [ ] Accessible (WCAG 2.1 AA)
- [ ] Cross-browser compatible

---

## Success Metrics for Dashboard

The dashboard is successful if it enables:

1. **Quick Health Check:** Can see overall status in <5 seconds
2. **Issue Identification:** Critical issues are visible immediately
3. **Trend Analysis:** Can see data growth over time
4. **Source Comparison:** Easy to compare source quality
5. **Actionable Insights:** Clear what to do next

**Target:** Team should check dashboard daily and take action on issues within 24 hours.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-20
**Next Review:** 2025-10-27
