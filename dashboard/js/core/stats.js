/**
 * Statistics Module
 * Updates hero statistics and story cards from metrics data
 */

import { getMetrics } from './data-service.js';

/**
 * Update statistics display from loaded metrics data
 * Updates hero stats cards and story mode cards
 */
export function updateStats() {
    const metricsData = getMetrics();

    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        // Empty state - set all to 0
        console.log('No metrics data - displaying empty state');

        // Update hero stats
        document.getElementById('total-records').setAttribute('data-count', '0');
        document.getElementById('total-sources').setAttribute('data-count', '0');
        document.getElementById('pipeline-types').setAttribute('data-count', '0');

        // Update story cards
        document.getElementById('story-records').textContent = '0';
        document.getElementById('story-quality').textContent = '0';
        document.getElementById('story-sources').textContent = '0';

        return;
    }

    // Calculate real metrics
    const metrics = metricsData.metrics;
    const totalRecords = metrics.reduce((sum, m) => sum + m.records_written, 0);
    const totalSources = new Set(metrics.map(m => m.source.split('-')[0])).size;

    // Calculate average quality pass rate (meaningful across all pipeline types)
    const avgQualityRate = metrics.reduce((sum, m) => {
        const quality = m.pipeline_metrics?.quality_pass_rate || 0;
        return sum + quality;
    }, 0) / metrics.length * 100;

    // Count unique pipeline types
    const pipelineTypes = new Set(metrics.map(m => m.pipeline_type || 'unknown')).size;

    console.log('Calculated stats:', { totalRecords, totalSources, pipelineTypes, avgQualityRate });

    // Update hero stats
    document.getElementById('total-records').setAttribute('data-count', totalRecords);
    document.getElementById('total-sources').setAttribute('data-count', totalSources);
    document.getElementById('pipeline-types').setAttribute('data-count', pipelineTypes);

    // Update story cards
    document.getElementById('story-records').textContent = totalRecords.toLocaleString();
    document.getElementById('story-quality').textContent = avgQualityRate.toFixed(1);
    document.getElementById('story-sources').textContent = totalSources;
}
