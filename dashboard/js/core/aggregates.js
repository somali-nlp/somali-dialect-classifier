/**
 * Aggregate helper utilities for dashboard metrics.
 * Produces consistent rollups for executive/story views and analyst scorecards.
 */

import { Logger } from '../utils/logger.js';
import { normalizeSourceName } from '../utils/formatters.js';
import { loadFilterCatalog, extractLabels } from '../data/filter-catalog-loader.js';

const DEFAULT_SLA = {
    durationSeconds: 1800,
    recordsPerMinute: 1800,
    urlsPerSecond: 50,
    successRate: 0.95,
    retries: 20
};

function toNumber(value, fallback = 0) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
}

function clampRatio(value) {
    const num = toNumber(value, 0);
    if (!Number.isFinite(num)) {
        return 0;
    }
    if (num < 0) return 0;
    if (num > 1) return 1;
    return num;
}

function extractRecordsWritten(metric) {
    if (!metric) return 0;
    return toNumber(
        metric.records_written ??
        metric.legacy_metrics?.snapshot?.records_written,
        0
    );
}

function extractQualityRate(metric) {
    if (!metric) return 0;

    const direct = clampRatio(metric.quality_pass_rate);
    if (direct > 0) {
        return direct;
    }

    const legacyStats = metric.legacy_metrics?.statistics || {};
    const legacyRatio = clampRatio(legacyStats.quality_pass_rate);
    if (legacyRatio > 0) {
        return legacyRatio;
    }

    const quality = metric.legacy_metrics?.statistics?.quality ||
                    metric.legacy_metrics?.layered_metrics?.quality ||
                    {};
    const passed = toNumber(quality.records_passed_filters, null);
    const received = toNumber(quality.records_received, null);
    if (passed !== null && received) {
        return clampRatio(passed / received);
    }

    const snapshot = metric.legacy_metrics?.snapshot || {};
    const recordsWritten = toNumber(snapshot.records_written, null);
    const recordsFiltered = toNumber(snapshot.records_filtered, null);
    if (recordsWritten !== null && recordsFiltered !== null) {
        const total = recordsWritten + recordsFiltered;
        if (total > 0) {
            return clampRatio(recordsWritten / total);
        }
    }

    return 0;
}

function extractSuccessRate(metric) {
    if (!metric) return 0;

    const candidates = [
        metric.http_request_success_rate,
        metric.content_extraction_success_rate,
        metric.legacy_metrics?.statistics?.http_request_success_rate,
        metric.legacy_metrics?.statistics?.fetch_success_rate,
        metric.legacy_metrics?.statistics?.file_extraction_success_rate,
        metric.legacy_metrics?.statistics?.record_parsing_success_rate
    ];

    for (const candidate of candidates) {
        const value = clampRatio(candidate);
        if (value > 0) {
            return value;
        }
    }

    const snapshot = metric.legacy_metrics?.snapshot || {};
    const urlsFetched = toNumber(snapshot.urls_fetched ?? snapshot.files_processed, 0);
    const recordsWritten = extractRecordsWritten(metric);

    if (urlsFetched > 0) {
        return clampRatio(recordsWritten / urlsFetched);
    }

    if (recordsWritten > 0) {
        return 1;
    }

    return 0;
}

export function computePipelineAggregates(metrics = []) {
    if (!Array.isArray(metrics)) {
        Logger.warn('computePipelineAggregates called with non-array metrics');
        return {
            totalRecords: 0,
            avgQualityRate: 0,
            avgSuccessRate: 0,
            activeSources: 0
        };
    }

    let totalRecords = 0;
    let successNumerator = 0;
    let successDenominator = 0;
    let activeSources = 0;
    let totalCandidateRecords = 0;

    metrics.forEach(metric => {
        if (!metric) return;

        const recordsWritten = extractRecordsWritten(metric);
        const successRate = extractSuccessRate(metric);
        let rejectedCount = Object.values(metric.filter_breakdown || {}).reduce((sum, value) => sum + (Number(value) || 0), 0);
        const qualityRate = extractQualityRate(metric);

        if (rejectedCount === 0 && recordsWritten > 0 && qualityRate > 0 && qualityRate < 1) {
            const estimatedCandidates = Math.round(recordsWritten / qualityRate);
            const estimatedRejected = Math.max(estimatedCandidates - recordsWritten, 0);
            if (estimatedRejected > 0) {
                rejectedCount = estimatedRejected;
            }
        }

        totalRecords += recordsWritten;
        totalCandidateRecords += recordsWritten + rejectedCount;

        if (recordsWritten > 0) {
            activeSources += 1;
        }

        if (recordsWritten > 0) {
            successNumerator += successRate * recordsWritten;
            successDenominator += recordsWritten;
        }
    });

    const avgQualityRate = totalCandidateRecords > 0 ? totalRecords / totalCandidateRecords : 0;
    const avgSuccessRate = successDenominator > 0 ? successNumerator / successDenominator : 0;

    return {
        totalRecords,
        avgQualityRate,
        avgSuccessRate,
        activeSources
    };
}

// Fallback filter labels (used if dynamic catalog loading fails)
// DO NOT DELETE - This is the safety net for catalog loading failures
const FALLBACK_FILTER_LABELS = {
    // Length filters
    min_length_filter: 'Minimum length (50 chars)',

    // Language filters
    langid_filter: 'Language ID (non-Somali)',

    // Cleaning filters
    empty_after_cleaning: 'Empty after cleaning',

    // TikTok early-stage filters
    emoji_only_comment: 'Emoji-only comment',
    text_too_short_after_cleanup: 'Very short text (<3 chars)',

    // Dialect/topic filters
    dialect_heuristic_filter: 'Dialect heuristics',

    // Wikipedia-specific
    namespace_filter: 'Wikipedia namespace exclusion',

    // Future filters
    quality_score_filter: 'Quality score threshold',
    profanity_filter: 'Profanity detection',
    toxic_filter: 'Toxicity detection',
    duplicate_filter: 'Duplicate content',
    invalid_charset_filter: 'Invalid character encoding',
    encoding_filter: 'Encoding issues',
    stopword_filter: 'Stopword threshold',

    // Fallback
    unspecified_filter: 'Unspecified filter'
};

// Dynamic filter labels (loaded from catalog at runtime)
// Initialize with fallback to prevent null reference errors during async loading
export let FILTER_REASON_LABELS = { ...FALLBACK_FILTER_LABELS };

/**
 * Initialize filter labels from dynamic catalog.
 *
 * This function should be called once during app initialization
 * to load filter labels from the Python-generated catalog JSON.
 * Falls back to FALLBACK_FILTER_LABELS if loading fails.
 *
 * @returns {Promise<Object>} Loaded filter labels map
 */
export async function initializeFilterLabels() {
    try {
        const catalog = await loadFilterCatalog();
        FILTER_REASON_LABELS = extractLabels(catalog);
        Logger.info('Filter labels initialized from catalog');
        return FILTER_REASON_LABELS;
    } catch (error) {
        Logger.error('Failed to initialize filter labels from catalog:', error);
        FILTER_REASON_LABELS = { ...FALLBACK_FILTER_LABELS };
        Logger.warn('Using fallback filter labels');
        return FILTER_REASON_LABELS;
    }
}

/**
 * Get human-readable label for a filter key.
 *
 * Provides synchronous access to filter labels after initialization.
 * If labels haven't been initialized, falls back to FALLBACK_FILTER_LABELS.
 *
 * @param {string} filterKey - Filter identifier (e.g., "min_length_filter")
 * @returns {string} Human-readable label
 */
export function getFilterLabel(filterKey) {
    // Use loaded labels if available
    const labels = FILTER_REASON_LABELS || FALLBACK_FILTER_LABELS;

    // Return label if found, otherwise format the key
    if (labels[filterKey]) {
        return labels[filterKey];
    }

    // Fallback: Convert snake_case to Title Case
    return filterKey
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

// FILTER_LABELS export removed - FILTER_REASON_LABELS is now exported directly

export function computeQualityAnalytics(metrics = []) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        return {
            totalRecords: 0,
            totalRejected: 0,
            candidateRecords: 0,
            avgQualityRate: 0,
            avgDedupRate: 0,
            rejectionRate: 0,
            languageRejected: 0,
            languageShare: 0,
            perSource: [],
            trend: [],
            filterTotals: {},
            filterTrends: {},
            topFilter: null,
            familyTotals: {},
            latest: null,
            previous: null
        };
    }

    let totalRecords = 0;
    let totalRejected = 0;
    let qualityWeighted = 0;
    let qualityWeight = 0;
    let dedupWeighted = 0;
    let dedupWeight = 0;

    const filterTotals = new Map();
    const familyTotals = new Map();
    const sourceMap = new Map();
    const trendMap = new Map();
    const filterTrendMap = new Map();

    const languageReasons = new Set([
        'langid_filter',
        'language_filter',
        'non_somali_filter'
    ]);
    const lengthReasons = new Set([
        'min_length_filter'
    ]);
    const contentReasons = new Set([
        'emoji_only_comment',
        'text_too_short_after_cleanup',
        'empty_after_cleaning',
        'emoji_normalization_filter',
        'translation_guard_filter',
        'quality_score_filter',
        'metadata_harmonizer_filter',
        'article_extractor_filter'
    ]);
    const toxicityReasons = new Set([
        'toxic_filter',
        'toxicity_filter',
        'profanity_filter'
    ]);
    const dedupeReasons = new Set([
        'duplicate_filter',
        'near_duplicate_filter'
    ]);
    const manualReasons = new Set([
        'manual_review',
        'manual_override'
    ]);

    function getFamily(reason = '') {
        if (languageReasons.has(reason)) return 'Language';
        if (lengthReasons.has(reason)) return 'Length';
        if (contentReasons.has(reason)) return 'Content';
        if (toxicityReasons.has(reason)) return 'Toxicity';
        if (dedupeReasons.has(reason)) return 'Deduplication';
        if (manualReasons.has(reason)) return 'Manual';
        if (/lang/.test(reason)) return 'Language';
        if (/min_length|minimum.*length/.test(reason)) return 'Length';
        if (/emoji|short|empty|clean|quality|translation/.test(reason)) return 'Content';
        if (/tox|prof/.test(reason)) return 'Toxicity';
        if (/dup/.test(reason)) return 'Deduplication';
        if (/manual|override/.test(reason)) return 'Manual';
        return 'Other';
    }

    metrics.forEach(metric => {
        if (!metric) return;

        const records = Number(metric.records_written) || 0;
        const qualityRate = Number(metric.quality_pass_rate) || 0;
        const dedupRate = Number(metric.deduplication_rate) || 0;
        let filterBreakdown = metric.filter_breakdown || {};
        let rejected = Object.values(filterBreakdown).reduce((sum, value) => sum + (Number(value) || 0), 0);
        if (rejected === 0 && records > 0 && qualityRate > 0 && qualityRate < 1) {
            const estimatedCandidates = Math.round(records / qualityRate);
            const estimatedRejected = Math.max(estimatedCandidates - records, 0);
            if (estimatedRejected > 0) {
                rejected = estimatedRejected;
                filterBreakdown = { ...filterBreakdown };
                filterBreakdown.unspecified_filter = (filterBreakdown.unspecified_filter || 0) + estimatedRejected;
            }
        }
        const timestamp = metric.timestamp || null;
        const dateKey = timestamp ? new Date(timestamp).toISOString().slice(0, 10) : null;

        totalRecords += records;
        totalRejected += rejected;
        qualityWeighted += qualityRate * records;
        qualityWeight += records;
        dedupWeighted += dedupRate * records;
        dedupWeight += records;

        Object.entries(filterBreakdown).forEach(([reason, count]) => {
            const numeric = Number(count) || 0;
            if (numeric <= 0) return;
            filterTotals.set(reason, (filterTotals.get(reason) || 0) + numeric);
            const family = getFamily(reason);
            familyTotals.set(family, (familyTotals.get(family) || 0) + numeric);

            if (dateKey) {
                if (!filterTrendMap.has(reason)) {
                    filterTrendMap.set(reason, new Map());
                }
                const trendForReason = filterTrendMap.get(reason);
                trendForReason.set(dateKey, (trendForReason.get(dateKey) || 0) + numeric);
            }
        });

        const sourceName = normalizeSourceName(metric.source || 'Unknown');
        if (!sourceMap.has(sourceName)) {
            sourceMap.set(sourceName, {
                name: sourceName,
                records: 0,
                rejected: 0,
                weight: 0,
                dedupWeighted: 0,
                filters: {},
                families: new Map(),
                lastUpdated: null,
                lastUpdatedMs: null
            });
        }

        const sourceEntry = sourceMap.get(sourceName);
        sourceEntry.records += records;
        sourceEntry.rejected += rejected;
        sourceEntry.weight += records;
        sourceEntry.dedupWeighted += dedupRate * records;
        Object.entries(filterBreakdown).forEach(([reason, count]) => {
            const numeric = Number(count) || 0;
            if (numeric <= 0) return;
            sourceEntry.filters[reason] = (sourceEntry.filters[reason] || 0) + numeric;
            const family = getFamily(reason);
            sourceEntry.families.set(family, (sourceEntry.families.get(family) || 0) + numeric);
        });

        if (timestamp) {
            const ms = Date.parse(timestamp);
            if (!Number.isNaN(ms) && (!sourceEntry.lastUpdatedMs || ms > sourceEntry.lastUpdatedMs)) {
                sourceEntry.lastUpdated = timestamp;
                sourceEntry.lastUpdatedMs = ms;
            }
        }

        if (dateKey) {
            if (!trendMap.has(dateKey)) {
                trendMap.set(dateKey, {
                    qualityWeighted: 0,
                    records: 0
                });
            }
            const trendEntry = trendMap.get(dateKey);
            trendEntry.qualityWeighted += qualityRate * records;
            trendEntry.records += records;
        }
    });

    const perSource = Array.from(sourceMap.values()).map(entry => {
        const candidateTotal = entry.records + entry.rejected;
        const quality = candidateTotal > 0 ? entry.records / candidateTotal : 0;
        const dedupRate = entry.weight > 0 ? entry.dedupWeighted / entry.weight : 0;
        const share = totalRecords > 0 ? entry.records / totalRecords : 0;
        const rejectionRate = candidateTotal > 0 ? entry.rejected / candidateTotal : 0;

        const filterEntries = Object.entries(entry.filters)
            .filter(([, count]) => Number(count) > 0)
            .sort((a, b) => b[1] - a[1]);
        const topFilter = filterEntries.length
            ? {
                reason: filterEntries[0][0],
                count: filterEntries[0][1],
                percentage: entry.rejected > 0 ? (filterEntries[0][1] / entry.rejected) * 100 : 0
            }
            : null;

        return {
            name: entry.name,
            records: entry.records,
            share,
            quality,
            dedupRate,
            rejected: entry.rejected,
            rejectionRate,
            filters: entry.filters,
            familyBreakdown: Object.fromEntries(entry.families.entries()),
            topFilter,
            lastUpdated: entry.lastUpdated,
            lastUpdatedMs: entry.lastUpdatedMs
        };
    });

    const sortedTrend = Array.from(trendMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([date, value]) => ({
            date,
            quality: value.records > 0 ? value.qualityWeighted / value.records : 0,
            records: value.records
        }));

    const filterTotalsObj = Object.fromEntries(filterTotals.entries());
    const topFilterEntries = Object.entries(filterTotalsObj)
        .filter(([, count]) => Number(count) > 0)
        .sort((a, b) => b[1] - a[1]);
    const topFilter = topFilterEntries.length
        ? {
            reason: topFilterEntries[0][0],
            count: topFilterEntries[0][1],
            percentage: totalRejected > 0 ? (topFilterEntries[0][1] / totalRejected) * 100 : 0
        }
        : null;

    const combinedTotal = totalRecords + totalRejected;
    const avgQualityRate = combinedTotal > 0 ? totalRecords / combinedTotal : 0;
    const avgDedupRate = dedupWeight > 0 ? dedupWeighted / dedupWeight : 0;
    const rejectionRate = combinedTotal > 0 ? totalRejected / combinedTotal : 0;

    const languageRejected = Array.from(filterTotals.entries())
        .filter(([reason]) => getFamily(reason) === 'Language')
        .reduce((sum, [, count]) => sum + count, 0);
    const languageShare = totalRejected > 0 ? languageRejected / totalRejected : 0;

    const filterTrends = Object.fromEntries(
        Array.from(filterTrendMap.entries()).map(([reason, map]) => [
            reason,
            Array.from(map.entries())
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([date, value]) => ({ date, value }))
        ])
    );

    const latest = sortedTrend.length ? sortedTrend[sortedTrend.length - 1] : null;
    const previous = sortedTrend.length > 1 ? sortedTrend[sortedTrend.length - 2] : null;

    return {
        totalRecords,
        totalRejected,
        candidateRecords: combinedTotal,
        avgQualityRate,
        avgDedupRate,
        rejectionRate,
        languageRejected,
        languageShare,
        perSource,
        trend: sortedTrend,
        filterTotals: filterTotalsObj,
        filterTrends,
        topFilter,
        familyTotals: Object.fromEntries(familyTotals.entries()),
        latest,
        previous
    };
}

export function computePerformanceAnalytics(metrics = []) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        return {
            lastRun: null,
            previousRun: null,
            tiles: null,
            stages: [],
            perSource: [],
            timeline: [],
            errorMatrix: {},
            resources: {
                concurrency: null,
                queueDepth: null,
                bandwidth: null
            }
        };
    }

    const sorted = metrics
        .filter(Boolean)
        .sort((a, b) => {
            const timeA = a.timestamp ? Date.parse(a.timestamp) : 0;
            const timeB = b.timestamp ? Date.parse(b.timestamp) : 0;
            return timeB - timeA;
        });

    const groupedByTimestamp = new Map();
    sorted.forEach(metric => {
        const key = metric.timestamp || metric.run_id || 'latest';
        if (!groupedByTimestamp.has(key)) groupedByTimestamp.set(key, []);
        groupedByTimestamp.get(key).push(metric);
    });

    const [latestKey, previousKey] = Array.from(groupedByTimestamp.keys());
    const latestMetrics = groupedByTimestamp.get(latestKey) || [];
    const previousMetrics = previousKey ? groupedByTimestamp.get(previousKey) : [];

    const lastRun = summarizePerformanceRun(latestMetrics);
    const previousRun = summarizePerformanceRun(previousMetrics);

    const tiles = buildPerformanceTiles(lastRun, previousRun);
    const stages = lastRun.stages;
    const perSource = summarizePerformanceSources(latestMetrics);
    const timeline = buildPerformanceTimeline(metrics, 8);
    const errorMatrix = buildErrorMatrix(metrics);
    const resources = summarizeResources(latestMetrics);

    return {
        lastRun,
        previousRun,
        tiles,
        stages,
        perSource,
        timeline,
        errorMatrix,
        resources
    };
}

function summarizePerformanceRun(metrics = []) {
    if (!metrics.length) {
        return {
            durationSeconds: 0,
            recordsPerMinute: 0,
            urlsPerSecond: 0,
            retries: 0,
            parallelWorkers: null,
            stageTotals: {
                discover: 0,
                fetch: 0,
                extract: 0,
                quality: 0,
                write: 0
            },
            stages: []
        };
    }

    let durationSum = 0;
    let recordsPerMinuteSum = 0;
    let urlsPerSecondSum = 0;
    let retriesSum = 0;
    let workersSum = 0;
    let workersCount = 0;
    const stageTotals = {
        discover: 0,
        fetch: 0,
        extract: 0,
        quality: 0,
        write: 0
    };

    metrics.forEach(metric => {
        const duration = toNumber(metric.duration_seconds, 0);
        const rpm = toNumber(metric.records_per_minute, 0);
        const ups = toNumber(metric.urls_per_second, 0);
        durationSum += duration;
        recordsPerMinuteSum += rpm;
        urlsPerSecondSum += ups;
        retriesSum += extractRetryCount(metric);
        const workers = toNumber(metric.performance?.parallel_workers, null);
        if (Number.isFinite(workers) && workers > 0) {
            workersSum += workers;
            workersCount += 1;
        }

        const stageBreakdown = estimateStageDurations(metric);
        stageTotals.discover += stageBreakdown.discover;
        stageTotals.fetch += stageBreakdown.fetch;
        stageTotals.extract += stageBreakdown.extract;
        stageTotals.quality += stageBreakdown.quality;
        stageTotals.write += stageBreakdown.write;
    });

    const count = metrics.length;
    const averageDuration = durationSum / count;
    const averageRpm = recordsPerMinuteSum / count;
    const averageUps = urlsPerSecondSum / count;
    const averageWorkers = workersCount > 0 ? workersSum / workersCount : null;

    const stages = Object.keys(stageTotals).map(key => ({
        key,
        seconds: stageTotals[key],
        target: getStageTarget(key),
        variance: stageTotals[key] - getStageTarget(key)
    }));

    return {
        durationSeconds: averageDuration,
        recordsPerMinute: averageRpm,
        urlsPerSecond: averageUps,
        retries: retriesSum,
        parallelWorkers: averageWorkers,
        stageTotals,
        stages
    };
}

function buildPerformanceTiles(lastRun, previousRun) {
    if (!lastRun) return null;

    const prevDuration = previousRun?.durationSeconds ?? null;
    const prevRpm = previousRun?.recordsPerMinute ?? null;
    const prevUps = previousRun?.urlsPerSecond ?? null;
    const prevRetries = previousRun?.retries ?? null;

    return {
        duration: {
            value: lastRun.durationSeconds,
            delta: prevDuration !== null ? lastRun.durationSeconds - prevDuration : null,
            sla: DEFAULT_SLA.durationSeconds
        },
        rpm: {
            value: lastRun.recordsPerMinute,
            delta: prevRpm !== null ? lastRun.recordsPerMinute - prevRpm : null,
            sla: DEFAULT_SLA.recordsPerMinute
        },
        ups: {
            value: lastRun.urlsPerSecond,
            delta: prevUps !== null ? lastRun.urlsPerSecond - prevUps : null,
            sla: DEFAULT_SLA.urlsPerSecond
        },
        retries: {
            value: lastRun.retries,
            delta: prevRetries !== null ? lastRun.retries - prevRetries : null,
            sla: DEFAULT_SLA.retries
        }
    };
}

function summarizePerformanceSources(metrics = []) {
    const sourceMap = new Map();

    metrics.forEach(metric => {
        if (!metric) return;
        const source = normalizeSourceName(metric.source || 'Unknown');
        if (!sourceMap.has(source)) {
            sourceMap.set(source, {
                name: source,
                urlsPerSecond: 0,
                recordsPerMinute: 0,
                successRate: 0,
                durationSeconds: 0,
                retries: 0,
                count: 0
            });
        }
        const entry = sourceMap.get(source);
        entry.urlsPerSecond += toNumber(metric.urls_per_second, 0);
        entry.recordsPerMinute += toNumber(metric.records_per_minute, 0);
        entry.successRate += clampRatio(metric.http_request_success_rate);
        entry.durationSeconds += toNumber(metric.duration_seconds, 0);
        entry.retries += extractRetryCount(metric);
        entry.count += 1;
    });

    return Array.from(sourceMap.values()).map(entry => {
        const count = entry.count || 1;
        return {
            name: entry.name,
            urlsPerSecond: entry.urlsPerSecond / count,
            recordsPerMinute: entry.recordsPerMinute / count,
            successRate: entry.successRate / count,
            durationSeconds: entry.durationSeconds / count,
            retries: entry.retries,
            sla: {
                durationSeconds: DEFAULT_SLA.durationSeconds,
                successRate: DEFAULT_SLA.successRate,
                urlsPerSecond: DEFAULT_SLA.urlsPerSecond,
                recordsPerMinute: DEFAULT_SLA.recordsPerMinute,
                retries: DEFAULT_SLA.retries
            }
        };
    });
}

function buildPerformanceTimeline(metrics = [], limit = 8) {
    const runMap = new Map();
    metrics.forEach(metric => {
        if (!metric) return;
        const runId = (metric.run_id || metric.timestamp || '').split('_')[0];
        if (!runMap.has(runId)) {
            runMap.set(runId, {
                runId,
                timestamp: metric.timestamp || null,
                durationSeconds: 0,
                records: 0,
                retries: 0,
                sources: new Set()
            });
        }
        const entry = runMap.get(runId);
        entry.durationSeconds += toNumber(metric.duration_seconds, 0);
        entry.records += toNumber(metric.records_written, 0);
        entry.retries += extractRetryCount(metric);
        entry.sources.add(normalizeSourceName(metric.source || 'Unknown'));
        if (!entry.timestamp && metric.timestamp) {
            entry.timestamp = metric.timestamp;
        }
    });

    return Array.from(runMap.values())
        .sort((a, b) => {
            const timeA = a.timestamp ? Date.parse(a.timestamp) : 0;
            const timeB = b.timestamp ? Date.parse(b.timestamp) : 0;
            return timeB - timeA;
        })
        .slice(0, limit)
        .map(item => ({
            runId: item.runId,
            timestamp: item.timestamp,
            durationSeconds: item.durationSeconds,
            records: item.records,
            retries: item.retries,
            sources: Array.from(item.sources)
        }));
}

function buildErrorMatrix(metrics = []) {
    const matrix = {};

    metrics.forEach(metric => {
        if (!metric) return;
        const source = normalizeSourceName(metric.source || 'Unknown');
        if (!matrix[source]) {
            matrix[source] = { http: 0, extraction: 0, quality: 0 };
        }
        const urlsFetched = toNumber(metric.urls_fetched, toNumber(metric.urls_discovered, 0));
        const httpFailures = Math.max(0, Math.round((1 - clampRatio(metric.http_request_success_rate)) * urlsFetched));
        const extractionFailures = Math.max(0, Math.round((1 - clampRatio(metric.content_extraction_success_rate)) * toNumber(metric.urls_processed, urlsFetched)));
        const qualityFailures = Object.values(metric.filter_breakdown || {}).reduce((sum, value) => sum + (Number(value) || 0), 0);

        matrix[source].http += httpFailures;
        matrix[source].extraction += extractionFailures;
        matrix[source].quality += qualityFailures;
    });

    return matrix;
}

function summarizeResources(metrics = []) {
    let workersSum = 0;
    let workersCount = 0;
    let queueSum = 0;
    let queueCount = 0;
    let bandwidthSum = 0;
    let bandwidthCount = 0;

    metrics.forEach(metric => {
        const workers = toNumber(metric.performance?.parallel_workers, null);
        if (Number.isFinite(workers) && workers > 0) {
            workersSum += workers;
            workersCount += 1;
        }
        const queueDepth = toNumber(metric.performance?.queue_depth, null);
        if (Number.isFinite(queueDepth) && queueDepth >= 0) {
            queueSum += queueDepth;
            queueCount += 1;
        }
        const bandwidth = toNumber(metric.performance?.bandwidth_mbps, null);
        if (Number.isFinite(bandwidth) && bandwidth > 0) {
            bandwidthSum += bandwidth;
            bandwidthCount += 1;
        }
    });

    return {
        concurrency: workersCount > 0 ? workersSum / workersCount : null,
        queueDepth: queueCount > 0 ? queueSum / queueCount : null,
        bandwidth: bandwidthCount > 0 ? bandwidthSum / bandwidthCount : null
    };
}

function estimateStageDurations(metric) {
    const total = Math.max(toNumber(metric.duration_seconds, 0), 0);
    if (total <= 0) {
        return { discover: 0, fetch: 0, extract: 0, quality: 0, write: 0 };
    }

    const urlsFetched = Math.max(toNumber(metric.urls_fetched, 0), 0);
    const recordsWritten = Math.max(toNumber(metric.records_written, 0), 0);
    const ups = Math.max(toNumber(metric.urls_per_second, 0), 0);
    const rpm = Math.max(toNumber(metric.records_per_minute, 0), 0);

    let fetch = ups > 0 ? urlsFetched / ups : total * 0.25;
    let extract = rpm > 0 ? (recordsWritten / rpm) * 60 : total * 0.25;
    fetch = Math.min(fetch, total * 0.6);
    extract = Math.min(extract, total * 0.6);

    let remaining = total - fetch - extract;
    if (remaining < 0) {
        remaining = total * 0.2;
    }

    const failureRatio = Math.min(Math.max(1 - clampRatio(metric.quality_pass_rate), 0.1), 0.6);
    let quality = remaining * failureRatio;
    let write = remaining - quality;
    let discover = total - (fetch + extract + quality + write);
    if (discover < 0) {
        discover = total * 0.1;
        write = Math.max(0, total - (fetch + extract + quality + discover));
    }

    return { discover, fetch, extract, quality, write };
}

function getStageTarget(stageKey) {
    switch (stageKey) {
        case 'discover':
            return DEFAULT_SLA.durationSeconds * 0.1;
        case 'fetch':
            return DEFAULT_SLA.durationSeconds * 0.35;
        case 'extract':
            return DEFAULT_SLA.durationSeconds * 0.25;
        case 'quality':
            return DEFAULT_SLA.durationSeconds * 0.2;
        case 'write':
            return DEFAULT_SLA.durationSeconds * 0.1;
        default:
            return DEFAULT_SLA.durationSeconds * 0.2;
    }
}

function extractRetryCount(metric) {
    const direct = toNumber(metric.retries, null);
    if (Number.isFinite(direct)) return direct;
    const perf = metric.performance || {};
    const legacy = metric.legacy_metrics?.statistics || {};
    const candidates = [
        perf.retries,
        perf.retry_count,
        legacy.retry_count,
        legacy.retries
    ];
    for (const candidate of candidates) {
        const value = toNumber(candidate, null);
        if (Number.isFinite(value)) return value;
    }
    return 0;
}
