/**
 * Aggregate helper utilities for dashboard metrics.
 * Produces consistent rollups for executive/story views and analyst scorecards.
 */

import { Logger } from '../utils/logger.js';
import { normalizeSourceName } from '../utils/formatters.js';

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

export const FILTER_REASON_LABELS = {
    min_length_filter: 'Min-length',
    langid_filter: 'Language ID',
    empty_after_cleaning: 'Empty after cleaning',
    quality_score_filter: 'Quality score',
    profanity_filter: 'Profanity',
    toxic_filter: 'Toxicity',
    duplicate_filter: 'Duplicate',
    invalid_charset_filter: 'Invalid charset',
    encoding_filter: 'Encoding',
    stopword_filter: 'Stopword threshold',
    unspecified_filter: 'Unspecified filter'
};

export function computeQualityAnalytics(metrics = []) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        return {
            totalRecords: 0,
            totalRejected: 0,
            avgQualityRate: 0,
            avgDedupRate: 0,
            perSource: [],
            trend: [],
            filterTotals: {},
            topFilter: null
        };
    }

    let totalRecords = 0;
    let totalRejected = 0;
    let qualityWeighted = 0;
    let qualityWeight = 0;
    let dedupWeighted = 0;
    let dedupWeight = 0;

    const filterTotals = new Map();
    const sourceMap = new Map();
    const trendMap = new Map();

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

    return {
        totalRecords,
        totalRejected,
        avgQualityRate,
        avgDedupRate,
        perSource,
        trend: sortedTrend,
        filterTotals: filterTotalsObj,
        topFilter
    };
}
