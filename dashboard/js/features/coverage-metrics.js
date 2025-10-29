/**
 * Coverage Metrics Module
 * Manages coverage scorecard and coverage overview charts
 */

import { getMetrics } from '../core/data-service.js';
import { computePipelineAggregates } from '../core/aggregates.js';
import { normalizeSourceName } from '../utils/formatters.js';

function getSourceColor(label) {
    if (label.includes('Wikipedia')) return '#3b82f6';
    if (label.includes('BBC')) return '#ef4444';
    if (label.includes('HuggingFace')) return '#10b981';
    if (label.includes('Språkbanken') || label.includes('Sprakbanken')) return '#f59e0b';
    return '#2563eb';
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

    // Update DOM
    const recordsEl = document.getElementById('coverage-total-records');
    const qualityEl = document.getElementById('coverage-quality-rate');
    const successEl = document.getElementById('coverage-success-rate');
    const sourcesEl = document.getElementById('coverage-sources');

    if (recordsEl) recordsEl.textContent = aggregates.totalRecords.toLocaleString();
    if (qualityEl) qualityEl.textContent = avgQualityPercent.toFixed(1) + '%';
    if (successEl) successEl.textContent = avgSuccessPercent.toFixed(1) + '%';
    if (sourcesEl) sourcesEl.textContent = aggregates.activeSources;

    // Update progress bars
    const maxRecords = 50000; // Target goal
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
        setTimeout(() => sourcesBar.style.width = sourcesPct + '%', 400);
    }
}

/**
 * Render coverage records bar chart
 */
export function createCoverageRecordsChart() {
    const metricsData = getMetrics();
    const ctx = document.getElementById('coverageRecordsChart');
    if (!ctx || !metricsData || !metricsData.metrics) return;

    const sourceMap = new Map();
    metricsData.metrics.forEach(m => {
        const records = m.records_written || 0;
        if (records <= 0) return;
        const name = normalizeSourceName(m.source);
        sourceMap.set(name, (sourceMap.get(name) || 0) + records);
    });

    const rows = Array.from(sourceMap.entries())
        .sort((a, b) => b[1] - a[1]);

    if (rows.length === 0) {
        const wrapper = ctx.parentElement;
        if (wrapper) {
            wrapper.innerHTML = '<p style="text-align:center;padding:2rem;color:#6b7280;">Coverage data is not yet available.</p>';
        }
        return;
    }

    const labels = rows.map(([label]) => label);
    const data = rows.map(([, value]) => value);
    const colors = labels.map(getSourceColor);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Records Written',
                data,
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
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = data.reduce((acc, value) => acc + value, 0);
                            const percentage = total > 0 ? ((context.parsed.x / total) * 100).toFixed(1) : '0.0';
                            return `${context.parsed.x.toLocaleString()} records (${percentage}%)`;
                        }
                    }
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
