/**
 * Manifest Analytics Feature Module
 * Displays manifest run history with summary cards and detailed table
 */

import { getManifestAnalytics } from '../core/data-service.js';
import { Logger } from '../utils/logger.js';

/**
 * Initialize manifest analytics visualization.
 * Fetches manifest data and renders summary + table.
 */
export async function initManifestAnalytics() {
    try {
        const analytics = await getManifestAnalytics();

        if (!analytics) {
            Logger.warn('No manifest analytics data available');
            renderErrorState('manifest-summary', 'Manifest data is currently unavailable');
            return;
        }

        renderManifestSummary(analytics);
        renderManifestTable(analytics);
        Logger.info('Manifest analytics initialized', {
            runs: analytics.summary?.total_runs || 0
        });
    } catch (error) {
        Logger.error('Failed to initialize manifest analytics', error);
        renderErrorState('manifest-summary', 'Failed to load manifest analytics');
    }
}

/**
 * Render manifest summary cards using roster-card pattern
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
        <article class="roster-card">
            <h3>Total Runs</h3>
            <p class="roster-value big-number">${totalRuns}</p>
            <p class="roster-caption">Orchestration executions</p>
        </article>
        <article class="roster-card">
            <h3>Total Records</h3>
            <p class="roster-value big-number">${formatNumber(totalRecords)}</p>
            <p class="roster-caption">Records ingested across all runs</p>
        </article>
        <article class="roster-card">
            <h3>Quota Hit Runs</h3>
            <p class="roster-value big-number">${quotaHitRuns}</p>
            <p class="roster-caption">Runs with quota limits reached</p>
        </article>
    `;
}

/**
 * Render manifest history table
 * Shows 10 most recent runs with details
 * @param {Object} analytics - Manifest analytics data
 */
function renderManifestTable(analytics) {
    const tbody = document.getElementById('manifest-table-body');
    if (!tbody) {
        Logger.warn('Manifest table body not found');
        return;
    }

    const recentManifests = analytics.recent_manifests || [];

    if (recentManifests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 3rem 2rem; color: var(--gray-500);">No manifest runs available. Run the ingestion orchestrator to generate manifests.</td></tr>';
        return;
    }

    const rows = recentManifests.map(manifest => renderTableRow(manifest)).join('');
    tbody.innerHTML = rows;
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
        ? quotaHits.join(', ')
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
