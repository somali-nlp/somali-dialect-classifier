/**
 * Chart Utilities and Component Abstractions
 * Reusable charting components for the Somali Dialect Classifier Dashboard
 */

// Chart.js Configuration Presets
const ChartPresets = {
    // Base theme colors
    colors: {
        primary: '#0176D3',
        secondary: '#032D60',
        success: '#00A651',
        warning: '#f59e0b',
        error: '#ef4444',
        wikipedia: '#3b82f6',
        bbc: '#ef4444',
        huggingface: '#00A651',
        sprakbanken: '#f59e0b',
        gray: {
            50: '#f9fafb',
            100: '#f3f4f6',
            200: '#e5e7eb',
            300: '#d1d5db',
            500: '#6b7280',
            700: '#374151'
        }
    },

    // Common Chart.js options
    commonOptions: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: {
                    font: {
                        family: "'Inter', sans-serif",
                        size: 12,
                        weight: '500'
                    },
                    padding: 15,
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleFont: {
                    family: "'Inter', sans-serif",
                    size: 13,
                    weight: '600'
                },
                bodyFont: {
                    family: "'Inter', sans-serif",
                    size: 12
                },
                padding: 12,
                cornerRadius: 8,
                displayColors: true,
                boxPadding: 6
            }
        }
    },

    // Radial/Polar chart options
    radialOptions: function(title) {
        return {
            ...this.commonOptions,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        callback: value => value + '%',
                        backdropColor: 'transparent',
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: this.colors.gray[200]
                    },
                    pointLabels: {
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    }
                }
            },
            plugins: {
                ...this.commonOptions.plugins,
                title: {
                    display: !!title,
                    text: title,
                    font: {
                        size: 16,
                        weight: '600'
                    },
                    padding: 20
                }
            }
        };
    },

    // Bar chart options
    barOptions: function(horizontal = false) {
        return {
            ...this.commonOptions,
            indexAxis: horizontal ? 'y' : 'x',
            scales: {
                x: {
                    grid: {
                        display: !horizontal,
                        color: this.colors.gray[100]
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        display: horizontal,
                        color: this.colors.gray[100]
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            }
        };
    },

    // Line/Timeline chart options
    timelineOptions: function() {
        return {
            ...this.commonOptions,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        }
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: this.colors.gray[100]
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            }
        };
    }
};

// Data Processing Utilities
const DataUtils = {
    /**
     * Get source color based on source name
     */
    getSourceColor(sourceName) {
        if (!sourceName) return ChartPresets.colors.gray[500];
        const name = sourceName.toLowerCase();
        if (name.includes('wikipedia')) return ChartPresets.colors.wikipedia;
        if (name.includes('bbc')) return ChartPresets.colors.bbc;
        if (name.includes('huggingface')) return ChartPresets.colors.huggingface;
        if (name.includes('sprakbanken')) return ChartPresets.colors.sprakbanken;
        return ChartPresets.colors.gray[500];
    },

    /**
     * Clean source name for display
     */
    cleanSourceName(sourceName) {
        if (!sourceName) return 'Unknown';
        return sourceName
            .replace(/-Somali|_Somali_c4-so|-somali/g, '')
            .replace('Sprakbanken', 'Språkbanken')
            .replace('HuggingFace', 'HuggingFace')
            .trim();
    },

    /**
     * Calculate aggregate metrics from data array
     */
    calculateAggregates(metrics) {
        if (!metrics || metrics.length === 0) {
            return {
                totalRecords: 0,
                totalSources: 0,
                avgQualityRate: 0,
                avgSuccessRate: 0
            };
        }

        const validMetrics = metrics.filter(m => m && m.source);

        return {
            totalRecords: validMetrics.reduce((sum, m) => sum + (m.records_written || 0), 0),
            totalSources: new Set(validMetrics.map(m => m.source.split('-')[0])).size,
            avgQualityRate: this.average(validMetrics.map(m => {
                if (m.pipeline_metrics?.quality_pass_rate != null) {
                    return m.pipeline_metrics.quality_pass_rate * 100;
                }
                return 0;
            })),
            avgSuccessRate: this.average(validMetrics.map(m => (m.success_rate || 0) * 100))
        };
    },

    /**
     * Calculate average of array
     */
    average(arr) {
        if (!arr || arr.length === 0) return 0;
        const validValues = arr.filter(v => v != null && !isNaN(v));
        if (validValues.length === 0) return 0;
        return validValues.reduce((sum, val) => sum + val, 0) / validValues.length;
    },

    /**
     * Get text length statistics from metric
     */
    getTextLengthStats(metric) {
        if (!metric) return null;

        // Try legacy_metrics first
        if (metric.legacy_metrics?.statistics?.text_length_stats) {
            return metric.legacy_metrics.statistics.text_length_stats;
        }

        // Fall back to quality object
        if (metric.quality) {
            return metric.quality;
        }

        return null;
    },

    /**
     * Format number with K/M suffixes
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    },

    /**
     * Create histogram bins from array of values
     */
    createHistogram(values, binCount = 20) {
        if (!values || values.length === 0) return { bins: [], counts: [] };

        const min = Math.min(...values);
        const max = Math.max(...values);
        const binWidth = (max - min) / binCount;

        const bins = [];
        const counts = new Array(binCount).fill(0);

        for (let i = 0; i < binCount; i++) {
            bins.push(min + i * binWidth);
        }

        values.forEach(value => {
            const binIndex = Math.min(Math.floor((value - min) / binWidth), binCount - 1);
            counts[binIndex]++;
        });

        return { bins, counts };
    }
};

// Chart Component Factory
const ChartFactory = {
    /**
     * Create a radial progress chart (coverage scorecard)
     */
    createRadialProgress(ctx, data, options = {}) {
        return new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: data.colors || data.labels.map(l => DataUtils.getSourceColor(l)),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                ...ChartPresets.radialOptions(options.title),
                ...options.customOptions
            }
        });
    },

    /**
     * Create a distribution comparison chart
     */
    createDistributionComparison(ctx, data, options = {}) {
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, idx) => ({
                    label: dataset.label,
                    data: dataset.data,
                    backgroundColor: dataset.color || DataUtils.getSourceColor(dataset.label),
                    borderRadius: 6,
                    barThickness: options.barThickness || 'flex'
                }))
            },
            options: {
                ...ChartPresets.barOptions(options.horizontal),
                ...options.customOptions
            }
        });
    },

    /**
     * Create a timeline chart
     */
    createTimeline(ctx, data, options = {}) {
        return new Chart(ctx, {
            type: 'line',
            data: {
                datasets: data.datasets.map(dataset => ({
                    label: dataset.label,
                    data: dataset.data,
                    borderColor: dataset.color || DataUtils.getSourceColor(dataset.label),
                    backgroundColor: dataset.color + '20' || DataUtils.getSourceColor(dataset.label) + '20',
                    fill: options.fill !== false,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }))
            },
            options: {
                ...ChartPresets.timelineOptions(),
                ...options.customOptions
            }
        });
    }
};

// Feature Flag Management
const FeatureFlags = {
    flags: {
        audienceMode: false,
        advancedCharts: false,
        sankeyDiagram: false,
        ridgePlots: false
    },

    enable(flagName) {
        if (this.flags.hasOwnProperty(flagName)) {
            this.flags[flagName] = true;
            localStorage.setItem(`feature_${flagName}`, 'true');
            this.notifyChange(flagName, true);
        }
    },

    disable(flagName) {
        if (this.flags.hasOwnProperty(flagName)) {
            this.flags[flagName] = false;
            localStorage.setItem(`feature_${flagName}`, 'false');
            this.notifyChange(flagName, false);
        }
    },

    isEnabled(flagName) {
        const stored = localStorage.getItem(`feature_${flagName}`);
        if (stored !== null) {
            return stored === 'true';
        }
        return this.flags[flagName];
    },

    loadFromStorage() {
        Object.keys(this.flags).forEach(flagName => {
            const stored = localStorage.getItem(`feature_${flagName}`);
            if (stored !== null) {
                this.flags[flagName] = stored === 'true';
            }
        });
    },

    notifyChange(flagName, enabled) {
        window.dispatchEvent(new CustomEvent('featureFlagChange', {
            detail: { flag: flagName, enabled }
        }));
    }
};

// Audience Mode Manager
const AudienceMode = {
    modes: {
        STORY: 'story',
        ANALYST: 'analyst'
    },

    currentMode: 'story',

    init() {
        const saved = localStorage.getItem('audienceMode');
        if (saved && Object.values(this.modes).includes(saved)) {
            this.currentMode = saved;
        }
        this.apply();
    },

    setMode(mode) {
        if (!Object.values(this.modes).includes(mode)) return;
        this.currentMode = mode;
        localStorage.setItem('audienceMode', mode);
        this.apply();
        this.notifyChange();
    },

    toggle() {
        const newMode = this.currentMode === this.modes.STORY
            ? this.modes.ANALYST
            : this.modes.STORY;
        this.setMode(newMode);
    },

    apply() {
        document.body.setAttribute('data-audience-mode', this.currentMode);

        // Show/hide elements based on mode
        document.querySelectorAll('[data-show-in]').forEach(el => {
            const showIn = el.getAttribute('data-show-in');
            el.style.display = showIn === this.currentMode ? '' : 'none';
        });
    },

    notifyChange() {
        window.dispatchEvent(new CustomEvent('audienceModeChange', {
            detail: { mode: this.currentMode }
        }));
    }
};

// Export for use in main dashboard
if (typeof window !== 'undefined') {
    window.ChartPresets = ChartPresets;
    window.DataUtils = DataUtils;
    window.ChartFactory = ChartFactory;
    window.FeatureFlags = FeatureFlags;
    window.AudienceMode = AudienceMode;
}
