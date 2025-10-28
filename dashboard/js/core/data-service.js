/**
 * Data Service Module
 * Handles loading, normalizing, and managing metrics data from JSON files
 * Implements error handling, data validation, and schema normalization
 */

import { Config } from '../config.js';
import { Logger, DataLoadError, DataValidationError } from '../utils/logger.js';

// Store metrics data globally for the module
let metricsData = null;

/**
 * Load metrics from JSON file with fallback paths and retry logic
 * Implements Bug Fix #1: Correct file path to data/all_metrics.json
 * @returns {Promise<Object>} The loaded and normalized metrics data
 */
export async function loadMetrics() {
    Logger.info('Starting metrics data load...');

    try {
        const data = await fetchWithFallback(Config.DATA_PATHS);

        if (!data) {
            Logger.warn('No data loaded from any path, using empty state');
            metricsData = { metrics: [] };
            return metricsData;
        }

        // Validate and normalize the data structure
        metricsData = normalizeMetrics(data);
        Logger.info(`Metrics loaded successfully: ${metricsData.metrics.length} records`);

        return metricsData;
    } catch (error) {
        Logger.error('Fatal error loading metrics', error);
        metricsData = { metrics: [] };
        return metricsData;
    }
}

/**
 * Fetch data with fallback paths
 * Tries each path in order until one succeeds
 * Implements timeout using AbortController for reliability
 * @param {Array<string>} paths - Array of paths to try
 * @returns {Promise<Object|null>} The fetched data or null
 */
async function fetchWithFallback(paths) {
    for (let i = 0; i < paths.length; i++) {
        const path = paths[i];
        Logger.debug(`Attempting to fetch from: ${path}`);

        // Add timeout using AbortController
        const controller = new AbortController();
        const timeoutId = setTimeout(
            () => controller.abort(),
            Config.FETCH_TIMEOUT
        );

        try {
            const response = await fetch(path, {
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                Logger.info(`Successfully loaded data from: ${path}`);
                return data;
            } else {
                Logger.debug(`Path ${path} returned status ${response.status}`);
            }
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                Logger.debug(`Path ${path} timed out after ${Config.FETCH_TIMEOUT}ms`);
            } else {
                Logger.debug(`Path ${path} failed: ${error.message}`);
            }
            continue;
        }
    }

    // All paths failed
    Logger.warn('Could not load metrics from any configured path', paths);
    return null;
}

/**
 * Normalize metrics data structure
 * Handles different schema variations and ensures consistent downstream structure
 * Fixes nested data structure issues (Bugs #2-5)
 * @param {Object} rawData - Raw data from JSON file
 * @returns {Object} Normalized data structure
 */
function normalizeMetrics(rawData) {
    if (!rawData || typeof rawData !== 'object') {
        throw new DataValidationError('Invalid data format: expected object', rawData);
    }

    if (!Array.isArray(rawData.metrics)) {
        throw new DataValidationError('Invalid data format: metrics must be an array', rawData);
    }

    // Normalize each metric record
    const normalizedMetrics = rawData.metrics.map(metric => normalizeMetricRecord(metric));

    return {
        metrics: normalizedMetrics,
        metadata: rawData.metadata || {}
    };
}

/**
 * Normalize a single metric record
 * Ensures consistent property structure regardless of source schema
 * @param {Object} metric - Raw metric record
 * @returns {Object} Normalized metric record
 */
function normalizeMetricRecord(metric) {
    // Create normalized record with all expected properties
    const normalized = {
        // Core identifiers
        source: metric.source || 'unknown',
        pipeline_type: metric.pipeline_type || 'unknown',
        timestamp: metric.timestamp || new Date().toISOString(),

        // Data volume metrics
        records_written: metric.records_written || 0,
        urls_scraped: metric.urls_scraped || 0,

        // Quality metrics (flattened from nested structure)
        // Bug Fix #2: Handle both flat and nested pipeline_metrics
        quality_pass_rate: metric.quality_pass_rate ||
                          metric.pipeline_metrics?.quality_pass_rate || 0,

        // Performance metrics (flattened from nested structure)
        // Bug Fix #3: Handle both flat and nested performance
        records_per_minute: metric.records_per_minute ||
                           metric.performance?.records_per_minute || 0,
        urls_per_second: metric.urls_per_second ||
                        metric.performance?.urls_per_second || 0,

        // Text length statistics (normalized property name)
        // Bug Fix #4: Handle both text_length_stats and quality properties
        text_length_stats: metric.text_length_stats ||
                          metric.quality ||
                          {
                              min: 0,
                              max: 0,
                              mean: 0,
                              median: 0
                          },

        // Duration
        duration_seconds: metric.duration_seconds || 0,

        // Legacy metrics (preserve for backward compatibility)
        legacy_metrics: metric.legacy_metrics || null
    };

    return normalized;
}

/**
 * Get currently loaded metrics data
 * @returns {Object|null} The metrics data or null if not loaded
 */
export function getMetrics() {
    return metricsData;
}

/**
 * Validate metrics data structure
 * @param {Object} data - Data to validate
 * @returns {boolean} True if valid
 */
export function validateMetrics(data) {
    if (!data || !data.metrics) {
        return false;
    }

    if (!Array.isArray(data.metrics)) {
        return false;
    }

    // Check that at least one metric has required fields
    if (data.metrics.length > 0) {
        const firstMetric = data.metrics[0];
        const requiredFields = ['source', 'records_written', 'timestamp'];

        for (const field of requiredFields) {
            if (!(field in firstMetric)) {
                Logger.warn(`Metric validation failed: missing field ${field}`);
                return false;
            }
        }
    }

    return true;
}

/**
 * Refresh metrics data
 * Reloads data from source
 * @returns {Promise<Object>} Refreshed metrics data
 */
export async function refreshMetrics() {
    Logger.info('Refreshing metrics data...');
    return await loadMetrics();
}
