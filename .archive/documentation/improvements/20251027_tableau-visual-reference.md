# Tableau Visual Design Reference

**Project:** Somali Dialect Classifier Dashboard Redesign
**Date:** 2025-10-27
**Purpose:** Visual reference guide with annotated screenshots from Tableau.com

---

## Screenshot Gallery

### 1. Hero Section
**Location:** `.playwright-mcp/tableau-homepage-hero.png`

**Key Observations:**
- Light blue gradient background (`#EAF5FE` fading to white)
- Large, bold heading in dark navy (`#032D60`)
- Clean navigation with subtle design
- Two CTA buttons: Primary (filled blue) + Secondary (outlined blue)
- Large illustration on right side with whimsical elements
- Generous white space around all elements

**Typography:**
- Heading: ~56px, ITC Avant Garde, Regular weight
- Body: 16px, Salesforce Sans
- All headings use dark navy, never black

**Colors Visible:**
- Navigation text: `#080707` (near black)
- Heading: `#032D60` (dark navy)
- CTA button: `#0176D3` (Tableau blue)
- Background gradient: `#EAF5FE` to white

---

### 2. Card Grid Section
**Location:** `.playwright-mcp/tableau-cards-section.png`

**Key Observations:**
- Large hero card with gradient background (blue to purple tones)
- Three smaller cards in a row below
- All cards have white background with subtle shadows
- Small colored badges above each card title ("Agentic analytics", "Free trial", "Tableau+", "Gartner")
- Card border radius: 16px
- Cards use dual-layer shadow for depth

**Card Specifications:**
- Background: Pure white `#FFFFFF`
- Border radius: 16px
- Shadow: `rgba(23, 23, 23, 0.08) 0px 2px 8px -2px, rgba(23, 23, 23, 0.16) 0px 8px 12px -2px`
- Internal padding: Appears to be 32-48px
- Gap between cards: 32px

**Badge Style:**
- Small text badge above heading
- Light blue background for "Agentic analytics"
- Uppercase text
- Minimal padding

**Button Style:**
- "See it now" - Outlined button with blue border
- Border: 2px solid `#0176D3`
- Border radius: 4px (small, not rounded)
- Padding: 8px 24px

---

### 3. Feature Cards with Images
**Location:** `.playwright-mcp/tableau-feature-cards.png`

**Key Observations:**
- Four feature cards in a row
- Each card has large colored circular background with illustration
- Colors used: Purple, Orange, Blue, Cyan (brand persona colors)
- Card structure: Image on top, heading, body text, CTA link at bottom
- Clean white background for card content area
- Consistent shadow treatment across all cards

**Card Design Pattern:**
- Image/illustration fills top portion
- White content area below with generous padding
- Heading in dark navy (`#032D60`)
- Body text in default dark gray
- "Learn more" link in blue with underline
- All cards same height (aligned bottoms)

**Color Accents:**
- Purple gradient: For analysts
- Orange gradient: For data/IT leaders
- Blue gradient: For business leaders
- Cyan gradient: For developers

**Typography in Cards:**
- Heading: ~24px, ITC Avant Garde, Regular
- Body: 16px, Salesforce Sans
- Link: 16px, Blue `#0B5CAB`, underlined

---

### 4. Persona/Role Cards
**Location:** `.playwright-mcp/tableau-footer.png`

**Key Observations:**
- Four cards in a row showcasing different user personas
- Each card has large circular colored background
- Illustrations show people using Tableau (photos + screenshots)
- Decorative plus signs and sparkles around circles
- White background for overall section
- Generous spacing between cards

**Design Elements:**
- Large colored circles (gradients: pink/purple, orange, blue, cyan)
- Product screenshots overlaid on circles
- People photos integrated into design
- Playful geometric decorations (plus signs, sparkles)
- Clean typography below each card

**Section Design:**
- Large heading above cards: "Make data-driven decisions..."
- Clean white background
- Ample vertical padding (80px+)
- Grid layout with equal-width columns

---

## Color Palette Extract

### Primary Colors
```css
/* Blues */
--tableau-blue-primary: #0176D3;    /* Main CTA buttons */
--tableau-navy-heading: #032D60;    /* All headings */
--tableau-navy-link: #0B5CAB;       /* Links */
--tableau-dark-navy: #001639;       /* Dark elements */
```

### Background Colors
```css
/* Backgrounds */
--tableau-bg-light-blue: #EAF5FE;   /* Hero gradient start */
--tableau-bg-off-white: #F4F4F4;    /* Alternate sections */
--tableau-bg-white: #FFFFFF;        /* Cards, main bg */
--tableau-bg-badge: #CDD4F2;        /* Badge backgrounds */
```

### Accent Colors (Persona-specific)
```css
/* Used for persona cards, not primary UI */
--tableau-accent-purple: #7C3AED;   /* Analysts */
--tableau-accent-orange: #F59E0B;   /* Data/IT */
--tableau-accent-blue: #3B82F6;     /* Business */
--tableau-accent-cyan: #06B6D4;     /* Developers */
--tableau-accent-green: #32AE88;    /* Success states */
```

### Text Colors
```css
/* Typography */
--tableau-text-primary: #080707;    /* Body text */
--tableau-text-secondary: #333333;  /* Subdued text */
--tableau-text-light: #555555;      /* Light text */
--tableau-border-light: #EBEBEB;    /* Borders */
```

---

## Typography Specifications

### Font Families
```css
font-family: "ITC Avant Garde", system-ui, sans-serif;        /* Headings */
font-family: "Salesforce Sans", Arial, sans-serif;            /* Body */
```

### Font Sizes (from screenshots)
```css
/* Headings */
h1: 56px (3.5rem) / line-height: 1.14
h2: 40px (2.5rem) / line-height: 1.2
h3 (large): 32px (2rem) / line-height: 1.25
h3 (small): 24px (1.5rem) / line-height: 1.33

/* Body */
body: 16px (1rem) / line-height: 1.5
small: 14px (0.875rem) / line-height: 1.43
```

### Font Weights
```css
/* Important: Tableau uses REGULAR weight for headings */
h1, h2, h3: font-weight: 400 (Regular, not bold!)
body: font-weight: 400 (Regular)
badge: font-weight: 500 (Medium)
```

---

## Component Specifications from Screenshots

### Navigation Bar
```css
.navbar {
  background: white;
  border-bottom: 1px solid #EBEBEB;
  padding: 16px 40px;
  position: sticky;
  top: 0;
}

.nav-link {
  color: #080707;
  font-size: 16px;
  font-weight: 400;
  padding: 16px;
}
```

### Primary Button (from hero)
```css
.btn-primary {
  background: #0176D3;
  color: white;
  border: 2px solid #0176D3;
  border-radius: 4px;
  padding: 8px 24px;
  font-size: 16px;
  font-weight: 400;
}
```

### Secondary Button (from hero)
```css
.btn-secondary {
  background: transparent;
  color: #0176D3;
  border: 2px solid #0176D3;
  border-radius: 4px;
  padding: 8px 24px;
  font-size: 16px;
  font-weight: 400;
}
```

### Card (from grid section)
```css
.card {
  background: white;
  border-radius: 16px;
  box-shadow:
    rgba(23, 23, 23, 0.08) 0px 2px 8px -2px,
    rgba(23, 23, 23, 0.16) 0px 8px 12px -2px;
  padding: 48px;
  transition: all 350ms ease;
}

.card:hover {
  box-shadow:
    rgba(23, 23, 23, 0.12) 0px 4px 12px -2px,
    rgba(23, 23, 23, 0.24) 0px 12px 20px -2px;
  transform: translateY(-2px);
}
```

### Badge (from card section)
```css
.badge {
  background: #EAF5FE;
  color: #0B5CAB;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
```

### Text Link (from feature cards)
```css
.text-link {
  color: #0B5CAB;
  font-size: 16px;
  font-weight: 400;
  text-decoration: underline;
}

.text-link:hover {
  color: #032D60;
}
```

---

## Layout Patterns Observed

### Hero Section Layout
```
[Navigation Bar - sticky, white background]

[Hero Section - light blue gradient background]
  [Left Column - 50%]
    - Large heading (56px)
    - Supporting text (16px)
    - Button group (Primary + Secondary)
  [Right Column - 50%]
    - Large illustration/screenshot

[Padding: 120px vertical, 40px horizontal]
```

### Card Grid Pattern
```
[Section Heading - centered]
  - H2 (40px)

[Card Grid - 3-4 columns]
  Card 1: [Badge] [Heading] [Body] [CTA Link]
  Card 2: [Badge] [Heading] [Body] [CTA Link]
  Card 3: [Badge] [Heading] [Body] [CTA Link]
  Card 4: [Badge] [Heading] [Body] [CTA Link]

[Gap: 32px between cards]
[Padding: 80px vertical]
```

### Feature Card with Image Pattern
```
Card Structure:
  [Image/Illustration - full width, fixed height]
  [Content Area - white background, 32px padding]
    - Badge (small, colored)
    - Heading (24px, navy)
    - Body text (16px, dark gray)
    - CTA link (16px, blue, underlined)

[Card: border-radius 16px, shadow]
```

---

## Spacing System from Screenshots

### Vertical Spacing (Sections)
- Hero section: 120px top/bottom
- Standard section: 80px top/bottom
- Between cards in grid: 32px
- Between heading and content: 24px

### Horizontal Spacing
- Container max-width: ~1440px
- Container padding: 40px horizontal
- Grid gap: 32px
- Button spacing: 16px between buttons

### Internal Padding
- Cards: 48px (large) or 32px (compact)
- Buttons: 8px vertical, 24px horizontal
- Badges: 4px vertical, 12px horizontal
- Navigation links: 16px

---

## Design Principles Observed

### 1. Restraint
- Minimal color usage (blue dominant)
- No flashy effects or animations
- Subtle shadows only
- Clean, simple layouts

### 2. Professionalism
- Large, confident typography
- Generous white space
- High-quality imagery
- Consistent styling

### 3. Clarity
- Clear visual hierarchy
- Easy-to-read text (high contrast)
- Obvious CTAs
- Logical information flow

### 4. Enterprise Feel
- Corporate blue color scheme
- Professional photography
- Product screenshots prominently featured
- Trust-building elements (Gartner badge, customer logos)

### 5. Accessibility
- High color contrast (WCAG AAA)
- Large click targets
- Clear focus states
- Semantic structure

---

## Key Differences: Current Dashboard vs Tableau

| Aspect | Current Dashboard | Tableau Style |
|--------|------------------|---------------|
| **Primary Color** | Blue + Purple mix | Pure blue only |
| **Card Style** | Glassmorphism | Solid white |
| **Shadows** | Heavy glow | Subtle dual-layer |
| **Typography** | Mixed fonts | Consistent hierarchy |
| **Heading Weight** | Bold (600-700) | Regular (400) |
| **Spacing** | Compact | Generous |
| **Effects** | Trendy (blur, glow) | Professional (subtle) |
| **Border Radius** | 12px | 16px cards, 4px buttons |
| **Button Style** | Gradient | Solid color |
| **Overall Feel** | Modern, trendy | Enterprise, timeless |

---

## Screenshot File Paths

All screenshots saved to:
```
.playwright-mcp/tableau-homepage-hero.png
.playwright-mcp/tableau-cards-section.png
.playwright-mcp/tableau-feature-cards.png
.playwright-mcp/tableau-footer.png
```

---

## Recommended Application to Dashboard

### 1. Immediate Visual Impact
- Replace purple with Tableau blue throughout
- Remove glassmorphism from cards
- Apply Tableau shadow style to cards
- Update button styling to match Tableau

### 2. Typography Overhaul
- Add Montserrat for headings (Tableau uses ITC Avant Garde - not freely available)
- Set all headings to regular weight (400)
- Change heading color to dark navy `#032D60`
- Increase heading sizes (H1: 56px, H2: 40px)

### 3. Layout Refinements
- Increase card padding from 32px to 48px
- Increase section vertical spacing to 80px
- Add more breathing room in grid layouts
- Ensure consistent spacing throughout

### 4. Component Updates
- Redesign buttons with solid colors and 2px borders
- Update card border-radius to 16px
- Add badge components for source labels
- Style links with underlines (Tableau style)

---

## Implementation Priority

### Phase 1: High Impact, Low Effort
1. Update color variables (purple → blue)
2. Change heading colors to navy
3. Remove glassmorphism effects
4. Apply new shadow style to cards

### Phase 2: Medium Impact, Medium Effort
5. Add Montserrat font for headings
6. Update button styling completely
7. Increase card padding
8. Adjust spacing throughout

### Phase 3: Polish, Higher Effort
9. Refine all typography sizes
10. Add badge components
11. Update link styling
12. Test and iterate

---

*Visual reference compiled: 2025-10-27*
*Screenshots: 4 captured from Tableau.com*
*Analysis: Complete design system extraction*
