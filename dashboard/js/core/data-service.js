/**
 * Data Service Module
 * Handles loading and managing metrics data from JSON files
 */

// Store metrics data globally for the module
let metricsData = null;

/**
 * Load metrics from JSON file
 * Tries multiple paths for robustness
 * @returns {Promise<Object>} The loaded metrics data
 */
export async function loadMetrics() {
    try {
        // Try multiple paths (relative and absolute)
        const paths = [
            'metrics-ledger.json',
            './metrics-ledger.json',
            '../metrics-ledger.json',
            '/metrics-ledger.json'
        ];

        let metricsResponse = null;
        for (const path of paths) {
            try {
                const response = await fetch(path);
                if (response.ok) {
                    metricsResponse = response;
                    break;
                }
            } catch (e) {
                continue;
            }
        }

        if (!metricsResponse) {
            console.warn('⚠ Could not load metrics from any path, using empty state');
            return { metrics: [] };
        }

        metricsData = await metricsResponse.json();
        console.log('✓ Metrics loaded successfully:', metricsData);
        return metricsData;
    } catch (error) {
        console.error('✗ Error loading metrics:', error);
        return { metrics: [] };
    }
}

/**
 * Get currently loaded metrics data
 * @returns {Object|null} The metrics data or null if not loaded
 */
export function getMetrics() {
    return metricsData;
}
