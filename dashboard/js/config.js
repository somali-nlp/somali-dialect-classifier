/**
 * Configuration Module
 * Centralized configuration for dashboard paths and settings
 * Enables environment-specific overrides and eliminates hardcoded values
 */

/**
 * Dashboard configuration object
 * Contains all configurable paths, timeouts, and feature flags
 */
export const Config = {
    /**
     * Data file paths
     * Ordered by priority - first successful fetch wins
     */
    DATA_PATHS: [
        'data/all_metrics.json',
        './data/all_metrics.json',
        '../data/all_metrics.json',
        '/data/all_metrics.json'
    ],

    /**
     * Network settings
     */
    FETCH_TIMEOUT: 10000, // 10 seconds
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000, // 1 second

    /**
     * UI settings
     */
    ANIMATION_DURATION: 2000,
    CHART_COLORS: {
        wikipedia: '#3b82f6',
        bbc: '#ef4444',
        huggingface: '#10b981',
        sprakbanken: '#f59e0b'
    },

    /**
     * Feature flags
     */
    FEATURES: {
        enableAdvancedCharts: true,
        enableExport: true,
        enableComparison: true,
        enableLogger: true
    },

    /**
     * Environment detection
     */
    isDevelopment: () => {
        return window.location.hostname === 'localhost' ||
               window.location.hostname === '127.0.0.1' ||
               window.location.protocol === 'file:';
    }
};

/**
 * Override configuration values
 * Useful for testing or environment-specific settings
 * @param {Object} overrides - Object with configuration overrides
 */
export function configureApp(overrides) {
    Object.assign(Config, overrides);
}
