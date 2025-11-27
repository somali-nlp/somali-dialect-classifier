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
            timestamp: new Date(run.timestamp),
            schema_version: run.schema_version || '1.0',  // Default to v1.0

            // Provide safe defaults for missing fields (backward compatibility)
            resource_metrics: run.resource_metrics || {
              cpu: { peak_percent: null, avg_percent: null },
              memory: { peak_mb: null, avg_mb: null },
              disk: { read_mb: null, write_mb: null },
              network: { bytes_downloaded: null, requests_made: null }
            },

            environment: run.environment || { python_version: 'unknown' },
            data_quality: run.data_quality || { completeness_score: null }
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

  /**
   * Calculate baseline metrics from historical runs
   * Computes p50, p95, p99 percentiles for throughput and duration
   * @param {number} windowSize - Number of recent runs to analyze (default: 15)
   * @returns {Promise<Object>} Baseline metrics object with percentiles
   */
  async calculateBaselines(windowSize = 15) {
    const runHistory = await this.loadRunHistory();

    if (runHistory.length < 2) {
      return {
        sufficient_data: false,
        message: 'Insufficient historical data for baseline calculation',
        runs_available: runHistory.length,
        runs_required: 2
      };
    }

    const recentRuns = runHistory.slice(0, windowSize);

    // Extract metrics for baseline calculation
    const throughputs = recentRuns.map(r => r.throughput_rpm).filter(v => v != null);
    const durations = recentRuns.map(r => r.total_duration_seconds).filter(v => v != null);
    const qualityRates = recentRuns.map(r => r.quality_pass_rate).filter(v => v != null);

    // Calculate percentiles
    const calculatePercentiles = (values) => {
      if (values.length === 0) return { p50: 0, p95: 0, p99: 0 };

      const sorted = [...values].sort((a, b) => a - b);
      const p50Index = Math.floor(sorted.length * 0.50);
      const p95Index = Math.floor(sorted.length * 0.95);
      const p99Index = Math.floor(sorted.length * 0.99);

      return {
        p50: sorted[p50Index] || sorted[sorted.length - 1],
        p95: sorted[p95Index] || sorted[sorted.length - 1],
        p99: sorted[p99Index] || sorted[sorted.length - 1],
        min: Math.min(...sorted),
        max: Math.max(...sorted),
        mean: sorted.reduce((sum, v) => sum + v, 0) / sorted.length
      };
    };

    return {
      sufficient_data: true,
      window_size: recentRuns.length,
      date_range: {
        start: recentRuns[recentRuns.length - 1].timestamp,
        end: recentRuns[0].timestamp
      },
      throughput: calculatePercentiles(throughputs),
      duration: calculatePercentiles(durations),
      quality: calculatePercentiles(qualityRates),
      runs_analyzed: recentRuns.length
    };
  }

  /**
   * Compare current run metrics to baseline percentiles
   * @param {Object} currentMetrics - Current run metrics
   * @param {Object} baselines - Baseline metrics from calculateBaselines()
   * @returns {Object} Comparison results with deviation percentages
   */
  compareToBaseline(currentMetrics, baselines) {
    if (!baselines.sufficient_data) {
      return {
        available: false,
        message: 'Baseline comparison unavailable - insufficient historical data'
      };
    }

    const calculateDeviation = (current, baseline) => {
      if (!baseline || baseline === 0) return 0;
      return ((current - baseline) / baseline) * 100;
    };

    return {
      available: true,
      throughput: {
        current: currentMetrics.throughput_rpm,
        baseline_p50: baselines.throughput.p50,
        baseline_p95: baselines.throughput.p95,
        deviation_from_p50: calculateDeviation(currentMetrics.throughput_rpm, baselines.throughput.p50),
        deviation_from_p95: calculateDeviation(currentMetrics.throughput_rpm, baselines.throughput.p95),
        status: currentMetrics.throughput_rpm >= baselines.throughput.p50 ? 'above_median' : 'below_median'
      },
      duration: {
        current: currentMetrics.total_duration_seconds,
        baseline_p50: baselines.duration.p50,
        baseline_p95: baselines.duration.p95,
        deviation_from_p50: calculateDeviation(currentMetrics.total_duration_seconds, baselines.duration.p50),
        deviation_from_p95: calculateDeviation(currentMetrics.total_duration_seconds, baselines.duration.p95),
        status: currentMetrics.total_duration_seconds <= baselines.duration.p50 ? 'below_median' : 'above_median'
      },
      quality: {
        current: currentMetrics.quality_pass_rate,
        baseline_p50: baselines.quality.p50,
        baseline_p95: baselines.quality.p95,
        deviation_from_p50: calculateDeviation(currentMetrics.quality_pass_rate, baselines.quality.p50),
        deviation_from_p95: calculateDeviation(currentMetrics.quality_pass_rate, baselines.quality.p95),
        status: currentMetrics.quality_pass_rate >= baselines.quality.p50 ? 'above_median' : 'below_median'
      },
      baseline_window: baselines.window_size
    };
  }

  /**
   * Detect anomalies using Z-score statistical method
   * Flags metrics when |z-score| > 2 (medium severity) or > 3 (high severity)
   * @param {Object} currentRun - Current run metrics
   * @param {number} windowSize - Number of recent runs for baseline (default: 15)
   * @returns {Promise<Object>} Anomaly detection results
   */
  async detectAnomalies(currentRun, windowSize = 15) {
    const runHistory = await this.loadRunHistory();

    if (runHistory.length < 5) {
      return {
        anomalies: [],
        detection_available: false,
        message: 'Insufficient historical data for anomaly detection (need 5+ runs)',
        runs_available: runHistory.length
      };
    }

    const recentRuns = runHistory.slice(0, windowSize);
    const anomalies = [];

    // Helper function to calculate Z-score
    const calculateZScore = (values) => {
      if (values.length === 0) return { mean: 0, stdDev: 0 };

      const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
      const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
      const stdDev = Math.sqrt(variance);

      return { mean, stdDev };
    };

    const detectMetricAnomaly = (metricName, currentValue, historicalValues, higherIsBetter = true) => {
      const { mean, stdDev } = calculateZScore(historicalValues);

      if (stdDev === 0) {
        // No variance in historical data - can't detect anomalies
        return null;
      }

      const zScore = (currentValue - mean) / stdDev;
      const absZScore = Math.abs(zScore);

      if (absZScore > 2) {
        const severity = absZScore > 3 ? 'high' : 'medium';
        const direction = zScore > 0 ? 'increase' : 'decrease';
        const isGood = higherIsBetter ? (zScore > 0) : (zScore < 0);

        return {
          metric: metricName,
          value: currentValue,
          expected: mean,
          z_score: Math.round(zScore * 100) / 100,
          std_deviations: Math.round(absZScore * 100) / 100,
          severity,
          direction,
          is_positive_anomaly: isGood,
          message: `${metricName} ${direction} detected: ${currentValue.toFixed(2)} vs expected ${mean.toFixed(2)} (${absZScore.toFixed(1)}σ ${direction})`
        };
      }

      return null;
    };

    // Check throughput anomalies (higher is better)
    const throughputs = recentRuns.map(r => r.throughput_rpm).filter(v => v != null);
    const throughputAnomaly = detectMetricAnomaly(
      'throughput_rpm',
      currentRun.throughput_rpm,
      throughputs,
      true
    );
    if (throughputAnomaly) anomalies.push(throughputAnomaly);

    // Check duration anomalies (lower is better)
    const durations = recentRuns.map(r => r.total_duration_seconds).filter(v => v != null);
    const durationAnomaly = detectMetricAnomaly(
      'total_duration_seconds',
      currentRun.total_duration_seconds,
      durations,
      false
    );
    if (durationAnomaly) anomalies.push(durationAnomaly);

    // Check quality rate anomalies (higher is better)
    const qualityRates = recentRuns.map(r => r.quality_pass_rate).filter(v => v != null);
    const qualityAnomaly = detectMetricAnomaly(
      'quality_pass_rate',
      currentRun.quality_pass_rate,
      qualityRates,
      true
    );
    if (qualityAnomaly) anomalies.push(qualityAnomaly);

    // Check retry anomalies (lower is better)
    const retries = recentRuns.map(r => r.retries || 0).filter(v => v != null);
    const retryAnomaly = detectMetricAnomaly(
      'retries',
      currentRun.retries || 0,
      retries,
      false
    );
    if (retryAnomaly) anomalies.push(retryAnomaly);

    // Check error anomalies (lower is better)
    const errors = recentRuns.map(r => r.errors || 0).filter(v => v != null);
    const errorAnomaly = detectMetricAnomaly(
      'errors',
      currentRun.errors || 0,
      errors,
      false
    );
    if (errorAnomaly) anomalies.push(errorAnomaly);

    return {
      anomalies,
      detection_available: true,
      window_size: recentRuns.length,
      anomalies_detected: anomalies.length,
      run_id: currentRun.run_id,
      timestamp: currentRun.timestamp,
      summary: anomalies.length > 0
        ? `${anomalies.length} anomaly(ies) detected`
        : 'No anomalies detected - performance within normal range'
    };
  }

  /**
   * Record a new pipeline run to history
   * NOTE: This is a CLIENT-SIDE utility for testing/demo purposes.
   * Production implementation should be server-side (Python script).
   *
   * @param {Object} runData - Pipeline run object matching schema v2.0
   * @returns {Promise<Object>} Result with success status and validation errors
   */
  async recordPipelineRun(runData) {
    // Validate required fields
    const requiredFields = [
      'run_id', 'timestamp', 'sources_processed', 'total_duration_seconds',
      'total_records', 'throughput_rpm', 'quality_pass_rate'
    ];

    const missingFields = requiredFields.filter(field => !(field in runData));

    if (missingFields.length > 0) {
      return {
        success: false,
        error: 'VALIDATION_ERROR',
        message: `Missing required fields: ${missingFields.join(', ')}`,
        missing_fields: missingFields
      };
    }

    // Validate schema version
    const schemaVersion = runData.schema_version || '1.0';
    if (!['1.0', '2.0'].includes(schemaVersion)) {
      return {
        success: false,
        error: 'INVALID_SCHEMA',
        message: `Unsupported schema version: ${schemaVersion}`
      };
    }

    // Validate timestamp format
    try {
      const timestamp = new Date(runData.timestamp);
      if (isNaN(timestamp.getTime())) {
        throw new Error('Invalid timestamp');
      }
    } catch (e) {
      return {
        success: false,
        error: 'INVALID_TIMESTAMP',
        message: 'Timestamp must be ISO 8601 format'
      };
    }

    // Validate numeric ranges
    const validations = [
      { field: 'sources_processed', min: 1, max: 10 },
      { field: 'total_duration_seconds', min: 0, max: 86400 },
      { field: 'total_records', min: 0, max: 1000000 },
      { field: 'throughput_rpm', min: 0, max: 100000 },
      { field: 'quality_pass_rate', min: 0, max: 1 }
    ];

    for (const { field, min, max } of validations) {
      const value = runData[field];
      if (value < min || value > max) {
        return {
          success: false,
          error: 'RANGE_ERROR',
          message: `${field} must be between ${min} and ${max}, got ${value}`
        };
      }
    }

    // Check for duplicate run_id
    const existingRuns = await this.loadRunHistory();
    const isDuplicate = existingRuns.some(r => r.run_id === runData.run_id);

    if (isDuplicate) {
      return {
        success: false,
        error: 'DUPLICATE_RUN_ID',
        message: `Run ID ${runData.run_id} already exists in history`,
        suggestion: 'Use a different run_id or update existing run'
      };
    }

    // WARNING: This is client-side demo code
    // Real implementation should POST to a backend API
    console.warn('[PipelineDataService] recordPipelineRun() is demo code only');
    console.warn('Production: Implement server-side API endpoint for recording runs');

    return {
      success: true,
      message: 'Run validated successfully',
      run_id: runData.run_id,
      timestamp: runData.timestamp,
      warnings: [
        'Client-side recording not implemented',
        'Use Python script: scripts/record_pipeline_run.py'
      ]
    };
  }

  /**
   * Detect anomalies using advanced statistical methods
   * - Robust Z-score using median + MAD (outlier-resistant)
   * - Seasonality detection (day-of-week patterns)
   * - Confidence intervals instead of fixed thresholds
   *
   * @param {Object} currentRun - Current run metrics
   * @param {number} windowSize - Number of recent runs for baseline (default: 30)
   * @returns {Promise<Object>} Anomaly detection results with seasonality info
   */
  async detectAnomaliesAdvanced(currentRun, windowSize = 30) {
    const runHistory = await this.loadRunHistory();

    // Check for minimum data requirement
    if (runHistory.length < 30) {
      // Fall back to simple threshold detection
      console.warn(`[detectAnomaliesAdvanced] Only ${runHistory.length} runs available, need 30+ for statistical detection`);
      return this.detectAnomalies(currentRun, Math.min(runHistory.length, 15));
    }

    const recentRuns = runHistory.slice(0, windowSize);
    const anomalies = [];

    // Helper: Calculate Z-score with outlier-resistant statistics
    const calculateRobustZScore = (values) => {
      if (values.length === 0) return { mean: 0, stdDev: 0, median: 0 };

      // Use median instead of mean (more robust to outliers)
      const sorted = [...values].sort((a, b) => a - b);
      const median = sorted[Math.floor(sorted.length / 2)];

      // Use MAD (Median Absolute Deviation) instead of stddev
      const deviations = values.map(v => Math.abs(v - median));
      const mad = deviations.sort((a, b) => a - b)[Math.floor(deviations.length / 2)];

      // Convert MAD to approximate stddev (for normal distribution)
      const stdDev = mad * 1.4826;

      return { mean: median, stdDev, median };
    };

    // Helper: Detect seasonality (day-of-week patterns)
    const detectSeasonality = (runs, metricKey) => {
      const byDayOfWeek = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };

      runs.forEach(run => {
        const dayOfWeek = new Date(run.timestamp).getDay();
        const value = run[metricKey];
        if (value != null) {
          byDayOfWeek[dayOfWeek].push(value);
        }
      });

      // Calculate average per day
      const avgByDay = {};
      for (const [day, values] of Object.entries(byDayOfWeek)) {
        if (values.length > 0) {
          avgByDay[day] = values.reduce((sum, v) => sum + v, 0) / values.length;
        }
      }

      // Detect if variance across days is significant (>20%)
      const avgValues = Object.values(avgByDay);
      if (avgValues.length === 0) return { seasonal: false };

      const overallAvg = avgValues.reduce((sum, v) => sum + v, 0) / avgValues.length;
      const maxDev = Math.max(...avgValues.map(v => Math.abs(v - overallAvg) / overallAvg));

      return {
        seasonal: maxDev > 0.20,  // >20% variance = seasonal
        day_averages: avgByDay,
        max_deviation_percent: maxDev * 100
      };
    };

    // Detect metric anomaly with seasonality adjustment
    const detectMetricAnomaly = (metricName, currentValue, historicalRuns, higherIsBetter = true) => {
      const values = historicalRuns.map(r => r[metricName]).filter(v => v != null);

      if (values.length < 5) return null;

      // Check for seasonality
      const seasonality = detectSeasonality(historicalRuns, metricName);

      // Adjust expected value based on day-of-week if seasonal
      let expectedValue;
      if (seasonality.seasonal) {
        const currentDay = new Date(currentRun.timestamp).getDay();
        expectedValue = seasonality.day_averages[currentDay] || calculateRobustZScore(values).median;
      } else {
        expectedValue = calculateRobustZScore(values).median;
      }

      const { stdDev } = calculateRobustZScore(values);

      if (stdDev === 0) return null;  // No variance

      const zScore = (currentValue - expectedValue) / stdDev;
      const absZScore = Math.abs(zScore);

      // Confidence intervals (Z-score thresholds)
      // 2σ = 95% confidence, 3σ = 99.7% confidence
      if (absZScore > 2) {
        const severity = absZScore > 3 ? 'high' : 'medium';
        const direction = zScore > 0 ? 'increase' : 'decrease';
        const isGood = higherIsBetter ? (zScore > 0) : (zScore < 0);

        return {
          metric: metricName,
          value: currentValue,
          expected: expectedValue,
          z_score: Math.round(zScore * 100) / 100,
          std_deviations: Math.round(absZScore * 100) / 100,
          confidence_level: absZScore > 3 ? '99.7%' : '95%',
          severity,
          direction,
          is_positive_anomaly: isGood,
          seasonality: seasonality.seasonal ? {
            detected: true,
            day_of_week: new Date(currentRun.timestamp).toLocaleDateString('en-US', { weekday: 'long' }),
            expected_for_day: expectedValue,
            max_day_variance: Math.round(seasonality.max_deviation_percent)
          } : { detected: false },
          message: `${metricName} ${direction} detected: ${currentValue.toFixed(2)} vs expected ${expectedValue.toFixed(2)} (${absZScore.toFixed(1)}σ ${direction}, ${absZScore > 3 ? '99.7%' : '95%'} confidence)`
        };
      }

      return null;
    };

    // Check anomalies for key metrics
    const metrics = [
      { key: 'throughput_rpm', higherIsBetter: true },
      { key: 'total_duration_seconds', higherIsBetter: false },
      { key: 'quality_pass_rate', higherIsBetter: true },
      { key: 'retries', higherIsBetter: false },
      { key: 'errors', higherIsBetter: false }
    ];

    for (const { key, higherIsBetter } of metrics) {
      const anomaly = detectMetricAnomaly(key, currentRun[key], recentRuns, higherIsBetter);
      if (anomaly) anomalies.push(anomaly);
    }

    return {
      anomalies,
      detection_available: true,
      method: 'robust_z_score',
      window_size: recentRuns.length,
      anomalies_detected: anomalies.length,
      run_id: currentRun.run_id,
      timestamp: currentRun.timestamp,
      seasonality_detected: anomalies.some(a => a.seasonality?.detected),
      summary: anomalies.length > 0
        ? `${anomalies.length} anomaly(ies) detected with 95-99.7% confidence`
        : 'No anomalies detected - performance within normal range'
    };
  }

  /**
   * Get aggregated resource metrics from historical runs
   * Computes trends, percentiles, and identifies resource bottlenecks
   *
   * @param {number} windowSize - Number of recent runs to analyze (default: 15)
   * @returns {Promise<Object>} Resource metrics analysis
   */
  async getResourceMetrics(windowSize = 15) {
    const runHistory = await this.loadRunHistory();

    if (runHistory.length === 0) {
      return {
        available: false,
        message: 'No historical runs available'
      };
    }

    const recentRuns = runHistory.slice(0, windowSize);

    // Filter runs with resource metrics (schema v2.0)
    const runsWithResources = recentRuns.filter(r =>
      r.schema_version === '2.0' && r.resource_metrics
    );

    if (runsWithResources.length === 0) {
      return {
        available: false,
        message: 'No runs with resource metrics found (need schema v2.0)',
        total_runs: recentRuns.length,
        upgrade_instructions: 'Update pipeline to record resource_metrics field'
      };
    }

    // Helper: Calculate percentiles
    const percentile = (values, p) => {
      if (values.length === 0) return null;
      const sorted = [...values].sort((a, b) => a - b);
      const index = Math.floor(sorted.length * p);
      return sorted[index] || sorted[sorted.length - 1];
    };

    // Extract CPU metrics
    const cpuPeaks = runsWithResources.map(r => r.resource_metrics?.cpu?.peak_percent).filter(v => v != null);
    const cpuAvgs = runsWithResources.map(r => r.resource_metrics?.cpu?.avg_percent).filter(v => v != null);

    // Extract Memory metrics
    const memPeaks = runsWithResources.map(r => r.resource_metrics?.memory?.peak_mb).filter(v => v != null);
    const memAvgs = runsWithResources.map(r => r.resource_metrics?.memory?.avg_mb).filter(v => v != null);

    // Extract Disk metrics
    const diskReads = runsWithResources.map(r => r.resource_metrics?.disk?.read_mb).filter(v => v != null);
    const diskWrites = runsWithResources.map(r => r.resource_metrics?.disk?.write_mb).filter(v => v != null);

    // Identify resource bottlenecks
    const bottlenecks = [];

    const avgCpuPeak = cpuPeaks.reduce((sum, v) => sum + v, 0) / cpuPeaks.length;
    if (avgCpuPeak > 80) {
      bottlenecks.push({
        resource: 'cpu',
        severity: 'high',
        message: `Average CPU peak ${avgCpuPeak.toFixed(1)}% exceeds 80% threshold`,
        recommendation: 'Consider parallelizing I/O-bound tasks or upgrading CPU'
      });
    }

    const avgMemPeak = memPeaks.reduce((sum, v) => sum + v, 0) / memPeaks.length;
    const totalMemoryMB = runsWithResources[0]?.environment?.total_memory_mb || 16384;
    const memUtilization = (avgMemPeak / totalMemoryMB) * 100;

    if (memUtilization > 75) {
      bottlenecks.push({
        resource: 'memory',
        severity: 'medium',
        message: `Memory utilization ${memUtilization.toFixed(1)}% approaching limit`,
        recommendation: 'Optimize batch sizes or increase system memory'
      });
    }

    // Calculate trends (compare first half vs second half of window)
    const midpoint = Math.floor(runsWithResources.length / 2);
    const recentCpuAvg = cpuAvgs.slice(0, midpoint).reduce((sum, v) => sum + v, 0) / midpoint;
    const olderCpuAvg = cpuAvgs.slice(midpoint).reduce((sum, v) => sum + v, 0) / (cpuAvgs.length - midpoint);
    const cpuTrend = ((recentCpuAvg - olderCpuAvg) / olderCpuAvg) * 100;

    return {
      available: true,
      window_size: runsWithResources.length,
      date_range: {
        start: runsWithResources[runsWithResources.length - 1].timestamp,
        end: runsWithResources[0].timestamp
      },

      cpu: {
        peak_percent: {
          p50: percentile(cpuPeaks, 0.50),
          p95: percentile(cpuPeaks, 0.95),
          max: Math.max(...cpuPeaks),
          avg: avgCpuPeak
        },
        avg_percent: {
          p50: percentile(cpuAvgs, 0.50),
          p95: percentile(cpuAvgs, 0.95),
          trend_percent: cpuTrend
        }
      },

      memory: {
        peak_mb: {
          p50: percentile(memPeaks, 0.50),
          p95: percentile(memPeaks, 0.95),
          max: Math.max(...memPeaks),
          avg: avgMemPeak
        },
        utilization_percent: memUtilization
      },

      disk: {
        read_mb: {
          p50: percentile(diskReads, 0.50),
          p95: percentile(diskReads, 0.95),
          total: diskReads.reduce((sum, v) => sum + v, 0)
        },
        write_mb: {
          p50: percentile(diskWrites, 0.50),
          p95: percentile(diskWrites, 0.95),
          total: diskWrites.reduce((sum, v) => sum + v, 0)
        }
      },

      bottlenecks: bottlenecks,
      recommendations: bottlenecks.length > 0
        ? bottlenecks.map(b => b.recommendation)
        : ['No resource bottlenecks detected - system running efficiently']
    };
  }
}

// Export both the class and singleton instance
export { PipelineDataService };
export const pipelineDataService = new PipelineDataService();
