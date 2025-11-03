import { getSourceCatalog } from '../core/data-service.js';

/**
 * Filter Manager - Advanced Filtering and Date Range Selection
 * Handles source filtering, quality thresholds, date ranges, and URL state management
 */

export const FilterManager = {
    filters: {
        sources: [], // Selected sources
        qualityThreshold: 0, // Minimum quality threshold (0-100)
        status: 'all', // 'all', 'success', 'failed'
        dateRange: {
            start: null,
            end: null,
            preset: 'all' // 'all', 'last7days', 'last30days', 'custom'
        },
        acquisitionMethods: [],
        integrationStages: []
    },

    allMetrics: [], // Store all metrics for filtering
    listeners: [],
    lastFilteredMetrics: [],
    catalog: null,
    chipUpdateCallback: null,

    /**
     * Initialize filter manager
     */
    init(metrics) {
        this.allMetrics = metrics || [];
        this.catalog = getSourceCatalog();

        // Load filters from URL or localStorage
        this.loadFiltersFromURL();

        // Create filter UI
        this.createFilterPanel();

        // Apply initial filters
        this.applyFilters();
    },

    /**
     * Create filter panel UI
     */
    createFilterPanel() {
        const dashboardTabs = document.querySelector('.dashboard-tabs .container');
        if (!dashboardTabs) return;

        // Create filter toggle button
        const filterToggle = document.createElement('button');
        filterToggle.id = 'filter-toggle';
        filterToggle.className = 'filter-toggle-btn';
        filterToggle.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            <span>Filters</span>
            <span class="filter-count" style="display: none;">0</span>
        `;
        filterToggle.addEventListener('click', () => this.toggleFilterPanel());

        dashboardTabs.appendChild(filterToggle);

        // Create filter panel
        const filterPanel = document.createElement('div');
        filterPanel.id = 'filter-panel';
        filterPanel.className = 'filter-panel';
        filterPanel.innerHTML = `
            <div class="filter-panel-header">
                <h3>Filter Data</h3>
                <button class="filter-panel-close" aria-label="Close filters">&times;</button>
            </div>
            <div class="filter-panel-body">
                <!-- Date Range Filter -->
                <div class="filter-section">
                    <h4>Date Range</h4>
                    <div class="filter-date-presets">
                        <button class="filter-preset-btn active" data-preset="all">All Time</button>
                        <button class="filter-preset-btn" data-preset="last7days">Last 7 Days</button>
                        <button class="filter-preset-btn" data-preset="last30days">Last 30 Days</button>
                        <button class="filter-preset-btn" data-preset="custom">Custom Range</button>
                    </div>
                    <div class="filter-date-custom" style="display: none;">
                        <div class="filter-input-group">
                            <label for="filter-date-start">Start Date</label>
                            <input type="date" id="filter-date-start" class="filter-input">
                        </div>
                        <div class="filter-input-group">
                            <label for="filter-date-end">End Date</label>
                            <input type="date" id="filter-date-end" class="filter-input">
                        </div>
                    </div>
                </div>

                <!-- Source Filter -->
                <div class="filter-section">
                    <h4>Data Sources</h4>
                    <div class="filter-checkboxes">
                        <label class="filter-checkbox">
                            <input type="checkbox" value="Wikipedia" checked>
                            <span class="filter-checkbox-label">Wikipedia</span>
                        </label>
                        <label class="filter-checkbox">
                            <input type="checkbox" value="BBC" checked>
                            <span class="filter-checkbox-label">BBC</span>
                        </label>
                        <label class="filter-checkbox">
                            <input type="checkbox" value="HuggingFace" checked>
                            <span class="filter-checkbox-label">HuggingFace</span>
                        </label>
                        <label class="filter-checkbox">
                            <input type="checkbox" value="Sprakbanken" checked>
                            <span class="filter-checkbox-label">Språkbanken</span>
                        </label>
                        <label class="filter-checkbox">
                            <input type="checkbox" value="TikTok" checked>
                            <span class="filter-checkbox-label">TikTok</span>
                        </label>
                    </div>
                </div>

                <!-- Quality Threshold Filter -->
                <div class="filter-section">
                    <h4>Quality Threshold</h4>
                    <div class="filter-slider-group">
                        <input type="range" id="quality-threshold-slider" class="filter-slider" min="0" max="100" value="0" step="5">
                        <div class="filter-slider-labels">
                            <span>0%</span>
                            <span class="filter-slider-value">0%</span>
                            <span>100%</span>
                        </div>
                    </div>
                    <p class="filter-help-text">Show only sources with quality rate above this threshold</p>
                </div>

                <!-- Status Filter -->
                <div class="filter-section">
                    <h4>Pipeline Status</h4>
                    <div class="filter-radio-group">
                        <label class="filter-radio">
                            <input type="radio" name="status-filter" value="all" checked>
                            <span>All</span>
                        </label>
                        <label class="filter-radio">
                            <input type="radio" name="status-filter" value="success">
                            <span>Success Only</span>
                        </label>
                        <label class="filter-radio">
                            <input type="radio" name="status-filter" value="failed">
                            <span>Failed Only</span>
                        </label>
                    </div>
                </div>
            </div>
            <div class="filter-panel-footer">
                <button class="filter-btn filter-btn-secondary" id="filter-reset-btn">Reset All</button>
                <button class="filter-btn filter-btn-primary" id="filter-apply-btn">Apply Filters</button>
            </div>
        `;

        document.body.appendChild(filterPanel);

        // Attach event listeners
        this.attachFilterListeners();
    },

    /**
     * Attach event listeners to filter controls
     */
    attachFilterListeners() {
        const panel = document.getElementById('filter-panel');
        if (!panel) return;

        // Close button
        const closeBtn = panel.querySelector('.filter-panel-close');
        closeBtn.addEventListener('click', () => this.toggleFilterPanel());

        // Date presets
        const presetBtns = panel.querySelectorAll('.filter-preset-btn');
        presetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                presetBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const preset = btn.dataset.preset;
                const customRangeDiv = panel.querySelector('.filter-date-custom');

                if (preset === 'custom') {
                    customRangeDiv.style.display = 'block';
                } else {
                    customRangeDiv.style.display = 'none';
                    this.setDatePreset(preset);
                }
            });
        });

        // Date inputs
        const startDate = panel.querySelector('#filter-date-start');
        const endDate = panel.querySelector('#filter-date-end');

        startDate.addEventListener('change', () => {
            this.filters.dateRange.start = startDate.value ? new Date(startDate.value) : null;
        });

        endDate.addEventListener('change', () => {
            this.filters.dateRange.end = endDate.value ? new Date(endDate.value) : null;
        });

        // Quality slider
        const qualitySlider = panel.querySelector('#quality-threshold-slider');
        const qualityValue = panel.querySelector('.filter-slider-value');

        qualitySlider.addEventListener('input', () => {
            qualityValue.textContent = qualitySlider.value + '%';
        });

        // Apply button
        const applyBtn = panel.querySelector('#filter-apply-btn');
        applyBtn.addEventListener('click', () => {
            this.collectFilters();
            this.applyFilters();
            this.toggleFilterPanel();
        });

        // Reset button
        const resetBtn = panel.querySelector('#filter-reset-btn');
        resetBtn.addEventListener('click', () => {
            this.resetFilters();
        });
    },

    /**
     * Set date range preset
     */
    setDatePreset(preset) {
        const now = new Date();
        const start = new Date();

        switch (preset) {
            case 'last7days':
                start.setDate(now.getDate() - 7);
                this.filters.dateRange.start = start;
                this.filters.dateRange.end = now;
                this.filters.dateRange.preset = preset;
                break;

            case 'last30days':
                start.setDate(now.getDate() - 30);
                this.filters.dateRange.start = start;
                this.filters.dateRange.end = now;
                this.filters.dateRange.preset = preset;
                break;

            case 'all':
            default:
                this.filters.dateRange.start = null;
                this.filters.dateRange.end = null;
                this.filters.dateRange.preset = 'all';
                break;
        }
    },

    /**
     * Collect filter values from UI
     */
    collectFilters() {
        const panel = document.getElementById('filter-panel');
        if (!panel) return;

        // Source checkboxes
        const sourceCheckboxes = panel.querySelectorAll('.filter-checkboxes input[type="checkbox"]');
        this.filters.sources = Array.from(sourceCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        // Quality threshold
        const qualitySlider = panel.querySelector('#quality-threshold-slider');
        this.filters.qualityThreshold = parseInt(qualitySlider.value);

        // Status filter
        const statusRadio = panel.querySelector('input[name="status-filter"]:checked');
        this.filters.status = statusRadio.value;
    },

    /**
     * Apply filters to metrics
     */
    applyFilters() {
        const filtered = this.allMetrics.filter(metric => {
            if (!metric) return false;

            // Source filter
            const sourceName = this.getSourceName(metric._source || metric.source);
            if (this.filters.sources.length > 0 && !this.filters.sources.includes(sourceName)) {
                return false;
            }

            const sourceInfo = this.catalog?.sources?.[sourceName] || {};
            const acquisitionMethod = sourceInfo.acquisitionMethod || 'Unspecified';
            const integrationStage = sourceInfo.integrationStage || 'Planned';

            if (this.filters.acquisitionMethods.length > 0 && !this.filters.acquisitionMethods.includes(acquisitionMethod)) {
                return false;
            }

            if (this.filters.integrationStages.length > 0 && !this.filters.integrationStages.includes(integrationStage)) {
                return false;
            }

            // Quality threshold filter
            const qualityRate = this.getQualityRate(metric);
            if (qualityRate < this.filters.qualityThreshold) {
                return false;
            }

            // Status filter
            if (this.filters.status !== 'all') {
                const isSuccess = this.isSuccessful(metric);
                if (this.filters.status === 'success' && !isSuccess) return false;
                if (this.filters.status === 'failed' && isSuccess) return false;
            }

            // Date range filter
            if (this.filters.dateRange.start || this.filters.dateRange.end) {
                const metricDate = new Date(metric._timestamp || metric.timestamp);

                if (this.filters.dateRange.start && metricDate < this.filters.dateRange.start) {
                    return false;
                }

                if (this.filters.dateRange.end && metricDate > this.filters.dateRange.end) {
                    return false;
                }
            }

            return true;
        });

        this.lastFilteredMetrics = filtered;

        // Update filter count badge
        this.updateFilterCount();

        // Update URL with filter state
        this.updateURL();

        // Notify listeners
        this.notifyListeners(filtered);

        return filtered;
    },

    setChipUpdateCallback(callback) {
        this.chipUpdateCallback = callback;
    },

    isAcquisitionMethodActive(method) {
        return this.filters.acquisitionMethods.includes(method);
    },

    isIntegrationStageActive(stage) {
        return this.filters.integrationStages.includes(stage);
    },

    toggleAcquisitionMethod(method) {
        if (!method) return;
        if (this.isAcquisitionMethodActive(method)) {
            this.filters.acquisitionMethods = this.filters.acquisitionMethods.filter(value => value !== method);
        } else {
            this.filters.acquisitionMethods = [...this.filters.acquisitionMethods, method];
        }
        this.applyFilters();
        if (typeof this.chipUpdateCallback === 'function') {
            this.chipUpdateCallback();
        }
    },

    toggleIntegrationStage(stage) {
        if (!stage) return;
        if (this.isIntegrationStageActive(stage)) {
            this.filters.integrationStages = this.filters.integrationStages.filter(value => value !== stage);
        } else {
            this.filters.integrationStages = [...this.filters.integrationStages, stage];
        }
        this.applyFilters();
        if (typeof this.chipUpdateCallback === 'function') {
            this.chipUpdateCallback();
        }
    },

    /**
     * Reset all filters
     */
    resetFilters() {
        this.filters = {
            sources: [],
            qualityThreshold: 0,
            status: 'all',
            dateRange: {
                start: null,
                end: null,
                preset: 'all'
            },
            acquisitionMethods: [],
            integrationStages: []
        };

        // Reset UI
        const panel = document.getElementById('filter-panel');
        if (panel) {
            // Reset checkboxes
            panel.querySelectorAll('.filter-checkboxes input[type="checkbox"]').forEach(cb => {
                cb.checked = true;
            });

            // Reset quality slider
            const qualitySlider = panel.querySelector('#quality-threshold-slider');
            qualitySlider.value = 0;
            panel.querySelector('.filter-slider-value').textContent = '0%';

            // Reset status radio
            panel.querySelector('input[name="status-filter"][value="all"]').checked = true;

            // Reset date presets
            panel.querySelectorAll('.filter-preset-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.preset === 'all');
            });

            panel.querySelector('.filter-date-custom').style.display = 'none';
        }

        this.applyFilters();
        if (typeof this.chipUpdateCallback === 'function') {
            this.chipUpdateCallback();
        }
    },

    /**
     * Toggle filter panel visibility
     */
    toggleFilterPanel() {
        const panel = document.getElementById('filter-panel');
        if (panel) {
            panel.classList.toggle('active');
        }
    },

    /**
     * Update filter count badge
     */
    updateFilterCount() {
        const badge = document.querySelector('.filter-count');
        if (!badge) return;

        let activeFilters = 0;
        const totalSources = Object.keys(this.catalog?.sources || {}).length || 0;

        // Count active filters
        if (this.filters.sources.length > 0 && (totalSources === 0 || this.filters.sources.length < totalSources)) {
            activeFilters++;
        }

        if (this.filters.qualityThreshold > 0) {
            activeFilters++;
        }

        if (this.filters.status !== 'all') {
            activeFilters++;
        }

        if (this.filters.dateRange.preset !== 'all') {
            activeFilters++;
        }

        if (this.filters.acquisitionMethods.length > 0) {
            activeFilters++;
        }

        if (this.filters.integrationStages.length > 0) {
            activeFilters++;
        }

        // Update badge
        if (activeFilters > 0) {
            badge.textContent = activeFilters;
            badge.style.display = 'inline-flex';
        } else {
            badge.style.display = 'none';
        }
    },

    /**
     * Load filters from URL parameters
     */
    loadFiltersFromURL() {
        const params = new URLSearchParams(window.location.search);

        // Sources
        const sources = params.get('sources');
        if (sources) {
            this.filters.sources = sources.split(',');
        }

        // Quality threshold
        const quality = params.get('quality');
        if (quality) {
            this.filters.qualityThreshold = parseInt(quality);
        }

        // Status
        const status = params.get('status');
        if (status) {
            this.filters.status = status;
        }

        // Date range
        const datePreset = params.get('datePreset');
        if (datePreset) {
            this.setDatePreset(datePreset);
        }

        const acquisition = params.get('acquisition');
        if (acquisition) {
            this.filters.acquisitionMethods = acquisition.split(',');
        }

        const stage = params.get('stage');
        if (stage) {
            this.filters.integrationStages = stage.split(',');
        }
    },

    /**
     * Update URL with current filter state
     */
    updateURL() {
        const params = new URLSearchParams();

        // Add filters to URL
        const totalSources = Object.keys(this.catalog?.sources || {}).length || 0;
        if (this.filters.sources.length > 0 && (totalSources === 0 || this.filters.sources.length < totalSources)) {
            params.set('sources', this.filters.sources.join(','));
        }

        if (this.filters.qualityThreshold > 0) {
            params.set('quality', this.filters.qualityThreshold);
        }

        if (this.filters.status !== 'all') {
            params.set('status', this.filters.status);
        }

        if (this.filters.dateRange.preset !== 'all') {
            params.set('datePreset', this.filters.dateRange.preset);
        }

        if (this.filters.acquisitionMethods.length > 0) {
            params.set('acquisition', this.filters.acquisitionMethods.join(','));
        }

        if (this.filters.integrationStages.length > 0) {
            params.set('stage', this.filters.integrationStages.join(','));
        }

        // Update URL without reload
        const newURL = params.toString() ? `?${params.toString()}` : window.location.pathname;
        window.history.replaceState({}, '', newURL);
    },

    /**
     * Register listener for filter changes
     */
    onFilterChange(callback) {
        this.listeners.push(callback);
    },

    /**
     * Notify all listeners of filter change
     */
    notifyListeners(filteredMetrics) {
        this.listeners.forEach(callback => {
            callback(filteredMetrics, this.filters);
        });
    },

    /**
     * Get source name from metric
     */
    getSourceName(fullSource) {
        if (!fullSource) return 'Unknown';
        return fullSource
            .replace(/-Somali|_Somali_c4-so|-somali/gi, '')
            .replace('Sprakbanken', 'Språkbanken')
            .trim();
    },

    /**
     * Get quality rate from metric
     */
    getQualityRate(metric) {
        // Bug Fix #7: Use normalized quality_pass_rate (not legacy_metrics)
        return (metric.quality_pass_rate || 0) * 100;
    },

    /**
     * Check if metric represents successful pipeline run
     */
    isSuccessful(metric) {
        const layered = metric.layered_metrics || {};
        const connectivity = layered.connectivity || {};
        const volume = layered.volume || {};

        return connectivity.connection_successful && (volume.records_written || 0) > 0;
    }
};
