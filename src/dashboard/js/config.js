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
    METADATA_PATHS: [
        'data/dashboard_metadata.json',
        './data/dashboard_metadata.json',
        '../data/dashboard_metadata.json',
        '/data/dashboard_metadata.json'
    ],
    SANKEY_PATHS: [
        'data/sankey_flow.json',
        './data/sankey_flow.json',
        '../data/sankey_flow.json',
        '/data/sankey_flow.json'
    ],
    TEXT_DISTRIBUTION_PATHS: [
        'data/text_distributions.json',
        './data/text_distributions.json',
        '../data/text_distributions.json',
        '/data/text_distributions.json'
    ],
    SOURCE_CATALOG_PATHS: [
        'data/source_catalog.json',
        './data/source_catalog.json',
        '../data/source_catalog.json',
        '/data/source_catalog.json'
    ],
    PIPELINE_STATUS_PATHS: [
        'data/source_pipeline_status.json',
        './data/source_pipeline_status.json',
        '../data/source_pipeline_status.json',
        '/data/source_pipeline_status.json'
    ],
    QUALITY_ALERTS_PATHS: [
        'data/quality_alerts.json',
        './data/quality_alerts.json',
        '../data/quality_alerts.json',
        '/data/quality_alerts.json'
    ],
    QUALITY_WAIVERS_PATHS: [
        'data/quality_waivers.json',
        './data/quality_waivers.json',
        '../data/quality_waivers.json',
        '/data/quality_waivers.json'
    ],
    PIPELINE_ALERTS_PATHS: [
        'data/pipeline_alerts.json',
        './data/pipeline_alerts.json',
        '../data/pipeline_alerts.json',
        '/data/pipeline_alerts.json'
    ],
    PIPELINE_OBSERVATIONS_PATHS: [
        'data/pipeline_observations.json',
        './data/pipeline_observations.json',
        '../data/pipeline_observations.json',
        '/data/pipeline_observations.json'
    ],
    QUOTA_STATUS_PATHS: [
        'data/quota_status.json',
        './data/quota_status.json',
        '../data/quota_status.json',
        '/data/quota_status.json'
    ],
    MANIFEST_ANALYTICS_PATHS: [
        'data/manifest_analytics.json',
        './data/manifest_analytics.json',
        '../data/manifest_analytics.json',
        '/data/manifest_analytics.json'
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
        wikipedia: '#3B82F6',
        bbc: '#DC2626',
        huggingface: '#059669',
        sprakbanken: '#B45309',
        tiktok: '#BE185D'
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
 * Design System Color Palettes
 * Dual-palette system: Brand colors for UI, Data colors for visualizations
 */
export const BRAND_COLORS = {
    primary: '#1B3A6B',
    accent: '#C2522D',
    success: '#1A7F4E',
    warning: '#92400E',
    danger: '#B91C1C',
    info: '#1D4ED8'
};

export const DATA_COLORS = [
    '#33BBEE',  // Cyan (primary data color)
    '#0077BB',  // Blue
    '#EE7733',  // Orange
    '#009988',  // Teal
    '#CC3311',  // Red
    '#EE3377',  // Magenta
    '#BBBBBB',  // Gray
    '#000000'   // Black
];

/**
 * Override configuration values
 * Useful for testing or environment-specific settings
 * @param {Object} overrides - Object with configuration overrides
 */
export function configureApp(overrides) {
    Object.assign(Config, overrides);
}

/**
 * Get a dashboard data asset path relative to the current deployment base.
 * @param {string} filename - Data asset filename within the dashboard data directory
 * @returns {string} Relative path to the requested asset
 */
export function getDataPath(filename) {
    return `data/${filename}`;
}
