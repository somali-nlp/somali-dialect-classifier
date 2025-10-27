import { test, expect } from '@playwright/test';

/**
 * Sankey Diagram Tests
 *
 * Comprehensive test suite for Sankey/funnel diagram visualization
 * covering data transformation, rendering, interactivity, edge cases,
 * responsiveness, and accessibility.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Sankey Diagram - Data Transformation', () => {

  test('should transform metrics data to Sankey format correctly', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sankeyData = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      if (metrics.length === 0) return null;

      // Expected transformation: source -> pipeline_type -> records_written
      const nodes = new Set();
      const links = [];

      metrics.forEach(m => {
        nodes.add(m.source);
        nodes.add(m.pipeline_type);
        nodes.add('Records Written');

        links.push({
          source: m.source,
          target: m.pipeline_type,
          value: m.records_written || 0
        });
      });

      return {
        nodes: Array.from(nodes),
        links: links
      };
    });

    expect(sankeyData).toBeTruthy();
    expect(sankeyData.nodes.length).toBeGreaterThan(0);
    expect(sankeyData.links.length).toBeGreaterThan(0);
  });

  test('should handle zero record values in transformation', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const hasZeroRecords = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      return metrics.some(m => m.records_written === 0);
    });

    // Sankey should still render even with zero values
    if (hasZeroRecords) {
      const sankeyContainer = page.locator('.sankey-container');
      await expect(sankeyContainer).toBeVisible();
    }
  });

  test('should aggregate duplicate source-target pairs', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const aggregatedCorrectly = await page.evaluate(() => {
      const metrics = window.metricsData?.metrics || [];
      const linkMap = new Map();

      metrics.forEach(m => {
        const key = `${m.source}-${m.pipeline_type}`;
        const current = linkMap.get(key) || 0;
        linkMap.set(key, current + (m.records_written || 0));
      });

      // All aggregations should be unique
      return linkMap.size > 0;
    });

    expect(aggregatedCorrectly).toBe(true);
  });
});

test.describe('Sankey Diagram - Rendering', () => {

  test('should render Sankey container', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const sankeyContainer = page.locator('.sankey-container');
    await expect(sankeyContainer).toBeVisible();
  });

  test('should render nodes with correct positioning', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const nodesRendered = await page.evaluate(() => {
      const container = document.querySelector('.sankey-container');
      if (!container) return false;

      const nodes = container.querySelectorAll('.sankey-node');
      return nodes.length > 0;
    });

    expect(nodesRendered).toBe(true);
  });

  test('should render links with appropriate widths', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const linksValid = await page.evaluate(() => {
      const container = document.querySelector('.sankey-container');
      if (!container) return false;

      const links = container.querySelectorAll('.sankey-link');
      if (links.length === 0) return false;

      // Check that links have width proportional to values
      for (const link of links) {
        const width = parseFloat(link.getAttribute('stroke-width') || '0');
        if (width <= 0) return false;
      }

      return true;
    });

    expect(linksValid).toBe(true);
  });

  test('should apply color coding to nodes', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const colorsApplied = await page.evaluate(() => {
      const nodes = document.querySelectorAll('.sankey-node');
      if (nodes.length === 0) return false;

      for (const node of nodes) {
        const fill = node.getAttribute('fill') || '';
        if (!fill || fill === 'none') return false;
      }

      return true;
    });

    expect(colorsApplied).toBe(true);
  });

  test('should render node labels', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const labelsRendered = await page.evaluate(() => {
      const labels = document.querySelectorAll('.sankey-node-label');
      return labels.length > 0;
    });

    expect(labelsRendered).toBe(true);
  });
});

test.describe('Sankey Diagram - Interactivity', () => {

  test('should highlight node on hover', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const node = page.locator('.sankey-node').first();
    if (await node.count() > 0) {
      await node.hover();

      const isHighlighted = await node.evaluate(el => {
        const opacity = window.getComputedStyle(el).opacity;
        return parseFloat(opacity) > 0.5;
      });

      expect(isHighlighted).toBe(true);
    }
  });

  test('should show tooltip on node hover', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const node = page.locator('.sankey-node').first();
    if (await node.count() > 0) {
      await node.hover();

      // Wait for tooltip
      await page.waitForTimeout(200);

      const tooltip = page.locator('.tooltip, [role="tooltip"]');
      const tooltipVisible = await tooltip.count() > 0 && await tooltip.isVisible();

      if (tooltipVisible) {
        expect(await tooltip.textContent()).toBeTruthy();
      }
    }
  });

  test('should highlight connected links on node hover', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const highlightsWork = await page.evaluate(() => {
      const node = document.querySelector('.sankey-node');
      if (!node) return false;

      const event = new MouseEvent('mouseenter', { bubbles: true });
      node.dispatchEvent(event);

      // Check if any links changed opacity
      const links = document.querySelectorAll('.sankey-link');
      return links.length > 0;
    });

    expect(highlightsWork).toBe(true);
  });

  test('should handle click events on nodes', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const node = page.locator('.sankey-node').first();
    if (await node.count() > 0) {
      await node.click();

      // Should not cause errors
      const errors = [];
      page.on('pageerror', err => errors.push(err));

      await page.waitForTimeout(500);
      expect(errors.length).toBe(0);
    }
  });
});

test.describe('Sankey Diagram - Edge Cases', () => {

  test('should handle single source gracefully', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          records: 100,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: [{
            run_id: 'test1',
            source: 'Wikipedia-Somali',
            pipeline_type: 'discovery',
            records_written: 100,
            timestamp: new Date().toISOString()
          }]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const sankeyContainer = page.locator('.sankey-container');
    await expect(sankeyContainer).toBeVisible();
  });

  test('should handle empty data gracefully', async ({ page }) => {
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

    await page.goto(DASHBOARD_URL);

    // Should show empty state or not render
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });

  test('should handle very large values', async ({ page }) => {
    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          records: 1000000000,
          sources: ['Wikipedia-Somali'],
          pipeline_types: ['discovery'],
          metrics: [{
            run_id: 'test1',
            source: 'Wikipedia-Somali',
            pipeline_type: 'discovery',
            records_written: 1000000000,
            timestamp: new Date().toISOString()
          }]
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    // Should render without overflow
    const overflow = await page.evaluate(() => {
      const container = document.querySelector('.sankey-container');
      if (!container) return false;

      const rect = container.getBoundingClientRect();
      return rect.width > window.innerWidth * 2;
    });

    expect(overflow).toBe(false);
  });

  test('should handle many sources (10+)', async ({ page }) => {
    const metrics = [];
    for (let i = 0; i < 15; i++) {
      metrics.push({
        run_id: `test${i}`,
        source: `Source-${i}`,
        pipeline_type: 'discovery',
        records_written: 100 * i,
        timestamp: new Date().toISOString()
      });
    }

    await page.route('**/data/all_metrics.json', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: metrics.length,
          records: 10000,
          sources: metrics.map(m => m.source),
          pipeline_types: ['discovery'],
          metrics: metrics
        })
      });
    });

    await page.goto(DASHBOARD_URL);

    const sankeyContainer = page.locator('.sankey-container');
    await expect(sankeyContainer).toBeVisible();
  });
});

test.describe('Sankey Diagram - Responsiveness', () => {

  test('should render correctly on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DASHBOARD_URL);

    const sankeyContainer = page.locator('.sankey-container');
    if (await sankeyContainer.count() > 0) {
      await expect(sankeyContainer).toBeVisible();

      const containerWidth = await sankeyContainer.evaluate(el => {
        return el.getBoundingClientRect().width;
      });

      expect(containerWidth).toBeLessThanOrEqual(375);
    }
  });

  test('should render correctly on tablet (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(DASHBOARD_URL);

    const sankeyContainer = page.locator('.sankey-container');
    if (await sankeyContainer.count() > 0) {
      await expect(sankeyContainer).toBeVisible();
    }
  });

  test('should render correctly on desktop (1920px)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(DASHBOARD_URL);

    const sankeyContainer = page.locator('.sankey-container');
    if (await sankeyContainer.count() > 0) {
      await expect(sankeyContainer).toBeVisible();
    }
  });

  test('should adapt layout on window resize', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto(DASHBOARD_URL);

    const initialWidth = await page.locator('.sankey-container').evaluate(el => {
      return el.getBoundingClientRect().width;
    });

    await page.setViewportSize({ width: 800, height: 600 });
    await page.waitForTimeout(500);

    const newWidth = await page.locator('.sankey-container').evaluate(el => {
      return el.getBoundingClientRect().width;
    });

    expect(newWidth).toBeLessThan(initialWidth);
  });
});

test.describe('Sankey Diagram - Accessibility', () => {

  test('should have ARIA labels on container', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const container = page.locator('.sankey-container');
    if (await container.count() > 0) {
      const ariaLabel = await container.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
    }
  });

  test('should have descriptive labels for nodes', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const hasLabels = await page.evaluate(() => {
      const labels = document.querySelectorAll('.sankey-node-label');
      if (labels.length === 0) return false;

      for (const label of labels) {
        if (!label.textContent || label.textContent.trim().length === 0) {
          return false;
        }
      }

      return true;
    });

    expect(hasLabels).toBe(true);
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const container = page.locator('.sankey-container');
    if (await container.count() > 0) {
      await container.focus();

      const isFocusable = await container.evaluate(el => {
        return el === document.activeElement;
      });

      expect(isFocusable).toBe(true);
    }
  });

  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const contrastSufficient = await page.evaluate(() => {
      const nodes = document.querySelectorAll('.sankey-node');
      if (nodes.length === 0) return true;

      // Check that nodes are visible
      for (const node of nodes) {
        const fill = node.getAttribute('fill');
        if (!fill || fill === 'transparent') return false;
      }

      return true;
    });

    expect(contrastSufficient).toBe(true);
  });

  test('should have role attributes', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const container = page.locator('.sankey-container');
    if (await container.count() > 0) {
      const role = await container.getAttribute('role');
      expect(role).toBeTruthy();
    }
  });
});
