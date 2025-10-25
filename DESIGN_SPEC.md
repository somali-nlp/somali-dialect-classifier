# Somali NLP Dialect Classifier - Design Specification
**GitHub Pages Website Design System & Implementation Guide**

Version: 1.0.0
Date: October 25, 2025
Status: Ready for Implementation

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Color System](#color-system)
3. [Typography System](#typography-system)
4. [Spacing & Layout Grid](#spacing--layout-grid)
5. [Component Library](#component-library)
6. [Page Layouts](#page-layouts)
7. [Interaction Patterns](#interaction-patterns)
8. [Accessibility Standards](#accessibility-standards)
9. [Responsive Breakpoints](#responsive-breakpoints)
10. [CSS Architecture](#css-architecture)
11. [Implementation Checklist](#implementation-checklist)

---

## Design Philosophy

### Core Principles

**1. Research-First, Human-Centered**
- Balance technical depth with accessibility for non-technical audiences
- Progressive disclosure: Surface key insights first, detailed metrics on demand
- Data storytelling over raw numbers

**2. Accessibility as Foundation**
- WCAG 2.1 AA compliance (minimum)
- Keyboard navigation throughout
- Screen reader optimized
- Colorblind-safe palette (already using Paul Tol's palette)
- Reduced motion support

**3. Modern Minimalism**
- Clean, spacious layouts inspired by Linear and Stripe
- Generous white space (breathing room)
- Typography-driven hierarchy
- Purposeful animation (never decorative)

**4. Performance-First**
- Fast loading (< 2s on 3G)
- Progressive enhancement
- Optimized assets
- No framework dependencies (vanilla JS + Chart.js only)

---

## Color System

### Brand Palette

```css
:root {
  /* Primary - Blue (Research/Science) */
  --color-primary-50:  #EFF6FF;
  --color-primary-100: #DBEAFE;
  --color-primary-200: #BFDBFE;
  --color-primary-300: #93C5FD;
  --color-primary-400: #60A5FA;
  --color-primary-500: #3B82F6;  /* Primary brand */
  --color-primary-600: #2563EB;  /* Hover states */
  --color-primary-700: #1D4ED8;  /* Active states */
  --color-primary-800: #1E40AF;
  --color-primary-900: #1E3A8A;

  /* Secondary - Indigo (Accent) */
  --color-secondary-50:  #EEF2FF;
  --color-secondary-100: #E0E7FF;
  --color-secondary-500: #6366F1;
  --color-secondary-600: #4F46E5;

  /* Success - Green (Data validated) */
  --color-success-50:  #F0FDF4;
  --color-success-100: #DCFCE7;
  --color-success-500: #22C55E;
  --color-success-600: #16A34A;
  --color-success-700: #15803D;

  /* Warning - Amber (Processing) */
  --color-warning-50:  #FFFBEB;
  --color-warning-100: #FEF3C7;
  --color-warning-500: #F59E0B;
  --color-warning-600: #D97706;

  /* Error - Red (Failed) */
  --color-error-50:  #FEF2F2;
  --color-error-100: #FEE2E2;
  --color-error-500: #EF4444;
  --color-error-600: #DC2626;

  /* Neutral - Gray (UI foundation) */
  --color-gray-50:  #F9FAFB;
  --color-gray-100: #F3F4F6;
  --color-gray-200: #E5E7EB;
  --color-gray-300: #D1D5DB;
  --color-gray-400: #9CA3AF;
  --color-gray-500: #6B7280;
  --color-gray-600: #4B5563;
  --color-gray-700: #374151;
  --color-gray-800: #1F2937;
  --color-gray-900: #111827;

  /* Semantic Colors */
  --color-text-primary:   var(--color-gray-900);
  --color-text-secondary: var(--color-gray-600);
  --color-text-tertiary:  var(--color-gray-500);
  --color-text-inverse:   #FFFFFF;

  --color-bg-primary:   #FFFFFF;
  --color-bg-secondary: var(--color-gray-50);
  --color-bg-tertiary:  var(--color-gray-100);

  --color-border-light: var(--color-gray-200);
  --color-border-medium: var(--color-gray-300);
  --color-border-heavy: var(--color-gray-400);
}
```

### Dark Mode Palette

```css
@media (prefers-color-scheme: dark) {
  :root {
    /* Inverted semantic colors */
    --color-text-primary:   #F9FAFB;
    --color-text-secondary: #D1D5DB;
    --color-text-tertiary:  #9CA3AF;
    --color-text-inverse:   #111827;

    --color-bg-primary:   #111827;
    --color-bg-secondary: #1F2937;
    --color-bg-tertiary:  #374151;

    --color-border-light:  #374151;
    --color-border-medium: #4B5563;
    --color-border-heavy:  #6B7280;

    /* Adjusted primary for dark mode (higher contrast) */
    --color-primary-500: #60A5FA;
    --color-primary-600: #3B82F6;
  }
}
```

### Color Usage Guidelines

| Element | Light Mode | Dark Mode | Purpose |
|---------|------------|-----------|---------|
| Background | `#FFFFFF` | `#111827` | Primary surface |
| Cards/Panels | `#FFFFFF` + shadow | `#1F2937` | Elevated surfaces |
| Borders | `#E5E7EB` | `#374151` | Separators |
| Text (Primary) | `#111827` | `#F9FAFB` | Headlines, body |
| Text (Secondary) | `#6B7280` | `#D1D5DB` | Supporting text |
| Links | `#2563EB` | `#60A5FA` | Interactive text |
| CTAs (Primary) | `#3B82F6` | `#3B82F6` | Main actions |
| CTAs (Secondary) | `#F3F4F6` + `#374151` text | `#374151` + `#F9FAFB` text | Secondary actions |

**Accessibility Requirements:**
- All text must meet WCAG AA contrast ratio (4.5:1 minimum for body, 3:1 for large text)
- Interactive elements must have 3:1 contrast against background
- Focus states must have 3:1 contrast against adjacent colors

---

## Typography System

### Font Families

```css
:root {
  /* Primary Font - Body & UI */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
               'Roboto', 'Helvetica Neue', Arial, sans-serif;

  /* Code & Data */
  --font-mono: 'Fira Code', 'SF Mono', 'Monaco', 'Cascadia Code',
               'Roboto Mono', 'Courier New', monospace;

  /* Headings (Optional: Inter with tighter tracking) */
  --font-display: 'Inter', var(--font-sans);
}
```

**Font Loading Strategy:**
```html
<!-- Preconnect for performance -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<!-- Load only necessary weights -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
```

### Type Scale

Modular scale with 1.25 ratio (Major Third) for harmony:

```css
:root {
  /* Font Sizes */
  --text-xs:   0.75rem;   /* 12px */
  --text-sm:   0.875rem;  /* 14px */
  --text-base: 1rem;      /* 16px - base size */
  --text-lg:   1.125rem;  /* 18px */
  --text-xl:   1.25rem;   /* 20px */
  --text-2xl:  1.5rem;    /* 24px */
  --text-3xl:  1.875rem;  /* 30px */
  --text-4xl:  2.25rem;   /* 36px */
  --text-5xl:  3rem;      /* 48px */
  --text-6xl:  3.75rem;   /* 60px */
  --text-7xl:  4.5rem;    /* 72px */

  /* Line Heights */
  --leading-none:   1;
  --leading-tight:  1.25;
  --leading-snug:   1.375;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
  --leading-loose:  2;

  /* Letter Spacing */
  --tracking-tighter: -0.05em;
  --tracking-tight:   -0.025em;
  --tracking-normal:  0;
  --tracking-wide:    0.025em;
  --tracking-wider:   0.05em;
  --tracking-widest:  0.1em;

  /* Font Weights */
  --font-normal:    400;
  --font-medium:    500;
  --font-semibold:  600;
  --font-bold:      700;
}
```

### Typography Hierarchy

```css
/* Display - Hero headlines */
.text-display-1 {
  font-family: var(--font-display);
  font-size: var(--text-6xl);      /* 60px */
  font-weight: var(--font-bold);
  line-height: var(--leading-none);
  letter-spacing: var(--tracking-tighter);
  color: var(--color-text-primary);
}

@media (max-width: 768px) {
  .text-display-1 {
    font-size: var(--text-4xl);    /* 36px on mobile */
  }
}

/* Headings */
.text-h1 {
  font-family: var(--font-display);
  font-size: var(--text-4xl);      /* 36px */
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
  color: var(--color-text-primary);
}

.text-h2 {
  font-family: var(--font-display);
  font-size: var(--text-3xl);      /* 30px */
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
  color: var(--color-text-primary);
}

.text-h3 {
  font-family: var(--font-display);
  font-size: var(--text-2xl);      /* 24px */
  font-weight: var(--font-semibold);
  line-height: var(--leading-snug);
  color: var(--color-text-primary);
}

.text-h4 {
  font-family: var(--font-sans);
  font-size: var(--text-xl);       /* 20px */
  font-weight: var(--font-semibold);
  line-height: var(--leading-snug);
  color: var(--color-text-primary);
}

/* Body Text */
.text-body-lg {
  font-family: var(--font-sans);
  font-size: var(--text-lg);       /* 18px */
  font-weight: var(--font-normal);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);
}

.text-body {
  font-family: var(--font-sans);
  font-size: var(--text-base);     /* 16px */
  font-weight: var(--font-normal);
  line-height: var(--leading-normal);
  color: var(--color-text-primary);
}

.text-body-sm {
  font-family: var(--font-sans);
  font-size: var(--text-sm);       /* 14px */
  font-weight: var(--font-normal);
  line-height: var(--leading-normal);
  color: var(--color-text-secondary);
}

/* Labels & UI */
.text-label {
  font-family: var(--font-sans);
  font-size: var(--text-sm);       /* 14px */
  font-weight: var(--font-medium);
  line-height: var(--leading-snug);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

/* Code */
.text-code {
  font-family: var(--font-mono);
  font-size: 0.9em;                /* Relative to parent */
  font-weight: var(--font-normal);
  background: var(--color-bg-tertiary);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  color: var(--color-text-primary);
}
```

### Responsive Typography

**Base Size**: 16px (never smaller for accessibility)

**Scaling Strategy**: Fluid typography using clamp()

```css
.text-fluid-display {
  font-size: clamp(2.25rem, 4vw + 1rem, 4.5rem);
  /* Min 36px, scales with viewport, max 72px */
}

.text-fluid-h1 {
  font-size: clamp(1.875rem, 3vw + 0.5rem, 3rem);
  /* Min 30px, scales with viewport, max 48px */
}

.text-fluid-h2 {
  font-size: clamp(1.5rem, 2vw + 0.5rem, 2.25rem);
  /* Min 24px, scales with viewport, max 36px */
}
```

---

## Spacing & Layout Grid

### Spacing Scale

8px base unit for consistency (divisible by 2 and 4):

```css
:root {
  --space-0:   0;
  --space-1:   0.25rem;  /* 4px */
  --space-2:   0.5rem;   /* 8px */
  --space-3:   0.75rem;  /* 12px */
  --space-4:   1rem;     /* 16px */
  --space-5:   1.25rem;  /* 20px */
  --space-6:   1.5rem;   /* 24px */
  --space-8:   2rem;     /* 32px */
  --space-10:  2.5rem;   /* 40px */
  --space-12:  3rem;     /* 48px */
  --space-16:  4rem;     /* 64px */
  --space-20:  5rem;     /* 80px */
  --space-24:  6rem;     /* 96px */
  --space-32:  8rem;     /* 128px */
  --space-40:  10rem;    /* 160px */
  --space-48:  12rem;    /* 192px */
  --space-56:  14rem;    /* 224px */
  --space-64:  16rem;    /* 256px */
}
```

### Container Widths

```css
:root {
  --container-sm:  640px;   /* Small content */
  --container-md:  768px;   /* Medium content */
  --container-lg:  1024px;  /* Large content */
  --container-xl:  1280px;  /* Extra large */
  --container-2xl: 1536px;  /* Maximum width */

  /* Content widths for readability */
  --content-prose: 65ch;    /* Optimal reading width */
  --content-narrow: 50ch;   /* Narrow content */
  --content-wide: 80ch;     /* Wide content */
}
```

### Grid System

**12-column grid** for flexible layouts:

```css
.grid-12 {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--space-6);
}

/* Common Patterns */
.grid-2-col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-6);
}

.grid-3-col {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-6);
}

.grid-4-col {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-6);
}

/* Responsive */
@media (max-width: 1024px) {
  .grid-4-col {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .grid-2-col,
  .grid-3-col,
  .grid-4-col {
    grid-template-columns: 1fr;
  }
}
```

### Layout Sections

```css
/* Vertical Rhythm */
.section {
  padding-top: var(--space-16);    /* 64px */
  padding-bottom: var(--space-16);
}

.section-lg {
  padding-top: var(--space-24);    /* 96px */
  padding-bottom: var(--space-24);
}

.section-xl {
  padding-top: var(--space-32);    /* 128px */
  padding-bottom: var(--space-32);
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .section {
    padding-top: var(--space-12);
    padding-bottom: var(--space-12);
  }

  .section-lg {
    padding-top: var(--space-16);
    padding-bottom: var(--space-16);
  }

  .section-xl {
    padding-top: var(--space-20);
    padding-bottom: var(--space-20);
  }
}
```

---

## Component Library

### 1. Navigation Header

**Description**: Fixed/sticky navigation with smooth transitions

**Specifications**:
- Height: 64px (80px on desktop)
- Background: Semi-transparent with backdrop blur
- Shadow on scroll: subtle elevation
- Sticky behavior with transform animation

```css
.nav-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  height: 64px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px) saturate(180%);
  border-bottom: 1px solid var(--color-border-light);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-header.scrolled {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
              0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.nav-container {
  max-width: var(--container-2xl);
  margin: 0 auto;
  padding: 0 var(--space-6);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-logo {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  text-decoration: none;
  letter-spacing: var(--tracking-tight);
}

.nav-links {
  display: flex;
  gap: var(--space-8);
  align-items: center;
}

.nav-link {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  text-decoration: none;
  padding: var(--space-2) var(--space-3);
  border-radius: 0.375rem;
  transition: all 0.2s ease;
  position: relative;
}

.nav-link:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.nav-link:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* Active link indicator */
.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-primary-600);
}

/* Mobile menu toggle */
.nav-menu-toggle {
  display: none;
  width: 40px;
  height: 40px;
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-2);
}

@media (max-width: 768px) {
  .nav-header {
    height: 56px;
  }

  .nav-menu-toggle {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
  }

  .nav-menu-toggle span {
    display: block;
    width: 24px;
    height: 2px;
    background: var(--color-text-primary);
    transition: all 0.3s ease;
  }

  .nav-links {
    position: fixed;
    top: 56px;
    left: 0;
    right: 0;
    background: var(--color-bg-primary);
    flex-direction: column;
    gap: 0;
    padding: var(--space-4);
    border-bottom: 1px solid var(--color-border-light);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    transform: translateY(-100%);
    opacity: 0;
    pointer-events: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .nav-links.open {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
  }

  .nav-link {
    width: 100%;
    padding: var(--space-3) var(--space-4);
  }
}
```

### 2. Hero Section

**Description**: Full-width hero with gradient background, headline, and CTA

**Layout**:
```
┌─────────────────────────────────────────┐
│                                         │
│          [Project Title]                │
│      [Tagline/Description]              │
│                                         │
│     [Primary CTA] [Secondary CTA]       │
│                                         │
│           [Scroll Hint]                 │
└─────────────────────────────────────────┘
```

**Specifications**:
- Height: 100vh (minimum 600px, maximum 900px)
- Background: Subtle gradient with pattern overlay
- Content: Centered, max-width 800px
- Animation: Fade-up on load

```css
.hero {
  position: relative;
  min-height: 600px;
  max-height: 900px;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg,
    var(--color-primary-600) 0%,
    var(--color-secondary-600) 100%);
  overflow: hidden;
}

/* Optional: Animated gradient background */
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity: 0.3;
  animation: pattern-drift 60s linear infinite;
}

@keyframes pattern-drift {
  0% { transform: translate(0, 0); }
  100% { transform: translate(60px, 60px); }
}

.hero-content {
  position: relative;
  z-index: 10;
  max-width: 800px;
  padding: 0 var(--space-6);
  text-align: center;
  color: white;
  animation: fade-up 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.hero-title {
  font-size: clamp(2.5rem, 5vw, 4.5rem);
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tighter);
  margin-bottom: var(--space-6);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.hero-subtitle {
  font-size: clamp(1.125rem, 2vw, 1.5rem);
  font-weight: var(--font-normal);
  line-height: var(--leading-relaxed);
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: var(--space-10);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.hero-cta {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  flex-wrap: wrap;
}

.hero-scroll-hint {
  position: absolute;
  bottom: var(--space-8);
  left: 50%;
  transform: translateX(-50%);
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(-10px); }
}

.hero-scroll-hint svg {
  width: 24px;
  height: 24px;
  color: rgba(255, 255, 255, 0.7);
}

@media (max-width: 768px) {
  .hero {
    min-height: 500px;
  }

  .hero-cta {
    flex-direction: column;
    align-items: center;
  }

  .hero-cta .btn {
    width: 100%;
    max-width: 300px;
  }
}
```

### 3. Metric Cards

**Description**: Dashboard-style cards displaying key metrics

**Layout**: 4-column grid (responsive to 2-column on tablet, 1-column on mobile)

**Card Anatomy**:
```
┌──────────────────────┐
│ [Icon]               │
│ [Large Number]       │
│ [Label]              │
│ [Trend/Change]       │
└──────────────────────┘
```

**Specifications**:
- Border-radius: 12px
- Padding: 24px
- Shadow: Subtle, increases on hover
- Border: 1px solid --color-border-light

```css
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-6);
  margin-bottom: var(--space-16);
}

.metric-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  padding: var(--space-6);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.metric-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg,
    var(--color-primary-500),
    var(--color-secondary-500));
  transform: translateX(-100%);
  transition: transform 0.3s ease;
}

.metric-card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
              0 4px 6px -2px rgba(0, 0, 0, 0.05);
  transform: translateY(-2px);
  border-color: var(--color-primary-200);
}

.metric-card:hover::before {
  transform: translateX(0);
}

.metric-icon {
  width: 48px;
  height: 48px;
  background: var(--color-primary-50);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
  color: var(--color-primary-600);
}

.metric-value {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  line-height: var(--leading-none);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
  font-variant-numeric: tabular-nums;
}

.metric-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  margin-bottom: var(--space-3);
}

.metric-change {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: var(--space-1) var(--space-2);
  border-radius: 9999px;
}

.metric-change.positive {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.metric-change.negative {
  background: var(--color-error-50);
  color: var(--color-error-700);
}

@media (max-width: 1024px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .metrics-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .metric-card {
    padding: var(--space-5);
  }

  .metric-value {
    font-size: var(--text-3xl);
  }
}
```

### 4. Chart Container

**Description**: Wrapper for Chart.js visualizations with consistent styling

**Specifications**:
- Background: White card with border
- Padding: 32px
- Border-radius: 16px
- Title: Above chart, left-aligned
- Description: Optional, below title

```css
.chart-section {
  margin-bottom: var(--space-16);
}

.chart-header {
  margin-bottom: var(--space-6);
}

.chart-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.chart-description {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
  max-width: 60ch;
}

.chart-wrapper {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 16px;
  padding: var(--space-8);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s ease;
}

.chart-wrapper:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.chart-canvas-container {
  position: relative;
  height: 400px;
  margin-bottom: var(--space-4);
}

@media (max-width: 768px) {
  .chart-wrapper {
    padding: var(--space-4);
    border-radius: 12px;
  }

  .chart-canvas-container {
    height: 300px;
  }
}
```

### 5. Buttons (CTAs)

**Primary Button**:
```css
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  line-height: 1;
  text-decoration: none;
  color: white;
  background: var(--color-primary-600);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.btn-primary:hover {
  background: var(--color-primary-700);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: translateY(0);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.btn-primary:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}
```

**Secondary Button**:
```css
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  line-height: 1;
  text-decoration: none;
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-secondary:hover {
  background: var(--color-bg-secondary);
  border-color: var(--color-border-heavy);
  transform: translateY(-1px);
}

.btn-secondary:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}
```

**Ghost Button**:
```css
.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  line-height: 1;
  text-decoration: none;
  color: var(--color-text-primary);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-ghost:hover {
  background: var(--color-bg-secondary);
}

.btn-ghost:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}
```

**Button Sizes**:
```css
.btn-sm {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
}

.btn-lg {
  padding: var(--space-4) var(--space-8);
  font-size: var(--text-lg);
}
```

### 6. Source Comparison Section

**Layout**: Side-by-side comparison or tabbed interface

```css
.source-comparison {
  background: var(--color-bg-secondary);
  border-radius: 16px;
  padding: var(--space-8);
  margin-bottom: var(--space-16);
}

.source-tabs {
  display: flex;
  gap: var(--space-2);
  border-bottom: 2px solid var(--color-border-light);
  margin-bottom: var(--space-8);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.source-tab {
  padding: var(--space-3) var(--space-5);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  position: relative;
  margin-bottom: -2px;
}

.source-tab:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-tertiary);
}

.source-tab.active {
  color: var(--color-primary-600);
  border-bottom-color: var(--color-primary-600);
}

.source-tab:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: -2px;
}

.source-content {
  display: none;
}

.source-content.active {
  display: block;
  animation: fade-in 0.3s ease;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

### 7. Footer

**Specifications**:
- Background: Dark or light depending on theme
- Height: Auto, minimum 200px
- Layout: Multi-column grid (4 columns desktop, 2 mobile)

```css
.footer {
  background: var(--color-gray-900);
  color: var(--color-gray-300);
  padding: var(--space-16) 0 var(--space-8);
  margin-top: var(--space-32);
}

.footer-container {
  max-width: var(--container-2xl);
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.footer-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-8);
  margin-bottom: var(--space-12);
}

.footer-column h4 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: white;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  margin-bottom: var(--space-4);
}

.footer-links {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-links li {
  margin-bottom: var(--space-3);
}

.footer-link {
  font-size: var(--text-sm);
  color: var(--color-gray-400);
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-link:hover {
  color: white;
}

.footer-link:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

.footer-bottom {
  padding-top: var(--space-8);
  border-top: 1px solid var(--color-gray-800);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-gray-500);
}

@media (max-width: 1024px) {
  .footer-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .footer-grid {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }
}
```

---

## Page Layouts

### Homepage Layout Structure

```
┌─────────────────────────────────────────┐
│         Navigation Header               │
├─────────────────────────────────────────┤
│         Hero Section                    │
│  - Title, Tagline, CTAs                 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Key Metrics Dashboard           │
│  [Card] [Card] [Card] [Card]            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Data Ingestion Overview         │
│  - Text introduction                    │
│  - Time series chart                    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Source Comparison               │
│  - Tab navigation                       │
│  - Bar chart / Pie chart                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Pipeline Visualization          │
│  - Funnel chart                         │
│  - Performance metrics                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         GitHub/Docs Integration         │
│  - Repository info                      │
│  - Documentation links                  │
│  - Contribution guidelines              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Footer                          │
│  [Links] [Links] [Links] [Social]       │
└─────────────────────────────────────────┘
```

### Content Hierarchy

**Visual Weight** (top to bottom):
1. Hero title (largest, boldest)
2. Key metrics (large numbers)
3. Section headers (H2)
4. Chart titles (H3)
5. Body text
6. Supporting text
7. Footer text

---

## Interaction Patterns

### 1. Smooth Scroll

```javascript
// Smooth scroll to sections
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));

    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });

      // Update URL without jumping
      history.pushState(null, null, this.getAttribute('href'));
    }
  });
});
```

### 2. Scroll-triggered Animations

**Fade-in on scroll**:
```css
.fade-in {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.fade-in.visible {
  opacity: 1;
  transform: translateY(0);
}
```

```javascript
// Intersection Observer for scroll animations
const observerOptions = {
  root: null,
  threshold: 0.1,
  rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

document.querySelectorAll('.fade-in').forEach(el => {
  observer.observe(el);
});
```

### 3. Header Scroll State

```javascript
const header = document.querySelector('.nav-header');
let lastScroll = 0;

window.addEventListener('scroll', () => {
  const currentScroll = window.pageYOffset;

  // Add shadow when scrolled
  if (currentScroll > 10) {
    header.classList.add('scrolled');
  } else {
    header.classList.remove('scrolled');
  }

  // Hide header on scroll down, show on scroll up
  if (currentScroll > lastScroll && currentScroll > 80) {
    header.style.transform = 'translateY(-100%)';
  } else {
    header.style.transform = 'translateY(0)';
  }

  lastScroll = currentScroll;
});
```

### 4. Theme Toggle (Dark Mode)

```css
/* Theme toggle button */
.theme-toggle {
  width: 40px;
  height: 40px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theme-toggle:hover {
  background: var(--color-bg-secondary);
  transform: rotate(15deg);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}
```

```javascript
// Theme toggle functionality
const themeToggle = document.querySelector('.theme-toggle');
const htmlEl = document.documentElement;

// Check for saved theme preference or default to system
const currentTheme = localStorage.getItem('theme') ||
  (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

htmlEl.setAttribute('data-theme', currentTheme);

themeToggle.addEventListener('click', () => {
  const newTheme = htmlEl.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  htmlEl.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);

  // Announce to screen readers
  const message = newTheme === 'dark' ? 'Dark mode activated' : 'Light mode activated';
  announceToScreenReader(message);
});
```

### 5. Interactive Chart Tooltips

Already implemented in `enhanced-charts.js`, but ensure:
- Tooltips appear on hover and keyboard focus
- Clear visual connection to data point (crosshair)
- Dismiss on Escape key
- Announced to screen readers

### 6. Metric Card Animations

**Animate numbers on scroll into view**:
```javascript
function animateValue(element, start, end, duration) {
  const startTime = performance.now();
  const startValue = parseFloat(start);
  const endValue = parseFloat(end);
  const range = endValue - startValue;

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Easing function (ease-out)
    const easeOut = 1 - Math.pow(1 - progress, 3);
    const currentValue = startValue + (range * easeOut);

    element.textContent = Math.round(currentValue).toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

// Trigger when metric cards enter viewport
const metricObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const valueElement = entry.target.querySelector('.metric-value');
      const endValue = valueElement.getAttribute('data-value');
      animateValue(valueElement, 0, endValue, 2000);
      metricObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('.metric-card').forEach(card => {
  metricObserver.observe(card);
});
```

---

## Accessibility Standards

### WCAG 2.1 AA Compliance Checklist

#### Perceivable

- [ ] **Text Alternatives (1.1.1)**: All images have alt text
- [ ] **Captions (1.2.2)**: Videos have captions (if applicable)
- [ ] **Color Contrast (1.4.3)**: Minimum 4.5:1 for text, 3:1 for large text
- [ ] **Resize Text (1.4.4)**: Text can be resized to 200% without loss
- [ ] **Images of Text (1.4.5)**: Use actual text instead of images where possible
- [ ] **Reflow (1.4.10)**: Content reflows at 320px without horizontal scroll
- [ ] **Non-text Contrast (1.4.11)**: UI components have 3:1 contrast
- [ ] **Text Spacing (1.4.12)**: Text remains readable with increased spacing

#### Operable

- [ ] **Keyboard (2.1.1)**: All functionality available via keyboard
- [ ] **No Keyboard Trap (2.1.2)**: Focus can always be moved away
- [ ] **Timing Adjustable (2.2.1)**: Users can extend time limits
- [ ] **Pause, Stop, Hide (2.2.2)**: Users can control moving content
- [ ] **Three Flashes (2.3.1)**: No content flashes more than 3 times/second
- [ ] **Skip Links (2.4.1)**: "Skip to main content" link available
- [ ] **Page Titled (2.4.2)**: Pages have descriptive titles
- [ ] **Focus Order (2.4.3)**: Logical focus order
- [ ] **Link Purpose (2.4.4)**: Link text describes destination
- [ ] **Multiple Ways (2.4.5)**: Multiple ways to find pages
- [ ] **Headings and Labels (2.4.6)**: Descriptive headings
- [ ] **Focus Visible (2.4.7)**: Keyboard focus is clearly visible
- [ ] **Pointer Gestures (2.5.1)**: All functionality works with single pointer
- [ ] **Pointer Cancellation (2.5.2)**: Up-event or abort available
- [ ] **Label in Name (2.5.3)**: Accessible name contains visible text
- [ ] **Motion Actuation (2.5.4)**: Alternative to motion-based input

#### Understandable

- [ ] **Language of Page (3.1.1)**: Page language is identified
- [ ] **Language of Parts (3.1.2)**: Language changes are identified
- [ ] **On Focus (3.2.1)**: Focus doesn't trigger unexpected changes
- [ ] **On Input (3.2.2)**: Input doesn't trigger unexpected changes
- [ ] **Consistent Navigation (3.2.3)**: Navigation is consistent
- [ ] **Consistent Identification (3.2.4)**: Components are consistently identified
- [ ] **Error Identification (3.3.1)**: Errors are clearly identified
- [ ] **Labels or Instructions (3.3.2)**: Form inputs have labels
- [ ] **Error Suggestion (3.3.3)**: Error corrections are suggested
- [ ] **Error Prevention (3.3.4)**: Important actions can be reviewed/reversed

#### Robust

- [ ] **Parsing (4.1.1)**: Valid HTML
- [ ] **Name, Role, Value (4.1.2)**: Correct ARIA attributes
- [ ] **Status Messages (4.1.3)**: Status messages announced to screen readers

### Semantic HTML Structure

```html
<!-- Proper document structure -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Somali NLP Dialect Classifier - Data Ingestion Dashboard</title>
  <meta name="description" content="Real-time data ingestion metrics for Somali dialect classification research project">
</head>
<body>
  <!-- Skip link for keyboard users -->
  <a href="#main-content" class="skip-link">Skip to main content</a>

  <!-- Header with navigation -->
  <header role="banner">
    <nav aria-label="Main navigation">
      <!-- Navigation content -->
    </nav>
  </header>

  <!-- Main content -->
  <main id="main-content" role="main">
    <!-- Hero section -->
    <section aria-labelledby="hero-title">
      <h1 id="hero-title">Somali NLP Dialect Classifier</h1>
      <!-- Hero content -->
    </section>

    <!-- Metrics section -->
    <section aria-labelledby="metrics-title">
      <h2 id="metrics-title">Key Metrics</h2>
      <!-- Metrics content -->
    </section>

    <!-- Charts section -->
    <section aria-labelledby="charts-title">
      <h2 id="charts-title">Data Visualizations</h2>
      <!-- Charts content -->
    </section>
  </main>

  <!-- Footer -->
  <footer role="contentinfo">
    <!-- Footer content -->
  </footer>

  <!-- Live region for announcements -->
  <div id="live-region" role="status" aria-live="polite" aria-atomic="true" class="sr-only"></div>
</body>
</html>
```

### Focus Management

```css
/* Skip link (visible only on focus) */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  padding: 8px;
  background: var(--color-primary-600);
  color: white;
  text-decoration: none;
  z-index: 10000;
}

.skip-link:focus {
  top: 0;
}

/* Focus styles for interactive elements */
*:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* Remove default outline but keep for keyboard users */
*:focus:not(:focus-visible) {
  outline: none;
}

/* High contrast focus for accessibility */
@media (prefers-contrast: high) {
  *:focus-visible {
    outline-width: 3px;
    outline-color: currentColor;
  }
}
```

### ARIA Labels and Roles

```html
<!-- Button with accessible name -->
<button aria-label="Toggle dark mode" class="theme-toggle">
  <svg aria-hidden="true" focusable="false">...</svg>
</button>

<!-- Chart with accessible description -->
<div class="chart-wrapper" role="region" aria-labelledby="chart-1-title" aria-describedby="chart-1-desc">
  <h3 id="chart-1-title">Data Source Comparison</h3>
  <p id="chart-1-desc">Bar chart showing total records from each data source</p>
  <canvas id="chart-1" aria-label="Interactive chart"></canvas>
</div>

<!-- Tabs with proper ARIA -->
<div class="source-tabs" role="tablist" aria-label="Data sources">
  <button role="tab" aria-selected="true" aria-controls="panel-1" id="tab-1">
    Wikipedia
  </button>
  <button role="tab" aria-selected="false" aria-controls="panel-2" id="tab-2">
    BBC
  </button>
</div>
<div role="tabpanel" id="panel-1" aria-labelledby="tab-1">
  <!-- Panel content -->
</div>
```

---

## Responsive Breakpoints

### Breakpoint System

```css
:root {
  --breakpoint-sm:  640px;   /* Small devices */
  --breakpoint-md:  768px;   /* Tablets */
  --breakpoint-lg:  1024px;  /* Laptops */
  --breakpoint-xl:  1280px;  /* Desktops */
  --breakpoint-2xl: 1536px;  /* Large desktops */
}
```

### Media Query Strategy

**Mobile-first approach**: Base styles for mobile, add complexity at larger sizes

```css
/* Base (mobile) */
.element {
  font-size: 16px;
  padding: 12px;
}

/* Tablet */
@media (min-width: 768px) {
  .element {
    font-size: 18px;
    padding: 16px;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .element {
    font-size: 20px;
    padding: 20px;
  }
}
```

### Layout Breakdowns

| Breakpoint | Layout | Grid Columns | Container | Gutter |
|------------|--------|--------------|-----------|--------|
| < 640px (Mobile) | Single column | 1 | 100% - 32px | 16px |
| 640px - 767px (Large mobile) | 2 columns | 2 | 640px | 20px |
| 768px - 1023px (Tablet) | 2-3 columns | 6 | 768px | 24px |
| 1024px - 1279px (Laptop) | 3-4 columns | 12 | 1024px | 24px |
| 1280px+ (Desktop) | 4 columns | 12 | 1280px | 32px |

### Touch Target Sizes

**Minimum touch target**: 44x44px (iOS/Android guidelines)

```css
/* Ensure sufficient touch targets on mobile */
@media (max-width: 768px) {
  button,
  a,
  input[type="checkbox"],
  input[type="radio"] {
    min-width: 44px;
    min-height: 44px;
  }

  /* Increase spacing between interactive elements */
  .nav-link {
    padding: 12px 16px;
  }
}
```

---

## CSS Architecture

### File Structure

```
styles/
├── base/
│   ├── reset.css           # CSS reset/normalize
│   ├── typography.css      # Font families, scales
│   └── variables.css       # CSS custom properties
├── components/
│   ├── buttons.css         # Button variants
│   ├── cards.css           # Card components
│   ├── charts.css          # Chart containers (from enhanced-charts.css)
│   ├── header.css          # Navigation header
│   ├── hero.css            # Hero section
│   └── footer.css          # Footer
├── layouts/
│   ├── grid.css            # Grid system
│   ├── spacing.css         # Spacing utilities
│   └── containers.css      # Container widths
├── utilities/
│   ├── accessibility.css   # Screen reader only, skip links
│   ├── animations.css      # Keyframe animations
│   └── helpers.css         # Utility classes
└── main.css                # Imports all files
```

### Naming Convention

**BEM (Block Element Modifier)** for components:

```css
/* Block */
.metric-card { }

/* Element */
.metric-card__title { }
.metric-card__value { }

/* Modifier */
.metric-card--highlighted { }
.metric-card__value--large { }
```

### CSS Custom Properties Organization

```css
:root {
  /* Colors first */
  --color-primary-500: #3B82F6;

  /* Typography */
  --font-sans: Inter, sans-serif;
  --text-base: 1rem;

  /* Spacing */
  --space-4: 1rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);

  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-base: 0.2s ease;
  --transition-slow: 0.3s ease;

  /* Borders */
  --border-radius-sm: 0.25rem;
  --border-radius-md: 0.375rem;
  --border-radius-lg: 0.5rem;
}
```

### Performance Optimization

```css
/* Use will-change for animated elements */
.hero-content {
  will-change: transform, opacity;
}

/* Contain paint for isolated components */
.metric-card {
  contain: layout style paint;
}

/* Use CSS containment for independent sections */
section {
  contain: layout;
}

/* Optimize font rendering */
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)

- [ ] Set up file structure (`/index.html`, `/styles/`, `/scripts/`)
- [ ] Implement CSS reset and base styles
- [ ] Define CSS custom properties (colors, typography, spacing)
- [ ] Create responsive container system
- [ ] Implement dark mode toggle functionality
- [ ] Add skip link and focus management

### Phase 2: Components (Week 1-2)

- [ ] Build navigation header (responsive, sticky)
- [ ] Create hero section with gradient background
- [ ] Develop metric card component
- [ ] Implement button variants (primary, secondary, ghost)
- [ ] Build chart container component
- [ ] Create footer component

### Phase 3: Layout & Content (Week 2)

- [ ] Assemble homepage layout
- [ ] Integrate real data from `summary.json`
- [ ] Add section transitions and animations
- [ ] Implement scroll-triggered effects
- [ ] Add smooth scrolling navigation

### Phase 4: Chart Integration (Week 2-3)

- [ ] Import Chart.js and plugins
- [ ] Integrate `chart-config-enhanced.js`
- [ ] Integrate `enhanced-charts.js`
- [ ] Create time series chart
- [ ] Create source comparison chart
- [ ] Create pipeline funnel chart
- [ ] Create performance radar chart

### Phase 5: Interactivity (Week 3)

- [ ] Add metric number animations
- [ ] Implement tab navigation for source comparison
- [ ] Add chart filtering interactions
- [ ] Create data export functionality
- [ ] Test keyboard navigation
- [ ] Test screen reader compatibility

### Phase 6: Polish & Testing (Week 3-4)

- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Mobile device testing (iOS, Android)
- [ ] Accessibility audit (WAVE, Axe DevTools)
- [ ] Performance audit (Lighthouse)
- [ ] Color contrast verification (Contrast Checker)
- [ ] Keyboard-only navigation test
- [ ] Screen reader test (NVDA, JAWS, VoiceOver)

### Phase 7: Deployment (Week 4)

- [ ] Optimize assets (minify CSS/JS, compress images)
- [ ] Add meta tags (SEO, social sharing)
- [ ] Configure GitHub Pages
- [ ] Test production build
- [ ] Add analytics (optional, privacy-friendly)
- [ ] Document deployment process

---

## Visual Reference

### Color Palette Preview

```
Primary Blue Scale:
███ 50  #EFF6FF  (Backgrounds)
███ 100 #DBEAFE
███ 200 #BFDBFE
███ 300 #93C5FD
███ 400 #60A5FA
███ 500 #3B82F6  ← Brand Primary
███ 600 #2563EB  ← Interactive
███ 700 #1D4ED8  ← Active
███ 800 #1E40AF
███ 900 #1E3A8A

Neutral Gray Scale:
███ 50  #F9FAFB  (Light backgrounds)
███ 100 #F3F4F6
███ 200 #E5E7EB  (Borders)
███ 300 #D1D5DB
███ 400 #9CA3AF
███ 500 #6B7280  (Secondary text)
███ 600 #4B5563
███ 700 #374151
███ 800 #1F2937  (Dark backgrounds)
███ 900 #111827  (Text)
```

### Typography Scale Preview

```
Display 1:  Somali NLP Dialect Classifier (60px / 72px)
H1:         Data Ingestion Dashboard (36px / 48px)
H2:         Key Performance Metrics (30px)
H3:         Source Comparison (24px)
H4:         Wikipedia-Somali (20px)
Body Large: Introduction paragraph text (18px)
Body:       Regular paragraph text (16px)
Body Small: Supporting details (14px)
Label:      TOTAL RECORDS (14px, uppercase)
Code:       data.summary.json (14px, monospace)
```

### Spacing Examples

```
Component Padding:
Button:      12px 24px
Card:        24px (mobile: 20px)
Section:     64px vertical (mobile: 48px)
Container:   0 24px horizontal

Component Gaps:
Grid:        24px
Button group: 16px
Nav links:   32px
Card stack:  16px
```

---

## Next Steps

1. **Review & Approve**: Share this spec with stakeholders
2. **Create Assets**: Generate any missing icons/graphics
3. **Begin Implementation**: Start with Phase 1 (Foundation)
4. **Iterate**: Gather feedback and refine
5. **Test Early**: Don't wait until the end to test accessibility
6. **Document**: Keep this spec updated as design evolves

---

## References & Resources

### Design Inspiration
- [Stripe Docs](https://stripe.com/docs) - Clean, professional data presentation
- [Linear](https://linear.app) - Modern minimalism, excellent typography
- [Airbnb Design](https://airbnb.design) - Accessible, inclusive design
- [ChainGPT](https://chaingpt.org) - Futuristic, award-winning
- [Lusion](https://lusion.co) - Creative, engaging interactions

### Accessibility Tools
- [WAVE Browser Extension](https://wave.webaim.org/extension/)
- [Axe DevTools](https://www.deque.com/axe/devtools/)
- [Color Contrast Analyzer](https://www.tpgi.com/color-contrast-checker/)
- [NVDA Screen Reader](https://www.nvaccess.org/)
- [VoiceOver (Mac/iOS)](https://www.apple.com/accessibility/voiceover/)

### Performance Tools
- [Google Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [WebPageTest](https://www.webpagetest.org/)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)

### Color Resources
- [Paul Tol's Notes](https://personal.sron.nl/~pault/) - Colorblind-safe palettes
- [Color Oracle](https://colororacle.org/) - Colorblindness simulator
- [Coolors](https://coolors.co/) - Palette generator

---

**Document Version**: 1.0.0
**Last Updated**: October 25, 2025
**Status**: Ready for Implementation
**Prepared by**: UX/UI Design Expert
**For**: Frontend Engineer Implementation
