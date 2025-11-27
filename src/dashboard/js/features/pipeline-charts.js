/**
 * Pipeline Performance Charts Module
 *
 * Advanced Chart.js implementations for pipeline performance visualization:
 * - Stage Latency Waterfall (stacked horizontal bar)
 * - Source SLA Monitor (grouped bar with target lines)
 * - Run Timeline (timeline with bars)
 * - P95/P99 Latency Box Plot
 * - Quality Distribution Charts
 * - Filter Breakdown Heatmap
 *
 * @version 1.0
 * @author Frontend Team
 * @created 2025-11-08
 */

import { BRAND_COLORS, DATA_COLORS } from '../config.js';

/**
 * Format duration in seconds to human-readable string
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g., "2m 30s", "1h 15m")
 */
export function formatDuration(seconds) {
    if (!Number.isFinite(seconds)) return '—';

    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    }

    if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
    }

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
}

/**
 * Format number with commas and optional suffix
 * @param {number} num - Number to format
 * @param {string} suffix - Optional suffix (e.g., ' rpm', '%')
 * @returns {string} Formatted number
 */
export function formatNumber(num, suffix = '') {
    if (!Number.isFinite(num)) return '—';
    return num.toLocaleString() + suffix;
}

/**
 * Get color for SLA compliance status
 * @param {string} status - Status ('pass', 'warn', 'fail')
 * @returns {string} CSS color variable
 */
export function getSLAColor(status) {
    const colors = {
        pass: '#00A651',      // Green
        warn: '#FFC857',      // Yellow
        fail: '#FF6B35'       // Red
    };
    return colors[status] || colors.fail;
}

/**
 * Stage colors for waterfall chart (brand colors)
 */
export const STAGE_COLORS = {
    discovery: '#0176D3',    // Blue (primary brand color)
    fetch: '#00A651',        // Green
    extract: '#FFC857',      // Amber
    quality: '#9CA3AF',      // Gray
    write: '#6A4C93'         // Purple
};

/**
 * Create Stage Latency Waterfall Chart
 * Horizontal stacked bar showing time spent in each pipeline stage
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Object} stageDurations - Object with stage durations {discovery: 11.3, fetch: 828.8, ...}
 * @param {number} slaTarget - SLA target duration in seconds
 * @returns {Chart} Chart.js instance
 */
export function createStageWaterfallChart(canvasId, stageDurations, slaTarget = 1800) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas element #${canvasId} not found`);
        return null;
    }

    const ctx = canvas.getContext('2d');

    const stages = ['discovery', 'fetch', 'extract', 'quality', 'write'];
    const labels = stages.map(s => s.charAt(0).toUpperCase() + s.slice(1));
    const durations = stages.map(s => stageDurations[s] || 0);

    // Destroy existing chart if present
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Duration (seconds)',
                data: durations,
                backgroundColor: stages.map(s => STAGE_COLORS[s]),
                borderWidth: 0
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const stage = stages[context.dataIndex];
                            const duration = context.parsed.x;
                            const percentage = ((duration / durations.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                            return `${context.label}: ${formatDuration(duration)} (${percentage}%)`;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        slaLine: {
                            type: 'line',
                            xMin: slaTarget,
                            xMax: slaTarget,
                            borderColor: '#FF6B35',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: `SLA: ${formatDuration(slaTarget)}`,
                                enabled: true,
                                position: 'end',
                                backgroundColor: '#FF6B35',
                                color: '#FFFFFF',
                                padding: 4
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Duration (seconds)',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
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

/**
 * Create P95/P99 Latency Box Plot Chart
 * Shows latency distribution for each source
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} sourceMetrics - Array of source metrics with latency data
 * @returns {Chart} Chart.js instance
 */
export function createLatencyBoxPlot(canvasId, sourceMetrics) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas element #${canvasId} not found`);
        return null;
    }

    const ctx = canvas.getContext('2d');

    const sources = sourceMetrics.map(s => s.source);
    const p50Data = sourceMetrics.map(s => s.latency?.mean || 0);
    const p95Data = sourceMetrics.map(s => s.latency?.p95 || 0);
    const p99Data = sourceMetrics.map(s => s.latency?.p99 || 0);

    // Destroy existing chart if present
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sources,
            datasets: [
                {
                    label: 'P50 (Median)',
                    data: p50Data,
                    backgroundColor: '#0176D3',
                    stack: 'latency'
                },
                {
                    label: 'P95',
                    data: p95Data.map((val, idx) => val - p50Data[idx]),
                    backgroundColor: '#FFC857',
                    stack: 'latency'
                },
                {
                    label: 'P99',
                    data: p99Data.map((val, idx) => val - p95Data[idx]),
                    backgroundColor: '#FF6B35',
                    stack: 'latency'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const idx = context.dataIndex;
                            return [
                                `P50: ${p50Data[idx]}ms`,
                                `P95: ${p95Data[idx]}ms`,
                                `P99: ${p99Data[idx]}ms`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Source',
                        font: { size: 12, weight: '500' }
                    }
                },
                y: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Latency (ms)',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });
}

/**
 * Create Quality Pass Rate Distribution Chart
 * Horizontal bar chart showing quality pass rate per source
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} sourceMetrics - Array of source metrics with quality data
 * @returns {Chart} Chart.js instance
 */
export function createQualityDistributionChart(canvasId, sourceMetrics) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas element #${canvasId} not found`);
        return null;
    }

    const ctx = canvas.getContext('2d');

    // Map source names to clean display names
    const sourceMap = {
        'Wikipedia-Somali': 'Wikipedia',
        'BBC-Somali': 'BBC',
        'HuggingFace-Somali_c4-so': 'HuggingFace',
        'Sprakbanken-Somali': 'Språkbanken',
        'TikTok-Somali': 'TikTok'
    };

    const sources = sourceMetrics.map(s => sourceMap[s.source] || s.source);
    const qualityRates = sourceMetrics.map(s => (s.performance?.qualityRate || 0) * 100);

    // Color based on quality thresholds
    const colors = qualityRates.map(rate => {
        if (rate >= 90) return '#00A651'; // Green
        if (rate >= 70) return '#FFC857'; // Yellow
        return '#FF6B35';                  // Red
    });

    // Destroy existing chart if present
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sources,
            datasets: [{
                label: 'Quality Pass Rate',
                data: qualityRates,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const rate = context.parsed.x;
                            const status = rate >= 90 ? 'Excellent' : rate >= 70 ? 'Good' : 'Needs Attention';
                            return `${rate.toFixed(1)}% - ${status}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Quality Pass Rate (%)',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
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

/**
 * Create Run Timeline Chart (Enhanced Scatter Plot)
 * Scatter plot showing all historical pipeline runs on timeline
 * X-axis: timestamp, Y-axis: throughput (RPM)
 * Color-coded by success/failure or quality threshold
 * Bubble size indicates duration
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} runHistory - Array of historical run objects
 * @param {Object} options - Configuration options
 * @param {number} options.limit - Number of runs to show (default: 20)
 * @param {string} options.colorBy - Color by 'status' or 'quality' (default: 'status')
 * @param {number} options.qualityThreshold - Quality threshold for success (default: 0.70)
 * @returns {Chart} Chart.js instance
 */
export function createRunTimelineChart(canvasId, runHistory, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas element #${canvasId} not found`);
        return null;
    }

    const ctx = canvas.getContext('2d');

    // Default options (handle legacy limit parameter)
    let limit, colorBy, qualityThreshold;
    if (typeof options === 'number') {
        // Legacy: createRunTimelineChart(canvasId, runHistory, limit)
        limit = options;
        colorBy = 'status';
        qualityThreshold = 0.50;
    } else {
        limit = options.limit || 20;
        colorBy = options.colorBy || 'status';
        qualityThreshold = options.qualityThreshold || 0.50;
    }

    // Prepare data
    const recentRuns = runHistory.slice(0, limit).reverse();

    // Convert to scatter data points
    const dataPoints = recentRuns.map((run, index) => {
        const timestamp = new Date(run.timestamp).getTime();
        const throughput = run.throughput_rpm || 0;
        const duration = run.total_duration_seconds || 0;
        const quality = run.quality_pass_rate || 0;
        const retries = run.retries || 0;
        const errors = run.errors || 0;

        // Determine status - prioritize errors, then quality
        let status = 'success';
        if (quality < qualityThreshold) {
            status = 'warning';
        }
        if (errors > 0 || retries > 5) {
            status = 'error';
        }
        // Override: if quality is decent and no errors, it's success
        if (quality >= qualityThreshold && errors === 0 && retries <= 2) {
            status = 'success';
        }

        // Color mapping
        const colorMap = {
            success: '#00A651',   // Green
            warning: '#FFC857',   // Yellow
            error: '#FF6B35'      // Red
        };

        // Quality-based coloring (alternative)
        let color;
        if (colorBy === 'quality') {
            if (quality >= 0.90) color = '#00A651';      // Excellent
            else if (quality >= 0.70) color = '#0176D3'; // Good
            else if (quality >= 0.50) color = '#FFC857'; // Fair
            else color = '#FF6B35';                       // Poor
        } else {
            color = colorMap[status];
        }

        // Bubble size based on duration (normalize to 5-15 range)
        const minSize = 5;
        const maxSize = 15;
        const maxDuration = Math.max(...recentRuns.map(r => r.total_duration_seconds || 0));
        const minDuration = Math.min(...recentRuns.map(r => r.total_duration_seconds || 0));
        const normalizedSize = minSize + ((duration - minDuration) / (maxDuration - minDuration || 1)) * (maxSize - minSize);

        return {
            x: timestamp,
            y: throughput,
            r: normalizedSize,
            backgroundColor: color,
            borderColor: '#FFFFFF',
            borderWidth: 2,
            // Store metadata for tooltips
            run_id: run.run_id,
            duration,
            quality,
            retries,
            errors,
            sources: run.sources_processed,
            records: run.total_records,
            status
        };
    });

    // Destroy existing chart if present
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    // Calculate statistics for title
    const successCount = dataPoints.filter(p => p.status === 'success').length;
    const warningCount = dataPoints.filter(p => p.status === 'warning').length;
    const errorCount = dataPoints.filter(p => p.status === 'error').length;
    const successRate = ((successCount / dataPoints.length) * 100).toFixed(0);

    return new Chart(ctx, {
        type: 'bubble',
        data: {
            datasets: [{
                label: 'Pipeline Runs',
                data: dataPoints,
                backgroundColor: dataPoints.map(p => p.backgroundColor),
                borderColor: dataPoints.map(p => p.borderColor),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 10,
                    right: 15,
                    bottom: 10,
                    left: 15
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `Run Timeline - ${successRate}% success rate (${successCount}/${dataPoints.length} runs)`,
                    font: { size: 14, weight: '600' },
                    align: 'start',
                    padding: { top: 5, bottom: 20 }
                },
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        generateLabels: () => {
                            if (colorBy === 'status') {
                                return [
                                    { text: 'Success', fillStyle: '#00A651', strokeStyle: '#FFFFFF', lineWidth: 2 },
                                    { text: 'Warning', fillStyle: '#FFC857', strokeStyle: '#FFFFFF', lineWidth: 2 },
                                    { text: 'Error', fillStyle: '#FF6B35', strokeStyle: '#FFFFFF', lineWidth: 2 }
                                ];
                            } else {
                                return [
                                    { text: 'Excellent (≥90%)', fillStyle: '#00A651', strokeStyle: '#FFFFFF', lineWidth: 2 },
                                    { text: 'Good (70-89%)', fillStyle: '#0176D3', strokeStyle: '#FFFFFF', lineWidth: 2 },
                                    { text: 'Fair (50-69%)', fillStyle: '#FFC857', strokeStyle: '#FFFFFF', lineWidth: 2 },
                                    { text: 'Poor (<50%)', fillStyle: '#FF6B35', strokeStyle: '#FFFFFF', lineWidth: 2 }
                                ];
                            }
                        },
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 20,
                        boxWidth: 12,
                        boxHeight: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        title: (tooltipItems) => {
                            const point = tooltipItems[0].raw;
                            const date = new Date(point.x);
                            return date.toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        },
                        label: (context) => {
                            const point = context.raw;
                            return [
                                `Run ID: ${point.run_id}`,
                                `Throughput: ${point.y.toLocaleString()} rpm`,
                                `Duration: ${formatDuration(point.duration)}`,
                                `Quality: ${(point.quality * 100).toFixed(1)}%`,
                                `Records: ${point.records?.toLocaleString() || '—'}`,
                                `Sources: ${point.sources || '—'}`,
                                `Retries: ${point.retries}`,
                                `Errors: ${point.errors}`,
                                `Status: ${point.status.toUpperCase()}`
                            ];
                        }
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        },
                        tooltipFormat: 'MMM d, yyyy HH:mm'
                    },
                    title: {
                        display: true,
                        text: 'Run Date/Time',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Throughput (records/min)',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: (value) => value.toLocaleString()
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                intersect: true
            }
        }
    });
}

/**
 * Create Enhanced Throughput Trend Chart
 * Line chart showing throughput over time with:
 * - Actual throughput line (blue)
 * - 7-run moving average (gray dashed)
 * - Baseline target line (red dashed, if baselineMetrics provided)
 * - Trend arrows with percentage change in title
 * - Anomaly detection highlights (if baselineMetrics provided)
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} runHistory - Array of historical run objects
 * @param {Object} baselineMetrics - Optional baseline metrics from calculateBaselines()
 * @param {number} limit - Number of runs to show (default: 10)
 * @returns {Chart} Chart.js instance
 */
export function createThroughputTrendChart(canvasId, runHistory, baselineMetrics = null, limit = 10) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas element #${canvasId} not found`);
        return null;
    }

    const ctx = canvas.getContext('2d');

    const recentRuns = runHistory.slice(0, limit).reverse();
    const labels = recentRuns.map(run => {
        const date = new Date(run.timestamp);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const throughputs = recentRuns.map(run => run.throughput_rpm || 0);

    // Calculate 7-run moving average
    const movingAvg = [];
    const window = Math.min(7, recentRuns.length);
    for (let i = 0; i < throughputs.length; i++) {
        const start = Math.max(0, i - window + 1);
        const slice = throughputs.slice(start, i + 1);
        const avg = slice.reduce((sum, val) => sum + val, 0) / slice.length;
        movingAvg.push(avg);
    }

    // Calculate trend (first vs last)
    const firstThroughput = throughputs[0];
    const lastThroughput = throughputs[throughputs.length - 1];
    const trendPercent = firstThroughput > 0
        ? ((lastThroughput - firstThroughput) / firstThroughput * 100).toFixed(1)
        : 0;
    const trendDirection = parseFloat(trendPercent) > 0 ? 'up' : parseFloat(trendPercent) < 0 ? 'down' : 'stable';
    const trendIcon = trendDirection === 'up' ? '↑' : trendDirection === 'down' ? '↓' : '→';
    const trendColor = trendDirection === 'up' ? '#00A651' : trendDirection === 'down' ? '#FF6B35' : '#9CA3AF';

    // Baseline target line (if available)
    const baselineTarget = baselineMetrics?.throughput?.p50 || null;
    const baselineTargetData = baselineTarget ? new Array(labels.length).fill(baselineTarget) : null;

    // Detect anomalies (throughput < p50 * 0.8 or > p95 * 1.2)
    const anomalyPoints = [];
    if (baselineMetrics?.throughput) {
        const p50 = baselineMetrics.throughput.p50;
        const p95 = baselineMetrics.throughput.p95;

        throughputs.forEach((value, idx) => {
            if (value < p50 * 0.8 || value > p95 * 1.2) {
                anomalyPoints.push({
                    x: idx,
                    y: value,
                    r: 8
                });
            }
        });
    }

    // Build datasets
    const datasets = [
        {
            label: 'Throughput (rpm)',
            data: throughputs,
            borderColor: '#0176D3',
            backgroundColor: 'rgba(1, 118, 211, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#0176D3',
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2
        },
        {
            label: `${window}-Run Moving Average`,
            data: movingAvg,
            borderColor: '#9CA3AF',
            borderDash: [5, 5],
            fill: false,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 0
        }
    ];

    // Add baseline target if available
    if (baselineTargetData) {
        datasets.push({
            label: 'P50 Baseline',
            data: baselineTargetData,
            borderColor: '#FF6B35',
            borderDash: [10, 5],
            fill: false,
            tension: 0,
            pointRadius: 0,
            pointHoverRadius: 0,
            borderWidth: 2
        });
    }

    // Add anomaly points if detected
    if (anomalyPoints.length > 0) {
        datasets.push({
            label: 'Anomalies',
            data: anomalyPoints,
            type: 'bubble',
            backgroundColor: '#FF6B35',
            borderColor: '#FFFFFF',
            borderWidth: 2
        });
    }

    // Destroy existing chart if present
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Throughput Trend: ${trendIcon} ${Math.abs(trendPercent)}% over ${labels.length} runs`,
                    color: trendColor,
                    font: { size: 14, weight: '600' },
                    align: 'start',
                    padding: { bottom: 10 }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        filter: (item) => {
                            // Hide anomalies legend if no anomalies
                            return !(item.text === 'Anomalies' && anomalyPoints.length === 0);
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;

                            if (label.includes('Moving Average')) {
                                return `${label}: ${value.toLocaleString(undefined, {maximumFractionDigits: 0})} rpm`;
                            }

                            if (label === 'Throughput (rpm)') {
                                const runIndex = context.dataIndex;
                                const run = recentRuns[runIndex];

                                let status = '';
                                if (baselineMetrics?.throughput) {
                                    const p50 = baselineMetrics.throughput.p50;
                                    if (value >= p50) {
                                        status = ' (Above median ✓)';
                                    } else if (value >= p50 * 0.8) {
                                        status = ' (Near median)';
                                    } else {
                                        status = ' (Below median ⚠)';
                                    }
                                }

                                return [
                                    `${label}: ${value.toLocaleString(undefined, {maximumFractionDigits: 0})} rpm${status}`,
                                    `Duration: ${formatDuration(run.total_duration_seconds)}`,
                                    `Quality: ${(run.quality_pass_rate * 100).toFixed(1)}%`
                                ];
                            }

                            if (label === 'P50 Baseline') {
                                return `${label}: ${value.toLocaleString(undefined, {maximumFractionDigits: 0})} rpm (median target)`;
                            }

                            if (label === 'Anomalies') {
                                return `⚠ Anomaly detected: ${value.toLocaleString(undefined, {maximumFractionDigits: 0})} rpm`;
                            }

                            return `${label}: ${value}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Run Date',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Records per Minute',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: (value) => value.toLocaleString()
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

/**
 * Create Bandwidth Efficiency Scatter Plot
 * Shows bytes downloaded vs records written for each source
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} sourceMetrics - Array of source metrics
 * @returns {Chart} Chart.js instance
 */
export function createBandwidthEfficiencyChart(canvasId, sourceMetrics) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas element #${canvasId} not found`);
        return null;
    }

    const ctx = canvas.getContext('2d');

    const data = sourceMetrics.map(s => ({
        x: (s.latestRunData?.bytes_downloaded || 0) / 1024 / 1024, // Convert to MB
        y: s.latestRunData?.records || 0,
        label: s.source
    }));

    // Destroy existing chart if present
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    return new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Sources',
                data,
                backgroundColor: '#0176D3',
                pointRadius: 8,
                pointHoverRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const point = context.raw;
                            const efficiency = point.x > 0 ? (point.y / point.x).toFixed(2) : 0;
                            return [
                                point.label,
                                `Downloaded: ${point.x.toFixed(2)} MB`,
                                `Records: ${point.y.toLocaleString()}`,
                                `Efficiency: ${efficiency} records/MB`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Data Downloaded (MB)',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Records Produced',
                        font: { size: 12, weight: '500' }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });
}

/**
 * Destroy all charts (cleanup utility)
 * @param {Array<string>} canvasIds - Array of canvas IDs to destroy
 */
export function destroyCharts(canvasIds) {
    canvasIds.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas) {
            const chart = Chart.getChart(canvas);
            if (chart) {
                chart.destroy();
            }
        }
    });
}
