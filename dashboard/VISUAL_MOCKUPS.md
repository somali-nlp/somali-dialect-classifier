# Visual Mockups & Design Specifications

**Project:** Somali NLP Dialect Classifier Dashboard
**Document Type:** Visual Reference Guide
**Status:** Design Reference

---

## Overview

This document provides ASCII-based visual mockups and detailed design specifications for each visualization. Use these as reference during implementation to ensure consistency with the intended design.

---

## Chart 1: Source Contribution Bar Chart

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Data Source Contribution                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HuggingFace-MC4    ▓ 48 (0.3%)                                │
│                                                                  │
│  BBC-Somali         ▓ 49 (0.4%)                                │
│                                                                  │
│  Språkbanken        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 4,015 (29.2%)          │
│                                                                  │
│  Wikipedia-Somali   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    │
│                     9,623 (70.1%)                               │
│                                                                  │
│                     ├─────┬─────┬─────┬─────┬─────┬─────┤      │
│                     0    2K    4K    6K    8K   10K             │
│                             Number of Records                   │
└─────────────────────────────────────────────────────────────────┘
```

### Color Mapping

```
Wikipedia-Somali   ████  Blue    #4477AA  (70.1% - Dominant)
Språkbanken        ████  Yellow  #CCBB44  (29.2% - Secondary)
BBC-Somali         ████  Red     #EE6677  (0.4% - Quality source)
HuggingFace-MC4    ████  Green   #228833  (0.3% - External data)
```

### Design Details

- **Bar Height:** 48px each, 12px gap
- **Border Radius:** 8px (rounded corners)
- **Border Width:** 2px solid (same color as fill)
- **Opacity:** 85% fill, 100% border
- **Font Size:** 14px for labels, 12px for percentages
- **Bar Order:** Ascending (smallest to largest)
- **Data Labels:** Inside bar (right-aligned) if width > 100px, else outside

### Interaction States

```
Normal:     ████████████ opacity: 0.85
Hover:      ████████████ opacity: 1.0, border: 3px, shadow: 0 4px 12px
Active:     ████████████ scale: 1.02, shadow: 0 6px 16px
Focus:      ████████████ outline: 3px solid #2563EB (keyboard focus)
```

### Tooltip Content

```
┌──────────────────────────┐
│ Wikipedia-Somali         │
├──────────────────────────┤
│ Records: 9,623           │
│ Percentage: 70.1%        │
│ Rank: 1 of 4             │
└──────────────────────────┘
```

---

## Chart 2: Pipeline Funnel Chart

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline Processing Funnel                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Items Discovered   ████████████████████████████ 10,687 (100%) │
│                                                                  │
│  Items Processed    ████████████████████████████ 10,687 (100%) │
│                                                                  │
│  Records Written    ████████████████████████████████████        │
│                     13,735 (128%)                               │
│                                                                  │
│                     ├─────┬──────┬──────┬──────┬──────┤         │
│                     0    5K    10K    15K    20K                │
│                                 Count                            │
│                                                                  │
│  Legend: ███ Processed  ▒▒▒ Dropped                            │
└─────────────────────────────────────────────────────────────────┘
```

### Stacked Bar Representation

```
Stage 1 (Discovered):  [████████████████████████] (10,687)
Stage 2 (Processed):   [████████████████████████] (10,687) [no drop]
Stage 3 (Written):     [████████████████████████████] (13,735)
                       └─ Processed ─┘└─ Added ─┘

Note: Stage 3 > Stage 2 due to file processing that creates
      multiple records per source file
```

### Color Scheme

```
Processed:  Green    #228833  opacity: 0.8
Dropped:    Red      #EE6677  opacity: 0.3
Background: Grey     #F3F4F6
```

### Annotations

```
Between Stage 1 → 2:  "100% conversion"
Between Stage 2 → 3:  "128% expansion" (file processing creates more records)
```

### Tooltip Content

```
┌──────────────────────────┐
│ Items Processed          │
├──────────────────────────┤
│ Processed: 10,687        │
│ Conversion: 100%         │
│ Drop-off: 0%             │
└──────────────────────────┘
```

---

## Chart 3: Quality Metrics Radar Chart

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Source Quality Metrics Comparison                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        Success Rate (100%)                      │
│                               ▲                                  │
│                              / \                                 │
│                             /   \                                │
│                            /     \                               │
│          Consistency      /       \      Text Quality            │
│            (100%) ◄──────┼─────────┼──────► (0-90%)            │
│                          /         \                             │
│                         /     ✱     \                            │
│                        /    (center)  \                          │
│                       /                 \                        │
│            Throughput/                   \Coverage               │
│            (0-100%) /                     \ (0-70%)              │
│                   ▼                         ▼                    │
│                                                                  │
│  Legend:  ──── Wikipedia  ······ BBC  ─ ─ HuggingFace  ─── Språkbanken │
└─────────────────────────────────────────────────────────────────┘
```

### Axis Configuration

```
5 Axes (Pentagon shape):
1. Success Rate (top)           - 0-100%, higher = better
2. Text Quality (top-right)     - 0-100%, higher = better
3. Coverage (bottom-right)      - 0-100%, higher = better
4. Throughput (bottom-left)     - 0-100%, higher = better
5. Consistency (top-left)       - 0-100%, higher = better
```

### Data Point Examples

```
Wikipedia-Somali:
  Success Rate: 100  ●━━━━━━━━━━● (outer ring)
  Text Quality:  66  ●━━━━━━●     (mid ring)
  Throughput:    95  ●━━━━━━━━━● (near outer)
  Coverage:      70  ●━━━━━━━━●   (mid-outer)
  Consistency:  100  ●━━━━━━━━━━● (outer ring)

BBC-Somali:
  Success Rate:  98  ●━━━━━━━━━● (near outer)
  Text Quality:  74  ●━━━━━━━●   (mid-outer)
  Throughput:     3  ●            (very low)
  Coverage:     0.4  ●            (very low)
  Consistency:  100  ●━━━━━━━━━━● (outer ring)
```

### Color & Fill

```
Wikipedia:     Blue     #4477AA  fill: rgba(68,119,170,0.15)  line: 2px
BBC:           Red      #EE6677  fill: rgba(238,102,119,0.15) line: 2px
HuggingFace:   Green    #228833  fill: rgba(34,136,51,0.15)   line: 2px
Språkbanken:   Yellow   #CCBB44  fill: rgba(204,187,68,0.15)  line: 2px
```

### Grid Lines

```
Circular grids at: 20%, 40%, 60%, 80%, 100%
Color: rgba(0, 0, 0, 0.08)
Width: 1px
```

### Tooltip Content

```
┌──────────────────────────────┐
│ Wikipedia-Somali             │
├──────────────────────────────┤
│ Success Rate: 100            │
│ → 100% of requests succeeded │
│                              │
│ Text Quality: 66             │
│ → Avg 3960 characters/record │
└──────────────────────────────┘
```

---

## Chart 4: Processing Timeline

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Cumulative Records Collection Timeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 14K │                                        ┌────────────       │
│     │                                   ┌────┘                   │
│ 12K │                                   │                        │
│     │                              ┌────┘                        │
│ 10K │              ┌───────────────┘                             │
│  8K │              │                                             │
│  6K │              │                                             │
│  4K │        ┌─────┘                                             │
│  2K │   ┌────┘                                                   │
│   0 └───┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴    │
│     11:36  11:40  11:50  12:00  12:10  12:20  12:30 (time)     │
│                                                                  │
│  Legend: ████ Wikipedia  ████ BBC  ████ HuggingFace  ████ Språkbanken │
└─────────────────────────────────────────────────────────────────┘
```

### Area Fill Pattern

```
Top Layer:    Språkbanken   (Yellow)   │▒▒▒▒│
Mid-Top:      BBC           (Red)      │░░░░│
Mid-Bottom:   HuggingFace   (Green)    │▓▓▓▓│
Bottom:       Wikipedia     (Blue)     │████│
```

### Key Moments

```
11:36:13  ●  Wikipedia starts (0 → 9,623 in 17 seconds)
11:36:41  ●  BBC starts (parallel processing)
11:37:04  ●  HuggingFace starts
11:38:33  ●  Språkbanken starts
12:26:44  ●  All complete (BBC finishes last - 50 minutes)
```

### Time Axis

```
Format: HH:mm
Intervals: 5 minutes
Rotation: 0° (horizontal labels)
Grid: Vertical lines every 10 minutes
```

### Y-Axis

```
Format: Abbreviated (K, M)
Intervals: Auto (Chart.js calculates)
Grid: Horizontal lines
Begin at Zero: true
```

### Crosshair

```
Vertical line follows cursor:
  Color: #374151
  Width: 1px
  Style: Dashed [5px dash, 5px gap]

Tooltip shows all sources at that time point
```

### Zoom Controls

```
Zoom: Ctrl+Scroll or Pinch
Pan: Click-drag or Touch-swipe
Reset: Press 'R' key or double-click
```

---

## Chart 5: Performance KPI Cards

### Grid Layout

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│              │              │              │              │
│ Total Records│ Success Rate │ Avg Text Len │ Throughput   │
│              │              │              │              │
│    13,735    │    82.7%     │  2,979 chars │  259 rec/s   │
│   ┌────┐     │   ┌────┐     │   ┌────┐     │   ┌────┐     │
│   │ ╱╲ │     │   │╲  ╱│     │   │╲  ╱│     │   │╲   │     │
│   │╱  ╲│     │   │ ╲╱ │     │   │ ╲╱ │     │   │ ╲  │     │
│   └────┘     │   └────┘     │   └────┘     │   └────┘     │
│  +42% ↑      │  -15.6% ↓    │  -33% ↓      │  -70.9% ↓    │
│  Target: 15K │  Target: 95% │  Target: 4K  │  Target: 500 │
│  Progress:   │  Progress:   │  Progress:   │  Progress:   │
│  ██████░░ 91%│  ████░░░ 87% │  ███░░░ 74%  │  ██░░░ 51%   │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### Individual Card Anatomy

```
┌────────────────────────┐
│ METRIC NAME      +42%↑ │ ← Header (status color bar on left)
├────────────────────────┤
│                        │
│      13,735           │ ← Large value (2rem, bold)
│                        │
│   ┌────────────┐       │ ← Sparkline (30px height)
│   │  ╱╲  ╱╲ ╱  │       │
│   └────────────┘       │
│                        │
│ Target: 15,000   91.6% │ ← Footer (target & progress)
└────────────────────────┘
```

### Status Color Coding

```
Good (Green border):
  ┃  Total Records: 13,735
  ┃  (Green #10B981 - 4px left border)

Warning (Orange border):
  ┃  Success Rate: 82.7%
  ┃  (Orange #F59E0B - 4px left border)

Critical (Red border):
  ┃  Throughput: 259 rec/s
  ┃  (Red #EF4444 - 4px left border)
```

### Change Indicator

```
Positive (up):    +42% ↑  background: #D1FAE5  color: #065F46
Negative (down):  -15.6% ↓ background: #FEE2E2  color: #991B1B
Neutral:           0%     background: #F3F4F6  color: #6B7280
```

### Sparkline Mini-Chart

```
Trend visualization (last 5 runs):

Upward trend:     ╱╲  ╱╲ ╱
Downward trend:  ╲  ╲╱  ╲╱
Stable:          ─────────
Volatile:        ╱╲╱╲╱╲╱╲
```

### Progress Bar

```
High (> 85%):  ████████░░  Green  #10B981
Mid (50-85%):  █████░░░░░  Yellow #CCBB44
Low (< 50%):   ██░░░░░░░░  Red    #EF4444
```

---

## Responsive Breakpoints

### Desktop (> 1024px)

```
Source Contribution:   Height: 400px, Width: 100%
Pipeline Funnel:       Height: 350px, Width: 100%
Quality Radar:         Height: 450px, Width: 100% (square aspect)
Processing Timeline:   Height: 400px, Width: 100%
KPI Cards:             Grid: 4 columns, Gap: 20px
```

### Tablet (768px - 1024px)

```
Source Contribution:   Height: 350px, Width: 100%
Pipeline Funnel:       Height: 300px, Width: 100%
Quality Radar:         Height: 400px, Width: 100%
Processing Timeline:   Height: 350px, Width: 100%
KPI Cards:             Grid: 2 columns, Gap: 16px
```

### Mobile (< 768px)

```
Source Contribution:   Height: 300px, Width: 100%, Labels abbreviated
Pipeline Funnel:       Height: 280px, Width: 100%, Vertical layout
Quality Radar:         Height: 320px, Width: 100%, Legend stacked
Processing Timeline:   Height: 280px, Width: 100%, Labels rotated 45°
KPI Cards:             Grid: 1 column, Gap: 12px, Compact spacing
```

---

## Typography Scale

```
Chart Titles:          18px, weight: 600, color: #111827
Axis Labels:           13px, weight: 500, color: #374151
Axis Ticks:            11px, weight: 400, color: #6B7280
Tooltip Headers:       14px, weight: 600, color: #111827
Tooltip Body:          13px, weight: 400, color: #4B5563
Data Labels:           12px, weight: 600, color: #111827
Legend Labels:         12px, weight: 400, color: #374151
Card Values:           32px (2rem), weight: 700, color: #111827
Card Labels:           14px (0.875rem), weight: 500, color: #6B7280
Card Change:           12px (0.75rem), weight: 600
```

---

## Spacing System

```
Chart Padding:         32px (desktop), 24px (tablet), 16px (mobile)
Section Margins:       40px (desktop), 32px (tablet), 24px (mobile)
Card Padding:          20px (desktop), 16px (tablet), 12px (mobile)
Grid Gap:              20px (desktop), 16px (tablet), 12px (mobile)
Element Spacing:       12px (standard), 8px (tight), 16px (loose)
```

---

## Shadow & Elevation

```
Level 0 (Flat):        box-shadow: none
Level 1 (Cards):       box-shadow: 0 1px 3px rgba(0,0,0,0.1)
Level 2 (Hover):       box-shadow: 0 4px 12px rgba(0,0,0,0.15)
Level 3 (Active):      box-shadow: 0 6px 16px rgba(0,0,0,0.2)
Level 4 (Modal):       box-shadow: 0 20px 40px rgba(0,0,0,0.3)
```

---

## Animation Timings

```
Fast:    150ms  (button clicks, checkbox toggles)
Normal:  250ms  (card hover, tooltip show/hide)
Slow:    400ms  (chart data transitions, modal open)
Easing:  cubic-bezier(0.4, 0, 0.2, 1)  (standard Material Design)
```

---

## Accessibility Visual Indicators

### Keyboard Focus

```
Standard:  outline: 3px solid #2563EB, offset: 2px
Error:     outline: 3px solid #EF4444, offset: 2px
Success:   outline: 3px solid #10B981, offset: 2px
```

### Hover States

```
Chart Elements:   opacity: 1.0, border-width: +1px
Buttons:          background: darken(10%), scale: 1.02
Links:            text-decoration: underline, color: #1E40AF
```

### Loading States

```
Skeleton:    background: linear-gradient(90deg,
               #F3F4F6 25%,
               #E5E7EB 50%,
               #F3F4F6 75%)
             animation: shimmer 2s infinite

Spinner:     color: #2563EB
             size: 40px
             stroke: 4px
```

---

## Print Styles

```css
@media print {
  /* Remove interactive elements */
  .chart-controls { display: none; }

  /* Expand charts to full width */
  .chart-canvas { height: 300px !important; }

  /* High contrast colors */
  body { background: white; color: black; }

  /* Page breaks */
  .chart-section { page-break-inside: avoid; }

  /* Remove shadows */
  * { box-shadow: none !important; }
}
```

---

## Dark Mode (Future Enhancement)

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #111827;
    --bg-secondary: #1F2937;
    --text-primary: #F9FAFB;
    --text-secondary: #D1D5DB;
    --border-color: #374151;
  }

  /* Adjust chart colors */
  .chart-canvas {
    filter: invert(0.9) hue-rotate(180deg);
  }

  /* Keep original colors */
  .chart-canvas canvas {
    filter: invert(1) hue-rotate(180deg);
  }
}
```

---

## Icon Library (Optional Enhancement)

```
Success:   ✓  (U+2713)
Warning:   ⚠  (U+26A0)
Error:     ✗  (U+2717)
Info:      ℹ  (U+2139)
Trending Up:   ↑  (U+2191)
Trending Down: ↓  (U+2193)
Neutral:   →  (U+2192)
```

---

## Footer Specifications

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│              Somali Dialect Classifier Dashboard                │
│              Data Ingestion Phase | Last Updated: Oct 25, 2025  │
│                                                                  │
│  Background: #F9FAFB                                            │
│  Text: #6B7280, 14px                                            │
│  Padding: 40px vertical, 20px horizontal                        │
│  Border-top: 1px solid #E5E7EB                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

Use this checklist while implementing each visualization:

### Source Contribution Chart
- [ ] Horizontal bars render correctly
- [ ] Bars sorted ascending (smallest to largest)
- [ ] Colors match SourceColors mapping
- [ ] Percentages display on bars
- [ ] Tooltip shows record count, percentage, rank
- [ ] Border radius is 8px
- [ ] Border width is 2px
- [ ] Hover increases opacity to 100%
- [ ] Click announces to screen reader
- [ ] Mobile: min height 280px
- [ ] Mobile: labels truncate if needed

### Pipeline Funnel Chart
- [ ] Stages display in correct order
- [ ] Stacked bars show processed + dropped
- [ ] Green for processed, light red for dropped
- [ ] Conversion rates annotate between stages
- [ ] Tooltip shows conversion percentages
- [ ] Legend displays correctly
- [ ] Mobile: switches to vertical layout
- [ ] Handles edge case where stage 3 > stage 2

### Quality Radar Chart
- [ ] Pentagon shape (5 axes)
- [ ] All sources render as filled areas
- [ ] Colors use 15% opacity fill
- [ ] Border lines are 2px
- [ ] Circular grid at 20% intervals
- [ ] Axis labels don't overlap
- [ ] Legend allows toggling sources
- [ ] Tooltip shows metric + explanation
- [ ] Mobile: legend stacks vertically
- [ ] Data normalized 0-100 scale

### Processing Timeline
- [ ] Time-series x-axis renders correctly
- [ ] Stacked areas show cumulative growth
- [ ] Colors match SourceColors
- [ ] Crosshair plugin active
- [ ] Zoom enabled (Ctrl+scroll)
- [ ] Pan enabled (click-drag)
- [ ] Reset zoom on 'R' key
- [ ] Tooltip shows all sources at time point
- [ ] Mobile: pinch-zoom works
- [ ] Mobile: time format abbreviated

### Performance KPI Cards
- [ ] Grid layout responsive
- [ ] Status color bar on left (4px)
- [ ] Large value displays (2rem, bold)
- [ ] Sparkline renders mini trend
- [ ] Change indicator shows % and direction
- [ ] Progress bar shows target completion
- [ ] Hover elevates card with shadow
- [ ] Mobile: 1 column layout
- [ ] Mobile: values scale to 1.5rem

---

**End of Visual Mockups Document**

Use this document alongside `VISUALIZATION_SPECIFICATIONS.md` for complete implementation guidance.
