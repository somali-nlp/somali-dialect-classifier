/**
 * Quota Status Feature Module
 * Displays quota usage cards with progress bars and quota hit indicators
 */

import { getQuotaStatus } from '../core/data-service.js';
import Logger from '../utils/logger.js';

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

    if (Object.keys(latestBySource).length === 0) {
        container.innerHTML = '<p class="chart-empty-state">No quota data available. Run the ingestion orchestrator to populate quota tracking.</p>';
        return;
    }

    // Render cards for each source
    const cards = Object.entries(latestBySource)
        .sort((a, b) => a[0].localeCompare(b[0])) // Sort by source name alphabetically
        .map(([source, data]) => renderQuotaCard(source, data, quotaData.quota_hits_by_source || {}))
        .join('');

    container.innerHTML = cards;
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
 * Render a single quota card for a source
 * @param {string} source - Source identifier (e.g., "bbc")
 * @param {Object} data - Latest usage data for the source
 * @param {Object} quotaHits - Map of source to array of quota hit dates
 * @returns {string} HTML string for the card
 */
function renderQuotaCard(source, data, quotaHits) {
    const sourceName = normalizeSourceName(source);
    const usageColor = getUsageColor(data.usage_percent || 0);
    const quotaHitCount = (quotaHits[source] || []).length;
    const quotaHitBadge = data.quota_hit
        ? '<span class="quota-hit-badge">Quota Hit</span>'
        : '';

    const itemsRemainingText = data.items_remaining > 0
        ? `<p class="items-remaining">${data.items_remaining.toLocaleString()} items remaining</p>`
        : '';

    return `
        <div class="quota-card">
            <div class="quota-card-header">
                <h3>${sourceName}</h3>
                ${quotaHitBadge}
            </div>
            <div class="quota-usage">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${Math.min(data.usage_percent, 100)}%; background-color: ${usageColor}"></div>
                </div>
                <p class="usage-text">${data.records_ingested.toLocaleString()} / ${data.quota_limit.toLocaleString()} (${data.usage_percent.toFixed(1)}%)</p>
                ${itemsRemainingText}
            </div>
            <div class="quota-stats">
                <p>Quota hits (30d): ${quotaHitCount}</p>
            </div>
        </div>
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
 * Get usage color based on percentage
 * Color coding: green (<80%), orange (80-99%), red (100%)
 * @param {number} usagePercent - Usage percentage (0-100)
 * @returns {string} CSS color variable
 */
function getUsageColor(usagePercent) {
    if (usagePercent >= 100) return 'var(--error)';      // Red
    if (usagePercent >= 80) return 'var(--warning)';     // Orange
    return 'var(--success)';                              // Green
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
