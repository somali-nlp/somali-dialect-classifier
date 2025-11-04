/**
 * Charts Module
 * Creates and manages all Chart.js visualizations
 */

import { getMetrics } from './data-service.js';
import { normalizeSourceName, formatDate } from '../utils/formatters.js';
import { Logger } from '../utils/logger.js';
import { computeQualityAnalytics, FILTER_REASON_LABELS } from './aggregates.js';

function prepareCanvas(id) {
    const canvas = document.getElementById(id);
    if (!canvas) return null;
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    return canvas;
}

/**
 * Initialize all dashboard charts
 * Creates Chart.js instances for all visualizations
 */
export function initCharts() {
    const metricsData = getMetrics();
    if (!metricsData) return;

    // Chart.js defaults
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#6b7280';
    Chart.defaults.animation = false;
    if (Chart.defaults.plugins?.legend?.labels) {
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 12;
    }

    // Initialize all chart types
    createSourceTradeoffChart(metricsData);
    createQualityTrendChart(metricsData);
    createFilterParetoChart(metricsData);
    createQualityStabilityChart(metricsData);
    createPerformanceBulletChart(metricsData);
    createQualityVsSpeedChart(metricsData);
    createCumulativeTimelineChart(metricsData);
}

export function refreshQualityCharts(filteredMetrics = []) {
    const dataset = { metrics: filteredMetrics };
    createQualityTrendChart(dataset);
    createFilterParetoChart(dataset);
    createQualityStabilityChart(dataset);
}


/**
 * Create source tradeoff bubble chart
 * Plots records delivered vs quality rate with bubble size indicating avg length
 */
function createSourceTradeoffChart(metricsData) {
    const tradeoffCtx = prepareCanvas('sourceTradeoffChart');

    if (!tradeoffCtx) {
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        Logger.warn('Invalid or empty metrics data for source tradeoff chart');
        return;
    }

    const totalRecords = metricsData.metrics.reduce((sum, metric) => sum + (metric.records_written || 0), 0);
    if (totalRecords === 0) {
        tradeoffCtx.parentElement.innerHTML = '<p class="chart-empty-state">Source tradeoff data is not yet available.</p>';
        return;
    }

    const colorMap = metric => {
        const source = metric.source || '';
        if (source.includes('Wikipedia')) return '#3b82f6';
        if (source.includes('BBC')) return '#ef4444';
        if (source.includes('HuggingFace')) return '#10b981';
        if (source.includes('TikTok')) return '#ec4899';
        return '#f59e0b';  // Default for Språkbanken and others
    };

    const datasets = metricsData.metrics.map(metric => {
        const label = normalizeSourceName(metric.source);
        const records = metric.records_written || 0;
        const share = totalRecords > 0 ? (records / totalRecords) * 100 : 0;
        const qualityRate = (metric.quality_pass_rate || 0) * 100;
        const meanLength = metric.text_length_stats?.mean || 0;
        const bubbleRadius = Math.max(8, Math.min(24, Math.sqrt(meanLength) * 0.8));

        return {
            label,
            data: [{
                x: records,
                y: qualityRate,
                r: bubbleRadius,
                share,
                avgLength: meanLength
            }],
            backgroundColor: colorMap(metric) + 'CC',
            borderColor: colorMap(metric),
            borderWidth: 2,
            hoverBorderWidth: 3
        };
    });

    new Chart(tradeoffCtx, {
        type: 'bubble',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 14
                    }
                },
                tooltip: {
                    callbacks: {
                        title(context) {
                            return context[0].dataset.label;
                        },
                        label(context) {
                            const point = context.raw;
                            const records = context.parsed.x.toLocaleString();
                            const quality = context.parsed.y.toFixed(1) + '%';
                            const share = point.share.toFixed(1) + '% of mix';
                            const avgLength = Math.round(point.avgLength || 0).toLocaleString() + ' chars';
                            return [
                                `Records: ${records}`,
                                `Quality: ${quality}`,
                                `Share: ${share}`,
                                `Avg Length: ${avgLength}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Records Delivered',
                        font: { size: 12, weight: 600 }
                    },
                    ticks: {
                        callback: value => value >= 1000 ? (value / 1000).toFixed(0) + 'K' : value
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Quality Pass Rate',
                        font: { size: 12, weight: 600 }
                    },
                    ticks: {
                        callback: value => value + '%'
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                }
            }
        }
    });
}

function createQualityTrendChart(metricsData) {
    const trendCtx = prepareCanvas('qualityTrendChart');
    if (!trendCtx) {
        return;
    }

    const analytics = computeQualityAnalytics(metricsData?.metrics || []);
    const trend = analytics?.trend || [];
    if (!trend.length) {
        const wrapper = trendCtx.parentElement;
        if (wrapper) {
            wrapper.innerHTML = '<p class="chart-empty-state">Quality trend data is not yet available.</p>';
        }
        return;
    }

    const context = trendCtx.getContext('2d');
    const trendDataset = trend.map(entry => ({
        x: entry.date,
        y: (entry.quality || 0) * 100,
        records: entry.records || 0
    }));

    new Chart(context, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Quality Pass Rate',
                    data: trendDataset,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.15)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: trendDataset.length === 1 ? 5 : 3,
                    pointHoverRadius: 5,
                    fill: false
                },
                {
                    label: 'Target 85%',
                    data: trendDataset.map(point => ({ x: point.x, y: 85 })),
                    borderColor: '#9ca3af',
                    borderDash: [6, 6],
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            const value = context.parsed.y;
                            const records = context.raw?.records || 0;
                            return `${context.dataset.label}: ${value.toFixed(1)}% (${records.toLocaleString()} records)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        tooltipFormat: 'MMM dd, yyyy'
                    },
                    grid: {
                        color: '#f3f4f6'
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true
                    }
                },
                y: {
                    beginAtZero: true,
                    max: Math.max(100, Math.ceil(latestQuality / 10) * 10),
                    grid: {
                        color: '#f3f4f6'
                    },
                    ticks: {
                        callback: value => value + '%'
                    }
                }
            }
        }
    });
}

function createFilterParetoChart(metricsData) {
    const canvas = document.getElementById('filterParetoChart');
    if (!canvas) {
        return;
    }

    const analytics = computeQualityAnalytics(metricsData?.metrics || []);
    const filterTotals = analytics?.filterTotals || {};
    const totalRejected = analytics?.totalRejected || 0;

    const sortedFilters = Object.entries(filterTotals)
        .filter(([, count]) => Number(count) > 0)
        .sort((a, b) => b[1] - a[1]);

    if (!sortedFilters.length) {
        const wrapper = canvas.parentElement;
        if (wrapper) {
            wrapper.innerHTML = '<p class="chart-empty-state">Filter drilldown will appear after the next ingestion run.</p>';
        }
        return;
    }

    const labels = sortedFilters.map(([reason]) => FILTER_REASON_LABELS[reason] || reason.replace(/_/g, ' '));
    const counts = sortedFilters.map(([, count]) => count);
    const cumulative = counts.reduce((acc, value, index) => {
        const prev = index === 0 ? 0 : acc[index - 1];
        acc.push(prev + value);
        return acc;
    }, []);
    const cumulativePercent = cumulative.map(value => totalRejected > 0 ? (value / totalRejected) * 100 : 0);

    const filterSummary = sortedFilters.map(([reason, count], index) => ({
        reason,
        label: labels[index],
        count,
        share: totalRejected > 0 ? (count / totalRejected) * 100 : 0,
        cumulative: cumulativePercent[index]
    }));

    const chart = new Chart(canvas.getContext('2d'), {
        data: {
            labels,
            datasets: [
                {
                    type: 'bar',
                    label: 'Rejections',
                    data: counts,
                    backgroundColor: '#2563eb',
                    borderRadius: 6,
                    order: 1
                },
                {
                    type: 'line',
                    label: 'Cumulative',
                    data: cumulativePercent,
                    borderColor: '#f59e0b',
                    backgroundColor: '#f59e0b',
                    yAxisID: 'y1',
                    tension: 0.3,
                    order: 0,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            if (context.dataset.type === 'line') {
                                return `Cumulative: ${context.parsed.y.toFixed(1)}%`;
                            }
                            const count = context.parsed.y || 0;
                            const share = totalRejected > 0 ? (count / totalRejected) * 100 : 0;
                            return `${count.toLocaleString()} records (${share.toFixed(1)}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: '#f3f4f6' },
                    ticks: { autoSkip: false, maxRotation: 45, minRotation: 0 }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f9fafb' },
                    ticks: {
                        callback: value => value >= 1000 ? (value / 1000).toFixed(0) + 'K' : value
                    }
                },
                y1: {
                    beginAtZero: true,
                    suggestedMax: 100,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: {
                        callback: value => value + '%'
                    }
                }
            }
        }
    });

    canvas.onclick = event => {
        const points = chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, true);
        if (!points.length) return;
        const index = points[0].index;
        const detail = filterSummary[index];
        if (detail) {
            window.dispatchEvent(new CustomEvent('qualityFilterSelected', { detail }));
        }
    };

    window.dispatchEvent(new CustomEvent('qualityFilterSummary', {
        detail: {
            summary: filterSummary
        }
    }));
}

function createQualityStabilityChart(metricsData) {
    const canvas = document.getElementById('qualityStabilityChart');
    if (!canvas) {
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        canvas.parentElement.innerHTML = '<p class="chart-empty-state">Stability plot will appear after the next ingestion run.</p>';
        return;
    }

    const palette = ['#2563eb', '#ef4444', '#10b981', '#f59e0b', '#ec4899', '#6366f1'];
    const datasetMap = new Map();

    metricsData.metrics.forEach(metric => {
        if (!metric) return;
        const source = normalizeSourceName(metric.source || 'Unknown');
        const success = Number(metric.http_request_success_rate) * 100 || 0;
        const quality = Number(metric.quality_pass_rate) * 100 || 0;
        const timestamp = metric.timestamp ? formatDate(metric.timestamp) : 'N/A';
        if (!datasetMap.has(source)) datasetMap.set(source, []);
        datasetMap.get(source).push({ x: success, y: quality, runId: metric.run_id || '—', timestamp });
    });

    const datasets = Array.from(datasetMap.entries()).map(([label, data], index) => ({
        label,
        data,
        backgroundColor: palette[index % palette.length] + 'CC',
        borderColor: palette[index % palette.length],
        pointRadius: 5
    }));

    if (!datasets.length) {
        canvas.parentElement.innerHTML = '<p class="chart-empty-state">No stability data available.</p>';
        return;
    }

    new Chart(canvas.getContext('2d'), {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true } },
                tooltip: {
                    callbacks: {
                        label(context) {
                            const point = context.raw || {};
                            return [
                                `${context.dataset.label}`,
                                `Success: ${context.parsed.x.toFixed(1)}%`,
                                `Quality: ${context.parsed.y.toFixed(1)}%`,
                                `Run: ${point.runId || 'N/A'}`,
                                `Timestamp: ${point.timestamp || 'N/A'}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 105,
                    title: { display: true, text: 'Success Rate (%)' },
                    grid: { color: '#f3f4f6' }
                },
                y: {
                    beginAtZero: true,
                    max: 105,
                    title: { display: true, text: 'Quality Rate (%)' },
                    grid: { color: '#f3f4f6' }
                }
            }
        }
    });
}

/**
 * Create text length distribution bar chart
 */
function createTextLengthChart(metricsData) {
    const textLengthCtx = document.getElementById('textLengthChart');

    // Bug Fix #10: Comprehensive validation before processing
    if (!textLengthCtx) {
        Logger.warn('Chart container not found: textLengthChart');
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        Logger.warn('Invalid or empty metrics data for text length chart');
        return;
    }

    if (textLengthCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        // Bug Fix #9: Use consistent source name normalization
        const labels = metricsData.metrics.map(m => normalizeSourceName(m.source));
        // Bug Fix #4: Use text_length_stats.mean (normalized by data-service)
        const data = metricsData.metrics.map(m => m.text_length_stats?.mean || 0);
        const colors = metricsData.metrics.map(m => {
            if (m.source.includes('Wikipedia')) return '#3b82f6';
            if (m.source.includes('BBC')) return '#ef4444';
            if (m.source.includes('HuggingFace')) return '#10b981';
            return '#f59e0b';
        });

        new Chart(textLengthCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Avg Text Length (chars)',
                    data: data,
                    backgroundColor: colors,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' chars';
                            }
                        },
                        grid: {
                            color: '#f3f4f6'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
}

/**
 * Create deduplication polar area chart
 */
function createDeduplicationChart(metricsData) {
    const dedupCtx = document.getElementById('deduplicationChart');
    if (!dedupCtx) {
        Logger.warn('Chart container not found: deduplicationChart');
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        Logger.warn('Invalid or empty metrics data for deduplication chart');
        return;
    }

    const dedupMap = new Map();

    metricsData.metrics.forEach(metric => {
        if (!metric) return;

        const source = normalizeSourceName(metric.source);
        const breakdown = metric.filter_breakdown || {};

        const duplicateFiltered = Object.entries(breakdown).reduce((sum, [reason, count]) => {
            const normalizedReason = reason.toLowerCase();
            if (normalizedReason.includes('duplicate') || normalizedReason.includes('hash')) {
                return sum + count;
            }
            return sum;
        }, 0);

        const written = metric.records_written || 0;
        const totalConsidered = duplicateFiltered + written;
        if (totalConsidered === 0) return;

        const entry = dedupMap.get(source) || { duplicates: 0, total: 0 };
        entry.duplicates += duplicateFiltered;
        entry.total += totalConsidered;
        dedupMap.set(source, entry);
    });

    if (dedupMap.size === 0) {
        const wrapper = dedupCtx.parentElement;
        if (wrapper) {
            wrapper.innerHTML = '<p style="text-align:center;padding:2rem;color:#6b7280;">Deduplication data is not yet available.</p>';
        }
        return;
    }

    const labels = Array.from(dedupMap.keys());
    const values = labels.map(label => {
        const data = dedupMap.get(label);
        return data.total > 0 ? (data.duplicates / data.total) * 100 : 0;
    });

    new Chart(dedupCtx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                label: 'Deduplication Rate',
                data: values,
                backgroundColor: labels.map(label => {
                    if (label.includes('Wikipedia')) return 'rgba(59, 130, 246, 0.6)';
                    if (label.includes('BBC')) return 'rgba(239, 68, 68, 0.6)';
                    if (label.includes('HuggingFace')) return 'rgba(16, 185, 129, 0.6)';
                    if (label.includes('Språkbanken')) return 'rgba(245, 158, 11, 0.6)';
                    return 'rgba(107, 114, 128, 0.6)';
                }),
                borderColor: labels.map(label => {
                    if (label.includes('Wikipedia')) return '#3b82f6';
                    if (label.includes('BBC')) return '#ef4444';
                    if (label.includes('HuggingFace')) return '#10b981';
                    if (label.includes('Språkbanken')) return '#f59e0b';
                    return '#6b7280';
                }),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed.toFixed(1)}% duplicates removed`;
                        }
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create performance efficiency bullet chart
 */
function createPerformanceBulletChart(metricsData) {
    const bulletCtx = document.getElementById('performanceBulletChart');

    // Bug Fix #10: Comprehensive validation before processing
    if (!bulletCtx) {
        Logger.warn('Chart container not found: performanceBulletChart');
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        Logger.warn('Invalid or empty metrics data for performance bullet chart');
        return;
    }

    if (bulletCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        const metrics = metricsData.metrics;
        // Bug Fix #9: Use consistent source name normalization (with abbreviations for space)
        const sources = metrics.map(m => {
            const normalized = normalizeSourceName(m.source);
            return normalized.replace('HuggingFace', 'HF').replace('Språkbanken', 'Språk');
        });
        // Bug Fix #3/#8: Use flattened records_per_minute with safety checks
        const recordsPerMin = metrics.map(m => m.records_per_minute || 0);
        const qualityRates = metrics.map(m => {
            // Bug Fix #2: Use flattened quality_pass_rate (normalized by data-service)
            const quality = m.quality_pass_rate || 0;
            return quality * 100;
        });
        const maxRPM = Math.max(...recordsPerMin, 1); // Ensure at least 1 to avoid division by zero

        // Calculate composite performance score (60% speed + 40% quality)
        const performanceScores = metrics.map((m, i) => {
            const speedScore = (recordsPerMin[i] / maxRPM) * 100;
            const qualityScore = qualityRates[i];
            return (speedScore * 0.6 + qualityScore * 0.4);
        });

        // Create threshold arrays based on actual data length
        const numSources = sources.length;
        const poorThreshold = Array(numSources).fill(40);
        const fairThreshold = Array(numSources).fill(60);
        const goodThreshold = Array(numSources).fill(80);
        const excellentThreshold = Array(numSources).fill(100);

        new Chart(bulletCtx, {
            type: 'bar',
            data: {
                labels: sources,
                datasets: [
                    { label: 'Poor', data: poorThreshold, backgroundColor: 'rgba(239, 68, 68, 0.1)', borderWidth: 0, barPercentage: 1.0, order: 4 },
                    { label: 'Fair', data: fairThreshold, backgroundColor: 'rgba(251, 146, 60, 0.1)', borderWidth: 0, barPercentage: 1.0, order: 3 },
                    { label: 'Good', data: goodThreshold, backgroundColor: 'rgba(250, 204, 21, 0.1)', borderWidth: 0, barPercentage: 1.0, order: 2 },
                    { label: 'Excellent', data: excellentThreshold, backgroundColor: 'rgba(34, 197, 94, 0.1)', borderWidth: 0, barPercentage: 1.0, order: 1 },
                    { label: 'Performance Score', data: performanceScores, backgroundColor: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'], borderColor: '#1f2937', borderWidth: 2, barPercentage: 0.5, order: 0 }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: { display: true, text: 'Performance Efficiency Score', font: { size: 16, weight: 700 }, padding: { bottom: 20 } },
                    subtitle: { display: true, text: 'Composite: 60% processing speed + 40% quality rate', font: { size: 11 }, color: '#6b7280' },
                    legend: {
                        labels: {
                            filter: (item) => ['Performance Score', 'Excellent', 'Good'].includes(item.text),
                            usePointStyle: true,
                            padding: 10,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                if (ctx.dataset.label === 'Performance Score') {
                                    const idx = ctx.dataIndex;
                                    return [
                                        `Overall Score: ${ctx.parsed.x.toFixed(1)}%`,
                                        `Speed: ${recordsPerMin[idx].toLocaleString()} RPM`,
                                        `Quality: ${qualityRates[idx].toFixed(1)}%`,
                                        ctx.parsed.x >= 80 ? '✓ Exceeds target' : '⚠ Below 80% target'
                                    ];
                                }
                                return null;
                            }
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, max: 100, ticks: { callback: (v) => v + '%' }, grid: { color: 'rgba(0,0,0,0.05)' } },
                    y: { grid: { display: false } }
                }
            }
        });
    }
}

/**
 * Create quality vs speed scatter plot
 */
function createQualityVsSpeedChart(metricsData) {
    const scatterCtx = document.getElementById('qualityVsSpeedChart');

    // Bug Fix #10: Comprehensive validation before processing
    if (!scatterCtx) {
        Logger.warn('Chart container not found: qualityVsSpeedChart');
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        Logger.warn('Invalid or empty metrics data for quality vs speed chart');
        return;
    }

    if (scatterCtx && metricsData.metrics) {
        const datasets = metricsData.metrics.map(m => {
            // Bug Fix #9: Use consistent source name normalization (with abbreviations for space)
            const normalized = normalizeSourceName(m.source);
            const sourceShort = normalized.replace('HuggingFace', 'HF').replace('Språkbanken', 'Språk');
            let color = m.source.includes('Wikipedia') ? '#3b82f6' :
                        m.source.includes('BBC') ? '#ef4444' :
                        m.source.includes('HuggingFace') ? '#10b981' : '#f59e0b';
            const bubbleSize = Math.log10(m.records_written + 1) * 7 + 5;
            // Bug Fix #2: Use flattened quality_pass_rate (normalized by data-service)
            const qualityRate = m.quality_pass_rate || 0;

            return {
                label: `${sourceShort} (${m.records_written.toLocaleString()})`,
                data: [{
                    // Bug Fix #3/#8: Use flattened records_per_minute with safety checks
                    x: m.records_per_minute || 0,
                    y: qualityRate * 100,
                    r: bubbleSize
                }],
                backgroundColor: color + 'aa',
                borderColor: color,
                borderWidth: 2
            };
        });

        new Chart(scatterCtx, {
            type: 'bubble',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: { display: true, text: 'Quality vs. Speed Trade-off', font: { size: 16, weight: 700 }, padding: { bottom: 15 } },
                    subtitle: { display: true, text: 'Bubble size = data volume (records)', font: { size: 11 }, color: '#6b7280' },
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const point = ctx.raw;
                                return [
                                    `Speed: ${point.x.toLocaleString()} RPM`,
                                    `Quality: ${point.y.toFixed(1)}%`,
                                    point.x > 1000 && point.y > 95 ? '✓ High Performance & Quality' : '⚠ Optimization Opportunity'
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        beginAtZero: true,
                        title: { display: true, text: 'Processing Speed (records per minute)', font: { size: 12, weight: 600 } },
                        ticks: {
                            callback: (value) => Math.round(value).toLocaleString()
                        },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: 'Quality Pass Rate (%)', font: { size: 12, weight: 600 } },
                        ticks: { callback: (v) => v + '%' },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    }
                }
            }
        });
    }
}

/**
 * Create cumulative timeline stream graph
 */
function createCumulativeTimelineChart(metricsData) {
    const timelineCtx = document.getElementById('cumulativeTimelineChart');

    // Bug Fix #10: Comprehensive validation before processing
    if (!timelineCtx) {
        Logger.warn('Chart container not found: cumulativeTimelineChart');
        return;
    }

    if (!metricsData || !Array.isArray(metricsData.metrics) || metricsData.metrics.length === 0) {
        Logger.warn('Invalid or empty metrics data for cumulative timeline chart');
        return;
    }

    if (timelineCtx && metricsData.metrics) {
        const sorted = [...metricsData.metrics].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        const sources = [...new Set(sorted.map(m => m.source))];

        const datasets = sources.map(source => {
            // Bug Fix #9: Use consistent source name normalization (with abbreviations for space)
            const normalized = normalizeSourceName(source);
            const sourceShort = normalized.replace('HuggingFace', 'HF').replace('Språkbanken', 'Språk');
            let color = source.includes('Wikipedia') ? '#3b82f6' :
                        source.includes('BBC') ? '#ef4444' :
                        source.includes('HuggingFace') ? '#10b981' : '#f59e0b';

            let cumulative = 0;
            const data = sorted.map(m => {
                if (m.source === source) cumulative += m.records_written;
                return { x: new Date(m.timestamp), y: cumulative };
            });

            return {
                label: sourceShort,
                data: data,
                backgroundColor: color + '66',
                borderColor: color,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5
            };
        });

        new Chart(timelineCtx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: { display: true, text: 'Cumulative Data Collection Timeline', font: { size: 16, weight: 700 }, padding: { bottom: 15 } },
                    legend: { position: 'top', labels: { usePointStyle: true, padding: 12, font: { size: 11 } } },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: (items) => new Date(items[0].parsed.x).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} records`,
                            footer: (items) => {
                                const total = items.reduce((sum, item) => sum + item.parsed.y, 0);
                                return `Total: ${total.toLocaleString()} records`;
                            }
                        }
                    }
                },
                scales: {
                    x: { type: 'time', time: { unit: 'day', displayFormats: { day: 'MMM dd' } }, title: { display: true, text: 'Collection Date', font: { size: 12, weight: 600 } }, grid: { color: 'rgba(0,0,0,0.05)' } },
                    y: { beginAtZero: true, title: { display: true, text: 'Cumulative Records', font: { size: 12, weight: 600 } }, ticks: { callback: (v) => v >= 1000 ? (v/1000).toFixed(0) + 'K' : v }, grid: { color: 'rgba(0,0,0,0.05)' } }
                }
            }
        });
    }
}

/**
 * Download a chart as PNG image
 * @param {string} chartId - The ID of the canvas element
 */
export function downloadChart(chartId) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;

    const url = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `${chartId}-${Date.now()}.png`;
    link.href = url;
    link.click();
}
