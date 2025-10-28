/**
 * Logger Utility Module
 * Provides structured logging with level control and formatting
 * Replaces console.log/warn/error with production-ready logging
 */

import { Config } from '../config.js';

/**
 * Log levels enum
 */
const LogLevel = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    OFF: 4
};

/**
 * Logger class for structured logging
 */
export class Logger {
    /**
     * Current log level
     * Only messages at or above this level will be logged
     */
    static level = Config.isDevelopment() ? LogLevel.DEBUG : LogLevel.INFO;

    /**
     * Log a debug message (development only)
     * @param {string} message - The message to log
     * @param {*} data - Optional data to log
     */
    static debug(message, data = null) {
        if (this.level <= LogLevel.DEBUG) {
            console.log(`[DEBUG] ${message}`, data ? data : '');
        }
    }

    /**
     * Log an info message
     * @param {string} message - The message to log
     * @param {*} data - Optional data to log
     */
    static info(message, data = null) {
        if (this.level <= LogLevel.INFO) {
            console.log(`✓ ${message}`, data ? data : '');
        }
    }

    /**
     * Log a warning message
     * @param {string} message - The warning message
     * @param {*} data - Optional data to log
     */
    static warn(message, data = null) {
        if (this.level <= LogLevel.WARN) {
            console.warn(`⚠ ${message}`, data ? data : '');
        }
    }

    /**
     * Log an error message
     * @param {string} message - The error message
     * @param {Error} error - Optional error object
     */
    static error(message, error = null) {
        if (this.level <= LogLevel.ERROR) {
            console.error(`✗ ${message}`, error ? error : '');

            // Log stack trace in development
            if (Config.isDevelopment() && error && error.stack) {
                console.error('Stack trace:', error.stack);
            }
        }
    }

    /**
     * Set the log level
     * @param {number} level - The log level (use LogLevel enum)
     */
    static setLevel(level) {
        this.level = level;
    }

    /**
     * Time a function execution
     * @param {string} label - Label for the timer
     * @param {Function} fn - Function to time
     * @returns {*} Result of the function
     */
    static async time(label, fn) {
        const start = performance.now();
        try {
            const result = await fn();
            const duration = (performance.now() - start).toFixed(2);
            this.debug(`${label} completed in ${duration}ms`);
            return result;
        } catch (error) {
            const duration = (performance.now() - start).toFixed(2);
            this.error(`${label} failed after ${duration}ms`, error);
            throw error;
        }
    }
}

/**
 * Custom error classes for better error handling
 */

export class DataLoadError extends Error {
    constructor(message, paths) {
        super(message);
        this.name = 'DataLoadError';
        this.paths = paths;
    }
}

export class DataValidationError extends Error {
    constructor(message, data) {
        super(message);
        this.name = 'DataValidationError';
        this.data = data;
    }
}

export class NetworkError extends Error {
    constructor(message, url, status) {
        super(message);
        this.name = 'NetworkError';
        this.url = url;
        this.status = status;
    }
}
