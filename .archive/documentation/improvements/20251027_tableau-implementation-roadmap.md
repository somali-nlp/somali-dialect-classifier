# Tableau Design Adaptation - Implementation Roadmap

**Project:** Somali Dialect Classifier Dashboard Redesign
**Timeline:** 2-3 weeks
**Difficulty:** Medium
**Risk Level:** Low (CSS-only changes, no functionality impact)

---

## Overview

This roadmap provides a step-by-step guide to transform the Somali Dialect Classifier dashboard from its current modern, trendy aesthetic to a professional, enterprise-grade design inspired by Tableau's visual system.

**Key Transformation:**
- **From:** Glassmorphism, gradients, purple/blue mix, trendy effects
- **To:** Solid whites, Tableau blue, professional shadows, enterprise credibility

---

## Week 1: Foundation & Core Visual Changes

### Day 1-2: Color Palette Migration

**Files to Modify:**
- `/dashboard/templates/index.html` (CSS variables in `<style>` section)

**Tasks:**

1. **Update CSS Custom Properties**
   ```css
   /* REPLACE EXISTING COLOR VARIABLES */
   :root {
     /* Old: --brand-primary: #2563eb; */
     --brand-primary: #0176D3;  /* Tableau Blue */

     /* Old: --brand-secondary: #7c3aed; */
     --brand-secondary: #032D60;  /* Dark Navy - REMOVE PURPLE */

     /* Old: --brand-accent: #10b981; */
     --brand-accent: #32AE88;  /* Tableau Green */

     /* ADD NEW TABLEAU COLORS */
     --tableau-blue: #0176D3;
     --tableau-navy: #032D60;
     --tableau-navy-link: #0B5CAB;
     --tableau-dark-navy: #001639;
     --tableau-bg-light-blue: #EAF5FE;
     --tableau-bg-off-white: #F4F4F4;
     --tableau-green: #32AE88;
     --tableau-text-primary: #080707;
     --tableau-text-secondary: #333333;
   }
   ```

2. **Find and Replace ALL Purple References**
   - Search for: `#7c3aed`, `#7c3a`, `purple`, `var(--brand-secondary)`
   - Replace with: `#0176D3` or appropriate Tableau blue variant
   - Check: buttons, links, badges, charts, accents

3. **Update Source-Specific Colors (if needed)**
   ```css
   /* Update source colors to align with Tableau palette */
   --wikipedia: #3B82F6;     /* Keep blue */
   --bbc: #EF4444;           /* Keep red */
   --huggingface: #32AE88;   /* Update to Tableau green */
   --sprakbanken: #F59E0B;   /* Keep orange */
   ```

**Verification:**
- [ ] No purple visible anywhere on the dashboard
- [ ] All primary actions use `#0176D3`
- [ ] All headings use `#032D60`
- [ ] Color palette is now blue-dominant

**Estimated Time:** 4-6 hours

---

### Day 3-4: Typography System Overhaul

**Files to Modify:**
- `/dashboard/templates/index.html` (font imports and typography CSS)

**Tasks:**

1. **Add Montserrat Font Import**
   ```html
   <!-- ADD TO <head> SECTION -->
   <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
   ```

2. **Update Typography Variables**
   ```css
   :root {
     /* REPLACE FONT FAMILIES */
     --font-heading: 'Montserrat', 'Inter', -apple-system, sans-serif;
     --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
     --font-mono: 'Fira Code', Monaco, monospace;

     /* UPDATE TYPE SCALE TO TABLEAU SIZES */
     --text-h1: 3.5rem;     /* 56px - was 3rem */
     --text-h2: 2.5rem;     /* 40px - was 1.875rem */
     --text-h3-lg: 2rem;    /* 32px - was 1.5rem */
     --text-h3: 1.5rem;     /* 24px */
     --text-body: 1rem;     /* 16px - keep */
     --text-small: 0.875rem; /* 14px - keep */
   }
   ```

3. **Update Heading Styles**
   ```css
   /* FIND AND REPLACE ALL HEADING STYLES */
   h1, h2, h3, h4, h5, h6 {
     font-family: var(--font-heading);
     font-weight: 400; /* CRITICAL: Regular, not bold! */
     color: var(--tableau-navy); /* #032D60 */
     line-height: 1.2;
     margin-bottom: 1rem;
   }

   h1 {
     font-size: var(--text-h1); /* 56px */
     line-height: 1.14;
   }

   h2 {
     font-size: var(--text-h2); /* 40px */
     line-height: 1.2;
   }

   h3 {
     font-size: var(--text-h3); /* 24px */
     line-height: 1.33;
   }
   ```

4. **Update Body Text**
   ```css
   body {
     font-family: var(--font-body);
     font-size: var(--text-body);
     line-height: 1.5;
     color: var(--tableau-text-primary);
   }
   ```

**Verification:**
- [ ] Montserrat loads correctly for headings
- [ ] All headings are regular weight (400, not bold)
- [ ] All headings are dark navy `#032D60`
- [ ] H1 is 56px, H2 is 40px, H3 is 24px
- [ ] Body text remains Inter

**Estimated Time:** 4-5 hours

---

### Day 5: Remove Glassmorphism Effects

**Files to Modify:**
- `/dashboard/templates/index.html` (card and component styles)

**Tasks:**

1. **Find ALL Glassmorphism Effects**
   Search for:
   - `backdrop-filter`
   - `blur(`
   - `rgba(255, 255, 255, 0.`
   - `rgba(0, 0, 0, 0.`
   - `-webkit-backdrop-filter`

2. **Replace Card Backgrounds**
   ```css
   /* BEFORE */
   .card {
     background: rgba(255, 255, 255, 0.1);
     backdrop-filter: blur(10px);
     -webkit-backdrop-filter: blur(10px);
     border: 1px solid rgba(255, 255, 255, 0.2);
   }

   /* AFTER */
   .card {
     background: #FFFFFF; /* Solid white */
     backdrop-filter: none;
     -webkit-backdrop-filter: none;
     border: none;
   }
   ```

3. **Remove Gradient Backgrounds**
   ```css
   /* FIND gradient backgrounds like: */
   background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);

   /* REPLACE WITH: */
   background: #FFFFFF; /* or appropriate solid color */
   ```

4. **Update ALL Card Classes**
   - `.stat-card`
   - `.metric-card`
   - `.source-card`
   - `.overview-card`
   - Any custom card variants

**Verification:**
- [ ] No glassmorphism effects anywhere
- [ ] All cards have solid white backgrounds
- [ ] No transparent/translucent cards remain
- [ ] No blur effects applied
- [ ] Cards look clean and professional

**Estimated Time:** 3-4 hours

---

## Week 2: Component Redesign & Layout

### Day 6-7: Card Styling Update

**Files to Modify:**
- `/dashboard/templates/index.html` (card component styles)

**Tasks:**

1. **Apply Tableau Shadow Style**
   ```css
   /* REPLACE EXISTING SHADOW STYLES */
   .card {
     background: #FFFFFF;
     border-radius: 16px; /* Increase from 12px */
     box-shadow:
       rgba(23, 23, 23, 0.08) 0px 2px 8px -2px,
       rgba(23, 23, 23, 0.16) 0px 8px 12px -2px;
     padding: 48px; /* Increase from 24-32px */
     transition: all 350ms ease;
   }

   .card:hover {
     box-shadow:
       rgba(23, 23, 23, 0.12) 0px 4px 12px -2px,
       rgba(23, 23, 23, 0.24) 0px 12px 20px -2px;
     transform: translateY(-2px);
   }
   ```

2. **Create Card Variants**
   ```css
   /* Compact card for smaller spaces */
   .card-compact {
     padding: 32px;
   }

   /* Card with image */
   .card-with-image {
     padding: 0;
     overflow: hidden;
   }

   .card-with-image img {
     width: 100%;
     height: auto;
     display: block;
   }

   .card-with-image .card-content {
     padding: 32px;
   }
   ```

3. **Update Border Radius**
   ```css
   :root {
     --radius-sm: 0.25rem;  /* 4px - buttons */
     --radius-card: 1rem;   /* 16px - cards */
     --radius-lg: 1.5rem;   /* 24px - large elements */
   }
   ```

4. **Apply to All Card Elements**
   - Stat cards
   - Metric cards
   - Source cards
   - Overview panels
   - Chart containers

**Verification:**
- [ ] All cards have 16px border radius
- [ ] All cards use Tableau shadow (dual-layer)
- [ ] Card padding is generous (48px standard, 32px compact)
- [ ] Hover effect works (slight lift + darker shadow)
- [ ] Cards look professional, not flashy

**Estimated Time:** 6-8 hours

---

### Day 8-9: Button Redesign

**Files to Modify:**
- `/dashboard/templates/index.html` (button styles)

**Tasks:**

1. **Update Button Base Styles**
   ```css
   .btn {
     display: inline-block;
     padding: 8px 24px; /* Specific Tableau ratio */
     font-size: 1rem;
     font-weight: 400; /* Regular, not bold */
     text-align: center;
     text-decoration: none;
     border-radius: 4px; /* Small radius */
     transition: all 250ms ease;
     cursor: pointer;
     border: 2px solid transparent;
     font-family: var(--font-body);
   }
   ```

2. **Primary Button**
   ```css
   /* REMOVE GRADIENT, USE SOLID COLOR */
   .btn-primary {
     background: var(--tableau-blue); /* #0176D3 */
     color: white;
     border-color: var(--tableau-blue);
   }

   .btn-primary:hover {
     background: #0158A5; /* Darker blue */
     border-color: #0158A5;
     transform: translateY(-1px);
     box-shadow: 0 4px 8px rgba(1, 118, 211, 0.2);
   }
   ```

3. **Secondary Button (Outlined)**
   ```css
   .btn-secondary {
     background: transparent;
     color: var(--tableau-blue);
     border-color: var(--tableau-blue);
   }

   .btn-secondary:hover {
     background: rgba(1, 118, 211, 0.08);
   }
   ```

4. **Success/Action Buttons**
   ```css
   .btn-success {
     background: var(--tableau-green);
     color: white;
     border-color: var(--tableau-green);
   }

   .btn-success:hover {
     background: #2A9474;
     border-color: #2A9474;
   }
   ```

5. **Update All Button Usage**
   - Check all `<button>` elements
   - Check all `.btn` classes
   - Verify CTAs in hero sections
   - Test form buttons
   - Update icon buttons if present

**Verification:**
- [ ] No gradient backgrounds on buttons
- [ ] All buttons have 4px border radius
- [ ] Primary buttons use `#0176D3`
- [ ] Outlined buttons have 2px border
- [ ] Hover states work correctly
- [ ] Text is not uppercase (unless intentional)

**Estimated Time:** 4-6 hours

---

### Day 10: Spacing System Update

**Files to Modify:**
- `/dashboard/templates/index.html` (spacing variables and utilities)

**Tasks:**

1. **Update Spacing Scale**
   ```css
   :root {
     /* MORE GENEROUS SPACING */
     --space-xs: 0.5rem;    /* 8px */
     --space-sm: 1rem;      /* 16px */
     --space-md: 1.5rem;    /* 24px */
     --space-lg: 2rem;      /* 32px */
     --space-xl: 3rem;      /* 48px */
     --space-2xl: 4rem;     /* 64px */
     --space-3xl: 5rem;     /* 80px */
     --space-4xl: 6rem;     /* 96px */
   }
   ```

2. **Update Section Spacing**
   ```css
   .section {
     padding: var(--space-3xl) 0; /* 80px vertical */
   }

   .section-hero {
     padding: 7.5rem 0; /* 120px for hero */
   }

   .section-compact {
     padding: var(--space-2xl) 0; /* 64px */
   }
   ```

3. **Update Grid Gaps**
   ```css
   .grid {
     display: grid;
     gap: var(--space-lg); /* 32px between items */
   }

   .grid-tight {
     gap: var(--space-md); /* 24px for tighter layouts */
   }
   ```

4. **Review ALL Spacing**
   - Section vertical padding
   - Card internal padding
   - Grid gaps
   - Heading margins
   - Button spacing
   - Navigation spacing

**Verification:**
- [ ] Sections have 80px+ vertical spacing
- [ ] Cards have 48px internal padding
- [ ] Grids have 32px gaps
- [ ] Layout feels spacious, not cramped
- [ ] Responsive spacing adjusts appropriately

**Estimated Time:** 4-5 hours

---

## Week 3: Polish & Testing

### Day 11-12: Link & Badge Styling

**Files to Modify:**
- `/dashboard/templates/index.html` (link and badge styles)

**Tasks:**

1. **Update Link Styles**
   ```css
   /* Text links with underline */
   a {
     color: var(--tableau-navy-link); /* #0B5CAB */
     text-decoration: underline;
     transition: color 150ms ease;
   }

   a:hover {
     color: var(--tableau-navy); /* #032D60 */
   }

   /* CTA links without underline */
   a.cta-link {
     text-decoration: none;
     border-bottom: 2px solid transparent;
   }

   a.cta-link:hover {
     border-bottom-color: var(--tableau-blue);
   }
   ```

2. **Create Badge Component**
   ```css
   .badge {
     display: inline-block;
     padding: 4px 12px;
     font-size: 0.875rem;
     font-weight: 500;
     text-transform: uppercase;
     letter-spacing: 0.5px;
     border-radius: 4px;
     background: var(--tableau-bg-light-blue);
     color: var(--tableau-navy-link);
   }

   /* Source-specific badges */
   .badge-wikipedia {
     background: #EBF2FF;
     color: #3B82F6;
   }

   .badge-bbc {
     background: #FEE;
     color: #EF4444;
   }

   .badge-huggingface {
     background: #E6F7F0;
     color: #32AE88;
   }

   .badge-sprakbanken {
     background: #FFF4E6;
     color: #F59E0B;
   }
   ```

3. **Add Badges to Cards**
   - Add small badge above card titles
   - Use for source identification
   - Use for status indicators
   - Use for category labels

**Verification:**
- [ ] Links have proper colors and underlines
- [ ] CTA links have bottom border on hover
- [ ] Badges display correctly
- [ ] Badge colors match Tableau aesthetic

**Estimated Time:** 3-4 hours

---

### Day 13: Background & Section Updates

**Files to Modify:**
- `/dashboard/templates/index.html` (section backgrounds)

**Tasks:**

1. **Update Hero Section**
   ```css
   .hero-section {
     background: linear-gradient(180deg, var(--tableau-bg-light-blue) 0%, white 100%);
     padding: 7.5rem 0;
   }
   ```

2. **Alternating Sections**
   ```css
   .section {
     background: white;
   }

   .section-alt {
     background: var(--tableau-bg-off-white);
   }
   ```

3. **Remove Dark Backgrounds**
   - Replace any dark backgrounds with white or light gray
   - Ensure sufficient contrast
   - Keep professional, light appearance

**Verification:**
- [ ] Hero has subtle blue gradient
- [ ] Sections alternate white/off-white
- [ ] No dark backgrounds remain
- [ ] Professional, clean appearance

**Estimated Time:** 2-3 hours

---

### Day 14-15: Responsive Testing & Adjustments

**Tasks:**

1. **Test All Breakpoints**
   - Desktop: 1440px, 1920px
   - Tablet: 768px, 1024px
   - Mobile: 375px, 414px

2. **Adjust Mobile Styles**
   ```css
   @media (max-width: 768px) {
     h1 {
       font-size: 2.5rem; /* 40px instead of 56px */
     }

     h2 {
       font-size: 2rem; /* 32px instead of 40px */
     }

     .card {
       padding: var(--space-lg); /* 32px instead of 48px */
     }

     .section {
       padding: var(--space-2xl) 0; /* 64px instead of 80px */
     }
   }
   ```

3. **Test Interactive Elements**
   - All buttons clickable
   - All links working
   - Cards hover correctly
   - Forms function properly
   - Charts display correctly

4. **Browser Testing**
   - Chrome (latest)
   - Firefox (latest)
   - Safari (latest)
   - Edge (latest)
   - Mobile browsers

**Verification:**
- [ ] Responsive on all devices
- [ ] Touch targets adequate on mobile
- [ ] Text readable on small screens
- [ ] No horizontal scrolling
- [ ] All features work on all browsers

**Estimated Time:** 8-10 hours

---

### Day 16: Accessibility Audit

**Tasks:**

1. **Color Contrast Check**
   - Use WebAIM Contrast Checker
   - Verify all text meets WCAG AA (4.5:1 minimum)
   - Test button states
   - Check link colors

2. **Keyboard Navigation**
   - Tab through entire interface
   - Verify focus states visible
   - Test skip links
   - Verify logical tab order

3. **Add Focus States**
   ```css
   a:focus,
   button:focus,
   .btn:focus {
     outline: 2px solid var(--tableau-blue);
     outline-offset: 2px;
   }

   .card:focus-within {
     box-shadow:
       var(--shadow-card-hover),
       0 0 0 3px rgba(1, 118, 211, 0.2);
   }
   ```

4. **Semantic HTML Review**
   - Proper heading hierarchy (H1 > H2 > H3)
   - ARIA labels where needed
   - Alt text on images
   - Form labels associated

**Verification:**
- [ ] All color contrasts pass WCAG AA
- [ ] Keyboard navigation works completely
- [ ] Focus states clearly visible
- [ ] Screen reader compatible
- [ ] Semantic HTML structure

**Estimated Time:** 4-6 hours

---

### Day 17: Final Polish & Review

**Tasks:**

1. **Visual QA**
   - Review every page/section
   - Check alignment and spacing
   - Verify color consistency
   - Ensure typography consistency

2. **Performance Check**
   - Test page load times
   - Optimize images if needed
   - Check font loading
   - Verify no layout shift

3. **Cross-Browser Final Check**
   - Screenshot all browsers
   - Compare side-by-side
   - Fix any browser-specific issues

4. **Stakeholder Review**
   - Present to team
   - Gather feedback
   - Make final adjustments
   - Get approval

**Verification:**
- [ ] All pages look professional
- [ ] Consistent Tableau aesthetic throughout
- [ ] Fast page loads
- [ ] Team approval received

**Estimated Time:** 6-8 hours

---

## Deployment Checklist

### Pre-Deployment
- [ ] All changes tested in staging environment
- [ ] Backup current production CSS
- [ ] Document all changes made
- [ ] Create rollback plan

### Deployment
- [ ] Deploy to production during low-traffic period
- [ ] Monitor for errors
- [ ] Test critical user flows
- [ ] Verify analytics tracking still works

### Post-Deployment
- [ ] Monitor user feedback
- [ ] Watch analytics for impact
- [ ] Address any issues immediately
- [ ] Document lessons learned

---

## Risk Mitigation

### Potential Issues & Solutions

| Risk | Impact | Mitigation |
|------|--------|------------|
| Font loading slow | High | Use font-display: swap, subset fonts |
| Color contrast fails | Medium | Test all colors with WCAG checker |
| Mobile layout breaks | High | Test thoroughly on real devices |
| Browser incompatibility | Medium | Use autoprefixer, test all browsers |
| User confusion | Low | Keep layout similar, change only styling |

---

## Success Metrics

### Measure These Post-Redesign

1. **User Perception**
   - Professional appearance rating
   - Trust indicators
   - Brand alignment

2. **Technical Metrics**
   - Page load time (should not increase)
   - Accessibility score (should improve)
   - Browser compatibility (100%)

3. **Business Metrics**
   - User engagement time
   - Bounce rate
   - Return visitor rate

---

## Team Responsibilities

### Frontend Developer
- Implement all CSS changes
- Test responsive behavior
- Fix browser compatibility issues
- Optimize performance

### UX Designer (You)
- Review all changes for design accuracy
- Provide feedback on spacing/alignment
- Verify Tableau aesthetic maintained
- Conduct final visual QA

### Project Manager
- Track progress against timeline
- Coordinate testing
- Manage stakeholder communication
- Schedule deployment

---

## Post-Launch Iteration

### Week 4: Monitor & Adjust

1. **Collect Feedback**
   - User surveys
   - Team input
   - Analytics review

2. **Make Minor Adjustments**
   - Tweak spacing if needed
   - Adjust colors slightly if contrast issues
   - Fix any bugs discovered

3. **Document Final State**
   - Update style guide
   - Document component library
   - Create design system documentation

---

## Estimated Total Time

| Phase | Time |
|-------|------|
| Week 1: Foundation | 20-25 hours |
| Week 2: Components | 25-30 hours |
| Week 3: Polish | 25-30 hours |
| **Total** | **70-85 hours** |

**Calendar Time:** 3 weeks with 1 person working ~30 hours/week

---

## Conclusion

This roadmap provides a structured approach to transforming the dashboard aesthetic from trendy to professional. By following this plan phase-by-phase, you'll minimize risk while maximizing visual impact.

**Remember:**
- Test frequently throughout the process
- Don't skip accessibility checks
- Get feedback early and often
- Document everything for future maintenance

**The Result:**
A professional, enterprise-grade dashboard that conveys trust, credibility, and authority in the NLP research space.

---

*Roadmap created: 2025-10-27*
*Estimated completion: 3 weeks*
*Complexity: Medium*
*Risk: Low*
