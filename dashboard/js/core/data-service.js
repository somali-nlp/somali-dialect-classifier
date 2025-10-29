/**
 * Data Service Module
 * Handles loading, normalizing, and managing metrics data from JSON files
 * Implements error handling, data validation, and schema normalization
 */

import { Config } from '../config.js';
import { Logger, DataLoadError, DataValidationError } from '../utils/logger.js';

// Store dashboard data globally for the module
let dashboardData = {
    metrics: [],
    metadata: {},
    sankey: null,
    textDistributions: null
};

/**
 * Load metrics from JSON file with fallback paths and retry logic
 * Implements Bug Fix #1: Correct file path to data/all_metrics.json
 * @returns {Promise<Object>} The loaded and normalized metrics data
 */
export async function loadMetrics() {
    Logger.info('Starting dashboard data load...');

    try {
        const [rawMetrics, metadata, sankey, textDistributions] = await Promise.all([
            fetchWithFallback(Config.DATA_PATHS),
            fetchWithOptionalFallback(Config.METADATA_PATHS),
            fetchWithOptionalFallback(Config.SANKEY_PATHS),
            fetchWithOptionalFallback(Config.TEXT_DISTRIBUTION_PATHS)
        ]);

        if (!rawMetrics) {
            Logger.warn('No metrics data loaded from any path, using empty state');
            dashboardData = {
                metrics: [],
                metadata: metadata || {},
                sankey: normalizeSankeyData(sankey),
                textDistributions: normalizeTextDistributions(textDistributions)
            };
            return dashboardData;
        }

        const normalizedMetrics = normalizeMetrics(rawMetrics);

        dashboardData = {
            metrics: normalizedMetrics.metrics,
            metadata: metadata || rawMetrics.metadata || {},
            sankey: normalizeSankeyData(sankey || rawMetrics.sankey_flow),
            textDistributions: normalizeTextDistributions(textDistributions || rawMetrics.text_distributions)
        };

        Logger.info(`Dashboard data loaded: metrics=${dashboardData.metrics.length}, sankey=${dashboardData.sankey ? 'yes' : 'no'}, distributions=${dashboardData.textDistributions ? 'yes' : 'no'}`);

        return dashboardData;
    } catch (error) {
        Logger.error('Fatal error loading dashboard data', error);
        dashboardData = {
            metrics: [],
            metadata: {},
            sankey: null,
            textDistributions: null
        };
        return dashboardData;
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
 * Fetch data with fallback paths, but suppress warnings when all fail
 * Useful for optional datasets that may not exist yet
 * @param {Array<string>} paths - Array of paths to try
 * @returns {Promise<Object|null>} The fetched data or null
 */
async function fetchWithOptionalFallback(paths) {
    if (!Array.isArray(paths) || paths.length === 0) {
        return null;
    }

    for (let i = 0; i < paths.length; i++) {
        const path = paths[i];
        Logger.debug(`Attempting optional fetch from: ${path}`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), Config.FETCH_TIMEOUT);

        try {
            const response = await fetch(path, { signal: controller.signal });
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                Logger.info(`Loaded optional data from: ${path}`);
                return data;
            }
        } catch (error) {
            clearTimeout(timeoutId);
            Logger.debug(`Optional path ${path} unavailable: ${error.message}`);
        }
    }

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
    const snapshot = metric.snapshot || metric.legacy_metrics?.snapshot || {};
    const layered = metric.layered_metrics || {};
    const performance = metric.performance || metric.statistics || {};
    const quality = layered.quality || metric.quality || {};

    // Create normalized record with all expected properties
    const normalized = {
        // Core identifiers
        source: metric.source || 'unknown',
        pipeline_type: metric.pipeline_type || 'unknown',
        timestamp: metric.timestamp || new Date().toISOString(),

        // Data volume metrics
        records_written: metric.records_written || 0,
        urls_scraped: metric.urls_scraped || 0,
        urls_discovered: metric.urls_discovered || snapshot.urls_discovered || snapshot.files_discovered || 0,
        urls_fetched: metric.urls_fetched || snapshot.urls_fetched || snapshot.files_processed || 0,
        records_extracted: metric.records_extracted || snapshot.records_extracted || snapshot.urls_processed || 0,

        // Quality metrics (flattened from nested structure)
        // Bug Fix #2: Handle both flat and nested pipeline_metrics
        quality_pass_rate: metric.quality_pass_rate ||
                          metric.pipeline_metrics?.quality_pass_rate || 0,
        http_request_success_rate: metric.http_request_success_rate ||
                                    performance.http_request_success_rate ||
                                    performance.fetch_success_rate || 0,
        content_extraction_success_rate: metric.content_extraction_success_rate ||
                                         performance.content_extraction_success_rate || 0,
        deduplication_rate: metric.deduplication_rate ||
                            performance.deduplication_rate || 0,

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
        filter_breakdown: quality.filter_breakdown || snapshot.filter_reasons || {},

        // Duration
        duration_seconds: metric.duration_seconds || 0,

        // Legacy metrics (preserve for backward compatibility)
        legacy_metrics: metric.legacy_metrics || null
    };

    return normalized;
}

/**
 * Normalize Sankey flow data
 * @param {Object|null} data - Raw sankey data
 * @returns {Object|null}
 */
function normalizeSankeyData(data) {
    if (!data || typeof data !== 'object') {
        return null;
    }

    const stageCounts = data.stage_counts || {};
    const normalizedStages = {
        discovered: stageCounts.discovered || stageCounts.discovery || 0,
        fetched: stageCounts.fetched || stageCounts.quality_received || stageCounts.discovered || 0,
        extracted: stageCounts.extracted || stageCounts.records_extracted || 0,
        quality_received: stageCounts.quality_received || stageCounts.extracted || 0,
        quality_passed: stageCounts.quality_passed || stageCounts.passed_quality || 0,
        written: stageCounts.written || stageCounts['Silver Dataset'] || stageCounts.quality_passed || 0
    };

    const hasData = Object.values(normalizedStages).some(value => value > 0) ||
                    (Array.isArray(data.links) && data.links.length > 0);

    if (!hasData) {
        return null;
    }

    return {
        nodes: data.nodes || [],
        links: data.links || [],
        filter_breakdown: data.filter_breakdown || {},
        stage_counts: normalizedStages,
        generated_at: data.generated_at || null
    };
}

/**
 * Normalize text distribution data for ridge plot
 * @param {Object|null} data - Raw text distribution data
 * @returns {Object|null}
 */
function normalizeTextDistributions(data) {
    if (!data || typeof data !== 'object') {
        return null;
    }

    const distributions = data.distributions || {};
    const sources = data.sources || Object.keys(distributions);

    if (!sources || sources.length === 0) {
        return null;
    }

    return {
        sources,
        bin_info: data.bin_info || {},
        distributions,
        generated_at: data.generated_at || null
    };
}

/**
 * Get currently loaded metrics data
 * @returns {Object|null} The metrics data or null if not loaded
 */
export function getMetrics() {
    return dashboardData;
}

export function getSankeyFlow() {
    return dashboardData.sankey;
}

export function getTextDistributions() {
    return dashboardData.textDistributions;
}

export function getDashboardMetadata() {
    return dashboardData.metadata;
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
