/**
 * Theme Manager - Dark Mode Support
 * Manages theme switching, localStorage persistence, and chart color updates
 */

const ThemeManager = {
    themes: {
        LIGHT: 'light',
        DARK: 'dark'
    },

    currentTheme: 'light',
    charts: [],

    /**
     * Initialize theme manager
     */
    init() {
        // Load saved theme or detect system preference
        const savedTheme = localStorage.getItem('dashboard-theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        this.currentTheme = savedTheme || (systemPrefersDark ? this.themes.DARK : this.themes.LIGHT);
        this.applyTheme(this.currentTheme, false);

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('dashboard-theme')) {
                this.setTheme(e.matches ? this.themes.DARK : this.themes.LIGHT);
            }
        });

        // Create toggle button
        this.createToggleButton();
    },

    /**
     * Create theme toggle button
     */
    createToggleButton() {
        const nav = document.querySelector('.nav-links');
        if (!nav) return;

        const toggleContainer = document.createElement('li');
        toggleContainer.style.display = 'flex';
        toggleContainer.style.alignItems = 'center';

        const toggle = document.createElement('button');
        toggle.id = 'theme-toggle';
        toggle.className = 'theme-toggle';
        toggle.setAttribute('aria-label', 'Toggle dark mode');
        toggle.setAttribute('title', 'Toggle dark mode');
        toggle.innerHTML = this.getToggleIcon();

        toggle.addEventListener('click', () => {
            this.toggle();
        });

        toggleContainer.appendChild(toggle);
        nav.appendChild(toggleContainer);
    },

    /**
     * Get toggle icon SVG based on current theme
     */
    getToggleIcon() {
        if (this.currentTheme === this.themes.DARK) {
            // Sun icon (switch to light)
            return `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="5"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                </svg>
            `;
        } else {
            // Moon icon (switch to dark)
            return `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                </svg>
            `;
        }
    },

    /**
     * Toggle between light and dark themes
     */
    toggle() {
        const newTheme = this.currentTheme === this.themes.LIGHT ? this.themes.DARK : this.themes.LIGHT;
        this.setTheme(newTheme);
    },

    /**
     * Set specific theme
     */
    setTheme(theme) {
        if (!Object.values(this.themes).includes(theme)) return;

        this.currentTheme = theme;
        localStorage.setItem('dashboard-theme', theme);
        this.applyTheme(theme);

        // Update toggle icon
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            toggle.innerHTML = this.getToggleIcon();
        }

        // Notify listeners
        window.dispatchEvent(new CustomEvent('themeChange', {
            detail: { theme }
        }));
    },

    /**
     * Apply theme to document
     */
    applyTheme(theme, animate = true) {
        document.documentElement.setAttribute('data-theme', theme);

        if (animate) {
            document.documentElement.classList.add('theme-transition');
            setTimeout(() => {
                document.documentElement.classList.remove('theme-transition');
            }, 300);
        }

        // Update all registered charts
        this.updateChartThemes();
    },

    /**
     * Register a chart for theme updates
     */
    registerChart(chart) {
        if (chart && !this.charts.includes(chart)) {
            this.charts.push(chart);
        }
    },

    /**
     * Update all charts with new theme colors
     */
    updateChartThemes() {
        const isDark = this.currentTheme === this.themes.DARK;

        this.charts.forEach(chart => {
            if (!chart || typeof chart.update !== 'function') return;

            // Update chart options for dark mode
            if (chart.options) {
                // Update text colors
                if (chart.options.plugins?.legend?.labels) {
                    chart.options.plugins.legend.labels.color = isDark ? '#e5e7eb' : '#374151';
                }

                if (chart.options.plugins?.title) {
                    chart.options.plugins.title.color = isDark ? '#e5e7eb' : '#374151';
                }

                // Update grid colors
                if (chart.options.scales) {
                    Object.keys(chart.options.scales).forEach(scaleKey => {
                        const scale = chart.options.scales[scaleKey];
                        if (scale.grid) {
                            scale.grid.color = isDark ? '#374151' : '#e5e7eb';
                        }
                        if (scale.ticks) {
                            scale.ticks.color = isDark ? '#9ca3af' : '#6b7280';
                        }
                    });
                }

                // Update tooltip background
                if (chart.options.plugins?.tooltip) {
                    chart.options.plugins.tooltip.backgroundColor = isDark ? '#1f2937' : 'rgba(0, 0, 0, 0.8)';
                }
            }

            chart.update('none'); // Update without animation
        });
    },

    /**
     * Get color for current theme
     */
    getThemeColor(lightColor, darkColor) {
        return this.currentTheme === this.themes.DARK ? darkColor : lightColor;
    },

    /**
     * Get current theme
     */
    getCurrentTheme() {
        return this.currentTheme;
    },

    /**
     * Check if dark mode is active
     */
    isDarkMode() {
        return this.currentTheme === this.themes.DARK;
    },

    /**
     * Get theme-aware chart colors
     */
    getChartColors() {
        const isDark = this.isDarkMode();

        return {
            primary: isDark ? '#60a5fa' : '#0176D3',
            secondary: isDark ? '#4b8fd6' : '#032D60',
            success: isDark ? '#34d399' : '#00A651',
            warning: isDark ? '#fbbf24' : '#f59e0b',
            error: isDark ? '#f87171' : '#ef4444',
            wikipedia: isDark ? '#60a5fa' : '#3b82f6',
            bbc: isDark ? '#f87171' : '#ef4444',
            huggingface: isDark ? '#34d399' : '#00A651',
            sprakbanken: isDark ? '#fbbf24' : '#f59e0b',
            text: isDark ? '#e5e7eb' : '#374151',
            textLight: isDark ? '#9ca3af' : '#6b7280',
            background: isDark ? '#111827' : '#ffffff',
            backgroundAlt: isDark ? '#1f2937' : '#f9fafb',
            border: isDark ? '#374151' : '#e5e7eb',
            gridLine: isDark ? '#374151' : '#e5e7eb'
        };
    }
};

// Export for use in main dashboard
if (typeof window !== 'undefined') {
    window.ThemeManager = ThemeManager;

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
    } else {
        ThemeManager.init();
    }
}
