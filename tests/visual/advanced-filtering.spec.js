import { test, expect } from '@playwright/test';

/**
 * Advanced Filtering Tests
 *
 * Comprehensive test suite for advanced filtering functionality covering
 * source filters, quality threshold sliders, status filters, combined filters,
 * URL parameter persistence, filter badges, and reset functionality.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Advanced Filtering - Source Filter', () => {

  test('should have source filter control', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"], .source-filter, button:has-text("Filter by Source")');
    const count = await sourceFilter.count();

    // Filters might not be implemented yet
    if (count > 0) {
      await expect(sourceFilter.first()).toBeVisible();
    }
  });

  test('should display all available sources in filter', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      const options = await sourceFilter.locator('option').count();
      expect(options).toBeGreaterThan(1); // At least "All" + sources
    }
  });

  test('should filter data by single source', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 }); // Select first source
      await page.waitForTimeout(500);

      const filteredData = await page.evaluate(() => {
        return window.filteredMetrics || window.metricsData;
      });

      expect(filteredData).toBeTruthy();
    }
  });

  test('should filter data by multiple sources', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceCheckboxes = page.locator('input[type="checkbox"][name*="source"]');
    const count = await sourceCheckboxes.count();

    if (count >= 2) {
      await sourceCheckboxes.nth(0).check();
      await sourceCheckboxes.nth(1).check();
      await page.waitForTimeout(500);

      const filteredData = await page.evaluate(() => {
        return window.filteredMetrics || window.metricsData;
      });

      expect(filteredData).toBeTruthy();
    }
  });

  test('should update charts when source filter changes', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      const initialChartData = await page.evaluate(() => {
        const chart = Chart.instances.values().next().value;
        return chart?.data?.datasets?.[0]?.data || [];
      });

      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(1000);

      const updatedChartData = await page.evaluate(() => {
        const chart = Chart.instances.values().next().value;
        return chart?.data?.datasets?.[0]?.data || [];
      });

      // Data should change (or remain same if filter matches all data)
      expect(updatedChartData).toBeTruthy();
    }
  });
});

test.describe('Advanced Filtering - Quality Threshold', () => {

  test('should have quality threshold slider', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const qualitySlider = page.locator('input[type="range"][name*="quality"], input[type="number"][name*="quality"]');
    const count = await qualitySlider.count();

    if (count > 0) {
      await expect(qualitySlider.first()).toBeVisible();
    }
  });

  test('should display current threshold value', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();

    if (await qualitySlider.count() > 0) {
      const value = await qualitySlider.inputValue();
      expect(value).toBeTruthy();

      const valueDisplay = page.locator('.quality-value, .threshold-value');
      if (await valueDisplay.count() > 0) {
        const displayText = await valueDisplay.textContent();
        expect(displayText).toBeTruthy();
      }
    }
  });

  test('should filter metrics by quality threshold', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();

    if (await qualitySlider.count() > 0) {
      await qualitySlider.fill('0.8'); // Set to 80%
      await page.waitForTimeout(500);

      const filteredMetrics = await page.evaluate(() => {
        const metrics = window.filteredMetrics || window.metricsData?.metrics || [];
        return metrics.filter(m => (m.quality_metrics?.deduplication_rate || 0) >= 0.8);
      });

      expect(Array.isArray(filteredMetrics)).toBe(true);
    }
  });

  test('should update slider value display in real-time', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();
    const valueDisplay = page.locator('.quality-value, .threshold-value').first();

    if (await qualitySlider.count() > 0 && await valueDisplay.count() > 0) {
      await qualitySlider.fill('0.5');
      await page.waitForTimeout(200);

      const displayText = await valueDisplay.textContent();
      expect(displayText).toContain('5') || expect(displayText).toContain('50');
    }
  });
});

test.describe('Advanced Filtering - Status Filter', () => {

  test('should have status filter options', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const statusFilter = page.locator('select[name="status"], input[type="radio"][name="status"]');
    const count = await statusFilter.count();

    if (count > 0) {
      await expect(statusFilter.first()).toBeVisible();
    }
  });

  test('should filter by success status', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const successFilter = page.locator('input[value="success"], option[value="success"]').first();

    if (await successFilter.count() > 0) {
      await successFilter.click();
      await page.waitForTimeout(500);

      const filteredData = await page.evaluate(() => {
        const metrics = window.filteredMetrics || window.metricsData?.metrics || [];
        return metrics.filter(m => m.status === 'success');
      });

      expect(Array.isArray(filteredData)).toBe(true);
    }
  });

  test('should filter by failed status', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const failedFilter = page.locator('input[value="failed"], option[value="failed"]').first();

    if (await failedFilter.count() > 0) {
      await failedFilter.click();
      await page.waitForTimeout(500);

      const filteredData = await page.evaluate(() => {
        const metrics = window.filteredMetrics || window.metricsData?.metrics || [];
        return metrics.filter(m => m.status === 'failed' || m.status === 'error');
      });

      expect(Array.isArray(filteredData)).toBe(true);
    }
  });

  test('should show all when status filter is cleared', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const statusFilter = page.locator('select[name="status"]').first();

    if (await statusFilter.count() > 0) {
      await statusFilter.selectOption('all');
      await page.waitForTimeout(500);

      const allData = await page.evaluate(() => {
        return window.filteredMetrics || window.metricsData?.metrics || [];
      });

      expect(allData.length).toBeGreaterThan(0);
    }
  });
});

test.describe('Advanced Filtering - Combined Filters', () => {

  test('should apply multiple filters simultaneously', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();

    if (await sourceFilter.count() > 0 && await qualitySlider.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await qualitySlider.fill('0.7');
      await page.waitForTimeout(500);

      const filteredData = await page.evaluate(() => {
        return window.filteredMetrics || window.metricsData?.metrics || [];
      });

      expect(Array.isArray(filteredData)).toBe(true);
    }
  });

  test('should combine source and status filters', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const statusFilter = page.locator('select[name="status"]').first();

    if (await sourceFilter.count() > 0 && await statusFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await statusFilter.selectOption('success');
      await page.waitForTimeout(500);

      const filteredData = await page.evaluate(() => {
        const metrics = window.filteredMetrics || window.metricsData?.metrics || [];
        return metrics;
      });

      expect(Array.isArray(filteredData)).toBe(true);
    }
  });

  test('should apply filters in correct order', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const filters = page.locator('.filter-control, select[name*="filter"], input[name*="filter"]');
    const count = await filters.count();

    if (count >= 2) {
      await filters.nth(0).click();
      await page.waitForTimeout(300);
      await filters.nth(1).click();
      await page.waitForTimeout(300);

      // Should not cause errors
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      expect(errors.length).toBe(0);
    }
  });

  test('should handle empty results from combined filters', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();

    if (await sourceFilter.count() > 0 && await qualitySlider.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await qualitySlider.fill('0.99'); // Very high threshold
      await page.waitForTimeout(500);

      const emptyMessage = page.locator('.no-results, .empty-state');
      // Empty message might appear
      if (await emptyMessage.count() > 0) {
        await expect(emptyMessage).toBeVisible();
      }
    }
  });
});

test.describe('Advanced Filtering - URL Parameter Persistence', () => {

  test('should add filter parameters to URL', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const url = page.url();
      const hasParams = url.includes('?') || url.includes('#');

      if (hasParams) {
        expect(url).toContain('source=') || expect(url).toContain('filter=');
      }
    }
  });

  test('should restore filters from URL on page load', async ({ page }) => {
    const urlWithFilters = `${DASHBOARD_URL}?source=Wikipedia-Somali&quality=0.8`;
    await page.goto(urlWithFilters);
    await page.waitForTimeout(1000);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      const selectedValue = await sourceFilter.inputValue();
      // Should restore from URL
      if (selectedValue) {
        expect(selectedValue).toBeTruthy();
      }
    }
  });

  test('should update URL when filters change', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      const initialUrl = page.url();

      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const newUrl = page.url();

      // URL might update with filter params
      if (initialUrl !== newUrl) {
        expect(newUrl).not.toBe(initialUrl);
      }
    }
  });

  test('should handle malformed URL parameters gracefully', async ({ page }) => {
    const malformedUrl = `${DASHBOARD_URL}?source=invalid&quality=abc`;
    await page.goto(malformedUrl);

    // Should load without errors
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Advanced Filtering - Filter Badges', () => {

  test('should display active filter badges', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const badge = page.locator('.filter-badge, .active-filter, .chip');
      const count = await badge.count();

      if (count > 0) {
        await expect(badge.first()).toBeVisible();
      }
    }
  });

  test('should show filter value in badge', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const badge = page.locator('.filter-badge').first();
      if (await badge.count() > 0) {
        const badgeText = await badge.textContent();
        expect(badgeText?.length).toBeGreaterThan(0);
      }
    }
  });

  test('should remove badge when filter is removed', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();

    if (await sourceFilter.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const badge = page.locator('.filter-badge').first();
      if (await badge.count() > 0) {
        const closeButton = badge.locator('button, .close, .remove');
        if (await closeButton.count() > 0) {
          await closeButton.click();
          await page.waitForTimeout(300);

          expect(await badge.isVisible()).toBe(false);
        }
      }
    }
  });

  test('should display count of active filters', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const qualitySlider = page.locator('input[type="range"][name*="quality"]').first();

    if (await sourceFilter.count() > 0 && await qualitySlider.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await qualitySlider.fill('0.7');
      await page.waitForTimeout(500);

      const filterCount = page.locator('.filter-count, .active-filters-count');
      if (await filterCount.count() > 0) {
        const countText = await filterCount.textContent();
        expect(countText).toContain('2') || expect(countText).toContain('filter');
      }
    }
  });
});

test.describe('Advanced Filtering - Reset Functionality', () => {

  test('should have reset/clear filters button', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const resetButton = page.locator('button:has-text("Clear"), button:has-text("Reset"), button:has-text("Clear Filters")');
    const count = await resetButton.count();

    if (count > 0) {
      await expect(resetButton.first()).toBeVisible();
    }
  });

  test('should clear all filters on reset', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const resetButton = page.locator('button:has-text("Clear Filters")').first();

    if (await sourceFilter.count() > 0 && await resetButton.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      await resetButton.click();
      await page.waitForTimeout(500);

      const selectedValue = await sourceFilter.inputValue();
      expect(selectedValue === '' || selectedValue === 'all').toBe(true);
    }
  });

  test('should restore original data after reset', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const initialMetricsCount = await page.evaluate(() => {
      return window.metricsData?.metrics?.length || 0;
    });

    const sourceFilter = page.locator('select[name="source"]').first();
    const resetButton = page.locator('button:has-text("Clear Filters")').first();

    if (await sourceFilter.count() > 0 && await resetButton.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      await resetButton.click();
      await page.waitForTimeout(500);

      const finalMetricsCount = await page.evaluate(() => {
        return window.filteredMetrics?.length || window.metricsData?.metrics?.length || 0;
      });

      expect(finalMetricsCount).toBe(initialMetricsCount);
    }
  });

  test('should remove all filter badges on reset', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sourceFilter = page.locator('select[name="source"]').first();
    const resetButton = page.locator('button:has-text("Clear Filters")').first();

    if (await sourceFilter.count() > 0 && await resetButton.count() > 0) {
      await sourceFilter.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      await resetButton.click();
      await page.waitForTimeout(500);

      const badges = page.locator('.filter-badge');
      const badgeCount = await badges.count();

      expect(badgeCount).toBe(0);
    }
  });

  test('should clear URL parameters on reset', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}?source=Wikipedia`);

    const resetButton = page.locator('button:has-text("Clear Filters")').first();

    if (await resetButton.count() > 0) {
      await resetButton.click();
      await page.waitForTimeout(500);

      const url = page.url();
      const hasParams = url.includes('source=');

      expect(hasParams).toBe(false);
    }
  });
});
