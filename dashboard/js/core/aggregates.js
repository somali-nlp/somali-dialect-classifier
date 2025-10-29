/**
 * Aggregate helper utilities for dashboard metrics.
 * Produces consistent rollups for executive/story views and analyst scorecards.
 */

import { Logger } from '../utils/logger.js';

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
    let qualityNumerator = 0;
    let qualityDenominator = 0;
    let successNumerator = 0;
    let successDenominator = 0;
    let activeSources = 0;

    metrics.forEach(metric => {
        if (!metric) return;

        const recordsWritten = extractRecordsWritten(metric);
        const qualityRate = extractQualityRate(metric);
        const successRate = extractSuccessRate(metric);

        totalRecords += recordsWritten;

        if (recordsWritten > 0) {
            activeSources += 1;
        }

        if (recordsWritten > 0) {
            qualityNumerator += qualityRate * recordsWritten;
            qualityDenominator += recordsWritten;
        }

        if (recordsWritten > 0) {
            successNumerator += successRate * recordsWritten;
            successDenominator += recordsWritten;
        }
    });

    const avgQualityRate = qualityDenominator > 0 ? qualityNumerator / qualityDenominator : 0;
    const avgSuccessRate = successDenominator > 0 ? successNumerator / successDenominator : 0;

    return {
        totalRecords,
        avgQualityRate,
        avgSuccessRate,
        activeSources
    };
}
