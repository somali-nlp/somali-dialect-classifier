import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Dashboard Visual Regression Testing
 *
 * This configuration extends the root config with visual regression-specific settings.
 * It inherits baseURL and webServer from the root playwright.config.js.
 */
export default defineConfig({
  testDir: './',
  timeout: 30000,

  expect: {
    timeout: 5000,
    toHaveScreenshot: {
      maxDiffPixels: 100,  // Allow minor anti-aliasing differences
      threshold: 0.2,       // 20% threshold for pixel differences
      animations: 'disabled', // Disable animations for consistent screenshots
    },
  },

  reporter: [
    ['html', { outputFolder: 'test-results/visual-regression' }],
    ['json', { outputFile: 'test-results/visual-regression.json' }],
    ['list'],
  ],

  // Visual regression tests use specific device configurations
  projects: [
    {
      name: 'chromium-desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: 'firefox-desktop',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: 'webkit-desktop',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: 'tablet',
      use: {
        ...devices['iPad Pro'],
      },
    },
    {
      name: 'mobile',
      use: {
        ...devices['iPhone 13'],
      },
    },
  ],
});
