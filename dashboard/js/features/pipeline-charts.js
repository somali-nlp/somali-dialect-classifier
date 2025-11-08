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
 * Create Run Timeline Chart
 * Shows last N pipeline runs with duration and status
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} runHistory - Array of historical run objects
 * @param {number} limit - Number of runs to show (default: 10)
 * @returns {Chart} Chart.js instance
 */
export function createRunTimelineChart(canvasId, runHistory, limit = 10) {
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
    const durations = recentRuns.map(run => run.total_duration_seconds);
    const retries = recentRuns.map(run => run.retries || 0);

    // Color based on retry count
    const colors = retries.map(r => {
        if (r === 0) return '#00A651';       // Green
        if (r < 5) return '#FFC857';         // Yellow
        return '#FF6B35';                     // Red
    });

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
                label: 'Duration',
                data: durations,
                backgroundColor: colors,
                borderWidth: 0
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
                            const idx = context.dataIndex;
                            const duration = durations[idx];
                            const retry = retries[idx];
                            const run = recentRuns[idx];
                            return [
                                `Duration: ${formatDuration(duration)}`,
                                `Retries: ${retry}`,
                                `Records: ${run.total_records?.toLocaleString() || '—'}`,
                                `Throughput: ${run.throughput_rpm?.toLocaleString() || '—'} rpm`
                            ];
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
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Duration (seconds)',
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
 * Create Throughput Trend Chart
 * Line chart showing throughput over time with trend indicator
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} runHistory - Array of historical run objects
 * @param {number} limit - Number of runs to show (default: 10)
 * @returns {Chart} Chart.js instance
 */
export function createThroughputTrendChart(canvasId, runHistory, limit = 10) {
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

    // Calculate 7-day moving average (if enough data)
    const movingAvg = [];
    const window = Math.min(7, recentRuns.length);
    for (let i = 0; i < throughputs.length; i++) {
        const start = Math.max(0, i - window + 1);
        const slice = throughputs.slice(start, i + 1);
        const avg = slice.reduce((sum, val) => sum + val, 0) / slice.length;
        movingAvg.push(avg);
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
            datasets: [
                {
                    label: 'Throughput (rpm)',
                    data: throughputs,
                    borderColor: '#0176D3',
                    backgroundColor: 'rgba(1, 118, 211, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: '7-Day Moving Average',
                    data: movingAvg,
                    borderColor: '#9CA3AF',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0
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
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Run Date',
                        font: { size: 12, weight: '500' }
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
                    }
                }
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
