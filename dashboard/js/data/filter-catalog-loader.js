/**
 * Dynamic filter catalog loader.
 * Fetches filter metadata from Python-generated JSON catalog.
 *
 * This module provides the frontend with access to the canonical filter
 * catalog maintained in Python, eliminating manual label synchronization.
 */

import { Logger } from '../utils/logger.js';

// In-memory cache to avoid repeated fetches
let cachedCatalog = null;

/**
 * Load filter catalog from JSON.
 *
 * Fetches the filter catalog exported by the Python backend
 * (scripts/export_filter_catalog.py). Results are cached in memory
 * to avoid repeated HTTP requests.
 *
 * @returns {Promise<Object>} Filter catalog with filters, categories, version
 * @throws {Error} If fetch fails and no cache available
 */
export async function loadFilterCatalog() {
    // Return cached catalog if available
    if (cachedCatalog !== null) {
        Logger.debug('Returning cached filter catalog');
        return cachedCatalog;
    }

    try {
        const response = await fetch('/data/filter_catalog.json');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const catalog = await response.json();

        // Validate structure
        if (!catalog.filters || typeof catalog.filters !== 'object') {
            throw new Error('Invalid catalog structure: missing filters object');
        }

        // Cache the result
        cachedCatalog = catalog;

        const filterCount = Object.keys(catalog.filters).length;
        const version = catalog.version || 'unknown';

        Logger.info(`Filter catalog loaded: ${filterCount} filters (version ${version})`);

        return catalog;

    } catch (error) {
        Logger.error('Failed to load filter catalog:', error);

        // Fallback to hardcoded labels if fetch fails
        Logger.warn('Using fallback hardcoded filter labels');
        const fallback = getFallbackCatalog();

        // Cache the fallback to avoid repeated fetch attempts
        cachedCatalog = fallback;

        return fallback;
    }
}

/**
 * Extract labels-only mapping for backward compatibility.
 *
 * Transforms the full catalog structure into a simple key-value map
 * compatible with existing code that expects FILTER_REASON_LABELS.
 *
 * @param {Object} catalog - Full catalog from loadFilterCatalog()
 * @returns {Object} Map of filter_key -> label string
 */
export function extractLabels(catalog) {
    const labels = {};

    for (const [key, metadata] of Object.entries(catalog.filters)) {
        labels[key] = metadata.label;
    }

    return labels;
}

/**
 * Fallback catalog if JSON fetch fails.
 *
 * Uses current hardcoded labels from aggregates.js as a safety net.
 * This ensures the dashboard remains functional even if the catalog
 * JSON is unavailable (e.g., during development, network issues).
 *
 * @returns {Object} Fallback catalog structure
 */
function getFallbackCatalog() {
    return {
        filters: {
            // Length filters
            min_length_filter: {
                label: 'Minimum length (50 chars)',
                description: 'Text must be at least 50 characters',
                category: 'length'
            },

            // Language filters
            langid_filter: {
                label: 'Language ID (non-Somali)',
                description: 'Text identified as non-Somali language',
                category: 'language'
            },

            // Cleaning filters
            empty_after_cleaning: {
                label: 'Empty after cleaning',
                description: 'Text becomes empty after cleaning operations',
                category: 'cleaning'
            },

            // TikTok early-stage filters
            emoji_only_comment: {
                label: 'Emoji-only comment',
                description: 'Comment contains only emoji characters',
                category: 'tiktok'
            },
            text_too_short_after_cleanup: {
                label: 'Very short text (<3 chars)',
                description: 'Text too short after cleanup operations',
                category: 'tiktok'
            },

            // Topic enrichment filters
            topic_lexicon_enrichment_filter: {
                label: 'Topic lexicon enrichment',
                description: 'Enriches records with topic/domain markers (NOT dialect detection)',
                category: 'enrichment'
            },

            // Wikipedia-specific
            namespace_filter: {
                label: 'Wikipedia namespace exclusion',
                description: 'Wikipedia namespace excluded from dataset',
                category: 'wikipedia'
            },

            // Future filters
            quality_score_filter: {
                label: 'Quality score threshold',
                description: 'Quality score below threshold',
                category: 'quality'
            },
            profanity_filter: {
                label: 'Profanity detection',
                description: 'Text contains profanity',
                category: 'quality'
            },
            toxic_filter: {
                label: 'Toxicity detection',
                description: 'Text flagged as toxic',
                category: 'quality'
            },
            duplicate_filter: {
                label: 'Duplicate content',
                description: 'Duplicate or near-duplicate content',
                category: 'quality'
            },
            invalid_charset_filter: {
                label: 'Invalid character encoding',
                description: 'Invalid character encoding detected',
                category: 'technical'
            },
            encoding_filter: {
                label: 'Encoding issues',
                description: 'Text encoding issues detected',
                category: 'technical'
            },
            stopword_filter: {
                label: 'Stopword threshold',
                description: 'Stopword ratio exceeds threshold',
                category: 'quality'
            },

            // Fallback
            unspecified_filter: {
                label: 'Unspecified filter',
                description: 'Filter reason not specified',
                category: 'other'
            }
        },
        categories: {
            length: ['min_length_filter'],
            language: ['langid_filter'],
            cleaning: ['empty_after_cleaning'],
            tiktok: ['emoji_only_comment', 'text_too_short_after_cleanup'],
            enrichment: ['topic_lexicon_enrichment_filter'],
            wikipedia: ['namespace_filter'],
            quality: ['quality_score_filter', 'profanity_filter', 'toxic_filter',
                     'duplicate_filter', 'stopword_filter'],
            technical: ['invalid_charset_filter', 'encoding_filter'],
            other: ['unspecified_filter']
        },
        version: '0.0.0-fallback',
        last_updated: new Date().toISOString()
    };
}

/**
 * Clear the cached catalog.
 *
 * Useful for testing or when you need to force a fresh fetch.
 * Not typically needed in production code.
 *
 * @private
 */
export function clearCache() {
    cachedCatalog = null;
    Logger.debug('Filter catalog cache cleared');
}
