/**
 * Coverage Metrics Module
 * Manages coverage scorecard and radial chart
 */

import { getMetrics } from '../core/data-service.js';

/**
 * Update coverage scorecard with aggregated metrics
 */
export function updateCoverageScorecard() {
    const metricsData = getMetrics();
    if (!metricsData || !metricsData.metrics) return;

    const aggregates = {
        totalRecords: metricsData.metrics.reduce((sum, m) => sum + (m.records_written || 0), 0),
        avgQuality: 0,
        avgSuccess: 0,
        activeSources: metricsData.metrics.filter(m => m.records_written > 0).length
    };

    // Calculate averages
    const validMetrics = metricsData.metrics.filter(m => m.records_written > 0);
    if (validMetrics.length > 0) {
        aggregates.avgQuality = validMetrics.reduce((sum, m) => {
            const rate = m.quality_pass_rate || 0;
            return sum + (rate * 100);
        }, 0) / validMetrics.length;

        aggregates.avgSuccess = validMetrics.reduce((sum, m) => {
            const success = m.http_request_success_rate || m.content_extraction_success_rate || 0;
            return sum + (success * 100);
        }, 0) / validMetrics.length;
    }

    // Update DOM
    const recordsEl = document.getElementById('coverage-total-records');
    const qualityEl = document.getElementById('coverage-quality-rate');
    const successEl = document.getElementById('coverage-success-rate');
    const sourcesEl = document.getElementById('coverage-sources');

    if (recordsEl) recordsEl.textContent = aggregates.totalRecords.toLocaleString();
    if (qualityEl) qualityEl.textContent = aggregates.avgQuality.toFixed(1) + '%';
    if (successEl) successEl.textContent = aggregates.avgSuccess.toFixed(1) + '%';
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
    if (qualityBar) setTimeout(() => qualityBar.style.width = aggregates.avgQuality + '%', 200);
    if (successBar) setTimeout(() => successBar.style.width = aggregates.avgSuccess + '%', 300);
    if (sourcesBar) {
        const sourcesPct = (aggregates.activeSources / 4) * 100;
        setTimeout(() => sourcesBar.style.width = sourcesPct + '%', 400);
    }
}

/**
 * Create coverage radial polar area chart
 */
export function createCoverageRadialChart() {
    const metricsData = getMetrics();
    const ctx = document.getElementById('coverageRadialChart');
    if (!ctx || !metricsData || !metricsData.metrics) return;

    const sourceMap = new Map();
    metricsData.metrics.forEach(m => {
        if (m.records_written > 0) {
            const name = m.source.replace(/-Somali|_Somali_c4-so|-somali/g, '').replace('Sprakbanken', 'Språkbanken').trim();
            sourceMap.set(name, (sourceMap.get(name) || 0) + m.records_written);
        }
    });

    const labels = Array.from(sourceMap.keys());
    const data = Array.from(sourceMap.values());
    const colors = labels.map(label => {
        if (label.includes('Wikipedia')) return '#3b82f6';
        if (label.includes('BBC')) return '#ef4444';
        if (label.includes('HuggingFace')) return '#10b981';
        return '#f59e0b';
    });

    new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.map(c => c + '80'),
                borderColor: colors,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                r: {
                    beginAtZero: true,
                    ticks: {
                        backdropColor: 'transparent',
                        font: { size: 11 }
                    },
                    grid: { color: '#e5e7eb' },
                    pointLabels: {
                        font: { size: 12, weight: '600' }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: { size: 12, weight: '500' }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed.r / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed.r.toLocaleString()} records (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}
