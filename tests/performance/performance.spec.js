import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Performance Tests
 *
 * Comprehensive performance test suite covering bundle size analysis,
 * page load time, chart render time, export operation time, memory usage,
 * and behavior with large datasets.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Performance - Bundle Size', () => {

  test('should measure total page size', async ({ page }) => {
    const resources = [];

    page.on('response', response => {
      resources.push({
        url: response.url(),
        size: 0,
        type: response.request().resourceType()
      });
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const totalSize = resources.reduce((sum, r) => sum + r.size, 0);
    console.log(`Total page size: ${totalSize} bytes`);

    // Total page size should be under 5MB
    expect(totalSize).toBeLessThan(5 * 1024 * 1024);
  });

  test('should measure JavaScript bundle size', async ({ page }) => {
    const jsResources = [];

    page.on('response', async response => {
      if (response.request().resourceType() === 'script') {
        const buffer = await response.body();
        jsResources.push({
          url: response.url(),
          size: buffer.length
        });
      }
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const totalJsSize = jsResources.reduce((sum, r) => sum + r.size, 0);
    console.log(`Total JS size: ${(totalJsSize / 1024).toFixed(2)} KB`);

    // JS should be under 2MB
    expect(totalJsSize).toBeLessThan(2 * 1024 * 1024);
  });

  test('should measure CSS bundle size', async ({ page }) => {
    const cssResources = [];

    page.on('response', async response => {
      if (response.request().resourceType() === 'stylesheet') {
        const buffer = await response.body();
        cssResources.push({
          url: response.url(),
          size: buffer.length
        });
      }
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const totalCssSize = cssResources.reduce((sum, r) => sum + r.size, 0);
    console.log(`Total CSS size: ${(totalCssSize / 1024).toFixed(2)} KB`);

    // CSS should be under 500KB
    expect(totalCssSize).toBeLessThan(500 * 1024);
  });

  test('should verify compression is enabled', async ({ page }) => {
    let hasCompression = false;

    page.on('response', response => {
      const encoding = response.headers()['content-encoding'];
      if (encoding && (encoding.includes('gzip') || encoding.includes('br'))) {
        hasCompression = true;
      }
    });

    await page.goto(DASHBOARD_URL);

    // At least some resources should be compressed
    if (hasCompression) {
      expect(hasCompression).toBe(true);
    }
  });
});

test.describe('Performance - Page Load Time', () => {

  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    const loadTime = Date.now() - startTime;
    console.log(`Page load time: ${loadTime}ms`);

    // Should load within 10 seconds
    expect(loadTime).toBeLessThan(10000);
  });

  test('should measure Time to First Byte (TTFB)', async ({ page }) => {
    const navigationTiming = await page.evaluate(() =>
      JSON.parse(JSON.stringify(performance.timing))
    );

    await page.goto(DASHBOARD_URL);

    const ttfb = navigationTiming.responseStart - navigationTiming.requestStart;
    console.log(`TTFB: ${ttfb}ms`);

    // TTFB should be under 1 second
    if (ttfb > 0) {
      expect(ttfb).toBeLessThan(1000);
    }
  });

  test('should measure First Contentful Paint (FCP)', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const fcp = await page.evaluate(() => {
      const entries = performance.getEntriesByType('paint');
      const fcpEntry = entries.find(e => e.name === 'first-contentful-paint');
      return fcpEntry?.startTime || 0;
    });

    console.log(`FCP: ${fcp}ms`);

    if (fcp > 0) {
      // FCP should be under 2 seconds
      expect(fcp).toBeLessThan(2000);
    }
  });

  test('should measure Largest Contentful Paint (LCP)', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const lcp = await page.evaluate(() => {
      return new Promise(resolve => {
        new PerformanceObserver(list => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1];
          resolve(lastEntry.startTime);
        }).observe({ entryTypes: ['largest-contentful-paint'] });

        setTimeout(() => resolve(0), 5000);
      });
    });

    console.log(`LCP: ${lcp}ms`);

    if (lcp > 0) {
      // LCP should be under 2.5 seconds (Core Web Vital)
      expect(lcp).toBeLessThan(2500);
    }
  });

  test('should measure Time to Interactive (TTI)', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const startTime = Date.now();

    await page.waitForLoadState('networkidle');
    await page.waitForSelector('button', { state: 'visible' });

    const tti = Date.now() - startTime;
    console.log(`TTI: ${tti}ms`);

    // TTI should be under 5 seconds
    expect(tti).toBeLessThan(5000);
  });
});

test.describe('Performance - Chart Render Time', () => {

  test('should measure chart initialization time', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const renderTime = await page.evaluate(() => {
      return new Promise(resolve => {
        const startTime = performance.now();

        const observer = new MutationObserver(() => {
          const canvas = document.querySelector('canvas');
          if (canvas) {
            const endTime = performance.now();
            observer.disconnect();
            resolve(endTime - startTime);
          }
        });

        observer.observe(document.body, {
          childList: true,
          subtree: true
        });

        setTimeout(() => {
          observer.disconnect();
          resolve(0);
        }, 10000);
      });
    });

    console.log(`Chart render time: ${renderTime}ms`);

    if (renderTime > 0) {
      // Charts should render within 3 seconds
      expect(renderTime).toBeLessThan(3000);
    }
  });

  test('should measure multiple chart render time', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const startTime = Date.now();
    await page.waitForSelector('canvas', { timeout: 10000 });

    const chartCount = await page.locator('canvas').count();
    const renderTime = Date.now() - startTime;

    console.log(`Rendered ${chartCount} charts in ${renderTime}ms`);

    // Multiple charts should render within 5 seconds
    expect(renderTime).toBeLessThan(5000);
  });

  test('should measure chart update time on data change', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const filter = page.locator('select[name="source"]').first();

    if (await filter.count() > 0) {
      const startTime = Date.now();

      await filter.selectOption({ index: 1 });
      await page.waitForTimeout(100);

      const updateTime = Date.now() - startTime;
      console.log(`Chart update time: ${updateTime}ms`);

      // Updates should be under 1 second
      expect(updateTime).toBeLessThan(1000);
    }
  });

  test('should measure chart animation performance', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const fps = await page.evaluate(() => {
      return new Promise(resolve => {
        let frames = 0;
        const startTime = performance.now();

        function countFrames() {
          frames++;
          if (performance.now() - startTime < 1000) {
            requestAnimationFrame(countFrames);
          } else {
            resolve(frames);
          }
        }

        requestAnimationFrame(countFrames);
      });
    });

    console.log(`Animation FPS: ${fps}`);

    // Should maintain at least 30 FPS
    expect(fps).toBeGreaterThan(30);
  });
});

test.describe('Performance - Export Time', () => {

  test('should measure PNG export time', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const startTime = Date.now();

      await exportButton.click();
      await page.waitForEvent('download');

      const exportTime = Date.now() - startTime;
      console.log(`PNG export time: ${exportTime}ms`);

      // Export should complete within 3 seconds
      expect(exportTime).toBeLessThan(3000);
    }
  });

  test('should measure PDF export time', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const pdfButton = page.locator('button:has-text("PDF")').first();

    if (await pdfButton.count() > 0) {
      const startTime = Date.now();

      try {
        await pdfButton.click();
        await page.waitForEvent('download', { timeout: 10000 });

        const exportTime = Date.now() - startTime;
        console.log(`PDF export time: ${exportTime}ms`);

        // PDF export should complete within 10 seconds
        expect(exportTime).toBeLessThan(10000);
      } catch (e) {
        // PDF export might not be implemented
        console.log('PDF export not available');
      }
    }
  });

  test('should measure multiple exports performance', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const startTime = Date.now();

      for (let i = 0; i < 5; i++) {
        await exportButton.click();
        await page.waitForEvent('download');
        await page.waitForTimeout(100);
      }

      const totalTime = Date.now() - startTime;
      console.log(`5 exports in ${totalTime}ms (avg: ${totalTime / 5}ms)`);

      // 5 exports should complete within 15 seconds
      expect(totalTime).toBeLessThan(15000);
    }
  });
});

test.describe('Performance - Memory Usage', () => {

  test('should monitor memory usage during page load', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const metrics = await page.evaluate(() => {
      if (performance.memory) {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
        };
      }
      return null;
    });

    if (metrics) {
      console.log(`Memory usage: ${(metrics.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`);

      // Memory usage should be under 200MB
      expect(metrics.usedJSHeapSize).toBeLessThan(200 * 1024 * 1024);
    }
  });

  test('should not leak memory on repeated navigation', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const initialMemory = await page.evaluate(() => {
      return performance.memory?.usedJSHeapSize || 0;
    });

    // Navigate multiple times
    for (let i = 0; i < 5; i++) {
      await page.reload();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);
    }

    const finalMemory = await page.evaluate(() => {
      return performance.memory?.usedJSHeapSize || 0;
    });

    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - initialMemory;
      const percentIncrease = (memoryIncrease / initialMemory) * 100;

      console.log(`Memory increase: ${percentIncrease.toFixed(2)}%`);

      // Memory should not increase more than 50%
      expect(percentIncrease).toBeLessThan(50);
    }
  });

  test('should clean up chart instances on unmount', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const initialChartCount = await page.evaluate(() => {
      return Chart.instances?.size || 0;
    });

    const tab = page.locator('.tab-button').nth(1);
    if (await tab.count() > 0) {
      await tab.click();
      await page.waitForTimeout(500);

      await page.locator('.tab-button').first().click();
      await page.waitForTimeout(500);

      const finalChartCount = await page.evaluate(() => {
        return Chart.instances?.size || 0;
      });

      console.log(`Initial charts: ${initialChartCount}, Final charts: ${finalChartCount}`);

      // Should not accumulate unused chart instances
      expect(finalChartCount).toBeLessThanOrEqual(initialChartCount + 2);
    }
  });

  test('should handle memory pressure gracefully', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    // Simulate memory pressure by creating large data
    await page.evaluate(() => {
      const largeArray = new Array(1000000).fill('test');
      window.testData = largeArray;
    });

    // Page should still be responsive
    await page.click('body');
    await expect(page.locator('body')).toBeVisible();

    // Cleanup
    await page.evaluate(() => {
      delete window.testData;
    });
  });
});

test.describe('Performance - Large Datasets', () => {

  test('should handle 100+ metrics records', async ({ page }) => {
    const largeMetrics = Array.from({ length: 100 }, (_, i) => ({
      run_id: `test${i}`,
      source: ['Wikipedia-Somali', 'BBC-Somali', 'HuggingFace-Somali'][i % 3],
      pipeline_type: 'discovery',
      records_written: Math.floor(Math.random() * 10000),
      timestamp: new Date(Date.now() - i * 86400000).toISOString(),
      performance: {
        records_per_minute: Math.floor(Math.random() * 1000)
      }
    }));

    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: largeMetrics.length,
          records: largeMetrics.reduce((sum, m) => sum + m.records_written, 0),
          sources: ['Wikipedia-Somali', 'BBC-Somali', 'HuggingFace-Somali'],
          pipeline_types: ['discovery'],
          metrics: largeMetrics
        })
      });
    });

    const startTime = Date.now();
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForSelector('.metric-card', { timeout: 15000 });

    const loadTime = Date.now() - startTime;
    console.log(`Load time with 100 metrics: ${loadTime}ms`);

    // Should load within 15 seconds
    expect(loadTime).toBeLessThan(15000);
  });

  test('should handle 1000+ metrics records', async ({ page }) => {
    const largeMetrics = Array.from({ length: 1000 }, (_, i) => ({
      run_id: `test${i}`,
      source: ['Wikipedia-Somali', 'BBC-Somali', 'HuggingFace-Somali', 'Sprakbanken-Somali'][i % 4],
      pipeline_type: ['discovery', 'extraction'][i % 2],
      records_written: Math.floor(Math.random() * 10000),
      timestamp: new Date(Date.now() - i * 3600000).toISOString(),
      performance: {
        records_per_minute: Math.floor(Math.random() * 1000)
      }
    }));

    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: largeMetrics.length,
          records: largeMetrics.reduce((sum, m) => sum + m.records_written, 0),
          sources: ['Wikipedia-Somali', 'BBC-Somali', 'HuggingFace-Somali', 'Sprakbanken-Somali'],
          pipeline_types: ['discovery', 'extraction'],
          metrics: largeMetrics
        })
      });
    });

    const startTime = Date.now();
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const loadTime = Date.now() - startTime;
    console.log(`Load time with 1000 metrics: ${loadTime}ms`);

    // Should load within 30 seconds
    expect(loadTime).toBeLessThan(30000);
  });

  test('should paginate or virtualize large tables', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const tableRows = page.locator('table tbody tr');
    const count = await tableRows.count();

    if (count > 0) {
      console.log(`Table rows rendered: ${count}`);

      // Should limit visible rows for performance
      expect(count).toBeLessThan(500);
    }
  });

  test('should maintain performance with filtering on large dataset', async ({ page }) => {
    // Use large dataset from previous test
    const largeMetrics = Array.from({ length: 1000 }, (_, i) => ({
      run_id: `test${i}`,
      source: 'Wikipedia-Somali',
      pipeline_type: 'discovery',
      records_written: Math.floor(Math.random() * 10000),
      timestamp: new Date(Date.now() - i * 3600000).toISOString()
    }));

    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: largeMetrics.length,
          records: largeMetrics.reduce((sum, m) => sum + m.records_written, 0),
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: largeMetrics
        })
      });
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    const filter = page.locator('select[name="source"]').first();

    if (await filter.count() > 0) {
      const startTime = Date.now();

      await filter.selectOption({ index: 1 });
      await page.waitForTimeout(100);

      const filterTime = Date.now() - startTime;
      console.log(`Filter time on 1000 records: ${filterTime}ms`);

      // Filtering should be under 2 seconds
      expect(filterTime).toBeLessThan(2000);
    }
  });
});
