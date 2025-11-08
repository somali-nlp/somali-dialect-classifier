/**
 * Pipeline Data Service
 *
 * Centralized service for loading, caching, and aggregating pipeline performance data.
 * Provides a clean API for the frontend to consume historical runs, SLA targets,
 * alerts, and observations with built-in error handling and caching.
 *
 * @version 1.0
 * @author Data Engineering Team
 * @created 2025-11-08
 */

class PipelineDataService {
  constructor() {
    this.cache = new Map();
    this.CACHE_TTL = 5 * 60 * 1000; // 5 minutes
    this.BASE_PATH = 'data/';
  }

  /**
   * Load historical pipeline run data
   * @returns {Promise<Array>} Array of pipeline run objects
   */
  async loadRunHistory() {
    return this.fetchWithCache(
      'run_history',
      `${this.BASE_PATH}pipeline_run_history.json`,
      (data) => {
        // Validate and sort by timestamp descending (newest first)
        if (!Array.isArray(data)) {
          throw new Error('Pipeline run history must be an array');
        }
        return data
          .map(run => ({
            ...run,
            timestamp: new Date(run.timestamp)
          }))
          .sort((a, b) => b.timestamp - a.timestamp);
      }
    );
  }

  /**
   * Load SLA targets configuration
   * @returns {Promise<Object>} SLA targets object
   */
  async loadSLATargets() {
    return this.fetchWithCache(
      'sla_targets',
      `${this.BASE_PATH}sla_targets.json`,
      (data) => {
        // Validate SLA structure
        if (!data.global_targets || !data.per_source_targets) {
          throw new Error('Invalid SLA targets structure');
        }
        return data;
      },
      Infinity // Cache SLA targets indefinitely (static config)
    );
  }

  /**
   * Load pipeline alerts
   * @returns {Promise<Array>} Array of alert objects
   */
  async loadAlerts() {
    return this.fetchWithCache(
      'alerts',
      `${this.BASE_PATH}pipeline_alerts.json`,
      (data) => {
        // Extract and sort alerts by severity (high > medium > low)
        const alerts = data.alerts || [];
        const severityOrder = { high: 3, medium: 2, low: 1 };
        return alerts.sort((a, b) =>
          (severityOrder[b.severity] || 0) - (severityOrder[a.severity] || 0)
        );
      }
    );
  }

  /**
   * Load pipeline observations
   * @returns {Promise<Array>} Array of observation objects
   */
  async loadObservations() {
    return this.fetchWithCache(
      'observations',
      `${this.BASE_PATH}pipeline_observations.json`,
      (data) => {
        // Extract and filter by active/monitoring status
        const entries = data.entries || [];
        return entries.filter(obs =>
          obs.status === 'Active' || obs.status === 'Monitoring'
        );
      }
    );
  }

  /**
   * Load current metrics from all_metrics.json
   * @returns {Promise<Object>} Current metrics object
   */
  async getCurrentMetrics() {
    return this.fetchWithCache(
      'current_metrics',
      `${this.BASE_PATH}all_metrics.json`,
      (data) => {
        // Validate current metrics structure
        if (!data.metrics || !Array.isArray(data.metrics)) {
          throw new Error('Invalid current metrics structure');
        }
        return data;
      }
    );
  }

  /**
   * Get aggregated analytics combining all data sources
   * @returns {Promise<Object>} Aggregated analytics object
   */
  async getAggregatedPipelineAnalytics() {
    try {
      // Load all data sources in parallel
      const [runHistory, slaTargets, alerts, observations, currentMetrics] = await Promise.all([
        this.loadRunHistory(),
        this.loadSLATargets(),
        this.loadAlerts(),
        this.loadObservations(),
        this.getCurrentMetrics()
      ]);

      // Get most recent run
      const latestRun = runHistory[0];

      // Calculate per-source analytics
      const perSource = currentMetrics.metrics.map(metric => {
        const sourceName = metric.source;
        const slaTarget = slaTargets.per_source_targets[sourceName] || {};
        const latestSourceData = latestRun?.per_source_metrics?.[sourceName] || {};

        return {
          source: sourceName,
          pipelineType: metric.pipeline_type,
          performance: {
            duration: metric.duration_seconds,
            throughput: metric.records_per_minute,
            qualityRate: metric.quality_pass_rate,
            successRate: metric.http_request_success_rate || 1.0
          },
          latency: {
            mean: metric.fetch_duration_stats?.mean || 0,
            p95: metric.fetch_duration_stats?.p95 || 0,
            p99: metric.fetch_duration_stats?.p99 || 0
          },
          errors: metric.filter_breakdown || {},
          sla: slaTarget,
          alertCount: alerts.filter(a => a.scope === sourceName).length,
          latestRunData: latestSourceData
        };
      });

      // Calculate global metrics
      const global = this.calculateGlobalMetrics(perSource, latestRun);

      return {
        perSource,
        global,
        alerts,
        observations,
        runHistory,
        slaTargets,
        timestamp: new Date().toISOString(),
        latestRunId: latestRun?.run_id || null
      };
    } catch (error) {
      console.error('Error aggregating pipeline analytics:', error);
      throw error;
    }
  }

  /**
   * Calculate global metrics from per-source data
   * @param {Array} perSource - Per-source metrics array
   * @param {Object} latestRun - Latest run data
   * @returns {Object} Global metrics
   */
  calculateGlobalMetrics(perSource, latestRun) {
    const totalDuration = perSource.reduce((sum, s) => sum + s.performance.duration, 0);
    const totalRecords = perSource.reduce((sum, s) => sum + (s.latestRunData.records || 0), 0);

    // Calculate weighted average throughput (weighted by duration)
    const weightedThroughput = this.calculateWeightedThroughput(perSource);

    // Calculate overall quality rate (weighted by records processed)
    const weightedQuality = perSource.reduce((sum, s) => {
      const records = s.latestRunData.records || 0;
      return sum + (s.performance.qualityRate * records);
    }, 0) / totalRecords;

    return {
      totalSources: perSource.length,
      totalDuration: latestRun?.total_duration_seconds || totalDuration,
      totalRecords: latestRun?.total_records || totalRecords,
      avgThroughput: weightedThroughput,
      avgQualityRate: weightedQuality,
      totalAlerts: perSource.reduce((sum, s) => sum + s.alertCount, 0),
      totalRetries: latestRun?.retries || 0,
      totalErrors: latestRun?.errors || 0
    };
  }

  /**
   * Calculate weighted average throughput
   * Weighted by source duration, not simple average
   * @param {Array} sourceMetrics - Array of source metrics
   * @returns {number} Weighted average throughput in records/minute
   */
  calculateWeightedThroughput(sourceMetrics) {
    const totalRecords = sourceMetrics.reduce((sum, s) => sum + (s.latestRunData.records || 0), 0);
    const totalDurationMinutes = sourceMetrics.reduce((sum, s) => sum + s.performance.duration, 0) / 60;

    return totalDurationMinutes > 0 ? totalRecords / totalDurationMinutes : 0;
  }

  /**
   * Generic fetch with caching
   * @param {string} key - Cache key
   * @param {string} url - URL to fetch
   * @param {Function} transform - Optional transformation function
   * @param {number} ttl - Cache TTL in milliseconds (default: 5 minutes)
   * @returns {Promise<any>} Fetched and transformed data
   */
  async fetchWithCache(key, url, transform = x => x, ttl = this.CACHE_TTL) {
    // Check cache
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < ttl) {
      console.log(`[PipelineDataService] Cache hit: ${key}`);
      return cached.data;
    }

    console.log(`[PipelineDataService] Cache miss or expired: ${key}, fetching from ${url}`);

    try {
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const rawData = await response.json();
      const transformedData = transform(rawData);

      // Cache the result
      this.cache.set(key, {
        data: transformedData,
        timestamp: Date.now()
      });

      return transformedData;

    } catch (error) {
      console.error(`[PipelineDataService] Error fetching ${url}:`, error);

      // Try to return stale cache if available
      if (cached?.data) {
        console.warn(`[PipelineDataService] Returning stale cache for ${key}`);
        return cached.data;
      }

      // Return fallback data
      const fallback = this.getFallbackData(key);
      console.warn(`[PipelineDataService] Returning fallback data for ${key}`);
      return fallback;
    }
  }

  /**
   * Get fallback data for a given cache key
   * @param {string} key - Cache key
   * @returns {any} Fallback data
   */
  getFallbackData(key) {
    const fallbacks = {
      'run_history': [],
      'sla_targets': {
        global_targets: {},
        per_source_targets: {}
      },
      'alerts': [],
      'observations': [],
      'current_metrics': {
        count: 0,
        records: 0,
        sources: [],
        metrics: []
      }
    };

    return fallbacks[key] || null;
  }

  /**
   * Invalidate cache for a specific key or all keys
   * @param {string|null} key - Cache key to invalidate, or null to clear all
   */
  invalidateCache(key = null) {
    if (key) {
      console.log(`[PipelineDataService] Invalidating cache: ${key}`);
      this.cache.delete(key);
    } else {
      console.log('[PipelineDataService] Clearing entire cache');
      this.cache.clear();
    }
  }

  /**
   * Validate run history data structure
   * @param {Array} data - Run history array
   * @returns {boolean} True if valid
   */
  validateRunHistory(data) {
    if (!Array.isArray(data)) return false;

    // Check that each run has required fields
    return data.every(run =>
      run.run_id &&
      run.timestamp &&
      run.sources_processed !== undefined &&
      run.total_duration_seconds !== undefined &&
      run.total_records !== undefined
    );
  }

  /**
   * Get performance trends from historical data
   * @param {number} windowSize - Number of recent runs to analyze
   * @returns {Promise<Object>} Trend analysis
   */
  async getPerformanceTrends(windowSize = 10) {
    const runHistory = await this.loadRunHistory();
    const recentRuns = runHistory.slice(0, windowSize);

    if (recentRuns.length < 2) {
      return {
        throughputTrend: 'insufficient_data',
        durationTrend: 'insufficient_data',
        qualityTrend: 'insufficient_data'
      };
    }

    const latest = recentRuns[0];
    const baseline = recentRuns[recentRuns.length - 1];

    return {
      throughputTrend: this.calculateTrend(latest.throughput_rpm, baseline.throughput_rpm),
      durationTrend: this.calculateTrend(baseline.total_duration_seconds, latest.total_duration_seconds),
      qualityTrend: this.calculateTrend(latest.quality_pass_rate, baseline.quality_pass_rate),
      windowSize: recentRuns.length,
      dateRange: {
        start: baseline.timestamp,
        end: latest.timestamp
      }
    };
  }

  /**
   * Calculate trend between two values
   * @param {number} current - Current value
   * @param {number} baseline - Baseline value
   * @returns {Object} Trend object
   */
  calculateTrend(current, baseline) {
    if (!baseline || baseline === 0) {
      return { direction: 'unknown', deltaPercent: 0 };
    }

    const delta = current - baseline;
    const deltaPercent = (delta / baseline) * 100;

    return {
      direction: delta > 0 ? 'up' : delta < 0 ? 'down' : 'stable',
      delta,
      deltaPercent: Math.round(deltaPercent * 10) / 10,
      current,
      baseline
    };
  }
}

// Export both the class and singleton instance
export { PipelineDataService };
export const pipelineDataService = new PipelineDataService();
