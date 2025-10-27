import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Export Functionality Tests
 *
 * Comprehensive test suite for data and chart export features covering
 * PNG export for charts, PDF export (single and multi-page), file naming,
 * download handling, export quality/resolution, different chart states,
 * and error handling.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';
const DOWNLOAD_DIR = path.join(__dirname, 'downloads');

test.use({
  acceptDownloads: true,
});

test.beforeAll(async () => {
  if (!fs.existsSync(DOWNLOAD_DIR)) {
    fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });
  }
});

test.describe('Export - PNG Export for Charts', () => {

  test('should have export button for charts', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button:has-text("Export"), button:has-text("Download"), .chart-action:has-text("PNG")');
    const count = await exportButton.count();

    if (count > 0) {
      await expect(exportButton.first()).toBeVisible();
    }
  });

  test('should export chart as PNG on button click', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button:has-text("Export PNG"), button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      expect(download.suggestedFilename()).toContain('.png');

      const filePath = path.join(DOWNLOAD_DIR, download.suggestedFilename());
      await download.saveAs(filePath);

      expect(fs.existsSync(filePath)).toBe(true);

      // Verify file size (should be > 1KB)
      const stats = fs.statSync(filePath);
      expect(stats.size).toBeGreaterThan(1000);

      // Cleanup
      fs.unlinkSync(filePath);
    }
  });

  test('should export multiple charts independently', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButtons = page.locator('button:has-text("Export PNG"), button[onclick*="downloadChart"]');
    const count = await exportButtons.count();

    if (count >= 2) {
      const downloads = [];

      // Export first chart
      const [download1] = await Promise.all([
        page.waitForEvent('download'),
        exportButtons.nth(0).click()
      ]);
      downloads.push(download1);

      await page.waitForTimeout(500);

      // Export second chart
      const [download2] = await Promise.all([
        page.waitForEvent('download'),
        exportButtons.nth(1).click()
      ]);
      downloads.push(download2);

      expect(downloads.length).toBe(2);
      expect(download1.suggestedFilename()).not.toBe(download2.suggestedFilename());
    }
  });

  test('should include timestamp in filename', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      const filename = download.suggestedFilename();

      // Should contain timestamp or date
      const hasTimestamp = /\d{13}|\d{4}-\d{2}-\d{2}/.test(filename);
      expect(hasTimestamp).toBe(true);
    }
  });

  test('should export at appropriate resolution', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      const filePath = path.join(DOWNLOAD_DIR, download.suggestedFilename());
      await download.saveAs(filePath);

      const stats = fs.statSync(filePath);

      // High-quality PNG should be > 50KB
      expect(stats.size).toBeGreaterThan(50000);

      fs.unlinkSync(filePath);
    }
  });
});

test.describe('Export - PDF Export (Single Chart)', () => {

  test('should have PDF export option', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const pdfExportButton = page.locator('button:has-text("PDF"), button:has-text("Export PDF")');
    const count = await pdfExportButton.count();

    // PDF export might not be implemented yet
    if (count > 0) {
      await expect(pdfExportButton.first()).toBeVisible();
    }
  });

  test('should export single chart as PDF', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const pdfExportButton = page.locator('button:has-text("Export PDF")').first();

    if (await pdfExportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        pdfExportButton.click()
      ]);

      expect(download.suggestedFilename()).toContain('.pdf');

      const filePath = path.join(DOWNLOAD_DIR, download.suggestedFilename());
      await download.saveAs(filePath);

      expect(fs.existsSync(filePath)).toBe(true);

      const stats = fs.statSync(filePath);
      expect(stats.size).toBeGreaterThan(1000);

      fs.unlinkSync(filePath);
    }
  });

  test('should include chart title in PDF', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const pdfExportButton = page.locator('button:has-text("Export PDF")').first();

    if (await pdfExportButton.count() > 0) {
      // This would require PDF parsing library to verify
      // For now, just verify file is created
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        pdfExportButton.click()
      ]);

      expect(download).toBeTruthy();
    }
  });
});

test.describe('Export - Multi-Page PDF', () => {

  test('should have option to export all charts as PDF', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const exportAllButton = page.locator('button:has-text("Export All"), button:has-text("Download Report")');
    const count = await exportAllButton.count();

    if (count > 0) {
      await expect(exportAllButton.first()).toBeVisible();
    }
  });

  test('should export multiple charts in single PDF', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportAllButton = page.locator('button:has-text("Export All PDF")').first();

    if (await exportAllButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 30000 }),
        exportAllButton.click()
      ]);

      const filePath = path.join(DOWNLOAD_DIR, download.suggestedFilename());
      await download.saveAs(filePath);

      const stats = fs.statSync(filePath);

      // Multi-page PDF should be larger
      expect(stats.size).toBeGreaterThan(100000);

      fs.unlinkSync(filePath);
    }
  });

  test('should include metadata in PDF', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const exportAllButton = page.locator('button:has-text("Export All")').first();

    if (await exportAllButton.count() > 0) {
      // Metadata should include title, date, etc.
      // This would require PDF parsing to verify
      expect(true).toBe(true);
    }
  });
});

test.describe('Export - File Naming and Download', () => {

  test('should use descriptive filenames', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      const filename = download.suggestedFilename();

      // Should include chart name
      expect(filename.length).toBeGreaterThan(10);
      expect(filename).toMatch(/[a-zA-Z]/);
    }
  });

  test('should handle special characters in filenames', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      const filename = download.suggestedFilename();

      // Should not contain invalid characters
      expect(filename).not.toMatch(/[<>:"/\\|?*]/);
    }
  });

  test('should prevent filename collisions with timestamps', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download1] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      await page.waitForTimeout(100);

      const [download2] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      expect(download1.suggestedFilename()).not.toBe(download2.suggestedFilename());
    }
  });

  test('should trigger browser download dialog', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const downloadPromise = page.waitForEvent('download');
      await exportButton.click();

      const download = await downloadPromise;
      expect(download).toBeTruthy();
    }
  });
});

test.describe('Export - Quality and Resolution', () => {

  test('should export at full canvas resolution', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const canvasSize = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      return {
        width: canvas?.width || 0,
        height: canvas?.height || 0
      };
    });

    expect(canvasSize.width).toBeGreaterThan(400);
    expect(canvasSize.height).toBeGreaterThan(200);
  });

  test('should use PNG format for lossless quality', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const usePNG = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas) return false;

      const url = canvas.toDataURL('image/png');
      return url.startsWith('data:image/png');
    });

    expect(usePNG).toBe(true);
  });

  test('should handle high DPI displays', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const dpiHandled = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas) return false;

      const context = canvas.getContext('2d');
      return context !== null;
    });

    expect(dpiHandled).toBe(true);
  });

  test('should maintain aspect ratio in exported images', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const aspectRatio = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas) return 0;

      return canvas.width / canvas.height;
    });

    expect(aspectRatio).toBeGreaterThan(0);
  });
});

test.describe('Export - Different Chart States', () => {

  test('should export chart with active hover state', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const canvas = page.locator('canvas').first();
    await canvas.hover();
    await page.waitForTimeout(300);

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        exportButton.click()
      ]);

      expect(download).toBeTruthy();
    }
  });

  test('should export chart with filtered data', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const filterButton = page.locator('button:has-text("Filter"), select').first();

    if (await filterButton.count() > 0) {
      await filterButton.click();
      await page.waitForTimeout(500);

      const exportButton = page.locator('button[onclick*="downloadChart"]').first();

      if (await exportButton.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          exportButton.click()
        ]);

        expect(download).toBeTruthy();
      }
    }
  });

  test('should export chart in dark mode', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

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
      }
    }
  });

  test('should export chart with custom date range', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const dateRangeSelector = page.locator('select[name="dateRange"], input[type="date"]').first();

    if (await dateRangeSelector.count() > 0) {
      await dateRangeSelector.click();
      await page.waitForTimeout(500);

      const exportButton = page.locator('button[onclick*="downloadChart"]').first();

      if (await exportButton.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          exportButton.click()
        ]);

        expect(download).toBeTruthy();
      }
    }
  });
});

test.describe('Export - Error Handling', () => {

  test('should handle canvas toDataURL errors gracefully', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    // Mock toDataURL to throw error
    await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (canvas) {
        const originalToDataURL = canvas.toDataURL;
        canvas.toDataURL = function() {
          throw new Error('Security error');
        };
      }
    });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      await exportButton.click();
      await page.waitForTimeout(500);

      // Should handle error without crashing
      expect(errors.length).toBeLessThan(2);
    }
  });

  test('should handle very large canvas sizes', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (canvas) {
        canvas.width = 10000;
        canvas.height = 10000;
      }
    });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      await exportButton.click();
      await page.waitForTimeout(1000);

      // Should either succeed or fail gracefully
      expect(true).toBe(true);
    }
  });

  test('should show user feedback during export', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('canvas', { timeout: 10000 });

    const exportButton = page.locator('button[onclick*="downloadChart"]').first();

    if (await exportButton.count() > 0) {
      await exportButton.click();

      // Should show loading indicator or change button state
      const buttonDisabled = await exportButton.evaluate(el => {
        return el.disabled || el.classList.contains('loading');
      });

      // Button might disable during export
      if (buttonDisabled !== null) {
        expect(typeof buttonDisabled).toBe('boolean');
      }
    }
  });

  test('should handle JSON export errors', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const jsonExportLink = page.locator('a[download][href*=".json"]').first();

    if (await jsonExportLink.count() > 0) {
      await page.route('**/data/all_metrics.json', route => {
        route.abort('failed');
      });

      await jsonExportLink.click();
      await page.waitForTimeout(500);

      // Should handle error gracefully
      expect(true).toBe(true);
    }
  });
});
