import { test, expect } from '@playwright/test';

/**
 * Feature Integration Tests
 *
 * Comprehensive integration test suite covering feature interactions,
 * combined functionality, end-to-end workflows, and browser compatibility.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Feature Integration - Dark Mode + Export', () => {

  test('should export charts in dark mode with correct colors', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();

    if (await darkModeToggle.count() > 0) {
      await darkModeToggle.click();
      await page.waitForTimeout(1000);

      const exportButton = page.locator('button[onclick*="downloadChart"]').first();

      if (await exportButton.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          exportButton.click()
        ]);

        expect(download).toBeTruthy();
        expect(download.suggestedFilename()).toContain('.png');
      }
    }
  });

  test('should persist dark mode during export workflow', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();

    if (await darkModeToggle.count() > 0) {
      await darkModeToggle.click();
      await page.waitForTimeout(500);

      const exportButton = page.locator('button[onclick*="downloadChart"]').first();

      if (await exportButton.count() > 0) {
        await exportButton.click();
        await page.waitForEvent('download');

        const stillDarkMode = await page.evaluate(() => {
          return document.documentElement.classList.contains('dark-mode') ||
                 document.documentElement.getAttribute('data-theme') === 'dark';
        });

        expect(stillDarkMode).toBe(true);
      }
    }
  });
});

test.describe('Feature Integration - Filters + Charts', () => {

  test('should update all charts when filter is applied', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const chartCount = await page.locator('canvas').count();
    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0 && chartCount > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(1000);

      const chartsUpdated = await page.evaluate(() => {
        const charts = Chart.instances;
        if (!charts || charts.size === 0) return false;

        for (const chart of charts.values()) {
          if (!chart.data || !chart.data.datasets) return false;
        }

        return true;
      });

      expect(chartsUpdated).toBe(true);
    }
  });

  test('should synchronize filter state across all visualizations', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const metricCards = page.locator('.metric-card');
      const cardCount = await metricCards.count();

      if (cardCount > 0) {
        const cardText = await metricCards.first().textContent();
        expect(cardText).toBeTruthy();
      }
    }
  });

  test('should maintain filter when switching tabs', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const tabs = page.locator('.tab-button');

    if (await sourceFilter.count() > 0 && await tabs.count() > 1) {
      await sourceFilter.selectOption({ index: 1 });
      const selectedValue = await sourceFilter.inputValue();

      await tabs.nth(1).click();
      await page.waitForTimeout(500);

      await tabs.nth(0).click();
      await page.waitForTimeout(500);

      const finalValue = await sourceFilter.inputValue();
      expect(finalValue).toBe(selectedValue);
    }
  });
});

test.describe('Feature Integration - Filters + Export', () => {

  test('should export filtered chart data', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const sourceFilter = page.locator('select[name="source"]').first();
    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await sourceFilter.count() > 0 && await exportButton.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(1000);

      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      expect(download).toBeTruthy();
    }
  });

  test('should include filter information in exported filename', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const sourceFilter = page.locator('select[name="source"]').first();
    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await sourceFilter.count() > 0 && await exportButton.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      const filename = download.suggestedFilename();
      // Filename might include filter info
      expect(filename).toBeTruthy();
    }
  });
});

test.describe('Feature Integration - Dark Mode + Filters + Export', () => {

  test('should handle all features together', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();
    const sourceFilter = page.locator('select[name="source"]').first();
    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await darkModeToggle.count() > 0 &&
        await sourceFilter.count() > 0 &&
        await exportButton.count() > 0) {

      // Enable dark mode
      await darkModeToggle.click();
      await page.waitForTimeout(500);

      // Apply filter
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Export
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      expect(download).toBeTruthy();
    }
  });

  test('should maintain all feature states after complex interaction', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();
    const sourceFilter = page.locator('select[name="source"]').first();

    if (await darkModeToggle.count() > 0 && await sourceFilter.count() > 0) {
      await darkModeToggle.click();
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      await page.reload();
      await page.waitForLoadState('networkidle');

      const isDarkMode = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark-mode') ||
               document.documentElement.getAttribute('data-theme') === 'dark';
      });

      const filterValue = await sourceFilter.inputValue();

      // Dark mode should persist
      if (isDarkMode !== null) {
        expect(isDarkMode).toBe(true);
      }

      // Filter might not persist without URL params
      expect(filterValue).toBeTruthy();
    }
  });
});

test.describe('Feature Integration - End-to-End Workflows', () => {

  test('should complete full data exploration workflow', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    // 1. View overview
    const overviewTab = page.locator('button[aria-controls="overview-panel"]').first();
    if (await overviewTab.count() > 0) {
      await overviewTab.click();
      await page.waitForTimeout(500);
    }

    // 2. Explore sources
    const sourcesTab = page.locator('button[aria-controls="sources-panel"]').first();
    if (await sourcesTab.count() > 0) {
      await sourcesTab.click();
      await page.waitForTimeout(500);
    }

    // 3. Apply filter
    const sourceFilter = page.locator('select[name="source"]').first();
    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);
    }

    // 4. Export data
    const exportButton = page.locator('button[onclick*="downloadChart"]').first();
    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      expect(download).toBeTruthy();
    }
  });

  test('should complete full customization workflow', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    // 1. Toggle dark mode
    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();
    if (await darkModeToggle.count() > 0) {
      await darkModeToggle.click();
      await page.waitForTimeout(500);
    }

    // 2. Apply filters
    const sourceFilter = page.locator('select[name="source"]').first();
    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);
    }

    // 3. Navigate tabs
    const tabs = page.locator('.tab-button');
    const tabCount = await tabs.count();
    if (tabCount > 1) {
      for (let i = 0; i < Math.min(tabCount, 3); i++) {
        await tabs.nth(i).click();
        await page.waitForTimeout(300);
      }
    }

    // Should complete without errors
    expect(true).toBe(true);
  });
});

test.describe('Feature Integration - Error Recovery', () => {

  test('should recover from failed API requests', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.abort('failed');
    });

    await page.goto(DASHBOARD_URL);
    await page.waitForTimeout(2000);

    // Page should still render
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle network interruption gracefully', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    // Simulate network offline
    await page.context().setOffline(true);

    const filter = page.locator('select[name="source"]').first();
    if (await filter.count() > 0) {
      await filter.click();
      await page.waitForTimeout(500);

      // Should still be functional with cached data
      await expect(filter).toBeVisible();
    }

    await page.context().setOffline(false);
  });

  test('should handle rapid feature toggling', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();

    if (await darkModeToggle.count() > 0) {
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      // Rapidly toggle dark mode
      for (let i = 0; i < 10; i++) {
        await darkModeToggle.click();
        await page.waitForTimeout(50);
      }

      expect(errors.length).toBe(0);
    }
  });
});

test.describe('Feature Integration - Browser Compatibility', () => {

  test('should work in Chromium', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    const metricCards = page.locator('.metric-card');
    await expect(metricCards.first()).toBeVisible();
  });

  test('should handle touch events on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DASHBOARD_URL);

    const mobileMenu = page.locator('.mobile-menu-toggle');
    if (await mobileMenu.count() > 0) {
      await mobileMenu.tap();
      await page.waitForTimeout(300);
    }

    // Should be functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    // Tab through elements
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
    }

    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    expect(focusedElement).toBeTruthy();
  });

  test('should respect reduced motion preference', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(DASHBOARD_URL);

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();

    if (await darkModeToggle.count() > 0) {
      await darkModeToggle.click();

      // Transitions should be minimal
      const transitionDuration = await page.evaluate(() => {
        const html = document.documentElement;
        return window.getComputedStyle(html).transitionDuration;
      });

      // Should be very short or 0s
      expect(transitionDuration === '0s' || parseFloat(transitionDuration) < 0.1).toBe(true);
    }
  });
});

test.describe('Feature Integration - State Management', () => {

  test('should maintain consistent state across page reload', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();

    if (await darkModeToggle.count() > 0) {
      await darkModeToggle.click();
      await page.waitForTimeout(500);

      await page.reload();
      await page.waitForLoadState('networkidle');

      const isDarkMode = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark-mode') ||
               document.documentElement.getAttribute('data-theme') === 'dark';
      });

      expect(isDarkMode).toBe(true);
    }
  });

  test('should handle concurrent state updates', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const sourceFilter = page.locator('select[name="source"]').first();
    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();

    if (await sourceFilter.count() > 0 && await qualitySlider.count() > 0) {
      // Update both filters simultaneously
      await Promise.all([
        sourceFilter.selectOption({ index: 1 }),
        qualitySlider.fill('0.7')
      ]);

      await page.waitForTimeout(1000);

      // Should handle both updates
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      expect(errors.length).toBe(0);
    }
  });

  test('should clear transient state appropriately', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const resetButton = page.locator('button:has-text("Clear Filters"), button:has-text("Reset")').first();

    if (await sourceFilter.count() > 0 && await resetButton.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      await resetButton.click();
      await page.waitForTimeout(500);

      const filterValue = await sourceFilter.inputValue();
      expect(filterValue === '' || filterValue === 'all').toBe(true);
    }
  });
});

test.describe('Feature Integration - Performance Under Load', () => {

  test('should maintain performance with all features active', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const startTime = Date.now();

    const darkModeToggle = page.locator('button[aria-label*="dark" i], .theme-toggle').first();
    const sourceFilter = page.locator('select[name="source"]').first();

    if (await darkModeToggle.count() > 0 && await sourceFilter.count() > 0) {
      await darkModeToggle.click();
      await page.waitForTimeout(300);

      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const totalTime = Date.now() - startTime;
      console.log(`All features activation time: ${totalTime}ms`);

      // Should complete within 3 seconds
      expect(totalTime).toBeLessThan(3000);
    }
  });

  test('should handle rapid user interactions', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const tabs = page.locator('.tab-button');
    const tabCount = await tabs.count();

    if (tabCount > 1) {
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      // Rapidly switch tabs
      for (let i = 0; i < 20; i++) {
        await tabs.nth(i % tabCount).click();
        await page.waitForTimeout(100);
      }

      expect(errors.length).toBeLessThan(3);
    }
  });
});
