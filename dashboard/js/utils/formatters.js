/**
 * Formatters Utility Module
 * Provides consistent data formatting functions across the dashboard
 */

/**
 * Normalize source names for consistent display
 * Removes redundant suffixes and standardizes spellings
 *
 * @param {string} source - Raw source name from data
 * @returns {string} Formatted display name
 *
 * @example
 * normalizeSourceName('Wikipedia-Somali') // => 'Wikipedia'
 * normalizeSourceName('BBC_Somali_c4-so') // => 'BBC'
 * normalizeSourceName('Sprakbanken-Somali') // => 'Språkbanken'
 */
export function normalizeSourceName(source) {
    if (!source || typeof source !== 'string') {
        return 'Unknown Source';
    }

    const normalized = source.toLowerCase();

    if (normalized.includes('wikipedia')) {
        return 'Wikipedia';
    }
    if (normalized.includes('bbc')) {
        return 'BBC';
    }
    if (normalized.includes('huggingface') || normalized.includes('mc4')) {
        return 'HuggingFace';
    }
    if (normalized.includes('sprak')) {
        return 'Språkbanken';
    }
    if (normalized.includes('tiktok')) {
        return 'TikTok';
    }

    return source.replace(/-Somali|_Somali_c4-so/, '').trim();
}

/**
 * Format large numbers with K/M suffixes
 *
 * @param {number} value - Number to format
 * @returns {string} Formatted string (e.g., "1.5M", "234K", "42")
 *
 * @example
 * formatNumber(1500000) // => '1.5M'
 * formatNumber(234000) // => '234K'
 * formatNumber(42) // => '42'
 */
export function formatNumber(value) {
    if (typeof value !== 'number' || isNaN(value)) {
        return '0';
    }

    if (value >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    }
    if (value >= 1000) {
        return (value / 1000).toFixed(0) + 'K';
    }
    return value.toString();
}

/**
 * Format percentage values
 *
 * @param {number} value - Decimal value (0-1)
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage (e.g., "95.5%")
 *
 * @example
 * formatPercentage(0.955) // => '95.5%'
 * formatPercentage(0.955, 2) // => '95.50%'
 * formatPercentage(null) // => '0%'
 */
export function formatPercentage(value, decimals = 1) {
    if (typeof value !== 'number' || isNaN(value)) {
        return '0%';
    }
    return (value * 100).toFixed(decimals) + '%';
}

/**
 * Format duration in seconds to human-readable string
 *
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g., "5m 30s", "45s")
 *
 * @example
 * formatDuration(330) // => '5m 30s'
 * formatDuration(45) // => '45s'
 * formatDuration(3665) // => '1h 1m'
 */
export function formatDuration(seconds) {
    if (typeof seconds !== 'number' || isNaN(seconds) || seconds < 0) {
        return '0s';
    }

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    }
    if (minutes > 0) {
        return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
    }
    return `${secs}s`;
}

/**
 * Format bytes to human-readable file size
 *
 * @param {number} bytes - Size in bytes
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted size (e.g., "1.5 MB", "234 KB")
 *
 * @example
 * formatBytes(1536000) // => '1.50 MB'
 * formatBytes(1024) // => '1.00 KB'
 */
export function formatBytes(bytes, decimals = 2) {
    if (typeof bytes !== 'number' || isNaN(bytes) || bytes < 0) {
        return '0 Bytes';
    }

    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format date to locale string
 *
 * @param {string|Date} date - Date to format
 * @param {string} locale - Locale code (default: 'en-US')
 * @returns {string} Formatted date string
 *
 * @example
 * formatDate('2025-10-28') // => 'Oct 28, 2025'
 * formatDate(new Date()) // => 'Oct 28, 2025'
 */
export function formatDate(date, locale = 'en-US') {
    if (!date) return 'N/A';

    try {
        const dateObj = date instanceof Date ? date : new Date(date);
        if (isNaN(dateObj.getTime())) return 'Invalid Date';

        return dateObj.toLocaleDateString(locale, {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } catch (error) {
        return 'Invalid Date';
    }
}

/**
 * Truncate text with ellipsis
 *
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated text with ellipsis if needed
 *
 * @example
 * truncateText('Very long text here', 10) // => 'Very long...'
 */
export function truncateText(text, maxLength) {
    if (!text || typeof text !== 'string') return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}
