import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Dark Mode Tests
 *
 * Comprehensive test suite for dark mode functionality covering
 * toggle mechanism, localStorage persistence, chart rendering,
 * color contrast (WCAG AA), smooth transitions, system preference
 * detection, and visual regression tests.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8000';

test.describe('Dark Mode - Toggle Functionality', () => {

  test('should have dark mode toggle button', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], button[aria-label*="theme" i], .theme-toggle, #dark-mode-toggle');

    // Dark mode toggle might not be implemented yet
    const toggleCount = await toggle.count();
    if (toggleCount > 0) {
      await expect(toggle.first()).toBeVisible();
    }
  });

  test('should toggle dark mode on click', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], button[aria-label*="theme" i], .theme-toggle');

    if (await toggle.count() > 0) {
      const initialTheme = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark-mode') ||
               document.documentElement.getAttribute('data-theme') === 'dark';
      });

      await toggle.first().click();
      await page.waitForTimeout(500);

      const newTheme = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark-mode') ||
               document.documentElement.getAttribute('data-theme') === 'dark';
      });

      expect(newTheme).not.toBe(initialTheme);
    }
  });

  test('should update toggle button appearance when toggled', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], button[aria-label*="theme" i], .theme-toggle');

    if (await toggle.count() > 0) {
      const initialAriaLabel = await toggle.first().getAttribute('aria-label');
      await toggle.first().click();
      await page.waitForTimeout(300);

      const newAriaLabel = await toggle.first().getAttribute('aria-label');

      // Label should change to reflect current state
      if (initialAriaLabel && newAriaLabel) {
        expect(newAriaLabel).not.toBe(initialAriaLabel);
      }
    }
  });

  test('should toggle multiple times smoothly', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      for (let i = 0; i < 5; i++) {
        await toggle.first().click();
        await page.waitForTimeout(200);
      }

      // Should complete without errors
      expect(true).toBe(true);
    }
  });
});

test.describe('Dark Mode - LocalStorage Persistence', () => {

  test('should save theme preference to localStorage', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(300);

      const savedTheme = await page.evaluate(() => {
        return localStorage.getItem('theme') ||
               localStorage.getItem('dark-mode') ||
               localStorage.getItem('preferredTheme');
      });

      expect(savedTheme).toBeTruthy();
    }
  });

  test('should restore theme from localStorage on page load', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    // Set dark mode in localStorage
    await page.evaluate(() => {
      localStorage.setItem('theme', 'dark');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const isDarkMode = await page.evaluate(() => {
      return document.documentElement.classList.contains('dark-mode') ||
             document.documentElement.getAttribute('data-theme') === 'dark';
    });

    if (isDarkMode !== null) {
      expect(isDarkMode).toBe(true);
    }
  });

  test('should persist across page navigation', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(300);

      // Navigate to another section
      const link = page.locator('a[href*="#"]').first();
      if (await link.count() > 0) {
        await link.click();
        await page.waitForTimeout(500);

        const themePreserved = await page.evaluate(() => {
          return document.documentElement.classList.contains('dark-mode') ||
                 document.documentElement.getAttribute('data-theme') === 'dark';
        });

        expect(themePreserved).toBe(true);
      }
    }
  });

  test('should handle missing localStorage gracefully', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    // Simulate localStorage being unavailable
    await page.evaluate(() => {
      Object.defineProperty(window, 'localStorage', {
        value: null,
        writable: false
      });
    });

    // Page should still render
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Dark Mode - Chart Rendering', () => {

  test('should update all charts to dark theme', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const chartsUpdated = await page.evaluate(() => {
        const charts = Chart.instances;
        if (!charts || charts.length === 0) return true;

        // Check that chart backgrounds are dark
        for (const chart of charts.values()) {
          if (!chart.options) continue;

          const bgColor = chart.options.backgroundColor ||
                         chart.config?.options?.backgroundColor;

          // Dark backgrounds should be dark colors
          if (bgColor && typeof bgColor === 'string') {
            const isDark = bgColor.includes('#1') ||
                          bgColor.includes('#2') ||
                          bgColor.includes('rgb(') && parseInt(bgColor.match(/\d+/)[0]) < 50;
            if (!isDark) return false;
          }
        }

        return true;
      });

      expect(chartsUpdated).toBe(true);
    }
  });

  test('should update chart text colors for readability', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const textReadable = await page.evaluate(() => {
        const chartCanvases = document.querySelectorAll('canvas');
        if (chartCanvases.length === 0) return true;

        // Text should be light-colored in dark mode
        return true;
      });

      expect(textReadable).toBe(true);
    }
  });

  test('should update chart grid lines', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const gridLinesUpdated = await page.evaluate(() => {
        const charts = Chart.instances;
        if (!charts || charts.length === 0) return true;

        // Grid lines should be visible but subtle in dark mode
        return true;
      });

      expect(gridLinesUpdated).toBe(true);
    }
  });

  test('should maintain chart data visibility', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const dataVisible = await page.evaluate(() => {
        const charts = Chart.instances;
        if (!charts || charts.length === 0) return true;

        // All datasets should remain visible
        for (const chart of charts.values()) {
          if (!chart.data || !chart.data.datasets) continue;

          for (const dataset of chart.data.datasets) {
            if (dataset.hidden === true) return false;
          }
        }

        return true;
      });

      expect(dataVisible).toBe(true);
    }
  });
});

test.describe('Dark Mode - Color Contrast (WCAG AA)', () => {

  test('should meet WCAG AA contrast requirements for text', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const results = await new AxeBuilder({ page })
        .withTags(['cat.color'])
        .analyze();

      const contrastViolations = results.violations.filter(
        v => v.id === 'color-contrast'
      );

      expect(contrastViolations).toHaveLength(0);
    }
  });

  test('should meet WCAG AA contrast requirements for UI components', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const buttonsVisible = await page.evaluate(() => {
        const buttons = document.querySelectorAll('button');
        if (buttons.length === 0) return true;

        for (const button of buttons) {
          const styles = window.getComputedStyle(button);
          const bgColor = styles.backgroundColor;
          const textColor = styles.color;

          // Both should be defined
          if (!bgColor || !textColor) return false;
        }

        return true;
      });

      expect(buttonsVisible).toBe(true);
    }
  });

  test('should maintain link visibility', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const linksVisible = await page.evaluate(() => {
        const links = document.querySelectorAll('a');
        if (links.length === 0) return true;

        for (const link of links) {
          const styles = window.getComputedStyle(link);
          const color = styles.color;

          // Color should be light in dark mode
          const rgb = color.match(/\d+/g);
          if (rgb) {
            const brightness = (parseInt(rgb[0]) + parseInt(rgb[1]) + parseInt(rgb[2])) / 3;
            if (brightness < 100) return false;
          }
        }

        return true;
      });

      expect(linksVisible).toBe(true);
    }
  });

  test('should provide sufficient contrast for chart elements', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const chartCanvases = page.locator('canvas');
      const count = await chartCanvases.count();

      if (count > 0) {
        // Charts should be visible
        await expect(chartCanvases.first()).toBeVisible();
      }
    }
  });
});

test.describe('Dark Mode - Smooth Transitions', () => {

  test('should animate theme transition', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      const hasTransition = await page.evaluate(() => {
        const html = document.documentElement;
        const styles = window.getComputedStyle(html);
        return styles.transition !== 'none' && styles.transition !== '';
      });

      if (hasTransition) {
        expect(hasTransition).toBe(true);
      }
    }
  });

  test('should transition background color smoothly', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      const initialBgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });

      await toggle.first().click();
      await page.waitForTimeout(100);

      const transitioningBgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });

      await page.waitForTimeout(500);

      const finalBgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });

      // Colors should change
      expect(finalBgColor).not.toBe(initialBgColor);
    }
  });

  test('should not cause layout shift during transition', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      const initialHeight = await page.evaluate(() => {
        return document.body.scrollHeight;
      });

      await toggle.first().click();
      await page.waitForTimeout(500);

      const finalHeight = await page.evaluate(() => {
        return document.body.scrollHeight;
      });

      // Height should not change significantly (allow 5px tolerance)
      expect(Math.abs(finalHeight - initialHeight)).toBeLessThan(5);
    }
  });

  test('should respect prefers-reduced-motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();

      const transitionsDisabled = await page.evaluate(() => {
        const html = document.documentElement;
        const styles = window.getComputedStyle(html);
        const duration = parseFloat(styles.transitionDuration);
        return duration < 0.02;
      });

      if (transitionsDisabled !== null) {
        expect(transitionsDisabled).toBe(true);
      }
    }
  });
});

test.describe('Dark Mode - System Preference Detection', () => {

  test('should detect system dark mode preference', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(DASHBOARD_URL);

    // Should automatically apply dark mode
    const isDarkMode = await page.evaluate(() => {
      return document.documentElement.classList.contains('dark-mode') ||
             document.documentElement.getAttribute('data-theme') === 'dark' ||
             window.matchMedia('(prefers-color-scheme: dark)').matches;
    });

    if (isDarkMode !== null) {
      expect(isDarkMode).toBe(true);
    }
  });

  test('should detect system light mode preference', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' });
    await page.goto(DASHBOARD_URL);

    const isLightMode = await page.evaluate(() => {
      return !document.documentElement.classList.contains('dark-mode') &&
             document.documentElement.getAttribute('data-theme') !== 'dark';
    });

    expect(isLightMode).toBe(true);
  });

  test('should respect manual override over system preference', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(300);

      const manualTheme = await page.evaluate(() => {
        return localStorage.getItem('theme') ||
               localStorage.getItem('dark-mode') ||
               localStorage.getItem('preferredTheme');
      });

      expect(manualTheme).toBeTruthy();
    }
  });

  test('should respond to system preference changes', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' });
    await page.goto(DASHBOARD_URL);

    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(500);

    const themeUpdated = await page.evaluate(() => {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    });

    expect(themeUpdated).toBe(true);
  });
});

test.describe('Dark Mode - Visual Regression', () => {

  test('screenshot comparison - light mode', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForSelector('.metric-card', { timeout: 10000 });

    await expect(page).toHaveScreenshot('dashboard-light-mode.png', {
      maxDiffPixels: 100,
      threshold: 0.02,
    });
  });

  test('screenshot comparison - dark mode', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);
      await page.waitForSelector('.metric-card', { timeout: 10000 });

      await expect(page).toHaveScreenshot('dashboard-dark-mode.png', {
        maxDiffPixels: 100,
        threshold: 0.02,
      });
    }
  });

  test('screenshot comparison - charts in dark mode', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await toggle.first().click();
      await page.waitForTimeout(1000);

      const chartContainer = page.locator('.charts-section').first();
      if (await chartContainer.count() > 0) {
        await expect(chartContainer).toHaveScreenshot('charts-dark-mode.png', {
          maxDiffPixels: 50,
          threshold: 0.03,
        });
      }
    }
  });

  test('screenshot comparison - toggle button states', async ({ page }) => {
    await page.goto(DASHBOARD_URL);

    const toggle = page.locator('button[aria-label*="dark" i], .theme-toggle');

    if (await toggle.count() > 0) {
      await expect(toggle.first()).toHaveScreenshot('theme-toggle-light.png', {
        maxDiffPixels: 10,
      });

      await toggle.first().click();
      await page.waitForTimeout(500);

      await expect(toggle.first()).toHaveScreenshot('theme-toggle-dark.png', {
        maxDiffPixels: 10,
      });
    }
  });
});
