/**
 * Enhanced Chart.js Configuration Module
 * Somali Dialect Classifier Dashboard
 *
 * Features:
 * - Colorblind-safe palettes (Paul Tol's palette)
 * - Advanced interactivity (zoom, pan, crosshair, data export)
 * - Comprehensive accessibility (ARIA, keyboard navigation)
 * - Mobile optimizations (responsive, touch-friendly)
 * - Performance optimizations (lazy loading, decimation)
 *
 * Dependencies:
 * - Chart.js 4.4.0+
 * - chartjs-plugin-zoom 2.0.0+
 * - chartjs-plugin-annotation 3.0.0+ (optional for annotations)
 */

// ============================================================================
// COLORBLIND-SAFE PALETTES
// ============================================================================

/**
 * Paul Tol's colorblind-safe qualitative palette
 * Source: https://personal.sron.nl/~pault/
 * Verified with Color Oracle for deuteranopia, protanopia, and tritanopia
 */
const ColorPalettes = {
    // Bright qualitative scheme (max 7 colors) - best for distinct categories
    bright: [
        '#4477AA', // Blue
        '#EE6677', // Red
        '#228833', // Green
        '#CCBB44', // Yellow
        '#66CCEE', // Cyan
        '#AA3377', // Purple
        '#BBBBBB'  // Grey
    ],

    // High contrast scheme (max 3 colors) - best for emphasis
    highContrast: [
        '#004488', // Dark blue
        '#DDAA33', // Orange
        '#BB5566'  // Red-purple
    ],

    // Vibrant scheme (max 7 colors) - balanced visibility
    vibrant: [
        '#EE7733', // Orange
        '#0077BB', // Blue
        '#33BBEE', // Cyan
        '#EE3377', // Magenta
        '#CC3311', // Red
        '#009988', // Teal
        '#BBBBBB'  // Grey
    ],

    // Sequential schemes for heatmaps/gradients
    sequential: {
        blue: ['#F0F9FF', '#CCEEFF', '#99DDFF', '#66CCFF', '#33BBFF', '#0099DD', '#0077BB'],
        green: ['#F0FFF4', '#D1FAE5', '#A7F3D0', '#6EE7B7', '#34D399', '#10B981', '#059669'],
        orange: ['#FFF7ED', '#FFEDD5', '#FED7AA', '#FDBA74', '#FB923C', '#F97316', '#EA580C'],
        purple: ['#FAF5FF', '#F3E8FF', '#E9D5FF', '#D8B4FE', '#C084FC', '#A855F7', '#9333EA']
    },

    // Diverging scheme for showing deviation from center
    diverging: {
        blueRed: ['#053061', '#2166AC', '#4393C3', '#92C5DE', '#D1E5F0', '#F7F7F7', '#FDDBC7', '#F4A582', '#D6604D', '#B2182B', '#67001F']
    }
};

/**
 * Map data sources to consistent colors
 */
const SourceColors = {
    'Wikipedia-Somali': ColorPalettes.bright[0],      // Blue
    'BBC-Somali': ColorPalettes.bright[1],            // Red
    'HuggingFace-MC4': ColorPalettes.bright[2],       // Green
    'Sprakbanken': ColorPalettes.bright[3],           // Yellow
    'default': ColorPalettes.bright[6]                 // Grey for unknown sources
};

/**
 * Get color with opacity
 */
function getColorWithAlpha(color, alpha = 1.0) {
    // Convert hex to rgba
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ============================================================================
// ACCESSIBILITY CONFIGURATION
// ============================================================================

/**
 * Accessible chart defaults
 * Implements WCAG 2.1 AA standards
 */
const AccessibilityDefaults = {
    // Font configuration for readability
    font: {
        family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        size: 14,
        lineHeight: 1.5,
        weight: 400
    },

    // Color configuration
    color: '#374151', // WCAG AA contrast ratio > 4.5:1 on white

    // Animation configuration (reduced motion support)
    animation: {
        duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 750,
        easing: 'easeInOutQuart'
    },

    // Interaction configuration
    interaction: {
        mode: 'index',
        intersect: false
    },

    // Tooltip configuration for keyboard users
    tooltip: {
        enabled: true,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: '#4B5563',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 6,
        titleFont: {
            size: 14,
            weight: 600
        },
        bodyFont: {
            size: 13,
            weight: 400
        },
        displayColors: true,
        boxWidth: 12,
        boxHeight: 12,
        boxPadding: 6,
        usePointStyle: true
    }
};

/**
 * Setup keyboard navigation for chart
 */
function setupKeyboardNavigation(chart, canvas) {
    let currentIndex = 0;
    const maxIndex = chart.data.labels ? chart.data.labels.length - 1 : 0;

    canvas.setAttribute('tabindex', '0');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', chart.options.plugins?.title?.text || 'Data visualization');

    canvas.addEventListener('keydown', (e) => {
        switch(e.key) {
            case 'ArrowRight':
            case 'ArrowUp':
                e.preventDefault();
                currentIndex = Math.min(currentIndex + 1, maxIndex);
                showTooltipAtIndex(chart, currentIndex);
                announceDataPoint(chart, currentIndex);
                break;

            case 'ArrowLeft':
            case 'ArrowDown':
                e.preventDefault();
                currentIndex = Math.max(currentIndex - 1, 0);
                showTooltipAtIndex(chart, currentIndex);
                announceDataPoint(chart, currentIndex);
                break;

            case 'Home':
                e.preventDefault();
                currentIndex = 0;
                showTooltipAtIndex(chart, currentIndex);
                announceDataPoint(chart, currentIndex);
                break;

            case 'End':
                e.preventDefault();
                currentIndex = maxIndex;
                showTooltipAtIndex(chart, currentIndex);
                announceDataPoint(chart, currentIndex);
                break;

            case 'Escape':
                e.preventDefault();
                chart.tooltip.setActiveElements([]);
                chart.update('none');
                break;
        }
    });

    // Focus indicator
    canvas.addEventListener('focus', () => {
        canvas.style.outline = '3px solid #2563EB';
        canvas.style.outlineOffset = '3px';
    });

    canvas.addEventListener('blur', () => {
        canvas.style.outline = 'none';
        chart.tooltip.setActiveElements([]);
        chart.update('none');
    });
}

/**
 * Show tooltip at specific data index
 */
function showTooltipAtIndex(chart, index) {
    const activeElements = [];
    chart.data.datasets.forEach((dataset, datasetIndex) => {
        if (dataset.data[index] !== undefined) {
            activeElements.push({
                datasetIndex: datasetIndex,
                index: index
            });
        }
    });

    chart.tooltip.setActiveElements(activeElements);
    chart.setActiveElements(activeElements);
    chart.update('none');
}

/**
 * Announce data point for screen readers
 */
function announceDataPoint(chart, index) {
    const label = chart.data.labels?.[index] || `Data point ${index + 1}`;
    const values = chart.data.datasets.map(dataset => {
        const value = dataset.data[index];
        return `${dataset.label}: ${formatValue(value, dataset)}`;
    }).join(', ');

    announceToScreenReader(`${label}. ${values}`);
}

/**
 * Create live region for screen reader announcements
 */
function announceToScreenReader(message) {
    let liveRegion = document.getElementById('chart-live-region');

    if (!liveRegion) {
        liveRegion = document.createElement('div');
        liveRegion.id = 'chart-live-region';
        liveRegion.setAttribute('role', 'status');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.style.position = 'absolute';
        liveRegion.style.left = '-10000px';
        liveRegion.style.width = '1px';
        liveRegion.style.height = '1px';
        liveRegion.style.overflow = 'hidden';
        document.body.appendChild(liveRegion);
    }

    liveRegion.textContent = message;
}

/**
 * Format value for display
 */
function formatValue(value, dataset) {
    if (value === null || value === undefined) return 'No data';

    // Check if it's a percentage
    if (dataset.label?.toLowerCase().includes('rate') ||
        dataset.label?.toLowerCase().includes('percent')) {
        return `${value.toFixed(1)}%`;
    }

    // Check if it's a large number
    if (typeof value === 'number' && value >= 1000) {
        return value.toLocaleString('en-US');
    }

    return value.toString();
}

// ============================================================================
// INTERACTIVITY ENHANCEMENTS
// ============================================================================

/**
 * Zoom and pan configuration
 * Requires chartjs-plugin-zoom
 */
const ZoomConfig = {
    pan: {
        enabled: true,
        mode: 'x',
        modifierKey: null, // No modifier key needed
        scaleMode: 'x',
        onPanComplete: ({ chart }) => {
            announceToScreenReader('Chart panned. Press R to reset zoom.');
        }
    },
    zoom: {
        wheel: {
            enabled: true,
            speed: 0.1,
            modifierKey: null
        },
        pinch: {
            enabled: true
        },
        mode: 'x',
        onZoomComplete: ({ chart }) => {
            announceToScreenReader('Chart zoomed. Press R to reset zoom.');
        }
    },
    limits: {
        x: { min: 'original', max: 'original', minRange: 1000 * 60 * 60 * 24 }, // 1 day minimum
        y: { min: 0, max: 'original' }
    }
};

/**
 * Setup zoom reset button
 */
function setupZoomReset(chart, canvas) {
    // Add keyboard shortcut
    canvas.addEventListener('keydown', (e) => {
        if (e.key === 'r' || e.key === 'R') {
            e.preventDefault();
            chart.resetZoom();
            announceToScreenReader('Zoom reset to default view');
        }
    });

    // Add reset button if zoom plugin is available
    if (chart.options.plugins?.zoom) {
        const container = canvas.parentElement;
        let resetBtn = container.querySelector('.chart-reset-zoom');

        if (!resetBtn) {
            resetBtn = document.createElement('button');
            resetBtn.className = 'chart-reset-zoom';
            resetBtn.textContent = 'Reset Zoom';
            resetBtn.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                padding: 6px 12px;
                background: #ffffff;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.2s ease;
                z-index: 10;
            `;
            resetBtn.setAttribute('aria-label', 'Reset chart zoom to default view');

            resetBtn.addEventListener('click', () => {
                chart.resetZoom();
                announceToScreenReader('Zoom reset to default view');
            });

            container.style.position = 'relative';
            container.appendChild(resetBtn);
        }

        // Show/hide reset button based on zoom state
        chart.options.plugins.zoom.zoom.onZoom = ({ chart }) => {
            resetBtn.style.opacity = '1';
            resetBtn.style.pointerEvents = 'auto';
        };

        chart.options.plugins.zoom.zoom.onZoomComplete = ({ chart }) => {
            announceToScreenReader('Chart zoomed. Press R or click Reset Zoom button to reset.');
        };

        chart.options.plugins.zoom.zoom.onZoomRejected = () => {
            resetBtn.style.opacity = '0';
            resetBtn.style.pointerEvents = 'none';
        };
    }
}

/**
 * Crosshair plugin for better data point identification
 */
const CrosshairPlugin = {
    id: 'crosshair',
    defaults: {
        enabled: true,
        color: 'rgba(107, 114, 128, 0.5)',
        width: 1,
        dash: [5, 5]
    },

    afterDraw(chart, args, options) {
        if (!options.enabled) return;

        const { ctx, chartArea: { left, right, top, bottom } } = chart;
        const activeElements = chart.tooltip?._active || [];

        if (activeElements.length === 0) return;

        const x = activeElements[0].element.x;

        ctx.save();
        ctx.beginPath();
        ctx.setLineDash(options.dash);
        ctx.strokeStyle = options.color;
        ctx.lineWidth = options.width;
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
        ctx.restore();
    }
};

/**
 * Data export functionality
 */
function setupDataExport(chart, canvas, filename = 'chart-data') {
    const container = canvas.parentElement;
    let exportBtn = container.querySelector('.chart-export-btn');

    if (!exportBtn) {
        exportBtn = document.createElement('button');
        exportBtn.className = 'chart-export-btn';
        exportBtn.innerHTML = '&#8595; CSV'; // Download arrow
        exportBtn.style.cssText = `
            position: absolute;
            top: 10px;
            right: 100px;
            padding: 6px 12px;
            background: #ffffff;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            z-index: 10;
        `;
        exportBtn.setAttribute('aria-label', 'Export chart data as CSV');

        exportBtn.addEventListener('click', () => {
            exportChartDataAsCSV(chart, filename);
            announceToScreenReader('Chart data exported as CSV');
        });

        exportBtn.addEventListener('mouseenter', () => {
            exportBtn.style.background = '#F3F4F6';
        });

        exportBtn.addEventListener('mouseleave', () => {
            exportBtn.style.background = '#ffffff';
        });

        container.appendChild(exportBtn);
    }
}

/**
 * Export chart data to CSV
 */
function exportChartDataAsCSV(chart, filename) {
    const rows = [];
    const headers = ['Label', ...chart.data.datasets.map(d => d.label)];
    rows.push(headers.join(','));

    chart.data.labels.forEach((label, index) => {
        const row = [
            label,
            ...chart.data.datasets.map(dataset => {
                const value = dataset.data[index];
                return typeof value === 'object' ? value.y : value;
            })
        ];
        rows.push(row.join(','));
    });

    const csv = rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
}

// ============================================================================
// MOBILE OPTIMIZATIONS
// ============================================================================

/**
 * Responsive configuration based on screen size
 */
function getResponsiveConfig() {
    const isMobile = window.innerWidth < 768;
    const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

    return {
        responsive: true,
        maintainAspectRatio: false,

        // Adjust font sizes for mobile
        plugins: {
            legend: {
                display: !isMobile, // Hide legend on mobile to save space
                position: isMobile ? 'bottom' : 'top',
                labels: {
                    padding: isMobile ? 8 : 10,
                    font: {
                        size: isMobile ? 11 : 13
                    },
                    boxWidth: isMobile ? 10 : 12,
                    boxHeight: isMobile ? 10 : 12
                }
            },
            tooltip: {
                enabled: true,
                padding: isMobile ? 8 : 12,
                titleFont: {
                    size: isMobile ? 12 : 14
                },
                bodyFont: {
                    size: isMobile ? 11 : 13
                },
                // Position tooltips better on mobile
                position: 'nearest',
                caretPadding: isMobile ? 8 : 10
            },
            title: {
                display: true,
                padding: {
                    top: isMobile ? 8 : 10,
                    bottom: isMobile ? 8 : 16
                },
                font: {
                    size: isMobile ? 14 : 16,
                    weight: 600
                }
            }
        },

        // Adjust scales for mobile
        scales: {
            x: {
                ticks: {
                    font: {
                        size: isMobile ? 10 : 12
                    },
                    maxRotation: isMobile ? 45 : 0,
                    minRotation: isMobile ? 45 : 0,
                    autoSkip: true,
                    autoSkipPadding: isMobile ? 20 : 10,
                    maxTicksLimit: isMobile ? 6 : 12
                },
                grid: {
                    display: !isMobile // Hide grid lines on mobile for clarity
                }
            },
            y: {
                ticks: {
                    font: {
                        size: isMobile ? 10 : 12
                    },
                    maxTicksLimit: isMobile ? 6 : 10
                },
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            }
        },

        // Touch interaction improvements
        interaction: {
            mode: isMobile ? 'nearest' : 'index',
            axis: isMobile ? 'x' : 'xy',
            intersect: false
        },

        // Point sizing for touch targets
        elements: {
            point: {
                radius: isMobile ? 6 : 4,
                hoverRadius: isMobile ? 8 : 6,
                hitRadius: isMobile ? 20 : 10 // Larger hit area for touch
            },
            line: {
                borderWidth: isMobile ? 3 : 2
            },
            bar: {
                borderRadius: isMobile ? 4 : 6
            }
        }
    };
}

/**
 * Setup responsive resize handler
 */
function setupResponsiveResize(chart) {
    let resizeTimeout;

    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            // Update chart options based on new size
            const responsiveConfig = getResponsiveConfig();
            Object.assign(chart.options, responsiveConfig);
            chart.update('none'); // Update without animation

            announceToScreenReader('Chart resized for current screen size');
        }, 250); // Debounce resize events
    });
}

// ============================================================================
// PERFORMANCE OPTIMIZATIONS
// ============================================================================

/**
 * Decimation configuration for large datasets
 * Reduces number of points displayed while maintaining visual fidelity
 */
const DecimationConfig = {
    enabled: true,
    algorithm: 'lttb', // Largest Triangle Three Buckets - best quality
    samples: 500,
    threshold: 1000 // Only decimate if more than 1000 points
};

/**
 * Lazy loading configuration
 */
function setupLazyLoading(canvas, renderFunction) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Chart is visible, render it
                renderFunction();
                observer.unobserve(entry.target);
            }
        });
    }, {
        rootMargin: '50px' // Start loading 50px before chart is visible
    });

    observer.observe(canvas);
}

/**
 * Progressive rendering for complex charts
 */
function progressiveRender(chart, data, chunkSize = 100) {
    let currentIndex = 0;

    function renderChunk() {
        const end = Math.min(currentIndex + chunkSize, data.length);
        const chunk = data.slice(currentIndex, end);

        // Add chunk to chart
        chunk.forEach(item => {
            chart.data.labels.push(item.label);
            chart.data.datasets.forEach((dataset, i) => {
                dataset.data.push(item.datasets[i]);
            });
        });

        chart.update('none');
        currentIndex = end;

        if (currentIndex < data.length) {
            requestAnimationFrame(renderChunk);
        } else {
            // Final update with animation
            chart.update();
            announceToScreenReader('Chart fully loaded');
        }
    }

    renderChunk();
}

// ============================================================================
// DATA TABLE ALTERNATIVE
// ============================================================================

/**
 * Generate accessible data table from chart data
 */
function generateDataTable(chart, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const table = document.createElement('table');
    table.className = 'chart-data-table';
    table.setAttribute('role', 'table');
    table.setAttribute('aria-label', `Data table for ${chart.options.plugins.title?.text || 'chart'}`);

    // Create table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.setAttribute('role', 'row');

    const labelHeader = document.createElement('th');
    labelHeader.setAttribute('role', 'columnheader');
    labelHeader.textContent = 'Label';
    headerRow.appendChild(labelHeader);

    chart.data.datasets.forEach(dataset => {
        const th = document.createElement('th');
        th.setAttribute('role', 'columnheader');
        th.textContent = dataset.label;
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create table body
    const tbody = document.createElement('tbody');
    tbody.setAttribute('role', 'rowgroup');

    chart.data.labels.forEach((label, index) => {
        const row = document.createElement('tr');
        row.setAttribute('role', 'row');

        const labelCell = document.createElement('td');
        labelCell.setAttribute('role', 'cell');
        labelCell.textContent = label;
        row.appendChild(labelCell);

        chart.data.datasets.forEach(dataset => {
            const cell = document.createElement('td');
            cell.setAttribute('role', 'cell');
            const value = dataset.data[index];
            cell.textContent = formatValue(value, dataset);
            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    container.appendChild(table);

    // Add toggle button
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'chart-table-toggle';
    toggleBtn.textContent = 'Show Data Table';
    toggleBtn.setAttribute('aria-label', 'Toggle data table visibility');
    toggleBtn.setAttribute('aria-expanded', 'false');

    let tableVisible = false;
    table.style.display = 'none';

    toggleBtn.addEventListener('click', () => {
        tableVisible = !tableVisible;
        table.style.display = tableVisible ? 'table' : 'none';
        toggleBtn.textContent = tableVisible ? 'Hide Data Table' : 'Show Data Table';
        toggleBtn.setAttribute('aria-expanded', tableVisible.toString());
        announceToScreenReader(tableVisible ? 'Data table shown' : 'Data table hidden');
    });

    container.insertBefore(toggleBtn, table);
}

// ============================================================================
// EXPORT MODULE
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ColorPalettes,
        SourceColors,
        getColorWithAlpha,
        AccessibilityDefaults,
        setupKeyboardNavigation,
        ZoomConfig,
        setupZoomReset,
        CrosshairPlugin,
        setupDataExport,
        getResponsiveConfig,
        setupResponsiveResize,
        DecimationConfig,
        setupLazyLoading,
        progressiveRender,
        generateDataTable
    };
}
