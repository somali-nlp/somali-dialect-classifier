/**
 * UI Renderer Module
 * Populates DOM elements with metrics data
 */

import { getMetrics } from './data-service.js';
import { normalizeSourceName } from '../utils/formatters.js';

/**
 * Populate the source comparison table
 */
export function populateSourceTable() {
    const metricsData = getMetrics();
    const tbody = document.getElementById('sourceTableBody');
    if (!tbody) return;

    // Handle empty state
    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 2rem; color: var(--gray-500);">
                    No data available yet. Run the data ingestion pipeline to populate metrics.
                </td>
            </tr>
        `;
        return;
    }

    // Build rows from real metrics data
    const rows = metricsData.metrics.map(metric => {
        // Bug Fix #9: Use consistent source name normalization
        const sourceName = normalizeSourceName(metric.source);

        const records = metric.records_written;
        // Bug Fix #2: Use flattened quality_pass_rate (normalized by data-service)
        const qualityRate = metric.quality_pass_rate || 0;
        const qualityRateFormatted = (qualityRate * 100).toFixed(1) + '%';
        // Bug Fix #4: Use text_length_stats.mean (normalized by data-service)
        const avgLength = metric.text_length_stats?.mean ? Math.round(metric.text_length_stats.mean).toLocaleString() : '0';

        // Format total chars
        const totalChars = metric.quality?.total_chars || 0;
        const formattedChars = totalChars >= 1000000
            ? (totalChars / 1000000).toFixed(1) + 'M'
            : totalChars >= 1000
            ? (totalChars / 1000).toFixed(0) + 'K'
            : totalChars.toString();

        return {
            name: sourceName,
            records,
            quality: qualityRateFormatted,
            avgLength,
            totalChars: formattedChars
        };
    });

    tbody.innerHTML = rows.map(row => `
        <tr>
            <td style="font-weight: 600;">${row.name}</td>
            <td>${row.records.toLocaleString()}</td>
            <td>${row.quality}</td>
            <td>${row.avgLength}</td>
            <td>${row.totalChars}</td>
        </tr>
    `).join('');
}

/**
 * Populate quality metrics cards in the Quality tab
 */
export function populateQualityMetrics() {
    const metricsData = getMetrics();

    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        // Hide quality metrics section or show empty state
        const qualitySection = document.querySelector('#quality-panel .source-grid');
        if (qualitySection) {
            qualitySection.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--gray-500);">
                    <p>No quality metrics available yet. Run the data ingestion pipeline to populate metrics.</p>
                </div>
            `;
        }
        return;
    }

    // Create a map of sources to their quality data
    const sourceQualityMap = {
        'Wikipedia': metricsData.metrics.find(m => m.source.includes('Wikipedia')),
        'BBC': metricsData.metrics.find(m => m.source.includes('BBC')),
        'HuggingFace': metricsData.metrics.find(m => m.source.includes('HuggingFace')),
        'Språkbanken': metricsData.metrics.find(m => m.source.includes('Sprakbanken'))
    };

    // Update Wikipedia Somali card
    const wikipediaCard = document.querySelector('#quality-panel .source-grid .source-card:nth-child(1)');
    if (wikipediaCard && sourceQualityMap['Wikipedia']) {
        updateQualityCard(wikipediaCard, sourceQualityMap['Wikipedia']);
    }

    // Update BBC Somali card
    const bbcCard = document.querySelector('#quality-panel .source-grid .source-card:nth-child(2)');
    if (bbcCard && sourceQualityMap['BBC']) {
        updateQualityCard(bbcCard, sourceQualityMap['BBC']);
    }

    // Update HuggingFace MC4 card
    const hfCard = document.querySelector('#quality-panel .source-grid .source-card:nth-child(3)');
    if (hfCard && sourceQualityMap['HuggingFace']) {
        updateQualityCard(hfCard, sourceQualityMap['HuggingFace']);
    }

    // Update Språkbanken card
    const sprakCard = document.querySelector('#quality-panel .source-grid .source-card:nth-child(4)');
    if (sprakCard && sourceQualityMap['Språkbanken']) {
        updateQualityCard(sprakCard, sourceQualityMap['Språkbanken']);
    }
}

/**
 * Update a single quality card with metric data
 */
function updateQualityCard(card, metric) {
    // Bug Fix #5: Use text_length_stats (normalized by data-service)
    if (!card || !metric || !metric.text_length_stats) return;

    const metrics = card.querySelectorAll('.source-metric-value');
    if (metrics.length === 4) {
        // Min Length
        metrics[0].textContent = (metric.text_length_stats.min || 0).toLocaleString() + ' chars';

        // Max Length
        const maxChars = metric.text_length_stats.max || 0;
        metrics[1].textContent = maxChars >= 1000
            ? Math.round(maxChars / 1000).toLocaleString() + 'K chars'
            : maxChars.toLocaleString() + ' chars';

        // Mean Length
        metrics[2].textContent = Math.round(metric.text_length_stats.mean || 0).toLocaleString() + ' chars';

        // Median Length
        metrics[3].textContent = Math.round(metric.text_length_stats.median || 0).toLocaleString() + ' chars';
    }
}

/**
 * Populate performance metrics cards in the Pipeline tab
 */
export function populatePerformanceMetrics() {
    const metricsData = getMetrics();

    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        const perfSection = document.querySelector('#pipeline-panel .source-grid');
        if (perfSection) {
            perfSection.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--gray-500);">
                    <p>No performance metrics available yet. Run the data ingestion pipeline to populate metrics.</p>
                </div>
            `;
        }
        return;
    }

    // Create a map of sources to their performance data
    const sourcePerfMap = {
        'Wikipedia': metricsData.metrics.find(m => m.source.includes('Wikipedia')),
        'BBC': metricsData.metrics.find(m => m.source.includes('BBC')),
        'HuggingFace': metricsData.metrics.find(m => m.source.includes('HuggingFace')),
        'Språkbanken': metricsData.metrics.find(m => m.source.includes('Sprakbanken'))
    };

    // Update Wikipedia Somali card
    const wikipediaCard = document.querySelector('#pipeline-panel .source-grid .source-card:nth-child(1)');
    if (wikipediaCard && sourcePerfMap['Wikipedia']) {
        updatePerformanceCard(wikipediaCard, sourcePerfMap['Wikipedia']);
    }

    // Update BBC Somali card
    const bbcCard = document.querySelector('#pipeline-panel .source-grid .source-card:nth-child(2)');
    if (bbcCard && sourcePerfMap['BBC']) {
        updatePerformanceCard(bbcCard, sourcePerfMap['BBC']);
    }

    // Update HuggingFace MC4 card
    const hfCard = document.querySelector('#pipeline-panel .source-grid .source-card:nth-child(3)');
    if (hfCard && sourcePerfMap['HuggingFace']) {
        updatePerformanceCard(hfCard, sourcePerfMap['HuggingFace']);
    }

    // Update Språkbanken card
    const sprakCard = document.querySelector('#pipeline-panel .source-grid .source-card:nth-child(4)');
    if (sprakCard && sourcePerfMap['Språkbanken']) {
        updatePerformanceCard(sprakCard, sourcePerfMap['Språkbanken']);
    }
}

/**
 * Update a single performance card with metric data
 */
function updatePerformanceCard(card, metric) {
    if (!card || !metric) return;

    const metrics = card.querySelectorAll('.source-metric-value');
    if (metrics.length === 3) {
        // URLs/Second
        // Bug Fix #3: Use flattened urls_per_second (normalized by data-service)
        const urlsPerSec = metric.urls_per_second || 0;
        metrics[0].textContent = urlsPerSec >= 1
            ? Math.round(urlsPerSec).toLocaleString()
            : urlsPerSec.toFixed(2);

        // Records/Minute
        // Bug Fix #3: Use flattened records_per_minute (normalized by data-service)
        const recordsPerMin = metric.records_per_minute || 0;
        metrics[1].textContent = recordsPerMin >= 1
            ? Math.round(recordsPerMin).toLocaleString()
            : recordsPerMin.toFixed(2);

        // Duration
        const duration = metric.duration_seconds || 0;
        metrics[2].textContent = duration >= 60
            ? Math.round(duration / 60).toLocaleString() + 'm'
            : duration.toFixed(1) + 's';
    }
}

/**
 * Populate overview source cards
 */
export function populateOverviewCards() {
    const metricsData = getMetrics();

    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        // Set all cards to empty state
        const sourceCards = document.querySelectorAll('#overview-panel .source-card');
        sourceCards.forEach(card => {
            const metrics = card.querySelectorAll('.source-metric-value');
            metrics.forEach(m => m.textContent = '0');
            const footer = card.querySelector('.source-card-footer span:first-child');
            if (footer) footer.textContent = 'No data yet';
        });
        return;
    }

    // Calculate total records for percentages
    const totalRecords = metricsData.metrics.reduce((sum, m) => sum + m.records_written, 0);

    // Create a map of sources to their data
    const sourceDataMap = {
        'Wikipedia': metricsData.metrics.find(m => m.source.includes('Wikipedia')),
        'BBC': metricsData.metrics.find(m => m.source.includes('BBC')),
        'HuggingFace': metricsData.metrics.find(m => m.source.includes('HuggingFace')),
        'Språkbanken': metricsData.metrics.find(m => m.source.includes('Sprakbanken'))
    };

    // Update Wikipedia Somali card
    const wikipediaCard = document.querySelector('#overview-panel .source-card.wikipedia');
    if (wikipediaCard && sourceDataMap['Wikipedia']) {
        updateOverviewCard(wikipediaCard, sourceDataMap['Wikipedia'], totalRecords);
    }

    // Update BBC Somali card
    const bbcCard = document.querySelector('#overview-panel .source-card.bbc');
    if (bbcCard && sourceDataMap['BBC']) {
        updateOverviewCard(bbcCard, sourceDataMap['BBC'], totalRecords);
    }

    // Update HuggingFace MC4 card
    const hfCard = document.querySelector('#overview-panel .source-card.huggingface');
    if (hfCard && sourceDataMap['HuggingFace']) {
        updateOverviewCard(hfCard, sourceDataMap['HuggingFace'], totalRecords);
    }

    // Update Språkbanken card
    const sprakCard = document.querySelector('#overview-panel .source-card.sprakbanken');
    if (sprakCard && sourceDataMap['Språkbanken']) {
        updateOverviewCard(sprakCard, sourceDataMap['Språkbanken'], totalRecords);
    }
}

/**
 * Update a single overview card with metric data
 */
function updateOverviewCard(card, metric, totalRecords) {
    if (!card || !metric) return;

    const metrics = card.querySelectorAll('.source-metric-value');
    if (metrics.length === 3) {
        // Records
        const records = metric.records_written || 0;
        metrics[0].textContent = records.toLocaleString();
        metrics[0].setAttribute('data-value', records);

        // Percentage
        const percentage = totalRecords > 0 ? (records / totalRecords * 100) : 0;
        metrics[1].textContent = percentage.toFixed(1) + '%';

        // Quality Rate (pipeline-specific)
        // Bug Fix #2: Use flattened quality_pass_rate (normalized by data-service)
        const qualityRate = metric.quality_pass_rate || 0;
        metrics[2].textContent = (qualityRate * 100).toFixed(1) + '%';
    }

    // Update last run date
    const footer = card.querySelector('.source-card-footer span:first-child');
    if (footer && metric.timestamp) {
        const date = new Date(metric.timestamp);
        const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        footer.textContent = `Last run: ${formattedDate}`;
    }
}

/**
 * Update quality metrics with real data
 */
export function updateQualityMetrics() {
    const metricsData = getMetrics();
    if (!metricsData || !metricsData.metrics) return;

    const sourceDataMap = {
        'Wikipedia': metricsData.metrics.find(m => m.source.includes('Wikipedia')),
        'BBC': metricsData.metrics.find(m => m.source.includes('BBC')),
        'HuggingFace': metricsData.metrics.find(m => m.source.includes('HuggingFace')),
        'Sprakbanken': metricsData.metrics.find(m => m.source.includes('Sprakbanken'))
    };

    Object.keys(sourceDataMap).forEach(sourceName => {
        const metric = sourceDataMap[sourceName];
        const card = document.querySelector(`[data-quality-source="${sourceName}"]`);

        if (card && metric) {
            // Bug Fix #5: Use normalized text_length_stats (data-service handles fallback)
            const stats = metric.text_length_stats;

            if (stats) {
                const minEl = card.querySelector('.quality-min');
                const maxEl = card.querySelector('.quality-max');
                const meanEl = card.querySelector('.quality-mean');
                const medianEl = card.querySelector('.quality-median');

                if (minEl) minEl.textContent = (stats.min || 0).toLocaleString() + ' chars';
                if (maxEl) maxEl.textContent = (stats.max || 0).toLocaleString() + ' chars';
                if (meanEl) meanEl.textContent = (stats.mean || 0).toFixed(0) + ' chars';
                if (medianEl) medianEl.textContent = (stats.median || 0).toFixed(0) + ' chars';
            } else {
                // No data available
                const values = card.querySelectorAll('.source-metric-value');
                values.forEach(v => v.textContent = 'N/A');
            }
        }
    });
}
