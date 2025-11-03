/**
 * Playwright Configuration for Dashboard Testing
 *
 * Unified configuration for visual regression, accessibility, and integration tests.
 * Supports both local development and CI environments.
 */

module.exports = {
    testDir: './tests',
    timeout: 60000,
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,

    reporter: [
        ['list'],
        ['html', { outputFolder: 'test-results/html-report' }],
        ['json', { outputFile: 'test-results/results.json' }],
        ['junit', { outputFile: 'test-results/junit.xml' }]
    ],

    use: {
        baseURL: process.env.DASHBOARD_URL || 'http://localhost:8000',
        headless: true,
        viewport: { width: 1280, height: 720 },
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
        trace: 'on-first-retry',
        actionTimeout: 10000,
    },

    projects: [
        {
            name: 'chromium',
            use: {
                browserName: 'chromium',
                viewport: { width: 1440, height: 900 },
            },
        },
        {
            name: 'firefox',
            use: {
                browserName: 'firefox',
                viewport: { width: 1440, height: 900 },
            },
        },
        {
            name: 'webkit',
            use: {
                browserName: 'webkit',
                viewport: { width: 1440, height: 900 },
            },
        },
        {
            name: 'mobile-chrome',
            use: {
                browserName: 'chromium',
                viewport: { width: 375, height: 667 },
            },
        },
        {
            name: 'tablet',
            use: {
                browserName: 'chromium',
                viewport: { width: 768, height: 1024 },
            },
        },
    ],

    // Web server configuration for local development
    // In CI, the dashboard is already built and served by the workflow
    webServer: process.env.CI ? {
        command: 'npx http-server _site -p 8000',
        port: 8000,
        timeout: 120000,
        reuseExistingServer: true,
    } : {
        command: 'npx http-server _site -p 8000',
        port: 8000,
        timeout: 120000,
        reuseExistingServer: true,
    },
};
