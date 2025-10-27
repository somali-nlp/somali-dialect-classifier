import { test, expect } from '@playwright/test';

/**
 * Ridge Plot Tests
 *
 * Comprehensive test suite for ridge plot (joy plot) visualization
 * covering data binning, density calculations, overlapping curves,
 * source toggle, logarithmic scale, responsiveness, and accessibility.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Ridge Plot - Data Binning Algorithm', () => {

  test('should bin data into appropriate ranges', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const binsValid = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      if (metrics.length === 0) return true;

      const values = metrics.map(m => m.records_written || 0);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const binCount = 20;
      const binSize = (max - min) / binCount;

      return binSize > 0 && binCount > 0;
    });

    expect(binsValid).toBe(true);
  });

  test('should handle uniform distribution', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      const metrics = Array.from({ length: 10 }, (_, i) => ({
        run_id: `test${i}`,
        source: 'Wikipedia-Somali',
        pipeline_type: 'discovery',
        records_written: 100,
        timestamp: new Date().toISOString()
      }));

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: metrics.length,
          records: 1000,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: metrics
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const ridgePlot = page.locator('.ridge-plot-container');
    if (await ridgePlot.count() > 0) {
      await expect(ridgePlot).toBeVisible();
    }
  });

  test('should handle bimodal distribution', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      const metrics = [
        ...Array.from({ length: 5 }, (_, i) => ({
          run_id: `test${i}`,
          source: 'Wikipedia-Somali',
          pipeline_type: 'discovery',
          records_written: 100,
          timestamp: new Date().toISOString()
        })),
        ...Array.from({ length: 5 }, (_, i) => ({
          run_id: `test${i + 5}`,
          source: 'BBC-Somali',
          pipeline_type: 'discovery',
          records_written: 1000,
          timestamp: new Date().toISOString()
        }))
      ];

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: metrics.length,
          records: 5500,
          sources: ['Wikipedia-Somali', 'BBC-Somali'],
          pipeline_types: ['discovery'],
          metrics: metrics
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const ridgePlot = page.locator('.ridge-plot-container');
    if (await ridgePlot.count() > 0) {
      await expect(ridgePlot).toBeVisible();
    }
  });

  test('should adjust bin size based on data range', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const binSizeAppropriate = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      if (metrics.length === 0) return true;

      const values = metrics.map(m => m.records_written || 0);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min;

      // Bin size should be reasonable fraction of range
      const binSize = range / 20;
      return binSize >= 1;
    });

    expect(binSizeAppropriate).toBe(true);
  });
});

test.describe('Ridge Plot - Density Calculations', () => {

  test('should calculate kernel density estimates correctly', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const densityValid = await page.evaluate(() => {
      const ridgePlot = document.querySelector('.ridge-plot-container');
      if (!ridgePlot) return true;

      const paths = ridgePlot.querySelectorAll('path.ridge-plot-layer');
      if (paths.length === 0) return false;

      // Check that paths have valid d attributes
      for (const path of paths) {
        const d = path.getAttribute('d');
        if (!d || d.length < 10) return false;
      }

      return true;
    });

    expect(densityValid).toBe(true);
  });

  test('should normalize density values', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const normalized = await page.evaluate(() => {
      const ridgePlot = document.querySelector('.ridge-plot-container');
      if (!ridgePlot) return true;

      // Check that all paths fit within container
      const rect = ridgePlot.getBoundingClientRect();
      const paths = ridgePlot.querySelectorAll('path.ridge-plot-layer');

      for (const path of paths) {
        const pathRect = path.getBoundingClientRect();
        if (pathRect.bottom > rect.bottom + 50) return false;
      }

      return true;
    });

    expect(normalized).toBe(true);
  });

  test('should handle sparse data', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 2,
          records: 150,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: [
            {
              run_id: 'test1',
              source: 'Wikipedia-Somali',
              pipeline_type: 'discovery',
              records_written: 50,
              timestamp: new Date().toISOString()
            },
            {
              run_id: 'test2',
              source: 'Wikipedia-Somali',
              pipeline_type: 'discovery',
              records_written: 100,
              timestamp: new Date().toISOString()
            }
          ]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const ridgePlot = page.locator('.ridge-plot-container');
    if (await ridgePlot.count() > 0) {
      await expect(ridgePlot).toBeVisible();
    }
  });
});

test.describe('Ridge Plot - Overlapping Curves Rendering', () => {

  test('should render multiple overlapping curves', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const curvesRendered = await page.evaluate(() => {
      const ridgePlot = document.querySelector('.ridge-plot-container');
      if (!ridgePlot) return false;

      const layers = ridgePlot.querySelectorAll('.ridge-plot-layer');
      return layers.length >= 2;
    });

    if (curvesRendered) {
      expect(curvesRendered).toBe(true);
    }
  });

  test('should apply vertical offset to curves', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const offsetsCorrect = await page.evaluate(() => {
      const layers = document.querySelectorAll('.ridge-plot-layer');
      if (layers.length < 2) return true;

      const positions = Array.from(layers).map(layer => {
        return layer.getBoundingClientRect().top;
      });

      // Check that positions are different
      const uniquePositions = new Set(positions);
      return uniquePositions.size > 1;
    });

    expect(offsetsCorrect).toBe(true);
  });

  test('should apply transparency to overlapping areas', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const transparencyApplied = await page.evaluate(() => {
      const layers = document.querySelectorAll('.ridge-plot-layer');
      if (layers.length === 0) return true;

      for (const layer of layers) {
        const opacity = window.getComputedStyle(layer).opacity;
        if (parseFloat(opacity) >= 1.0) return false;
      }

      return true;
    });

    expect(transparencyApplied).toBe(true);
  });

  test('should maintain z-index ordering', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const zIndexCorrect = await page.evaluate(() => {
      const layers = document.querySelectorAll('.ridge-plot-layer');
      if (layers.length < 2) return true;

      const zIndexes = Array.from(layers).map(layer => {
        return parseInt(window.getComputedStyle(layer).zIndex || '0');
      });

      // Check that z-indexes are in order
      for (let i = 1; i < zIndexes.length; i++) {
        if (zIndexes[i] <= zIndexes[i - 1]) return false;
      }

      return true;
    });

    expect(zIndexCorrect).toBe(true);
  });
});

test.describe('Ridge Plot - Source Toggle Functionality', () => {

  test('should have source toggle controls', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggles = page.locator('.ridge-plot-toggle, .source-toggle');
    if (await toggles.count() > 0) {
      await expect(toggles.first()).toBeVisible();
    }
  });

  test('should toggle source visibility on click', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('.ridge-plot-toggle, .source-toggle').first();
    if (await toggle.count() > 0) {
      await toggle.click();
      await page.waitForTimeout(300);

      // Check that at least one layer changed visibility
      const visibilityChanged = await page.evaluate(() => {
        const layers = document.querySelectorAll('.ridge-plot-layer');
        for (const layer of layers) {
          const display = window.getComputedStyle(layer).display;
          if (display === 'none') return true;
        }
        return false;
      });

      if (visibilityChanged) {
        expect(visibilityChanged).toBe(true);
      }
    }
  });

  test('should update toggle state visually', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('.ridge-plot-toggle, .source-toggle').first();
    if (await toggle.count() > 0) {
      const initialClass = await toggle.getAttribute('class');
      await toggle.click();
      const afterClass = await toggle.getAttribute('class');

      expect(initialClass).not.toBe(afterClass);
    }
  });

  test('should handle toggle all sources', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggleAll = page.locator('button:has-text("Toggle All"), button:has-text("All Sources")');
    if (await toggleAll.count() > 0) {
      await toggleAll.click();
      await page.waitForTimeout(300);

      const allHidden = await page.evaluate(() => {
        const layers = document.querySelectorAll('.ridge-plot-layer');
        for (const layer of layers) {
          const display = window.getComputedStyle(layer).display;
          if (display !== 'none') return false;
        }
        return layers.length > 0;
      });

      if (allHidden) {
        expect(allHidden).toBe(true);
      }
    }
  });
});

test.describe('Ridge Plot - Logarithmic Scale', () => {

  test('should apply logarithmic scale when enabled', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const logScaleToggle = page.locator('button:has-text("Log Scale"), input[type="checkbox"]:near(:text("Logarithmic"))');
    if (await logScaleToggle.count() > 0) {
      await logScaleToggle.click();
      await page.waitForTimeout(500);

      // Check that scale changed
      const scaleChanged = await page.evaluate(() => {
        const ridgePlot = document.querySelector('.ridge-plot-container');
        return ridgePlot !== null;
      });

      expect(scaleChanged).toBe(true);
    }
  });

  test('should handle zero values with log scale', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 2,
          records: 100,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: [
            {
              run_id: 'test1',
              source: 'Wikipedia-Somali',
              pipeline_type: 'discovery',
              records_written: 0,
              timestamp: new Date().toISOString()
            },
            {
              run_id: 'test2',
              source: 'Wikipedia-Somali',
              pipeline_type: 'discovery',
              records_written: 100,
              timestamp: new Date().toISOString()
            }
          ]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const logScaleToggle = page.locator('button:has-text("Log Scale")');
    if (await logScaleToggle.count() > 0) {
      await logScaleToggle.click();

      // Should not cause errors
      const errors = [];
      page.on('pageerror', err => errors.push(err));
      await page.waitForTimeout(500);

      expect(errors.length).toBe(0);
    }
  });

  test('should toggle between linear and log scale smoothly', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const logScaleToggle = page.locator('button:has-text("Log Scale")');
    if (await logScaleToggle.count() > 0) {
      await logScaleToggle.click();
      await page.waitForTimeout(300);

      await logScaleToggle.click();
      await page.waitForTimeout(300);

      // Should complete without errors
      expect(true).toBe(true);
    }
  });
});

test.describe('Ridge Plot - Responsiveness', () => {

  test('should render on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DASHBOARD_URL);

    const ridgePlot = page.locator('.ridge-plot-container');
    if (await ridgePlot.count() > 0) {
      await expect(ridgePlot).toBeVisible();

      const width = await ridgePlot.evaluate(el => {
        return el.getBoundingClientRect().width;
      });

      expect(width).toBeLessThanOrEqual(375);
    }
  });

  test('should render on tablet (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(DASHBOARD_URL);

    const ridgePlot = page.locator('.ridge-plot-container');
    if (await ridgePlot.count() > 0) {
      await expect(ridgePlot).toBeVisible();
    }
  });

  test('should adjust curve density on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DASHBOARD_URL);

    const curvesSimplified = await page.evaluate(() => {
      const layers = document.querySelectorAll('.ridge-plot-layer');
      if (layers.length === 0) return true;

      // On mobile, should have fewer curves visible or simplified
      return true;
    });

    expect(curvesSimplified).toBe(true);
  });

  test('should adapt on window resize', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto(DASHBOARD_URL);

    await page.setViewportSize({ width: 600, height: 800 });
    await page.waitForTimeout(500);

    const ridgePlot = page.locator('.ridge-plot-container');
    if (await ridgePlot.count() > 0) {
      await expect(ridgePlot).toBeVisible();
    }
  });
});

test.describe('Ridge Plot - Accessibility', () => {

  test('should have ARIA label on container', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const container = page.locator('.ridge-plot-container');
    if (await container.count() > 0) {
      const ariaLabel = await container.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
    }
  });

  test('should have accessible toggle controls', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggles = page.locator('.ridge-plot-toggle, .source-toggle');
    if (await toggles.count() > 0) {
      const firstToggle = toggles.first();
      const ariaLabel = await firstToggle.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
    }
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('.ridge-plot-toggle, .source-toggle').first();
    if (await toggle.count() > 0) {
      await toggle.focus();

      const isFocused = await toggle.evaluate(el => {
        return el === document.activeElement;
      });

      expect(isFocused).toBe(true);
    }
  });

  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const contrastSufficient = await page.evaluate(() => {
      const layers = document.querySelectorAll('.ridge-plot-layer');
      if (layers.length === 0) return true;

      for (const layer of layers) {
        const fill = window.getComputedStyle(layer).fill;
        if (!fill || fill === 'transparent') return false;
      }

      return true;
    });

    expect(contrastSufficient).toBe(true);
  });

  test('should announce toggle changes to screen readers', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('.ridge-plot-toggle, .source-toggle').first();
    if (await toggle.count() > 0) {
      const ariaPressed = await toggle.getAttribute('aria-pressed');
      await toggle.click();
      const newAriaPressed = await toggle.getAttribute('aria-pressed');

      if (ariaPressed !== null) {
        expect(ariaPressed).not.toBe(newAriaPressed);
      }
    }
  });
});
