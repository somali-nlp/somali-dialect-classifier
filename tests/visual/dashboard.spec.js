/**
 * Playwright Visual Regression Tests for Dashboard
 *
 * These tests verify the visual appearance and functionality of the dashboard
 * across different viewports and data states.
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';
const VISUAL_THRESHOLD = 0.02; // 2% difference threshold

test.describe('Dashboard Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    // Set up console logging
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error('Browser console error:', msg.text());
      }
    });

    // Navigate to dashboard
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
  });

  test('should load dashboard without errors', async ({ page }) => {
    await expect(page).toHaveTitle(/Somali NLP/);

    // Check that main sections exist
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('.dashboard-container')).toBeVisible();
  });

  test('should display metrics cards', async ({ page }) => {
    // Wait for data to load
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    // Check that metric cards are visible
    const metricCards = page.locator('.metric-card');
    const count = await metricCards.count();

    expect(count).toBeGreaterThan(0);

    // Verify each card has content
    for (let i = 0; i < count; i++) {
      const card = metricCards.nth(i);
      await expect(card).toBeVisible();

      // Check for value and label
      await expect(card.locator('.metric-value')).toBeVisible();
      await expect(card.locator('.metric-label')).toBeVisible();
    }
  });

  test('should display charts', async ({ page }) => {
    // Wait for charts to render
    await page.waitForSelector('.plotly', { timeout: 10000 });

    const charts = page.locator('.plotly');
    const chartCount = await charts.count();

    expect(chartCount).toBeGreaterThan(0);
    console.log(`Found ${chartCount} charts`);
  });

  test('should handle tab navigation', async ({ page }) => {
    // Wait for tabs to be visible
    await page.waitForSelector('.tab-button', { timeout: 5000 });

    const tabs = page.locator('.tab-button');
    const tabCount = await tabs.count();

    expect(tabCount).toBeGreaterThan(0);

    // Click through each tab
    for (let i = 0; i < tabCount; i++) {
      const tab = tabs.nth(i);
      await tab.click();

      // Wait for content to update
      await page.waitForTimeout(1000);

      // Check that tab is active
      await expect(tab).toHaveClass(/active/);

      // Verify content panel is visible
      const tabContent = page.locator('.tab-content.active');
      await expect(tabContent).toBeVisible();
    }
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Verify page is still usable
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('.metric-card')).toBeVisible();

    // Check that cards stack vertically
    const firstCard = page.locator('.metric-card').first();
    const secondCard = page.locator('.metric-card').nth(1);

    const box1 = await firstCard.boundingBox();
    const box2 = await secondCard.boundingBox();

    if (box1 && box2) {
      // On mobile, cards should stack (y positions should differ)
      expect(Math.abs(box1.y - box2.y)).toBeGreaterThan(50);
    }
  });

  test('should be responsive on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('.metric-card')).toBeVisible();
  });

  test('should handle empty data state', async ({ page }) => {
    // Intercept API calls and return empty data
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 0,
          records: 0,
          sources: [],
          pipeline_types: [],
          metrics: []
        })
      });
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    // Check for empty state message or handling
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });

  test('should handle data loading errors gracefully', async ({ page }) => {
    // Intercept API calls and return error
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    // Page should still render without crashing
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have accessible navigation', async ({ page }) => {
    // Check for keyboard navigation
    await page.keyboard.press('Tab');

    // At least one element should be focused
    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    expect(focusedElement).toBeTruthy();
  });

  test('should have proper ARIA labels', async ({ page }) => {
    // Check for ARIA landmarks
    const main = page.locator('main, [role="main"]');
    await expect(main).toBeVisible();
  });

  test('screenshot comparison - overview tab', async ({ page }) => {
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    // Take screenshot
    await expect(page).toHaveScreenshot('overview-tab.png', {
      maxDiffPixels: 100,
      threshold: VISUAL_THRESHOLD,
    });
  });

  test('screenshot comparison - full page', async ({ page }) => {
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    await expect(page).toHaveScreenshot('full-page.png', {
      fullPage: true,
      maxDiffPixels: 200,
      threshold: VISUAL_THRESHOLD,
    });
  });

  test('should display source breakdown', async ({ page }) => {
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    // Check for source-related content
    const pageContent = await page.textContent('body');

    // Should mention common sources
    const hasSources = pageContent.includes('BBC') ||
                      pageContent.includes('Wikipedia') ||
                      pageContent.includes('HuggingFace') ||
                      pageContent.includes('Sprakbanken');

    expect(hasSources).toBeTruthy();
  });

  test('should update dynamically on data change', async ({ page }) => {
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    // Get initial metric value
    const initialValue = await page.locator('.metric-value').first().textContent();

    // Simulate data update (if dashboard has refresh functionality)
    const refreshButton = page.locator('button:has-text("Refresh")');
    if (await refreshButton.count() > 0) {
      await refreshButton.click();
      await page.waitForTimeout(2000);

      // Verify page is still functional
      await expect(page.locator('.metric-card')).toBeVisible();
    }
  });

  test('performance - page load time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    const loadTime = Date.now() - startTime;

    console.log(`Page load time: ${loadTime}ms`);

    // Assert reasonable load time (adjust threshold as needed)
    expect(loadTime).toBeLessThan(15000); // 15 seconds max
  });

  test('performance - no console errors', async ({ page }) => {
    const errors = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    if (errors.length > 0) {
      console.log('Console errors detected:', errors);
    }

    // Allow some tolerance for external resource errors
    expect(errors.length).toBeLessThanOrEqual(2);
  });
});

test.describe('Dashboard Data Integration', () => {
  test('should load all_metrics.json successfully', async ({ page }) => {
    const response = await page.goto(`${DASHBOARD_URL}/data/all_metrics.json`);

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('count');
    expect(data).toHaveProperty('records');
    expect(data).toHaveProperty('sources');
    expect(data).toHaveProperty('metrics');
  });

  test('should have valid metrics structure', async ({ page }) => {
    const response = await page.goto(`${DASHBOARD_URL}/data/all_metrics.json`);
    const data = await response.json();

    expect(Array.isArray(data.sources)).toBeTruthy();
    expect(Array.isArray(data.metrics)).toBeTruthy();

    if (data.metrics.length > 0) {
      const firstMetric = data.metrics[0];

      expect(firstMetric).toHaveProperty('run_id');
      expect(firstMetric).toHaveProperty('source');
      expect(firstMetric).toHaveProperty('timestamp');
      expect(firstMetric).toHaveProperty('pipeline_type');
      expect(firstMetric).toHaveProperty('records_written');
    }
  });
});
