/**
 * Charts Module
 * Creates and manages all Chart.js visualizations
 */

import { getMetrics } from './data-service.js';

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

    // Initialize all chart types
    createSourceDistributionChart(metricsData);
    createQualityRateChart(metricsData);
    createSourceComparisonChart(metricsData);
    createTextLengthChart(metricsData);
    createDeduplicationChart();
    createPerformanceBulletChart(metricsData);
    createQualityVsSpeedChart(metricsData);
    createCumulativeTimelineChart(metricsData);
}

/**
 * Create source distribution donut chart
 */
function createSourceDistributionChart(metricsData) {
    const sourceDistCtx = document.getElementById('sourceDistributionChart');
    if (sourceDistCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        const sourceMap = new Map();
        metricsData.metrics.forEach(m => {
            const name = m.source.replace(/-Somali|_Somali_c4-so|-Somali/, '').replace('Sprakbanken', 'Språkbanken').replace('HuggingFace', 'HuggingFace');
            sourceMap.set(name, (sourceMap.get(name) || 0) + m.records_written);
        });

        const labels = Array.from(sourceMap.keys());
        const data = Array.from(sourceMap.values());
        const colors = labels.map(label => {
            if (label.includes('Wikipedia')) return '#3b82f6';
            if (label.includes('BBC')) return '#ef4444';
            if (label.includes('HuggingFace')) return '#10b981';
            return '#f59e0b';
        });

        new Chart(sourceDistCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
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
                            usePointStyle: true,
                            font: {
                                size: 12,
                                weight: '500'
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${context.parsed.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Create quality pass rate bar chart
 */
function createQualityRateChart(metricsData) {
    const qualityRateCtx = document.getElementById('qualityRateChart');
    if (qualityRateCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        const labels = metricsData.metrics.map(m => m.source.replace(/-Somali|_Somali_c4-so/, '').replace('Sprakbanken', 'Språkbanken'));
        const data = metricsData.metrics.map(m => {
            const qualityRate = m.pipeline_metrics?.quality_pass_rate || 0;
            return qualityRate * 100;
        });
        const colors = metricsData.metrics.map(m => {
            if (m.source.includes('Wikipedia')) return '#3b82f6';
            if (m.source.includes('BBC')) return '#ef4444';
            if (m.source.includes('HuggingFace')) return '#10b981';
            return '#f59e0b';
        });

        new Chart(qualityRateCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Quality Pass Rate',
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
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
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
 * Create source comparison horizontal bar chart
 */
function createSourceComparisonChart(metricsData) {
    const sourceCompCtx = document.getElementById('sourceComparisonChart');
    if (sourceCompCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        const labels = metricsData.metrics.map(m => m.source.replace(/-Somali|_Somali_c4-so/, '').replace('Sprakbanken', 'Språkbanken'));
        const data = metricsData.metrics.map(m => m.records_written);
        const colors = metricsData.metrics.map(m => {
            if (m.source.includes('Wikipedia')) return '#3b82f6';
            if (m.source.includes('BBC')) return '#ef4444';
            if (m.source.includes('HuggingFace')) return '#10b981';
            return '#f59e0b';
        });

        new Chart(sourceCompCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Records',
                    data: data,
                    backgroundColor: colors,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
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
}

/**
 * Create text length distribution bar chart
 */
function createTextLengthChart(metricsData) {
    const textLengthCtx = document.getElementById('textLengthChart');
    if (textLengthCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        const labels = metricsData.metrics.map(m => m.source.replace(/-Somali|_Somali_c4-so/, '').replace('Sprakbanken', 'Språkbanken'));
        const data = metricsData.metrics.map(m => m.quality?.avg_text_length || 0);
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
function createDeduplicationChart() {
    const dedupCtx = document.getElementById('deduplicationChart');
    if (dedupCtx) {
        new Chart(dedupCtx, {
            type: 'polarArea',
            data: {
                labels: ['Wikipedia', 'BBC Somali', 'HuggingFace', 'Språkbanken'],
                datasets: [{
                    label: 'Deduplication Rate',
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.6)',
                        'rgba(239, 68, 68, 0.6)',
                        'rgba(16, 185, 129, 0.6)',
                        'rgba(245, 158, 11, 0.6)'
                    ],
                    borderColor: [
                        '#3b82f6',
                        '#ef4444',
                        '#10b981',
                        '#f59e0b'
                    ],
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
                        max: 10,
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
}

/**
 * Create performance efficiency bullet chart
 */
function createPerformanceBulletChart(metricsData) {
    const bulletCtx = document.getElementById('performanceBulletChart');
    if (bulletCtx && metricsData.metrics && metricsData.metrics.length > 0) {
        const metrics = metricsData.metrics;
        const sources = metrics.map(m => m.source.replace(/-Somali|_Somali_c4-so|-Somali/, '').replace('HuggingFace', 'HF').replace('Sprakbanken', 'Språk'));
        const recordsPerMin = metrics.map(m => m.performance.records_per_minute);
        const qualityRates = metrics.map(m => {
            const quality = m.pipeline_metrics?.quality_pass_rate || 0;
            return quality * 100;
        });
        const maxRPM = Math.max(...recordsPerMin);

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
    if (scatterCtx && metricsData.metrics) {
        const datasets = metricsData.metrics.map(m => {
            const sourceShort = m.source.replace(/-Somali|_Somali_c4-so/, '').replace('Sprakbanken', 'Språk').replace('HuggingFace', 'HF');
            let color = m.source.includes('Wikipedia') ? '#3b82f6' :
                        m.source.includes('BBC') ? '#ef4444' :
                        m.source.includes('HuggingFace') ? '#10b981' : '#f59e0b';
            const bubbleSize = Math.log10(m.records_written + 1) * 7 + 5;
            const qualityRate = m.pipeline_metrics?.quality_pass_rate || 0;

            return {
                label: `${sourceShort} (${m.records_written.toLocaleString()})`,
                data: [{
                    x: m.performance.records_per_minute,
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
                    x: { type: 'logarithmic', title: { display: true, text: 'Processing Speed (RPM) - Log Scale', font: { size: 12, weight: 600 } }, ticks: { callback: (v) => v >= 1000 ? (v/1000).toFixed(0) + 'K' : v }, grid: { color: 'rgba(0,0,0,0.05)' } },
                    y: { beginAtZero: true, max: 100, title: { display: true, text: 'Quality Pass Rate (%)', font: { size: 12, weight: 600 } }, ticks: { callback: (v) => v + '%' }, grid: { color: 'rgba(0,0,0,0.05)' } }
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
    if (timelineCtx && metricsData.metrics) {
        const sorted = [...metricsData.metrics].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        const sources = [...new Set(sorted.map(m => m.source))];

        const datasets = sources.map(source => {
            const sourceShort = source.replace(/-Somali|_Somali_c4-so/, '').replace('Sprakbanken', 'Språk').replace('HuggingFace', 'HF');
            let color = source.includes('Wikipedia') ? '#3b82f6' :
                        source.includes('BBC') ? '#ef4444' :
                        source.includes('HuggingFace') ? '#10b981' : '#f59e0b';

            let cumulative = 0;
            const data = sorted.map(m => {
                if (m.source === source) cumulative += m.records_written;
                return { x: new Date(m.timestamp), y: cumulative };
            });

            return {
                label: `${sourceShort} (${cumulative.toLocaleString()})`,
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
                            label: (ctx) => `${ctx.dataset.label.split(' ')[0]}: ${ctx.parsed.y.toLocaleString()} records`,
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
