/**
 * Manifest Analytics Feature Module
 * Displays manifest run history with summary cards and detailed table
 */

import { getManifestAnalytics } from '../core/data-service.js';
import Logger from '../utils/logger.js';

/**
 * Initialize manifest analytics visualization.
 * Fetches manifest data and renders summary + table.
 */
export async function initManifestAnalytics() {
    try {
        const analytics = await getManifestAnalytics();

        if (!analytics) {
            Logger.warn('No manifest analytics data available');
            renderErrorState('manifest-section', 'Manifest data is currently unavailable');
            return;
        }

        renderManifestSummary(analytics);
        renderManifestTable(analytics);
        Logger.info('Manifest analytics initialized', {
            runs: analytics.summary?.total_runs || 0
        });
    } catch (error) {
        Logger.error('Failed to initialize manifest analytics', error);
        renderErrorState('manifest-section', 'Failed to load manifest analytics');
    }
}

/**
 * Render manifest summary cards
 * Shows aggregate statistics across all runs
 * @param {Object} analytics - Manifest analytics data
 */
function renderManifestSummary(analytics) {
    const container = document.getElementById('manifest-summary');
    if (!container) {
        Logger.warn('Manifest summary container not found');
        return;
    }

    const summary = analytics.summary || {};
    const totalRuns = summary.total_runs || 0;
    const totalRecords = summary.total_records_ingested || 0;
    const quotaHitRuns = summary.quota_hit_runs || 0;

    container.innerHTML = `
        <div class="summary-cards">
            <div class="summary-card">
                <h4>Total Runs</h4>
                <p class="big-number">${totalRuns}</p>
            </div>
            <div class="summary-card">
                <h4>Total Records</h4>
                <p class="big-number">${formatNumber(totalRecords)}</p>
            </div>
            <div class="summary-card">
                <h4>Quota Hit Runs</h4>
                <p class="big-number">${quotaHitRuns}</p>
            </div>
        </div>
    `;
}

/**
 * Render manifest history table
 * Shows 10 most recent runs with details
 * @param {Object} analytics - Manifest analytics data
 */
function renderManifestTable(analytics) {
    const container = document.getElementById('manifest-table');
    if (!container) {
        Logger.warn('Manifest table container not found');
        return;
    }

    const recentManifests = analytics.recent_manifests || [];

    if (recentManifests.length === 0) {
        container.innerHTML = '<p class="chart-empty-state">No manifest runs available. Run the ingestion orchestrator to generate manifests.</p>';
        return;
    }

    const rows = recentManifests.map(manifest => renderTableRow(manifest)).join('');

    container.innerHTML = `
        <table class="manifest-history-table">
            <thead>
                <tr>
                    <th>Run ID</th>
                    <th>Timestamp</th>
                    <th>Records</th>
                    <th>Quota Hits</th>
                </tr>
            </thead>
            <tbody>
                ${rows}
            </tbody>
        </table>
    `;
}

/**
 * Render a single table row for a manifest run
 * @param {Object} manifest - Manifest run data
 * @returns {string} HTML string for table row
 */
function renderTableRow(manifest) {
    const runId = manifest.run_id || 'Unknown';
    const timestamp = formatTimestamp(manifest.timestamp);
    const totalRecords = formatNumber(manifest.total_records || 0);
    const quotaHits = manifest.sources_with_quota_hit || [];

    const quotaHitsDisplay = quotaHits.length > 0
        ? quotaHits.map(source => `<span class="quota-hit-badge">${source}</span>`).join(' ')
        : '—';

    return `
        <tr>
            <td><code>${runId}</code></td>
            <td>${timestamp}</td>
            <td>${totalRecords}</td>
            <td>${quotaHitsDisplay}</td>
        </tr>
    `;
}

/**
 * Format ISO 8601 timestamp to readable date/time
 * @param {string} timestamp - ISO 8601 timestamp
 * @returns {string} Formatted date string (e.g., "Nov 13, 2025, 2:30 PM")
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '—';

    try {
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) {
            return timestamp;
        }

        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        Logger.warn('Failed to format timestamp', { timestamp, error });
        return timestamp;
    }
}

/**
 * Format number with thousand separators
 * @param {number} num - Number to format
 * @returns {string} Formatted number (e.g., "12,600")
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString();
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
