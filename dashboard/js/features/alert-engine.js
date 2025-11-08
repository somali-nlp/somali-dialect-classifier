/**
 * Pipeline Alert Engine
 *
 * Dashboard-side alert generation logic that analyzes pipeline performance
 * against SLA targets and generates actionable alerts automatically.
 *
 * Features:
 * - SLA breach detection (throughput, duration, quality)
 * - Anomaly detection (statistical outliers)
 * - Alert deduplication
 * - Severity classification (high, medium, low)
 * - Actionable recommendations
 *
 * @version 1.0
 * @author Frontend Team
 * @created 2025-11-08
 */

import { pipelineDataService } from '../core/pipeline-data-service.js';
import { formatDuration, formatNumber } from './pipeline-charts.js';

/**
 * Alert Engine Class
 * Generates alerts from pipeline analytics and SLA targets
 */
export class AlertEngine {
    constructor(dataService = pipelineDataService) {
        this.dataService = dataService;
        this.severityWeights = { high: 1, medium: 2, low: 3 };
    }

    /**
     * Generate all alerts from current pipeline analytics
     * @returns {Promise<Array>} Array of alert objects sorted by severity
     */
    async generateAlerts() {
        try {
            const analytics = await this.dataService.getAggregatedPipelineAnalytics();
            const slaTargets = analytics.slaTargets;
            const preGeneratedAlerts = analytics.alerts;

            const generatedAlerts = [];

            // Check global throughput SLA
            const globalThroughputAlert = this.checkGlobalThroughputSLA(
                analytics.global,
                slaTargets.global_targets
            );
            if (globalThroughputAlert) {
                generatedAlerts.push(globalThroughputAlert);
            }

            // Check global duration SLA
            const globalDurationAlert = this.checkGlobalDurationSLA(
                analytics.global,
                slaTargets.global_targets
            );
            if (globalDurationAlert) {
                generatedAlerts.push(globalDurationAlert);
            }

            // Check global quality SLA
            const globalQualityAlert = this.checkGlobalQualitySLA(
                analytics.global,
                slaTargets.global_targets
            );
            if (globalQualityAlert) {
                generatedAlerts.push(globalQualityAlert);
            }

            // Check per-source SLAs
            analytics.perSource.forEach(source => {
                const sourceTarget = slaTargets.per_source_targets[source.source];
                if (!sourceTarget) return;

                // Duration SLA
                const durationAlert = this.checkSourceDurationSLA(source, sourceTarget);
                if (durationAlert) {
                    generatedAlerts.push(durationAlert);
                }

                // Throughput SLA
                const throughputAlert = this.checkSourceThroughputSLA(source, sourceTarget);
                if (throughputAlert) {
                    generatedAlerts.push(throughputAlert);
                }

                // Quality SLA
                const qualityAlert = this.checkSourceQualitySLA(source, sourceTarget);
                if (qualityAlert) {
                    generatedAlerts.push(qualityAlert);
                }

                // P95 Latency SLA
                const latencyAlert = this.checkSourceLatencySLA(source, sourceTarget);
                if (latencyAlert) {
                    generatedAlerts.push(latencyAlert);
                }
            });

            // Check retry budget
            const retryAlert = this.checkRetryBudget(analytics.global, analytics.perSource);
            if (retryAlert) {
                generatedAlerts.push(retryAlert);
            }

            // Check for anomalies (if historical data available)
            if (analytics.runHistory.length >= 5) {
                const anomalies = this.detectAnomalies(
                    analytics.runHistory[0],
                    analytics.runHistory.slice(1, 6)
                );
                generatedAlerts.push(...anomalies);
            }

            // Merge with pre-generated alerts (deduplicate)
            const mergedAlerts = this.mergeAlerts(generatedAlerts, preGeneratedAlerts);

            // Sort by severity (high > medium > low)
            return mergedAlerts.sort((a, b) =>
                this.severityWeights[a.severity] - this.severityWeights[b.severity]
            );

        } catch (error) {
            console.error('AlertEngine: Error generating alerts:', error);
            return [];
        }
    }

    /**
     * Check global throughput SLA
     * @param {Object} global - Global metrics
     * @param {Object} targets - Global SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkGlobalThroughputSLA(global, targets) {
        const actual = global.avgThroughput;
        const target = targets.min_throughput_rpm;

        if (!target || actual >= target) return null;

        const percentBelow = ((target - actual) / target) * 100;

        return {
            id: `alert_gen_global_throughput_${Date.now()}`,
            severity: percentBelow > 50 ? 'high' : percentBelow > 20 ? 'medium' : 'low',
            scope: 'Global',
            category: 'throughput_sla_breach',
            alert: `Global throughput at ${formatNumber(Math.round(actual))} rpm (${percentBelow.toFixed(1)}% below target of ${formatNumber(target)} rpm)`,
            recommendation: 'Review per-source performance metrics and identify bottlenecks. Consider increasing worker concurrency or optimizing slow stages.',
            threshold_value: actual,
            sla_target: target,
            breach_percentage: percentBelow,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Acquisition Team'
        };
    }

    /**
     * Check global duration SLA
     * @param {Object} global - Global metrics
     * @param {Object} targets - Global SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkGlobalDurationSLA(global, targets) {
        const actual = global.totalDuration;
        const target = targets.max_duration_seconds;

        if (!target || actual <= target) return null;

        const percentOver = ((actual - target) / target) * 100;

        return {
            id: `alert_gen_global_duration_${Date.now()}`,
            severity: percentOver > 50 ? 'high' : percentOver > 20 ? 'medium' : 'low',
            scope: 'Global',
            category: 'duration_sla_breach',
            alert: `Pipeline duration ${formatDuration(actual)} exceeded ${formatDuration(target)} SLA target (${percentOver.toFixed(1)}% over)`,
            recommendation: 'Investigate stage-level bottlenecks using the waterfall chart. Check for network latency, API rate limits, or resource constraints.',
            threshold_value: actual,
            sla_target: target,
            breach_percentage: percentOver,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Acquisition Team'
        };
    }

    /**
     * Check global quality SLA
     * @param {Object} global - Global metrics
     * @param {Object} targets - Global SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkGlobalQualitySLA(global, targets) {
        const actual = global.avgQualityRate;
        const target = targets.min_quality_pass_rate;

        if (!target || actual >= target) return null;

        const percentBelow = ((target - actual) / target) * 100;

        return {
            id: `alert_gen_global_quality_${Date.now()}`,
            severity: percentBelow > 30 ? 'high' : percentBelow > 15 ? 'medium' : 'low',
            scope: 'Global',
            category: 'quality_sla_breach',
            alert: `Quality pass rate ${(actual * 100).toFixed(1)}% below ${(target * 100).toFixed(1)}% target (${percentBelow.toFixed(1)}% below)`,
            recommendation: 'Review filter breakdown heatmap to identify problematic filters. Consider adjusting filter thresholds or improving source data quality.',
            threshold_value: actual,
            sla_target: target,
            breach_percentage: percentBelow,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Quality Team'
        };
    }

    /**
     * Check source-specific duration SLA
     * @param {Object} source - Source metrics
     * @param {Object} target - Source SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkSourceDurationSLA(source, target) {
        const actual = source.performance.duration;
        const sla = target.max_duration_seconds;

        if (!sla || actual <= sla) return null;

        const percentOver = ((actual - sla) / sla) * 100;

        return {
            id: `alert_gen_${source.source}_duration_${Date.now()}`,
            severity: percentOver > 50 ? 'high' : percentOver > 20 ? 'medium' : 'low',
            scope: source.source,
            category: 'duration_sla_breach',
            alert: `${source.source} duration ${formatDuration(actual)} exceeded ${formatDuration(sla)} SLA (${percentOver.toFixed(1)}% over)`,
            recommendation: `Investigate ${source.source} pipeline stage latencies. Check for API throttling, network issues, or increased data volume.`,
            threshold_value: actual,
            sla_target: sla,
            breach_percentage: percentOver,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Acquisition Team',
            related_source: source.source
        };
    }

    /**
     * Check source-specific throughput SLA
     * @param {Object} source - Source metrics
     * @param {Object} target - Source SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkSourceThroughputSLA(source, target) {
        const actual = source.performance.throughput;
        const sla = target.min_throughput_rpm;

        if (!sla || actual >= sla) return null;

        const percentBelow = ((sla - actual) / sla) * 100;

        return {
            id: `alert_gen_${source.source}_throughput_${Date.now()}`,
            severity: percentBelow > 50 ? 'high' : percentBelow > 20 ? 'medium' : 'low',
            scope: source.source,
            category: 'throughput_sla_breach',
            alert: `${source.source} throughput ${formatNumber(Math.round(actual))} rpm below ${formatNumber(sla)} rpm target (${percentBelow.toFixed(1)}% below)`,
            recommendation: `Review ${source.source} processing efficiency. Consider increasing batch size, parallelization, or optimizing extraction logic.`,
            threshold_value: actual,
            sla_target: sla,
            breach_percentage: percentBelow,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Acquisition Team',
            related_source: source.source
        };
    }

    /**
     * Check source-specific quality SLA
     * @param {Object} source - Source metrics
     * @param {Object} target - Source SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkSourceQualitySLA(source, target) {
        const actual = source.performance.qualityRate;
        const sla = target.min_quality_pass_rate;

        if (!sla || actual >= sla) return null;

        const percentBelow = ((sla - actual) / sla) * 100;

        return {
            id: `alert_gen_${source.source}_quality_${Date.now()}`,
            severity: percentBelow > 30 ? 'high' : percentBelow > 15 ? 'medium' : 'low',
            scope: source.source,
            category: 'quality_sla_breach',
            alert: `${source.source} quality ${(actual * 100).toFixed(1)}% below ${(sla * 100).toFixed(1)}% target (${percentBelow.toFixed(1)}% below)`,
            recommendation: `Analyze ${source.source} filter breakdown to identify top rejection reasons. Consider source-specific filter tuning.`,
            threshold_value: actual,
            sla_target: sla,
            breach_percentage: percentBelow,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Quality Team',
            related_source: source.source
        };
    }

    /**
     * Check source-specific P95 latency SLA
     * @param {Object} source - Source metrics
     * @param {Object} target - Source SLA targets
     * @returns {Object|null} Alert object or null
     */
    checkSourceLatencySLA(source, target) {
        const actual = source.latency.p95;
        const sla = target.p95_fetch_latency_ms;

        if (!sla || !actual || actual <= sla) return null;

        const percentOver = ((actual - sla) / sla) * 100;

        return {
            id: `alert_gen_${source.source}_latency_${Date.now()}`,
            severity: percentOver > 100 ? 'high' : percentOver > 50 ? 'medium' : 'low',
            scope: source.source,
            category: 'latency_sla_breach',
            alert: `${source.source} P95 fetch latency ${actual.toFixed(0)}ms exceeded ${sla}ms target (${percentOver.toFixed(1)}% over)`,
            recommendation: `Investigate ${source.source} API response times. Check for network latency, upstream service degradation, or rate limiting.`,
            threshold_value: actual,
            sla_target: sla,
            breach_percentage: percentOver,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Acquisition Team',
            related_source: source.source
        };
    }

    /**
     * Check retry budget utilization
     * @param {Object} global - Global metrics
     * @param {Array} sources - Array of source metrics
     * @returns {Object|null} Alert object or null
     */
    checkRetryBudget(global, sources) {
        const totalRetries = global.totalRetries;
        const maxRetries = sources.length * 10; // 10 retries per source budget
        const utilization = (totalRetries / maxRetries) * 100;

        if (utilization < 80) return null;

        return {
            id: `alert_gen_retry_budget_${Date.now()}`,
            severity: utilization > 95 ? 'high' : 'medium',
            scope: 'Global',
            category: 'retry_budget_exhaustion',
            alert: `Retry budget at ${utilization.toFixed(1)}% utilization (${totalRetries} of ${maxRetries} retries used)`,
            recommendation: 'Review error logs to identify sources with high retry rates. Consider adjusting retry backoff strategy or fixing upstream issues.',
            threshold_value: totalRetries,
            sla_target: maxRetries,
            breach_percentage: utilization,
            detected_at: new Date().toISOString(),
            status: 'monitoring',
            owner: 'Data Acquisition Team'
        };
    }

    /**
     * Detect anomalies using statistical methods
     * @param {Object} latestRun - Most recent run
     * @param {Array} historicalRuns - Array of previous runs
     * @returns {Array} Array of anomaly alerts
     */
    detectAnomalies(latestRun, historicalRuns) {
        const anomalies = [];

        // Throughput anomaly (z-score > 2)
        const throughputs = historicalRuns.map(r => r.throughput_rpm);
        const throughputAnomaly = this.detectOutlier(
            latestRun.throughput_rpm,
            throughputs,
            'throughput_rpm',
            'records per minute'
        );
        if (throughputAnomaly) {
            anomalies.push({
                id: `alert_gen_anomaly_throughput_${Date.now()}`,
                severity: Math.abs(throughputAnomaly.zScore) > 3 ? 'high' : 'medium',
                scope: 'Global',
                category: 'anomaly_detection',
                alert: `Throughput anomaly detected: ${throughputAnomaly.status} (${Math.abs(throughputAnomaly.zScore).toFixed(1)}σ deviation)`,
                recommendation: 'Investigate sudden changes in pipeline performance. Check for infrastructure changes, upstream API changes, or data volume spikes.',
                threshold_value: latestRun.throughput_rpm,
                sla_target: throughputAnomaly.mean,
                breach_percentage: throughputAnomaly.deviationPercent,
                detected_at: new Date().toISOString(),
                status: 'monitoring',
                owner: 'Data Acquisition Team'
            });
        }

        // Duration anomaly
        const durations = historicalRuns.map(r => r.total_duration_seconds);
        const durationAnomaly = this.detectOutlier(
            latestRun.total_duration_seconds,
            durations,
            'total_duration_seconds',
            'seconds'
        );
        if (durationAnomaly) {
            anomalies.push({
                id: `alert_gen_anomaly_duration_${Date.now()}`,
                severity: Math.abs(durationAnomaly.zScore) > 3 ? 'high' : 'medium',
                scope: 'Global',
                category: 'anomaly_detection',
                alert: `Duration anomaly detected: ${durationAnomaly.status} (${Math.abs(durationAnomaly.zScore).toFixed(1)}σ deviation)`,
                recommendation: 'Check for infrastructure bottlenecks, network issues, or unexpected data volume increases.',
                threshold_value: latestRun.total_duration_seconds,
                sla_target: durationAnomaly.mean,
                breach_percentage: durationAnomaly.deviationPercent,
                detected_at: new Date().toISOString(),
                status: 'monitoring',
                owner: 'Data Acquisition Team'
            });
        }

        return anomalies;
    }

    /**
     * Detect statistical outlier using z-score
     * @param {number} current - Current value
     * @param {Array} historical - Historical values
     * @param {string} metric - Metric name
     * @param {string} unit - Unit of measurement
     * @returns {Object|null} Anomaly details or null
     */
    detectOutlier(current, historical, metric, unit) {
        if (historical.length < 3) return null;

        const mean = historical.reduce((sum, val) => sum + val, 0) / historical.length;
        const variance = historical.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / historical.length;
        const stdDev = Math.sqrt(variance);

        if (stdDev === 0) return null; // No variation

        const zScore = (current - mean) / stdDev;

        // Alert if |z-score| > 2 (95% confidence interval)
        if (Math.abs(zScore) < 2) return null;

        const deviationPercent = ((current - mean) / mean) * 100;
        const status = zScore > 0 ? 'spike' : 'drop';

        return {
            zScore,
            mean,
            stdDev,
            deviationPercent,
            status
        };
    }

    /**
     * Merge generated alerts with pre-generated alerts (deduplicate)
     * @param {Array} generated - Generated alerts
     * @param {Array} preGenerated - Pre-generated alerts
     * @returns {Array} Merged and deduplicated alerts
     */
    mergeAlerts(generated, preGenerated) {
        // Use pre-generated alerts as base
        const merged = [...preGenerated];

        // Add generated alerts that don't duplicate pre-generated ones
        generated.forEach(genAlert => {
            const isDuplicate = preGenerated.some(preAlert =>
                preAlert.scope === genAlert.scope &&
                preAlert.category === genAlert.category
            );

            if (!isDuplicate) {
                merged.push(genAlert);
            }
        });

        return merged;
    }

    /**
     * Calculate percentage below target
     * @param {number} actual - Actual value
     * @param {number} target - Target value
     * @returns {number} Percentage below target
     */
    calculatePercentBelow(actual, target) {
        if (!target || target === 0) return 0;
        return ((target - actual) / target) * 100;
    }

    /**
     * Calculate percentage above target
     * @param {number} actual - Actual value
     * @param {number} target - Target value
     * @returns {number} Percentage above target
     */
    calculatePercentAbove(actual, target) {
        if (!target || target === 0) return 0;
        return ((actual - target) / target) * 100;
    }
}

// Export singleton instance
export const alertEngine = new AlertEngine();
