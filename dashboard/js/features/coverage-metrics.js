/**
 * Coverage Metrics Module
 * Manages coverage scorecard and redesigned processing summary visuals
 */

import { getMetrics, getDashboardMetadata, getSourceCatalog } from '../core/data-service.js';
import { computePipelineAggregates, FILTER_REASON_LABELS } from '../core/aggregates.js';
import { normalizeSourceName, formatDate } from '../utils/formatters.js';

const SOURCE_ORDER = ['Wikipedia', 'BBC', 'HuggingFace', 'Språkbanken', 'TikTok'];

// Pipeline stage colors - extracted for maintainability
const PIPELINE_STAGE_COLORS = {
    discovered: '#94a3b8',      // Slate 400 - earliest stage
    fetched: '#60a5fa',         // Blue 400
    extracted: '#3b82f6',       // Blue 600
    quality_received: '#2563eb',// Blue 700
    written: '#10b981'          // Green 500 - final stage (success)
};

const SOURCE_COLOR_MAP = {
    'Wikipedia': '#3b82f6',
    'BBC': '#ef4444',
    'HuggingFace': '#00A651',
    'HuggingFace MC4': '#00A651',
    'Språkbanken': '#f59e0b',
    'TikTok': '#ec4899'
};

const ACQUISITION_COLOR_MAP = {
    'API + file snapshots': '#0891b2',  // Cyan-600 (WCAG AA: 4.52:1 contrast)
    'Partner file drop': '#ea580c',      // Orange-600 (WCAG AA: 4.51:1 contrast)
    'Dataset API': '#16a34a',            // Green-600 (WCAG AA: 4.54:1 contrast)
    'Apify actor': '#7c3aed',            // Violet-600 (WCAG AA: 5.71:1 contrast)
    'Web crawler': '#db2777',            // Fuchsia-600 (WCAG AA: 5.12:1 contrast)
    'Uncategorized': '#6b7280'           // Gray fallback
};

const SOURCE_METADATA = {
    'Wikipedia': {
        pipelineType: 'file_processing',
        qualityBenchmark: 0.5,
        narrative: 'File pipeline (Wikipedia) where filters remove stub articles'
    },
    'Språkbanken': {
        pipelineType: 'file_processing',
        qualityBenchmark: 0.6,
        narrative: 'Curated corpora with file-processing pipeline'
    },
    'BBC': {
        pipelineType: 'web_scraping',
        qualityBenchmark: 0.7,
        narrative: 'Web scraping pipeline (BBC) monitoring article quality'
    },
    'HuggingFace MC4': {
        pipelineType: 'stream_processing',
        qualityBenchmark: 0.7,
        narrative: 'Stream ingestion (MC4) with language and length guards'
    }
};

const DEFAULT_FILTER_LABEL = 'quality filters';

const QUALITY_TARGET = 0.85;
const coverageCharts = {
    velocity: null,
    balance: null,
    quality: null,
    stageAllocation: null
};

// Hardcoded fallback for offline/error cases
const STATIC_SOURCE_MIX = {
    share: {
        'Wikipedia': 0.231,
        'BBC': 0.023,
        'HuggingFace': 0.155,
        'Språkbanken': 0.124,
        'TikTok': 0.466
    },
    volumes: {
        'Wikipedia': 14900,
        'BBC': 1500,
        'HuggingFace': 10000,
        'Språkbanken': 8000,
        'TikTok': 30000
    },
    version: '2025-10-volume-plan'
};
const STATIC_SOURCE_MIX_VERSION_KEY = STATIC_SOURCE_MIX.version
    ? `static:${STATIC_SOURCE_MIX.version}`
    : `static:${JSON.stringify(STATIC_SOURCE_MIX.volumes || {})}`;

// Module-level storage for dynamically loaded source mix targets
let loadedSourceMixTargets = null;
let sourceMixLoadAttempted = false;

/**
 * Load source mix targets from JSON file
 * Uses fetch() with graceful fallback to hardcoded values
 * @returns {Promise<Object>} Source mix targets object
 */
async function loadSourceMixTargets() {
    if (sourceMixLoadAttempted && loadedSourceMixTargets) {
        return loadedSourceMixTargets;
    }

    sourceMixLoadAttempted = true;

    try {
        const response = await fetch('data/source_mix_targets.json');
        if (!response.ok) {
            console.warn(`Could not load source_mix_targets.json (status ${response.status}), using fallback`);
            loadedSourceMixTargets = STATIC_SOURCE_MIX;
            return loadedSourceMixTargets;
        }

        const data = await response.json();
        loadedSourceMixTargets = buildSourceMixTargetsFromJSON(data);
        console.info('Source mix targets loaded from JSON file:', loadedSourceMixTargets.version);
        return loadedSourceMixTargets;
    } catch (error) {
        console.warn('Error loading source_mix_targets.json:', error.message);
        loadedSourceMixTargets = STATIC_SOURCE_MIX;
        return loadedSourceMixTargets;
    }
}

/**
 * Build source mix targets object from loaded JSON data
 * @param {Object} data - Raw JSON data from source_mix_targets.json
 * @returns {Object} Normalized source mix targets
 */
function buildSourceMixTargetsFromJSON(data) {
    if (!data || !data.volumes) {
        console.warn('Invalid source_mix_targets.json structure, using fallback');
        return STATIC_SOURCE_MIX;
    }

    const volumes = {};
    const totalVolume = Object.values(data.volumes).reduce((sum, v) => sum + (Number(v) || 0), 0);
    const share = {};

    for (const [key, value] of Object.entries(data.volumes)) {
        const normalized = normalizeSourceName(key);
        const numericValue = Number(value);

        if (Number.isFinite(numericValue) && numericValue >= 0) {
            volumes[normalized] = numericValue;
            share[normalized] = totalVolume > 0 ? numericValue / totalVolume : 0;
        }
    }

    return {
        share,
        volumes,
        version: data.version || null
    };
}

/**
 * Get source mix version key for cache invalidation
 * @param {Object} metadata - Dashboard metadata
 * @returns {string} Version key
 */
function getSourceMixVersionKey(metadata) {
    // Check if we have loaded targets
    if (loadedSourceMixTargets?.version) {
        return `loaded:${loadedSourceMixTargets.version}`;
    }

    // Fall back to metadata-based detection
    if (metadata?.source_mix_targets_version) {
        return metadata.source_mix_targets_version;
    }
    if (metadata?.source_mix_targets) {
        return JSON.stringify(metadata.source_mix_targets);
    }

    return STATIC_SOURCE_MIX_VERSION_KEY;
}

function getSourceColor(label, alpha = 1) {
    const match = SOURCE_ORDER.find(source => label.includes(source));
    const hex = SOURCE_COLOR_MAP[match || label] || '#2563eb';
    if (alpha >= 1) return hex;
    return applyAlpha(hex, alpha);
}

function applyAlpha(hex, alpha) {
    const sanitized = hex.replace('#', '');
    if (sanitized.length !== 6) return hex;
    const r = parseInt(sanitized.slice(0, 2), 16);
    const g = parseInt(sanitized.slice(2, 4), 16);
    const b = parseInt(sanitized.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function getVolumeMetric(metric) {
    if (!metric) return 0;

    const candidates = [
        metric.records_written,
        metric.records_passed_filters,
        metric.records_extracted,
        metric.records_received,
        metric.urls_processed,
        metric.urls_fetched,
        metric.records_processed
    ];

    for (const candidate of candidates) {
        const value = Number(candidate);
        if (Number.isFinite(value) && value > 0) {
            return value;
        }
    }

    return 0;
}

function getTopFilterInsight(metrics) {
    const totals = new Map();
    metrics.forEach(metric => {
        Object.entries(metric.filter_breakdown || {}).forEach(([reason, count]) => {
            if (!Number.isFinite(count)) return;
            totals.set(reason, (totals.get(reason) || 0) + count);
        });
    });

    const sorted = Array.from(totals.entries())
        .filter(([, count]) => count > 0)
        .sort((a, b) => b[1] - a[1]);

    if (!sorted.length) {
        return null;
    }

    const [reason, count] = sorted[0];
    const total = sorted.reduce((sum, [, value]) => sum + value, 0);
    if (!total) {
        return null;
    }

    const label = FILTER_REASON_LABELS[reason] || reason.replace(/_/g, ' ');
    const percentage = (count / total) * 100;
    return { reason, label, percentage };
}

let cachedSourceTargetShare = null;
let cachedSourceTargetVolumes = null;
let cachedSourceTargetVersion = null;

/**
 * Get source target share percentages
 * Priority: 1) Loaded JSON file, 2) Dashboard metadata, 3) Hardcoded fallback
 * @returns {Object} Source share targets (0-1 ratios)
 */
function getSourceTargetShare() {
    const metadata = typeof getDashboardMetadata === 'function' ? getDashboardMetadata() : null;
    const versionKey = getSourceMixVersionKey(metadata);

    // Return cached values if version hasn't changed
    if (cachedSourceTargetShare && cachedSourceTargetVersion === versionKey) {
        return cachedSourceTargetShare;
    }

    // Invalidate cache
    cachedSourceTargetVersion = versionKey;
    cachedSourceTargetShare = null;
    cachedSourceTargetVolumes = null;

    // Priority 1: Use dynamically loaded targets from JSON file
    if (loadedSourceMixTargets && loadedSourceMixTargets.share && Object.keys(loadedSourceMixTargets.share).length > 0) {
        cachedSourceTargetShare = loadedSourceMixTargets.share;
        cachedSourceTargetVolumes = loadedSourceMixTargets.volumes;
        return cachedSourceTargetShare;
    }

    // Priority 2: Use dashboard metadata (if available)
    const shareTargets = metadata?.source_mix_targets?.share;
    const volumeTargets = metadata?.source_mix_targets?.volumes;

    const defaultShare = STATIC_SOURCE_MIX.share || {};
    const defaultVolumes = STATIC_SOURCE_MIX.volumes || {};

    const normalizedShare = {};
    let normalizedVolumes = {};
    let sharePopulated = false;

    if (shareTargets && Object.keys(shareTargets).length > 0) {
        Object.entries(shareTargets).forEach(([key, value]) => {
            const normalizedKey = normalizeSourceName(key);
            const numericValue = Number(value);
            if (Number.isFinite(numericValue)) {
                const ratio = numericValue > 1 ? numericValue / 100 : numericValue;
                const safeRatio = Math.max(0, Math.min(ratio, 1));
                if (Number.isFinite(safeRatio)) {
                    normalizedShare[normalizedKey] = safeRatio;
                    sharePopulated = true;
                }
            }
        });
    }

    if (volumeTargets && Object.keys(volumeTargets).length > 0) {
        normalizedVolumes = Object.fromEntries(
            Object.entries(volumeTargets).map(([key, value]) => {
                const normalizedKey = normalizeSourceName(key);
                const numericValue = Number(value);
                return [
                    normalizedKey,
                    Number.isFinite(numericValue) && numericValue >= 0 ? numericValue : 0
                ];
            })
        );

        if (!sharePopulated) {
            const totalVolume = Object.values(normalizedVolumes).reduce((sum, value) => sum + (Number(value) || 0), 0);
            if (totalVolume > 0) {
                Object.entries(normalizedVolumes).forEach(([key, value]) => {
                    normalizedShare[key] = (Number(value) || 0) / totalVolume;
                });
                sharePopulated = true;
            }
        }
    }

    if (!Object.keys(normalizedVolumes).length && Object.keys(defaultVolumes).length) {
        normalizedVolumes = { ...defaultVolumes };
    }

    if (!sharePopulated && Object.keys(normalizedVolumes).length > 0) {
        const totalVolume = Object.values(normalizedVolumes).reduce((sum, value) => sum + (Number(value) || 0), 0);
        if (totalVolume > 0) {
            Object.entries(normalizedVolumes).forEach(([key, value]) => {
                normalizedShare[key] = (Number(value) || 0) / totalVolume;
            });
            sharePopulated = true;
        }
    }

    // Priority 3: Fall back to hardcoded values
    const mergedShare = sharePopulated
        ? { ...(defaultShare || {}), ...normalizedShare }
        : { ...(defaultShare || {}) };

    cachedSourceTargetShare = mergedShare;
    cachedSourceTargetVolumes = Object.keys(normalizedVolumes).length
        ? { ...(defaultVolumes || {}), ...normalizedVolumes }
        : { ...(defaultVolumes || {}) };

    return cachedSourceTargetShare;
}

function getSourceTargetVolumes() {
    const metadata = typeof getDashboardMetadata === 'function' ? getDashboardMetadata() : null;
    const versionKey = getSourceMixVersionKey(metadata);

    if (!cachedSourceTargetVolumes || cachedSourceTargetVersion !== versionKey) {
        getSourceTargetShare();
    }

    return cachedSourceTargetVolumes || {};
}

function extractTimestamp(metric) {
    return metric.last_successful_write || metric.timestamp || metric.snapshot?.timestamp || null;
}

function aggregateRunSeries(metrics, limit = 8) {
    const runMap = new Map();
    metrics.forEach(metric => {
        if (!metric) return;

        const records = Number(metric.records_written) || 0;
        const durationSeconds = Number(metric.duration_seconds) || 0;
        const source = normalizeSourceName(metric.source);
        const timestamp = extractTimestamp(metric);
        if (!timestamp || !source) return;

        const rawRunId = metric.run_id || metric._run_id || '';
        let runKey = null;
        if (rawRunId) {
            const parts = rawRunId.split('_');
            if (parts.length >= 2) {
                runKey = `${parts[0]}_${parts[1]}`;
            } else {
                runKey = parts[0];
            }
        }
        if (!runKey) {
            runKey = timestamp.slice(0, 16);
        }

        let entry = runMap.get(runKey);
        if (!entry) {
            entry = {
                runId: runKey,
                startTimestamp: timestamp,
                endTimestamp: timestamp,
                sources: {},
                total: 0,
                durationSeconds: 0,
                throughputWeighted: 0,
                throughputWeight: 0,
                activeSources: new Set(),
                timestamps: new Set(),
                sourceStats: {}
            };
            runMap.set(runKey, entry);
        }

        entry.timestamps.add(timestamp);
        if (timestamp < entry.startTimestamp) {
            entry.startTimestamp = timestamp;
        }
        if (timestamp > entry.endTimestamp) {
            entry.endTimestamp = timestamp;
        }

        if (Number.isFinite(records) && records > 0) {
            entry.sources[source] = (entry.sources[source] || 0) + records;
            entry.total += records;
            entry.activeSources.add(source);
        } else if (!entry.sources[source]) {
            entry.sources[source] = 0;
        }

        if (!entry.sourceStats[source]) {
            entry.sourceStats[source] = {
                records: 0,
                durationSeconds: 0,
                rpmWeighted: 0,
                rpmWeight: 0
            };
        }
        const stats = entry.sourceStats[source];
        if (Number.isFinite(records) && records > 0) {
            stats.records += records;
        }
        if (Number.isFinite(durationSeconds) && durationSeconds > 0) {
            stats.durationSeconds += durationSeconds;
        }

        entry.durationSeconds += durationSeconds;

        let rpm = Number(metric.records_per_minute);
        if (!Number.isFinite(rpm) || rpm < 0) {
            if (Number.isFinite(durationSeconds) && durationSeconds > 0 && Number.isFinite(records) && records > 0) {
                rpm = (records * 60) / durationSeconds;
            } else {
                rpm = null;
            }
        }

        if (Number.isFinite(rpm) && rpm >= 0) {
            const weight = records > 0 ? records : 1;
            entry.throughputWeighted += rpm * weight;
            entry.throughputWeight += weight;
            stats.rpmWeighted += rpm * weight;
            stats.rpmWeight += weight;
        }
    });

    const runs = Array.from(runMap.values())
        .map(entry => {
            const durationMinutes = entry.durationSeconds > 0 ? entry.durationSeconds / 60 : null;
            const avgThroughput = durationMinutes && durationMinutes > 0
                ? entry.total / durationMinutes
                : null;

            const sourceThroughput = {};
            const sourceDurations = {};
            Object.entries(entry.sourceStats || {}).forEach(([source, stats]) => {
                if (stats.durationSeconds > 0) {
                    sourceDurations[source] = stats.durationSeconds;
                }

                let sourceRpm = null;
                if (stats.rpmWeight > 0) {
                    sourceRpm = stats.rpmWeighted / stats.rpmWeight;
                } else if (stats.durationSeconds > 0 && stats.records > 0) {
                    sourceRpm = (stats.records * 60) / stats.durationSeconds;
                }

                if (Number.isFinite(sourceRpm) && sourceRpm >= 0) {
                    sourceThroughput[source] = sourceRpm;
                }
            });

            return {
                runId: entry.runId,
                timestamp: entry.endTimestamp || entry.startTimestamp,
                startTimestamp: entry.startTimestamp,
                endTimestamp: entry.endTimestamp,
                sources: entry.sources,
                total: entry.total,
                avgThroughput: avgThroughput !== null
                    ? avgThroughput
                    : (entry.throughputWeight > 0
                        ? entry.throughputWeighted / entry.throughputWeight
                        : null),
                activeSources: entry.activeSources.size || Object.keys(entry.sources).length,
                timestampCount: entry.timestamps.size,
                sourceThroughput,
                sourceDurations
            };
        })
        .sort((a, b) => {
            const tsA = new Date(a.timestamp || 0).getTime();
            const tsB = new Date(b.timestamp || 0).getTime();
            return tsA - tsB;
        })
        .slice(-limit);

    return runs;
}

function formatRunTimestamp(timestamp) {
    if (!timestamp) return 'Latest run';
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }
    return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatRunWindow(start, end, { long = false } = {}) {
    if (!start && !end) return 'Latest run';
    const startDate = start ? new Date(start) : null;
    const endDate = end ? new Date(end) : null;

    if (!startDate || Number.isNaN(startDate.getTime())) {
        return formatRunTimestamp(end);
    }

    if (!endDate || Number.isNaN(endDate.getTime())) {
        return formatRunTimestamp(start);
    }

    if (startDate.getTime() === endDate.getTime()) {
        return startDate.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }

    const sameDay = startDate.toDateString() === endDate.toDateString();
    const dayPrefix = sameDay
        ? startDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' · '
        : '';
    const startLabel = sameDay
        ? startDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
        : startDate.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    const endLabel = endDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });

    if (long && !sameDay) {
        return `${startDate.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        })} – ${endDate.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        })}`;
    }

    return `${dayPrefix}${startLabel} – ${endLabel}`;
}

function computePipelineStageTotals(metrics = []) {
    const totals = {
        discovered: 0,
        fetched: 0,
        extracted: 0,
        quality_received: 0,
        passed_quality: 0,
        written: 0
    };

    if (!Array.isArray(metrics) || !metrics.length) {
        return totals;
    }

    metrics.forEach(metric => {
        if (!metric) return;

        const filteredTotal = Object.values(metric.filter_breakdown || {}).reduce((sum, value) => sum + (Number(value) || 0), 0);
        const written = Number(metric.records_written) || 0;

        let qualityReceived = Number(metric.records_received);
        if (!Number.isFinite(qualityReceived) || qualityReceived <= 0) {
            qualityReceived = written + filteredTotal;
        }

        let extracted = Number(metric.records_extracted);
        if (!Number.isFinite(extracted) || extracted <= 0) {
            extracted = Number(metric.records_processed) || Number(metric.urls_processed) || qualityReceived;
        }
        extracted = Math.max(extracted, qualityReceived);

        let fetched = Number(metric.urls_fetched);
        if (!Number.isFinite(fetched) || fetched <= 0) {
            fetched = extracted;
        }
        fetched = Math.max(fetched, extracted);

        let discovered = Number(metric.urls_discovered);
        if (!Number.isFinite(discovered) || discovered <= 0) {
            discovered = fetched;
        }
        discovered = Math.max(discovered, fetched);

        totals.discovered += discovered;
        totals.fetched += fetched;
        totals.extracted += extracted;
        totals.quality_received += qualityReceived;
        totals.passed_quality += written;
        totals.written += written;
    });

    totals.fetched = Math.min(totals.fetched, totals.discovered);
    totals.extracted = Math.min(totals.extracted, totals.fetched);
    totals.quality_received = Math.min(totals.quality_received, totals.extracted);
    totals.passed_quality = Math.min(totals.passed_quality, totals.quality_received);
    totals.written = Math.min(totals.written, totals.passed_quality);

    return totals;
}

function renderPipelineEfficiency(metricsData) {
    const barContainer = document.getElementById('pipelineEfficiencyBar');
    const statsList = document.getElementById('pipelineEfficiencyStats');
    const calloutValue = document.getElementById('efficiency-yield-label');
    const footnote = document.getElementById('pipeline-efficiency-footnote');

    if (!barContainer || !statsList) {
        return;
    }

    barContainer.innerHTML = '';
    statsList.innerHTML = '';

    const stages = computePipelineStageTotals(metricsData?.metrics || []);
    const baseline = Math.max(
        stages.discovered,
        stages.fetched,
        stages.extracted,
        stages.quality_received,
        stages.written
    );

    if (!baseline) {
        if (calloutValue) {
            calloutValue.textContent = '—';
        }
        statsList.innerHTML = `<li class="pipeline-efficiency-empty">Run the ingestion orchestrator to view retention across pipeline stages.</li>`;
        barContainer.innerHTML = '<div class="chart-empty-state">Pipeline efficiency visualization will appear after the next run.</div>';
        if (footnote) {
            footnote.textContent = 'Retention values update after each orchestration run.';
        }
        return;
    }

    const stageOrder = [
        { key: 'discovered', label: 'Discovered', color: PIPELINE_STAGE_COLORS.discovered },
        { key: 'fetched', label: 'Fetched', color: PIPELINE_STAGE_COLORS.fetched },
        { key: 'extracted', label: 'Extracted', color: PIPELINE_STAGE_COLORS.extracted },
        { key: 'quality_received', label: 'Quality Check', color: PIPELINE_STAGE_COLORS.quality_received },
        { key: 'written', label: 'Silver Dataset', color: PIPELINE_STAGE_COLORS.written }
    ];

    const segments = stageOrder.map(stage => {
        const value = stages[stage.key] || 0;
        // Calculate width percentage, ensuring minimum 2% visibility for non-zero values
        let width = 0;
        if (baseline > 0) {
            width = (value / baseline) * 100;
            // Ensure minimum 2% width for non-zero values (visibility)
            if (value > 0) {
                width = Math.max(width, 2);
            }
        }
        return `<div class="pipeline-efficiency-segment" aria-hidden="true" style="width:${width}%;background-color:${stage.color};" title="${stage.label}: ${value.toLocaleString()} records"></div>`;
    });

    barContainer.innerHTML = segments.join('');

    let previousValue = baseline;
    const statsItems = stageOrder.map((stage, index) => {
        const value = stages[stage.key] || 0;
        const originShare = baseline > 0 ? (value / baseline) * 100 : 0;
        const relativeShare = index === 0
            ? 100
            : previousValue > 0
                ? (value / previousValue) * 100
                : 0;
        previousValue = value;
        const roundedValue = Math.round(value);

        return `
            <li class="pipeline-efficiency-stage">
                <span class="pipeline-stage-dot" style="background-color:${stage.color};"></span>
                <span class="pipeline-stage-label">${stage.label}</span>
                <span class="pipeline-stage-value">${roundedValue.toLocaleString()}</span>
                <span class="pipeline-stage-percent">${originShare.toFixed(1)}% of origin${index > 0 ? ` · ${relativeShare.toFixed(1)}% vs prior` : ''}</span>
            </li>
        `;
    });

    statsList.innerHTML = statsItems.join('');

    if (calloutValue) {
        const silverYield = baseline > 0 ? (stages.written / baseline) * 100 : 0;
        calloutValue.textContent = `${silverYield.toFixed(1)}%`;
    }

    if (footnote) {
        const latestRun = aggregateRunSeries(metricsData?.metrics || [], 1)[0];
        if (latestRun) {
            footnote.textContent = `Latest data from ${formatRunWindow(latestRun.startTimestamp, latestRun.endTimestamp, { long: true })}.`;
        } else {
            const latestTimestamp = (metricsData?.metrics || [])
                .map(metric => metric.timestamp)
                .filter(Boolean)
                .sort()
                .pop();
            if (latestTimestamp) {
                footnote.textContent = `Latest data from ${formatRunTimestamp(latestTimestamp)}.`;
            }
        }
    }
}

function aggregateSourceTotals(metrics) {
    const totals = new Map();
    const uniqueSources = new Set();
    let grandTotal = 0;

    metrics.forEach(metric => {
        if (!metric) return;
        const source = normalizeSourceName(metric.source);
        uniqueSources.add(source);

        const contribution = getVolumeMetric(metric);
        if (Number.isFinite(contribution) && contribution > 0) {
            totals.set(source, (totals.get(source) || 0) + contribution);
            grandTotal += contribution;
        } else if (!totals.has(source)) {
            totals.set(source, 0);
        }
    });

    return { totals, grandTotal, uniqueSources };
}

function computeQualityBySource(metrics) {
    const aggregates = new Map();

    metrics.forEach(metric => {
        const source = normalizeSourceName(metric.source);
        if (!aggregates.has(source)) {
            aggregates.set(source, {
                source,
                records: 0,
                qualityWeighted: 0,
                qualitySamples: 0,
                successWeighted: 0,
                successSamples: 0,
                latestTimestamp: null
            });
        }

        const entry = aggregates.get(source);
        const records = Number(metric.records_written) || 0;
        const weight = records > 0 ? records : 1;

        entry.records += records;

        const quality = typeof metric.quality_pass_rate === 'number' ? metric.quality_pass_rate : null;
        if (quality !== null) {
            entry.qualityWeighted += quality * weight;
            entry.qualitySamples += weight;
        }

        const success = typeof metric.success_rate === 'number'
            ? metric.success_rate
            : (typeof metric.http_request_success_rate === 'number' ? metric.http_request_success_rate : null);
        if (success !== null) {
            entry.successWeighted += success * weight;
            entry.successSamples += weight;
        }

        const timestamp = extractTimestamp(metric);
        if (timestamp && (!entry.latestTimestamp || timestamp > entry.latestTimestamp)) {
            entry.latestTimestamp = timestamp;
        }
    });

    const list = Array.from(aggregates.values()).map(entry => ({
        source: entry.source,
        records: entry.records,
        qualityRate: entry.qualitySamples > 0 ? entry.qualityWeighted / entry.qualitySamples : null,
        successRate: entry.successSamples > 0 ? entry.successWeighted / entry.successSamples : null,
        latestTimestamp: entry.latestTimestamp
    }));

    return list.sort((a, b) => {
        const idxA = SOURCE_ORDER.indexOf(a.source);
        const idxB = SOURCE_ORDER.indexOf(b.source);
        if (idxA === -1 && idxB === -1) return a.source.localeCompare(b.source);
        if (idxA === -1) return 1;
        if (idxB === -1) return -1;
        return idxA - idxB;
    });
}

function renderEmptyState(canvas, message) {
    if (!canvas) return;
    const wrapper = canvas.parentElement;
    if (!wrapper) return;
    wrapper.innerHTML = `<p class="chart-empty-state">${message}</p>`;
}

function resetCalloutClasses(element, ...classNames) {
    if (!element) return;
    element.classList.remove(...classNames);
}

function updateOverviewNarrative(aggregates, metrics = []) {
    const narrativeEl = document.getElementById('overview-narrative');
    if (!narrativeEl) return;

    if (!aggregates || !Array.isArray(metrics) || metrics.length === 0) {
        narrativeEl.textContent = 'Run the ingestion pipelines to populate this overview.';
        return;
    }

    const { totals, grandTotal, uniqueSources } = aggregateSourceTotals(metrics);
    const activeSources = uniqueSources.size || aggregates.activeSources || 0;

    const positiveTotals = Array.from(totals.entries()).filter(([, value]) => value > 0);
    const leaderEntry = grandTotal > 0 && positiveTotals.length > 0
        ? positiveTotals.sort((a, b) => b[1] - a[1])[0]
        : null;
    const leaderName = leaderEntry ? leaderEntry[0] : null;
    const leaderShare = leaderEntry ? ((leaderEntry[1] / Math.max(grandTotal, 1)) * 100).toFixed(1) : null;
    const leaderFragment = leaderName && leaderShare
        ? `, led by ${leaderName} at ${leaderShare}% of submissions`
        : '';

    const statements = [];
    const totalRecords = Number.isFinite(aggregates.totalRecords) ? aggregates.totalRecords : 0;

    if (totalRecords > 0) {
        statements.push(`Ingestion has landed ${totalRecords.toLocaleString()} records across ${activeSources} active sources${leaderFragment}.`);
    } else if (grandTotal > 0) {
        statements.push(`Pipelines evaluated ${grandTotal.toLocaleString()} candidate records across ${activeSources} sources${leaderFragment}, with quality gates holding back new silver data until they pass validation.`);
    } else {
        statements.push(`Pipelines ran across ${activeSources} sources, but no new silver records were published in the latest cycle.`);
    }

    const qualityValue = Number.isFinite(aggregates.avgQualityRate) ? aggregates.avgQualityRate : null;
    const qualityInsight = getTopFilterInsight(metrics);
    if (qualityValue === null) {
        statements.push('Quality filters have not reported yet; check the Quality Insights panel for run-level details.');
    } else {
        const qualityPercent = (qualityValue * 100).toFixed(1);

        if (qualityValue >= QUALITY_TARGET) {
            const filterSentence = qualityInsight && qualityInsight.percentage >= 1
                ? ` with ${qualityInsight.label.toLowerCase()} accounting for ${qualityInsight.percentage.toFixed(1)}% of removals`
                : '';
            statements.push(`Record-weighted quality sits at ${qualityPercent}%, comfortably above the 85% target${filterSentence}.`);
        } else if (qualityValue >= 0.5) {
            const filterSentence = qualityInsight && qualityInsight.percentage >= 1
                ? ` (${qualityInsight.label}, ${qualityInsight.percentage.toFixed(1)}% of rejections)`
                : '';
            statements.push(`Record-weighted quality holds at ${qualityPercent}%, showing filters are keeping short or off-topic records out of silver${filterSentence}.`);
        } else {
            const filterSentence = qualityInsight && qualityInsight.percentage >= 1
                ? ` (${qualityInsight.label}, ${qualityInsight.percentage.toFixed(1)}% of rejections)`
                : '';
            statements.push(`Record-weighted quality is ${qualityPercent}%; review recent runs to confirm whether source shifts or filter tuning are needed${filterSentence}.`);
        }
    }

    const successValue = Number.isFinite(aggregates.avgSuccessRate) ? aggregates.avgSuccessRate : null;
    if (successValue === null) {
        statements.push('Pipeline reliability metrics are still populating.');
    } else {
        const successPercent = (successValue * 100).toFixed(1);
        if (successValue >= 0.99) {
            statements.push(`Success rate remains at ${successPercent}%, indicating every scheduled run delivered data after retries.`);
        } else if (successValue >= 0.95) {
            statements.push(`Success rate is ${successPercent}%, showing only light retry activity across sources.`);
        } else {
            statements.push(`Success rate is ${successPercent}%; audit recent run logs to confirm connectors are healthy.`);
        }
    }

    const freshestMetric = metrics
        .filter(metric => metric && metric.timestamp)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];

    if (freshestMetric) {
        const freshestSource = normalizeSourceName(freshestMetric.source);
        const freshestTime = new Date(freshestMetric.timestamp);
        const timestampLabel = Number.isFinite(freshestTime.getTime())
            ? freshestTime.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
            : formatDate(freshestMetric.timestamp);
        const freshestRecords = Number(freshestMetric.records_written) || 0;
        const freshestThroughput = Number(freshestMetric.records_per_minute);
        const throughputLabel = Number.isFinite(freshestThroughput) && freshestThroughput > 0
            ? ` at ~${Math.round(freshestThroughput).toLocaleString()} records/min`
            : '';
        statements.push(`Most recent run: ${freshestSource} on ${timestampLabel}, landing ${freshestRecords.toLocaleString()} records${throughputLabel}.`);
    }

    narrativeEl.textContent = statements.join(' ');
}

function updateVelocityNarrative(runSeries) {
    const latestValueEl = document.getElementById('velocity-latest-total');
    const deltaEl = document.getElementById('velocity-delta');
    const callout = document.getElementById('velocity-callout');
    const footnote = document.getElementById('velocity-footnote');

    const latest = runSeries.length ? runSeries[runSeries.length - 1] : null;
    const previous = runSeries.length > 1 ? runSeries[runSeries.length - 2] : null;

    if (latestValueEl) {
        latestValueEl.textContent = latest ? (latest.total || 0).toLocaleString() : '0';
    }

    if (deltaEl) {
        resetCalloutClasses(deltaEl, 'positive', 'negative', 'neutral');
        if (!latest || !previous) {
            deltaEl.textContent = '–';
            deltaEl.classList.add('neutral');
        } else {
            const diff = (latest.total || 0) - (previous.total || 0);
            const throughputDiff = Number.isFinite(latest.avgThroughput) && Number.isFinite(previous.avgThroughput)
                ? latest.avgThroughput - previous.avgThroughput
                : null;

            const parts = [];
            if (diff === 0) {
                parts.push('No change vs prior run');
            } else {
                parts.push(`${diff > 0 ? '+' : ''}${diff.toLocaleString()} vs prior run`);
            }

            if (throughputDiff !== null && Math.abs(throughputDiff) >= 1) {
                parts.push(`${throughputDiff > 0 ? '+' : ''}${Math.round(throughputDiff)} rpm`);
            }

            deltaEl.textContent = parts.join(' · ');
            deltaEl.classList.add(diff > 0 ? 'positive' : diff < 0 ? 'negative' : 'neutral');
        }
    }

    if (callout) {
        resetCalloutClasses(callout, 'positive', 'negative');
        if (deltaEl?.classList.contains('positive')) {
            callout.classList.add('positive');
        } else if (deltaEl?.classList.contains('negative')) {
            callout.classList.add('negative');
        }
    }

    if (footnote) {
        if (!latest) {
            footnote.textContent = 'Waiting for pipeline runs…';
        } else {
            const activeSources = latest.activeSources || Object.keys(latest.sources || {}).length;
            const plural = activeSources === 1 ? '' : 's';
            const windowLabel = formatRunWindow(latest.startTimestamp, latest.endTimestamp, { long: true });
            footnote.textContent = `${windowLabel} · ${activeSources} active source${plural}.`;
        }
    }
}

function updateBalanceNarrative(labels, actualPercentages, targetPercentages) {
    const calloutValue = document.getElementById('balance-gap-label');
    const calloutWrapper = document.getElementById('balance-callout');
    if (!calloutValue || !calloutWrapper) return;

    resetCalloutClasses(calloutValue, 'positive', 'negative', 'neutral');
    resetCalloutClasses(calloutWrapper, 'positive', 'negative');

    if (!labels.length) {
        calloutValue.textContent = '–';
        calloutValue.classList.add('neutral');
        return;
    }

    let largestDiffIndex = 0;
    let largestDiffValue = 0;

    labels.forEach((label, idx) => {
        const diff = (actualPercentages[idx] ?? 0) - (targetPercentages[idx] ?? 0);
        if (Math.abs(diff) > Math.abs(largestDiffValue)) {
            largestDiffValue = diff;
            largestDiffIndex = idx;
        }
    });

    const diff = largestDiffValue;
    const label = labels[largestDiffIndex];
    const formattedDiff = `${diff > 0 ? '+' : ''}${diff.toFixed(1)} pts`;

    calloutValue.textContent = `${label}: ${formattedDiff}`;

    if (diff >= 2) {
        calloutValue.classList.add('positive');
        calloutWrapper.classList.add('positive');
    } else if (diff <= -2) {
        calloutValue.classList.add('negative');
        calloutWrapper.classList.add('negative');
    } else {
        calloutValue.classList.add('neutral');
    }

    const footnote = document.getElementById('source-balance-footnote');
    if (footnote) {
        const metadata = typeof getDashboardMetadata === 'function' ? getDashboardMetadata() : null;
        const targetsVersion = metadata?.source_mix_targets_version;
        const targets = getSourceTargetShare();
        const volumes = getSourceTargetVolumes();
        const targetSummary = SOURCE_ORDER
            .filter(name => Object.prototype.hasOwnProperty.call(targets, name))
            .map(name => {
                const shareValue = Number(targets[name]) || 0;
                const sharePct = (shareValue * 100).toFixed(1);
                const volumeValue = Number(volumes[name]);
                const volumeLabel = Number.isFinite(volumeValue)
                    ? `${volumeValue.toLocaleString()} (~${sharePct}%)`
                    : `${sharePct}%`;
                return `${name} ${volumeLabel}`;
            });
        const versionLabel = targetsVersion ? `v${targetsVersion}` : '';
        footnote.textContent = `Targets reflect planned dataset volumes${versionLabel ? ` (${versionLabel})` : ''}: ${targetSummary.join(', ')}.`;
    }
}

function updateQualityNarrative(qualityData) {
    const calloutValue = document.getElementById('quality-average-label');
    const calloutWrapper = document.getElementById('quality-callout');
    const freshnessNote = document.getElementById('quality-freshness-note');

    resetCalloutClasses(calloutValue, 'positive', 'negative', 'neutral');
    resetCalloutClasses(calloutWrapper, 'positive', 'negative');

    if (!qualityData.length) {
        if (calloutValue) {
            calloutValue.textContent = '0%';
            calloutValue.classList.add('neutral');
        }
        if (freshnessNote) {
            freshnessNote.textContent = 'Quality targets set at 85% minimum pass rate.';
        }
        return;
    }

    const totalRecords = qualityData.reduce((sum, item) => sum + Math.max(item.records || 0, 0), 0);
    const weightedQuality = totalRecords > 0
        ? qualityData.reduce((sum, item) => sum + (item.qualityRate ?? 0) * Math.max(item.records || 0, 0), 0) / totalRecords
        : qualityData.reduce((sum, item) => sum + (item.qualityRate ?? 0), 0) / qualityData.length;

    const avgQuality = weightedQuality;

    if (calloutValue) {
        calloutValue.textContent = (avgQuality * 100).toFixed(1) + '%';
        if (avgQuality >= QUALITY_TARGET) {
            calloutValue.classList.add('positive');
            calloutWrapper?.classList.add('positive');
        } else {
            calloutValue.classList.add('negative');
            calloutWrapper?.classList.add('negative');
        }
    }

    if (freshnessNote) {
        const freshest = qualityData.reduce((acc, item) => {
            if (!item.latestTimestamp) return acc;
            if (!acc || item.latestTimestamp > acc.latestTimestamp) return item;
            return acc;
        }, null);

        if (freshest?.latestTimestamp) {
            freshnessNote.textContent = `Most recent source update: ${freshest.source} on ${formatDate(freshest.latestTimestamp)}.`;
        } else {
            freshnessNote.textContent = 'Quality targets set at 85% minimum pass rate.';
        }
    }
}

function createIngestionVelocityChart(metricsData) {
    const canvas = document.getElementById('ingestionVelocityChart');
    if (!canvas) return;

    const runSeries = aggregateRunSeries(metricsData.metrics);

    if (!runSeries.length) {
        updateVelocityNarrative([]);
        renderEmptyState(canvas, 'Ingestion runs have not produced records yet.');
        return;
    }

    updateVelocityNarrative(runSeries);

    const uniqueSources = new Set();
    runSeries.forEach(run => {
        Object.keys(run.sources).forEach(source => uniqueSources.add(source));
    });

    const orderedSources = SOURCE_ORDER
        .filter(source => uniqueSources.has(source))
        .concat(Array.from(uniqueSources).filter(source => !SOURCE_ORDER.includes(source)).sort());

    const timelineEntries = [];
    runSeries.forEach((run, index) => {
        const runLabel = formatRunWindow(run.startTimestamp, run.endTimestamp);
        const sourcesInRun = orderedSources.filter(source => (run.sources[source] || 0) > 0);
        const fallbackSources = Object.keys(run.sources || {})
            .filter(source => !orderedSources.includes(source) && (run.sources[source] || 0) > 0)
            .sort();

        const orderedRunSources = sourcesInRun.concat(fallbackSources);

        if (!orderedRunSources.length) {
            timelineEntries.push({
                run,
                source: 'Unknown',
                records: 0,
                throughput: null,
                durationSeconds: null,
                label: 'Unknown',
                runLabel,
                isFirstInRun: true,
                isLastInRun: true
            });
            return;
        }

        orderedRunSources.forEach((source, idxInRun) => {
            const records = run.sources[source] || 0;
            const throughput = run.sourceThroughput?.[source] ?? null;
            const durationSeconds = run.sourceDurations?.[source] ?? null;
            timelineEntries.push({
                run,
                source,
                records,
                throughput,
                durationSeconds,
                label: source,
                runLabel,
                isFirstInRun: idxInRun === 0,
                isLastInRun: idxInRun === orderedRunSources.length - 1
            });
        });
    });

    const labels = timelineEntries.map(entry => entry.label);

    const datasets = orderedSources.map((source, datasetIndex) => ({
        label: source,
        data: timelineEntries.map(entry => entry.source === source ? entry.records : null),
        backgroundColor: timelineEntries.map(entry => {
            if (entry.source !== source) return 'rgba(0,0,0,0)';
            const isLatestRun = entry.run === runSeries[runSeries.length - 1];
            return getSourceColor(source, isLatestRun ? 0.95 : 0.6);
        }),
        borderColor: getSourceColor(source),
        borderWidth: 1,
        borderRadius: 8,
        categoryPercentage: 0.7,
        barPercentage: 0.85,
        order: datasetIndex,
        skipNull: true
    }));

    datasets.push({
        type: 'line',
        label: 'Source throughput',
        data: timelineEntries.map(entry => Number.isFinite(entry.throughput) ? entry.throughput : null),
        yAxisID: 'y1',
        borderColor: '#0ea5e9',
        backgroundColor: 'rgba(14, 165, 233, 0.2)',
        tension: 0.45,
        cubicInterpolationMode: 'monotone',
        fill: false,
        pointRadius: 4,
        pointBackgroundColor: '#0ea5e9',
        pointBorderWidth: 2,
        spanGaps: true,
        order: orderedSources.length + 1
    });

    /**
     * Custom Chart.js plugin to render run label badges above bar clusters.
     * Displays run time windows grouped above their corresponding sources.
     */
    const velocityRunLabelPlugin = {
        id: 'velocityRunLabels',
        afterDatasetsDraw(chart) {
            const { ctx, chartArea, scales } = chart;
            if (!chartArea || !scales?.x) return;

            // Get timeline entries from closure scope
            const entries = timelineEntries;
            if (!entries || !entries.length) return;

            // Find run boundaries (indices where new run starts)
            const runGroups = [];
            let currentRun = null;
            let startIdx = 0;

            entries.forEach((entry, idx) => {
                if (entry.isFirstInRun) {
                    if (currentRun) {
                        runGroups.push({
                            run: currentRun,
                            startIdx,
                            endIdx: idx - 1,
                            label: formatRunWindow(currentRun.startTimestamp, currentRun.endTimestamp)
                        });
                    }
                    currentRun = entry.run;
                    startIdx = idx;
                }

                // Handle last group
                if (idx === entries.length - 1) {
                    runGroups.push({
                        run: currentRun,
                        startIdx,
                        endIdx: idx,
                        label: formatRunWindow(currentRun.startTimestamp, currentRun.endTimestamp)
                    });
                }
            });

            // Render badges for each run group
            ctx.save();
            ctx.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif';

            runGroups.forEach(group => {
                // Calculate badge position (centered above group)
                const startPixel = scales.x.getPixelForValue(group.startIdx);
                const endPixel = scales.x.getPixelForValue(group.endIdx);
                const centerX = (startPixel + endPixel) / 2;
                const groupWidth = endPixel - startPixel;
                const badgeY = chartArea.top - 20;  // 20px above chart

                // Smart text truncation
                let displayText = group.label;
                const maxTextWidth = groupWidth - 20;  // 10px margin each side
                let textWidth = ctx.measureText(displayText).width;

                if (textWidth > maxTextWidth && maxTextWidth > 40) {
                    // Truncate and add ellipsis
                    while (textWidth > maxTextWidth - 10 && displayText.length > 10) {
                        displayText = displayText.slice(0, -1);
                        textWidth = ctx.measureText(displayText + '…').width;
                    }
                    displayText += '…';
                }

                // Badge dimensions
                const hPadding = 12;
                const badgeWidth = ctx.measureText(displayText).width + hPadding * 2;
                const badgeHeight = 22;
                const badgeX = centerX - badgeWidth / 2;

                // Draw rounded background
                ctx.fillStyle = '#f8fafc';    // Slate-50
                ctx.strokeStyle = '#e2e8f0';  // Slate-200
                ctx.lineWidth = 1;

                // Rounded rectangle (with polyfill fallback)
                ctx.beginPath();
                if (ctx.roundRect) {
                    ctx.roundRect(badgeX, badgeY, badgeWidth, badgeHeight, 12);
                } else {
                    // Fallback for older browsers
                    const r = 12;
                    ctx.moveTo(badgeX + r, badgeY);
                    ctx.arcTo(badgeX + badgeWidth, badgeY, badgeX + badgeWidth, badgeY + badgeHeight, r);
                    ctx.arcTo(badgeX + badgeWidth, badgeY + badgeHeight, badgeX, badgeY + badgeHeight, r);
                    ctx.arcTo(badgeX, badgeY + badgeHeight, badgeX, badgeY, r);
                    ctx.arcTo(badgeX, badgeY, badgeX + badgeWidth, badgeY, r);
                    ctx.closePath();
                }
                ctx.fill();
                ctx.stroke();

                // Draw text
                ctx.fillStyle = '#64748b';  // Slate-500
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(displayText, centerX, badgeY + badgeHeight / 2);
            });
            ctx.restore();
        }
    };

    coverageCharts.velocity?.destroy?.();

    coverageCharts.velocity = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 35
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 16,
                        generateLabels(chart) {
                            const defaultGenerator = (typeof Chart !== 'undefined' && Chart?.defaults?.plugins?.legend?.labels?.generateLabels)
                                ? Chart.defaults.plugins.legend.labels.generateLabels
                                : null;
                            const labels = defaultGenerator ? defaultGenerator(chart) : chart.data.datasets.map((dataset, idx) => ({
                                text: dataset.label || `Dataset ${idx + 1}`,
                                datasetIndex: idx,
                                fillStyle: dataset.borderColor || '#6b7280',
                                strokeStyle: dataset.borderColor || '#6b7280',
                                hidden: chart.isDatasetVisible(idx) === false
                            }));

                            return labels.map(label => {
                                const dataset = chart.data.datasets[label.datasetIndex];

                                // Special styling for line dataset
                                if (dataset.type === 'line') {
                                    return {
                                        text: 'Source throughput (rec/min)',
                                        datasetIndex: label.datasetIndex,
                                        hidden: label.hidden,
                                        lineWidth: 2,
                                        strokeStyle: '#0ea5e9',
                                        fillStyle: '#0ea5e9',
                                        pointStyle: 'line',
                                        fontColor: '#0ea5e9'
                                    };
                                }

                                // Keep bar datasets with default styling
                                const palette = Array.isArray(dataset.backgroundColor)
                                    ? dataset.backgroundColor
                                    : [dataset.backgroundColor];
                                const color = palette.find(color => color && color !== 'rgba(0,0,0,0)') || dataset.borderColor || '#6b7280';
                                return {
                                    ...label,
                                    fillStyle: color,
                                    strokeStyle: color
                                };
                            });
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        title(context) {
                            const idx = context[0].dataIndex;
                            const entry = timelineEntries[idx];
                            const run = entry.run;
                            const runThroughput = Number.isFinite(run.avgThroughput)
                                ? ` · Run avg ${Math.round(run.avgThroughput).toLocaleString()} rec/min`
                                : '';
                            const sources = run.activeSources;
                            const sourceLabel = sources ? ` · ${sources} source${sources === 1 ? '' : 's'}` : '';
                            return `${entry.runLabel || formatRunWindow(run.startTimestamp, run.endTimestamp)} • ${run.total.toLocaleString()} records${runThroughput}${sourceLabel}`;
                        },
                        label(context) {
                            if (context.dataset.type === 'line') {
                                const value = context.parsed.y;
                                if (!Number.isFinite(value)) return null;
                                return `${timelineEntries[context.dataIndex].source}: ${Math.round(value).toLocaleString()} rec/min`;
                            }
                            const entry = timelineEntries[context.dataIndex];
                            if (!Number.isFinite(context.parsed.y) || context.parsed.y === null) {
                                return null;
                            }
                            const total = entry.run.total || 0;
                            const value = context.parsed.y ?? 0;
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                            const throughput = Number.isFinite(entry.throughput)
                                ? ` · ${Math.round(entry.throughput).toLocaleString()} rec/min`
                                : '';
                            return `${context.dataset.label}: ${value.toLocaleString()} records (${percentage}%)${throughput}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: false,
                    grid: {
                        display: false
                    },
                    ticks: {
                        autoSkip: false,
                        maxRotation: 0,
                        callback(value) {
                            const label = typeof value === 'string' ? value : this.getLabelForValue(value);
                            return label ?? '';
                        }
                    }
                },
                y: {
                    stacked: false,
                    beginAtZero: true,
                    ticks: {
                        callback: value => value.toLocaleString()
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        callback: value => Math.round(value).toLocaleString()
                    },
                    title: {
                        display: true,
                        text: 'Records per minute',
                        font: { size: 12, weight: 600 }
                    }
                }
            }
        },
        plugins: [velocityRunLabelPlugin]
    });
}

function createSourceBalanceChart(metricsData) {
    const canvas = document.getElementById('sourceBalanceChart');
    if (!canvas) return;

    const { totals, grandTotal } = aggregateSourceTotals(metricsData.metrics);
    if (grandTotal === 0) {
        updateBalanceNarrative([], [], []);
        renderEmptyState(canvas, 'Source mix data is not yet available.');
        return;
    }

    const labels = Array.from(totals.keys()).sort((a, b) => {
        const idxA = SOURCE_ORDER.indexOf(a);
        const idxB = SOURCE_ORDER.indexOf(b);
        if (idxA === -1 && idxB === -1) return a.localeCompare(b);
        if (idxA === -1) return 1;
        if (idxB === -1) return -1;
        return idxA - idxB;
    });

    const targetMix = getSourceTargetShare();
    const actualPercentages = labels.map(label => ((totals.get(label) || 0) / grandTotal) * 100);
    const targetPercentages = labels.map(label => (targetMix[label] ?? 0) * 100);

    updateBalanceNarrative(labels, actualPercentages, targetPercentages);

    coverageCharts.balance?.destroy?.();

    coverageCharts.balance = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Actual',
                    data: actualPercentages,
                    backgroundColor: labels.map(label => getSourceColor(label, 0.85)),
                    borderColor: labels.map(label => getSourceColor(label)),
                    borderWidth: 1,
                    borderRadius: 6,
                    maxBarThickness: 28
                },
                {
                    label: 'Target',
                    data: targetPercentages,
                    backgroundColor: 'transparent',
                    borderColor: '#9ca3af',
                    borderWidth: 1.5,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 28
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 8,
                    bottom: 4,
                    left: 0,
                    right: 0
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 12,
                        boxHeight: 8
                    }
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            return `${context.dataset.label}: ${context.parsed.x.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: value => value + '%'
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function createQualityBulletChart(metricsData) {
    const canvas = document.getElementById('qualityBulletChart');
    if (!canvas) return;

    const qualityData = computeQualityBySource(metricsData.metrics);

    if (!qualityData.length) {
        updateQualityNarrative([]);
        renderEmptyState(canvas, 'Quality metrics are not yet available.');
        return;
    }

    updateQualityNarrative(qualityData);

    const labels = qualityData.map(item => item.source);
    const qualityPercentages = qualityData.map(item => (item.qualityRate ?? 0) * 100);
    const successPercentages = qualityData.map(item => (item.successRate ?? 0) * 100);

    const backgroundColors = qualityData.map(item => {
        const success = item.successRate ?? 0;
        if (success >= 0.95) return getSourceColor(item.source, 0.9);
        if (success >= 0.85) return getSourceColor(item.source, 0.75);
        if (success > 0) return getSourceColor(item.source, 0.6);
        return getSourceColor(item.source, 0.4);
    });

    const qualityTargetPlugin = {
        id: 'qualityTarget',
        afterDatasetsDraw(chart) {
            const { ctx, chartArea, scales } = chart;
            if (!chartArea || !scales?.x) return;
            const targetX = scales.x.getPixelForValue(QUALITY_TARGET * 100);
            ctx.save();
            ctx.setLineDash([6, 4]);
            ctx.strokeStyle = '#9ca3af';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(targetX, chartArea.top);
            ctx.lineTo(targetX, chartArea.bottom);
            ctx.stroke();
            ctx.restore();
        }
    };

    const context = canvas.getContext('2d');
    if (!context) {
        renderEmptyState(canvas, 'Quality visualization is unavailable in this viewport.');
        return;
    }

    coverageCharts.quality?.destroy?.();

    try {
        coverageCharts.quality = new Chart(context, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Quality Pass Rate',
                    data: qualityPercentages,
                    backgroundColor: backgroundColors,
                    borderColor: labels.map(label => getSourceColor(label)),
                    borderWidth: 1.2,
                    borderRadius: 8,
                    barThickness: 26,
                    maxBarThickness: 30
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const quality = context.parsed.x.toFixed(1);
                                const success = successPercentages[context.dataIndex];
                                const successText = Number.isFinite(success) && success > 0
                                    ? ` · Success ${success.toFixed(1)}%`
                                    : '';
                                return `${context.label}: Quality ${quality}%${successText}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => value + '%'
                        },
                        grid: {
                            color: '#f3f4f6'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            },
            plugins: [qualityTargetPlugin]
        });
    } catch (error) {
        console.error('Failed to render quality chart', error);
        renderEmptyState(canvas, 'Quality visualization is unavailable right now.');
    }
}

/**
 * Update coverage scorecard with aggregated metrics
 */
export function updateCoverageScorecard() {
    const metricsData = getMetrics();
    if (!metricsData || !metricsData.metrics) return;

    const aggregates = computePipelineAggregates(metricsData.metrics);
    const { totals, uniqueSources } = aggregateSourceTotals(metricsData.metrics);
    const activeSourceCount = uniqueSources.size || aggregates.activeSources || metricsData.metrics.length || 0;
    const avgQualityPercent = Number.isFinite(aggregates.avgQualityRate) ? aggregates.avgQualityRate * 100 : 0;
    const avgSuccessPercent = Number.isFinite(aggregates.avgSuccessRate) ? aggregates.avgSuccessRate * 100 : 0;
    const totalRecords = Number.isFinite(aggregates.totalRecords) ? aggregates.totalRecords : 0;

    const recordsEl = document.getElementById('coverage-total-records');
    const qualityEl = document.getElementById('coverage-quality-rate');
    const successEl = document.getElementById('coverage-success-rate');
    const sourcesEl = document.getElementById('coverage-sources');

    if (recordsEl) recordsEl.textContent = totalRecords.toLocaleString();
    if (qualityEl) qualityEl.textContent = avgQualityPercent.toFixed(1) + '%';
    if (successEl) successEl.textContent = avgSuccessPercent.toFixed(1) + '%';
    if (sourcesEl) sourcesEl.textContent = activeSourceCount;

    const maxRecords = Math.max(50000, totalRecords * 1.1);
    const recordsBar = document.getElementById('coverage-records-bar');
    const qualityBar = document.getElementById('coverage-quality-bar');
    const successBar = document.getElementById('coverage-success-bar');
    const sourcesBar = document.getElementById('coverage-sources-bar');

    if (recordsBar) {
        const recordsPct = Math.min((totalRecords / maxRecords) * 100, 100);
        setTimeout(() => recordsBar.style.width = recordsPct + '%', 100);
    }
    if (qualityBar) setTimeout(() => qualityBar.style.width = Math.min(avgQualityPercent, 100) + '%', 200);
    if (successBar) setTimeout(() => successBar.style.width = Math.min(avgSuccessPercent, 100) + '%', 300);
    if (sourcesBar) {
        const sourcesPct = (activeSourceCount / Math.max(SOURCE_ORDER.length, 1)) * 100;
        setTimeout(() => sourcesBar.style.width = Math.min(sourcesPct, 100) + '%', 400);
    }

    updateOverviewNarrative(aggregates, metricsData.metrics);
}

/**
 * Initialize redesigned coverage charts
 */
export function initCoverageCharts() {
    const metricsData = getMetrics();
    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        updateVelocityNarrative([]);
        updateBalanceNarrative([], [], []);
        updateQualityNarrative([]);
        renderPipelineEfficiency({ metrics: [] });
        renderStageAllocationChart(null);
        renderAcquisitionTreemap(null);
        renderIngestionTimeline(null);
        return;
    }

    createIngestionVelocityChart(metricsData);
    createSourceBalanceChart(metricsData);
    createQualityBulletChart(metricsData);
    renderPipelineEfficiency(metricsData);
    renderStageAllocationChart(metricsData);
    renderAcquisitionTreemap(metricsData);
    renderIngestionTimeline(metricsData);
}

/**
 * Initialize coverage metrics module
 * Loads source mix targets from JSON file with fallback to hardcoded values
 * Should be called during dashboard initialization, before rendering charts
 * @returns {Promise<void>}
 */
export async function initCoverageMetrics() {
    await loadSourceMixTargets();
    // Reset timeline filter to show all sources by default
    timelineFilteredSources.clear();
}

export function getSourceMixTargetsSnapshot() {
    return loadedSourceMixTargets || STATIC_SOURCE_MIX;
}

export function refreshDataSourceCharts(filteredMetrics = null) {
    const metricsData = filteredMetrics ? { metrics: filteredMetrics } : getMetrics();
    renderStageAllocationChart(metricsData);
    renderAcquisitionTreemap(metricsData);
    renderIngestionTimeline(metricsData);
}

function renderStageAllocationChart(metricsData) {
    const canvas = document.getElementById('sourceStageChart');
    if (!canvas) {
        return;
    }
    const wrapper = canvas.parentElement;
    if (!wrapper) return;

    const showEmpty = message => {
        canvas.style.display = 'none';
        let empty = wrapper.querySelector('.chart-empty-state');
        if (!empty) {
            empty = document.createElement('p');
            empty.className = 'chart-empty-state';
            wrapper.appendChild(empty);
        }
        empty.textContent = message;
    };

    const clearEmpty = () => {
        canvas.style.display = '';
        const empty = wrapper.querySelector('.chart-empty-state');
        if (empty) {
            empty.remove();
        }
    };

    if (coverageCharts.stageAllocation) {
        coverageCharts.stageAllocation.destroy();
        coverageCharts.stageAllocation = null;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        showEmpty('Stage allocation will appear after the next ingestion run.');
        return;
    }

    const stageSegments = buildStageSegments(metricsData.metrics);
    const sourceLabels = stageSegments.map(segment => segment.name);

    if (!sourceLabels.length) {
        showEmpty('Stage allocation will appear after the next ingestion run.');
        return;
    }

    clearEmpty();

    const datasets = [
        {
            label: 'Silver Dataset',
            data: stageSegments.map(segment => segment.segments.silver),
            backgroundColor: PIPELINE_STAGE_COLORS.written
        },
        {
            label: 'Quality Filters',
            data: stageSegments.map(segment => segment.segments.qualityLoss),
            backgroundColor: '#fbbf24'
        },
        {
            label: 'Extraction Drop',
            data: stageSegments.map(segment => segment.segments.extractionLoss),
            backgroundColor: PIPELINE_STAGE_COLORS.extracted
        },
        {
            label: 'Discovery Backlog',
            data: stageSegments.map(segment => segment.segments.discoveryBacklog),
            backgroundColor: PIPELINE_STAGE_COLORS.discovered
        }
    ];

    const context = canvas.getContext('2d');
    coverageCharts.stageAllocation = new Chart(context, {
        type: 'bar',
        data: {
            labels: sourceLabels,
            datasets
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: value => `${value}%`
                    },
                    title: {
                        display: true,
                        text: 'Record flow through pipeline stages (%)',
                        font: { size: 11, weight: 500 }
                    }
                },
                y: {
                    stacked: true,
                    title: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true }
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            const value = context.parsed.x?.toFixed(1) || 0;
                            return `${context.dataset.label}: ${value}%`;
                        }
                    }
                }
            }
        }
    });
}

function buildStageSegments(metrics = []) {
    const bySource = new Map();

    metrics.forEach(metric => {
        const source = normalizeSourceName(metric.source || 'Unknown');
        const pipelineType = metric.pipeline_type || 'unknown';

        if (!bySource.has(source)) {
            bySource.set(source, {
                discovered: 0,
                extracted: 0,
                received: 0,
                written: 0,
                filtered: 0,
                pipelineType: pipelineType
            });
        }

        const entry = bySource.get(source);

        // Unified metric mapping: normalize different pipeline types to common stages
        // Discovery stage: What was found/received at the very start
        let discovered = 0;
        let extracted = 0;

        if (pipelineType === 'web_scraping') {
            // Web scraping: URLs discovered → URLs fetched → Records extracted
            discovered = Number(metric.urls_discovered) || 0;
            extracted = Number(metric.urls_fetched) || 0;
        } else if (pipelineType === 'file_processing') {
            // File processing: Files processed → Records extracted → Quality filters
            // No URL discovery phase - start from extraction
            discovered = 0;
            extracted = Number(metric.records_extracted) || 0;
        } else if (pipelineType === 'stream_processing') {
            // Stream processing: Stream opened → Records received → Quality filters
            // No discovery or extraction phase - start from quality
            discovered = 0;
            extracted = 0;
        } else {
            // Unknown pipeline type: fallback to urls_discovered
            discovered = Number(metric.urls_discovered) || 0;
            extracted = Number(metric.records_extracted) || 0;
        }

        // Quality filter stage: What entered quality filters
        const written = Number(metric.records_written) || 0;
        const filtered = Object.values(metric.filter_breakdown || {}).reduce(
            (sum, value) => sum + (Number(value) || 0),
            0
        );
        const received = written + filtered;

        // Accumulate totals per source across all runs
        entry.discovered += discovered;
        entry.extracted += extracted;
        entry.received += received;
        entry.written += written;
        entry.filtered += filtered;
    });

    return Array.from(bySource.entries()).map(([name, entry]) => {
        // Calculate pipeline stage segments based on pipeline type
        let discoveryBacklog = 0;
        let extractionLoss = 0;
        let qualityLoss = 0;
        let silver = 0;
        let denominator = 1;

        if (entry.pipelineType === 'web_scraping') {
            // Web scraping: Discovery → Extraction → Quality → Silver
            discoveryBacklog = Math.max(entry.discovered - entry.extracted, 0);
            extractionLoss = Math.max(entry.extracted - entry.received, 0);
            qualityLoss = entry.filtered;
            silver = entry.written;
            denominator = entry.discovered > 0 ? entry.discovered : entry.received > 0 ? entry.received : 1;
        } else {
            // File processing and stream processing: Extraction → Quality → Silver
            // No discovery stage for these pipelines
            extractionLoss = Math.max(entry.extracted - entry.received, 0);
            qualityLoss = entry.filtered;
            silver = entry.written;
            // Use received as denominator (what entered the quality filters)
            denominator = entry.received > 0 ? entry.received : 1;
        }

        return {
            name,
            segments: {
                discoveryBacklog: (discoveryBacklog / denominator) * 100,
                extractionLoss: (extractionLoss / denominator) * 100,
                qualityLoss: (qualityLoss / denominator) * 100,
                silver: (silver / denominator) * 100
            }
        };
    }).sort((a, b) => b.segments.silver - a.segments.silver);
}

function renderAcquisitionTreemap(metricsData) {
    const container = document.getElementById('acquisitionTreemap');
    if (!container) {
        return;
    }

    container.innerHTML = '';
    const catalog = getSourceCatalog();

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        container.innerHTML = '<p class="chart-empty-state">Acquisition mix will appear after the next ingestion run.</p>';
        return;
    }

    const methodTotals = new Map();
    let totalRecords = 0;

    metricsData.metrics.forEach(metric => {
        const source = normalizeSourceName(metric.source || 'Unknown');
        const records = Number(metric.records_written) || 0;
        if (records <= 0) {
            return;
        }
        totalRecords += records;
        const method = catalog?.sources?.[source]?.acquisitionMethod || 'Uncategorized';
        methodTotals.set(method, (methodTotals.get(method) || 0) + records);
    });

    if (!totalRecords || methodTotals.size === 0) {
        container.innerHTML = '<p class="chart-empty-state">Acquisition mix will appear after the next ingestion run.</p>';
        return;
    }

    const nodes = Array.from(methodTotals.entries())
        .map(([method, records]) => ({
            method,
            records,
            share: (records / totalRecords) * 100
        }))
        .sort((a, b) => b.share - a.share);

    // Map to shorter display labels to prevent text cutoff
    const displayLabelMap = {
        'API + file snapshots': 'API + File',
        'Web crawler': 'Web Crawler',
        'Dataset API': 'Dataset API',
        'Partner file drop': 'File Drop',
        'Apify actor': 'Apify',
        'Uncategorized': 'Other'
    };

    nodes.forEach(node => {
        const div = document.createElement('div');
        div.className = 'treemap-node';
        div.setAttribute('role', 'listitem');
        div.setAttribute('aria-label', `${node.method} ${node.share.toFixed(1)} percent of volume`);
        div.style.background = ACQUISITION_COLOR_MAP[node.method] || ACQUISITION_COLOR_MAP.Uncategorized;
        div.style.flexBasis = `${Math.max(node.share * 4, 160)}px`;
        div.style.flexGrow = Math.max(node.share / 10, 1);
        div.title = `${node.method} · ${node.share.toFixed(1)}% (${node.records.toLocaleString()} records)`;

        // Use shorter label for display, full label in tooltip
        const displayLabel = displayLabelMap[node.method] || node.method;

        div.innerHTML = `
            <strong style="display: block; width: 100%; overflow-wrap: break-word; hyphens: auto;">${displayLabel}</strong>
            <span style="display: block; width: 100%;">${node.share.toFixed(1)}% · ${node.records.toLocaleString()} records</span>
        `;
        container.appendChild(div);
    });
}

// Module-level storage for timeline source filter state
let timelineFilteredSources = new Set();

/**
 * Toggle source visibility in timeline
 * @param {string} source - Source name to toggle
 */
function toggleTimelineSource(source) {
    if (!source) return;

    // Toggle source in filter set
    if (timelineFilteredSources.has(source)) {
        timelineFilteredSources.delete(source);
    } else {
        timelineFilteredSources.add(source);
    }

    // Re-render timeline with updated filter
    const metricsData = getMetrics();
    if (metricsData) {
        renderIngestionTimeline(metricsData);
    }
}

function renderIngestionTimeline(metricsData) {
    const container = document.getElementById('ingestionTimeline');
    const caption = document.getElementById('timeline-caption');
    const filterButtonsContainer = document.getElementById('timelineFilterButtons');
    if (!container) return;

    container.innerHTML = '';

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        if (caption) caption.textContent = 'Timeline will populate after the next orchestration run.';
        container.innerHTML = '<p class="chart-empty-state">Timeline will populate after the next orchestration run.</p>';
        if (filterButtonsContainer) filterButtonsContainer.innerHTML = '';
        return;
    }

    const runSeries = aggregateRunSeries(metricsData.metrics, 8);
    if (!runSeries.length) {
        if (caption) caption.textContent = 'Timeline will populate after the next orchestration run.';
        container.innerHTML = '<p class="chart-empty-state">Timeline will populate after the next orchestration run.</p>';
        if (filterButtonsContainer) filterButtonsContainer.innerHTML = '';
        return;
    }

    const runs = runSeries.slice(-8);
    const sources = Array.from(new Set(runs.flatMap(run => Object.keys(run.sources || {}))))
        .filter(Boolean);

    if (caption) {
        const latest = runs[runs.length - 1];
        const activeCount = timelineFilteredSources.size > 0 ? timelineFilteredSources.size : sources.length;
        caption.textContent = `Latest orchestration ${formatRunWindow(latest.startTimestamp, latest.endTimestamp)} · ${runs.length} runs shown`;
    }

    // Render filter toggle buttons
    if (filterButtonsContainer) {
        const orderedFilterSources = SOURCE_ORDER.filter(source => sources.includes(source))
            .concat(sources.filter(source => !SOURCE_ORDER.includes(source)));

        const buttonsHTML = orderedFilterSources.map(source => {
            const isActive = timelineFilteredSources.size === 0 || timelineFilteredSources.has(source);
            return `<button
                type="button"
                class="timeline-filter-btn ${isActive ? 'active' : ''}"
                data-source="${source}"
                aria-pressed="${isActive}"
                title="${isActive ? 'Hide' : 'Show'} ${source} in timeline">
                ${source}
            </button>`;
        }).join('');

        filterButtonsContainer.innerHTML = buttonsHTML;

        // Add click handlers to filter buttons
        filterButtonsContainer.querySelectorAll('.timeline-filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const source = btn.dataset.source;
                if (source) {
                    toggleTimelineSource(source);
                }
            });
        });
    }

    const orderedSources = SOURCE_ORDER.filter(source => sources.includes(source))
        .concat(sources.filter(source => !SOURCE_ORDER.includes(source)));

    orderedSources.forEach(source => {
        // Apply source filtering
        const isFiltered = timelineFilteredSources.size > 0 && !timelineFilteredSources.has(source);

        const column = document.createElement('div');
        column.className = 'timeline-column';
        column.dataset.source = source;

        // Hide column if filtered out
        if (isFiltered) {
            column.style.display = 'none';
        }

        const header = document.createElement('h4');
        header.textContent = source;
        column.appendChild(header);

        const segment = document.createElement('div');
        segment.className = 'timeline-segment';

        runs.forEach(run => {
            const button = document.createElement('button');
            button.type = 'button';
            const hasRun = (run.sources && run.sources[source]) ? run.sources[source] > 0 : false;
            button.dataset.active = hasRun.toString();
            button.dataset.source = source;
            button.setAttribute('aria-label', `${source} ${hasRun ? 'delivered' : 'idle'} · ${formatRunWindow(run.startTimestamp, run.endTimestamp)}`);
            const sr = document.createElement('span');
            sr.textContent = `${source} ${hasRun ? 'delivered' : 'idle'} · ${formatRunWindow(run.startTimestamp, run.endTimestamp)}`;
            button.appendChild(sr);
            segment.appendChild(button);
        });

        column.appendChild(segment);
        container.appendChild(column);
    });
}
