/**
 * Statistics Module
 * Updates hero statistics and story cards from metrics data
 */

import { getMetrics } from './data-service.js';
import { computePipelineAggregates } from './aggregates.js';
import { Logger } from '../utils/logger.js';

/**
 * Update statistics display from loaded metrics data
 * Updates hero stats cards and story mode cards
 */
export function updateStats() {
    const metricsData = getMetrics();

    if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
        // Empty state - set all to 0
        Logger.info('No metrics data - displaying empty state');

        // Update hero stats (null-safe)
        const elTotalRecords = document.getElementById('total-records');
        const elTotalSources = document.getElementById('total-sources');
        const elPipelineTypes = document.getElementById('pipeline-types') || document.getElementById('ingestion-types');
        const elCorpusRecords = document.getElementById('corpus-records');
        if (elTotalRecords) elTotalRecords.setAttribute('data-count', '0');
        if (elTotalSources) elTotalSources.setAttribute('data-count', '0');
        if (elPipelineTypes) elPipelineTypes.setAttribute('data-count', '0');
        if (elCorpusRecords) elCorpusRecords.setAttribute('data-count', '0');

        // Update story cards (null-safe)
        const elStoryRecords = document.getElementById('story-records');
        const elStoryQuality = document.getElementById('story-quality');
        const elStorySources = document.getElementById('story-sources');
        if (elStoryRecords) elStoryRecords.textContent = '0';
        if (elStoryQuality) elStoryQuality.textContent = '0';
        if (elStorySources) elStorySources.textContent = '0';

        return;
    }

    // Calculate real metrics
    const metrics = metricsData.metrics;
    const aggregates = computePipelineAggregates(metrics);
    const totalRecords = aggregates.totalRecords;
    const totalSources = new Set(metrics.map(m => (m.source || '').split('-')[0])).size;
    const avgQualityRate = aggregates.avgQualityRate * 100;

    // Count unique pipeline types
    const pipelineTypes = new Set(metrics.map(m => m.pipeline_type || 'unknown')).size;

    // Sum records_written across all runs for corpus-records KPI
    const corpusRecords = metrics.reduce((sum, m) => sum + (m.records_written || 0), 0);

    Logger.debug('Calculated stats', {
        totalRecords,
        totalSources,
        pipelineTypes,
        corpusRecords,
        avgQualityRate,
        activeSources: aggregates.activeSources,
        avgSuccessRate: aggregates.avgSuccessRate
    });

    // Update hero stats (null-safe — elements may be absent during HTML restructure)
    const elTotalRecords = document.getElementById('total-records');
    const elTotalSources = document.getElementById('total-sources');
    // Support both #pipeline-types (old) and #ingestion-types (new)
    const elPipelineTypes = document.getElementById('pipeline-types') || document.getElementById('ingestion-types');
    const elCorpusRecords = document.getElementById('corpus-records');
    if (elTotalRecords) elTotalRecords.setAttribute('data-count', totalRecords);
    if (elTotalSources) elTotalSources.setAttribute('data-count', totalSources);
    if (elPipelineTypes) elPipelineTypes.setAttribute('data-count', pipelineTypes);
    if (elCorpusRecords) elCorpusRecords.setAttribute('data-count', corpusRecords);

    // Update story cards (null-safe)
    const elStoryRecords = document.getElementById('story-records');
    const elStoryQuality = document.getElementById('story-quality');
    const elStorySources = document.getElementById('story-sources');
    if (elStoryRecords) elStoryRecords.textContent = totalRecords.toLocaleString();
    if (elStoryQuality) elStoryQuality.textContent = avgQualityRate.toFixed(1);
    if (elStorySources) elStorySources.textContent = totalSources;
}
