/**
 * Quota Status Feature Module
 * Displays quota usage cards with progress bars and quota hit indicators
 */

import { getQuotaStatus } from '../core/data-service.js';
import { Logger } from '../utils/logger.js';

/**
 * Initialize quota status visualization.
 * Fetches quota data and renders cards with progress bars.
 */
export async function initQuotaStatus() {
    try {
        const quotaData = await getQuotaStatus();

        if (!quotaData) {
            Logger.warn('No quota status data available');
            renderErrorState('quota-cards', 'Quota data is currently unavailable');
            return;
        }

        renderQuotaCards(quotaData);
        Logger.info('Quota status initialized', {
            sources: quotaData.summary?.sources_with_quotas?.length || 0
        });
    } catch (error) {
        Logger.error('Failed to initialize quota status', error);
        renderErrorState('quota-cards', 'Failed to load quota status');
    }
}

/**
 * Render quota cards showing current usage per source
 * @param {Object} quotaData - Quota status data from JSON file
 */
function renderQuotaCards(quotaData) {
    const container = document.getElementById('quota-cards');
    if (!container) {
        Logger.warn('Quota cards container not found');
        return;
    }

    // Get latest usage for each source
    const latestBySource = getLatestUsageBySource(quotaData.daily_usage || []);

    // Define all sources (even those without quotas)
    const allSources = ['bbc', 'huggingface', 'sprakbanken', 'wikipedia', 'tiktok'];

    // Render cards for all sources
    const cards = allSources
        .map(source => renderQuotaCard(source, latestBySource[source], quotaData.quota_hits_by_source || {}))
        .join('');

    container.innerHTML = cards || '<p class="chart-empty-state">No quota data available.</p>';
}

/**
 * Get latest usage record for each source
 * @param {Array} dailyUsage - Array of daily usage records
 * @returns {Object} Map of source name to latest usage record
 */
function getLatestUsageBySource(dailyUsage) {
    const latestBySource = {};

    dailyUsage.forEach(record => {
        const source = record.source;
        if (!source) return;

        // Keep the record with the latest date
        if (!latestBySource[source] || record.date > latestBySource[source].date) {
            latestBySource[source] = record;
        }
    });

    return latestBySource;
}

/**
 * Render a single quota card for a source using roster-card pattern
 * @param {string} source - Source identifier (e.g., "bbc")
 * @param {Object} data - Latest usage data for the source (null if no quota)
 * @param {Object} quotaHits - Map of source to array of quota hit dates
 * @returns {string} HTML string for the card
 */
function renderQuotaCard(source, data, quotaHits) {
    const sourceName = normalizeSourceName(source);

    // Handle sources without quotas
    if (!data) {
        let explanation = '';
        if (source === 'wikipedia') {
            explanation = 'Batch file processing · No rate limits';
        } else if (source === 'tiktok') {
            explanation = 'Apify API ingestion · Links provided, cost-based';
        }

        return `
            <article class="roster-card">
                <h3>${sourceName}</h3>
                <p class="roster-value">—</p>
                <p class="roster-caption">${explanation}</p>
            </article>
        `;
    }

    // Sources with quotas
    const quotaHitCount = (quotaHits[source] || []).length;
    const usagePercent = Math.round(data.usage_percent || 0);

    return `
        <article class="roster-card">
            <h3>${sourceName}</h3>
            <p class="roster-value">${usagePercent}%</p>
            <p class="roster-caption">
                ${data.records_ingested.toLocaleString()} / ${data.quota_limit.toLocaleString()}
                ${data.items_remaining > 0 ? ` · ${data.items_remaining.toLocaleString()} remaining` : ''}
            </p>
            ${quotaHitCount > 0 ? `<p class="roster-caption" style="margin-top: 0.5rem;">Quota hits (30d): ${quotaHitCount}</p>` : ''}
        </article>
    `;
}

/**
 * Normalize source name for display
 * Maps internal identifiers to human-readable names
 * @param {string} source - Source identifier
 * @returns {string} Normalized source name
 */
function normalizeSourceName(source) {
    const names = {
        'bbc': 'BBC Somali',
        'huggingface': 'HuggingFace',
        'sprakbanken': 'Språkbanken',
        'wikipedia': 'Wikipedia',
        'tiktok': 'TikTok'
    };
    return names[source.toLowerCase()] || source;
}

/**
 * Render error state in container
 * @param {string} containerId - ID of container element
 * @param {string} message - Error message to display
 */
function renderErrorState(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `<p class="chart-empty-state">${message}</p>`;
}
