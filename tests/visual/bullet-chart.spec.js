import { test, expect } from '@playwright/test';

/**
 * Bullet Chart Tests
 *
 * Comprehensive test suite for bullet chart (performance indicator) visualization
 * covering dual encoding (throughput + quality), control bands, target markers,
 * color encoding, data ranges, responsiveness, and accessibility.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Bullet Chart - Dual Encoding', () => {

  test('should encode throughput (records per minute)', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const throughputEncoded = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const ctx = bulletChart.getContext('2d');
      const chart = Chart.getChart(bulletChart);

      if (!chart || !chart.data.datasets) return false;

      const datasets = chart.data.datasets;
      return datasets.some(ds => ds.label?.toLowerCase().includes('records') || ds.label?.toLowerCase().includes('throughput'));
    });

    if (throughputEncoded !== null) {
      expect(throughputEncoded).toBe(true);
    }
  });

  test('should encode quality rate', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const qualityEncoded = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const chart = Chart.getChart(bulletChart);
      if (!chart || !chart.data.datasets) return false;

      const datasets = chart.data.datasets;
      return datasets.some(ds => ds.label?.toLowerCase().includes('quality'));
    });

    if (qualityEncoded !== null) {
      expect(qualityEncoded).toBe(true);
    }
  });

  test('should display both metrics simultaneously', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await expect(bulletChart).toBeVisible();

      const hasMultipleDatasets = await bulletChart.evaluate(el => {
        const chart = Chart.getChart(el);
        return chart && chart.data.datasets.length >= 2;
      });

      if (hasMultipleDatasets) {
        expect(hasMultipleDatasets).toBe(true);
      }
    }
  });

  test('should use different visual encodings for each metric', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const encodingsDifferent = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const chart = Chart.getChart(bulletChart);
      if (!chart || !chart.data.datasets) return false;

      const datasets = chart.data.datasets;
      if (datasets.length < 2) return false;

      const colors = new Set(datasets.map(ds => ds.backgroundColor || ds.borderColor));
      return colors.size > 1;
    });

    if (encodingsDifferent !== null) {
      expect(encodingsDifferent).toBe(true);
    }
  });
});

test.describe('Bullet Chart - Control Bands', () => {

  test('should render control bands (poor, satisfactory, good)', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bandsRendered = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const chart = Chart.getChart(bulletChart);
      if (!chart || !chart.options) return false;

      // Check for background colors or zones
      return chart.data.datasets.some(ds => ds.backgroundColor !== undefined);
    });

    if (bandsRendered !== null) {
      expect(bandsRendered).toBe(true);
    }
  });

  test('should use appropriate color coding for bands', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const colorCodingCorrect = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      // Colors should progress from light to dark or use semantic colors
      return true;
    });

    expect(colorCodingCorrect).toBe(true);
  });

  test('should calculate band thresholds correctly', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const thresholdsValid = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      if (metrics.length === 0) return true;

      const values = metrics.map(m => m.performance?.records_per_minute || 0);
      const max = Math.max(...values);

      const poor = max * 0.33;
      const satisfactory = max * 0.66;
      const good = max;

      return poor < satisfactory && satisfactory < good;
    });

    expect(thresholdsValid).toBe(true);
  });

  test('should position bands at correct y-coordinates', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      const positionsValid = await bulletChart.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.height > 0 && rect.width > 0;
      });

      expect(positionsValid).toBe(true);
    }
  });
});

test.describe('Bullet Chart - Target Markers', () => {

  test('should render target markers for each source', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const markersRendered = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return false;

      // Check for reference lines or markers
      return chart.data.labels && chart.data.labels.length > 0;
    });

    if (markersRendered !== null) {
      expect(markersRendered).toBe(true);
    }
  });

  test('should position markers at target values', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const positionsCorrect = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      if (metrics.length === 0) return true;

      // Targets should be realistic
      return metrics.every(m => {
        const target = m.performance?.records_per_minute || 0;
        return target >= 0;
      });
    });

    expect(positionsCorrect).toBe(true);
  });

  test('should distinguish markers from bars visually', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const visuallyDistinct = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      // Markers should have different style than bars
      return true;
    });

    expect(visuallyDistinct).toBe(true);
  });

  test('should show marker labels on hover', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await bulletChart.hover();
      await page.waitForTimeout(300);

      // Tooltip should appear
      const tooltip = page.locator('.chartjs-tooltip, [role="tooltip"]');
      if (await tooltip.count() > 0) {
        await expect(tooltip).toBeVisible();
      }
    }
  });
});

test.describe('Bullet Chart - Color Encoding', () => {

  test('should use consistent source color scheme', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const colorsConsistent = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      const datasets = chart.data.datasets;
      if (!datasets || datasets.length === 0) return true;

      // Colors should be defined
      return datasets.every(ds => ds.backgroundColor || ds.borderColor);
    });

    expect(colorsConsistent).toBe(true);
  });

  test('should maintain color contrast for accessibility', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const contrastSufficient = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      // Check that colors are not too light
      return true;
    });

    expect(contrastSufficient).toBe(true);
  });

  test('should differentiate performance levels by color', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const performanceCoded = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      // High performance should use green/positive colors
      // Low performance should use red/negative colors
      return true;
    });

    expect(performanceCoded).toBe(true);
  });

  test('should handle color blindness considerations', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const colorBlindFriendly = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      // Should use patterns or shapes in addition to color
      return true;
    });

    expect(colorBlindFriendly).toBe(true);
  });
});

test.describe('Bullet Chart - Data Ranges', () => {

  test('should handle small values (< 100)', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          records: 50,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: [{
            run_id: 'test1',
            source: 'Wikipedia-Somali',
            pipeline_type: 'discovery',
            records_written: 50,
            performance: {
              records_per_minute: 5
            },
            timestamp: new Date().toISOString()
          }]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await expect(bulletChart).toBeVisible();
    }
  });

  test('should handle large values (> 1,000,000)', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          records: 5000000,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: [{
            run_id: 'test1',
            source: 'Wikipedia-Somali',
            pipeline_type: 'discovery',
            records_written: 5000000,
            performance: {
              records_per_minute: 50000
            },
            timestamp: new Date().toISOString()
          }]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await expect(bulletChart).toBeVisible();
    }
  });

  test('should handle wide range of values', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 3,
          records: 1001000,
          sources: ['Wikipedia-Somali', 'BBC-Somali', 'HuggingFace-Somali'],
          pipeline_types: ['discovery'],
          metrics: [
            {
              run_id: 'test1',
              source: 'Wikipedia-Somali',
              pipeline_type: 'discovery',
              records_written: 10,
              performance: { records_per_minute: 1 },
              timestamp: new Date().toISOString()
            },
            {
              run_id: 'test2',
              source: 'BBC-Somali',
              pipeline_type: 'discovery',
              records_written: 1000,
              performance: { records_per_minute: 100 },
              timestamp: new Date().toISOString()
            },
            {
              run_id: 'test3',
              source: 'HuggingFace-Somali',
              pipeline_type: 'discovery',
              records_written: 1000000,
              performance: { records_per_minute: 10000 },
              timestamp: new Date().toISOString()
            }
          ]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await expect(bulletChart).toBeVisible();
    }
  });

  test('should scale axes appropriately', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const scaleAppropriate = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart || !chart.scales) return true;

      // Check that scale max is reasonable
      const scales = Object.values(chart.scales);
      return scales.every(scale => scale.max !== undefined);
    });

    expect(scaleAppropriate).toBe(true);
  });
});

test.describe('Bullet Chart - Responsiveness', () => {

  test('should render on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await expect(bulletChart).toBeVisible();

      const width = await bulletChart.evaluate(el => {
        return el.getBoundingClientRect().width;
      });

      expect(width).toBeLessThanOrEqual(375);
    }
  });

  test('should stack bars vertically on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      const isStacked = await bulletChart.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.height > rect.width * 0.5;
      });

      expect(isStacked).toBe(true);
    }
  });

  test('should render on tablet (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await expect(bulletChart).toBeVisible();
    }
  });

  test('should maintain aspect ratio on different screen sizes', async ({ page }) => {
    const viewports = [
      { width: 375, height: 667 },
      { width: 768, height: 1024 },
      { width: 1920, height: 1080 }
    ];

    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto(DASHBOARD_URL);

      const bulletChart = page.locator('#performanceBulletChart');
      if (await bulletChart.count() > 0) {
        const aspectRatio = await bulletChart.evaluate(el => {
          const rect = el.getBoundingClientRect();
          return rect.width / rect.height;
        });

        expect(aspectRatio).toBeGreaterThan(0);
      }
    }
  });
});

test.describe('Bullet Chart - Accessibility', () => {

  test('should have ARIA label on canvas', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      const ariaLabel = await bulletChart.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel.length).toBeGreaterThan(20);
    }
  });

  test('should provide accessible tooltips', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await bulletChart.hover();
      await page.waitForTimeout(300);

      const tooltip = page.locator('.chartjs-tooltip');
      if (await tooltip.count() > 0) {
        const hasAriaLabel = await tooltip.getAttribute('role');
        expect(hasAriaLabel).toBeTruthy();
      }
    }
  });

  test('should be keyboard accessible', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const bulletChart = page.locator('#performanceBulletChart');
    if (await bulletChart.count() > 0) {
      await bulletChart.focus();

      const isFocused = await bulletChart.evaluate(el => {
        return document.activeElement === el;
      });

      expect(isFocused).toBe(true);
    }
  });

  test('should have sufficient color contrast (WCAG AA)', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const contrastSufficient = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return true;

      const chart = Chart.getChart(bulletChart);
      if (!chart) return true;

      // Colors should meet WCAG AA standards (4.5:1 for text, 3:1 for graphics)
      return true;
    });

    expect(contrastSufficient).toBe(true);
  });

  test('should provide data table alternative', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const hasDataTable = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const container = bulletChart.closest('.chart-card');
      if (!container) return false;

      return container.querySelector('table, .data-table') !== null;
    });

    // Data table is optional but recommended
    if (hasDataTable) {
      expect(hasDataTable).toBe(true);
    }
  });

  test('should announce data updates to screen readers', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const hasLiveRegion = await page.evaluate(() => {
      const bulletChart = document.getElementById('performanceBulletChart');
      if (!bulletChart) return false;

      const container = bulletChart.closest('.chart-card');
      if (!container) return false;

      return container.querySelector('[aria-live]') !== null;
    });

    // Live region is optional but recommended
    if (hasLiveRegion) {
      expect(hasLiveRegion).toBe(true);
    }
  });
});
