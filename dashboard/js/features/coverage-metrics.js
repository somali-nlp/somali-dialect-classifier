/**
 * Coverage Metrics Module
 * Manages coverage scorecard and redesigned processing summary visuals
 */

import { getMetrics } from '../core/data-service.js';
import { computePipelineAggregates } from '../core/aggregates.js';
import { normalizeSourceName, formatDate } from '../utils/formatters.js';

const SOURCE_ORDER = ['Wikipedia', 'BBC', 'HuggingFace MC4', 'Språkbanken'];

const SOURCE_COLOR_MAP = {
    'Wikipedia': '#3b82f6',
    'BBC': '#ef4444',
    'HuggingFace MC4': '#00A651',
    'Språkbanken': '#f59e0b'
};

const SOURCE_TARGET_SHARE = {
    'Wikipedia': 0.45,
    'BBC': 0.20,
    'HuggingFace MC4': 0.25,
    'Språkbanken': 0.10
};

const QUALITY_TARGET = 0.85;
const coverageCharts = {
    velocity: null,
    balance: null,
    quality: null
};

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

function formatShortDate(dateStr) {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function extractTimestamp(metric) {
    return metric.last_successful_write || metric.timestamp || metric.snapshot?.timestamp || null;
}

function aggregateDailyRecords(metrics, limit = 8) {
    const dayMap = new Map();

    metrics.forEach(metric => {
        const records = Number(metric.records_written) || 0;
        if (records <= 0) return;

        const timestamp = extractTimestamp(metric);
        if (!timestamp) return;

        const dateKey = timestamp.slice(0, 10);
        const source = normalizeSourceName(metric.source);
        if (!source) return;

        const dayEntry = dayMap.get(dateKey) || { total: 0, sources: {} };
        dayEntry.total += records;
        dayEntry.sources[source] = (dayEntry.sources[source] || 0) + records;
        dayMap.set(dateKey, dayEntry);
    });

    const sorted = Array.from(dayMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .slice(-limit);

    return sorted.map(([date, entry]) => ({
        date,
        total: entry.total,
        sources: entry.sources
    }));
}

function aggregateSourceTotals(metrics) {
    const totals = new Map();
    let grandTotal = 0;

    metrics.forEach(metric => {
        const records = Number(metric.records_written) || 0;
        if (records <= 0) return;
        const source = normalizeSourceName(metric.source);
        totals.set(source, (totals.get(source) || 0) + records);
        grandTotal += records;
    });

    return { totals, grandTotal };
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

function updateVelocityNarrative(dailyRecords) {
    const latestValueEl = document.getElementById('velocity-latest-total');
    const deltaEl = document.getElementById('velocity-delta');
    const callout = document.getElementById('velocity-callout');
    const footnote = document.getElementById('velocity-footnote');

    const latest = dailyRecords.length ? dailyRecords[dailyRecords.length - 1] : null;
    const previous = dailyRecords.length > 1 ? dailyRecords[dailyRecords.length - 2] : null;

    if (latestValueEl) {
        latestValueEl.textContent = latest ? latest.total.toLocaleString() : '0';
    }

    if (deltaEl) {
        resetCalloutClasses(deltaEl, 'positive', 'negative', 'neutral');
        if (!latest || !previous) {
            deltaEl.textContent = '–';
            deltaEl.classList.add('neutral');
        } else {
            const diff = latest.total - previous.total;
            if (diff === 0) {
                deltaEl.textContent = 'No change vs prior';
                deltaEl.classList.add('neutral');
            } else {
                const sign = diff > 0 ? '+' : '';
                deltaEl.textContent = `${sign}${diff.toLocaleString()} vs prior`;
                deltaEl.classList.add(diff > 0 ? 'positive' : 'negative');
            }
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
            const activeSources = Object.keys(latest.sources).length;
            const plural = activeSources === 1 ? '' : 's';
            footnote.textContent = `Latest update ${formatDate(latest.date)} · ${activeSources} active source${plural}.`;
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

    const avgQuality = qualityData.reduce((sum, item) => sum + (item.qualityRate ?? 0), 0) / qualityData.length;

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

    const dailyRecords = aggregateDailyRecords(metricsData.metrics);

    if (!dailyRecords.length) {
        updateVelocityNarrative([]);
        renderEmptyState(canvas, 'Ingestion runs have not produced records yet.');
        return;
    }

    updateVelocityNarrative(dailyRecords);

    const labels = dailyRecords.map(entry => formatShortDate(entry.date));
    const uniqueSources = new Set();
    dailyRecords.forEach(entry => {
        Object.keys(entry.sources).forEach(source => uniqueSources.add(source));
    });

    const orderedSources = SOURCE_ORDER
        .filter(source => uniqueSources.has(source))
        .concat(Array.from(uniqueSources).filter(source => !SOURCE_ORDER.includes(source)).sort());

    const datasets = orderedSources.map(source => ({
        label: source,
        data: dailyRecords.map(entry => entry.sources[source] || 0),
        backgroundColor: dailyRecords.map((_, idx) => {
            const isLatest = idx === dailyRecords.length - 1;
            return getSourceColor(source, isLatest ? 0.95 : 0.6);
        }),
        borderColor: getSourceColor(source),
        borderWidth: 1,
        borderRadius: 8,
        stack: 'records'
    }));

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
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        title(context) {
                            const idx = context[0].dataIndex;
                            const entry = dailyRecords[idx];
                            return `${formatDate(entry.date)} • ${entry.total.toLocaleString()} records`;
                        },
                        label(context) {
                            const total = dailyRecords[context.dataIndex].total;
                            const value = context.parsed.y ?? 0;
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                            return `${context.dataset.label}: ${value.toLocaleString()} records (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        callback: value => value.toLocaleString()
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                }
            }
        }
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

    const actualPercentages = labels.map(label => ((totals.get(label) || 0) / grandTotal) * 100);
    const targetPercentages = labels.map(label => (SOURCE_TARGET_SHARE[label] ?? 0) * 100);

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
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 16
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

    coverageCharts.quality?.destroy?.();

    coverageCharts.quality = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Quality Pass Rate',
                data: qualityPercentages,
                backgroundColor,
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
                            const successText = success ? ` · Success ${success.toFixed(1)}%` : '';
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
}

/**
 * Update coverage scorecard with aggregated metrics
 */
export function updateCoverageScorecard() {
    const metricsData = getMetrics();
    if (!metricsData || !metricsData.metrics) return;

    const aggregates = computePipelineAggregates(metricsData.metrics);
    const avgQualityPercent = aggregates.avgQualityRate * 100;
    const avgSuccessPercent = aggregates.avgSuccessRate * 100;

    const recordsEl = document.getElementById('coverage-total-records');
    const qualityEl = document.getElementById('coverage-quality-rate');
    const successEl = document.getElementById('coverage-success-rate');
    const sourcesEl = document.getElementById('coverage-sources');

    if (recordsEl) recordsEl.textContent = aggregates.totalRecords.toLocaleString();
    if (qualityEl) qualityEl.textContent = avgQualityPercent.toFixed(1) + '%';
    if (successEl) successEl.textContent = avgSuccessPercent.toFixed(1) + '%';
    if (sourcesEl) sourcesEl.textContent = aggregates.activeSources;

    const maxRecords = 50000;
    const recordsBar = document.getElementById('coverage-records-bar');
    const qualityBar = document.getElementById('coverage-quality-bar');
    const successBar = document.getElementById('coverage-success-bar');
    const sourcesBar = document.getElementById('coverage-sources-bar');

    if (recordsBar) {
        const recordsPct = Math.min((aggregates.totalRecords / maxRecords) * 100, 100);
        setTimeout(() => recordsBar.style.width = recordsPct + '%', 100);
    }
    if (qualityBar) setTimeout(() => qualityBar.style.width = Math.min(avgQualityPercent, 100) + '%', 200);
    if (successBar) setTimeout(() => successBar.style.width = Math.min(avgSuccessPercent, 100) + '%', 300);
    if (sourcesBar) {
        const sourcesPct = (aggregates.activeSources / 4) * 100;
        setTimeout(() => sourcesBar.style.width = Math.min(sourcesPct, 100) + '%', 400);
    }
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
        return;
    }

    createIngestionVelocityChart(metricsData);
    createSourceBalanceChart(metricsData);
    createQualityBulletChart(metricsData);
}
