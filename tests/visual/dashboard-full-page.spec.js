import { test, expect } from '@playwright/test';

/**
 * Full Page Visual Regression Tests
 *
 * These tests capture full-page screenshots at various viewports
 * to detect unintended visual changes across the entire dashboard.
 */

test.describe('Dashboard Full Page Snapshots', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard and wait for all content to load
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for metrics to load
    await page.waitForFunction(() => window.metricsLoaded === true, { timeout: 10000 })
      .catch(() => console.log('Metrics did not load, continuing with test'));
  });

  test('full page renders correctly on desktop @visual', async ({ page }) => {
    await expect(page).toHaveScreenshot('dashboard-full-desktop.png', {
      fullPage: true,
      maxDiffPixels: 200,  // Allow for dynamic content like dates
    });
  });

  test('hero section renders correctly @visual', async ({ page }) => {
    const hero = page.locator('.hero');
    await expect(hero).toBeVisible();
    await expect(hero).toHaveScreenshot('hero-section.png');
  });

  test('navigation bar renders correctly @visual', async ({ page }) => {
    const nav = page.locator('.global-nav');
    await expect(nav).toBeVisible();
    await expect(nav).toHaveScreenshot('navigation-bar.png');
  });

  test('dashboard section renders correctly @visual', async ({ page }) => {
    await page.locator('#dashboard').scrollIntoViewIfNeeded();
    await page.waitForTimeout(500); // Wait for scroll animation

    const dashboard = page.locator('#dashboard');
    await expect(dashboard).toBeVisible();
    await expect(dashboard).toHaveScreenshot('dashboard-section.png');
  });

  test('data story section renders correctly @visual', async ({ page }) => {
    await page.locator('#story').scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    const story = page.locator('.data-story');
    await expect(story).toBeVisible();
    await expect(story).toHaveScreenshot('data-story-section.png');
  });

  test('contribute section renders correctly @visual', async ({ page }) => {
    await page.locator('#get-involved').scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    const contribute = page.locator('.contribute');
    await expect(contribute).toBeVisible();
    await expect(contribute).toHaveScreenshot('contribute-section.png');
  });

  test('footer renders correctly @visual', async ({ page }) => {
    await page.locator('footer').scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
    await expect(footer).toHaveScreenshot('footer-section.png');
  });
});

test.describe('Responsive Breakpoints', () => {
  const breakpoints = [
    { name: 'mobile-sm', width: 320, height: 568 },
    { name: 'mobile-md', width: 375, height: 667 },
    { name: 'mobile-lg', width: 414, height: 896 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'desktop-sm', width: 1024, height: 768 },
    { name: 'desktop-md', width: 1440, height: 900 },
    { name: 'desktop-lg', width: 1920, height: 1080 },
  ];

  for (const bp of breakpoints) {
    test(`dashboard renders correctly at ${bp.name} (${bp.width}x${bp.height}) @visual @responsive`, async ({ page }) => {
      await page.setViewportSize({ width: bp.width, height: bp.height });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForFunction(() => window.metricsLoaded === true, { timeout: 10000 })
        .catch(() => {});

      await expect(page).toHaveScreenshot(`dashboard-${bp.name}.png`, {
        fullPage: true,
        maxDiffPixels: 300,  // More tolerance for responsive layouts
      });
    });
  }
});

test.describe('Print Styles', () => {
  test('dashboard renders correctly for print @visual @print', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Emulate print media
    await page.emulateMedia({ media: 'print' });

    await expect(page).toHaveScreenshot('dashboard-print.png', {
      fullPage: true,
    });
  });
});
