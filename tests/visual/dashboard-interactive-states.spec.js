import { test, expect } from '@playwright/test';

/**
 * Interactive State Visual Regression Tests
 *
 * Tests for interactive elements like tab navigation, hover states,
 * and dynamic content changes to ensure visual consistency.
 */

test.describe('Tab Navigation States', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/#dashboard');
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => window.metricsLoaded === true, { timeout: 10000 })
      .catch(() => {});
  });

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'sources', label: 'Data Sources' },
    { id: 'quality', label: 'Quality Metrics' },
    { id: 'pipeline', label: 'Pipeline Performance' },
    { id: 'reports', label: 'Technical Reports' },
  ];

  for (const tab of tabs) {
    test(`${tab.label} tab active state renders correctly @visual @interactive`, async ({ page }) => {
      // Click tab
      await page.click(`button[aria-controls="${tab.id}-panel"]`);

      // Wait for tab panel to be visible
      await page.waitForSelector(`#${tab.id}-panel`, { state: 'visible' });

      // Wait for any charts to render
      if (tab.id === 'sources' || tab.id === 'quality' || tab.id === 'pipeline') {
        await page.waitForTimeout(1500); // Allow Chart.js animations
      }

      // Take screenshot of active tab button
      const tabButton = page.locator(`button[aria-controls="${tab.id}-panel"]`);
      await expect(tabButton).toHaveScreenshot(`tab-button-${tab.id}-active.png`);

      // Take screenshot of tab panel content
      const tabPanel = page.locator(`#${tab.id}-panel`);
      await expect(tabPanel).toHaveScreenshot(`tab-panel-${tab.id}.png`);
    });
  }

  test('tab list renders correctly with one active tab @visual', async ({ page }) => {
    await page.click('button[aria-controls="sources-panel"]');
    await page.waitForSelector('#sources-panel', { state: 'visible' });

    const tabList = page.locator('[role="tablist"]');
    await expect(tabList).toHaveScreenshot('tab-list-sources-active.png');
  });
});

test.describe('Hover States', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('CTA button hover state renders correctly @visual @hover', async ({ page }) => {
    const ctaButton = page.locator('#view-dashboard-btn');
    await ctaButton.hover();
    await page.waitForTimeout(300); // Wait for hover transition

    await expect(ctaButton).toHaveScreenshot('cta-button-hover.png');
  });

  test('navigation link hover state renders correctly @visual @hover', async ({ page }) => {
    const navLink = page.locator('.nav-links a').first();
    await navLink.hover();
    await page.waitForTimeout(300);

    await expect(navLink).toHaveScreenshot('nav-link-hover.png');
  });

  test('source card hover state renders correctly @visual @hover', async ({ page }) => {
    await page.goto('/#dashboard');
    await page.waitForLoadState('networkidle');

    const sourceCard = page.locator('.source-card.wikipedia').first();
    await sourceCard.scrollIntoViewIfNeeded();
    await sourceCard.hover();
    await page.waitForTimeout(400); // Wait for lift transition

    await expect(sourceCard).toHaveScreenshot('source-card-hover.png');
  });

  test('lifecycle stage hover state renders correctly @visual @hover', async ({ page }) => {
    const stage = page.locator('.lifecycle-stage').first();
    await stage.scrollIntoViewIfNeeded();
    await stage.hover();
    await page.waitForTimeout(300);

    await expect(stage).toHaveScreenshot('lifecycle-stage-hover.png');
  });
});

test.describe('Focus States', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('focused button has visible outline @visual @focus', async ({ page }) => {
    // Tab to first focusable element
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);

    const focused = page.locator(':focus');
    await expect(focused).toBeVisible();
    await expect(focused).toHaveScreenshot('focus-button.png');
  });

  test('focused link has visible outline @visual @focus', async ({ page }) => {
    // Tab through to navigation link
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press('Tab');
    }
    await page.waitForTimeout(200);

    const focused = page.locator(':focus');
    await expect(focused).toHaveScreenshot('focus-link.png');
  });

  test('focused tab has visible outline @visual @focus', async ({ page }) => {
    await page.goto('/#dashboard');

    // Focus tab list
    const tabButton = page.locator('button[role="tab"]').first();
    await tabButton.focus();
    await page.waitForTimeout(200);

    await expect(tabButton).toHaveScreenshot('focus-tab.png');
  });
});

test.describe('Loading States', () => {

  test('loading spinner renders correctly @visual @loading', async ({ page }) => {
    // Intercept metrics request to delay it
    await page.route('**/all_metrics.json', route => {
      setTimeout(() => route.continue(), 2000);
    });

    await page.goto('/');

    // Should show loading state
    const loading = page.locator('.loading').first();
    await expect(loading).toBeVisible({ timeout: 1000 });
    await expect(loading).toHaveScreenshot('loading-state.png');
  });
});

test.describe('Error States', () => {

  test('error message renders correctly @visual @error', async ({ page }) => {
    // Intercept metrics request and return error
    await page.route('**/all_metrics.json', route => {
      route.abort('failed');
    });

    await page.goto('/');
    await page.waitForTimeout(2000); // Wait for fetch to fail

    // Check if error message is shown
    const errorElement = page.locator('.error-message, .loading-error').first();
    if (await errorElement.isVisible()) {
      await expect(errorElement).toHaveScreenshot('error-state.png');
    }
  });
});

test.describe('Chart Interactive States', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/#dashboard');
    await page.waitForLoadState('networkidle');
    await page.click('button[aria-controls="sources-panel"]');
    await page.waitForSelector('#sources-panel', { state: 'visible' });
    await page.waitForTimeout(1500); // Wait for charts to render
  });

  test('chart tooltip on hover renders correctly @visual @chart', async ({ page }) => {
    const chart = page.locator('canvas#sourceBalanceChart');
    await chart.scrollIntoViewIfNeeded();

    // Hover over chart to show tooltip
    const box = await chart.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(500);

      // Take screenshot of chart area
      await expect(chart).toHaveScreenshot('chart-with-tooltip.png');
    }
  });
});

test.describe('Smooth Scroll Animation', () => {

  test('scroll-to-dashboard button works correctly @visual @animation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click view dashboard button
    await page.click('#view-dashboard-btn');

    // Wait for scroll animation
    await page.waitForTimeout(1000);

    // Dashboard should be in view
    const dashboard = page.locator('#dashboard');
    await expect(dashboard).toBeInViewport();

    // Take screenshot of current viewport
    await expect(page).toHaveScreenshot('after-scroll-to-dashboard.png');
  });
});
