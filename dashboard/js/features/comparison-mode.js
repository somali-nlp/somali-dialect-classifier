/**
 * Comparison Mode Manager
 * Enables split-screen comparison of metrics from different runs with diff indicators
 */

export const ComparisonMode = {
    isActive: false,
    runs: {
        left: null,
        right: null
    },
    allRuns: [],

    /**
     * Initialize comparison mode
     */
    init(metrics) {
        this.allRuns = this.extractRuns(metrics);
        this.createComparisonToggle();
    },

    /**
     * Extract unique runs from metrics
     */
    extractRuns(metrics) {
        const runsMap = new Map();

        metrics.forEach(metric => {
            if (!metric) return;

            const runId = metric._run_id || metric.run_id;
            const timestamp = metric._timestamp || metric.timestamp;
            const source = metric._source || metric.source;

            if (!runId) return;

            if (!runsMap.has(runId)) {
                runsMap.set(runId, {
                    id: runId,
                    timestamp: timestamp,
                    sources: [],
                    metrics: []
                });
            }

            const run = runsMap.get(runId);
            if (!run.sources.includes(source)) {
                run.sources.push(source);
            }
            run.metrics.push(metric);
        });

        return Array.from(runsMap.values()).sort((a, b) => {
            return new Date(b.timestamp) - new Date(a.timestamp);
        });
    },

    /**
     * Create comparison mode toggle button
     */
    createComparisonToggle() {
        const nav = document.querySelector('.nav-links');
        if (!nav) return;

        const toggleContainer = document.createElement('li');
        toggleContainer.style.display = 'flex';
        toggleContainer.style.alignItems = 'center';

        const toggle = document.createElement('button');
        toggle.id = 'comparison-toggle';
        toggle.className = 'comparison-toggle-btn';
        toggle.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="9" height="18" rx="1"></rect>
                <rect x="13" y="3" width="9" height="18" rx="1"></rect>
            </svg>
            <span>Compare</span>
        `;

        toggle.addEventListener('click', () => this.toggle());

        toggleContainer.appendChild(toggle);
        nav.appendChild(toggleContainer);
    },

    /**
     * Toggle comparison mode
     */
    toggle() {
        if (this.isActive) {
            this.disable();
        } else {
            this.enable();
        }
    },

    /**
     * Enable comparison mode
     */
    enable() {
        if (this.allRuns.length < 2) {
            alert('Not enough runs available for comparison. Need at least 2 runs.');
            return;
        }

        this.isActive = true;

        // Show comparison panel
        this.showComparisonPanel();

        // Update toggle button
        const toggle = document.getElementById('comparison-toggle');
        if (toggle) {
            toggle.classList.add('active');
        }

        // Hide regular content, show split view
        this.createSplitView();
    },

    /**
     * Disable comparison mode
     */
    disable() {
        this.isActive = false;

        // Hide comparison panel
        this.hideComparisonPanel();

        // Update toggle button
        const toggle = document.getElementById('comparison-toggle');
        if (toggle) {
            toggle.classList.remove('active');
        }

        // Restore regular view
        this.restoreNormalView();
    },

    /**
     * Show comparison panel with run selectors
     */
    showComparisonPanel() {
        let panel = document.getElementById('comparison-panel');

        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'comparison-panel';
            panel.className = 'comparison-panel';
            panel.innerHTML = `
                <div class="comparison-panel-content">
                    <div class="comparison-selector">
                        <label>Compare:</label>
                        <select id="comparison-left-select" class="comparison-select">
                            <option value="">Select Run A...</option>
                        </select>
                    </div>
                    <div class="comparison-vs">vs</div>
                    <div class="comparison-selector">
                        <label>With:</label>
                        <select id="comparison-right-select" class="comparison-select">
                            <option value="">Select Run B...</option>
                        </select>
                    </div>
                    <button id="comparison-apply-btn" class="comparison-apply-btn" disabled>Apply</button>
                    <button id="comparison-close-btn" class="comparison-close-btn">✕</button>
                </div>
            `;
            document.body.appendChild(panel);

            // Populate selects
            this.populateRunSelectors();

            // Attach listeners
            const leftSelect = panel.querySelector('#comparison-left-select');
            const rightSelect = panel.querySelector('#comparison-right-select');
            const applyBtn = panel.querySelector('#comparison-apply-btn');
            const closeBtn = panel.querySelector('#comparison-close-btn');

            leftSelect.addEventListener('change', () => {
                this.runs.left = leftSelect.value ? this.allRuns.find(r => r.id === leftSelect.value) : null;
                this.updateApplyButton();
            });

            rightSelect.addEventListener('change', () => {
                this.runs.right = rightSelect.value ? this.allRuns.find(r => r.id === rightSelect.value) : null;
                this.updateApplyButton();
            });

            applyBtn.addEventListener('click', () => {
                if (this.runs.left && this.runs.right) {
                    this.performComparison();
                }
            });

            closeBtn.addEventListener('click', () => {
                this.disable();
            });
        }

        panel.classList.add('active');
    },

    /**
     * Hide comparison panel
     */
    hideComparisonPanel() {
        const panel = document.getElementById('comparison-panel');
        if (panel) {
            panel.classList.remove('active');
        }
    },

    /**
     * Populate run selectors with available runs
     */
    populateRunSelectors() {
        const leftSelect = document.getElementById('comparison-left-select');
        const rightSelect = document.getElementById('comparison-right-select');

        if (!leftSelect || !rightSelect) return;

        // Clear existing options (except first)
        leftSelect.querySelectorAll('option:not(:first-child)').forEach(opt => opt.remove());
        rightSelect.querySelectorAll('option:not(:first-child)').forEach(opt => opt.remove());

        // Add run options
        this.allRuns.forEach(run => {
            const timestamp = new Date(run.timestamp).toLocaleString();
            const sourcesCount = run.sources.length;

            const optionLeft = document.createElement('option');
            optionLeft.value = run.id;
            optionLeft.textContent = `${timestamp} (${sourcesCount} sources)`;
            leftSelect.appendChild(optionLeft);

            const optionRight = document.createElement('option');
            optionRight.value = run.id;
            optionRight.textContent = `${timestamp} (${sourcesCount} sources)`;
            rightSelect.appendChild(optionRight);
        });
    },

    /**
     * Update apply button state
     */
    updateApplyButton() {
        const applyBtn = document.getElementById('comparison-apply-btn');
        if (applyBtn) {
            applyBtn.disabled = !(this.runs.left && this.runs.right && this.runs.left.id !== this.runs.right.id);
        }
    },

    /**
     * Perform comparison of selected runs
     */
    performComparison() {
        if (!this.runs.left || !this.runs.right) return;

        // Create split view
        this.createSplitView();

        // Load data for both runs
        this.loadComparisonData();

        // Show comparison summary
        this.showComparisonSummary();
    },

    /**
     * Create split-screen layout
     */
    createSplitView() {
        // Hide normal tab panels
        const tabPanels = document.querySelectorAll('.tab-content');
        tabPanels.forEach(panel => {
            panel.dataset.normalDisplay = panel.style.display || '';
            panel.style.display = 'none';
        });

        // Create or show split view container
        let splitView = document.getElementById('comparison-split-view');

        if (!splitView) {
            splitView = document.createElement('div');
            splitView.id = 'comparison-split-view';
            splitView.className = 'comparison-split-view';
            splitView.innerHTML = `
                <div class="comparison-pane comparison-pane-left">
                    <div class="comparison-pane-header">
                        <h3>Run A</h3>
                        <span class="comparison-pane-timestamp"></span>
                    </div>
                    <div class="comparison-pane-content"></div>
                </div>
                <div class="comparison-divider"></div>
                <div class="comparison-pane comparison-pane-right">
                    <div class="comparison-pane-header">
                        <h3>Run B</h3>
                        <span class="comparison-pane-timestamp"></span>
                    </div>
                    <div class="comparison-pane-content"></div>
                </div>
            `;

            const tabsSection = document.querySelector('.dashboard-tabs');
            if (tabsSection) {
                tabsSection.after(splitView);
            }

            // Enable synchronized scrolling
            this.enableSyncScroll();
        }

        splitView.style.display = 'flex';
    },

    /**
     * Restore normal view
     */
    restoreNormalView() {
        // Show normal tab panels
        const tabPanels = document.querySelectorAll('.tab-content');
        tabPanels.forEach(panel => {
            panel.style.display = panel.dataset.normalDisplay || '';
        });

        // Hide split view
        const splitView = document.getElementById('comparison-split-view');
        if (splitView) {
            splitView.style.display = 'none';
        }
    },

    /**
     * Load comparison data for both runs
     */
    loadComparisonData() {
        const leftPane = document.querySelector('.comparison-pane-left .comparison-pane-content');
        const rightPane = document.querySelector('.comparison-pane-right .comparison-pane-content');

        if (!leftPane || !rightPane) return;

        // Update timestamps
        const leftTimestamp = document.querySelector('.comparison-pane-left .comparison-pane-timestamp');
        const rightTimestamp = document.querySelector('.comparison-pane-right .comparison-pane-timestamp');

        if (leftTimestamp) {
            leftTimestamp.textContent = new Date(this.runs.left.timestamp).toLocaleString();
        }
        if (rightTimestamp) {
            rightTimestamp.textContent = new Date(this.runs.right.timestamp).toLocaleString();
        }

        // Generate comparison cards
        const leftCards = this.generateComparisonCards(this.runs.left.metrics);
        const rightCards = this.generateComparisonCards(this.runs.right.metrics);

        leftPane.innerHTML = leftCards;
        rightPane.innerHTML = rightCards;
    },

    /**
     * Generate comparison cards for a run
     */
    generateComparisonCards(metrics) {
        const aggregates = this.calculateAggregates(metrics);

        return `
            <div class="comparison-metrics-grid">
                <div class="comparison-metric-card">
                    <div class="comparison-metric-label">Total Records</div>
                    <div class="comparison-metric-value">${this.formatNumber(aggregates.totalRecords)}</div>
                </div>
                <div class="comparison-metric-card">
                    <div class="comparison-metric-label">Data Sources</div>
                    <div class="comparison-metric-value">${aggregates.totalSources}</div>
                </div>
                <div class="comparison-metric-card">
                    <div class="comparison-metric-label">Avg Quality Rate</div>
                    <div class="comparison-metric-value">${aggregates.avgQuality.toFixed(1)}%</div>
                </div>
                <div class="comparison-metric-card">
                    <div class="comparison-metric-label">Avg Success Rate</div>
                    <div class="comparison-metric-value">${aggregates.avgSuccess.toFixed(1)}%</div>
                </div>
            </div>

            <div class="comparison-source-list">
                <h4>Sources Breakdown</h4>
                ${metrics.map(m => this.generateSourceCard(m)).join('')}
            </div>
        `;
    },

    /**
     * Generate source card for comparison
     */
    generateSourceCard(metric) {
        const source = this.getSourceName(metric._source || metric.source);
        const records = metric.layered_metrics?.volume?.records_written || 0;
        const quality = (metric.legacy_metrics?.statistics?.quality_pass_rate || 0) * 100;

        return `
            <div class="comparison-source-card">
                <div class="comparison-source-name">${source}</div>
                <div class="comparison-source-metrics">
                    <span>${this.formatNumber(records)} records</span>
                    <span>${quality.toFixed(1)}% quality</span>
                </div>
            </div>
        `;
    },

    /**
     * Show comparison summary with diff indicators
     */
    showComparisonSummary() {
        const leftMetrics = this.runs.left.metrics;
        const rightMetrics = this.runs.right.metrics;

        const leftAgg = this.calculateAggregates(leftMetrics);
        const rightAgg = this.calculateAggregates(rightMetrics);

        // Create summary card
        let summary = document.getElementById('comparison-summary');

        if (!summary) {
            summary = document.createElement('div');
            summary.id = 'comparison-summary';
            summary.className = 'comparison-summary';

            const splitView = document.getElementById('comparison-split-view');
            if (splitView) {
                splitView.before(summary);
            }
        }

        const diffs = {
            records: this.calculateDiff(leftAgg.totalRecords, rightAgg.totalRecords),
            sources: this.calculateDiff(leftAgg.totalSources, rightAgg.totalSources),
            quality: this.calculateDiff(leftAgg.avgQuality, rightAgg.avgQuality),
            success: this.calculateDiff(leftAgg.avgSuccess, rightAgg.avgSuccess)
        };

        summary.innerHTML = `
            <h3>Comparison Summary</h3>
            <div class="comparison-summary-grid">
                <div class="comparison-summary-item">
                    <span class="comparison-summary-label">Total Records</span>
                    <span class="comparison-summary-diff ${diffs.records.className}">
                        ${diffs.records.icon} ${Math.abs(diffs.records.value).toFixed(0)}
                        <small>(${diffs.records.percent.toFixed(1)}%)</small>
                    </span>
                </div>
                <div class="comparison-summary-item">
                    <span class="comparison-summary-label">Data Sources</span>
                    <span class="comparison-summary-diff ${diffs.sources.className}">
                        ${diffs.sources.icon} ${Math.abs(diffs.sources.value).toFixed(0)}
                    </span>
                </div>
                <div class="comparison-summary-item">
                    <span class="comparison-summary-label">Quality Rate</span>
                    <span class="comparison-summary-diff ${diffs.quality.className}">
                        ${diffs.quality.icon} ${Math.abs(diffs.quality.value).toFixed(1)}%
                        <small>(${diffs.quality.percent.toFixed(1)}%)</small>
                    </span>
                </div>
                <div class="comparison-summary-item">
                    <span class="comparison-summary-label">Success Rate</span>
                    <span class="comparison-summary-diff ${diffs.success.className}">
                        ${diffs.success.icon} ${Math.abs(diffs.success.value).toFixed(1)}%
                        <small>(${diffs.success.percent.toFixed(1)}%)</small>
                    </span>
                </div>
            </div>
        `;

        summary.style.display = 'block';
    },

    /**
     * Calculate difference with formatting
     */
    calculateDiff(leftValue, rightValue) {
        const diff = rightValue - leftValue;
        const percent = leftValue > 0 ? (diff / leftValue) * 100 : 0;

        return {
            value: diff,
            percent: percent,
            className: diff > 0 ? 'increase' : diff < 0 ? 'decrease' : 'neutral',
            icon: diff > 0 ? '△' : diff < 0 ? '▽' : '='
        };
    },

    /**
     * Calculate aggregates for metrics
     */
    calculateAggregates(metrics) {
        const totalRecords = metrics.reduce((sum, m) => {
            return sum + (m.layered_metrics?.volume?.records_written || 0);
        }, 0);

        const sources = new Set(metrics.map(m => m._source || m.source));
        const totalSources = sources.size;

        const avgQuality = metrics.reduce((sum, m) => {
            return sum + ((m.legacy_metrics?.statistics?.quality_pass_rate || 0) * 100);
        }, 0) / metrics.length;

        const avgSuccess = metrics.reduce((sum, m) => {
            const layered = m.layered_metrics || {};
            const success = layered.connectivity?.connection_successful && (layered.volume?.records_written || 0) > 0;
            return sum + (success ? 100 : 0);
        }, 0) / metrics.length;

        return {
            totalRecords,
            totalSources,
            avgQuality: avgQuality || 0,
            avgSuccess: avgSuccess || 0
        };
    },

    /**
     * Enable synchronized scrolling between panes
     */
    enableSyncScroll() {
        const leftPane = document.querySelector('.comparison-pane-left .comparison-pane-content');
        const rightPane = document.querySelector('.comparison-pane-right .comparison-pane-content');

        if (!leftPane || !rightPane) return;

        let isSyncing = false;

        const syncScroll = (source, target) => {
            if (isSyncing) return;
            isSyncing = true;

            const scrollPercentage = source.scrollTop / (source.scrollHeight - source.clientHeight);
            target.scrollTop = scrollPercentage * (target.scrollHeight - target.clientHeight);

            setTimeout(() => {
                isSyncing = false;
            }, 10);
        };

        leftPane.addEventListener('scroll', () => syncScroll(leftPane, rightPane));
        rightPane.addEventListener('scroll', () => syncScroll(rightPane, leftPane));
    },

    /**
     * Get source name
     */
    getSourceName(fullSource) {
        if (!fullSource) return 'Unknown';
        return fullSource
            .replace(/-Somali|_Somali_c4-so|-somali/gi, '')
            .replace('Sprakbanken', 'Språkbanken')
            .trim();
    },

    /**
     * Format number with K/M suffixes
     */
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toLocaleString();
    }
};
