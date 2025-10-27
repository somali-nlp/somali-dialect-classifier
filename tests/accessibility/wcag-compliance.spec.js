import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * WCAG 2.1 AA Compliance Tests
 *
 * Automated accessibility testing using axe-core to ensure
 * the dashboard meets WCAG 2.1 Level AA standards.
 */

test.describe('WCAG 2.1 AA Compliance', () => {

  test('homepage has no accessibility violations @a11y @wcag', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('dashboard section has no accessibility violations @a11y @wcag', async ({ page }) => {
    await page.goto('/#dashboard');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('all tab panels have no accessibility violations @a11y @wcag', async ({ page }) => {
    await page.goto('/#dashboard');
    await page.waitForLoadState('networkidle');

    const tabs = ['overview', 'sources', 'quality', 'pipeline', 'reports'];

    for (const tab of tabs) {
      await page.click(`button[aria-controls="${tab}-panel"]`);
      await page.waitForSelector(`#${tab}-panel`, { state: 'visible' });

      const results = await new AxeBuilder({ page })
        .include(`#${tab}-panel`)
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();

      expect(results.violations).toEqual([]);
    }
  });

  test('footer has no accessibility violations @a11y @wcag', async ({ page }) => {
    await page.goto('/');
    await page.locator('footer').scrollIntoViewIfNeeded();

    const results = await new AxeBuilder({ page })
      .include('footer')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});

test.describe('Color Contrast (WCAG 2.1 AA)', () => {

  test('all text meets contrast requirements @a11y @contrast', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.color'])
      .analyze();

    const contrastViolations = results.violations.filter(
      v => v.id === 'color-contrast'
    );

    expect(contrastViolations).toHaveLength(0);
  });

  test('charts have sufficient color contrast @a11y @contrast @chart', async ({ page }) => {
    await page.goto('/#dashboard');
    await page.click('button[aria-controls="sources-panel"]');
    await page.waitForTimeout(1500); // Wait for charts

    const chartSection = page.locator('#sources-panel .charts-grid');
    await chartSection.scrollIntoViewIfNeeded();

    const results = await new AxeBuilder({ page })
      .include('#sources-panel')
      .withTags(['cat.color'])
      .analyze();

    expect(results.violations).toHaveLength(0);
  });
});

test.describe('Keyboard Accessibility', () => {

  test('skip link is first focusable element @a11y @keyboard', async ({ page }) => {
    await page.goto('/');

    await page.keyboard.press('Tab');
    const focused = await page.locator(':focus');

    const hasSkipLink = await focused.evaluate(el =>
      el.classList.contains('skip-link') ||
      el.textContent.toLowerCase().includes('skip')
    );

    expect(hasSkipLink).toBe(true);
  });

  test('all interactive elements are keyboard accessible @a11y @keyboard', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.keyboard'])
      .analyze();

    expect(results.violations).toHaveLength(0);
  });

  test('tab navigation follows logical order @a11y @keyboard', async ({ page }) => {
    await page.goto('/');

    const tabbableElements = [];

    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.locator(':focus');
      const tagName = await focused.evaluate(el => el.tagName.toLowerCase());
      const text = await focused.textContent();

      tabbableElements.push({ tagName, text: text?.trim() });
    }

    // Should tab through logical order: skip link -> nav -> hero CTAs
    expect(tabbableElements.length).toBeGreaterThan(0);
    expect(tabbableElements[0].text).toContain('Skip');
  });

  test('tab panels are keyboard navigable @a11y @keyboard @tabs', async ({ page }) => {
    await page.goto('/#dashboard');

    // Focus first tab
    await page.focus('button[role="tab"]');

    // Arrow right should move to next tab
    await page.keyboard.press('ArrowRight');
    const focused = await page.locator(':focus');
    const ariaControls = await focused.getAttribute('aria-controls');

    expect(ariaControls).toBeTruthy();
  });
});

test.describe('ARIA Attributes', () => {

  test('all buttons have accessible names @a11y @aria', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.name-role-value'])
      .analyze();

    const buttonNameViolations = results.violations.filter(
      v => v.id === 'button-name'
    );

    expect(buttonNameViolations).toHaveLength(0);
  });

  test('all images have alt text @a11y @aria', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.text-alternatives'])
      .analyze();

    const altTextViolations = results.violations.filter(
      v => v.id === 'image-alt'
    );

    expect(altTextViolations).toHaveLength(0);
  });

  test('tab list has correct ARIA attributes @a11y @aria @tabs', async ({ page }) => {
    await page.goto('/#dashboard');

    const tabList = page.locator('[role="tablist"]');
    await expect(tabList).toBeVisible();

    const tabs = await page.$$('[role="tab"]');
    expect(tabs.length).toBeGreaterThan(0);

    for (const tab of tabs) {
      const ariaControls = await tab.getAttribute('aria-controls');
      const ariaSelected = await tab.getAttribute('aria-selected');

      expect(ariaControls).toBeTruthy();
      expect(['true', 'false']).toContain(ariaSelected);
    }
  });

  test('tab panels have correct ARIA attributes @a11y @aria @tabs', async ({ page }) => {
    await page.goto('/#dashboard');

    const panels = await page.$$('[role="tabpanel"]');
    expect(panels.length).toBeGreaterThan(0);

    for (const panel of panels) {
      const ariaLabelledby = await panel.getAttribute('aria-labelledby');
      expect(ariaLabelledby).toBeTruthy();
    }
  });

  test('charts have aria-labels @a11y @aria @chart', async ({ page }) => {
    await page.goto('/#dashboard');
    await page.click('button[aria-controls="sources-panel"]');
    await page.waitForTimeout(1500);

    const charts = await page.$$('canvas');
    expect(charts.length).toBeGreaterThan(0);

    for (const chart of charts) {
      const ariaLabel = await chart.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel.length).toBeGreaterThan(15); // Descriptive label
    }
  });
});

test.describe('Semantic HTML', () => {

  test('page has proper heading hierarchy @a11y @semantics', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.structure'])
      .analyze();

    const headingViolations = results.violations.filter(
      v => v.id.includes('heading')
    );

    expect(headingViolations).toHaveLength(0);
  });

  test('page has exactly one h1 @a11y @semantics', async ({ page }) => {
    await page.goto('/');

    const h1Count = await page.$$eval('h1', h1s => h1s.length);
    expect(h1Count).toBe(1);
  });

  test('landmark regions are properly defined @a11y @semantics', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.structure'])
      .analyze();

    const landmarkViolations = results.violations.filter(
      v => v.id.includes('landmark') || v.id.includes('region')
    );

    expect(landmarkViolations).toHaveLength(0);
  });
});

test.describe('Focus Management', () => {

  test('focus is visible on all interactive elements @a11y @focus', async ({ page }) => {
    await page.goto('/');

    const interactiveSelectors = [
      'a',
      'button',
      'input',
      '[tabindex]:not([tabindex="-1"])'
    ];

    for (const selector of interactiveSelectors) {
      const elements = await page.$$(selector);

      for (let i = 0; i < Math.min(elements.length, 5); i++) {
        const element = elements[i];
        await element.focus();

        const hasVisibleFocus = await element.evaluate(el => {
          const styles = window.getComputedStyle(el);
          return styles.outlineWidth !== '0px' || styles.outline !== 'none';
        });

        expect(hasVisibleFocus).toBe(true);
      }
    }
  });

  test('focus is not trapped outside modals @a11y @focus', async ({ page }) => {
    await page.goto('/');

    // Tab through page
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Tab');
    }

    // Focus should still be within body
    const focused = await page.locator(':focus');
    await expect(focused).toBeVisible();
  });
});

test.describe('Forms and Inputs', () => {

  test('form inputs have labels @a11y @forms', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['cat.forms'])
      .analyze();

    const labelViolations = results.violations.filter(
      v => v.id === 'label' || v.id === 'form-field-multiple-labels'
    );

    expect(labelViolations).toHaveLength(0);
  });
});
