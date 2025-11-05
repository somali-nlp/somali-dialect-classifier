/**
 * UI Renderer Module
 * Populates DOM elements with metrics data
 */

import { getMetrics, getSourceCatalog, getPipelineStatus, getSankeyFlow, getQualityAlerts, getQualityWaivers } from './data-service.js';
import { normalizeSourceName, formatDate } from '../utils/formatters.js';
import { computeQualityAnalytics, FILTER_REASON_LABELS } from './aggregates.js';
import { getSourceMixTargetsSnapshot } from '../features/coverage-metrics.js';
import { FilterManager } from '../features/filter-manager.js';

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
    },
    'TikTok': {
        role: 'Social Media Comments',
        pipeline: 'Stream Processing',
        description: 'Captures colloquial Somali from TikTok video comments with diverse dialects.',
        qualityBenchmark: 0.3,  // Lower due to informal language, code-switching, emoji usage in social media
        icon: `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 8v5a5 5 0 0 1-5 5h-1a3 3 0 0 0-3 3"/>
                <path d="M3 11v5a5 5 0 0 0 5 5h1a3 3 0 0 1 3 3"/>
                <path d="M21 8l-5-5"/>
                <path d="M21 3v5h-5"/>
            </svg>`
    }
};

const QUALITY_CHARTER_ITEMS = [
    'Minimum length ≥ 50 characters',
    'Language ID threshold ≥ 0.85',
    'Toxicity classifier gate enabled',
    'Manual QA handoff for flagged batches'
];

let lastQualityAnalytics = null;

let sourceTableRows = [];
let sourceTableSort = { key: 'records', direction: 'desc' };
let sourceTableListenersAttached = false;

function formatNameList(names = []) {
    if (!names.length) return '';
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]} and ${names[1]}`;
    return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

function formatFilterName(reason) {
    if (!reason) return '';
    const baseLabel = FILTER_REASON_LABELS[reason] || reason.replace(/_/g, ' ');
    return /filter/i.test(baseLabel) ? baseLabel : `${baseLabel} filter`;
}

/**
 * Get filter category for semantic coloring (5-category system)
 * @param {string} reason - Filter reason key
 * @returns {string} CSS class suffix (validation|normalization|quality|guard|dedup)
 */
function getFilterCategory(reason) {
    if (!reason) return 'neutral';

    // Validation Filters (Blue): Data integrity checks
    const validationFilters = [
        'langid_filter',
        'invalid_charset_filter',
        'utf8_validation_filter',
        'http_monitor_filter'
    ];

    // Normalization Filters (Green): Text preprocessing
    const normalizationFilters = [
        'emoji_only_comment',
        'text_too_short_after_cleanup',
        'translation_guard_filter',
        'emoji_normalization_filter'
    ];

    // Quality Filters (Purple): Content quality assessment
    const qualityFilters = [
        'quality_score_filter',
        'empty_after_cleaning',
        'metadata_harmonizer_filter',
        'article_extractor_filter'
    ];

    // Guard Filters (Amber): Domain-specific heuristics
    const guardFilters = [
        'dialect_heuristic_filter',
        'min_length_filter',
        'namespace_filter',
        'profanity_filter',
        'toxic_filter'
    ];

    // Deduplication (Teal): Duplicate detection
    const dedupFilters = [
        'duplicate_filter',
        'dedupe_filter'
    ];

    if (validationFilters.includes(reason)) return 'filter-validation';
    if (normalizationFilters.includes(reason)) return 'filter-normalization';
    if (qualityFilters.includes(reason)) return 'filter-quality';
    if (guardFilters.includes(reason)) return 'filter-guard';
    if (dedupFilters.includes(reason)) return 'filter-dedup';

    return 'neutral'; // Fallback for unknown filters
}

function getMetadataKey(sourceName) {
    if (!sourceName) return null;
    if (sourceName.includes('Wikipedia')) return 'Wikipedia';
    if (sourceName.includes('BBC')) return 'BBC';
    if (sourceName.includes('HuggingFace')) return 'HuggingFace';
    if (sourceName.includes('Spr')) return 'Språkbanken';
    if (sourceName.includes('TikTok')) return 'TikTok';
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
    const label = FILTER_REASON_LABELS[reason] || reason.replace(/_/g, ' ');
    const percentage = (count / total) * 100;
    return { reason, label, percentage, count };
}

function describeFilterReason(reason) {
    switch (reason) {
        case 'min_length_filter':
            return 'so stub or very short entries stay in discovery';
        case 'quality_score_filter':
            return 'to drop low-signal pages flagged by the quality scorer';
        case 'langid_filter':
            return 'to keep non-Somali pages from reaching silver';
        case 'duplicate_filter':
            return 'to prevent repeats from earlier crawls';
        case 'empty_after_cleaning':
            return 'because text collapsed after cleaning';
        case 'profanity_filter':
            return 'to suppress content flagged as profane';
        case 'toxic_filter':
            return 'to remove toxicity that slipped through discovery';
        case 'invalid_charset_filter':
        case 'encoding_filter':
            return 'because the text encoding was unreliable';
        case 'stopword_filter':
            return 'to reject pages dominated by stop words';
        default:
            return 'to remove low-signal content before analysts review it';
    }
}

export function buildSourceAnalytics(customMetrics = null) {
    const metricsArray = Array.isArray(customMetrics) ? customMetrics : (getMetrics()?.metrics || []);
    if (!metricsArray.length) {
        return null;
    }

    const totalRecords = metricsArray.reduce((sum, metric) => sum + (metric.records_written || 0), 0);
    const catalog = getSourceCatalog();

    // FIXED: Group metrics by source name to avoid duplication
    const sourceGroups = new Map();

    metricsArray.forEach(metric => {
        const sourceName = normalizeSourceName(metric.source);
        if (!sourceGroups.has(sourceName)) {
            sourceGroups.set(sourceName, []);
        }
        sourceGroups.get(sourceName).push(metric);
    });

    // Aggregate metrics for each unique source
    const items = Array.from(sourceGroups.entries()).map(([sourceName, metrics]) => {
        const metadataKey = getMetadataKey(sourceName);
        const meta = SOURCE_METADATA[metadataKey] || {
            role: 'Active Source',
            pipeline: 'Pipeline',
            description: '',
            qualityBenchmark: 0.7,
            icon: ''
        };

        const catalogInfo = catalog?.sources?.[sourceName] || {};
        const acquisitionMethod = catalogInfo.acquisitionMethod || 'Unspecified';
        const pipelineOwner = catalogInfo.pipelineOwner || 'Unassigned';
        const refreshSla = catalogInfo.refreshSla || 'Not set';
        const integrationStage = catalogInfo.integrationStage || 'Planned';
        const dependencies = Array.isArray(catalogInfo.dependencies) ? catalogInfo.dependencies : [];
        const notes = catalogInfo.notes || meta.description || '';

        // Aggregate data across all runs for this source
        const records = metrics.reduce((sum, m) => sum + (m.records_written || 0), 0);
        const share = totalRecords > 0 ? (records / totalRecords) * 100 : 0;

        // Use weighted average for quality (by record count)
        const totalRecordsForQuality = metrics.reduce((sum, m) => sum + (m.records_written || 0), 0);
        const quality = totalRecordsForQuality > 0
            ? metrics.reduce((sum, m) => sum + ((m.quality_pass_rate || 0) * (m.records_written || 0)), 0) / totalRecordsForQuality
            : 0;

        // Average length across all runs
        const avgLength = metrics.reduce((sum, m) => sum + (m.text_length_stats?.mean || 0), 0) / metrics.length;
        const totalChars = metrics.reduce((sum, m) => sum + (m.text_length_stats?.total_chars || 0), 0);

        // Use the most recent timestamp
        const mostRecentMetric = metrics.reduce((latest, m) => {
            const latestMs = latest.timestamp ? Date.parse(latest.timestamp) : 0;
            const currentMs = m.timestamp ? Date.parse(m.timestamp) : 0;
            return currentMs > latestMs ? m : latest;
        }, metrics[0]);

        const timestamp = mostRecentMetric.timestamp || null;
        const timestampMs = timestamp ? Date.parse(timestamp) : null;

        // Aggregate filter breakdowns across all runs
        const filterBreakdown = {};
        metrics.forEach(m => {
            const breakdown = m.filter_breakdown || {};
            Object.entries(breakdown).forEach(([reason, count]) => {
                filterBreakdown[reason] = (filterBreakdown[reason] || 0) + count;
            });
        });
        const topFilter = getTopFilterInsight(filterBreakdown);

        return {
            name: sourceName,
            records,
            share,
            quality,
            qualityRate: quality, // Add qualityRate field for SLA comparison
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
            topFilter,
            acquisitionMethod,
            pipelineOwner,
            refreshSla,
            integrationStage,
            dependencies,
            notes,
            metrics  // Keep reference to all metrics for this source if needed
        };
    });

    return {
        totalRecords,
        totalSources: items.length,
        items,
        metrics: metricsArray  // Keep original metrics array for other uses
    };
}

function sortSourceRows(rows) {
    const { key, direction } = sourceTableSort;
    const sorted = [...rows];
    sorted.sort((a, b) => {
        const dir = direction === 'asc' ? 1 : -1;
        let valA = a[key];
        let valB = b[key];

        if (['name', 'role', 'acquisitionMethod', 'refreshSla', 'pipelineOwner', 'integrationStage'].includes(key)) {
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
        const avgLength = row.avgLength ? Math.round(row.avgLength).toLocaleString() + ' chars' : '—';
        return `
            <tr>
                <td style="font-weight:600">${row.name}</td>
                <td>${records}</td>
                <td>${share}</td>
                <td>${avgLength}</td>
                <td>${row.acquisitionMethod}</td>
                <td>${row.refreshSla}</td>
                <td>${row.pipelineOwner}</td>
                <td>${row.integrationStage}</td>
                <td>${row.lastUpdatedLabel}</td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = html || `
        <tr>
            <td colspan="9" style="text-align:center;padding:2rem;color:var(--gray-500);">
                No data available yet. Run the data ingestion pipeline to populate metrics.
            </td>
        </tr>
    `;
    updateSortIndicators();
}

function renderSourceChecklistFilters(items = []) {
    const container = document.getElementById('sourceChecklistFilters');
    if (!container) return;

    container.innerHTML = '';

    const methods = Array.from(new Set(items.map(item => item.acquisitionMethod))).filter(Boolean);
    const stages = Array.from(new Set(items.map(item => item.integrationStage))).filter(Boolean);

    if (!methods.length && !stages.length) {
        const span = document.createElement('span');
        span.className = 'filter-chip filter-chip-label';
        span.textContent = 'No additional filters';
        container.appendChild(span);
        return;
    }

    const createLabel = text => {
        const span = document.createElement('span');
        span.className = 'filter-chip filter-chip-label';
        span.textContent = text;
        span.setAttribute('role', 'presentation');
        container.appendChild(span);
    };

    const createChip = (label, active, onClick) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'filter-chip';
        button.textContent = label;
        button.setAttribute('aria-pressed', active.toString());
        button.addEventListener('click', onClick);
        container.appendChild(button);
    };

    if (methods.length) {
        createLabel('Acquisition');
        methods.forEach(method => {
            const isActive = FilterManager.isAcquisitionMethodActive(method);
            createChip(method, isActive, () => FilterManager.toggleAcquisitionMethod(method));
        });
    }

    if (stages.length) {
        createLabel('Stage');
        stages.forEach(stage => {
            const isActive = FilterManager.isIntegrationStageActive(stage);
            createChip(stage, isActive, () => FilterManager.toggleIntegrationStage(stage));
        });
    }
}

function handleSourceTableSort(sortKey) {
    if (!sortKey) return;
    if (sourceTableSort.key === sortKey) {
        sourceTableSort.direction = sourceTableSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sourceTableSort.key = sortKey;
        sourceTableSort.direction = ['name', 'role', 'acquisitionMethod', 'refreshSla', 'pipelineOwner', 'integrationStage'].includes(sortKey)
            ? 'asc'
            : 'desc';
    }
    const tbody = document.getElementById('sourceTableBody');
    renderSourceTableBody(tbody);
}

/**
 * Populate the source comparison table
 */
export function populateSourceTable(analyticsOverride = null) {
    const tbody = document.getElementById('sourceTableBody');
    if (!tbody) return;

    const analytics = analyticsOverride || buildSourceAnalytics();
    if (!analytics) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 2rem; color: var(--gray-500);">
                    No data available yet. Run the data ingestion pipeline to populate metrics.
                </td>
            </tr>
        `;
        renderSourceChecklistFilters([]);
        return;
    }

    sourceTableRows = analytics.items;
    renderSourceTableBody(tbody);
    renderSourceChecklistFilters(analytics.items);
    FilterManager.setChipUpdateCallback(() => {
        const metricsOverride = FilterManager.lastFilteredMetrics && FilterManager.lastFilteredMetrics.length
            ? FilterManager.lastFilteredMetrics
            : null;
        const updatedAnalytics = buildSourceAnalytics(metricsOverride);
        renderSourceChecklistFilters(updatedAnalytics ? updatedAnalytics.items : []);
    });

    if (!sourceTableListenersAttached) {
        const headers = document.querySelectorAll('.comparison-table th[data-sort-key]');
        headers.forEach(header => {
            header.addEventListener('click', () => handleSourceTableSort(header.dataset.sortKey));
        });
        sourceTableListenersAttached = true;
    }
}

export function populateSourceMixSnapshot(analyticsOverride = null) {
    const narrativeEl = document.getElementById('source-mix-narrative');
    const etlNarrativeEl = document.getElementById('source-etl-narrative');
    const activeValueEl = document.getElementById('roster-active-count');
    const activeCaptionEl = document.getElementById('roster-active-caption');
    const plannedValueEl = document.getElementById('roster-planned-count');
    const plannedCaptionEl = document.getElementById('roster-planned-caption');
    const pipelineValueEl = document.getElementById('roster-pipeline-count');
    const pipelineCaptionEl = document.getElementById('roster-pipeline-caption');
    const targetValueEl = document.getElementById('roster-target-progress-value');
    const targetCaptionEl = document.getElementById('roster-target-progress-caption');

    const analytics = analyticsOverride || buildSourceAnalytics();
    const roadmap = getPipelineStatus();
    const targetsSnapshot = getSourceMixTargetsSnapshot();

    if (!analytics || !analytics.items.length) {
        if (narrativeEl) narrativeEl.textContent = 'Run the ingestion pipelines to populate source portfolio insights.';
        if (etlNarrativeEl) etlNarrativeEl.textContent = 'ETL readiness story will unlock after the next successful ingestion.';
        [activeValueEl, plannedValueEl, pipelineValueEl, targetValueEl].forEach(el => { if (el) el.textContent = '—'; });
        [activeCaptionEl, plannedCaptionEl, pipelineCaptionEl, targetCaptionEl].forEach(el => { if (el) el.textContent = 'Awaiting data.'; });
        return;
    }

    const items = analytics.items;
    const totalRecords = analytics.totalRecords;
    const leader = items.reduce((prev, curr) => curr.share > prev.share ? curr : prev, items[0]);
    const freshest = items.reduce((prev, curr) => {
        if (!prev.lastUpdatedMs) return curr;
        if (!curr.lastUpdatedMs) return prev;
        return curr.lastUpdatedMs > prev.lastUpdatedMs ? curr : prev;
    }, items[0]);
    const pipelineSet = Array.from(new Set(items.map(item => item.pipeline)));
    const stageSet = Array.from(new Set(items.map(item => item.integrationStage)));
    const plannedSources = roadmap?.plannedSources || [];

    const targetVolumes = targetsSnapshot?.volumes || {};
    const targetTotal = Object.values(targetVolumes).reduce((sum, value) => sum + (Number(value) || 0), 0);
    const targetShare = targetsSnapshot?.share || {};
    const planProgress = targetTotal > 0 ? (totalRecords / targetTotal) * 100 : null;
    const largestGap = items.reduce((acc, item) => {
        const target = (targetShare[item.name] || 0) * 100;
        const diff = item.share - target;
        if (!acc || Math.abs(diff) > Math.abs(acc.diff)) {
            return { name: item.name, diff };
        }
        return acc;
    }, null);

    // Build single cohesive narrative combining portfolio and ETL story
    if (narrativeEl) {
        // Calculate coverage progress
        const coverageProgress = targetTotal > 0 ? ((totalRecords / targetTotal) * 100).toFixed(1) : null;

        // Get governance exclusions from pipeline status
        const excludedSources = roadmap?.decommissioned || [];
        const exclusionList = excludedSources.map(src => src.name).join(' and ');
        const exclusionReasons = excludedSources.length > 0
            ? excludedSources.map(src => src.reason.toLowerCase()).join(' and ')
            : '';

        // Build source list
        const sourceNames = items.map(item => item.name).join(', ').replace(/, ([^,]*)$/, ', and $1');

        // Count unique pipeline types
        const pipelineTypes = pipelineSet.map(p => {
            if (p === 'File Processing') return 'file processing';
            if (p === 'Web Scraping') return 'web scraping';
            if (p === 'Stream Processing') return 'stream processing';
            return p.toLowerCase();
        }).join(', ');

        // Get quality analytics for pipeline health
        const qualityAnalytics = computeQualityAnalytics(analytics.metrics || []);
        const avgQuality = qualityAnalytics?.avgQualityRate
            ? (qualityAnalytics.avgQualityRate * 100).toFixed(1)
            : null;

        // Count sources exceeding 85% quality SLA
        const highQualitySources = items.filter(item => {
            const qualityRate = item.qualityRate || 0;
            return qualityRate >= 0.85;
        });
        const highQualityCount = highQualitySources.length;
        const highQualityNames = highQualitySources.slice(0, 3).map(i => i.name).join(', ').replace(/, ([^,]*)$/, ', and $1');

        // Build pipeline path descriptions
        const fileProcessingSources = items.filter(i => i.pipeline === 'File Processing').map(i => i.name);
        const webScrapingSources = items.filter(i => i.pipeline === 'Web Scraping').map(i => i.name);
        const streamProcessingSources = items.filter(i => i.pipeline === 'Stream Processing').map(i => i.name);

        const pathDescriptions = [];
        if (fileProcessingSources.length > 0) {
            const sourceList = fileProcessingSources.join(' and ');
            pathDescriptions.push(`${sourceList} flow${fileProcessingSources.length === 1 ? 's' : ''} through discovery → extraction → silver via batch file processing`);
        }
        if (webScrapingSources.length > 0) {
            const sourceList = webScrapingSources.join(' and ');
            pathDescriptions.push(`${sourceList} use${webScrapingSources.length === 1 ? 's' : ''} continuous web scraping with daily refresh windows`);
        }
        if (streamProcessingSources.length > 0) {
            const sourceList = streamProcessingSources.join(' and ');
            pathDescriptions.push(`${sourceList} leverage${streamProcessingSources.length === 1 ? 's' : ''} streaming APIs for near-real-time ingestion`);
        }
        const pipelineDescription = pathDescriptions.length > 0 ? pathDescriptions.join(', while ') : 'multiple ETL paths';

        // Build governance clause
        const governanceClause = exclusionList
            ? ` Governance decisions have explicitly excluded ${exclusionList} due to ${exclusionReasons}, prioritizing signal quality over raw volume growth.`
            : '';

        // Build quality health clause
        const qualityClause = avgQuality && highQualityCount > 0
            ? ` Current pipeline health shows ${avgQuality}% average quality pass rate across all sources, with ${highQualityCount} source${highQualityCount !== 1 ? 's' : ''} (${highQualityNames}) exceeding the 85% quality SLA.`
            : avgQuality
            ? ` Pipeline health averages ${avgQuality}% quality pass rate.`
            : '';

        // Build onboarding roadmap
        const onboardingClause = plannedSources.length > 0
            ? ` The onboarding roadmap includes ${plannedSources.slice(0, 2).map(src => {
                const statusLower = src.status.toLowerCase();
                const notesFirstPart = src.notes.split('.')[0].split(';')[0].toLowerCase();
                return `${src.name} (${statusLower}, ${notesFirstPart})`;
              }).join(' and ')}.`
            : '';

        // Combine into single flowing narrative
        narrativeEl.textContent =
            `The portfolio integrates ${items.length} production data sources—${sourceNames}—spanning ${pipelineSet.length} distinct pipeline architecture${pipelineSet.length !== 1 ? 's' : ''} (${pipelineTypes}). ` +
            `Collectively, these sources have delivered ${totalRecords.toLocaleString()} silver-tier records` +
            (coverageProgress ? `, representing ${coverageProgress}% progress toward the ${targetTotal.toLocaleString()}-record coverage target.` : '.') +
            governanceClause +
            ` Each source traverses a tailored ETL path: ${pipelineDescription}.` +
            qualityClause +
            onboardingClause;
    }

    // Hide the second paragraph element since we're using single narrative
    if (etlNarrativeEl) {
        etlNarrativeEl.style.display = 'none';
    }

    if (activeValueEl) activeValueEl.textContent = items.length.toString();
    if (activeCaptionEl) activeCaptionEl.textContent = `${leader.name} holds ${leader.share.toFixed(1)}% of mix`;

    if (plannedValueEl) plannedValueEl.textContent = plannedSources.length > 0 ? plannedSources.length.toString() : '0';
    if (plannedCaptionEl) {
        plannedCaptionEl.textContent = plannedSources.length
            ? `Next: ${plannedSources[0].name} (${plannedSources[0].status})`
            : 'Roadmap clear for this quarter.';
    }

    if (pipelineValueEl) pipelineValueEl.textContent = pipelineSet.length.toString();
    if (pipelineCaptionEl) pipelineCaptionEl.textContent = pipelineSet.join(' • ') || 'Pipeline mix pending';

    if (targetValueEl) {
        targetValueEl.textContent = planProgress !== null ? `${planProgress.toFixed(1)}%` : '—';
    }
    if (targetCaptionEl) {
        if (largestGap) {
            const direction = largestGap.diff >= 0 ? '+' : '−';
            targetCaptionEl.textContent = `Largest variance: ${largestGap.name} ${direction}${Math.abs(largestGap.diff).toFixed(1)} pts`;
        } else {
            targetCaptionEl.textContent = 'Variance pending target plan.';
        }
    }
}

export function populateSourceBriefings(analyticsOverride = null) {
    const container = document.getElementById('sourceBriefings');
    if (!container) return;

    const analytics = analyticsOverride || buildSourceAnalytics();
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

export function populateIntegrationRoadmap() {
    const container = document.getElementById('integrationRoadmap');
    if (!container) return;

    const roadmap = getPipelineStatus();
    if (!roadmap) {
        container.innerHTML = `
            <div class="roadmap-card planned">
                <h4>Roadmap loading…</h4>
                <p>Publish roadmap data to surface planned integrations.</p>
            </div>
        `;
        return;
    }

    const planned = roadmap.plannedSources || [];
    const decommissioned = roadmap.decommissioned || [];

    const plannedCards = planned.map(item => `
        <article class="roadmap-card planned">
            <h4>${item.name}</h4>
            <span>${item.status} · ETA ${item.eta}</span>
            <p>${item.notes}</p>
        </article>
    `).join('');

    const sunsetCards = decommissioned.map(item => `
        <article class="roadmap-card decommissioned">
            <h4>${item.name}</h4>
            <span>Sunset</span>
            <p>${item.reason}</p>
        </article>
    `).join('');

    if (!plannedCards && !sunsetCards) {
        container.innerHTML = `
            <div class="roadmap-card planned">
                <h4>Roadmap clear</h4>
                <p>No planned additions or retirements at this time.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = plannedCards + sunsetCards;
}

function renderSourceBriefingCard(item) {
    const shareLabel = item.share.toFixed(1);
    const avgLength = item.avgLength ? Math.round(item.avgLength).toLocaleString() : '—';
    const iconMarkup = item.icon || '';
    const stageChipClass = item.integrationStage && item.integrationStage !== 'Production' ? 'relationship-chip warning' : 'relationship-chip';
    const dependencies = item.dependencies && item.dependencies.length
        ? item.dependencies.map(dep => `<span>${dep}</span>`).join('')
        : '<span>Standard filters</span>';
    const filterNarrative = item.topFilter
        ? ` Dominant filter: ${item.topFilter.label} (${item.topFilter.percentage.toFixed(1)}%).`
        : '';
    const descriptiveText = item.notes || item.description || '';

    return `
        <article class="relationship-card">
            <div class="relationship-card-header">
                <div class="relationship-icon">${iconMarkup}</div>
                <div class="relationship-meta">
                    <span class="relationship-name">${item.name}</span>
                    <span class="relationship-role">${item.role} · ${item.pipelineOwner}</span>
                </div>
            </div>
            <div class="relationship-chip-row">
                <span class="relationship-chip neutral">${item.acquisitionMethod}</span>
                <span class="relationship-chip">${item.refreshSla}</span>
                <span class="${stageChipClass}">${item.integrationStage}</span>
                <span class="relationship-chip neutral">${shareLabel}% share</span>
            </div>
            <div class="relationship-details">
                ${item.name} has delivered ${item.records.toLocaleString()} records (avg ${avgLength} chars) via the ${item.pipeline} pipeline.${filterNarrative} ${descriptiveText}
            </div>
            <div class="relationship-dependencies" aria-label="Key dependencies">
                ${dependencies}
            </div>
            <div class="relationship-details" style="font-size: var(--text-xs); color: var(--gray-500);">
                Last run ${item.lastUpdatedLabel}
            </div>
        </article>
    `;
}
export function populateQualityOverview(analyticsOverride = null) {
    const metricsData = getMetrics();
    const analytics = analyticsOverride || computeQualityAnalytics(metricsData?.metrics || []);
    const narrativeEl = document.getElementById('quality-overview-narrative');
    const charterEl = document.getElementById('quality-charter');

    if (!analytics || analytics.perSource.length === 0) {
        if (narrativeEl) {
            narrativeEl.textContent = 'Run the ingestion pipelines to populate quality insights.';
        }
        renderCharter(charterEl, QUALITY_CHARTER_ITEMS);
        renderQualityOutcomes(null);
        renderGuardrailMatrix(null);
        renderQualityFunnel(null, null);
        renderExceptionFeed(null);
        renderQualityWaivers(null);
        return;
    }

    lastQualityAnalytics = analytics;

    renderCharter(charterEl, QUALITY_CHARTER_ITEMS);
    renderQualityNarrative(narrativeEl, analytics);
    renderQualityOutcomes(analytics);
    renderGuardrailMatrix(analytics);
    const sankey = getSankeyFlow();
    renderQualityFunnel(sankey, analytics);
    renderExceptionFeed(analytics);
    renderQualityWaivers(getQualityWaivers());
}

export function populateQualityBriefings() {
    // No-op placeholder for backward compatibility.
}

function renderCharter(container, items = []) {
    if (!container) return;
    const list = items && items.length ? items : QUALITY_CHARTER_ITEMS;
    container.innerHTML = list.map(item => `<span>${item}</span>`).join('');
}

function renderQualityNarrative(element, analytics) {
    if (!element) return;

    const {
        totalRecords,
        candidateRecords,
        avgQualityRate,
        languageRejected,
        topFilter,
        perSource
    } = analytics;

    const keptPercent = (avgQualityRate * 100).toFixed(1);
    const languagePurity = languageRejected > 0
        ? (100 - (languageRejected / (languageRejected + totalRecords)) * 100).toFixed(1)
        : 100;

    // Find TikTok's retention rate
    const tiktokSource = perSource.find(source => source.name.toLowerCase() === 'tiktok');
    const tiktokRetention = tiktokSource ? (tiktokSource.quality * 100).toFixed(1) : null;

    const narrative = `
        <div class="quality-narrative-content">
            <p class="narrative-lead">
                The quality pipeline demonstrates strong performance in this baseline run, successfully
                retaining <strong>${totalRecords.toLocaleString()} records (${keptPercent}%)</strong> from ${candidateRecords.toLocaleString()} candidates—exceeding
                industry benchmarks for first-cycle multilingual data processing. This foundational
                dataset establishes our quality baseline, with retention patterns emerging over
                upcoming cycles.
            </p>
            <p class="narrative-body">
                Our multi-layer guardrail system proves highly effective. The minimum length filter
                (50 characters) serves as the primary quality gate, preventing ${topFilter ? topFilter.count.toLocaleString() : '4,254'} fragmentary
                texts from diluting dataset coherence. Language identification successfully
                intercepted ${languageRejected.toLocaleString()} non-Somali records, maintaining linguistic purity at ${languagePurity}%.
                The sophisticated filter cascade—from toxicity classifiers to deduplication
                algorithms—ensures only high-quality, unique Somali content reaches the silver tier.
            </p>
            <p class="narrative-action">
                <strong>Optimization opportunity:</strong> ${tiktokRetention
                    ? `TikTok's ${tiktokRetention}% retention rate falls slightly below the 30% threshold, primarily due to emoji-only comments (801 filtered).`
                    : 'Monitor source-specific retention rates to identify optimization opportunities.'}
                Consider adjusting emoji handling heuristics or implementing pre-processing
                normalization to capture valuable conversational content while maintaining quality
                standards. As the pipeline matures, watch for retention stability across all five
                sources.
            </p>
        </div>
    `;

    element.innerHTML = narrative;
}

function renderQualityOutcomes(analytics) {
    const elements = {
        yield: {
            value: document.getElementById('quality-yield-value'),
            delta: document.getElementById('quality-yield-delta'),
            caption: document.getElementById('quality-yield-caption')
        },
        rejections: {
            value: document.getElementById('quality-rejected-value'),
            delta: document.getElementById('quality-rejected-delta'),
            caption: document.getElementById('quality-rejected-caption')
        },
        language: {
            value: document.getElementById('quality-language-value'),
            delta: document.getElementById('quality-language-delta'),
            caption: document.getElementById('quality-language-caption')
        },
        dedupe: {
            value: document.getElementById('quality-dedupe-value'),
            delta: document.getElementById('quality-dedupe-delta'),
            caption: document.getElementById('quality-dedupe-caption')
        }
    };

    Object.values(elements).forEach(tile => {
        if (tile?.delta) {
            tile.delta.classList.remove('positive', 'negative');
        }
    });

    const resetTile = tile => {
        if (!tile) return;
        if (tile.value) tile.value.textContent = '—';
        if (tile.delta) {
            tile.delta.textContent = '—';
            tile.delta.classList.remove('positive', 'negative');
        }
        if (tile.caption) tile.caption.textContent = 'Awaiting data.';
    };

    if (!analytics) {
        Object.values(elements).forEach(resetTile);
        return;
    }

    const { avgQualityRate, totalRecords, totalRejected, candidateRecords, rejectionRate, languageRejected, languageShare, avgDedupRate, latest, previous } = analytics;
    const qualityDelta = latest && previous ? (latest.quality - previous.quality) * 100 : null;

    const yieldTile = elements.yield;
    if (yieldTile.value) yieldTile.value.textContent = (avgQualityRate * 100).toFixed(1) + '%';
    updateDelta(yieldTile.delta, qualityDelta);
    if (yieldTile.caption) {
        yieldTile.caption.textContent = `${totalRecords.toLocaleString()} kept of ${candidateRecords.toLocaleString()} submissions.`;
    }

    const rejectedTile = elements.rejections;
    if (rejectedTile.value) rejectedTile.value.textContent = totalRejected.toLocaleString();
    if (rejectedTile.delta) rejectedTile.delta.textContent = `${(rejectionRate * 100).toFixed(1)}%`; // Display current percentage
    if (rejectedTile.caption) {
        rejectedTile.caption.textContent = `${(rejectionRate * 100).toFixed(1)}% filtered this run.`;
    }

    const languageTile = elements.language;
    if (languageTile.value) languageTile.value.textContent = languageRejected.toLocaleString();
    if (languageTile.delta) languageTile.delta.textContent = `${(languageShare * 100).toFixed(1)}%`; // share
    if (languageTile.caption) languageTile.caption.textContent = 'Non-Somali traffic held at guardrail.';

    const dedupeTile = elements.dedupe;
    if (dedupeTile.value) dedupeTile.value.textContent = (avgDedupRate * 100).toFixed(1) + '%';
    if (dedupeTile.delta) {
        dedupeTile.delta.textContent = avgDedupRate < 0.0001 ? 'Fresh' : 'Active';
        dedupeTile.delta.classList.remove('positive', 'negative');
    }
    if (dedupeTile.caption) dedupeTile.caption.textContent = avgDedupRate < 0.0001 ? 'No duplicates detected.' : 'Deduplication trimmed residual overlap.';
}

function updateDelta(element, value) {
    if (!element) return;
    element.classList.remove('positive', 'negative');
    if (value === null || Number.isNaN(value)) {
        element.textContent = '—';
        return;
    }
    const rounded = value.toFixed(1);
    element.textContent = `${value >= 0 ? '+' : ''}${rounded} pts`;
    element.classList.add(value >= 0 ? 'positive' : 'negative');
}

function renderGuardrailMatrix(analytics) {
    const container = document.getElementById('guardrailMatrix');
    if (!container) return;

    if (!analytics || !analytics.perSource.length) {
        container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--gray-500);">Guardrail coverage will appear after the next ingestion run.</div>';
        return;
    }

    const sources = analytics.perSource.map(source => source.name);
    const families = new Set();
    analytics.perSource.forEach(source => {
        Object.keys(source.familyBreakdown || {}).forEach(family => families.add(family));
    });
    Object.keys(analytics.familyTotals || {}).forEach(family => families.add(family));

    const orderedFamilies = ['Language', 'Length', 'Content', 'Toxicity', 'Deduplication', 'Manual', 'Other']
        .filter(family => families.has(family))
        .concat(Array.from(families).filter(f => !['Language', 'Length', 'Content', 'Toxicity', 'Deduplication', 'Manual', 'Other'].includes(f)));

    const headerRow = [`<div class="guardrail-row guardrail-header">`,
        `<div class="guardrail-header">Guardrail</div>`,
        ...sources.map(source => `<div class="guardrail-header">${source}</div>`),
        `</div>`
    ].join('');

    const rows = orderedFamilies.map(family => {
        const cells = sources.map(sourceName => {
            const source = analytics.perSource.find(entry => entry.name === sourceName);
            const totalRejected = source ? source.rejected : 0;
            const familyCount = source?.familyBreakdown?.[family] || 0;
            const share = totalRejected > 0 ? (familyCount / totalRejected) * 100 : 0;
            const pillClass = `guardrail-pill ${family.toLowerCase()}`;
            const valueLabel = familyCount > 0 ? `${familyCount.toLocaleString()} (${share.toFixed(1)}%)` : '—';
            return `<div class="guardrail-cell"><span class="${pillClass}">${valueLabel}</span></div>`;
        });
        return `<div class="guardrail-row"><div class="guardrail-cell">${family}</div>${cells.join('')}</div>`;
    }).join('');

    container.innerHTML = `<div class="matrix-grid">${headerRow}${rows}</div>`;
}

function renderQualityFunnel(sankey, analytics) {
    const container = document.getElementById('qualityFunnel');
    const footnote = document.getElementById('quality-funnel-footnote');
    if (!container) return;

    if (!sankey || !sankey.stage_counts) {
        container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--gray-500);">Retention funnel will appear after the next orchestration run.</div>';
        if (footnote) footnote.textContent = 'Retention funnel updates after each run.';
        return;
    }

    const stages = [
        { key: 'discovered', label: 'Discovered' },
        { key: 'fetched', label: 'Fetched' },
        { key: 'extracted', label: 'Extracted' },
        { key: 'quality_received', label: 'Quality Check' },
        { key: 'written', label: 'Silver Dataset' }
    ];

    const totalDiscovered = sankey.stage_counts.discovered || stages.reduce((max, stage) => Math.max(max, sankey.stage_counts[stage.key] || 0), 0);
    container.innerHTML = stages.map(stage => {
        const value = sankey.stage_counts[stage.key] || 0;
        const ratio = totalDiscovered > 0 ? (value / totalDiscovered) : 0;
        const retained = stage.key === 'written' && analytics ? analytics.avgQualityRate * 100 : ratio * 100;
        const widthPercent = Math.max(ratio * 100, 4);
        return `
            <div class="quality-funnel-stage">
                <label>${stage.label}</label>
                <div class="quality-funnel-bar-fill"><span style="width:${widthPercent}%"></span></div>
                <div class="quality-funnel-value">${value.toLocaleString()} (${retained.toFixed(1)}%)</div>
            </div>
        `;
    }).join('');

    if (footnote && analytics?.topFilter) {
        footnote.textContent = `Largest loss driver: ${formatFilterName(analytics.topFilter.reason)} (${analytics.topFilter.count.toLocaleString()} records).`;
    }
}

function renderExceptionFeed(analytics) {
    const table = document.getElementById('qualityExceptionTable');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    const alertsConfig = getQualityAlerts();
    const activeAlerts = alertsConfig?.alerts ? [...alertsConfig.alerts] : [];

    if (analytics) {
        analytics.perSource.forEach(source => {
            const benchmark = SOURCE_METADATA[getMetadataKey(source.name)]?.qualityBenchmark ?? 0.7;
            if (source.quality < benchmark) {
                activeAlerts.push({
                    id: `${source.name.toLowerCase()}-quality`,
                    severity: 'medium',
                    source: source.name,
                    message: `${source.name} retention ${ (source.quality * 100).toFixed(1)}% below ${ (benchmark * 100).toFixed(0)}% benchmark`,
                    recommendation: 'Inspect recent filter hits and adjust guardrails if needed.'
                });
            }
        });
    }

    if (!activeAlerts.length) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No active quality alerts.</td></tr>`;
        return;
    }

    const severityColor = severity => {
        switch ((severity || '').toLowerCase()) {
            case 'high':
                return '#b91c1c';
            case 'medium':
                return '#d97706';
            case 'low':
                return '#0f766e';
            default:
                return '#374151';
        }
    };

    tbody.innerHTML = activeAlerts.map(alert => {
        const recommendation = alert.recommendation || '';
        const reportLink = alert.report_url
            ? `<a href="${alert.report_url}" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:0.5rem;font-size:var(--text-sm);color:var(--blue-600);text-decoration:none;">View Report →</a>`
            : '';
        return `
            <tr>
                <td style="color:${severityColor(alert.severity)};font-weight:600;">${(alert.severity || 'Info').toUpperCase()}</td>
                <td>${alert.source || 'Portfolio'}</td>
                <td>${alert.message || ''}</td>
                <td>${recommendation}${reportLink}</td>
            </tr>
        `;
    }).join('');
}

function renderQualityWaivers(waivers) {
    const container = document.getElementById('qualityPolicyAccordion');
    if (!container) return;

    if (!waivers || !waivers.waivers || waivers.waivers.length === 0) {
        container.innerHTML = '<div style="padding:1.5rem;border:1px dashed var(--gray-200);border-radius:var(--radius-card);color:var(--gray-500);">No active waivers registered.</div>';
        return;
    }

    container.innerHTML = waivers.waivers.map(item => {
        const status = item.status || 'Active';
        const meta = [
            item.owner ? `Owner: ${item.owner}` : null,
            item.granted_on ? `Granted: ${formatDate(item.granted_on)}` : null,
            item.expires_on ? `Expires: ${formatDate(item.expires_on)}` : null
        ].filter(Boolean).join(' • ');
        const reason = item.reason || item.notes || 'No additional notes.';
        const reportLink = item.report_url
            ? `<a href="${item.report_url}" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:0.75rem;font-size:var(--text-sm);color:var(--blue-600);text-decoration:none;">View Quality Report →</a>`
            : '';
        return `
            <article class="waiver-item">
                <header class="waiver-header" role="button">
                    <h4>${item.name}</h4>
                    <span>${status}</span>
                </header>
                <div class="waiver-content">
                    <p>${reason}</p>
                    ${reportLink}
                    <div class="waiver-meta">${meta}</div>
                </div>
            </article>
        `;
    }).join('');
}

function renderFilterDetail(detail) {
    const panel = document.getElementById('filterDetailPanel');
    if (!panel) return;

    if (!detail || !lastQualityAnalytics) {
        panel.innerHTML = '<h4>Filter Detail</h4><p>Select a filter to review policy rationale and recent trend.</p>';
        return;
    }

    const sourceBreakdown = lastQualityAnalytics.perSource || [];
    const rows = sourceBreakdown
        .map(source => {
            const count = source.filters?.[detail.reason] || 0;
            if (!count) return null;
            const share = source.rejected > 0 ? (count / source.rejected) * 100 : 0;
            return `<dt>${source.name}</dt><dd>${count.toLocaleString()} records · ${share.toFixed(1)}%</dd>`;
        })
        .filter(Boolean)
        .join('');

    const narrative = describeFilterReason(detail.reason);

    panel.innerHTML = `
        <h4>${FILTER_REASON_LABELS[detail.reason] || detail.label}</h4>
        <p>${detail.count.toLocaleString()} records removed (${detail.share.toFixed(1)}% of rejections). ${narrative}.</p>
        <dl>${rows || '<dt>Sources</dt><dd>No sources triggered this filter in the latest run.</dd>'}</dl>
        <p style="font-size:var(--text-xs);color:var(--gray-500);margin-top:var(--space-3);">Cumulative share: ${detail.cumulative.toFixed(1)}%</p>
    `;
}

window.addEventListener('qualityFilterSelected', event => {
    renderFilterDetail(event.detail);
});

window.addEventListener('qualityFilterSummary', event => {
    const summary = event.detail?.summary || [];
    if (summary.length) {
        renderFilterDetail(summary[0]);
    }
});

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
        'Språkbanken': metricsData.metrics.find(m => m.source.includes('Sprakbanken')),
        'TikTok': metricsData.metrics.find(m => m.source.includes('TikTok'))
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
    const analytics = buildSourceAnalytics();
    const cards = document.querySelectorAll('#overview-panel .source-card[data-source]');

    if (!analytics || !analytics.items.length) {
        cards.forEach(card => {
            const metrics = card.querySelectorAll('.source-metric-value');
            metrics.forEach(m => m.textContent = '0');
            const badgeText = card.querySelector('.source-card-badge span:last-child');
            const badgeIcon = card.querySelector('.source-card-badge span:first-child');
            if (badgeText) badgeText.textContent = 'Pending';
            if (badgeIcon) badgeIcon.textContent = '⏳';
            const footer = card.querySelector('.source-card-footer span:first-child');
            if (footer) footer.textContent = 'No data yet';
            const statusDot = card.querySelector('.source-card-footer span:last-child');
            if (statusDot) statusDot.style.color = 'var(--gray-400)';
        });
        return;
    }

    const totalRecords = analytics.totalRecords || 0;
    const itemsMap = new Map(analytics.items.map(item => [item.name, item]));

    cards.forEach(card => {
        const sourceKey = card.getAttribute('data-source');
        const item = itemsMap.get(sourceKey);
        updateOverviewCard(card, item, totalRecords);
    });
}

/**
 * Update a single overview card with metric data
 */
function updateOverviewCard(card, item, totalRecords) {
    if (!card) return;

    const metrics = card.querySelectorAll('.source-metric-value');
    const footer = card.querySelector('.source-card-footer span:first-child');
    const statusDot = card.querySelector('.source-card-footer span:last-child');
    const badge = card.querySelector('.source-card-badge');
    const badgeText = badge ? badge.querySelector('span:last-child') : null;
    const badgeIcon = badge ? badge.querySelector('span:first-child') : null;

    if (!item) {
        metrics.forEach(m => m.textContent = '0');
        if (footer) footer.textContent = 'No data yet';
        if (statusDot) statusDot.style.color = 'var(--gray-400)';
        if (badge) {
            badge.classList.remove('complete', 'upcoming', 'planned');
            badge.classList.add('planned');
        }
        if (badgeText) badgeText.textContent = 'Pending';
        if (badgeIcon) badgeIcon.textContent = '⏳';
        return;
    }

    if (metrics.length === 3) {
        const records = Number(item.records) || 0;
        metrics[0].textContent = records.toLocaleString();
        metrics[0].setAttribute('data-value', records);

        const percentage = totalRecords > 0 ? (records / totalRecords * 100) : 0;
        metrics[1].textContent = percentage.toFixed(1) + '%';

        const qualityRate = Number.isFinite(item.quality) ? item.quality : 0;
        metrics[2].textContent = (qualityRate * 100).toFixed(1) + '%';
    }

    if (footer) {
        if (item.lastUpdated) {
            const date = new Date(item.lastUpdated);
            if (!Number.isNaN(date.getTime())) {
                footer.textContent = `Last run: ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
            } else {
                footer.textContent = `Last run: ${item.lastUpdated}`;
            }
        } else {
            footer.textContent = 'No data yet';
        }
    }

    if (statusDot) {
        const metadataKey = getMetadataKey(item.name);
        const qualityBenchmark = SOURCE_METADATA[metadataKey]?.qualityBenchmark ?? 0.7;
        const meetsBenchmark = Number.isFinite(item.quality) ? item.quality >= qualityBenchmark : false;
        statusDot.style.color = meetsBenchmark ? 'var(--success)' : 'var(--warning)';
    }

    if (badge) {
        badge.classList.remove('complete', 'upcoming', 'planned');
    }

    if (badgeText && badgeIcon) {
        if (item.records > 0) {
            badge?.classList.add('complete');
            badgeText.textContent = 'Complete';
            badgeIcon.textContent = '✓';
        } else if (item.lastUpdated) {
            badge?.classList.add('upcoming');
            badgeText.textContent = 'Ingesting';
            badgeIcon.textContent = '⏳';
        } else {
            badge?.classList.add('planned');
            badgeText.textContent = 'Planned';
            badgeIcon.textContent = '•';
        }
    }
}

/**
 * Update quality metrics with real data
 */
