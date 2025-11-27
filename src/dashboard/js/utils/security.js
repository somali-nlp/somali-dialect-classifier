/**
 * Security utilities for XSS prevention.
 *
 * Provides HTML escaping and sanitization to prevent XSS attacks.
 */

/**
 * Escape HTML special characters to prevent XSS.
 *
 * Converts special characters to HTML entities:
 * - < becomes &lt;
 * - > becomes &gt;
 * - & becomes &amp;
 * - " becomes &quot;
 * - ' becomes &#x27;
 *
 * @param {string} unsafe - Potentially unsafe string
 * @returns {string} HTML-escaped string
 *
 * @example
 * escapeHtml('<script>alert("XSS")</script>')
 * // Returns: '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
 */
export function escapeHtml(unsafe) {
    if (!unsafe) return '';
    if (typeof unsafe !== 'string') {
        unsafe = String(unsafe);
    }

    return unsafe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

/**
 * Sanitize URL to prevent javascript: protocol attacks.
 *
 * Only allows http, https, and relative URLs.
 * Blocks javascript:, data:, vbscript:, and other dangerous protocols.
 *
 * @param {string} url - URL to sanitize
 * @returns {string} Sanitized URL or empty string if dangerous
 *
 * @example
 * sanitizeUrl('javascript:alert(1)')
 * // Returns: ''
 *
 * sanitizeUrl('https://example.com')
 * // Returns: 'https://example.com'
 */
export function sanitizeUrl(url) {
    if (!url) return '';
    if (typeof url !== 'string') return '';

    // Trim whitespace
    url = url.trim();

    // Normalize to lowercase for protocol check
    const urlLower = url.toLowerCase();

    // Block dangerous protocols
    const dangerousProtocols = [
        'javascript:',
        'data:',
        'vbscript:',
        'file:',
        'about:',
    ];

    for (const protocol of dangerousProtocols) {
        if (urlLower.startsWith(protocol)) {
            console.warn(`Blocked dangerous URL protocol: ${url}`);
            return '';
        }
    }

    // Allow http, https, and relative URLs
    if (
        urlLower.startsWith('http://') ||
        urlLower.startsWith('https://') ||
        urlLower.startsWith('/') ||
        urlLower.startsWith('./') ||
        urlLower.startsWith('../')
    ) {
        return url;
    }

    // For other cases, assume relative URL
    return url;
}

/**
 * Create safe HTML attributes.
 *
 * Escapes attribute values to prevent XSS via attributes.
 *
 * @param {Object} attrs - Attribute key-value pairs
 * @returns {string} Safe attribute string
 *
 * @example
 * createSafeAttributes({ href: 'https://example.com', title: 'Link <script>' })
 * // Returns: 'href="https://example.com" title="Link &lt;script&gt;"'
 */
export function createSafeAttributes(attrs) {
    if (!attrs || typeof attrs !== 'object') return '';

    return Object.entries(attrs)
        .map(([key, value]) => {
            // Sanitize attribute name (allow only alphanumeric and hyphens)
            const safeKey = key.replace(/[^a-zA-Z0-9-]/g, '');

            // Special handling for URLs
            if (key === 'href' || key === 'src') {
                value = sanitizeUrl(value);
            } else {
                value = escapeHtml(value);
            }

            return `${safeKey}="${value}"`;
        })
        .join(' ');
}

/**
 * Render text content safely without HTML interpretation.
 *
 * Uses textContent instead of innerHTML to prevent XSS.
 *
 * @param {HTMLElement} element - DOM element
 * @param {string} text - Text to render
 *
 * @example
 * const div = document.getElementById('content');
 * setTextContent(div, '<script>alert(1)</script>');
 * // Renders as literal text, not executed
 */
export function setTextContent(element, text) {
    if (!element) return;
    element.textContent = text || '';
}

/**
 * Create sanitized HTML element with escaped content.
 *
 * Safer alternative to innerHTML for dynamic content.
 *
 * @param {string} tagName - HTML tag name
 * @param {Object} options - Element options
 * @param {string} options.text - Text content (will be escaped)
 * @param {string} options.html - HTML content (use with caution)
 * @param {Object} options.attrs - HTML attributes
 * @param {string} options.className - CSS class names
 * @returns {HTMLElement} Sanitized element
 *
 * @example
 * const link = createSafeElement('a', {
 *     text: 'Click here <script>',
 *     attrs: { href: 'https://example.com' },
 *     className: 'btn btn-primary'
 * });
 */
export function createSafeElement(tagName, options = {}) {
    const element = document.createElement(tagName);

    // Set text content (escaped)
    if (options.text) {
        element.textContent = options.text;
    }

    // Set HTML content (use with caution - prefer text)
    if (options.html) {
        console.warn('createSafeElement: Using innerHTML should be avoided. Prefer text option.');
        element.innerHTML = options.html;
    }

    // Set attributes
    if (options.attrs) {
        for (const [key, value] of Object.entries(options.attrs)) {
            if (key === 'href' || key === 'src') {
                const safeUrl = sanitizeUrl(value);
                if (safeUrl) {
                    element.setAttribute(key, safeUrl);
                }
            } else {
                element.setAttribute(key, value);
            }
        }
    }

    // Set class name
    if (options.className) {
        element.className = options.className;
    }

    return element;
}

/**
 * Safely append child elements.
 *
 * @param {HTMLElement} parent - Parent element
 * @param {HTMLElement|HTMLElement[]} children - Child element(s) to append
 */
export function safeAppendChild(parent, children) {
    if (!parent) return;

    if (Array.isArray(children)) {
        children.forEach(child => {
            if (child instanceof HTMLElement) {
                parent.appendChild(child);
            }
        });
    } else if (children instanceof HTMLElement) {
        parent.appendChild(children);
    }
}
