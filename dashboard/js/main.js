/**
 * Main Dashboard Entry Point
 * Orchestrates all dashboard modules and initialization
 */

// Check for file:// protocol and show user-friendly error
if (window.location.protocol === 'file:') {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        font-family: 'Inter', sans-serif;
        padding: 2rem;
    `;
    errorDiv.innerHTML = `
        <div style="max-width: 600px; text-align: center;">
            <h1 style="font-size: 2rem; margin-bottom: 1rem;">⚠️ HTTP Server Required</h1>
            <p style="font-size: 1.125rem; margin-bottom: 2rem; line-height: 1.6;">
                This dashboard uses ES6 modules and must be run on an HTTP server.
            </p>
            <div style="background: #1f2937; padding: 1.5rem; border-radius: 0.5rem; text-align: left;">
                <p style="font-weight: 600; margin-bottom: 1rem;">Quick Start:</p>
                <pre style="background: #111827; padding: 1rem; border-radius: 0.25rem; overflow-x: auto; margin-bottom: 1rem;">cd _site
python -m http.server 8000</pre>
                <p style="margin-bottom: 0.5rem;">Then open: <a href="http://localhost:8000" style="color: #3b82f6;">http://localhost:8000</a></p>
            </div>
            <p style="margin-top: 2rem; font-size: 0.875rem; opacity: 0.7;">
                See <a href="https://github.com/somali-nlp/somali-dialect-classifier/blob/main/README.md" style="color: #3b82f6;">README.md</a> for more options.
            </p>
        </div>
    `;
    document.body.appendChild(errorDiv);
    throw new Error('Dashboard requires HTTP server (file:// protocol not supported)');
}

// Import core modules
import { loadMetrics, getMetrics } from './core/data-service.js';
import { updateStats } from './core/stats.js';
import { initTabs } from './core/tabs.js';
import { initCharts } from './core/charts.js';
import {
    populateSourceTable,
    populateQualityMetrics,
    populatePerformanceMetrics,
    populateOverviewCards,
    updateQualityMetrics
} from './core/ui-renderer.js';

// Import feature modules
import { initAudienceMode } from './features/audience-mode.js';
import { updateCoverageScorecard, createCoverageRadialChart } from './features/coverage-metrics.js';
import { ThemeManager } from './features/theme-manager.js';
import { FilterManager } from './features/filter-manager.js';
import { ExportManager } from './features/export-manager.js';
import { SankeyChart, RidgePlot, BulletChart } from './features/advanced-charts.js';
import { ComparisonMode } from './features/comparison-mode.js';

// Import utility modules
import { animateCountUp } from './utils/animations.js';
import { initSmoothScroll, initKeyboardNav, initScrollSpy } from './utils/accessibility.js';

/**
 * Main initialization function
 * Loads data and initializes all dashboard components
 */
async function init() {
    console.log('🚀 Initializing dashboard...');

    try {
        // Load data first
        await loadMetrics();

        // Update all stats from loaded data
        updateStats();

        // Initialize core components
        initTabs();
        initCharts();
        populateSourceTable();
        populateQualityMetrics();
        populatePerformanceMetrics();
        populateOverviewCards();

        // Initialize accessibility features
        initSmoothScroll();
        initKeyboardNav();
        initScrollSpy();

        // Initialize enhanced features
        initAudienceMode();
        updateCoverageScorecard();
        createCoverageRadialChart();
        updateQualityMetrics();

        // Animate counts (after stats are updated)
        animateCountUp();

        // Initialize advanced features
        initAdvancedFeatures();

        console.log('✓ Dashboard initialized successfully');
    } catch (error) {
        console.error('✗ Dashboard initialization failed:', error);
    }
}

/**
 * Initialize advanced features
 * Theme manager, filters, export, advanced charts, and comparison mode
 */
function initAdvancedFeatures() {
    const metricsData = getMetrics();

    if (metricsData && metricsData.metrics) {
        // Initialize theme manager
        ThemeManager.init();

        // Initialize filter manager
        FilterManager.init(metricsData.metrics);

        // Listen for filter changes and update charts
        FilterManager.onFilterChange((filteredMetrics) => {
            // Update advanced charts with filtered data
            SankeyChart.create('sankeyContainer', filteredMetrics);
            RidgePlot.create('ridgePlotContainer', filteredMetrics);
        });

        // Create advanced charts
        SankeyChart.create('sankeyContainer', metricsData.metrics);
        RidgePlot.create('ridgePlotContainer', metricsData.metrics);

        // Initialize comparison mode
        ComparisonMode.init(metricsData.metrics);

        // Emit dashboardReady event
        window.dispatchEvent(new CustomEvent('dashboardReady'));
        console.log('✓ Advanced features initialized');
    }
}

// Run on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
