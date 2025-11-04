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
import { loadMetrics, getMetrics, getSankeyFlow, getTextDistributions } from './core/data-service.js';
import { updateStats } from './core/stats.js';
import { initTabs } from './core/tabs.js';
import { initCharts, refreshQualityCharts } from './core/charts.js';
import {
    buildSourceAnalytics,
    populateSourceTable,
    populateSourceMixSnapshot,
    populateSourceBriefings,
    populateIntegrationRoadmap,
    populateQualityOverview,
    populateQualityBriefings,
    populatePerformanceMetrics,
    populateOverviewCards,
} from './core/ui-renderer.js';
import { initializeFilterLabels, computeQualityAnalytics } from './core/aggregates.js';

// Import feature modules
import { initAudienceMode } from './features/audience-mode.js';
import { updateCoverageScorecard, initCoverageCharts, initCoverageMetrics, refreshDataSourceCharts } from './features/coverage-metrics.js';
import { ThemeManager } from './features/theme-manager.js';
import { FilterManager } from './features/filter-manager.js';
import { ExportManager } from './features/export-manager.js';
import { SankeyChart, RidgePlot, BulletChart } from './features/advanced-charts.js';
import { ComparisonMode } from './features/comparison-mode.js';

// Import utility modules
import { Logger } from './utils/logger.js';
import { animateCountUp } from './utils/animations.js';
import { initSmoothScroll, initKeyboardNav, initScrollSpy, initMobileMenu } from './utils/accessibility.js';

/**
 * Main initialization function
 * Loads data and initializes all dashboard components
 * Enhanced with comprehensive error handling and logging
 */
async function init() {
    Logger.info('Initializing dashboard...');

    try {
        // Load filter labels before loading metrics
        // This ensures filter display labels are available when rendering
        await initializeFilterLabels();

        // Load data - critical step
        const metricsData = await loadMetrics();

        if (!metricsData || !metricsData.metrics || metricsData.metrics.length === 0) {
            Logger.warn('Dashboard initialized with empty data state');
            displayEmptyState();
            return;
        }

        // Initialize coverage metrics (loads source mix targets from JSON)
        // This must happen after loadMetrics() but before any chart rendering
        await initCoverageMetrics();

        // Update all stats from loaded data
        updateStats();

        // Initialize core components with individual error handling
        // Bug Fix #6: Wrap each component initialization to prevent cascade failures
        try {
            initTabs();
        } catch (error) {
            Logger.error('Failed to initialize tabs', error);
            // Non-critical: tabs can fail without breaking dashboard
        }

        try {
            initCharts();
        } catch (error) {
            Logger.error('Failed to initialize charts', error);
            // Non-critical: charts can fail without breaking dashboard
        }

        try {
            populateSourceTable();
        } catch (error) {
            Logger.error('Failed to populate source table', error);
            // Non-critical: table can fail without breaking dashboard
        }

        try {
            populateSourceMixSnapshot();
            populateSourceBriefings();
            populateIntegrationRoadmap();
        } catch (error) {
            Logger.error('Failed to populate source mix snapshot', error);
        }

        try {
            populateQualityOverview();
            populateQualityBriefings();
        } catch (error) {
            Logger.error('Failed to populate quality insights', error);
            // Non-critical: quality insights can fail without breaking dashboard
        }

        try {
            populatePerformanceMetrics();
        } catch (error) {
            Logger.error('Failed to populate performance metrics', error);
            // Non-critical: performance metrics can fail without breaking dashboard
        }

        try {
            populateOverviewCards();
        } catch (error) {
            Logger.error('Failed to populate overview cards', error);
            // Non-critical: overview cards can fail without breaking dashboard
        }

        // Initialize accessibility features
        try {
            initSmoothScroll();
            initKeyboardNav();
            initScrollSpy();
            initMobileMenu();
            initExecutiveTabs();
        } catch (error) {
            Logger.warn('Non-critical: Accessibility features failed to initialize', error);
        }

        // Initialize enhanced features
        // NOTE: These must run AFTER loadMetrics() completes to ensure metadata is available
        try {
            initAudienceMode();
            // Wait for metadata to be available before calling functions that depend on it
            updateCoverageScorecard();
            initCoverageCharts();  // Calls getSourceTargetShare() which needs metadata
            populateQualityOverview();
            populateQualityBriefings();
        } catch (error) {
            Logger.warn('Non-critical: Enhanced features failed to initialize', error);
        }

        // Animate counts (after stats are updated)
        try {
            animateCountUp();
        } catch (error) {
            Logger.warn('Non-critical: Count animation failed', error);
        }

        // Initialize advanced features
        try {
            initAdvancedFeatures();
        } catch (error) {
            Logger.warn('Non-critical: Advanced features failed to initialize', error);
        }

        Logger.info('Dashboard initialized successfully');
    } catch (error) {
        Logger.error('Dashboard initialization failed', error);
        displayErrorState(error);
    }
}

/**
 * Display empty state message
 */
function displayEmptyState() {
    const mainContent = document.querySelector('main');
    if (mainContent) {
        const emptyMessage = document.createElement('div');
        emptyMessage.style.cssText = `
            text-align: center;
            padding: 4rem 2rem;
            color: var(--gray-600, #6b7280);
        `;
        emptyMessage.innerHTML = `
            <h2 style="font-size: 1.5rem; margin-bottom: 1rem;">No Data Available</h2>
            <p>Run the data ingestion pipeline to populate the dashboard with metrics.</p>
        `;
        mainContent.prepend(emptyMessage);
    }
}

/**
 * Display error state message
 * @param {Error} error - The error that occurred
 */
function displayErrorState(error) {
    const mainContent = document.querySelector('main');
    if (mainContent) {
        const errorMessage = document.createElement('div');
        errorMessage.style.cssText = `
            text-align: center;
            padding: 4rem 2rem;
            color: var(--red-600, #dc2626);
        `;
        errorMessage.innerHTML = `
            <h2 style="font-size: 1.5rem; margin-bottom: 1rem;">⚠ Initialization Error</h2>
            <p style="margin-bottom: 1rem;">The dashboard failed to initialize properly.</p>
            <details style="max-width: 600px; margin: 0 auto; text-align: left;">
                <summary style="cursor: pointer; color: var(--gray-600, #6b7280);">Show error details</summary>
                <pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.25rem; overflow-x: auto; margin-top: 1rem; font-size: 0.875rem;">${error.message}\n${error.stack || ''}</pre>
            </details>
        `;
        mainContent.prepend(errorMessage);
    }
}

/**
 * Initialize executive dashboard tabs
 */
function initExecutiveTabs() {
    const buttons = document.querySelectorAll('.exec-tab-button');
    const panels = document.querySelectorAll('.exec-tab-panel');

    if (!buttons.length || !panels.length) {
        return;
    }

    panels.forEach(panel => {
        const isActive = panel.classList.contains('active');
        panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    });

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const targetPanelId = button.getAttribute('aria-controls');

            buttons.forEach(btn => {
                btn.classList.remove('active');
                btn.setAttribute('aria-selected', 'false');
            });

            button.classList.add('active');
            button.setAttribute('aria-selected', 'true');

            panels.forEach(panel => {
                const isMatch = panel.id === targetPanelId;
                panel.classList.toggle('active', isMatch);
                panel.setAttribute('aria-hidden', isMatch ? 'false' : 'true');
            });
        });
    });
}

/**
 * Initialize advanced features
 * Theme manager, filters, export, advanced charts, and comparison mode
 */
function initAdvancedFeatures() {
    const dashboardData = getMetrics();
    const sankeyFlow = getSankeyFlow();
    const textDistributions = getTextDistributions();

    if (dashboardData && dashboardData.metrics) {
        // Initialize theme manager
        ThemeManager.init();

        // Initialize filter manager
        FilterManager.init(dashboardData.metrics);

        // Listen for filter changes and update charts
        FilterManager.onFilterChange((filteredMetrics) => {
            // Update advanced charts with filtered data
            SankeyChart.create('sankeyContainer', filteredMetrics);
            RidgePlot.create('ridgePlotContainer', filteredMetrics);

            const analytics = buildSourceAnalytics(filteredMetrics);
            populateSourceMixSnapshot(analytics);
            populateSourceTable(analytics);
            populateSourceBriefings(analytics);
            refreshDataSourceCharts(filteredMetrics);

            const qualityAnalytics = computeQualityAnalytics(filteredMetrics || []);
            populateQualityOverview(qualityAnalytics);
            refreshQualityCharts(filteredMetrics || []);
        });

        // Create advanced charts
        SankeyChart.create('sankeyContainer', dashboardData.metrics, sankeyFlow);
        RidgePlot.create('ridgePlotContainer', dashboardData.metrics, textDistributions);

        // Initialize comparison mode
        ComparisonMode.init(dashboardData.metrics);

        // Emit dashboardReady event
        window.dispatchEvent(new CustomEvent('dashboardReady'));
        Logger.info('Advanced features initialized');
    }
}

// Run on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
