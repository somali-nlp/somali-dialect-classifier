/**
 * UI Renderer Module
 * Populates DOM elements with metrics data
 */

import { getMetrics } from './data-service.js';
import { normalizeSourceName, formatDate } from '../utils/formatters.js';

const SOURCE_METADATA = {
    'Wikipedia': {
        role: 'Volume Backbone',
        pipeline: 'File Processing',
        description: 'Anchors breadth with encyclopedic coverage while filters trim stubs.',
        qualityBenchmark: 0.5,
        icon: `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
                <path d="M8 7h6"/>
                <path d="M8 11h8"/>
            </svg>`
    },
    'BBC': {
        role: 'Fresh News Feed',
        pipeline: 'Web Scraping',
        description: 'Delivers professionally edited news for contemporary language coverage.',
        qualityBenchmark: 0.7,
        icon: `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
                <path d="M18 14h-8"/>
                <path d="M15 18h-5"/>
                <path d="M10 6h8v4h-8V6Z"/>
            </svg>`
    },
    'HuggingFace': {
        role: 'ML-Ready Snippets',
        pipeline: 'Stream Processing',
        description: 'Supplies preprocessed Somali text from web crawls for model experimentation.',
        qualityBenchmark: 0.7,
        icon: `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <circle cx="12" cy="19" r="3"/>
            </svg>`
    },
    'Språkbanken': {
        role: 'Curated Academic Corpus',
        pipeline: 'File Processing',
        description: 'Adds linguistically annotated research texts with strong formal language signals.',
        qualityBenchmark: 0.7,
        icon: `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/>
                <path d="M22 10v6"/>
                <path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>
            </svg>`
    }
};

const FILTER_LABELS = {
    min_length_filter: 'min-length filter',
    langid_filter: 'language ID check',
    empty_after_cleaning: 'empty-after-cleaning guard',
    quality_score_filter: 'quality score threshold',
    profanity_filter: 'profanity filter',
    toxic_filter: 'toxicity filter',
    duplicate_filter: 'duplicate detector'
};

let sourceTableRows = [];
let sourceTableSort = { key: 'records', direction: 'desc' };
let sourceTableListenersAttached = false;

function getMetadataKey(sourceName) {
    if (!sourceName) return null;
    if (sourceName.includes('Wikipedia')) return 'Wikipedia';
    if (sourceName.includes('BBC')) return 'BBC';
    if (sourceName.includes('HuggingFace')) return 'HuggingFace';
    if (sourceName.includes('Spr')) return 'Språkbanken';
    return sourceName;
}

function getTopFilterInsight(breakdown = {}) {
    const entries = Object.entries(breakdown)
        .filter(([, count]) => Number.isFinite(count) && count > 0)
        .sort((a, b) => b[1] - a[1]);

    if (!entries.length) return null;

    const total = entries.reduce((sum, [, count]) => sum + count, 0);
    if (!total) return null;

    const [reason, count] = entries[0];
    const label = FILTER_LABELS[reason] || reason.replace(/_/g, ' ');
    const percentage = (count / total) * 100;
    return { label, percentage };
}

function buildSourceAnalytics() {
    const metricsData = getMetrics();
    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        return null;
    }

    const totalRecords = metricsData.metrics.reduce((sum, metric) => sum + (metric.records_written || 0), 0);

    const items = metricsData.metrics.map(metric => {
        const sourceName = normalizeSourceName(metric.source);
        const metadataKey = getMetadataKey(sourceName);
        const meta = SOURCE_METADATA[metadataKey] || {
            role: 'Active Source',
            pipeline: 'Pipeline',
            description: '',
            qualityBenchmark: 0.7,
            icon: ''
        };

        const records = metric.records_written || 0;
        const share = totalRecords > 0 ? (records / totalRecords) * 100 : 0;
        const quality = metric.quality_pass_rate || 0;
        const avgLength = metric.text_length_stats?.mean || 0;
        const totalChars = metric.text_length_stats?.total_chars || 0;
        const timestamp = metric.timestamp || null;
        const timestampMs = timestamp ? Date.parse(timestamp) : null;
        const filterBreakdown = metric.filter_breakdown || {};
        const topFilter = getTopFilterInsight(filterBreakdown);

        return {
            name: sourceName,
            records,
            share,
            quality,
            avgLength,
            totalChars,
            lastUpdated: timestamp,
            lastUpdatedMs: timestampMs,
            lastUpdatedLabel: timestamp ? formatDate(timestamp) : 'Not yet run',
            role: meta.role,
            pipeline: meta.pipeline,
            description: meta.description,
            qualityBenchmark: meta.qualityBenchmark,
            icon: meta.icon,
            filterBreakdown,
            topFilter
        };
    });

    return {
        totalRecords,
        totalSources: items.length,
        items
    };
}

function sortSourceRows(rows) {
    const { key, direction } = sourceTableSort;
    const sorted = [...rows];
    sorted.sort((a, b) => {
        const dir = direction === 'asc' ? 1 : -1;
        let valA = a[key];
        let valB = b[key];

        if (key === 'name' || key === 'role') {
            valA = (valA || '').toString().toLowerCase();
            valB = (valB || '').toString().toLowerCase();
            if (valA < valB) return -1 * dir;
            if (valA > valB) return 1 * dir;
            return 0;
        }

        if (key === 'lastUpdated') {
            const msA = a.lastUpdatedMs || 0;
            const msB = b.lastUpdatedMs || 0;
            return (msA - msB) * dir;
        }

        return ((valA || 0) - (valB || 0)) * dir;
    });
    return sorted;
}

function updateSortIndicators() {
    const headers = document.querySelectorAll('.comparison-table th[data-sort-key]');
    headers.forEach(header => {
        header.classList.remove('active', 'desc');
        if (header.dataset.sortKey === sourceTableSort.key) {
            header.classList.add('active');
            if (sourceTableSort.direction === 'desc') {
                header.classList.add('desc');
            }
        }
    });
}

function renderSourceTableBody(tbody) {
    if (!tbody) return;
    const rows = sortSourceRows(sourceTableRows);
    const html = rows.map(row => {
        const records = row.records.toLocaleString();
        const share = row.share.toFixed(1) + '%';
        const quality = (row.quality * 100).toFixed(1) + '%';
        const avgLength = row.avgLength ? Math.round(row.avgLength).toLocaleString() + ' chars' : '—';
        return `
            <tr>
                <td style="font-weight:600">${row.name}</td>
                <td>${records}</td>
                <td>${share}</td>
                <td>${quality}</td>
                <td>${avgLength}</td>
                <td>${row.lastUpdatedLabel}</td>
                <td>${row.role}</td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = html || `
        <tr>
            <td colspan="7" style="text-align:center;padding:2rem;color:var(--gray-500);">
                No data available yet. Run the data ingestion pipeline to populate metrics.
            </td>
        </tr>
    `;
    updateSortIndicators();
}

function handleSourceTableSort(sortKey) {
    if (!sortKey) return;
    if (sourceTableSort.key === sortKey) {
        sourceTableSort.direction = sourceTableSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sourceTableSort.key = sortKey;
        sourceTableSort.direction = sortKey === 'name' || sortKey === 'role' ? 'asc' : 'desc';
    }
    const tbody = document.getElementById('sourceTableBody');
    renderSourceTableBody(tbody);
}

/**
 * Populate the source comparison table
 */
export function populateSourceTable() {
    const tbody = document.getElementById('sourceTableBody');
    if (!tbody) return;

    const analytics = buildSourceAnalytics();
    if (!analytics) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 2rem; color: var(--gray-500);">
                    No data available yet. Run the data ingestion pipeline to populate metrics.
                </td>
            </tr>
        `;
        return;
    }

    sourceTableRows = analytics.items;
    renderSourceTableBody(tbody);

    if (!sourceTableListenersAttached) {
        const headers = document.querySelectorAll('.comparison-table th[data-sort-key]');
        headers.forEach(header => {
            header.addEventListener('click', () => handleSourceTableSort(header.dataset.sortKey));
        });
        sourceTableListenersAttached = true;
    }
}

export function populateSourceMixSnapshot() {
    const narrativeEl = document.getElementById('source-mix-narrative');
    const shareValueEl = document.getElementById('mix-share-leader-value');
    const shareCaptionEl = document.getElementById('mix-share-leader-caption');
    const qualityValueEl = document.getElementById('mix-quality-standout-value');
    const qualityCaptionEl = document.getElementById('mix-quality-standout-caption');
    const freshnessValueEl = document.getElementById('mix-freshness-value');
    const freshnessCaptionEl = document.getElementById('mix-freshness-caption');

    const analytics = buildSourceAnalytics();

    if (!analytics || !analytics.items.length) {
        if (narrativeEl) narrativeEl.textContent = 'Run the ingestion pipelines to populate source mix insights.';
        [shareValueEl, qualityValueEl, freshnessValueEl].forEach(el => { if (el) el.textContent = '—'; });
        [shareCaptionEl, qualityCaptionEl, freshnessCaptionEl].forEach(el => { if (el) el.textContent = 'Awaiting data.'; });
        return;
    }

    const items = analytics.items;
    const totalRecords = analytics.totalRecords;
    const leader = items.reduce((prev, curr) => curr.share > prev.share ? curr : prev, items[0]);
    const qualityChamp = items.reduce((prev, curr) => curr.quality > prev.quality ? curr : prev, items[0]);
    const freshest = items.reduce((prev, curr) => {
        if (!prev.lastUpdatedMs) return curr;
        if (!curr.lastUpdatedMs) return prev;
        return curr.lastUpdatedMs > prev.lastUpdatedMs ? curr : prev;
    }, items[0]);

    const leaderShareLabel = leader.share.toFixed(1) + '%';
    const qualityPercentLabel = (qualityChamp.quality * 100).toFixed(1) + '%';

    if (narrativeEl) {
        narrativeEl.textContent = `Current corpus mix spans ${totalRecords.toLocaleString()} records across ${items.length} active sources. ` +
            `${leader.name} carries ${leaderShareLabel} of delivered volume while ${qualityChamp.name} leads quality at ${qualityPercentLabel}. ` +
            `Latest ingestion finished with ${freshest.name} on ${freshest.lastUpdatedLabel}.`;
    }

    if (shareValueEl) shareValueEl.textContent = leader.name;
    if (shareCaptionEl) shareCaptionEl.textContent = `${leaderShareLabel} of volume`;

    if (qualityValueEl) qualityValueEl.textContent = `${qualityChamp.name}`;
    if (qualityCaptionEl) qualityCaptionEl.textContent = `${qualityPercentLabel} pass rate`;

    if (freshnessValueEl) freshnessValueEl.textContent = freshest.lastUpdatedLabel;
    if (freshnessCaptionEl) freshnessCaptionEl.textContent = `${freshest.name} · ${freshest.pipeline}`;
}

export function populateSourceBriefings() {
    const container = document.getElementById('sourceBriefings');
    if (!container) return;

    const analytics = buildSourceAnalytics();
    if (!analytics || !analytics.items.length) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--gray-500);">
                No source briefings available yet.
            </div>
        `;
        return;
    }

    const cards = analytics.items
        .sort((a, b) => b.records - a.records)
        .map(item => renderSourceBriefingCard(item))
        .join('');

    container.innerHTML = cards;
}

function renderSourceBriefingCard(item) {
    const shareLabel = item.share.toFixed(1);
    const qualityPercent = (item.quality * 100).toFixed(1);
    const avgLength = item.avgLength ? Math.round(item.avgLength).toLocaleString() : '—';
    const qualityClass = item.quality >= item.qualityBenchmark ? 'success' : 'warning';

    let narrative = `${item.name} contributes ${shareLabel}% of recent records with a ${qualityPercent}% pass rate.`;
    if (item.topFilter) {
        narrative += ` Most filtering comes from the ${item.topFilter.label} (${item.topFilter.percentage.toFixed(1)}%).`;
    }
    if (item.quality < item.qualityBenchmark) {
        narrative += ' Quality is below the expected baseline—monitor upcoming runs.';
    }

    const iconMarkup = item.icon || '';

    return `
        <article class="source-briefing-card">
            <div class="source-briefing-header">
                <div class="source-briefing-icon">${iconMarkup}</div>
                <div>
                    <div class="source-briefing-title">${item.name}</div>
                    <div class="source-briefing-role">${item.role} · ${item.pipeline}</div>
                </div>
            </div>
            <div class="briefing-chip-row">
                <span class="briefing-chip">${shareLabel}% Share</span>
                <span class="briefing-chip ${qualityClass}">Quality ${qualityPercent}%</span>
                <span class="briefing-chip neutral">Avg ${avgLength} chars</span>
                <span class="briefing-chip neutral">${item.lastUpdatedLabel}</span>
            </div>
            ${item.description ? `<p class="source-briefing-text">${item.description}</p>` : ''}
            <p class="source-briefing-text">${narrative}</p>
        </article>
    `;
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

    // Update Wikipedia card
    const wikipediaCard = document.querySelector('#quality-panel .source-grid .source-card:nth-child(1)');
    if (wikipediaCard && sourceQualityMap['Wikipedia']) {
        updateQualityCard(wikipediaCard, sourceQualityMap['Wikipedia']);
    }

    // Update BBC card
    const bbcCard = document.querySelector('#quality-panel .source-grid .source-card:nth-child(2)');
    if (bbcCard && sourceQualityMap['BBC']) {
        updateQualityCard(bbcCard, sourceQualityMap['BBC']);
    }

    // Update HuggingFace card
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

    // Update Wikipedia card
    const wikipediaCard = document.querySelector('#pipeline-panel .source-grid .source-card:nth-child(1)');
    if (wikipediaCard && sourcePerfMap['Wikipedia']) {
        updatePerformanceCard(wikipediaCard, sourcePerfMap['Wikipedia']);
    }

    // Update BBC card
    const bbcCard = document.querySelector('#pipeline-panel .source-grid .source-card:nth-child(2)');
    if (bbcCard && sourcePerfMap['BBC']) {
        updatePerformanceCard(bbcCard, sourcePerfMap['BBC']);
    }

    // Update HuggingFace card
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

    // Update Wikipedia card
    const wikipediaCard = document.querySelector('#overview-panel .source-card.wikipedia');
    if (wikipediaCard && sourceDataMap['Wikipedia']) {
        updateOverviewCard(wikipediaCard, sourceDataMap['Wikipedia'], totalRecords);
    }

    // Update BBC card
    const bbcCard = document.querySelector('#overview-panel .source-card.bbc');
    if (bbcCard && sourceDataMap['BBC']) {
        updateOverviewCard(bbcCard, sourceDataMap['BBC'], totalRecords);
    }

    // Update HuggingFace card
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
